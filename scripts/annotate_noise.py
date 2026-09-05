"""Interactive annotator for the label-noise slice.

Editing 150 rows of Turkish in a spreadsheet invites two failure modes that are
hard to detect afterwards: an encoding change that mangles Turkish characters,
and a mis-scrolled row that shifts every answer by one. This walks the rows one
at a time, writes the answer straight back into the CSV, and is resumable, so
neither can happen and the work can be done in any number of sittings.

  python scripts/annotate_noise.py            # start / resume
  python scripts/annotate_noise.py --stats    # report epsilon, annotate nothing

Keys per row:  e = label correct   h = label wrong   s = skip / unsure
               b = back one row    q = save and quit

The question is NOT "is this the best possible label". It is "would a careful
annotator have rejected this label as wrong". Anything defensible counts as
correct -- we are measuring error, not taste.
"""
import argparse
import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANS, FIX, NOTE = 5, 6, 7          # column indices written by make_noise_slice.py


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval -- correct near 0, where the normal approximation
    produces negative lower bounds and would understate the uncertainty."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - m), min(1.0, c + m)


def load(path: Path) -> tuple[list, list]:
    rows = list(csv.reader(path.open(encoding="utf-8-sig")))
    if not rows:
        sys.exit(f"{path} is empty -- run: python scripts/make_noise_slice.py")
    return rows[0], [r + [""] * (8 - len(r)) for r in rows[1:]]


def save(path: Path, header: list, body: list) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(body)
    tmp.replace(path)                      # atomic: a Ctrl-C cannot truncate the file


def stats(body: list) -> tuple[int, int, int]:
    ok = sum(1 for r in body if r[ANS].strip().lower() == "e")
    bad = sum(1 for r in body if r[ANS].strip().lower() == "h")
    return ok, bad, len(body)


def report(body: list) -> None:
    ok, bad, total = stats(body)
    judged = ok + bad
    print(f"\n  judged {judged}/{total}   correct {ok}   wrong {bad}")
    if judged == 0:
        return
    eps = bad / judged
    lo, hi = wilson(bad, judged)
    print(f"  label-noise rate  eps = {eps:.3f}  ({eps*100:.1f}%)")
    print(f"  95% Wilson CI     [{lo*100:.1f}%, {hi*100:.1f}%]")
    if judged < total:
        print(f"  ({total - judged} rows still unjudged -- eps is provisional)")
    else:
        print("\n  Record this in DATACARD.md under the intent axis, with n and the CI.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "label_noise_massive.csv"))
    ap.add_argument("--stats", action="store_true", help="report only")
    a = ap.parse_args()
    path = Path(a.csv)
    if not path.exists():
        sys.exit(f"{path} not found -- run: python scripts/make_noise_slice.py")

    header, body = load(path)
    if a.stats:
        report(body)
        return

    i = 0
    while i < len(body):
        r = body[i]
        if r[ANS].strip():                 # resume: skip what is already answered
            i += 1
            continue
        done = sum(1 for x in body if x[ANS].strip())
        print("\n" + "=" * 72)
        print(f"  row {r[0]} of {len(body)}      answered so far: {done}")
        print("=" * 72)
        print(f"  TR    {r[2]}")
        print(f"  EN    {r[3]}")
        print(f"\n  LABEL {r[4]}")
        try:
            k = input("\n  correct? [e]vet  [h]ayır  [s]kip  [b]ack  [q]uit > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            save(path, header, body)
            print("\nsaved.")
            return
        if k == "q":
            save(path, header, body)
            print("\nsaved -- rerun the same command to continue.")
            report(body)
            return
        if k == "b":
            i = max(0, i - 1)
            body[i][ANS] = ""              # clear it so the loop re-asks
            continue
        if k == "s":
            i += 1
            continue
        if k not in ("e", "h"):
            print("  -- press e, h, s, b or q")
            continue
        r[ANS] = k
        if k == "h":
            r[FIX] = input("  what should it be? (blank = don't know) > ").strip()
        save(path, header, body)           # write after every answer, never batch
        i += 1

    save(path, header, body)
    print("\nall rows judged.")
    report(body)


if __name__ == "__main__":
    main()
