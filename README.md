# TR-OOLONG

The first Turkish long-context **aggregation** benchmark, with a matched English
twin built by the identical pipeline. The nearest multilingual long-context
benchmark, ONERULER (arXiv:2503.01996), covers 26 languages and **Turkish is not
one of them**; its two aggregation tasks are also lexical (most-frequent-word
extraction), answerable by counting strings rather than by classifying each
record. The claim here is therefore two gaps wide: the language, and
latent-label aggregation rather than word counting. It follows the OOLONG-synth construction
principle (Bertsch et al., 2025): concatenate examples from an existing *labeled*
dataset into a 50K–1M-token haystack, then auto-generate distributional
questions whose ground truth is computed exactly from the source labels — no
manual annotation.

> TR-OOLONG adopts the OOLONG-synth construction principle — distributional
> questions computed exactly from source labels — and extends it cross-lingually
> with a matched-twin design, a broader question typology, and a
> verified-by-construction ground-truth pipeline.

## 1. What it measures

Most long-context benchmarks test **retrieval** ("find the needle"). TR-OOLONG
tests **aggregation**: to answer *"how many records have intent X?"* a model must
classify every atom in the haystack and combine the results. The label never
appears verbatim in the text, so nothing is grep-solvable — every question forces
latent classification plus counting, not string matching. This makes it a probe
for whether a model actually *ingests* a long context rather than skimming it.

The review axis rests on **two independent corpora per language**, so aggregation
results can be shown to hold across datasets rather than being an artifact of a
single source. The supplement pair (Turkish Vitaminler.com ↔ English Amazon
Health & Personal Care) is same-domain and thus the tighter twin; the
reviews↔airline-tweets pair is matched by pipeline but not domain.

Two axes:

| Axis | Source | Label (classes) | Entity axis | Purpose |
|---|---|---|---|---|
| **Review / sentiment** | Two TR–EN corpus pairs: (a) Turkish brand reviews + EN airline tweets; (b) Turkish vitamin/supplement reviews + EN Amazon Health & Personal Care | sentiment (3) | brand / airline — *orthogonal* | length scaling to 1M tokens; entity-relational reasoning; cross-corpus robustness |
| **Intent** | Amazon MASSIVE (tr-TR / en-US, parallel corpus) | intent (48) | scenario (18) — *nested* | label-space difficulty; by-construction cross-lingual control |

The intent axis is built **twice**, in two matching regimes, because they answer
different questions:

- **token-matched** (`tr_intent` / `en_intent`) — equal token budget. Turkish
  therefore holds ~25% fewer utterances. Asks *"at equal cost, which language
  degrades faster?"*
- **record-matched** (`tr_intent_paired` / `en_intent_paired`) — equal *record*
  count, same records, same order, same drift target. **110 of 120 questions have
  a byte-identical gold answer in both languages** (the other 10 are `shift`,
  where the same fact is written `arttı` / `rose`). Asks *"at equal content,
  which language degrades faster?"* — and admits **paired** tests (McNemar)
  rather than comparing two independent samples.

The difference between the two regimes is itself a measurement: at identical
record counts Turkish costs **1.30–1.34× the tokens of English** under Qwen3-8B,
stable across every haystack. That ratio is the morphology tax, isolated from any
model's behaviour.

MASSIVE ships 60 intents, but 12 of them have too few examples to ever be
sampled competitively — with 6 rows in a 16.5K-row corpus, `cooking_query` was
the rarest label in *every* haystack, which made `least_common` answerable from
corpus priors without reading the context at all. Classes below a support floor
(`min_class_support`, 100 rows) are dropped from the pool, and the cut is taken
over the *union* of both locales so the twin keeps an identical label space.
See §4 and `DESIGN_DECISIONS.md` (D3, D4).

## 2. Question families and where they apply

The entity axis behaves differently on the two sources, and this determines which
families are meaningful:

- On the **review axis**, `brand` is *orthogonal* to `sentiment` (every brand
  receives all three sentiments), so entity-relational questions carry real
  signal.
- On the **intent axis**, `scenario` is *nested* inside `intent` (each MASSIVE
  intent belongs to exactly one scenario), so entity-relational questions are
  trivial or impossible. The builder detects nesting automatically and emits only
  the applicable families.

| Family | Question shape | Review axis | Intent axis |
|---|---|:---:|:---:|
| `count` | how many records have label X | ✓ | ✓ |
| `proportion` | what share have label X (percent, or per-mille if >10 classes) | ✓ | ✓ (per-mille) |
| `shift` | did label X's share rise or fall in the second half | ✓ | ✓ |
| `most_common` | which label is most frequent | ✓ | ✓ |
| `least_common` | which label is least frequent | ✓ | ✓ |
| `second_most` | which label is second most frequent | ✓ | ✓ |
| `entity_count` | how many X-labelled records in group G | ✓ | — nested |
| `entity_argmax` | which **named candidate** group has the most X | ✓ | — nested |
| `top_k` | the k **named candidates** with the most X, ordered | ✓ | — nested |
| `pairwise` | which of A or B has more X | ✓ | — nested |

**Every ranking question names its candidates.** `entity_argmax`, `top_k` and the
three label-ranking families list the options they range over. This is not a
convenience: it is what makes them (a) *well posed* — no model can be asked to
produce `iot_hue_lightoff` without being told such a label space exists — and
(b) *unanswerable from the corpus*, because the candidates are chosen to have
near-identical corpus-level counts, so only this haystack can rank them. See §4
and `DESIGN_DECISIONS.md` (D9, D10).

