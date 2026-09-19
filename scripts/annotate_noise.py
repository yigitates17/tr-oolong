"""Interactive annotator for the label-noise slice.

Editing 150 rows of Turkish in a spreadsheet invites two failure modes that are
hard to detect afterwards: an encoding change that mangles Turkish characters,
and a mis-scrolled row that shifts every answer by one. This walks the rows one
at a time, writes the answer straight back into the CSV, and is resumable, so
neither can happen and the work can be done in any number of sittings.

  python scripts/annotate_noise.py                                  # the intent slice
  python scripts/annotate_noise.py --csv noise_slices/sikayet_tr.csv
  python scripts/annotate_noise.py --csv noise_slices/sikayet_tr.csv --stats
  python scripts/annotate_noise.py --all-stats                      # every slice, one table

Reads any slice written by make_noise_slice.py. Long records (complaints, news
articles) are wrapped and clipped to --chars so one row stays on one screen;
press `m` to see the full text of the row you are on.

Keys per row:  e = label correct   h = label wrong   s = skip / unsure
               b = back one row    m = show full text   q = save and quit

The question is NOT "is this the best possible label". It is "would a careful
annotator have rejected this label as wrong". Anything defensible counts as
correct -- we are measuring error, not taste.
"""
import argparse
import csv
import math
import sys
import textwrap
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


def show(text: str, width: int, limit: int | None) -> str:
    """Wrap to the terminal and clip, so one record is one screenful. The full
    text stays one keypress away -- clipping silently would change what is being
    judged."""
    t = " ".join(str(text).split())
    clipped = limit is not None and len(t) > limit
    if clipped:
        t = t[:limit] + " ..."
    body = textwrap.fill(t, width=width, initial_indent="  ", subsequent_indent="  ")
    return body + ("\n  [clipped -- press m for the full text]" if clipped else "")


def label_menu(body: list, width: int) -> str:
    """The label space, so the reader can see what the alternatives were. On a
    29-class corpus 'is this label right' is unanswerable without them."""
    labs = sorted({r[4] for r in body if r[4]})
    if len(labs) > 40:
        return ""
    return textwrap.fill("labels: " + ", ".join(labs), width=width,
                         initial_indent="  ", subsequent_indent="          ")


def all_stats() -> None:
    """Every slice at once. Prints the table that goes into DATACARD."""
    paths = sorted((ROOT / "noise_slices").glob("*.csv"))
    legacy = ROOT / "label_noise_massive.csv"
    if legacy.exists():
        paths = [legacy] + paths
    if not paths:
        sys.exit("no slices found -- run: python scripts/make_noise_slice.py --dataset all")
    print(f"{'slice':22}{'judged':>8}{'wrong':>7}{'eps':>8}{'95% CI':>18}")
    print("-" * 63)
    for p in paths:
        _, b = load(p)
        ok, bad, total = stats(b)
        judged = ok + bad
        if judged == 0:
            print(f"{p.stem[:21]:22}{'0':>8}{'-':>7}{'-':>8}{'not started':>18}")
            continue
        eps = bad / judged
        lo, hi = wilson(bad, judged)
        flag = "" if judged == total else f"  ({total-judged} left)"
        print(f"{p.stem[:21]:22}{judged:>8}{bad:>7}{eps:>7.1%}"
              f"{f'[{lo*100:.1f}%, {hi*100:.1f}%]':>18}{flag}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "label_noise_massive.csv"))
    ap.add_argument("--stats", action="store_true", help="report only")
    ap.add_argument("--all-stats", action="store_true",
                    help="epsilon for every slice in noise_slices/, one table")
    ap.add_argument("--chars", type=int, default=700,
                    help="clip each record to this many characters (0 = never clip)")
    ap.add_argument("--width", type=int, default=92)
    a = ap.parse_args()
    if a.all_stats:
        all_stats()
        return
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
        limit = a.chars if a.chars > 0 else None
        print(show(r[2], a.width, limit))
        if r[3].strip():                   # bilingual slices only
            print(f"\n  EN:")
            print(show(r[3], a.width, limit))
        print(f"\n  LABEL >>> {r[4]} <<<")
        menu = label_menu(body, a.width)
        if menu:
            print(menu)
        try:
            k = input("\n  correct? [e]vet  [h]ayır  [s]kip  [b]ack  [m]ore  [q]uit > ").strip().lower()
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
        if k == "m":
            print("\n  FULL TEXT:")
            print(show(r[2], a.width, None))
            if r[3].strip():
                print("\n  FULL TEXT (EN):")
                print(show(r[3], a.width, None))
            continue
        if k == "s":
            i += 1
            continue
        if k not in ("e", "h"):
            print("  -- press e, h, s, b, m or q")
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
