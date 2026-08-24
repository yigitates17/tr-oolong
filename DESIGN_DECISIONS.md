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

**Problem.** The intent axis is a matched twin: tr-TR and en-US are the same utterance IDs, translated and localized per locale. That is the thesis's cross-lingual
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

**Why it matters for the thesis.** The two locales now draw from an identical
*pool*: same utterances, same label space, same row count.

> **Corrected in v0.4.0 — see D11.** This entry originally claimed that a
> Turkish-vs-English gap "can now be attributed to language rather than to a
> difference in what the two haystacks contain." That was **false as written**.
> Pool-level parity is not haystack-level parity: `language` was part of the RNG
> seed, so each locale sampled its own records (2,735 tr vs 3,478 en at 50K
> tokens), with different drift targets and different questions. D11 adds the
> record-matched build that makes the original claim true.

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

**Read `leak` against the right reference.** "Leakage score above majority
baseline" is the rule for families with *few* distinct gold answers. On a family
with many distinct answers the majority baseline is near zero and the rule
misfires: `tr_oolong` `pairwise` reports `leak=0.600 majority=0.133`, which looks
alarming until you note that pairwise has 14 distinct answers over 15 questions
and its **chance** rate is 0.5 — a filtered leakage solver degenerates to a
constant, and a constant scores ~0.5 on a binary family. Compare against
`max(majority, chance)`; both columns are reported for exactly this reason.

**This is the acceptance gate** for any future rebuild, alongside
`scripts/quality_audit.py` (D13). `manifests/baseline_report.json` is the
committed record.

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

## D9 — Entity-relational questions ask about a NAMED, prior-neutral candidate set

**Problem.** The three entity families (`entity_argmax`, `top_k`, `pairwise`) were
supposed to be the review axis's distinctive contribution. They were the most
broken part of the benchmark.

**Evidence.** A **context-free prior oracle** — a solver that answers every
question from source-corpus statistics and never reads the haystack — scored:

| set | `pairwise` | `entity_argmax` | `top_k` |
|---|---|---|---|
| `tr_oolong` | 0.733 | 0.867 | 0.077 |
| `en_twin` | 0.900 | 0.700 | 0.300 |
| `vitamins_tr` | **1.000** | 0.800 | 0.900 |
| `amazon_hpc_en` | 0.850 | 0.550 | 0.188 |

`vitamins_tr` `pairwise` was 20/20 correct with no context at all. And it got
*worse with length* — at 250K–1M tokens the haystack converges on corpus
proportions, so the biggest brand wins ever more reliably. Exactly backwards for
a long-context benchmark.

Separately, the questions were **thin**: the median `tr_oolong` `pairwise`
question was decided by **8 records out of a 3,919-record haystack**, with a
margin of 2. That is needle-in-a-haystack retrieval with a coin-flip tiebreak —
the task OOLONG exists to replace.

**Cause.** `draw_label_weights` gave every haystack a fresh random *label* prior,
but nothing perturbed the *entity* axis, so every haystack inherited the corpus's
brand ranking. D6's length ceiling protects the label axis only. The defect was
invisible to both existing baselines: the leakage solver saw no label strings,
and the majority baseline saw well-spread gold answers.

**Change.** Three parts, all needed:

1. **`draw_entity_jitter`** — a per-haystack log-normal perturbation (σ = 1.0) of
   the entity distribution, multiplied into the A-Res sampling weights. Big
   brands stay big (support survives) but the ordering among comparable brands
   becomes a property of *this haystack*.
2. **`pick_entity_candidates`** — the question names its candidates, and they are
   matched on their **pool count for the asked label** to within 5%. Matching on
   total brand *size* is not enough: label counts are roughly proportional to
   size, so the biggest candidate still wins. With the corpus-level counts
   near-identical, the corpus cannot rank them.
3. **Depth and margin floors in both GT paths** (`_margin_ok`, `min_answer`): the
   winner needs a real count and a real lead, so no answer rests on a handful of
   records or on a gap of one.

**Result** (measured on ~200–900 *distinct* questions per family, not on the
~15 that ship — a Monte Carlo that redraws the same question learns nothing):

| set | family | prior | chance | z |
|---|---|---|---|---|
| `tr_oolong` | `entity_argmax` | 0.221 | 0.200 | +0.9 |
| `tr_oolong` | `pairwise` | 0.528 | 0.500 | +0.8 |
| `tr_oolong` | `top_k` | 0.017 | 0.017 | +0.0 |
| `vitamins_tr` | `entity_argmax` | 0.209 | 0.200 | +0.3 |
| `vitamins_tr` | `pairwise` | 0.475 | 0.500 | −1.5 |

**Cost.** Fewer entity questions (the constraints reject many draws), and two
sets lose a family outright:

- **`en_twin` loses `entity_argmax` and `top_k`.** Six airlines cannot form a
  prior-neutral 5-way candidate set. Stated plainly rather than papered over.