A family ships only where it passes that test, and three sets lose one:
`en_twin` (6 airlines) cannot form a prior-neutral 5-candidate set, so it emits no
`entity_argmax`/`top_k`; `vitamins_tr` and `amazon_hpc_en` disable `top_k`, whose
*exact ordering* stayed prior-correlated even after entity randomization
(z = +5.5 and +3.7 under `--certify`). `top_k` therefore ships on `tr_oolong`
alone. Flipping one position is easy to randomize; permuting three independently
is not — so exact ordering is intrinsically the hardest family to make
prior-neutral. All of this is recorded, not hidden.

The `most_common` / `least_common` family mirrors the OOLONG-synth counting
typology; their actual task identifiers are `MOST_FREQ`, `LEAST_FREQ`,
`RELATIVE_FREQ`, `NUMERIC_ONE_CLASS` and `REPRESENTED_N_TIMES`. `second_most` is
an **extension, not a mirror** — OOLONG has second-most *user* and second-most
*date*, but no second-most *label*. Each is a
single-question-per-haystack family (like `shift`): asking twice adds nothing.

## 3. Example questions (produced by the actual builder)

Every answer below is computed from the source labels by two independent code
paths and asserted equal (see §6).

**Review axis** (orthogonal brand entity), from `tr_oolong_out/questions.jsonl`:

- `entity_argmax` — *"Şu markalardan hangisi en çok 'olumlu' yorum aldı: 'arzum', 'carrefoursa', 'general mobile', 'vestel', 'ziraat bankası'? Sadece marka adını yaz."* → **general mobile**
- `top_k` — *"Şu markalar arasında en çok 'olumlu' yorum alan ilk 3 marka hangileri: 'arzum', 'carrefoursa', 'general mobile', 'vestel', 'ziraat bankası'? …"* → **general mobile > carrefoursa > vestel**
- `pairwise` — *"'olumlu' yorumu hangisinde daha çok: 'arzum' mu yoksa 'derimod' mu? Sadece marka adını yaz."* → **arzum**
- `entity_count` — *"'kahve dünyası' markası hakkındaki yorumlardan kaç tanesi 'nötr'? Sadece sayıyı yaz."* → **10**

Note the question particle: *arzum **mu*** but *derimod **mu*** and *ebebek **mi***.
It is derived per brand by Turkish vowel harmony (`soru_eki`), not hardcoded.

**Intent axis, Turkish**, from `tr_intent_out/questions.jsonl`:

- `count` — *"Bu kayıtlarda kaç tane 'recommendation_locations' etiketli kayıt var? Sadece sayıyı yaz."* → **15**
- `proportion` — *"Kayıtların binde kaçı 'alarm_remove' etiketli? …"* → **17** (per-mille)
- `shift` — *"Kayıtların ikinci yarısında 'qa_currency' etiketli kayıtların oranı ilk yarıya göre arttı mı azaldı mı? 'arttı' veya 'azaldı' yaz."* → **arttı**
- `least_common` — *"Bu kayıtlarda en az görülen etiket hangisi? Etiketler: 'alarm_query', 'iot_coffee', 'iot_hue_lightoff', 'play_game', 'social_query'. …"* → **social_query**

**The record-matched twin.** The two sets contain **different text** — Turkish
utterances and their English counterparts. What is identical is *which* records
are present, in *what order*, with *what labels*. Because every answer is derived
from the labels, the gold answer is therefore the same in both languages:

```
row 13050  [iot_coffee]   TR: "biraz kahve yapar mısın"
                          EN: "can you make some coffee"
row  9651  [social_query] TR: "facebook bilgisi"
                          EN: "facebook info"
```

That is what makes the comparison paired: a model sees a genuinely Turkish
haystack and a genuinely English one, is asked the same question, and the correct
answer is the same number. Any difference in score is a difference in language,
not in what was being counted:

| | Turkish (`tr_intent_paired`) | English (`en_intent_paired`) |
|---|---|---|
| `most_common` | *"…en sık görülen etiket hangisi? Etiketler: 'alarm_query', 'iot_coffee', 'iot_hue_lightoff', 'music_likeness', 'play_game'."* | *"Which label is the most common…? Labels: 'alarm_query', 'iot_coffee', 'iot_hue_lightoff', 'music_likeness', 'play_game'."* |
| answer | **iot_hue_lightoff** | **iot_hue_lightoff** |
| `count` | *"…kaç tane 'transport_taxi' etiketli kayıt var?"* | *"How many utterances have the intent 'transport_taxi'?"* |
| answer | **18** | **18** |

By contrast the **token-matched** pair (`tr_intent` / `en_intent`) gives each
language an equal token budget, so they hold *different numbers of different
records* and their answers do not correspond. That pair answers "at equal cost";
the paired sets answer "at equal content". Both are shipped because they are
different questions — only the paired one supports a paired test.

A real sample question set is committed at `examples/sample_questions_review.jsonl`.

## 4. Construct validity

Three independent shortcut solvers must fail before a set ships. Each exists
because a *previous* version of the benchmark was solvable by it.

