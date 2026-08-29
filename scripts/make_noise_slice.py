"""Generate the label-noise annotation slice for the intent axis.

Only MASSIVE needs this. The four star-derived sets (vitamins_tr, musteri_tr,
marc_en, amazon_hpc_en) carry the writer's own 1-5 star rating, which is a
recorded fact rather than an annotator's estimate of a latent truth, so there is
no annotator to disagree with and classical label noise is ~0 by construction.

Output is UTF-8 with BOM so Excel renders Turkish characters. The reader ticks
the "LABEL CORRECT?" column with e (evet) or h (hayir); the other two columns are
optional context.

  n=150 gives about +/- 4.8 points at eps~10%, +/- 3.5 points at eps~5%.

Usage:
  python scripts/make_noise_slice.py [--n 150] [--seed 42] [--out label_noise_massive.csv]
"""
import argparse
import csv
import math

import polars as pl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="label_noise_massive.csv")
    a = ap.parse_args()

    tr = pl.read_parquet("datasets/massive_tr.parquet")
    en = pl.read_parquet("datasets/massive_en.parquet")
    # join on pair_id so the reader sees both renderings of the same utterance;
    # the English side often disambiguates an intent the Turkish alone does not
    rows = tr.join(en, on="pair_id", suffix="_en").sample(a.n, seed=a.seed, shuffle=True)

    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["#", "pair_id", "Turkish utterance", "English utterance",
                    "dataset label", "LABEL CORRECT? (e/h)",
                    "if wrong, what should it be?", "notes"])
        for i, r in enumerate(rows.to_dicts(), 1):
            w.writerow([i, r["pair_id"], r["utt"], r["utt_en"], r["intent"], "", "", ""])

    half = 1.96 * math.sqrt(0.1 * 0.9 / a.n) * 100
    print(f"wrote {a.out}: {a.n} rows (seed {a.seed})")
    print(f"  precision at eps~10%: +/- {half:.1f} points")
    print("  NOTE: *.csv is git-ignored, so the filled sheet lives outside the repo.")
    print("  Record the resulting eps in DATACARD.md under the intent axis.")


if __name__ == "__main__":
    main()
