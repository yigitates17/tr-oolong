# MusteriYorumlari pair — trial build and results

Branch `musteri-twin`. **Not merged.** Nothing shipped was modified; the existing
eight sets are untouched and the golden test still passes byte-identical.

## What was built

| | Turkish | English twin |
|---|---|---|
| source | `turkish-nlp-suite/MusteriYorumlari` (Hepsiburada + Trendyol) | Amazon-Reviews-2023 `Home_and_Kitchen` |
| labels | customer's own 1–5 stars → 3 classes | reviewer's own 1–5 stars → 3 classes |
| pool | 38,649 rows, **12,883 per class** | 38,649 rows, **12,883 per class** |
| tiers | 100K / 250K / 500K | 100K / 250K / 500K |
| questions | 138 | 138 |
| families | 6 (no entity column in the Turkish half) | 6 |
| licence | CC-BY-SA-4.0, text distributable | Amazon ToU, text withheld |

Both halves capped to the smallest class, so the pool is **perfectly balanced**
(normalised entropy 1.000, imbalance 1.0x) — better than any shipped review set.

## Gates

All pass. `quality_audit.py`: 100% OK on both sets, **no family answerable above
chance from corpus priors**. `trivial_baseline.py`: leakage solver at or below
the majority baseline everywhere. `test_golden.py`: byte-identical.

## The result that matters, and it is not the one expected

A fourth solver was written for this trial (`scripts/style_solver.py`): classify
every record in the haystack using **only** length, final period, and `!`/`?`,
then aggregate and answer the real questions with the frozen scorer. Scored as
lift over each family's majority baseline:

| set | mean style lift |
|---|---|
| `tr_oolong` (We-Bears) | **−0.008** |
| `en_twin` (airline) | **−0.116** |
| `musteri_tr` | **−0.044** |
| `amazon_home_en` | **+0.062** |

| pair | twin asymmetry |
|---|---|
| current (We-Bears ↔ airline) | **0.108** |
| new (Musteri ↔ Amazon Home) | **0.106** |

**The swap does not fix the confound it was proposed to fix.** The asymmetry is
the same size. The earlier claim — that We-Bears' source-level style shortcut
(+0.120 vs its twin's +0.017, a 7x gap) breaks the cross-lingual comparison —
was measured on the *source pool* and the consequence was inferred rather than
measured. At the question level the builder's prior-randomised sampling and
margin floors absorb most of it. Source-level style lift is **not** a good
predictor of question-level exploitability.

## What the swap does and does not buy

Buys: perfect class balance (1.0x vs 4.1x); documented label provenance (the
customer's own star vs undocumented); 970K-token ceiling vs 527K; a
distributable licence; a same-domain twin (both general e-commerce).

Costs: **four families**. No entity column, so 6 of 10 ship. And the English half
I picked has a real defect the current pair does not: `most_common` style lift
**+0.250** on `amazon_home_en`, because Home & Kitchen negative reviews are long
and positive ones short. If this pair is adopted, re-pick the English category
and re-run the solver.

## A genuine defect, independent of which corpus is used

`shift` is style-solvable in **all four** sets: +0.267, +0.267, +0.000, +0.300
lift over majority. Combined with its already-weak floor (mean majority baseline
0.61 across the suite, 0.73 on `tr_oolong`), this is the family to fix or drop —
and no change of source corpus addresses it. Adding a real dated timeline axis,
as OOLONG has, is the fix.

## Recommendation

**Do not swap on the confound argument — it does not hold.** There is still a
reasonable case on balance, provenance, licence and length ceiling, but it costs
four families, and four families is a large price for a benefit the measurement
does not support. If a third axis is wanted, adding `musteri_tr` ↔ a re-picked
English twin *alongside* the existing sets costs nothing and adds a
perfectly-balanced, distributable, 6-family pair.

## Reproduce

```
python scripts/musteri.py && python scripts/amazon_home_en.py
python src/build_tr_oolong.py --config configs/musteri_tr.json configs/amazon_home_en.json \
    --build --index manifests/musteri_pair_index.json
python scripts/quality_audit.py --sets musteri_tr_out amazon_home_en_out \
    --json manifests/musteri_quality_audit.json
python scripts/trivial_baseline.py --sets musteri_tr_out amazon_home_en_out \
    --out manifests/musteri_baseline.json
python scripts/style_solver.py --set musteri_tr_out --source datasets/musteri_tr.parquet
```
