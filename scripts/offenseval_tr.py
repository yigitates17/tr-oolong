"""OffensEval 2020 Turkish (Coltekin, LREC 2020) -> offensive / not offensive
tweets (v0.11 candidate).

Training and test tweets with their sub-task A label (OFF or NOT). User
mentions are already replaced by @USER upstream. The English OffensEval 2019
data (OLID) uses the same annotation guidelines.

Licence: annotations CC-BY (coltekin.github.io/offensive-turkish). The zip is
pinned by its SHA-256 so a rebuild reads the same bytes.
"""
import csv
import hashlib
import io
import urllib.request
import zipfile

import polars as pl

URL = "https://coltekin.github.io/offensive-turkish/offenseval2020-turkish.zip"
SHA256 = "7977e96255dbc9b8d14893f1b14cbe3dec53c70358503c062c5a59720ec9c2f2"
ROOT = "offenseval2020-turkish/"

raw = urllib.request.urlopen(URL).read()
assert hashlib.sha256(raw).hexdigest() == SHA256, "upstream zip changed"
z = zipfile.ZipFile(io.BytesIO(raw))
read = lambda p: list(csv.reader(io.TextIOWrapper(z.open(ROOT + p), encoding="utf-8"),
                                 delimiter="\t", quoting=csv.QUOTE_NONE))
train = read("offenseval-tr-training-v1/offenseval-tr-training-v1.tsv")[1:]
test = read("offenseval-tr-testset-v1/offenseval-tr-testset-v1.tsv")[1:]
gold = dict(line.decode("utf-8").strip().split(",") for line in
            z.open(ROOT + "offenseval-tr-testset-v1/offenseval-tr-labela-v1.tsv") if line.strip())
rows = [(r[0], r[1], r[2], "train") for r in train if len(r) >= 3]
rows += [(r[0], r[1], gold[r[0]], "test") for r in test if len(r) >= 2 and r[0] in gold]
df = pl.DataFrame(rows, schema=["id", "text", "label", "split"], orient="row")
df.write_parquet("datasets/offenseval_tr.parquet")
print(df.height, dict(df["label"].value_counts().iter_rows()), "-> datasets/offenseval_tr.parquet")
