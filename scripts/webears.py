import polars as pl
from datasets import load_dataset

ds = load_dataset("We-Bears/Turkish-Review-Sentiment-Data")
df = pl.from_arrow(ds["train"].data.table)

rename_map = {"Comments": "review", "Companies": "sirket", "Sentiment": "sentiment"}
df = df.rename({k: v for k, v in rename_map.items() if k in df.columns})

missing = {"review", "sentiment", "sirket"} - set(df.columns)
if missing:
    raise ValueError(f"missing expected columns after rename: {missing}, got: {df.columns}")

df.select("review", "sentiment", "sirket").write_csv("turkish_review_sentiment.csv")
print(f"wrote turkish_review_sentiment.csv -> {df.height} rows")