# TR-OOLONG

The first Turkish long-context **aggregation** benchmark, with a matched English
twin built by the identical pipeline. It follows the OOLONG-synth construction
principle (Bertsch et al., 2025): concatenate examples from an existing *labeled*
dataset into a 50K–500K-token haystack, then auto-generate distributional
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
| **Review / sentiment** | Two TR–EN corpus pairs: (a) Turkish brand reviews + EN airline tweets; (b) Turkish vitamin/supplement reviews + EN Amazon Health & Personal Care | sentiment (3) | brand / airline — *orthogonal* | length scaling to 500K; entity-relational reasoning; cross-corpus robustness |
| **Intent** | Amazon MASSIVE (tr-TR / en-US, parallel-translated) | intent (49) | scenario (18) — *nested* | label-space difficulty; by-construction cross-lingual control |

MASSIVE ships 60 intents, but 11 of them have too few examples to ever be
sampled competitively — with 6 rows in a 16.5K-row corpus, `cooking_query` was
the rarest label in *every* haystack, which made `least_common` answerable from
corpus priors without reading the context at all. Classes below a support floor
(`min_class_support`, 100 rows) are dropped from the pool, and the cut is taken
over the *union* of both locales so the twin keeps an identical label space.
See §4.

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
| `entity_argmax` | which group has the most X | ✓ | — nested |
| `top_k` | the k groups with the most X, ordered | ✓ | — nested |
| `pairwise` | which of A or B has more X | ✓ | — nested |

The `most_common` / `least_common` / `second_most` family mirrors the OOLONG-synth
counting typology (`most_common_label`, `least_common_label`, `second_most_freq`),
so the "we implement their typology and extend it" claim is concrete. Each is a
single-question-per-haystack family (like `shift`): asking twice adds nothing.

## 3. Example questions (produced by the actual builder)

Every answer below is computed from the source labels by two independent code
paths and asserted equal (see §5).

**Review axis** (orthogonal brand entity), from `tr_oolong_out/questions.jsonl`:

- `entity_count` — *"'biletix' markası hakkındaki yorumlardan kaç tanesi 'olumlu'? Sadece sayıyı yaz."* → **7**
  (count of records whose sentiment=olumlu among records whose brand=biletix)
- `entity_argmax` — *"En çok 'olumlu' yorumu alan marka hangisi? Sadece marka adını yaz."* → **apple**
  (brand with the highest positive count; ties rejected)
- `top_k` — *"En çok 'olumlu' yorumu alan ilk 3 marka hangileri? Çoktan aza doğru, aralarına ' > ' koyarak yaz."* → **apple > stanley > a10**
  (top-3 brands by positive count; rejected unless the top-4 boundary is strictly ordered)
- `pairwise` — *"'olumlu' yorumu hangisinde daha çok: 'ziraat bankası' mı yoksa 'arçelik' mi? Sadece marka adını yaz."* → **ziraat bankası**
  (whichever brand has more positives; ties and zeros rejected)

**Intent axis, Turkish** (nested; proportion switches to per-mille above 10 classes),
from `tr_intent_out/questions.jsonl`:

- `count` — *"Bu kayıtlarda kaç tane 'transport_ticket' etiketli kayıt var? Sadece sayıyı yaz."* → **62**
- `proportion` — *"Kayıtların binde kaçı 'qa_stock' etiketli? En yakın tam sayıya yuvarla, sadece sayıyı yaz."* → **31** (per-mille)
- `shift` — *"Kayıtların ikinci yarısında 'qa_currency' etiketli kayıtların oranı ilk yarıya göre arttı mı azaldı mı? 'artti' veya 'azaldi' yaz."* → **azaldi**

**Intent axis, English** (the matched twin — same utterances, translated),
from `en_intent_out/questions.jsonl`:

- `count` — *"How many utterances have the intent 'social_query'? Answer with the number only."* → **73**
- `proportion` — *"How many per thousand (per-mille) of records are labeled 'iot_hue_lightdim'? Round to the nearest integer, answer with the number only."* → **13**
- `shift` — *"Did the share of utterances with the intent 'play_radio' rise or fall in the second half compared to the first? Answer 'rose' or 'fell'."* → **rose**

