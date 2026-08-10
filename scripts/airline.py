import polars as pl
from datasets import load_dataset

# Twitter US Airline Sentiment (CrowdFlower, Feb 2015). The EN twin of the
# Turkish brand-review set: 3-class sentiment with an orthogonal entity.
ds = load_dataset("osanseviero/twitter-airline-sentiment", split="train")
df = pl.from_arrow(ds.data.table)

keep = ["text", "airline_sentiment", "airline"]
missing = set(keep) - set(df.columns)
if missing:
    raise ValueError(f"missing expected columns: {missing}, got: {df.columns}")

df.select(keep).write_csv("airline_tweets.csv")
print(f"wrote airline_tweets.csv -> {df.height} rows, {df['airline'].n_unique()} airlines")
