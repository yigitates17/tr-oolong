import polars as pl
from datasets import load_dataset

PER_CLASS_CAP = 20000  # rows kept per sentiment class; lower = more balanced, smaller

# match these EXACTLY to the label strings already in your existing Turkish review set
STAR_TO_LABEL = {1: "olumsuz", 2: "olumsuz", 3: "notr", 4: "olumlu", 5: "olumlu"}

ds = load_dataset("turkish-nlp-suite/vitamins-supplements-reviews", split="train")
df = (
    pl.from_arrow(ds.data.table)
    .select(
        pl.col("text").alias("text"),
        pl.col("star").cast(pl.Int64).replace_strict(STAR_TO_LABEL, default=None).alias("label"),
        pl.col("brand").cast(pl.Utf8).alias("entity"),
    )
    .drop_nulls()
    .filter(pl.col("text").str.strip_chars().str.len_chars() > 0)
)
# stratify: cap each sentiment class so the pool isn't dominated by 5-star reviews
df = (
    df.with_columns(pl.int_range(pl.len()).shuffle(seed=42).over("label").alias("_r"))
    .filter(pl.col("_r") < PER_CLASS_CAP)
    .drop("_r")
)
df.write_parquet("vitamins_tr.parquet")
print(df["label"].value_counts())
print(f"{df.height} rows, {df['entity'].n_unique()} brands -> vitamins_tr.parquet")