- **`vitamins_tr` and `amazon_hpc_en` lose `top_k`** (`families_disabled`).
  Certified at power, *exact ordering* stayed prior-correlated on both
  (vitamins 0.113 vs 0.017 chance, z = +5.5; amazon 0.107, z = +3.7) even after
  the jitter. `top_k` therefore ships on **`tr_oolong` only** (0.040 vs 0.017,
  z = +1.3), whose 1,430 brands are long-tailed enough (top-1 share 1.5%) that
  the ordering is genuinely contested.

  Note the asymmetry, which is the interesting part: `entity_argmax` decorrelates
  easily on every set (z = +0.5 to +1.4) because the jitter readily flips the top
  entry, but the *full ordering* retains rank correlation — flipping one position
  is easy, permuting three independently is not. **Exact ordering is intrinsically
  the hardest family to make prior-neutral**, and where it cannot be, it does not
  ship. This is also why the defect was invisible before `--certify`: `top_k`
  ships 6-8 questions per set, and no test on 8 samples can see z = +3.7.

**The generalisable finding.** D1 established that leakage *rate* does not
predict exploitability. D9 is its sibling: **prior-randomising one axis while
leaving a correlated second axis untouched reopens the shortcut you just
closed.** Anti-shortcut work has to cover every axis a question ranges over.

---

## D10 — The label-ranking families also name their candidates

**Problem.** Two separate defects, one fix.

**Evidence.** (a) `most_common` over the 48-class intent axis asks a model to
produce `iot_hue_lightoff` with no indication that such a label space exists —
the question is not well posed. (b) On that axis the ranking is decided by its
tail: in a 6,000-record haystack the rarest label has **~7 records** and adjacent
ranks differ by **1**, so `least_common` over all 48 labels is a coin flip.

**Change.** These families name their candidate labels, exactly as D9 does for
entities: `min(K, label_candidates)` labels, matched on pool counts when the
label space is larger than the candidate set. When `K <= label_candidates` the
candidate set *is* the whole label space, so the 3-class review axis keeps its
original semantics and wording.

**Result.** The question is self-contained (no dependence on a harness prompt to
inject the inventory), and `least_common` compares well-supported labels with a
real margin instead of ranking noise.

**Cost.** Chance rises from 1/48 to 1/5 on the intent axis, and is reported.
A well-posed question with a known chance rate is worth more than an unanswerable
one with a nominal chance of 2%.

---

## D11 — The matched twin is built in two regimes, and the difference is the finding

**Problem.** D4 made the intent twin row-identical *in the pool*. It was never
identical *in the haystack*: the RNG seed was `{seed}-{lang}-{target}-{k}`, so
each locale sampled its own records. At 50K tokens Turkish held 2,735 utterances
and English 3,478 — different records, different drift targets, different
questions. The claim in D4 that "any Turkish-vs-English gap can be attributed to
language rather than to a difference in what the two haystacks contain" was
**false as written**.

Fixing the seed alone is not enough, because an equal *token* budget necessarily
buys different numbers of records in the two languages.

**Change.** Two knobs, and both sets are built:

- `pair_seed` drops `language` from the RNG seed.
- `haystack_target_records` fixes the **record count** instead of the token
  budget.

Together they give a **record-matched twin**: `tr_intent_paired` and
`en_intent_paired`. Verified — identical `row_id` order, identical labels,
identical halves, identical drift target, and **110 of 120 questions identical
including the gold answer**. The 10 that differ are `shift`, where the same fact
is expressed in each language (`arttı` / `rose`).

**Why it matters.** The comparison becomes *paired*: the same question, over the
same records, differing only in language. That admits McNemar's test on matched
pairs instead of comparing two independent samples at n = 10, which was never
going to support a cross-lingual claim.

**And it yields a measurement.** At identical record counts, Turkish costs

> **1.30–1.34× the tokens of English** (Qwen3-8B), stable across every haystack.

That ratio *is* the morphology tax, isolated from any model. The two regimes now
answer two different questions: token-matched asks "at equal budget", and
record-matched asks "at equal content". The gap between them is attributable to
tokenization rather than to reasoning.

---

## D12 — Turkish that a Turkish speaker would accept

Small, and the cheapest credibility in the project.

- **Vowel harmony.** `pairwise` hardcoded `'{a}' mı yoksa '{b}' mi`, so
  *'akbank mı yoksa mng kargo mi'* — which should be **mu**. `soru_eki()` now
  derives the particle (mı/mi/mu/mü) from the last vowel, falling back to `mi`
  for vowelless acronyms (every Turkish consonant letter-name ends in *e*).
- **Orthography.** `artti`/`azaldi` → `arttı`/`azaldı`.
- **Label consistency.** `vitamins_tr` labelled neutral `notr` while `tr_oolong`
  used `nötr`; a model answering `nötr` on the vitamins set scored **0**. Fixed at
  the source, and `scoring.py` now accepts an ASCII-folded fallback so an
  orthographic artifact never costs a correct answer.
