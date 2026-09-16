#!/usr/bin/env python3
"""Per-QUESTION shortcut resistance, and the difficulty tier derived from it.

WHAT THIS IS FOR. `scripts/sampling_solver.py` reports, per FAMILY, how well a
reader that classifies a fraction of the records can do. Averaging over a family
hides the spread: a family whose mean lands in the resistant band still contains
individually trivial questions, and a family whose mean is poor still contains
questions no partial reader can touch. This grades every question on its own.

THE TIER IS THE DISCLOSURE. The benchmark's central limitation is that most of
its questions can be answered from a sample (README 4e). Publishing a measured
per-question resistance grade does not make that smaller. What it buys is an
INSTRUMENT, and it is the one the benchmark was missing:

  easy       answerable from ~5% of the records. Measures whether a model can
             CLASSIFY the records at all.
  very hard  needs near-total coverage. Measures whether a model AGGREGATES
             over the whole document.

The gap between a model's `easy` score and its `very hard` score is an estimate
of how much of the document it actually read. A single aggregate score cannot
separate reading from classifying (W4 finding 3); two bands can. A model at
0.90 easy and 0.30 very-hard is sampling. A model at 0.40 on both cannot read
Turkish, and its long-context result says nothing about long context.

HOW THE GRADE IS COMPUTED. For each question, every reader in
`sampling_solver.READERS` is run at each fraction, and the grade is set from the
**best** score any reader achieves, because a shortcut only has to work once.
The stochastic reader is averaged over `--trials` samples; the three
deterministic readers are run once because repeating them changes nothing.

  very hard   best partial reader scores below 0.35
  hard        0.35 to 0.60
  moderate    0.60 to 0.80
  easy        0.80 and above

WHAT A GRADE DOES NOT MEAN, and this has to be stated wherever grades are:

  * **The grade is relative to THESE readers.** "very hard" means the four
    readers modelled here failed, not that no shortcut exists. A reader with a
    different strategy could crack a question graded very hard.
  * **The readers are handed the true label of every record they read.** They
    are perfect classifiers reading a fraction, so they are UPPER bounds. A real
    model scores lower on the same reading.
  * **The grade is a property of the question AND the metric.** These are
    `relative` scores. Under exact match nearly every numeric question would
    grade very hard, and that is not informative because a full reader fails too.

OUTPUT is a sidecar, `<out_dir>/difficulty.jsonl`, one row per question, plus a
summary in `manifests/difficulty.json`. `questions.jsonl` is NOT modified: the
build is byte-identical against `tests/golden/` and a grading pass must not
perturb that.

Usage:
  python scripts/grade_questions.py                     # every built set
  python scripts/grade_questions.py --trials 200        # tighter grades
  python scripts/grade_questions.py --sets sikayet_tr_out
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from scoring import score                                   # noqa: E402
from sampling_solver import (READERS, STOCHASTIC,           # noqa: E402
                             answer_from_sample, blind_prediction, load_set)

BANDS = [(0.35, "very hard"), (0.60, "hard"), (0.80, "moderate"), (1.01, "easy")]


def band(x: float) -> str:
    for hi, name in BANDS:
        if x < hi:
            return name
    return "easy"


def grade_set(d: Path, fractions: list[float], trials: int, seed: int) -> list[dict]:
    qs, metas = load_set(d)
    out = []
    for q in qs:
        meta = metas.get(q["haystack_id"])
        if meta is None:
            continue
        rows = list(zip(meta["label"].to_list(), meta["entity"].to_list(),
                        meta["half"].to_list()))
        n, k_lab = len(rows), len(set(r[0] for r in rows))
        best, best_by = 0.0, None
        spread = []
        for frac in fractions:
            k = max(1, min(n, int(round(n * frac))))
            for name, fn in READERS.items():
                got = []
                for t in range(trials if name in STOCHASTIC else 1):
                    rng = random.Random(f"{seed}-{q['id']}-{name}-{frac}-{t}")
                    pred = answer_from_sample(q, fn(rows, k, rng), k / n)
                    if pred is not None:
                        got.append(score(q, pred)["relative"])
                if not got:
                    continue
                mean = sum(got) / len(got)
                if name in STOCHASTIC and len(got) > 1:
                    # the standard error of the MEAN, not the spread of single
                    # trials. Individual trials on a small-answer question swing
                    # between 0 and 1 by construction and that spread does not
                    # shrink with more trials; the error on the average does.
                    spread.append(statistics.stdev(got) / (len(got) ** 0.5))
                if mean > best:
                    best, best_by = mean, f"{name}@{frac}"
        b = blind_prediction(q, n, k_lab)
        bl = score(q, b)["relative"] if b is not None else None
        out.append({
            "id": q["id"], "haystack_id": q["haystack_id"],
            "kind": q["kind"], "rare": bool(q.get("rare")),
            "family": "count_rare" if q.get("rare") else q["kind"],
            "tier": q.get("target_tokens") or q.get("target_records"),
            "n_records": n,
            "shortcut_score": round(best, 4),
            "shortcut_reader": best_by,
            "blind_score": None if bl is None else round(bl, 4),
            "grade_se": round(max(spread), 4) if spread else 0.0,
            "difficulty": band(best),
            # True when the grade could flip under resampling: the score is
            # within two standard errors of a band boundary.
            "borderline": any(abs(best - hi) < 2 * (max(spread) if spread else 0.0)
                              for hi, _ in BANDS[:-1]),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", nargs="+", default=None)
    ap.add_argument("--fractions", nargs="+", type=float, default=[0.05])
    ap.add_argument("--trials", type=int, default=64,
                    help="samples averaged for the stochastic reader. The grade is a "
                         "shipped property, so it has to be stable; the reported "
                         "worst-case trial spread says whether it is.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json", default="manifests/difficulty.json")
    args = ap.parse_args()

    sets = args.sets
    if not sets:
        sets = []
        for cfg in sorted((ROOT / "configs").glob("*.json")):
            o = json.loads(cfg.read_text(encoding="utf-8")).get("out_dir")
            if o and (ROOT / o / "questions.jsonl").exists():
                sets.append(o)

    summary, all_rows = {}, []
    for s in sets:
        rows = grade_set(ROOT / s, args.fractions, args.trials, args.seed)
        (ROOT / s / "difficulty.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
            encoding="utf-8")
        c = Counter(r["difficulty"] for r in rows)
        summary[s] = {"n": len(rows), **{g: c[g] for _, g in BANDS},
                      "borderline": sum(1 for r in rows if r["borderline"]),
                      "max_grade_se": round(max((r["grade_se"] for r in rows), default=0.0), 4)}
        all_rows.extend(rows)
        print(f"{s:22} n={len(rows):>4}  " +
              "  ".join(f"{g}={c[g]}" for _, g in BANDS))

    tot = Counter(r["difficulty"] for r in all_rows)
    n = len(all_rows)
    print("\n=== all sets ===")
    for _, g in BANDS:
        print(f"   {g:11} {tot[g]:>5}  ({100*tot[g]/n:4.1f}%)")
    worst = max((r["grade_se"] for r in all_rows), default=0.0)
    nb = sum(1 for r in all_rows if r["borderline"])
    print(f"\ngrade stability: worst standard error {worst:.4f}; "
          f"{nb} of {n} questions ({100*nb/n:.1f}%) sit within two standard errors "
          f"of a band boundary and could flip under resampling.")

    by_tier = defaultdict(Counter)
    for r in all_rows:
        by_tier[r["tier"]][r["difficulty"]] += 1
    print("\nvery-hard share by tier (does the headline subset support a length curve?)")
    for t in sorted(by_tier, key=lambda x: (x is None, x)):
        c = by_tier[t]
        m = sum(c.values())
        print(f"   {str(t):>9}: {c['very hard']:>4} of {m:>4}  ({100*c['very hard']/m:4.1f}%)")

    Path(args.json).write_text(json.dumps(
        {"trials": args.trials, "fractions": args.fractions, "seed": args.seed,
         "bands": {g: f"<{hi}" for hi, g in BANDS},
         "caveat": "Relative to the readers in sampling_solver.READERS, which are "
                   "handed the true label of every record they read. 'very hard' "
                   "means these readers failed, not that no shortcut exists.",
         "totals": dict(tot), "by_set": summary}, indent=2), encoding="utf-8")
    print(f"\nreport -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
