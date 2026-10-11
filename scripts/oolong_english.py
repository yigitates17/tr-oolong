"""OOLONG-synth's screened English source data -> English sets directly
comparable with OOLONG (v0.11).

OOLONG publishes, for each of its 10 source datasets, the records left after
its two-model screening (`validated_data/*.jsonl`), with the screening output.
Using these files unchanged makes the English side's records identical to
OOLONG's. Each source keeps its own upstream licence; the OOLONG repository is
MIT.
"""
import io
import json
import urllib.request

import polars as pl

# Pinned commit of github.com/abertsch72/oolong (HEAD on 11 October 2026).
COMMIT = "0bb7eabe839218fee7fe8d007f41cfc2fd3ae24c"
URL = ("https://raw.githubusercontent.com/abertsch72/oolong/" + COMMIT
       + "/src/data_gen/oolong-synth/validated_data/{}_validated.jsonl")
NAMES = ["agnews", "app_reviews", "formality", "imdb", "metaphors",
         "multinli", "negation", "spam", "trec_coarse", "yahoo"]

for name in NAMES:
    raw = urllib.request.urlopen(URL.format(name)).read()
    rows = [json.loads(line) for line in io.BytesIO(raw)]
    df = pl.DataFrame({
        "text": [r["input"] for r in rows],
        "label": [str(r["label"]).strip() for r in rows],
        "screen_output": [json.dumps(r.get("model_output"), ensure_ascii=False) for r in rows],
    })
    df.write_parquet(f"datasets/oolong_{name}.parquet")
    print(f"{name:12} {df.height:7} {dict(df['label'].value_counts().sort('count', descending=True).iter_rows())}")