- **Separator.** `<<<KAYIT>>>` — a Turkish word — separated records inside the
  **English** haystacks, and tokenizes differently in each language. Replaced with
  the language-neutral `<<<###>>>`, which costs the same tokens in both.

---

## D13 — The acceptance gate now includes a context-free prior oracle

**Problem.** D5 added a second baseline because one had hidden D3. Two were still
not enough: both were blind to D9.

**Change.** `scripts/quality_audit.py` is a third gate, and reports per family:

- **thin** — how many questions are decided by fewer than N records;
- **knife-edge** — how many rest on a margin below the configured threshold;
- **prior accuracy vs chance**, with a one-sided binomial test.

Two lessons are built into it, both learned by getting them wrong first:

1. **Chance must be modelled correctly.** Scoring `top_k` against chance = 0
   flagged an at-chance family as broken; ordering 3 of 5 named candidates has
   chance 1/60. For free-form numeric families the reference is the majority
   baseline, not zero.
2. **Certify the generator, not the shipped sample.** At n = 10–20 a family
   cannot be certified: `tr_oolong` `pairwise` measured 0.85 on the 13 shipped
   questions and 0.53 on 235 distinct draws. And a Monte Carlo must **deduplicate**
   — redrawing the same question 400 times measures nothing.

`manifests/quality_audit.json` is the committed record; the script exits non-zero
if any family beats chance.

---

## D14 — Haystacks must actually reach their advertised length

**Problem.** The benchmark's headline axis is context length, and the lengths were
wrong.

**Evidence.** Measured actual-vs-target tokens per haystack:

| set | tier | mean actual/target | worst |
|---|---|---|---|
| `tr_oolong` | 100K | 0.820 | **0.531** |
| `tr_oolong` | 250K | 0.897 | 0.708 |
| `tr_oolong` | 500K | 0.849 | 0.763 |
| `en_twin` | 50K | 0.961 | 0.929 |
| all others | — | ≥0.986 | ≥0.983 |

A haystack advertised as 100K tokens contained **53K**; a 500K one contained
381K. Worse than the average error is its *variance* — 0.53 to 0.90 within one
tier — which puts noise directly on the axis the thesis measures.

**Cause.** The candidate count was estimated once from the pool's *mean* record
length (`need = target / mean_tokens * 1.05`). On a heavy-tailed length
distribution the sampled subset runs shorter than the pool mean, so every
candidate fits inside the budget and the haystack simply runs out of records.
The 1.05 safety factor covers a mild miss, not a heavy tail. It bit `tr_oolong`
(reviews, 3–400 words) and spared MASSIVE (utterances, near-uniform length) and
the stratified Amazon pool.

**Change.** `rank_candidate_rows` now returns the *full* A-Res ranking, and
`build()` deepens the slice until the token budget is met or the pool is
exhausted. Because one key is drawn per pool row regardless of how many rows are
wanted, the rankings for different depths are **nested** — deepening extends the
same weighted selection rather than resampling, so a haystack that already fit is
untouched. If the pool genuinely cannot fill a tier, the build prints
`[short-haystack]` with the shortfall.

**Result.** `tr_oolong` 0.531–0.897 → **0.972–0.986**, in line with every other
set.

**Why it went undetected.** Nothing compared the realized length to the target.
The manifest recorded `n_examples` but not `n_tokens`, so a haystack half its
advertised size looked identical to a correct one. Both are recorded now.

---

## Open items, stated as risks

- **Per-family n is still small.** 7–20 questions per family per set. The prior
  audit is run on hundreds of *candidate* draws so the generator is certified at
  adequate power, but the shipped sample cannot support a strong per-family
  cross-lingual claim on its own. Fix: more haystacks per length, not more
  questions per haystack. The record-matched twin (D11) partly compensates by
  making the comparison paired.
- **Source label noise is unmeasured.** Every gold answer is exact with respect
  to the haystack, but the haystack's labels come from the source corpus. If
  those are 90% accurate, a model that classifies *better* than the annotators is
  marked wrong. This is the benchmark's real accuracy ceiling and it is not yet
  quantified; the 200-row slices written by `--audit` exist for exactly this.
- **Haystack overlap at the longest tiers.** At 500K–1M a haystack consumes
  15–35% of its pool, so the five haystacks at a tier share records and are not
  independent samples. Ground truth is unaffected (it is computed from the actual
  haystack), but per-tier variance is understated.
- **`scripts/health.py` streams** the Amazon dataset and takes the first N per
  class in stream order rather than sampling with a seed. Reproducible in
  practice — the rebuild matched byte-for-byte — and guarded by
  `source_hash_first1000` in the manifest, but it is not a *guaranteed* sample.
