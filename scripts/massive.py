"""Fetch the MASSIVE intent axis as a parallel tr-TR / en-US pair.

The two locales are the SAME utterances, professionally translated, so any row
dropped in one locale must be dropped in the other or the twin stops being a
controlled comparison. The label-leakage filter is therefore applied as a UNION
over both locales: an utterance pair is dropped if the label surface form leaks
in either language. Per-locale filtering here would bias the twin toward
whichever language leaks less (English leaks; Turkish does not).
"""

import sys
from pathlib import Path

import polars as pl
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from build_tr_oolong import Config, clean, label_leak_mask  # canonical definitions

LOCALES = {"tr-TR": ("tr", "massive_tr.parquet"), "en-US": ("en", "massive_en.parquet")}
CONFIG_FOR = {"tr-TR": "tr_intent.json", "en-US": "en_intent.json"}

frames = {}
for locale, (lang, out) in LOCALES.items():
    ds = load_dataset("AmazonScience/massive", locale)
    intent_names = ds["train"].features["intent"].names
    scenario_names = ds["train"].features["scenario"].names
    df = pl.concat([pl.from_arrow(ds[s].data.table) for s in ds])
    frames[locale] = df.select(
        # (partition, id) is the join key that pairs an utterance across locales
        pl.concat_str([pl.col("partition"), pl.col("id")], separator=":").alias("pair_id"),
        pl.col("utt"),
        pl.col("intent").map_elements(lambda i: intent_names[i], return_dtype=pl.Utf8).alias("intent"),
        pl.col("scenario").map_elements(lambda i: scenario_names[i], return_dtype=pl.Utf8).alias("scenario"),
    )

MIN_CLASS_SUPPORT = 100   # see DATACARD: below this a class is always the rarest

leaking_pairs: set[str] = set()
for locale, (lang, _) in LOCALES.items():
    df = frames[locale]
    mask = label_leak_mask(df["utt"].to_list(), sorted(set(df["intent"].to_list())), lang)
    hit = df.filter(pl.Series(mask))["pair_id"].to_list()
    print(f"{locale}: {len(hit)} leaking utterances ({100 * len(hit) / df.height:.2f}%)")
    leaking_pairs.update(hit)
print(f"union dropped from both locales: {len(leaking_pairs)} pairs")

frames = {loc: df.filter(~pl.col("pair_id").is_in(list(leaking_pairs)))
          for loc, df in frames.items()}

# Exact row-level parallelism. The builder's cleaning (word bounds, near-dup
# collapse) is language-local and removes different utterances in each locale --
# before this intersection the twin differed by ~600 rows (15,250 tr vs 15,765
# en), so "the same utterances in both languages" was only approximately true.
# We run the real builder cleaner with the real configs, then keep the
# intersection, so both locales end up with an identical set of pair_ids.
survivors: set[str] | None = None
for locale, (lang, _) in LOCALES.items():
    cfg = Config.load(str(ROOT / "configs" / CONFIG_FOR[locale]))
    staged = frames[locale].select(
        pl.col("utt").alias("text"), pl.col("intent").alias("label"),
        pl.col("scenario").alias("entity"), pl.col("pair_id"),
    )
    ids = set(clean(staged, cfg)["pair_id"].to_list())
    print(f"{locale}: {len(ids)} of {frames[locale].height} rows survive cleaning")
    survivors = ids if survivors is None else (survivors & ids)
print(f"intersection kept in both locales: {len(survivors)}")
frames = {loc: df.filter(pl.col("pair_id").is_in(list(survivors)))
          for loc, df in frames.items()}

# Class support is a pair-level decision for the same reason leakage is: cutting
# per locale would leave the twin with different label spaces, and a
# cross-lingual comparison over different label spaces is not controlled. A
# class is dropped from BOTH locales if it is under-supported in EITHER.
low: set[str] = set()
for locale, df in frames.items():
    vc = df["intent"].value_counts()
    low.update(vc.filter(pl.col("count") < MIN_CLASS_SUPPORT)["intent"].to_list())
print(f"classes below support {MIN_CLASS_SUPPORT} in either locale: {len(low)} -> {sorted(low)}")

for locale, (lang, out) in LOCALES.items():
    df = frames[locale].filter(~pl.col("intent").is_in(list(low)))
    df.write_parquet(out)
    print(f"{locale}: {df.height} rows, {df['intent'].n_unique()} intents -> {out}")