**(a) Grep-proofness — the leakage solver.** The question asks about a latent
*label*, and no record contains any label's surface form; records that do are
dropped at build time (`drop_label_leakage`), over the whole label space, not
just the record's own label. This is enforcement, not assumption, because the
assumption was false: a solver doing nothing but substring search for three
Turkish words recovered `most_common` on `tr_oolong` **73%** of the time
(chance 33%). After filtering it scores at chance.

Only **0.84%** of records leaked, and that was enough to determine the argmax
over three classes, because the leaks correlate with the gold label. *Leakage
rate is not a proxy for exploitability.*

**(b) Answer skew — the majority baseline.** The score of always emitting the
most frequent gold answer. A leakage solver whose masks are all zero degenerates
to a constant predictor, so it is structurally blind to prior-driven degeneracy —
which is how a `least_common` family with a majority baseline of **1.00**
(`cooking_query` in 10/10 haystacks) survived undetected. Read `leak` against
`max(majority, chance)`: on a family with many distinct answers the majority
baseline is near zero and is the wrong reference.

**(c) Corpus priors — the context-free oracle** (`scripts/quality_audit.py`).
Answers every question from source-corpus statistics alone, never reading the
haystack. Both earlier solvers were blind to it, and it found the worst defect in
the benchmark:

| set | `pairwise` | `entity_argmax` | `top_k` |
|---|---|---|---|
| `tr_oolong` | 0.733 | 0.867 | 0.077 |
| `en_twin` | 0.900 | 0.700 | 0.300 |
| `vitamins_tr` | **1.000** | 0.800 | 0.900 |
| `amazon_hpc_en` | 0.850 | 0.550 | 0.188 |

Every `vitamins_tr` `pairwise` question was answerable with no context at all,
because the entity axis inherited the corpus's brand ranking while only the
*label* axis was prior-randomized — and it got **worse with length**, since a
longer haystack converges on corpus proportions. Fixed by per-haystack entity
jitter plus prior-matched candidate sets (D9); all entity families now pass. One
flag remains in the committed record and is stated rather than buried:
`en_intent` `most_common` scores a prior of 0.50 against a chance of 0.20
(p = 0.033, n = 10). By this section's own rule — per-family samples of 10–20
cannot certify a family — that is a small-sample flag, not a demonstrated
shortcut, and the `--certify` run at n in the hundreds is the governing test.
`manifests/quality_audit.json` is the committed record.

**(d) Surface style — the format solver** *(added 2026-08-25)*. A classifier using
**only** text length, whether the record ends in a period, and whether it contains
`!`/`?` — no words, no comprehension. It exists because the corpus, not the
builder, can encode the label in formatting:

| corpus | style-solver lift over majority |
|---|---|
| Turkish brand reviews (We-Bears) | **+12.0 pts** |
| Airline tweets (en twin) | +1.7 pts |
| `vitamins_tr` | +4.8 pts |
| `amazon_hpc_en` | +6.8 pts |

In We-Bears, `olumlu` records end in a period 99.2% of the time and average 9.2
words; `olumsuz` records 45.2% and 33.1 words. Note also that **0 of 262
duplicate-text groups carry conflicting labels**, against 17.1% for the
human-annotated airline twin — the signature of programmatic rather than human
labelling.

This does not make the benchmark grep-solvable: aggregation is still required.
What it breaks is the **cross-lingual** comparison, because the shortcut is
7× stronger on the Turkish half than on its English twin, so a model could score
well on Turkish by measuring sentence lengths instead of reading Turkish.
**Consequence:** the supplement pair (`vitamins_tr` ↔ `amazon_hpc_en`) is the
primary cross-lingual review pair — same domain, author-assigned star labels,
style-matched (+4.8 vs +6.8). The We-Bears pair ships as a secondary robustness
check with this caveat attached.

**(d) Surface format — the style solver** (`scripts/style_solver.py`). Classifies
every record using **only** length, whether it ends in a period, and whether it
contains `!`/`?` — no words at all — then aggregates and answers the real
questions with the frozen scorer. It exists because none of (a)–(c) can see a
corpus that encodes its labels in *formatting*: the leakage solver looks for
label words, the majority baseline at answer skew, the prior oracle at corpus
statistics.

The classic case is "long review = negative". It is present, mildly, in most
review corpora, and severely in one:

| source | longest class | shortest class | spread |
|---|---|---|---|
| Turkish brand reviews | olumsuz 33.1 w | olumlu 9.1 w | **3.6x** |
| `vitamins_tr` | olumsuz 15.0 w | olumlu 9.8 w | 1.5x |
| Airline tweets | negative 19.8 w | positive 14.1 w | 1.4x |
| `amazon_hpc_en` | **positive** 46.9 w | negative 41.8 w | 1.1x |

A format-solvable corpus still yields a valid aggregation task — the model must
classify every record and add up the results either way. What it stops being is a
test of reading the *language*. So the number to watch is not either half's lift
but **the gap between the twin's halves**, because an asymmetric bias means a
model can score on the Turkish half by measuring sentence lengths:

| pair | asymmetry |
|---|---|
| intent, record-matched | **0.015** |
| review pair (b), supplements | **0.017** |
| intent, token-matched | 0.033 |
| review pair (a), brand reviews / airline | **0.108** |

Pair (b) and the record-matched intent pair are the clean ones; pair (a) is the
outlier and is labelled as secondary in `DATACARD.md` for this reason. All eight
sets pass the gate (no set exceeds +0.15 mean lift over majority), and
`manifests/style_audit.json` is the committed record.

