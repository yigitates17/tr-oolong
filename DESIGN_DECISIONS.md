# TR-OOLONG — Design decisions and their evidence

Why the benchmark is built the way it is. Every entry states the problem, the
evidence that it was a problem, what was changed, and what the change cost —
in the form needed to answer a thesis-jury question without hedging.

Read this alongside `ROADMAP.md` (what is done) and `DATACARD.md` (what the data
*is*). This file is the *why*.

---

## D1 — Records containing a label's surface form are dropped

**Problem.** The benchmark's core claim is that questions are not grep-solvable:
the question asks about a *latent* label, so a model must classify every record
rather than string-search. This claim was false on the Turkish review axis.

**Evidence.** `scripts/trivial_baseline.py` answers every question using only
substring search for label names — no classification, no model. On `tr_oolong_out`
it scored **0.733 exact on `most_common`** against a 0.333 chance floor. Cause:
the Turkish sentiment labels `olumlu` / `olumsuz` are ordinary Turkish words that
appear in review prose ("olumsuz bir deneyim"), and their frequency correlates
with the true majority label. `nötr` never appears at all, so it was ranked last
by default.

**Change.** `clean()` drops any record whose text contains any label's surface
form (raw and with `_` → space, Turkish-aware casefold). Config knob
`drop_label_leakage`, default on. Matching is against the **whole label space**,
not the record's own label, which is what makes the guarantee total: afterwards a
substring solver sees zero hits for every label, so its ranking carries no
information at all.

**Result.** `tr_oolong_out` `most_common` leakage score 0.733 → **0.133**. Across
all six sets no family's leakage score now exceeds its majority baseline.

**Cost.** 0.40%–0.93% of source records per corpus. Negligible.

**The finding worth reporting.** Only **0.84%** of Turkish review records leaked,
and that was enough to determine the argmax over three classes. *Leakage rate is
not a proxy for exploitability* — a small, label-correlated leak fully determines
an aggregate ranking. This is why the shortcut is removed at the source rather
than merely reported as a baseline floor.

**If asked "did you delete data to make your numbers look good?"** — the opposite:
the filter removes an *easy* shortcut, so it makes the benchmark harder and all
model scores lower. The dropped records are listed and counted in every manifest
(`cleaning.rows_dropped_label_leakage`).

---

## D2 — The leakage drop rate *is* the cross-lingual leakage measurement

**Problem.** Filtering leakage would destroy the phenomenon the matched twin was
designed to expose (English surface text leaks intent labels; Turkish morphology
does not).

**Change.** The filter's drop rate is measured on the *source corpora before
building* and recorded, so the phenomenon becomes a corpus statistic rather than
a benchmark contaminant.

| Corpus | Leaking records | Rate |
|---|---|---|
| MASSIVE tr-TR | 0 / 16,521 | **0.00%** |
| MASSIVE en-US | 112 / 16,521 | **0.68%** |
| Turkish brand reviews | 341 / 40,597 | 0.84% |
| Amazon H&PC (en) | 560 / 60,000 | 0.93% |

**Why this is the better number.** The earlier attempt measured the asymmetry as
a *difference in baseline scores* over 10 questions per family — far too few to
support a claim. The drop rate is computed over 16,521 utterances and is exact.
On the intent axis the asymmetry is total: zero Turkish utterances in 16.5K
surface their own intent label. On the review axis the rates are comparable,
because there the label names are ordinary sentiment words in both languages.

---

## D3 — Classes with too little support are removed (`min_class_support`)

**Problem.** `least_common` was answerable without reading the context.

**Evidence.** The gold answer was `cooking_query` in **10 of 10** haystacks, in
*both* languages — a majority baseline of 1.00. Cause: `cooking_query` has **6
rows in the 16,521-row MASSIVE corpus**. A haystack samples thousands of records,
so a 6-row class is pinned to the bottom of every ranking by the corpus, not by
the sampled context.

**Why it went undetected.** The only baseline in place was the leakage solver,
which scored 0.000 on this family and therefore looked healthy. A leakage solver
whose masks are all zero degenerates to a *constant* predictor; it is
structurally blind to prior-driven degeneracy. This is the reason D5 exists.

**Change.** Classes with fewer than `min_class_support` (100) rows are dropped
from the pool. Intent label space **60 → 48**.

