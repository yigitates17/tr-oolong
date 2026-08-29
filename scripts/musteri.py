"""MusteriYorumlari (Hepsiburada + Trendyol product reviews) -> the review axis.

Labels are the customer's own 1-5 star rating, mapped by the same fixed rule
scripts/vitamins.py uses, so label provenance is the reviewer rather than an
annotator or a model. CC-BY-SA-4.0, so the text is distributable; anything
derived from this subset stays CC-BY-SA-4.0.

No product or brand column exists upstream, so this set carries no entity axis
and the four entity-relational families are omitted by construction. Its twin
(scripts/marc_en.py) is restricted to the same six families to stay parallel.
"""
import polars as pl
from datasets import load_dataset

# source labels are 0-4 (zero-indexed stars) over the card's 1-5 scale
STAR_TO_LABEL = {0: "olumsuz", 1: "olumsuz", 2: "nötr", 3: "olumlu", 4: "olumlu"}

df = (
    pl.from_arrow(load_dataset("turkish-nlp-suite/MusteriYorumlari", split="train").data.table)
    .select(
        pl.col("text").cast(pl.Utf8).alias("text"),
        pl.col("label").cast(pl.Int64).replace_strict(STAR_TO_LABEL, default=None).alias("label"),
    )
    .drop_nulls()
    .filter(pl.col("text").str.strip_chars().str.len_chars() > 0)
)
# balance to the smallest class: a flat pool removes the corpus prior outright
cap = df.group_by("label").len()["len"].min()
df = (
    df.with_columns(pl.int_range(pl.len()).shuffle(seed=42).over("label").alias("_r"))
    .filter(pl.col("_r") < cap).drop("_r")
)
df.write_parquet("datasets/musteri_tr.parquet")
print(df["label"].value_counts())
print(f"{df.height} rows (capped to {cap}/class) -> datasets/musteri_tr.parquet")
