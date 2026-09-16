"""BuyukSinema Turkish film reviews, a 10-point reviewer rating -> a REDISTRIBUTABLE
large-K review set.

WHY THIS ONE, GIVEN interpress_tr AND sikayet_tr ALREADY EXIST. Both of those
solve the label-space problem and neither can ship its text: their licences are
unstated upstream, so they ship questions-only with a local rebuild. This source
is **cc-by-sa-4.0**, the same licence as `musteri_tr` and `vitamins_tr`, so its
text is redistributable. It is the only large-K Turkish option found with a
declared licence.

It is also the closest register match to the sets it is meant to strengthen:
film reviews written by the reviewer who assigned the score, so the label is the
author's own rating exactly as on `vitamins_tr` and `musteri_tr`. The difference
is 10 rating points instead of 3 collapsed sentiment classes.

  67,328 reviews, labels 0-9 (a 1-10 star scale, stored zero-indexed),
  text median 201 characters, cc-by-sa-4.0.

The rating distribution is naturally uneven, 2.4% at label 2 up to 24.4% at
label 7, which is what a rating scale looks like and is useful here: uneven
classes put some counts in the rare band without any construction trick.

WHAT IT DOES NOT DO. It has no English twin, so it cannot carry the
cross-lingual claim; `vitamins_tr` <-> `amazon_hpc_en` and `musteri_tr` <->
`marc_en` remain the matched pairs and remain 3-class. This set is added for
aggregation difficulty on the review axis, not for the twin.

LABELS are kept as the rating number rendered as Turkish ("1 yıldız" .. "10
yıldız") rather than as sentiment words, because collapsing a 10-point scale to
3 classes is exactly what makes the existing review sets partially readable
(DESIGN_DECISIONS D21b).
"""
from pathlib import Path

import polars as pl
from datasets import load_dataset

# Pinned Hub revision, as every other fetch script here pins one.
REVISION = "137d0ff7"
OUT = Path("datasets/sinema_tr.parquet")
MIN_CHARS, MAX_CHARS = 80, 3000


def main() -> int:
    ds = load_dataset("turkish-nlp-suite/BuyukSinema", split="train", revision=REVISION)
    df = pl.from_arrow(ds.data.table).select(
        pl.col("text").str.strip_chars().alias("text"),
        # zero-indexed 0..9 -> "1 yıldız".."10 yıldız"
        (pl.col("label").cast(pl.Int64) + 1).cast(pl.Utf8).add(" yıldız").alias("label"),
    )
    df = (
        df.drop_nulls()
        .filter(pl.col("text").str.len_chars().is_between(MIN_CHARS, MAX_CHARS))
        .unique(subset=["text"], keep="first")
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT)
    print(df["label"].value_counts().sort("count", descending=True))
    print(f"{df.height} rows, {df['label'].n_unique()} rating classes -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