A real sample question set is committed at `examples/sample_questions_review.jsonl`.

## 4. Construct validity

**Grep-proofness (enforced, not assumed).** The question asks about a latent
*label*, and no record contains any label's surface form — records that do are
dropped at build time (`drop_label_leakage`, on by default; the check is over
the whole label space, not just the record's own label). This is enforcement
rather than an assumption because the assumption was false: before the filter, a
solver that did nothing but substring-search three Turkish words across a 500K-token
haystack recovered `most_common` on `tr_oolong_out` **73%** of the time
(chance 33%). The Turkish sentiment labels `olumlu` / `olumsuz` are ordinary
Turkish words that appear in review prose and correlate with the true majority;
`nötr` never appears, so it was always ranked last. After filtering, that same
solver scores **0.133**.

Note the size of the effect versus its frequency: only 0.84% of source records
leaked, and that was enough to determine the argmax over three classes, because
the leaks correlate with the gold label. Leakage *rate* is not a safe proxy for
exploitability — which is why the shortcut is now removed at the source rather
than reported as a floor.

**Label-leakage asymmetry (why the twin matters).** The filter's drop rate is
itself the cross-lingual measurement, taken on the source corpora before
anything is built:

| Corpus | Leaking records | Rate |
|---|---|---|
| MASSIVE **tr**-TR (intent) | 0 / 16,521 | **0.00%** |
| MASSIVE **en**-US (intent) | 112 / 16,521 | **0.68%** |
| Turkish brand reviews | 341 / 40,597 | 0.84% |
| Amazon H&PC (en) | 560 / 60,000 | 0.93% |

On the intent axis the asymmetry is total: English surface text leaks the label
("play music" ⇒ `play_music`) while Turkish morphology never surfaces it once in
16.5K utterances. On the review axis the rates are comparable, because there the
label names are ordinary sentiment words in *both* languages. Since the two
locales of MASSIVE are the same utterances, the filter is applied as a **union**
over the pair — dropping only the English side would bias the twin toward the
language that leaks less.

**Shortcut floor vs. answer skew.** `scripts/trivial_baseline.py` reports two
numbers per family: the leakage solver's score and the **majority baseline** (the
score of always emitting the most frequent gold answer). They must be read
together. Once leakage is filtered, the leakage solver's label masks are all
zero and it degenerates to a *constant* predictor, so its score measures
gold-answer skew, not an exploitable shortcut. Only a leakage score meaningfully
above the majority baseline is real leakage; across all six sets there is
currently none.

**Morphology at the tokenizer.** At equal token budgets, the Turkish intent axis
holds fewer utterances than English (≈11 vs ≈7 tokens/utterance under Qwen3-8B) —
a measurable effect that separates "harder to tokenize" from "harder to reason
about," feeding the Turkish-vs-English degradation analysis.

## 5. Reproducibility

- **Single seed.** All randomness derives from one string seed
  (`{seed}-{lang}-{target}-{k}`); rebuilds are byte-identical. Row order is
  canonicalized before every sampling step, so engine-level parallelism cannot
  perturb output.
- **Cross-platform.** Verified: all six sets rebuild manifest-identical on
  macOS/arm64 from an original built on Windows/x86 — same pinned versions, same
  bytes, including every per-haystack record. Every source corpus has a fetch
  script under `scripts/`, so the rebuild starts from the public datasets rather
  than from a local file.
- **Differential-tested ground truth.** Each answer is computed by a Polars path
  and an independent pure-Python path and asserted equal — the strongest validity
  claim in the pipeline. Extended to every family, including `top_k` and
  `pairwise`.
- **Manifest.** Records version, config, source hash, reference tokenizer,
  proportion unit, per-haystack drift target + detectability flag, and the
  realized question-family distribution.
