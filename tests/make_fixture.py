"""Generate the deterministic fixture dataset for the golden test. Run once;
the resulting CSV is committed so the fixture never drifts."""

import random
from pathlib import Path

import polars as pl

rng = random.Random(0)
LABELS = ["positive", "negative", "neutral"]
# v0.7.0: a few deliberately RARE labels, so the fixture exercises the
# rare-label count family. Without them the fixture has three roughly equal
# classes, no label ever falls in the [rare_min, rare_max] band, and the golden
# test covers none of the count_rare code path.
RARE = {"mixed": 24, "spam": 13, "off_topic": 7}
BRANDS = ["marka_a", "marka_b", "marka_c", "marka_d", "marka_e"]
WORDS = ("urun kargo hizli teslimat kalite fiyat ambalaj musteri hizmet iade "
         "beklenti memnun paket siparis magaza indirim yorum tavsiye deneyim garanti").split()

rows = [
    {
        "review": " ".join(rng.choices(WORDS, k=rng.randint(8, 20))) + f" no{i}",
        "sentiment": rng.choice(LABELS),
        "sirket": rng.choice(BRANDS),
    }
    for i in range(800)
]
# overwrite a fixed prefix of rows with the rare labels, so their counts are
# exact and the band is hit deterministically
at = 0
for lab, n in RARE.items():
    for _ in range(n):
        rows[at]["sentiment"] = lab
        at += 1
out = Path(__file__).resolve().parent / "fixture_source.csv"
pl.DataFrame(rows).write_csv(out)
print(f"wrote {out} ({len(rows)} rows)")