"""Experiment: the same attacks, on OOLONG itself.

Setup (2026-09-28). No language model. Downloads a few OOLONG-synth test files
(the revision pinned in scripts/oolong_crosscheck.py) and, for every question:

  * records its task group, task, and whether it is narrowed to listed user ids
    or to a month (scope), using the cross-check's own parser;
  * for narrowed questions, the share of records a string search for those
    user ids or that month would have to read (every record prints
    "Date: ... || User: ..."), and whether reading only those records, with
    true labels, gives the gold answer;
  * for "relative frequency" comparisons, how close the two counts are
    (relative margin), since close comparisons were the one question type that
    resisted every shortcut on TR-OOLONG.

Usage: python experiments/oolong_attacks.py [--shards 3 8 16 21 25 30]
"""
import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import oolong_crosscheck as oc                                    # noqa: E402

CACHE = Path("/private/tmp/claude-501/-Users-yigitates-tr-oolong/"
             "8d8e95ca-18c6-4b0b-bdda-a06ffbea2155/scratchpad/oolong")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", nargs="+", type=int, default=[3, 8, 16, 21, 25, 30])
    args = ap.parse_args()
    import pyarrow.parquet as pq

    groups = Counter()
    scoped = defaultdict(list)          # scope -> [(share read, correct?)]
    rel_margins = []
    per_task = Counter()
    ex = []
    for i in args.shards:
        path = oc.fetch_shard(i, CACHE)
        pf = pq.ParquetFile(path)
        for rg in range(pf.num_row_groups):
            for r in pf.read_row_group(rg, columns=oc.NEEDED).to_pylist():
                groups[r["task_group"]] += 1
                per_task[(r["task_group"], r["task"].replace("TASK_TYPE.", ""))] += 1
                recs = oc.parse_records(r["context_window_text_with_labels"])
                if not recs:
                    continue
                pred, scope = oc.scope_of(r["question"])
                g = oc.parse_gold(r["answer"])
                if scope != "global":
                    sub = [x for x in recs if pred(x)]
                    ans = oc.answer(r["task"], r["question"], sub, 1.0)
                    ok = oc.score3(g, ans)
                    scoped[scope].append((len(sub) / len(recs), bool(ok and ok[0] == 1.0),
                                          r["context_len"]))
                    if len(ex) < 2 and ok and ok[0] == 1.0 and r["context_len"] >= 131072:
                        ex.append((r["question"][-300:], g, len(sub), len(recs), r["context_len"]))
                if r["task"] == "TASK_TYPE.RELATIVE_FREQ" and scope == "global":
                    labs = re.findall(r"'([^']+)'", r["question"])
                    c = Counter(x[0] for x in recs)
                    present = [l for l in labs if l in c]
                    if len(present) >= 2:
                        a, b = present[:2]
                        rel_margins.append(abs(c[a] - c[b]) / max(c[a], c[b]))
        print(f"shard {i} done", flush=True)

    print("\nquestion groups in these files:", dict(groups))
    print("tasks:", dict(per_task))
    for sc, v in scoped.items():
        shares = [x[0] for x in v]
        print(f"\n{sc}: {len(v)} questions; search reads median {100*statistics.median(shares):.1f}% "
              f"of records (90th pct {100*sorted(shares)[int(.9*len(shares))]:.1f}%); "
              f"answer exactly right from those records alone: {100*statistics.mean(x[1] for x in v):.0f}%")
    if rel_margins:
        rm = sorted(rel_margins)
        print(f"\nglobal relative-frequency comparisons: {len(rm)}; margin median {rm[len(rm)//2]:.2f}; "
              f"share with margin under 5%: {100*sum(m < .05 for m in rm)/len(rm):.0f}%")
    print("\nexamples:")
    for e in ex:
        print("  ", e)
    json.dump({"groups": dict(groups),
               "scoped": {k: [list(x) for x in v] for k, v in scoped.items()},
               "relative_freq_margins": rel_margins},
              open(ROOT / "experiments" / "oolong_attacks.json", "w"))


if __name__ == "__main__":
    main()
