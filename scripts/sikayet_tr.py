"""TC32 Turkish consumer complaints, 32 categories -> the review-axis label space.

WHY. The four 3-class review sets are the most partially-readable part of the
benchmark: a reader classifying a random 5% and scaling up scores 0.88 to 0.91
on their counts. That is arithmetic (DESIGN_DECISIONS D21b): resistance needs the
average count `N/K` below roughly 60, so it needs a LARGE K. This source is the
only Turkish corpus found with K in that range AND consumer-review register, so
unlike `interpress_tr` (news) it is a direct replacement for what the review
axis is missing.

SOURCE AND HOW TO GET IT. Kaggle, `savasy/multiclass-classification-data-for-
turkish-tc32`, file `ticaret-yorum.csv`. Kaggle requires an account, so this
script does NOT download: pass the path to the file you downloaded.

    python scripts/sikayet_tr.py ~/Downloads/ticaret-yorum.csv

431,306 rows, 32 categories, 12,024 to 14,009 rows each, so the corpus is
already near-balanced before anything here touches it.

THE FILE'S STRUCTURE IS NOT WHAT THE HEADER SAYS, and a native reader spotted it
before the code did. The header is `category,text`, but `text` is really
**"<TITLE>,<BODY>"**: a complaint headline joined to the complaint narrative by a
comma. 100% of rows split on the first comma. Title median 39 chars, body median
315. The title is the part that names the company ("Teknosa Cep Telefonu
Değişimi"), and it is kept OUT of the record text for the leakage reason below.

TWO ARTIFACTS THAT WOULD HAVE SHIPPED UNNOTICED:

1. **89.7% of bodies end in "Devamını oku"** ("read more"), a scraping
   truncation marker. The 10.3% without it are systematically the shorter
   complaints. Left in, that is a surface feature correlated with length and
   therefore possibly with category, which is what `scripts/style_solver.py`
   exists to catch. Stripped here.

2. **Category-name leakage, measured per class, and it is severe for a few.**
   The fraction of a class's records containing a word from its own category
   name, body only: `kargo-nakliyat` 84.7%, `cep-telefon-kategori` 73.4%,
   `anne-bebek` 36.9%, every other class at or under 30%, mean 10.8%. A regex
   for "kargo" finds five of six cargo complaints. **Those three classes are
   dropped**, leaving 29, which is still comfortably above the K of roughly 25
   the resistance arithmetic asks for.

   The residual is handled by the builder's own filter, but only because that
   filter was hardened for this source: `leak_surface_forms` previously matched
   the whole label string only, and no Turkish complaint contains the literal
   string "kargo-nakliyat", so it would have reported zero leakage and passed by
   construction. The config sets `leak_label_words: true` so component words are
   matched too. Never ship this source with that flag off.

LABELS are rewritten from slugs into natural Turkish, both because the question
templates put them in front of a Turkish reader (D12) and because the word-level
leak filter needs real words to match.

LICENCE: not stated by the uploader, and the text is scraped from a Turkish
consumer-complaints site. Same position as `amazon_hpc_en` and `interpress_tr`,
handled the same way: **the text is NOT redistributed**, the set ships as
questions and answers, and this script rebuilds it locally from a file the user
obtained themselves. Resolve the licence before any release that includes it.
"""
import sys
from pathlib import Path

import polars as pl

OUT = Path("datasets/sikayet_tr.parquet")

# Body-only leakage above 30%: a substring solver finds these classes reliably.
DROP_CLASSES = {"kargo-nakliyat", "cep-telefon-kategori", "anne-bebek"}

# slug -> the Turkish a question should show. Kept close to the slug so the
# word-level leak filter still matches what a solver would grep for.
LABELS = {
    "alisveris": "alışveriş", "beyaz-esya": "beyaz eşya", "bilgisayar": "bilgisayar",
    "egitim": "eğitim", "elektronik": "elektronik", "emlak-ve-insaat": "emlak ve inşaat",
    "enerji": "enerji", "etkinlik-ve-organizasyon": "etkinlik ve organizasyon",
    "finans": "finans", "gida": "gıda", "giyim": "giyim",
    "hizmet-sektoru": "hizmet sektörü", "icecek": "içecek", "internet": "internet",
    "kamu-hizmetleri": "kamu hizmetleri",
    "kisisel-bakim-ve-kozmetik": "kişisel bakım ve kozmetik",
    "kucuk-ev-aletleri": "küçük ev aletleri", "medya": "medya",
    "mekan-ve-eglence": "mekan ve eğlence", "mobilya-ev-tekstili": "mobilya ve ev tekstili",
    "mucevher-saat-gozluk": "mücevher saat gözlük", "mutfak-arac-gerec": "mutfak araç gereç",
    "otomotiv": "otomotiv", "saglik": "sağlık", "sigortacilik": "sigortacılık",
    "spor": "spor", "temizlik": "temizlik", "turizm": "turizm", "ulasim": "ulaşım",
}
TRUNC = "Devamını oku"
MIN_CHARS, MAX_CHARS = 120, 4000


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.split("SOURCE AND HOW TO GET IT.")[1].split("431,306")[0].strip())
        return 2
    src = Path(sys.argv[1]).expanduser()
    df = pl.read_csv(src, infer_schema_length=0)
    n0 = df.height

    # split the real structure: text == "<title>,<body>"
    df = df.with_columns(
        pl.col("text").str.splitn(",", 2).struct.rename_fields(["title", "body"]).alias("parts")
    ).unnest("parts")

    df = (
        df.filter(pl.col("category").is_in(list(LABELS)))
        .with_columns(
            # the body only: the title names the company and carries the
            # heaviest share of the category-name leakage
            pl.col("body").str.strip_chars().str.strip_chars('"').alias("text"),
            pl.col("category").replace_strict(LABELS, default=None).alias("label"),
        )
        .with_columns(
            pl.when(pl.col("text").str.ends_with(TRUNC))
            .then(pl.col("text").str.slice(0, pl.col("text").str.len_chars() - len(TRUNC)))
            .otherwise(pl.col("text")).str.strip_chars().str.strip_chars(".").alias("text")
        )
        .select("text", "label")
        .drop_nulls()
        .filter(pl.col("text").str.len_chars().is_between(MIN_CHARS, MAX_CHARS))
        .unique(subset=["text"], keep="first")
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT)
    print(f"{n0} rows in, {len(DROP_CLASSES)} leaky classes dropped")
    print(df["label"].value_counts().sort("count", descending=True).head(6))
    print(f"{df.height} rows, {df['label'].n_unique()} categories -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