**Result.** `least_common` majority baseline **1.00 → 0.20**, with 7–8 distinct
answers per 10 haystacks.

**Cost.** ~3% of the intent pool, and the headline "60 intents" becomes "48
intents". Accepted: a 48-class label space is still far larger than any other
Turkish long-context aggregation set, and 20 of 900 questions were previously
answerable with no context at all.

**Alternatives rejected.** (a) Rank only over supported labels while keeping all
60 in the haystack — preserves the headline but makes the question strictly
easier and the wording ("among the following labels…") harder to defend.
(b) Drop the family — discards a family that works once the tail is cut.

---

## D4 — Pair-level filtering keeps the matched twin controlled

**Problem.** The intent axis is a matched twin: tr-TR and en-US are the *same*
utterances, professionally translated. That is the thesis's cross-lingual
control, so any filter applied to one language must be applied to the other.

**Evidence of the failure mode.** Applying D1 and D3 per locale produced **48
Turkish classes and 49 English ones**, with different dropped-class lists — a
"controlled" comparison across two different label spaces. Separately, per-locale
near-duplicate collapse and word-length bounds had *always* left the twin
unequal: 15,250 Turkish vs 15,765 English rows, so "the same utterances" was only
ever true to ±3%.

**Change.** `scripts/massive.py` performs every pair-sensitive decision on the
locale pair, joined on `(partition, id)`:
1. leakage filter as a **union** — an utterance leaking in *either* language is
   dropped from both;
2. class-support cut as a **union** — a class under-supported in *either* is
   dropped from both;
3. the builder's own cleaner is run per locale and only the **intersection** of
   surviving `pair_id`s is written.

**Result.** Both locales: exactly **15,075 rows, 48 intents**. The twin is now
row-identical, not approximately parallel.

**Why it matters for the thesis.** Any Turkish-vs-English performance gap can now
be attributed to language rather than to a difference in what the two haystacks
contain. Without this, a reviewer can ask whether the gap is a sampling artifact,
and the honest answer would have been "partly, and we cannot say how much."

---

## D5 — Two baselines, not one: leakage *and* majority-class

**Problem.** A single baseline hid D3 completely.

**Change.** `scripts/trivial_baseline.py` reports per family: the leakage score,
the **majority baseline** (score of always emitting the most frequent gold
answer), the number of distinct gold answers, and a `degenerate` flag
(majority ≥ 0.9).

**How to read them.** They are diagnostic of different failures:
- leakage score **above** majority baseline ⇒ an exploitable surface shortcut;
- majority baseline **high** ⇒ the answers are determined by the corpus prior,
  regardless of leakage;
- once leakage is filtered, the leakage solver becomes a constant predictor, so
  its score *equals* the majority baseline by construction — which is exactly
  what is observed now, and is the signature of a clean set.

**This is the acceptance gate** for any future rebuild. `manifests/baseline_report.json`
is the committed record.

---

## D6 — Maximum haystack length is derived, not chosen

**Problem.** "Make the context as long as possible" conflicts with keeping the
label-ranking families meaningful, and the conflict was invisible until measured.

**Evidence.** The English airline-tweet set at 250K tokens had a `most_common`
majority baseline of **0.700 with only 2 distinct answers across 10 haystacks**.
The corpus is 9,178 negative / 3,099 neutral / 2,363 positive, and a 250K-token
haystack consumes ~7,400 tweets — so `positive`, with 2,363 records in total,
*cannot* reach a one-third share no matter what the sampler does.

**The rule.** A haystack of R records over K classes gives each class a 1/K share
on average, so a class can only top the ranking if the pool can supply more than
R/K of it. The smallest class therefore caps the haystack at

> **R_max = min_class_pool × K records**

Above that, the rare classes are pinned by the corpus rather than by the sampled
context and the ranking families answer themselves. This binds only for small
label spaces; with many classes the ranking is contested among the well-supported
ones, which is what D3 handles instead (`RANKING_CONTESTED_K = 10`).

**Calibration.** `tr_oolong` at 0.85× its ceiling still varies (majority 0.467,
3 distinct); airline tweets at 1.12× is degenerate. The builder now warns above
**0.85×** (`check_length_feasibility`) and records the ceiling in every manifest
under `ranking_feasibility`.

