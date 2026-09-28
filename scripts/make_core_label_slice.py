"""Label-check slice for the categories that core questions compare (v0.9.0).

Core questions ("which are there more of, A or B?") compare two categories whose
counts are close, so wrongly labelled records in those two categories can decide
the answer. This draws records from exactly those categories, in the Turkish
datasets, so a native speaker can say how often the dataset's label is wrong.
The intent labels were already checked (150 records, 2.7% to 9.3% wrong).

Output: noise_slices/core_labels_tr.csv, in the same format as
make_noise_slice.py, so scripts/annotate_noise.py reads it unchanged:

  python scripts/make_core_label_slice.py                 # 40 records per dataset
  python scripts/annotate_noise.py --csv noise_slices/core_labels_tr.csv
  python scripts/annotate_noise.py --csv noise_slices/core_labels_tr.csv --stats

The file is git-ignored (it contains source text, including from the two
datasets whose text may not be redistributed).
"""
import argparse
import csv
import json
import random
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
SETS = ["sikayet_tr", "interpress_tr", "sinema_tr", "musteri_tr", "vitamins_tr"]
HEADER = ["#", "row_id", "text", "text_en", "dataset label",
          "LABEL CORRECT? (e/h)", "if wrong, what should it be?", "notes"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-set", type=int, default=40)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(ROOT / "noise_slices" / "core_labels_tr.csv"))
    args = ap.parse_args()
    rng = random.Random(args.seed)
    rows = []
    for s in SETS:
        d = ROOT / f"{s}_out"
        core = [json.loads(l) for l in open(d / "questions.jsonl", encoding="utf-8")
                if '"close_comparison"' in l]
        pool = {}
        for q in core:
            m = pl.read_parquet(d / f"meta_{q['haystack_id']}.parquet")
            for rid, t, lab in zip(m["row_id"].to_list(), m["text"].to_list(), m["label"].to_list()):
                if lab in (q["label_a"], q["label_b"]):
                    pool[(s, rid)] = (t, lab)
        keys = sorted(pool)
        pick = rng.sample(keys, min(args.per_set, len(keys)))
        for k in pick:
            t, lab = pool[k]
            rows.append([k[0], k[1], t, "", lab])
        print(f"{s:15} {len(core):>4} core questions, {len(keys):>6} records in compared "
              f"categories, {len(pick)} drawn")
    rng.shuffle(rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for i, (s, rid, t, en, lab) in enumerate(rows):
            w.writerow([i, f"{s}:{rid}", t, en, lab, "", "", ""])
    print(f"{len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