**One family fails this solver everywhere.** `shift` is the only family with a
positive lift on any set: **+0.400** (`amazon_hpc_en`), **+0.300** (`en_twin`,
`vitamins_tr`), +0.100 (`en_intent`). Its majority baseline is already the
highest in the suite (mean 0.61; 0.73 on `tr_oolong`). A binary rose/fell over
positional halves is simply too coarse. See §10.

**Questions must be answerable only by aggregating.** The same audit measures how
much of the haystack determines each answer. The median `tr_oolong` `pairwise`
question used to rest on **8 records out of 3,919**, with a margin of 2 — that is
needle-in-a-haystack retrieval with a coin-flip tiebreak, the task this benchmark
exists to replace. Depth and margin floors are now enforced in both ground-truth
paths, and 95–100% of shipped questions clear them.

**Certify the generator, not the sample.** At n = 13 the `tr_oolong` `pairwise`
prior measured 0.85; at n = 235 distinct draws it measured 0.53. Per-family
samples of 10–20 cannot certify a family, so the audit runs on hundreds of
deduplicated candidate draws.

**Label-leakage asymmetry (why the twin matters).** The filter's drop rate is
itself the cross-lingual measurement, taken on the source corpora before anything
is built:

| Corpus | Leaking records | Rate |
|---|---|---|
| MASSIVE **tr**-TR (intent) | 0 / 16,521 | **0.00%** |
| MASSIVE **en**-US (intent) | 112 / 16,521 | **0.68%** |
| Turkish brand reviews | 341 / 40,597 | 0.84% |
| Amazon H&PC (en) | 560 / 60,000 | 0.93% |

On the intent axis the asymmetry is total: English surface text leaks the label
("play music" ⇒ `play_music`) while Turkish morphology never surfaces it once in
16.5K utterances. Since the two locales are the same utterances, the filter is
applied as a **union** over the pair.

**Maximum length is derived, not chosen.** A haystack of R records over K classes
gives each class a 1/K share on average, so a class can top the ranking only if
the pool can supply more than R/K of it. The smallest class caps the haystack at
**R_max = min_class_pool × K** records. The builder computes the ceiling per set,
warns above 0.85×, and records it in the manifest under `ranking_feasibility`.

**Morphology at the tokenizer.** Measured directly by the record-matched twin: at
identical record counts Turkish costs **1.30–1.34×** the tokens of English under
Qwen3-8B. This separates "harder to tokenize" from "harder to reason about."

## 5. What ships

| set | lang | classes | tiers | haystacks | questions | longest |
|---|---|---|---|---|---|---|
| `tr_intent` | tr | 48 | 50K / 100K | 10 | 120 | 99,998 |
| `en_intent` | en | 48 | 50K / 100K | 10 | 120 | 99,871 |
| `tr_intent_paired` | tr | 48 | 3K rec / 6K rec | 10 | 120 | 99,057 |
| `en_intent_paired` | en | 48 | 3K rec / 6K rec | 10 | 120 | 75,187 |
| `tr_oolong` | tr | 3 | 100K / 250K / 500K | 15 | 174 | 494,505 |
| `en_twin` | en | 3 | 50K / 100K | 10 | 111 | 98,321 |
| `vitamins_tr` | tr | 3 | 100K / 250K / 500K / 750K | 20 | 235 | 744,132 |
| `amazon_hpc_en` | en | 3 | 100K / 250K / 500K / 1M | 20 | 234 | 986,533 |

**1234 questions over 105 haystacks**, eight instance sets. Realized
haystack lengths are within 0.97–1.00 of target on every set (D14); each
manifest records `n_tokens`, `n_chars`, and per-tier haystack overlap.

`tr_intent_paired` / `en_intent_paired` are sized in **records**, not tokens —
that is what makes them record-identical across languages (§1). Their token
counts therefore differ by language, and that difference is the measurement.

## 6. Reproducibility

- **Single seed.** All randomness derives from one string seed
  (`{seed}-{lang}-{target}-{k}`); rebuilds are byte-identical. Row order is
  canonicalized before every sampling step, so engine-level parallelism cannot
  perturb output.
- **Cross-platform.** Verified at v0.3.0: every set rebuilds manifest-identical on
  macOS/arm64 from an original built on Windows/x86 — same pinned versions, same
  bytes, including every per-haystack record. Every source corpus has a fetch
  script under `scripts/`, so the rebuild starts from the public datasets rather
  than from a local file.
- **Differential-tested ground truth.** Each answer is computed by a Polars path
  and an independent pure-Python path and asserted equal — the strongest validity
  claim in the pipeline. Extended to every family, including the depth and margin
  floors, so a question cannot ship unless both paths agree it is answerable.
