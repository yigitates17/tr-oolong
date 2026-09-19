"""Generate a label-noise annotation slice for ANY source dataset.

WHY THIS IS NOT ONLY FOR MASSIVE ANY MORE. The original version covered the
intent axis alone, on the argument that the star-derived sets carry the writer's
own rating and so have no annotator to disagree with. That argument still holds
for the five `author_stars` sets. It does NOT cover the two v0.7.0 sets that
supply most of the hard questions:

  sikayet_tr     the category is chosen by the COMPLAINANT when filing
  interpress_tr  the label is the publisher's own editorial desk

Neither is an annotator's judgement, so neither can be "wrong" in the usual
sense. What a slice measures for them is narrower and still worth having: how
often a Turkish reader, given only the text, would put it in the category the
corpus did. That is label PREDICTABILITY, and it is the thing that bounds what
any model can score. See DATACARD, "The ceiling is already measured".

OUTPUT FORMAT is uniform across datasets so `scripts/annotate_noise.py` reads
any of them without a flag:

  0 #   1 row_id   2 text   3 text_en (blank when monolingual)   4 label
  5 LABEL CORRECT? (e/h)    6 if wrong, what should it be?       7 notes

UTF-8 with BOM so Excel renders Turkish characters if anyone opens it there.

  n=150 gives about +/- 4.8 points at eps~10%, +/- 3.5 points at eps~5%.

Usage:
  python scripts/make_noise_slice.py --dataset massive          # bilingual, the original
  python scripts/make_noise_slice.py --dataset sikayet_tr
  python scripts/make_noise_slice.py --dataset all --n 150
"""
import argparse
import csv
import math
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "noise_slices"

# Every source that has a parquet under datasets/. `massive` is handled
# separately because it is the one bilingual case.
MONO = ["sikayet_tr", "interpress_tr", "sinema_tr", "vitamins_tr",
        "musteri_tr", "marc_en", "amazon_hpc_en"]
ALL = ["massive"] + MONO

HEADER = ["#", "row_id", "text", "text_en", "dataset label",
          "LABEL CORRECT? (e/h)", "if wrong, what should it be?", "notes"]


def write(path: Path, rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


def slice_massive(n: int, seed: int) -> list[list]:
    tr = pl.read_parquet(ROOT / "datasets/massive_tr.parquet")
    en = pl.read_parquet(ROOT / "datasets/massive_en.parquet")
    # join on pair_id so the reader sees both renderings of the same utterance;
    # the English side often disambiguates an intent the Turkish alone does not
    rows = tr.join(en, on="pair_id", suffix="_en").sample(n, seed=seed, shuffle=True)
    return [[i, r["pair_id"], r["utt"], r["utt_en"], r["intent"], "", "", ""]
            for i, r in enumerate(rows.to_dicts(), 1)]


def slice_mono(name: str, n: int, seed: int) -> list[list]:
    df = pl.read_parquet(ROOT / f"datasets/{name}.parquet")
    rows = df.sample(min(n, df.height), seed=seed, shuffle=True)
    return [[i, i, r["text"], "", r["label"], "", "", ""]
            for i, r in enumerate(rows.to_dicts(), 1)]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default="massive",
                    help=f"one of: all, {', '.join(ALL)}")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None, help="override the output path")
    a = ap.parse_args()

    names = ALL if a.dataset == "all" else [a.dataset]
    for name in names:
        if name not in ALL:
            raise SystemExit(f"unknown dataset {name!r}; choose from: all, {', '.join(ALL)}")
        rows = slice_massive(a.n, a.seed) if name == "massive" else slice_mono(name, a.n, a.seed)
        out = Path(a.out) if a.out else OUT_DIR / f"{name}.csv"
        if out.exists():
            print(f"[skip] {out} exists -- delete it first if you mean to resample, "
                  f"otherwise you would discard the answers already in it")
            continue
        write(out, rows)
        labs = sorted({r[4] for r in rows})
        print(f"wrote {out}: {len(rows)} rows, {len(labs)} distinct labels (seed {a.seed})")

    half = 1.96 * math.sqrt(0.1 * 0.9 / a.n) * 100
    print(f"\nprecision at eps~10%: +/- {half:.1f} points on n={a.n}")
    print("annotate with:  python scripts/annotate_noise.py --csv noise_slices/<name>.csv")
    print("NOTE: *.csv is git-ignored, so filled sheets stay out of the repo.")


if __name__ == "__main__":
    main()
