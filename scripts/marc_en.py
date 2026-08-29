"""Multilingual Amazon Reviews Corpus, English -> the twin of musteri_tr.

Chosen over sealuzh/app_reviews on licensing grounds. app_reviews is a closer
length match (14.7 vs 13.8 mean words against MARC's 34.1) but is tagged
license:unknown upstream, which is a declaration of no known grant rather than a
missing field. MARC is Apache-2.0 and its text is redistributable, which matters
for a benchmark meant to be downloaded and cited.

Matched to MusteriYorumlari on the two things that decide comparability: both
labels are the reviewer's own 1-5 star rating mapped by the same rule, and
neither half has an entity column, so both emit the same six families.

MARC ships exactly 40,000 rows per star, so the pool is balanced before we touch
it; the cap below only matches the per-class size to the Turkish half.
"""
import polars as pl
from datasets import load_dataset

STAR_TO_LABEL = {0: "negative", 1: "negative", 2: "neutral", 3: "positive", 4: "positive"}

df = (
    pl.from_arrow(load_dataset("SetFit/amazon_reviews_multi_en", split="train").data.table)
    .select(
        pl.col("text").cast(pl.Utf8).alias("text"),
        pl.col("label").cast(pl.Int64).replace_strict(STAR_TO_LABEL, default=None).alias("label"),
    )
    .drop_nulls()
    .filter(pl.col("text").str.strip_chars().str.len_chars() > 0)
)
cap = df.group_by("label").len()["len"].min()
df = (
    df.with_columns(pl.int_range(pl.len()).shuffle(seed=42).over("label").alias("_r"))
    .filter(pl.col("_r") < cap).drop("_r")
)
df.write_parquet("datasets/marc_en.parquet")
print(df["label"].value_counts())
print(f"{df.height} rows (capped to {cap}/class) -> datasets/marc_en.parquet")