- **Rebuild command** (per config):

  ```bash
  python src/build_tr_oolong.py --config configs/tr_intent.json --audit   # inspect first
  python src/build_tr_oolong.py --config configs/tr_intent.json --build
  ```

  Build all six sets at once (run from repo root):
  ```bash
  python src/build_tr_oolong.py --config configs/tr_intent.json configs/en_intent.json configs/tr_oolong.json configs/en_twin.json configs/vitamins_tr.json configs/amazon_hpc_en.json --build --index manifests/benchmark_index.json
  ```

## 6. Scaling to many datasets (N Turkish + M English)

A dataset is a **config file, not code**. To span N Turkish and M English source
datasets you write N+M configs — each naming a `source_path`, `text_col`,
`label_col`, and (optionally) `entity_col` — and build them in one command:

```bash
python src/build_tr_oolong.py --config configs/*.json --build --index manifests/benchmark_index.json
```

This writes each set to its own `out_dir` and a combined `benchmark_index.json`
(per-set language, source, question count, family distribution, and the total).
Adding a source never touches the builder.

Sources may be `.parquet`, `.csv`, **or `.jsonl`** — which means OOLONG's own
validated English splits (`{"input","label"}` lines) are usable directly as part
of your M, giving their datasets plus your controls:

```json
{ "source_path": "oolong/.../validated_data/agnews_validated.jsonl",
  "text_col": "input", "label_col": "label", "entity_col": "",
  "language": "en", "reference_tokenizer": "Qwen/Qwen3-8B", "out_dir": "agnews_out" }
```

By contrast, OOLONG requires a hand-written `EvalDataset` subclass, a validated
split, and two hardcoded per-example token constants **per dataset**, registered
in a `supported` list — so N+M datasets means N+M Python classes. The config-driven
design is why "I don't want a small benchmark" is a scaling knob here, not a
rewrite.

## 7. Extending: adding a question type

A question family is logic, not data, so a new one is a small, localized change to
`src/build_tr_oolong.py`:

1. a template in `Q_TEMPLATES` (both languages),
2. a branch in **both** `gt_primary` (Polars) and `gt_check` (pure Python) —
   the dual-path discipline is enforced, so a new family cannot ship without an
   independent oracle,
3. a generator branch in `_make_one` (its own rejection sampling), and
4. registration in `generate_questions` (and `SINGLETON_FAMILIES` if only one such
   question is meaningful per haystack).

The `most_common` / `least_common` / `second_most` families were added exactly this
way. The invariant to preserve: every answer is computed twice and asserted equal.

## What we reuse from OOLONG

TR-OOLONG *inherits* the OOLONG-synth recipe and *keeps its own generator* (which
adds the Turkish handling, matched twin, entity axis, per-string Qwen length,
dual-path ground truth, and reproducible manifests). From the OOLONG repo we reuse:
its **validated English splits** as ready-made anchor datasets, its **scoring
script** so the frozen metric provably matches theirs, and its **question typology**
as the skeleton our families extend.

## 8. Repository layout

```
tr-oolong/
├── README.md
├── ROADMAP.md          # tracked checklist — this is where progress lives
├── DATACARD.md         # per-axis source, license, label-noise, construction
├── LICENSE             # MIT (code); data licenses in DATACARD
├── src/build_tr_oolong.py
├── scripts/make_readme_figs.py
├── configs/            # one config per instance set
├── manifests/          # committed manifest.json per set (post-rebuild)
├── examples/           # a real sample question set
└── data/               # git-ignored; distributed via Hugging Face
```

Data is **not** committed (the largest instance file exceeds GitHub's 100 MB
limit, and the review-axis text is license-gated). The repo ships code + configs +
manifests, which reproduce every set by construction; the datasets themselves are
distributed on Hugging Face (intent axis first). See `DATACARD.md`.

## References

- Bertsch et al. (2025), *OOLONG*, arXiv:2511.02817 — construction principle.
- Zhang, Kraska & Khattab (2026), *Recursive Language Models*, arXiv:2512.24601 — the thesis method under evaluation.
