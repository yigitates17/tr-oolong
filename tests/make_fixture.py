"""Generate the deterministic fixture dataset for the golden test. Run once;
the resulting CSV is committed so the fixture never drifts."""

import random
from pathlib import Path

import polars as pl

rng = random.Random(0)
LABELS = ["positive", "negative", "neutral"]
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
out = Path(__file__).resolve().parent / "fixture_source.csv"
pl.DataFrame(rows).write_csv(out)
print(f"wrote {out} ({len(rows)} rows)")