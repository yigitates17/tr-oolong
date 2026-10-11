"""XNLI, Turkish and English -> a second parallel Turkish/English pair (v0.11).

Only the test and validation splits: they are professional human translations
of the same English sentence pairs, aligned row by row across languages. The
392K-row training split is machine-translated and is not used.

Records are written as "premise -> hypothesis", the format OOLONG uses for its
MultiNLI records, so the task matches OOLONG's. Labels keep the English names
in both languages (as the intent sets keep MASSIVE's English ids).
`pair_id` ties each Turkish record to its English translation.

Licence: CC BY-NC 4.0 (github.com/facebookresearch/XNLI, LICENSE).
"""
import polars as pl
from datasets import load_dataset

# Pinned Hub revision (HEAD on 11 October 2026).
REVISION = "b8dd5d7af51114dbda02c0e3f6133f332186418e"
NAMES = ["entailment", "neutral", "contradiction"]

frames = {}
for lang in ("tr", "en"):
    parts = []
    for split in ("validation", "test"):
        t = pl.from_arrow(load_dataset("facebook/xnli", lang, split=split, revision=REVISION).data.table)
        parts.append(t.with_columns(pl.concat_str([pl.lit(split), pl.int_range(pl.len()).cast(pl.Utf8)], separator="-").alias("pair_id")))
    df = pl.concat(parts).select(
        (pl.col("premise").str.strip_chars() + " -> " + pl.col("hypothesis").str.strip_chars()).alias("text"),
        pl.col("label").cast(pl.Int64).replace_strict(dict(enumerate(NAMES))).alias("label"),
        "pair_id",
    )
    frames[lang] = df
    df.write_parquet(f"datasets/xnli_{lang}.parquet")
    print(lang, df.height, dict(df["label"].value_counts().iter_rows()))
assert frames["tr"]["pair_id"].to_list() == frames["en"]["pair_id"].to_list()
assert frames["tr"]["label"].to_list() == frames["en"]["label"].to_list()
print("Turkish and English rows aligned; labels identical -> datasets/xnli_{tr,en}.parquet")
