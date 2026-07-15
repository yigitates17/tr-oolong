import polars as pl
from datasets import load_dataset

PER_CLASS_CAP = 20000
RATING_TO_LABEL = {1: "negative", 2: "negative", 3: "neutral", 4: "positive", 5: "positive"}
CAT = "Health_and_Personal_Care"

# 1) build parent_asin -> brand(store) map from the metadata shard (streamed)
meta = load_dataset("McAuley-Lab/Amazon-Reviews-2023", f"raw_meta_{CAT}",
                    split="full", streaming=True, trust_remote_code=True)
brand = {}
for m in meta:
    store = (m.get("store") or "").strip()
    if store and m.get("parent_asin"):
        brand[m["parent_asin"]] = store
print(f"{len(brand)} products with a brand")

# 2) stream reviews, attach brand, map rating, keep balanced classes
caps = {v: PER_CLASS_CAP for v in set(RATING_TO_LABEL.values())}
rows = []
reviews = load_dataset("McAuley-Lab/Amazon-Reviews-2023", f"raw_review_{CAT}",
                       split="full", streaming=True, trust_remote_code=True)
for r in reviews:
    pa = r.get("parent_asin")
    text = (r.get("text") or "").strip()
    label = RATING_TO_LABEL.get(int(r["rating"])) if r.get("rating") else None
    if not (pa in brand and text and label and caps[label] > 0):
        continue
    rows.append({"text": text, "label": label, "entity": brand[pa]})
    caps[label] -= 1
    if all(c == 0 for c in caps.values()):
        break

df = pl.DataFrame(rows)
df.write_parquet("amazon_hpc_en.parquet")
print(df["label"].value_counts())
print(f"{df.height} rows, {df['entity'].n_unique()} brands -> amazon_hpc_en.parquet")