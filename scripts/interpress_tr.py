"""Interpress Turkish news, 17 categories with publication dates -> the label
space the review axis was missing.

WHY THIS SOURCE. The four 3-class review sets are the most partially-readable
part of the benchmark: a reader that classifies a random 5% of the records and
scales up scores 0.88 to 0.91 on their counts. That is arithmetic, not a defect
that question design can fix. The relative error of a scaled-up sample is
`sqrt((1-f)/(f*m))` in the gold magnitude m, and with N records over K classes
the average count is N/K, so resistance needs a LARGE K. Three classes over
several thousand records cannot supply it; see DESIGN_DECISIONS D21b for the two
alternatives that were built and rejected.

Interpress supplies it, and supplies a second thing nothing else on the Hugging
Face Hub did: **real per-record dates**.

  218,839 usable rows (train split), 17 categories, daily publication dates
  from 2010-11-02 to 2017-11-01 (2,457 distinct days, ~84 months).

Category shares run from 8.13% (`ticaret`) to 2.34% (`savunma`), so the label
space is naturally uneven without being degenerate.

WHAT IT BUYS, computed from the real distribution at 3.4 chars/token:

  tier      records   largest class   predicted 5%-sample score
  100K          206              16   0.00
  250K          515              41   0.33
  500K        1,030              83   0.52
  1M          2,060             167   0.66

against 0.88-0.91 at every tier on the current review sets. Note the gradient:
resistance FALLS as documents get longer, which is a real length axis. The
current sets are flat in length under the proportional metric (README 4e), and
this is the first source that is not.

The records are full news articles (median 1,650 characters), which is why a
100K-token document holds ~206 of them rather than ~1,500. Every one of those
206 must still be classified to answer "how many are `saglik`", so the answers
are small without the questions becoming retrieval; that is the D21 argument.
Using `Title` instead was measured and is much worse: 28-character records give
12,000 per document and a 5% score of 0.86.

LICENCE, stated plainly. The upstream dataset card declares **no licence**
("[More Information Needed]"). This is the same position as `amazon_hpc_en`, and
it is handled the same way: **the text is NOT redistributed.** This set ships as
questions, answers and a manifest only, and the text is rebuilt locally by this
script. The Apache-2.0 header in the Hugging Face loading script covers that
SCRIPT, not the data, and must not be cited as the data's licence.

Before this set is included in any release, the licence question should be put
to Interpress directly; see DATASET_REVIEW. Until it is answered this set is
built and measured but flagged, exactly as amazon_hpc_en is.

SOURCE. The Hugging Face repository `yavuzkomecoglu/interpress_news_category_tr`
contains only a loading script, which no current `datasets` version will run.
The script points at the archive below, which is the actual data and is fetched
directly here so the build does not depend on a deprecated loader.
"""
import hashlib
import io
import sys
import zipfile
from pathlib import Path

import polars as pl
import requests

URL = "https://www.interpress.com/downloads/interpress_news_category_tr_270k.zip"
MEMBER = "interpress_news_category_tr_270k_train.tsv"
OUT = Path("datasets/interpress_tr.parquet")
# Recorded rather than pinned: this is a plain HTTP archive with no revision
# history, so the only reproducibility guarantee available is the hash of what
# was actually downloaded. Verify it before trusting a rebuild.
EXPECT_SHA256 = "f41659ed1f38e36759e382eaef2b6bd3680b3a8d49f4d6ef1829d8d0d999e246"

MIN_CHARS = 200         # drop stubs and photo captions
MAX_CHARS = 6000        # drop the long tail so one record cannot dominate a budget


def main() -> int:
    print(f"fetching {URL} ...", flush=True)
    blob = requests.get(URL, timeout=900).content
    digest = hashlib.sha256(blob).hexdigest()
    print(f"sha256 = {digest}")
    if EXPECT_SHA256 and digest != EXPECT_SHA256:
        print(f"[!] archive changed upstream. Expected {EXPECT_SHA256}.", file=sys.stderr)
        return 1

    raw = zipfile.ZipFile(io.BytesIO(blob)).read(MEMBER)
    df = pl.read_csv(io.BytesIO(raw), separator="\t", has_header=True,
                     truncate_ragged_lines=True, infer_schema_length=0, quote_char=None)
    df = (
        df.drop_nulls(["Category", "Content", "PublishDateTime"])
        .select(
            pl.col("Content").str.strip_chars().alias("text"),
            pl.col("Category").str.strip_chars().alias("label"),
            # kept for a future date-scoped family; the builder ignores extra
            # columns, and dates are the one axis no other source here has
            pl.col("PublishDateTime").str.slice(0, 10).alias("date"),
        )
        .filter(pl.col("text").str.len_chars().is_between(MIN_CHARS, MAX_CHARS))
        .unique(subset=["text"], keep="first")
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT)
    print(df["label"].value_counts().sort("count", descending=True))
    print(f"{df.height} rows, {df['label'].n_unique()} categories, "
          f"{df['date'].n_unique()} distinct dates -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
