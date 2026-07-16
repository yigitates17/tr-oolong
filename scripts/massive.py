import polars as pl
from datasets import load_dataset

for locale, out in [("tr-TR", "massive_tr.parquet"), ("en-US", "massive_en.parquet")]:
    ds = load_dataset("AmazonScience/massive", locale)
    intent_names = ds["train"].features["intent"].names
    scenario_names = ds["train"].features["scenario"].names
    df = pl.concat([pl.from_arrow(ds[s].data.table) for s in ds])
    df = df.select(
        pl.col("utt"),
        pl.col("intent").map_elements(lambda i: intent_names[i], return_dtype=pl.Utf8).alias("intent"),
        pl.col("scenario").map_elements(lambda i: scenario_names[i], return_dtype=pl.Utf8).alias("scenario"),
    )
    df.write_parquet(out)
    print(f"{locale}: {df.height} rows -> {out}")