- **Frozen metric.** `src/scoring.py` reports `exact`, `partial`
  (`0.75^|y-ŷ|`, identical to Oolong's formula so scores are comparable) and
  `relative` (scale-free). `partial` is degenerate at this benchmark's
  magnitudes — `count` answers have a median near 1,000 and reach 12,000, and
  `0.75^50 ≈ 6e-7` — so it is kept only for comparability and `relative` carries
  the signal. Do not edit this file after the first model run.
- **Manifest.** Records version, config, source hash, reference tokenizer,
  proportion unit, per-haystack drift target + detectability flag, and the
  realized question-family distribution.
- **Rebuild command** (per config):

  ```bash
  python src/build_tr_oolong.py --config configs/tr_intent.json --audit   # inspect first
  python src/build_tr_oolong.py --config configs/tr_intent.json --build
  ```

  Build every set and the combined index (run from repo root):
  ```bash
  python src/build_tr_oolong.py --config configs/*.json --build \
      --index manifests/benchmark_index.json
  ```

- **Acceptance gates** — a rebuild is not accepted until all four pass:

  ```bash
  python tests/test_golden.py                        # build is deterministic
  python scripts/trivial_baseline.py --sets *_out    # leakage + majority baselines
  python scripts/quality_audit.py                    # prior oracle, depth/margin, pair check
  python scripts/verify_release.py                   # the written files are what they claim
  ```

  `verify_release.py` is deliberately independent of the builder: it re-reads the
  shipped `questions.jsonl` and meta parquets and **recomputes every answer with
  an implementation that shares no code path with `src/`**, then compares
  byte-for-byte. It also re-searches the shipped haystack text for label leakage,
  checks char offsets, and refuses stale or orphaned files. The build-time
  dual-path check cannot catch a serialization bug; this can.

## 7. Scaling to many datasets (N Turkish + M English)

A dataset is a **config file, not code**. To span N Turkish and M English source
datasets you write N+M configs — each naming a `source_path`, `text_col`,
`label_col`, and (optionally) `entity_col` — and build them in one command:

```bash
python src/build_tr_oolong.py --config configs/*.json --build --index manifests/benchmark_index.json
```

This writes each set to its own `out_dir` and a combined `benchmark_index.json`
(per-set language, source, question count, family distribution, and the total).
Adding a source never touches the builder.

**A new source is calibrated, not assumed.** The difficulty floors that make
questions non-trivial are necessarily axis-specific: values tuned on a 3-class
label space reject *every* ranking draw on an 18-class one. Three mechanisms
handle this so it is not a judgement call:

- `--audit` measures the source before you build it — class balance and
  imbalance, entity concentration, the **observed adjacent-rank gaps across three
  trial haystacks**, and **recommended `min_rank_margin` / `min_answer_count`** —
  plus the chance rate each family hands a solver for free.
- The builder prints a loud `[starved]` warning when a family produces zero
  questions. This was a silent failure: an 18-class source lost `most_common`,
  `least_common` and `second_most` entirely while the quota spilled into
  `count`/`proportion`, and nothing said so.
- `scripts/quality_audit.py` **auto-discovers** every built set from `configs/`,
  so a new source cannot be omitted from the acceptance gate.

The leakage filter, nesting detection, proportion unit, length ceiling, entity
jitter, and prior-neutral candidate selection are all automatic and need no
per-source configuration.

Sources may be `.parquet`, `.csv`, **or `.jsonl`**, i.e. any file with a text
column and a label column. Should OOLONG release its validated English splits
(`{"input","label"}` lines), they would drop straight in as extra anchor sets with
no code change:

```json
{ "source_path": "oolong/.../validated_data/agnews_validated.jsonl",
  "text_col": "input", "label_col": "label", "entity_col": "",
  "language": "en", "reference_tokenizer": "Qwen/Qwen3-8B", "out_dir": "agnews_out" }
```

Adding a source is a config file, so "more datasets" is a scaling knob rather than
a rewrite.

## 8. Extending: adding a question type

A question family is logic, not data, so a new one is a small, localized change to
`src/build_tr_oolong.py`:

1. a template in `Q_TEMPLATES` (both languages),
2. a branch in **both** `gt_primary` (Polars) and `gt_check` (pure Python) —
   the dual-path discipline is enforced, so a new family cannot ship without an
   independent oracle,
3. a generator branch in `_make_one` (its own rejection sampling, including a
   depth floor and a margin floor — see D9),
4. registration in `generate_questions` (and `SINGLETON_FAMILIES` if only one such
   question is meaningful per haystack), and
5. a chance rate in `scripts/quality_audit.py`. Getting this wrong is not a
   detail: scoring `top_k` against chance = 0 flagged an at-chance family as
   broken, when ordering 3 of 5 named candidates has chance 1/60.

The `most_common` / `least_common` / `second_most` families were added exactly this
way. The invariant to preserve: every answer is computed twice and asserted equal.

## 9. OOLONG vs TR-OOLONG — a full comparison

**Checked against the OOLONG paper and repository, 2026-08-25.** Its release
checklist still lists the Oolong-synth construction code, the validated source
splits, the scoring scripts and the analysis scripts as not yet released; the
repo currently ships an example inference script. So there is no upstream
pipeline to call, and nothing of theirs is vendored here. What is taken is from
the paper.

### Scale and shape

| | OOLONG | TR-OOLONG |
|---|---|---|
| languages | English | **Turkish + record-matched English** |
| splits | `oolong-synth` (6.5K q), `oolong-real` (10.8K q) | 8 sets, **1,234 questions**, 105 haystacks |
| sources | 10 classification datasets (Spam, TREC-QC, AGNews, App Reviews, Pavlick Formality, IMDB, HiTZ Negation, Yahoo Topics, MultiNLI, Metaphors) + CRD3 D&D transcripts | 6 corpora over 2 axes (MASSIVE intent; four review/sentiment sets) |
| label space | 2–10 classes | **3 and 48** |
| context lengths | synth: powers of 2, 1K–4M (reporting focused at 8K–128K); real: 55K–1.3M | **50K / 100K / 250K / 500K / 750K / 1M** |
| largest built haystack | — | **986,533 tokens** (`amazon_hpc_en`), 22,259 records |
| records per haystack | not reported | 1,523 – 22,259 |
| entity axis | synthetic user IDs attached to records | **real brands and airlines**, orthogonality measured (normalised MI 0.022 on `vitamins_tr`) |
| temporal axis | **real dates, month/year granularity** | positional halves only |
| numeric metric | `0.75^\|y-ŷ\|` | same, **plus** `relative` = `max(0, 1 - \|y-ŷ\|/max(y,1))` |
| shortcut auditing | not reported | **4 solvers, committed manifests** |
| ground truth | derived from source labels | same, **computed twice by independent code paths and asserted equal** |

### Question families, one by one

`✓` implemented, `✗` absent, `≈` present in weaker form, `+` ours only.

| OOLONG-synth template | TR-OOLONG family | | note |
|---|---|:---:|---|
| **Counting** | | | |
| Which label is the most common? | `most_common` | ✓ | candidates always named, so the question is well posed |
| Which label is the least common? | `least_common` | ✓ | needed a class-support floor to de-trivialise (D3) |
| How many points have label X? | `count` | ✓ | counts here are ~1,000 vs ~100 in OOLONG |
| Is label A more/less/equally common than B? | — | ✗ | **gap**: our `pairwise` compares *entities*, not labels |
| **User** | | | |
| Among these users, who has most of label X? | `entity_argmax` | ✓ | entity is a real brand, not synthetic metadata |
| Who has more of label X, A or B? | `pairwise` | ✓ | |
| Filter by user subset | `entity_count` | ✓ | |
| Which user appears most / second-most often? | — | ✗ | **gap**: no label-free entity-frequency family |
| **Timeline** (OOLONG's hardest group) | | | |
| Was label X more common before or after date T? | `shift` | ≈ | **weaker**: positional halves, not real dates |
| Which date appears most / second-most often? | — | ✗ | **gap**: no date field in any source |
| How many dates appear exactly *n* times? | — | ✗ | **gap** |
| In which month did label A first exceed B? | — | ✗ | **gap** |
| For how many months is A more frequent than B? | — | ✗ | **gap** |
| For how many months is X the single most frequent? | — | ✗ | **gap** |
| **Ours only** | | | |
| — | `proportion` | + | normalised share (percent, or per-mille when >10 classes) |
| — | `second_most` | + | OOLONG has second-most *user* and *date*, not *label* |
| — | `top_k` | + | ordered top-*k* entities; chance 1/60 |

Their task identifiers are `MOST_FREQ`, `LEAST_FREQ`, `RELATIVE_FREQ`,
`NUMERIC_ONE_CLASS`, `REPRESENTED_N_TIMES`. `second_most` is an **extension, not
a mirror**.

### Where TR-OOLONG is harder, and where it is easier

Harder on three axes. The label space reaches **48 classes** against their 2–10.
Haystacks reach **1M tokens and 22,259 records** against a reporting focus at
128K. And counts are large enough that their partial-credit metric degenerates:
with a median `count` answer near 1,000 and a maximum of 12,225, `0.75^50 ≈ 6e-7`,
so `partial` collapses to exact match and a model off by 2% scores the same as
one off by 100%. That is why `relative` was added, and why both are reported.

**Easier on one axis, and it is the one they say matters most.** OOLONG reports
timeline questions as consistently their hardest type. TR-OOLONG reduces that
whole group to a single binary `shift` over positional halves, which has the
weakest floor in the suite (mean majority baseline 0.61, 0.73 on `tr_oolong`) and
is the only family the format solver beats (§4d). **Closing this is the single
highest-value extension.** It is blocked on data, not on code: `app_reviews` and
Amazon-Reviews-2023 carry real dates, but no Turkish source examined does, so a
*parallel* timeline axis is not currently buildable. See `PAIRING_SEARCH.md`.

## 10. How the pipeline was built

The order below is the actual order, and each step exists because the previous
one turned out to be insufficient. The method generalises to any language pair.

1. **Pick a labelled corpus, not a text corpus.** The whole design rests on
   ground truth being derivable, so a raw corpus (Havadis, 745K Turkish news
   articles) is useless no matter how large. The label *is* the answer key.
2. **Screen the source before building anything.** `--audit` reports class
   balance, the entity axis, the derived length ceiling, and the surface shape
   per class. A source that fails here cannot be rescued later.
3. **Derive the ceiling, do not choose it.** With *K* classes, a class can top a
   ranking only if the pool can supply more than *R/K* of it, so
   `R_max = smallest_class × K` records. Exceeding it makes ranking families
   unanswerable. The builder computes it, warns above 0.85x, and records it.
4. **Drop the tail.** Classes below `min_class_support` are removed, because a
   class too small to be sampled competitively is deterministically rarest in
   every haystack and `least_common` becomes free (D3).
5. **Filter leakage as enforcement, not assumption.** Any record containing any
   label's surface form is dropped, over the whole label space. The assumption
   that this was unnecessary was false: 0.84% leaking records were enough to
   give a substring solver 73% on `most_common` against 33% chance.
6. **Randomise the prior.** Per-haystack label proportions are drawn from a
   Dirichlet, and entity candidate sets are prior-matched and jittered, so the
   answer cannot be recovered from corpus-level statistics.
7. **Compute every answer twice.** Two independent code paths, asserted equal.
   This is what makes "no manual annotation" safe rather than merely cheap.
8. **Run four solvers and ship only what survives.** Leakage, majority skew,
   corpus priors, surface format. Each was added *after* a version of the
   benchmark was found solvable by it. A family that fails on a given source is
   switched off for that source and the omission is recorded, not hidden.
9. **Certify the generator, not the sample.** At n = 13 the `tr_oolong`
   `pairwise` prior measured 0.85; at n = 235 it measured 0.53. Per-family
   samples of 10–20 cannot certify anything, so `--certify` runs on hundreds of
   deduplicated draws.
10. **Freeze the scorer before any model runs**, and make every build
    byte-identical from a single seed, with a full manifest.

**For a new language pair, steps 1–2 are the entire difficulty.** The code is
language-agnostic; finding two corpora that match on task, label provenance,
record length and surface shape is the work.

## 11. Choosing a twin: what a good pairing looks like

The cross-lingual claim is only as good as the pairing. Four criteria, in order
of how often they are the binding constraint:

1. **Same label provenance.** Both halves' labels must be produced the same way.
   Author-assigned star ratings on both sides is the strongest available option,
   because the person who wrote the text assigned the label.
2. **Comparable record length.** A 4x length mismatch changes what "one chunk"
   means and interacts with every compression measurement.
3. **Comparable surface shape.** Measured by §4d. The *gap* matters, not the level.
4. **Both halves reach the same length tiers.** `R_max = smallest_class × K`.

### Worked examples

| pairing | provenance | length | style gap | verdict |
|---|---|---|---|---|
| **MASSIVE tr-TR ↔ en-US** | identical, same utterances | identical by construction | **0.017** | **best available.** The only true record-matched twin; 110/120 questions share a gold answer |
| **`vitamins_tr` ↔ `amazon_hpc_en`** | author's stars, both | 12.1 vs 44.8 w (3.7x) | **0.015** | **ships as primary review pair.** Length mismatch is its one weakness |
| Turkish brand reviews ↔ airline tweets | undocumented vs CrowdFlower humans | 24.2 vs 15.7 w | **0.108** | **secondary only.** Mismatched provenance and a 7x surface-shape asymmetry |
| MüşteriYorumları ↔ Amazon Home & Kitchen | author's stars, both | 13.2 vs 71.8 w (5.4x) | 0.106 | rejected: no Amazon category is terse enough |
| `vitamins_tr` ↔ `app_reviews` | author's stars, both | 12.1 vs 18.8 w (1.6x) | 0.021 | best length match found, but no better than the pair in use |
| SIB-200 tur ↔ eng | identical, parallel | identical | — | **structurally dead**: 1,004 rows total, ~14K token ceiling |
| XNLI tr ↔ en | identical, parallel | identical | — | **structurally dead**: 7,500 human-translated rows; the 393K train split is machine-translated |

**The lesson from the last two rows is worth stating plainly.** Parallel corpora
give a record-matched twin for free, which is the strongest possible design, but
human translation is expensive so they are all small, and this benchmark needs a
large pool for independent draws at 100K–1M tokens. MASSIVE, at 16.5K parallel
utterances, is the largest such Turkish resource in existence and it is already
used here. Full search in `PAIRING_SEARCH.md`.

## 12. Repository layout

```
tr-oolong/
├── README.md
├── ROADMAP.md          # tracked checklist — this is where progress lives
├── DESIGN_DECISIONS.md # why the benchmark is built this way, with the evidence
├── DATACARD.md         # per-axis source, license, label-noise, construction
├── LICENSE             # MIT (code); data licenses in DATACARD
├── CHEATSHEET.md       # vocabulary, workflows, and what the golden test is for
├── src/build_tr_oolong.py
├── src/scoring.py      # FROZEN metric
├── scripts/quality_audit.py   # prior-oracle + depth/margin acceptance gate
├── scripts/trivial_baseline.py
├── scripts/publish_hf.py      # per-subset licensing for release
├── scripts/make_readme_figs.py
├── configs/            # one config per instance set
├── manifests/          # committed manifest.json per set (post-rebuild)
├── examples/           # a real sample question set
└── data/               # git-ignored; distributed via Hugging Face
```

Data is **not** committed (the largest instance file exceeds GitHub's 100 MB
limit). The repo ships code + configs + manifests, which reproduce every set by
construction.

**Release and licensing.** The six source corpora carry five different licenses,
and two of them do not permit redistributing their text. `scripts/publish_hf.py`
packages each set as its own Hugging Face config with its own license tag, and
ships `en_twin` and `amazon_hpc_en` as questions-and-answers only — their
haystacks are rebuilt locally from the public source, byte-identically. Full
table in `DATACARD.md`. `LICENSE` (MIT) covers **code only**.


## 13. Limitations, stated before anyone asks

**Contamination resistance (a strength, stated because it will be questioned).**
Every source corpus is public and almost certainly in the pretraining data of any
model evaluated here. That is *not* a threat to this benchmark, and the reason is
structural: no question asks about a fact that exists in the corpus. It asks how
many records carrying a latent label appear in **one specific random sample**,
whose composition is decided by a seed at build time. Memorising MASSIVE tells a
model nothing about how many `play_music` utterances landed in haystack
`tr-100000-3`. Synthetic aggregation over resampled public data is
contamination-resistant by construction — unlike a QA benchmark, where the answer
is a corpus fact.

**Source label noise is a per-family ceiling, and the rate itself is still
unmeasured.** Every answer is exact *with respect to the haystack*, but the
haystack's labels come from the source corpus, so a model classifying *better*
than the annotators is scored wrong. What has been settled is how much that
matters, which turns out to be family-dependent. Under the OOLONG metric
`0.75^|y-ŷ|`, with symmetric flips at rate ε, a semantically perfect oracle scores:

| family | ε=2% | ε=5% | ε=10% |
|---|---|---|---|
| `count`, N=3,919 (100K tier) | 0.36 | 0.25 | 0.19 |
| `count`, N=9,873 (500K tier) | 0.26 | 0.18 | 0.13 |
| `proportion` (percent), N=3,919 | — | 0.95 | 0.92 |
| `most_common` / `pairwise` / `top_k` | P(answer flips) < 1e-6 at every N and ε tested |

Ranking families are effectively immune: the builder enforces a 10% gold margin
while noise drift grows only as √(Nε). `proportion` is robust. **Raw `count` is
not** — at the 100K tier even 2% noise caps a perfect model at 0.36, which is a
second, independent reason to read `relative` rather than `partial`. So the open
item is narrower than before: measure ε per corpus (n = 400 gives ±3 pts at
ε ≈ 0.10) and record it in `DATACARD.md`. Headline results are reported on
ranking and `proportion`.

**`shift` is the weakest family and should be read with that in mind.** It is a
binary rose/fell over positional halves, so its floor is the highest in the suite
(mean majority baseline 0.61; 0.73 on `tr_oolong`), and it is the only family the
surface-format solver beats: +0.400 on `amazon_hpc_en`, +0.300 on `en_twin` and
`vitamins_tr`, +0.100 on `en_intent` (§4d). Length correlates with label, and
length also correlates with position once drift is injected, so format alone
partly recovers the direction. The fix is a real dated timeline axis of the kind
OOLONG has, which is blocked on data rather than code: no Turkish source examined
carries dates (see §9 and `PAIRING_SEARCH.md`). **Until then, do not report
`shift` as a headline result.**

**Haystacks within a length tier are not independent.** They are drawn
independently from the same pool, so at the longest tiers — where one haystack
consumes 15–35% of the pool — they necessarily share records. Ground truth is
unaffected (it is computed from the actual haystack), but per-tier variance is
understated and the effective sample size is below five. Rather than assert this,
every manifest records `tier_overlap`: the mean and max Jaccard between the
haystacks of each tier, and the pool fraction each one consumes. Measured at each
set's worst tier:

| set | worst tier | mean Jaccard | pool consumed per haystack |
|---|---|---|---|
| `vitamins_tr` | 750K | 0.378 | 0.536 |
| `tr_oolong` | 500K | 0.281 | 0.379 |
| `tr_intent` | 100K | 0.279 | 0.403 |
| `amazon_hpc_en` | 1M | 0.213 | 0.310 |
| `en_twin` | 100K | 0.110 | 0.221 |

Overlap is negligible at the shortest tiers (`tr_oolong` 100K: J=0.052) and grows
with length, so treat long-tier variance as understated. Prefer more haystacks
over more questions per haystack when adding statistical power.

**Per-family n is 7–20.** The *generator* is certified at high power
(`quality_audit.py --certify` draws hundreds of deduplicated candidate
questions), but the shipped sample cannot support a strong per-family
cross-lingual claim on its own. The record-matched twin partly compensates by
making the comparison paired rather than between two independent samples.

**Lengths are measured with one tokenizer.** All tiers are sized under
Qwen3-8B. A "500K-token" haystack is not 500K tokens for a model with a
different tokenizer, and for Turkish the discrepancy is large (§4). Every
haystack therefore records `n_chars` alongside `n_tokens`, so lengths can be
re-derived for another tokenizer without rebuilding. Always report the tokenizer
alongside a length claim.

**The haystack is a concatenation, not a document.** Records are joined by a
separator, so the text has no discourse structure. This is inherited from
OOLONG-synth deliberately — it is what makes ground truth exact — but it means
results here do not transfer directly to naturally long documents. That is the
gap OOLONG-real addresses and this benchmark does not.

**Distribution shift is injected, not observed.** `shift` questions rely on a
deliberate over-representation of one label in the second half. The target and a
detectability flag are recorded per haystack (`drift_target`, `drift_ok`).

**Question wording is templated.** As with every synthetic benchmark, a model
could in principle overfit to the phrasing. Mitigated by ten families across two
languages, and by the set being evaluation-only — nothing here is for training.

**The retained review pool is not representative Turkish.** 38% of the We-Bears
corpus carries multi-aspect labels and is dropped, because ground truth needs one
label per record. The remainder skews shorter and more negative. Aggregate
answers stay exact for the built haystack, which is all any question asks about —
but no claim should describe this pool as representative of Turkish review text.

## References

- Bertsch et al. (2025), *OOLONG*, arXiv:2511.02817 — construction principle.
- Zhang, Kraska & Khattab (2026), *Recursive Language Models*, arXiv:2512.24601 — the thesis method under evaluation.
