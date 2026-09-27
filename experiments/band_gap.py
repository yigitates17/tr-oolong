"""Experiment: does the easy/very-hard score gap tell a skimmer from a full reader?

Setup (2026-09-27). No model is involved; every reader is a short program, run
on every shipped question and averaged per difficulty band.
  skim5     reads a random 5% of records, knows their true labels, scales up
            (the grader's own `random` reader)
  guess5    skim5, but answers ~12 records when it sees 0-1 matches
            (see experiments/small_guess.py)
  full@a    reads EVERY record, labels each correctly with probability a, and
            otherwise picks a uniformly random other label (the error model in
            sampling_solver.noisy_labels)
24 random repetitions per question and reader. Both metrics are reported:
`relative` (used by the grades) and `partial` (OOLONG's 0.75**error).

Usage: python experiments/band_gap.py     (about 3 minutes)
"""
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "experiments"))
from scoring import score                                                   # noqa: E402
from sampling_solver import load_set, answer_from_sample, read_random, noisy_labels  # noqa: E402
from small_guess import SETS, NUMERIC, guess_answer                         # noqa: E402

REPS = 24
ACCS = (0.99, 0.95, 0.9, 0.8)
READERS = ["skim5", "guess5"] + [f"full@{a}" for a in ACCS]
BANDS = ["very hard", "hard", "moderate", "easy"]


def main():
    res = defaultdict(lambda: defaultdict(list))
    for s in SETS:
        d = ROOT / f"{s}_out"
        qs, metas = load_set(d)
        grades = {r["uid"]: r for r in map(json.loads, open(d / "difficulty.jsonl"))}
        for q in qs:
            grp = "numeric" if q["kind"] in NUMERIC else "categorical"
            m = metas[q["haystack_id"]]
            rows = list(zip(m["label"].to_list(), m["entity"].to_list(), m["half"].to_list()))
            n = len(rows)
            k = max(1, round(n * 0.05))
            space = sorted({r[0] for r in rows})
            preds = defaultdict(list)
            for t in range(REPS):
                rng = random.Random(f"gap-{q['uid']}-{t}")
                smp = read_random(rows, k, rng)
                preds["skim5"].append(answer_from_sample(q, smp, k / n))
                preds["guess5"].append(guess_answer(q, smp, k, n, 12) if grp == "numeric"
                                       else answer_from_sample(q, smp, k / n))
                for a in ACCS:
                    nl = noisy_labels([r[0] for r in rows], a, space, rng)
                    preds[f"full@{a}"].append(answer_from_sample(
                        q, [(nl[i], rows[i][1], rows[i][2]) for i in range(n)], 1.0))
            key = (grades[q["uid"]]["difficulty"], grp)
            for name, ps in preds.items():
                sc = [score(q, p) if p is not None else {"relative": 0.0, "partial": 0.0}
                      for p in ps]
                res[key][name].append((statistics.mean(x["relative"] for x in sc),
                                       statistics.mean(x["partial"] for x in sc)))

    out = {}
    for metric, i in (("relative", 0), ("partial", 1)):
        print(f"\n=== {metric} ===")
        print(f"{'band':24}{'n':>5}" + "".join(f"{r:>11}" for r in READERS))
        for key in sorted(res, key=lambda kk: (BANDS.index(kk[0]), kk[1])):
            vals = {r: round(statistics.mean(v[i] for v in res[key][r]), 3) for r in READERS}
            out[f"{metric}/{key[0]}/{key[1]}"] = {"n": len(res[key]["skim5"]), **vals}
            print(f"{key[0] + ' / ' + key[1]:24}{len(res[key]['skim5']):>5}"
                  + "".join(f"{vals[r]:>11.3f}" for r in READERS))
    (ROOT / "experiments" / "band_gap.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
