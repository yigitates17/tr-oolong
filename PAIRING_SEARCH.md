# Exhaustive pairing search — 2026-08-25

Branch `pairing-search`. **Not merged.** Answers "is there a better twin?" by
measuring rather than by reading dataset cards.

## What was searched

| avenue | candidates | outcome |
|---|---|---|
| Amazon-Reviews-2023 categories | All_Beauty, Grocery, Digital_Music, Appliances, Video_Games, Baby, Office, Home_and_Kitchen | **all rejected** |
| terse English review corpora | app_reviews, yelp_review_full, rotten_tomatoes | one strong hit |
| parallel multilingual (twin by construction) | SIB-200 (tur/eng), XNLI (tr/en) | **both structurally dead** |

## Amazon: no category works

The target is a Turkish review set at 12–13 mean words with a style-solver lift
near zero. Every Amazon category missed on both axes:

| category | mean words | style lift |
|---|---|---|
| Grocery_and_Gourmet_Food | 46.8 | +0.091 |
| Appliances | 52.5 | +0.099 |
| All_Beauty | 58.9 | +0.067 |
| Office_Products | 59.7 | +0.072 |
| Home_and_Kitchen | 71.8 | +0.062 |
| Baby_Products | 72.3 | +0.051 |
| Digital_Music | 79.0 | +0.091 |
| Video_Games | 85.9 | +0.083 |

3.5–6.5x too long, and +0.05 to +0.10 of style signal everywhere, because
"long review = negative" is a universal Amazon pattern. Home_and_Kitchen, the
category criticised in `MUSTERI_TRIAL.md`, was near the **best** of the eight.
Re-picking the category does not work.

## Parallel corpora: killed by scale, not by quality

Both give a record-matched twin by construction, the property that makes the
intent axis strong. Both are far too small:

- **SIB-200** (tur_Latn/eng_Latn, 7 topic classes, FLORES-200 parallel):
  **1,004 rows total**, smallest class 58. Ceiling ≈ 14K tokens. Cannot reach
  even the 50K tier.
- **XNLI** (tr/en, 3 classes): human-translated portion is **7,500 rows**, which
  one 250K haystack would consume entirely, leaving no independence between
  haystacks. The 392,702-row train split is **machine-translated**, the exact
  confound the morphology claim must avoid.

**This is structural, not a search failure.** Human-translated parallel corpora
are small because human translation is expensive; TR-OOLONG needs a large pool
for independent draws at 100K–1M tokens. MASSIVE (16.5K parallel utterances) is
the largest such resource and is already used.

## The one strong hit: `sealuzh/app_reviews`

| | app_reviews | amazon_hpc_en (current twin) |
|---|---|---|
| rows | 288,065 | 60,000 |
| mean / median words | **18.8 / 12** | 44.8 / 26 |
| style lift (source) | **+0.000** | +0.068 |
| entity | 392 apps, MI **0.044** | 13,562 brands, MI 0.096 |
| **date column** | **yes, 2014–2017** | no |
| licence | **unstated** (withhold text) | Amazon ToU (withhold text) |

Built as `appreviews_en_out`: 237 questions, 9 families, tiers to 750K, all gates
pass, no family above chance from priors.

## But it does not fix the confound, because there is nothing to fix

Question-level style-solver lift over each family's majority baseline:

| pair | asymmetry |
|---|---|
| **current** vitamins_tr (+0.007) ↔ amazon_hpc_en (−0.008) | **0.015** |
| proposed vitamins_tr (+0.007) ↔ appreviews_en (−0.014) | 0.021 |

**The current primary pair is already at 0.015, which is noise.** The proposed
swap is marginally worse. Compare the pairs previously examined: We-Bears ↔
airline was 0.108 and Musteri ↔ Amazon Home was 0.106.

So: `vitamins_tr` ↔ `amazon_hpc_en` needs no replacement on this axis, and this
is now measured across four candidate pairings rather than assumed.

## What is actually worth taking

1. **`app_reviews` carries real dates.** That unlocks the timeline axis, which is
   the largest genuine gap against OOLONG: they have six timeline families and
   report them as their hardest question type; TR-OOLONG has one binary `shift`.
2. **It is one of OOLONG's own ten source datasets**, so it anchors the
   "we implement their typology" claim to a shared corpus rather than an analogy.
3. **`shift` is style-solvable in every set measured** — +0.300, +0.400, +0.300,
   +0.267, +0.267, +0.000, +0.300 across seven sets. This is now the
   best-evidenced defect in the benchmark and no choice of source corpus touches
   it. A dated timeline axis is the fix.

## Recommendation

Do **not** swap the primary pair. Add `app_reviews` as the substrate for a
**dated timeline axis** — that is where its value is, not as a twin.

## Reproduce

```
python scripts/appreviews.py
python src/build_tr_oolong.py --config configs/appreviews_en.json --build \
    --index manifests/appreviews_index.json
python scripts/quality_audit.py --sets appreviews_en_out --json manifests/appreviews_quality.json
python scripts/trivial_baseline.py --sets appreviews_en_out --out manifests/appreviews_baseline.json
python scripts/style_solver.py --set appreviews_en_out --source datasets/appreviews_en.parquet
```