**Applied ceilings and the resulting tiers.**

| Set | Pool | Smallest class | Ceiling | Tiers |
|---|---|---|---|---|
| `amazon_hpc_en` | 55,400 | 17,806 | ~3.16M | 100K / 250K / 500K / **1M** |
| `vitamins_tr` | 38,974 | 7,994 | ~911K | 100K / 250K / 500K / **750K** |
| `tr_oolong` | 24,071 | 2,913 | ~559K | 100K / 250K / **500K** (0.85×, at the limit) |
| `en_twin` (airline) | 14,280 | 2,219 | ~224K | **50K / 100K** (was 100K/250K) |

**Result.** Longest haystack in the benchmark goes 500K → **1M tokens**, and the
airline set stops being degenerate (`most_common` majority 0.700 → 0.500, 2 → 3
distinct answers). Total questions 900 → **1,020**.

**Cost.** The airline set no longer reaches 250K. Accepted: it was skewed there,
and length parity across the review pairs was already broken (the airline corpus
is roughly 400K tokens in total — it simply cannot carry long context). Pair (b),
the domain-matched supplement-review pair, carries the length gradient instead.

**If asked "why is one set shorter?"** — because its source corpus is too small
to support a longer haystack without the questions becoming answerable from the
corpus prior. The bound is computed, recorded per set, and enforced by a build
warning.

---

## D7 — Multi-aspect review labels are dropped (documented selection effect)

**Observation.** 15,411 of 40,597 We-Bears rows (38%) carry comma-joined
multi-aspect labels (`olumsuz,olumlu`) rather than one sentiment. The builder
drops them, because ground truth requires exactly one label per record.

**Consequence, stated plainly.** The retained pool is *not* a random sample of
the corpus: it skews toward shorter, single-aspect reviews and toward negative
(15,637 olumsuz / 5,734 olumlu / 3,815 nötr). Aggregate answers remain exact with
respect to the built haystack — which is all any question asks about — but the
pool is not representative of Turkish review text in general, and no claim in the
thesis should say that it is.

This is recorded rather than fixed: aggregating multi-aspect labels into one
would require an annotation decision the benchmark deliberately avoids making.

---

## D8 — Reproducibility guarantees

- **Single string seed** (`{seed}-{lang}-{target}-{k}`); row order canonicalised
  before every sampling step, so engine parallelism cannot perturb output.
- **Dual-path ground truth**: every answer computed by an independent Polars path
  and a pure-Python path and asserted equal. A new question family cannot ship
  without an independent oracle.
- **Golden regression test** (`tests/test_golden.py`): rebuilds a committed
  fixture and byte-compares. Any change to sampling, ordering, question
  generation, or ground truth fails it; intentional changes require `--regen`
  plus a `VERSION` bump.
- **Cross-platform verified**: all six sets rebuild manifest-identical on
  macOS/arm64 from an original built on Windows/x86, under the pinned versions in
  `requirements.txt`.
- **Every source has a fetch script** under `scripts/`, so a rebuild starts from
  the public datasets, not from a local file. (`scripts/airline.py` was added for
  this reason; before it, one of the six sets could not be reproduced by anyone.)

**Note on `VERSION`.** The `v0.3.0` git tag was originally pushed while
`VERSION` still read `0.2.1`, so the tag, the manifests, and the golden files
disagreed. Corrected; the discipline is that `VERSION` and the golden files move
together with any builder change.

---

## Open items, stated as risks

- **`shift` skew.** Binary family; majority baselines of 0.65–0.80 on some sets at
  n=10–20. Consistent with binomial noise at these counts, but the ranking
  families are underpowered for any strong per-family cross-lingual claim.
  Fix if needed: more haystacks per length, not more questions per haystack.
- **Haystack overlap at the longest tiers.** At 500K–1M a haystack consumes
  15–35% of its pool, so the five haystacks at a tier share records and are not
  independent samples. Ground truth is unaffected (it is computed from the actual
  haystack), but per-tier variance is understated.
- **`scripts/health.py` streams** the Amazon dataset and takes the first N per
  class in stream order rather than sampling with a seed. Reproducible in
  practice — the rebuild matched byte-for-byte — and guarded by
  `source_hash_first1000` in the manifest, but it is not a *guaranteed* sample.
