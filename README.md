# TR-OOLONG

The first Turkish long-context **aggregation** benchmark, with a matched English
twin built by the identical pipeline. The nearest multilingual long-context
benchmark, ONERULER (arXiv:2503.01996), covers 26 languages and **Turkish is not
one of them**; its two aggregation tasks are also lexical (most-frequent-word
extraction), answerable by counting strings rather than by classifying each
record. The claim here is therefore two gaps wide: the language, and
latent-label aggregation rather than word counting. It follows the OOLONG-synth construction
principle (Bertsch et al., 2025): concatenate examples from an existing *labeled*
dataset into a 36K–1M-token haystack, then auto-generate distributional
questions whose ground truth is computed exactly from the source labels — no
manual annotation.

> ### ⚠️ Before writing anything about Turkish morphology
>
> The "Turkish costs 1.30–1.34x the tokens of English" figure below is measured
> under **one tokenizer**. It is not a property of the language. On the same
> 3,000 pair-aligned utterances the ratio is **2.16x** under GPT-2, **1.53x**
> under Qwen3-8B, **1.29x** under mBERT and **0.57x** under BERTurk — where
> Turkish is *cheaper* than English. It measures how much Turkish a tokenizer
> saw, not agglutination. See [`PAPER_NOTES.md`](PAPER_NOTES.md) §1 for how to
> state it correctly.

**Where to start.** [`PAPER_NOTES.md`](PAPER_NOTES.md) lists every claim worth
carrying into a write-up, and what must not be claimed yet.
[`REVIEW.md`](REVIEW.md) reads the project adversarially.
[`COMPARISON.md`](COMPARISON.md) explains OOLONG and
TR-OOLONG side by side with real questions from both, for a reader without the
code. §3 below shows every data source with real rows and how its labels are
derived. [`DATASET_REVIEW.md`](DATASET_REVIEW.md) records every Turkish source
considered and why each was kept or rejected.

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
Health & Personal Care) carries the entity axis; the e-commerce pair
(Hepsiburada/Trendyol ↔ Multilingual Amazon Reviews) is the cleanest on every
balance and shortcut measurement.

Two axes:

| Axis | Source | Label (classes) | Entity axis | Purpose |
|---|---|---|---|---|
| **Review / sentiment** | Two TR–EN corpus pairs: (a) Turkish vitamin/supplement reviews + EN Amazon Health & Personal Care; (b) Turkish e-commerce reviews + EN Multilingual Amazon Reviews | sentiment (3) | brand / airline — *orthogonal* | length scaling to 1M tokens; entity-relational reasoning; cross-corpus robustness |
| **Intent** | Amazon MASSIVE (tr-TR / en-US, parallel corpus) | intent (48) | scenario (18) — *nested* | label-space difficulty; by-construction cross-lingual control |

The intent axis is built **twice**, in two matching regimes, because they answer
different questions:

- **token-matched** (`tr_intent` / `en_intent`) — equal token budget. Turkish
  therefore holds ~25% fewer utterances. Asks *"at equal cost, which language
  degrades faster?"*
- **record-matched** (`tr_intent_paired` / `en_intent_paired`) — equal *record*
  count, same records, same order, same drift target. **100 of 120 questions have
  a byte-identical gold answer in both languages** (the other 10 are `shift`,
  where the same fact is written `arttı` / `rose`). Asks *"at equal content,
  which language degrades faster?"* — and admits **paired** tests (McNemar)
  rather than comparing two independent samples.

The difference between the two regimes is itself a measurement: at identical
record counts Turkish costs **1.30–1.34× the tokens of English** under Qwen3-8B,
stable across every haystack. **Name the tokenizer whenever quoting this.** The
ratio is that model's tokenization penalty on Turkish, not a morphology constant:
on the same aligned utterances it runs from **0.57×** (BERTurk, where Turkish is
cheaper) to **2.16×** (GPT-2). The record-matched regime carries no token-budget
confound at all and is the right anchor for a cross-lingual claim.

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
| `label_vs_label` | is label A more, less, or equally common than label B | ✓ | ✓ |
| `entity_count` | how many X-labelled records in group G | ✓ | — nested |
| `entity_argmax` | which **named candidate** group has the most X | ✓ | — nested |
| ~~`top_k`~~ | *(withdrawn in v0.5.0 — see below)* | — | — |
| `pairwise` | which of A or B has more X | ✓ | — nested |

**Every ranking question names its candidates.** `entity_argmax`, `top_k` and the
three label-ranking families list the options they range over. This is not a
convenience: it is what makes them (a) *well posed* — no model can be asked to
produce `iot_hue_lightoff` without being told such a label space exists — and
(b) *unanswerable from the corpus*, because the candidates are chosen to have
near-identical corpus-level counts, so only this haystack can rank them. See §4
and `DESIGN_DECISIONS.md` (D9, D10).

**`top_k` no longer ships, and the reason is worth keeping.** Exact ordering was
always the hardest family to make prior-neutral: flipping one position is easy to
randomize, permuting three independently is not. It stayed prior-correlated on
`vitamins_tr` and `amazon_hpc_en` (z = +5.5 and +3.7 under `--certify`) and
survived on one corpus only — the brand-review set, which was **withdrawn in
v0.5.0 over undocumented label provenance** (§3.5). Rather than ship a family
resting on a single source we no longer trust, `top_k` is withdrawn with it.
Restoring it needs a corpus with a clean licence, documented labels, and an
entity axis orthogonal to the label; none of the candidates surveyed in
`DATASET_REVIEW.md` has all three.

**`label_vs_label` (added v0.6.0) closes the last gap in OOLONG's counting
group.** It mirrors their "is A more common, less common, or the same frequency
as B", needs no entity column, and therefore ships on all eight sets. Two
properties are worth stating because they are not obvious:

- **The asked order is chosen, not inherited.** "A vs B → more" and "B vs A →
  less" state the same fact, so the builder picks the direction that realises a
  target outcome drawn uniformly. Without this the answers skewed to whichever
  way the label ranking happened to fall (majority baseline 0.71 on `marc_en`);
  with it the baseline sits at 0.50–0.60, in line with `shift`.
- **"Equal" is reachable only when the label space is large.** At 48 classes many
  labels carry similar counts and `the same` is the gold answer about half the
  time; at 3 classes with per-haystack Dirichlet priors the classes are far
  apart, no pair falls inside the 2% band, and the family is effectively binary.
  This is reported rather than forced — widening the band to manufacture ties
  would make the gold answer an artifact of the threshold.

A pair whose relative gap falls between the 2% "equal" band and the 10% margin
floor is **rejected**, not bucketed, so no gold answer here is a judgement call.

The `most_common` / `least_common` family mirrors the OOLONG-synth counting
typology; their actual task identifiers are `MOST_FREQ`, `LEAST_FREQ`,
`RELATIVE_FREQ`, `NUMERIC_ONE_CLASS` and `REPRESENTED_N_TIMES`. `second_most` is
an **extension, not a mirror** — OOLONG has second-most *user* and second-most
*date*, but no second-most *label*. Each is a
single-question-per-haystack family (like `shift`): asking twice adds nothing.

## 2.5 The pipeline, end to end

How a pair of raw corpora becomes a set of scored questions. Every gate is a
place where a candidate can be rejected, and most of them have rejected
something — the rejections are recorded in
[`DATASET_REVIEW.md`](DATASET_REVIEW.md).

```
┌─ STEP 1 ── FIND A TURKISH CORPUS ──────────────────────────────────┐
│  Must be LABELLED. A raw text corpus is unusable no matter how      │
│  large, because the label IS the answer key.                        │
│  Record where the label came from:                                  │
│     writer's own star rating  > professional annotation             │
│     > crowd annotation        > undocumented   ← reject             │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─ STEP 2 ── SCREEN IT, BEFORE BUILDING ANYTHING  (`--audit`) ────────┐
│  • class balance          imbalance ratio, normalised entropy       │
│  • length ceiling         R_max = smallest_class × K records        │
│                           if it cannot reach 500K, it cannot carry  │
│                           the length gradient                       │
│  • surface shape          mean words / period rate / !? rate per    │
│                           class. Spread ≥ 2.0x is flagged           │
│  • licence                redistributable? share-alike? unknown?    │
│                           "unknown" means no grant, not no problem  │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─ STEP 3 ── FIND ITS ENGLISH TWIN ───────────────────────────────────┐
│  Turkish is the scarce side, so never start from English.           │
│  Match on, in order of how often each binds:                        │
│     1. same label provenance   (stars↔stars, humans↔humans)         │
│     2. comparable record length                                     │
│     3. comparable surface shape — the GAP, not either level         │
│     4. both halves reach the same length tiers                      │
│     + licence veto: a closer match is not worth an unusable corpus  │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─ STEP 4 ── BUILD BOTH HALVES ───────────────────────────────────────┐
│  drop records leaking any label's surface form  (enforced, not      │
│     assumed — 0.84% leakage once gave a solver 73% vs 33% chance)   │
│  drop classes below min_class_support                               │
│  sample with a Dirichlet-randomised prior, per haystack             │
│  inject drift into the second half so `shift` has signal            │
│  concatenate to the token target, measured with a real tokenizer    │
│  generate questions; compute every answer TWICE, by two             │
│     independent code paths, and assert they agree                   │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─ STEP 5 ── FOUR ACCEPTANCE GATES ── all must FAIL to solve it ──────┐
│  (a) leakage solver     can substring search answer it?             │
│  (b) majority baseline  is one answer always right?                 │
│  (c) prior oracle       answerable from corpus stats, no context?   │
│  (d) format solver      answerable from length + punctuation alone? │
│  + golden test          is the rebuild byte-identical?              │
│                                                                     │
│  A family that fails on a given source is switched OFF for that     │
│  source and the omission is recorded, not hidden.                   │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─ STEP 6 ── COMPARE CANDIDATE PAIRS, KEEP THE BEST ──────────────────┐
│  twin asymmetry = |mean style lift TR − mean style lift EN|         │
│  lower is cleaner. Shipping pairs: 0.010, 0.015, 0.017, 0.033.      │
│  A pair withdrawn in v0.5.0 sat at 0.108.                           │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
                    SHIPS AS A MATCHED TWIN
```

**The one rule that is easy to get wrong.** Steps 2 and 5 measure different
things and step 5 is the one that decides. A corpus can look disqualifying at the
source level and be perfectly fine once built, because the Dirichlet
prior-randomisation in step 4 absorbs source-level bias. This was learned the
expensive way: a replacement pair was built and gate-tested on a source-level
number, and the question-level number did not move (§4d). **Never accept or
reject a pairing on step-2 numbers alone.**

## 3. The data sources, one by one

Six corpora feed eight sets. This section shows what each one actually looks
like, and exactly how its raw fields become the label the benchmark counts.
Read it before anything else; every design decision downstream follows from
these tables.

**The rule that applies to all of them:** the label is never invented here. It is
either already in the source, or derived from a rating the *writer of the text*
supplied. Nothing is annotated by hand, and no model assigns any label.

---

### 3.1 `vitamins_tr` — Turkish supplement reviews

Source: `turkish-nlp-suite/vitamins-supplements-reviews` (Vitaminler.com),
CC-BY-SA-4.0, fetched by `scripts/vitamins.py`.

**Raw rows as they arrive** (4 columns):

| product_name | brand | star | text |
|---|---|---|---|
| Vitamin C 500 Mg Takviye Edici Gıda | Venatura | 5 | *güvenilir marka* |
| Plus Efervesan 3'lü Paket | Sambucol | 5 | *Hızlı kargo. Güzel paketlenmiş. Orijinal ürünler.* |
| Damla 30 ml | Sidefer | 5 | *Hızlı gönderi kaliteli paketleme* |

**Raw star distribution** — heavily skewed, which is why we stratify:

| star | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| rows | 10,359 | 3,950 | 8,734 | 19,321 | **156,226** |

**How stars become labels.** A fixed map, applied identically to the English
twin so the two halves stay comparable:

| star | label |
|---|---|
| 1, 2 | `olumsuz` (negative) |
| 3 | `nötr` (neutral) |
| 4, 5 | `olumlu` (positive) |

Then each class is capped at 20,000 rows, because 5-star reviews would otherwise
be 73% of the pool. Final: 43,043 rows — `olumlu` 20,000, `olumsuz` 14,309,
`nötr` 8,734.

**After the fetch script** (3 columns — `entity` is the brand):

| text | label | entity |
|---|---|---|
| *Indirim zamani buradan alinabilir gayet guzel paketlemesi de* | `olumlu` | Solgar |
| *Başkası İçin aldım ama sürekli kullanıyor 🙏🏻* | `nötr` | Tab İlaç |
| *kargo ve hizmet iyiydi. nutraxin ürünlerinden genel de memnun kaldık.* | `olumlu` | Nutraxin |

**Why the 3-star → neutral mapping is the weak point.** A 3-star review is the
most genuinely ambiguous case, and it is the whole `nötr` class. This is stated
rather than hidden; it is also why the label-noise ceiling (§13) matters most for
this class.

---

### 3.2 `amazon_hpc_en` — English twin of the above

Source: `McAuley-Lab/Amazon-Reviews-2023`, `Health_and_Personal_Care` subset,
fetched by `scripts/health.py`. Brand comes from joining the review shard to the
metadata shard on `parent_asin` (the `store` field).

**Same star map**, English names:

| rating | label |
|---|---|
| 1, 2 | `negative` |
| 3 | `neutral` |
| 4, 5 | `positive` |

Capped at 20,000 per class, so the pool is perfectly balanced at 60,000 rows.

| text | label | entity |
|---|---|---|
| *This review is more to clarify someone else's review bc they didn't un…* | `positive` | Life Nutrition |
| *Love these easy multitasking bleach tablets. Beats carrying home a big…* | `positive` | Evolve |
| *I have been suffering a couple months with heel pain from plantar fasc…* | `positive` | Dr.Foot |

**This is the primary cross-lingual pair.** Same domain (health/supplements),
same label origin (the reviewer's own star), and an orthogonal brand axis on the
Turkish half. Its one weakness is length: Amazon reviews average 44.8 words
against the Turkish set's 12.1.

**Licence.** The repository packaging is MIT-style but the review text remains
under Amazon's Conditions of Use, so **the text is withheld from release** and
rebuilt locally by the script. Questions and answers ship.

---

### 3.3 `tr_intent` / `en_intent` — Amazon MASSIVE, the parallel corpus

Source: `AmazonScience/massive`, locales `tr-TR` and `en-US`, CC-BY-4.0,
fetched by `scripts/massive.py`. **No mapping is needed** — the intent label is
already in the data.

**Raw rows, and the reason this axis is the strongest one here.** The same
`pair_id` gives the same utterance in both languages with the same label:

| pair_id | Turkish `utt` | English `utt` | intent | scenario |
|---|---|---|---|---|
| train:1 | *beni cuma günü sabah dokuzda uyandır* | *wake me up at nine am on friday* | `alarm_set` | alarm |
| train:2 | *iki saat sonrasına alarm kur* | *set an alarm for two hours from now* | `alarm_set` | alarm |
| train:4 | *olly sessiz ol* | *olly quiet* | `audio_volume_mute` | audio |

**48 of 60 intents are kept.** Twelve have fewer than 100 rows and are dropped,
because a class too small to be sampled competitively is the rarest one in every
haystack, which makes `least_common` answerable without reading anything. The
motivating case: `cooking_query` has 6 rows in 16.5K and was the gold answer in
10 of 10 haystacks in **both** languages.

**The entity column is unusable here** and this is detected automatically:
`scenario` is *nested* inside `intent` (each intent belongs to exactly one
scenario), so entity questions are either trivial or impossible. The intent axis
therefore ships six families, not ten.

**Two regimes, because they answer different questions:**

| | matched on | asks |
|---|---|---|
| `tr_intent` / `en_intent` | equal **token** budget | at equal cost, which language degrades faster? |
| `tr_intent_paired` / `en_intent_paired` | equal **record** count, same records, same order | at equal content, which language degrades faster? |

The paired regime is what makes 100 of 120 questions share a byte-identical gold
answer across languages, and what permits paired statistical tests.

---

### 3.4 `musteri_tr` / `marc_en` — the cleanest pair

Added 2026-08-25. Turkish: `turkish-nlp-suite/MusteriYorumlari`, product reviews
scraped from Hepsiburada.com and Trendyol.com, CC-BY-SA-4.0. English:
`SetFit/amazon_reviews_multi_en` (the Multilingual Amazon Reviews Corpus),
Apache-2.0.

**Raw rows as they arrive.** Both sources ship two columns, `text` and a
zero-indexed star `label`:

| | raw label | text |
|---|---|---|
| MüşteriYorumları | `1` | *Ürünleri 2025 olarak göndereceğiz dedikleri halde öyle gönderilmemiş* |
| MüşteriYorumları | `2` | *Ürün görseldeki gibi. kalitelisini beğenmeedim. yumuşak ama çok ince…* |
| MARC en | `0` | *Arrived broken. Manufacturer defect. Two of the legs of the ba…* |
| MARC en | `0` | *the cabinet dot were all detached from backing... got me* |

**Raw label distributions.** MARC ships exactly balanced; MüşteriYorumları does
not, which is why it is capped:

| star (0-indexed) | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| MüşteriYorumları | 9,053 | 8,099 | 12,883 | 22,142 | 21,743 |
| MARC en | 40,000 | 40,000 | 40,000 | 40,000 | 40,000 |

**Both labels are the customer's own 1–5 star rating**, mapped by the same rule
used for `vitamins_tr`:

| stars | Turkish label | English label |
|---|---|---|
| 1, 2 | `olumsuz` | `negative` |
| 3 | `nötr` | `neutral` |
| 4, 5 | `olumlu` | `positive` |

Each class is capped to the smallest, so **both pools are perfectly balanced**
(normalised entropy 1.000): 12,883 per class in Turkish, 40,000 in English.

**After the fetch scripts** (2 columns each — no entity, deliberately):

| set | label | text |
|---|---|---|
| `musteri_tr` | `olumsuz` | *Ürün aşırı dandik. Görselde fırın ve bulaşık makinesinin orada ışıklı…* |
| `musteri_tr` | `nötr` | *Ürün görseldeki gibi. kalitelisini beğenmeedim…* |
| `marc_en` | `negative` | *Followed directions, did not work as advertised.* |
| `marc_en` | `negative` | *Ordered 2 they shipped 1 promised by certain day, then the next day…* |

**Neither half has a product or brand column**, so both emit the same six
families. That symmetry is deliberate: a twin whose halves support different
question families is not a twin.

**Why this pair matters.** On the measurements that decide whether a
cross-lingual comparison is trustworthy, it is the best in the benchmark:

| | `musteri_tr` ↔ `marc_en` | `vitamins_tr` ↔ `amazon_hpc_en` | *withdrawn brand-review pair* |
|---|---|---|---|
| twin asymmetry (§4d) | **0.010** | 0.015 | 0.108 |
| class balance | **1.0x / 1.0x** | 2.3x / 1.0x | 4.1x / 3.9x |
| length spread within set | **1.2x / 1.1x** | 1.5x / 1.1x | 3.6x / 1.4x |
| tokens per record | **32.6 vs 41.3** | 22 vs 82 | 45 vs 30 |
| label provenance | writer's own stars, both | writer's own stars, both | undocumented vs CrowdFlower |
| text redistributable | **both** | Turkish only | Turkish only |

Its cost is six families instead of ten. It is therefore the **cleanest** pair,
not the richest — `vitamins_tr` ↔ `amazon_hpc_en` remains the primary pair
because it carries the entity axis.

### 3.5 Summary — what each source contributes

| set | source | label origin | classes | entity | ships |
|---|---|---|---|---|---|
| `tr_intent`, `en_intent` (+paired) | MASSIVE | already in the data, professional annotation | 48 | nested, unusable | 6 families |
| `vitamins_tr` | Vitaminler.com | **writer's own star rating** | 3 | brand, orthogonal | 10 families |
| `amazon_hpc_en` | Amazon H&PC | **writer's own star rating** | 3 | brand | 10 families |
| `musteri_tr` | Hepsiburada / Trendyol | **writer's own star rating** | 3 | none | 6 families |
| `marc_en` | MARC English | **writer's own star rating** | 3 | none | 6 families |


### 3.6 Example questions (produced by the actual builder)

Every answer below is computed from the source labels by two independent code
paths and asserted equal (see §6).

**Review axis** (orthogonal brand entity), from `vitamins_tr_out/questions.jsonl`:

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

> **On the set names in this section.** Several measurements below were taken on
> `tr_oolong` (Turkish brand reviews) and `en_twin` (airline tweets), a pair
> **withdrawn in v0.5.0** over undocumented label provenance. The measurements are
> kept because they are the evidence for why each solver exists — a defect found
> on a set that was later dropped is still a defect the pipeline now catches. No
> shipped set depends on them.

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
(p = 0.033, n = 10). ✅ **Resolved 2026-09-05 by `--certify 250`:** at **152
distinct draws** the same family measures a prior of **0.263 against a chance of
0.200, z = +1.9 — `ok`.** The flag was small-sample noise, exactly as this
section's own rule predicts. Every family on every set now passes at scale; the
label-ranking families are singleton (one distinct question per haystack), so
their power comes from more haystacks rather than more draws. By that rule —
per-family samples of 10–20 cannot certify a family — the original was a
small-sample flag, not a demonstrated
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
| `vitamins_tr` | olumsuz 15.0 w | olumlu 9.8 w | 1.5x |
| `musteri_tr` | olumsuz | olumlu | 1.2x |
| `marc_en` | negative | positive | 1.1x |
| `amazon_hpc_en` | **positive** 46.9 w | negative 41.8 w | 1.1x |

For scale, the brand-review corpus withdrawn in v0.5.0 had a **3.6x** spread —
`olumsuz` averaged 33.1 words and ended in a period 48% of the time, `olumlu`
averaged 9.1 words and ended in a period 99% of the time.

A format-solvable corpus still yields a valid aggregation task — the model must
classify every record and add up the results either way. What it stops being is a
test of reading the *language*. So the number to watch is not either half's lift
but **the gap between the twin's halves**, because an asymmetric bias means a
model can score on the Turkish half by measuring sentence lengths:

| pair | asymmetry (v0.6.0 build) |
|---|---|
| intent, record-matched | **0.014** |
| `vitamins_tr` ↔ `amazon_hpc_en` | 0.020 |
| intent, token-matched | 0.028 |
| `musteri_tr` ↔ `marc_en` | 0.030 |

Every shipping pair is now at or under 0.030. The one pair that sat at **0.108**
was the brand-reviews/airline pair, withdrawn in v0.5.0. All eight sets pass the
gate (no set exceeds +0.15 mean lift over majority) and
`manifests/style_audit.json` is the committed record.

**One family fails this solver everywhere.** `shift` is the only family with a
positive lift on any set: **+0.400** (`amazon_hpc_en`), **+0.300** (`en_twin`,
`vitamins_tr`), +0.100 (`en_intent`). Its majority baseline is already the
highest in the suite (mean 0.61). A binary rose/fell over
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

**Label leakage, as measured on the shipped build.** The filter drops any record
containing any label's surface form. These are the rates recorded in the
manifests of the current build, not from an earlier one:

| Corpus | Pool | Leaking records | Rate |
|---|---|---|---|
| MASSIVE **tr**-TR (intent) | 15,075 | 0 | **0.00%** |
| MASSIVE **en**-US (intent) | 15,075 | 0 | **0.00%** |
| `vitamins_tr` | 43,043 | 177 | 0.45% |
| `amazon_hpc_en` | 60,000 | 557 | 1.00% |
| `musteri_tr` | 38,649 | 80 | 0.22% |
| `marc_en` | 120,000 | 657 | 0.55% |

⚠️ **A claim previously made here has been withdrawn.** Earlier revisions reported
112 leaking English intent records (0.68%) against 0 Turkish, and read that as
Turkish morphology hiding labels where English surface text gives them away.
**The current build measures 0.00% on both**, so the asymmetry is not there to
interpret. The earlier figure came from a larger pool (16,521 rows) than the one
that ships.

**And the intent-axis comparison was confounded anyway**, which is the more useful
point. Both locales are scored against the *English* label vocabulary
(`play_music`), so a Turkish utterance cannot contain a label form no matter how
transparent it is — 0.00% is a tautology, not a finding. Scoring each language
against labels **in its own language** reverses the result:

| | leak rate |
|---|---|
| EN text vs English labels (`alarm_set`) | **0.00%** |
| TR text vs Turkish labels (`alarm_kur`) | **0.91%** (137 / 15,075) |

The cause is word order, not morphology: Turkish is verb-final, so a `noun_verb`
label name matches the natural phrase exactly ("iki saat sonrasına **alarm
kur**"), while English `verb_noun` labels never surface — you say "set an alarm",
not "alarm set". This is why the shipped intent labels stay in their original
MASSIVE identifier form; see §13 for the translation question.

Since the two locales are the same utterances, the filter is applied as a
**union** over the pair, so a drop on one side removes the same `pair_id` from
the other and the record-matched twin stays aligned.

**Maximum length is derived, not chosen.** A haystack of R records over K classes
gives each class a 1/K share on average, so a class can top the ranking only if
the pool can supply more than R/K of it. The smallest class caps the haystack at
**R_max = min_class_pool × K** records. The builder computes the ceiling per set,
warns above 0.85×, and records it in the manifest under `ranking_feasibility`.

**Tokenization penalty at the tokenizer.** Measured by the record-matched twin:
at identical record counts Turkish costs **1.30–1.34×** the tokens of English
**under Qwen3-8B**. This separates "harder to tokenize" from "harder to reason
about" — but only for that tokenizer. Across tokenizers the same aligned
utterances give 2.16× (GPT-2), 1.53× (Qwen3-8B), 1.29× (mBERT) and **0.57×**
(BERTurk), so it is a property of the tokenizer, not of Turkish.

## 5. What ships

| set | lang | classes | tiers | haystacks | questions | longest |
|---|---|---|---|---|---|---|
| `tr_intent` | tr | 48 | 50K / 100K | 10 | 120 | 99,998 |
| `en_intent` | en | 48 | 50K / 100K | 10 | 120 | 99,871 |
| `tr_intent_paired` | tr | 48 | 3K rec / 6K rec | 10 | 120 | 99,057 |
| `en_intent_paired` | en | 48 | 3K rec / 6K rec | 10 | 120 | 75,187 |
| `vitamins_tr` | tr | 3 | 100K / 250K / 500K / 750K | 20 | 237 | 744,785 |
| `amazon_hpc_en` | en | 3 | 100K / 250K / 500K / 1M | 20 | 236 | 987,623 |
| `musteri_tr` | tr | 3 | 100K / 250K / 500K | 15 | 153 | 496,238 |
| `marc_en` | en | 3 | 100K / 250K / 500K | 15 | 148 | 491,821 |

**1254 questions over 110 haystacks**, eight instance sets. Realized
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

## 9. OOLONG vs TR-OOLONG

**Full side-by-side, with real questions from both benchmarks, is in
[`COMPARISON.md`](COMPARISON.md).** That document is written for a reader with no
access to the code. The short version:

OOLONG's question set is **task types × conditioning axes** — the same handful of
shapes asked over everything, over a subset of users, and over a subset of dates.
TR-OOLONG matches their counting group, replaces the user axis with a richer
**entity** axis (real brands, prior-neutral candidate sets, plus ordered
ranking), adds normalised **proportions**, and **lacks their timeline axis** —
which their paper reports as the hardest of the three.

| | OOLONG | TR-OOLONG |
|---|---|---|
| languages | English | **Turkish + matched English** |
| questions | 6,500 synth + 10,810 real | 1,254 |
| haystacks | not reported per split | **110**, 28.2M tokens total |
| context | 1K–4M, reported at 8K–128K | 36K–**987K** (mean 257K) |
| label space | 2–10 classes | **3 and 48** |
| entity axis | synthetic user IDs | **real brands**, MI 0.022 on `vitamins_tr` |
| **timeline axis** | **6 families over real dates** | 1 binary family over positional halves |
| ordered ranking | — | implemented, withdrawn with its only corpus in v0.5.0 |
| numeric metric | `0.75^\|y-ŷ\|` | same **+ `relative`** (theirs degenerates at our counts) |
| shortcut audit | not reported | **4 solvers, committed manifests** |

**The timeline gap is the one real deficit, and it is blocked on data, not code.**
It needs a labelled corpus with real dates in *both* languages. English has
several; no Turkish source examined carries dates. See
[`DATASET_REVIEW.md`](DATASET_REVIEW.md).

**What is taken from OOLONG** (from the paper — their construction, scoring and
analysis code are all still listed as unreleased): the construction principle,
the counting typology (`most_common`/`least_common` mirror `MOST_FREQ`/`LEAST_FREQ`;
`second_most` is an extension, since they have second-most *user* and *date* but
no second-most *label*), and the `0.75^|y-ŷ|` metric implemented from its
published definition. Everything else is built here.

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

The cross-lingual claim is only as good as the pairing, so twins here are
**selected by measurement, not by intuition**. The procedure below is the one
actually followed; every rejected candidate in the table underneath was rejected
by a number, and all of them are recorded in
[`DATASET_REVIEW.md`](DATASET_REVIEW.md).

**The procedure**

1. **Shortlist Turkish corpora that are labelled, large, and permissively
   licensed.** Searched: `ytu-ce-cosmos`, `turkish-nlp-suite`, `Trendyol`, plus
   parallel multilingual corpora. A corpus with no labels (Havadis, 745K news
   articles) is unusable regardless of size — the label *is* the answer key.
2. **For each survivor, find the English corpus that matches it on the four
   criteria below.** Not the other way round: Turkish is the scarce side.
3. **Build both halves and run all four gates.** A pairing is only accepted on
   question-level numbers, never on source-pool numbers — see §4d, where a
   candidate that looked disqualifying at the source level turned out not to
   matter at all once built.
4. **Compare twin asymmetry across candidates and keep the lowest.**

**The four criteria, in order of how often they bind**

1. **Same label provenance.** Both halves' labels must be produced the same way.
   Author-assigned star ratings on both sides is the strongest available option,
   because the person who wrote the text assigned the label — there is no
   annotator to disagree with.
2. **Comparable record length.** A 4x mismatch changes what "one chunk" means and
   interacts with every compression measurement.
3. **Comparable surface shape.** Measured by §4d. The **gap between the halves**
   matters, not either half's level.
4. **Both halves reach the same length tiers.** `R_max = smallest_class × K`.

**And one veto: the licence.** A closer match is not worth an unredistributable
corpus. This decided the pair that ships — see the `app_reviews` row below.

### Worked examples

| pairing | provenance | length | style gap | verdict |
|---|---|---|---|---|
| **MASSIVE tr-TR ↔ en-US** | identical, same utterances | identical by construction | **0.017** | **best available.** The only true record-matched twin; 110/120 questions share a gold answer |
| **`musteri_tr` ↔ `marc_en`** | author's stars, both | 13.8 vs 34.1 w (2.5x) | **0.010** | **ships. Lowest asymmetry measured**; both halves redistributable; no entity column, so 6 families |
| **`vitamins_tr` ↔ `amazon_hpc_en`** | author's stars, both | 12.1 vs 44.8 w (3.7x) | **0.015** | **ships as the primary review pair** — the only one with an orthogonal entity axis (MI 0.022) |
| Turkish brand reviews ↔ airline tweets | undocumented vs CrowdFlower humans | 24.2 vs 15.7 w | **0.108** | **withdrawn in v0.5.0.** Mismatched provenance, 7x surface-shape asymmetry |
| MüşteriYorumları ↔ Amazon Home & Kitchen | author's stars, both | 13.2 vs 71.8 w (5.4x) | 0.106 | rejected: no Amazon category is terse enough |
| MüşteriYorumları ↔ `app_reviews` | author's stars, both | **13.8 vs 14.7 w (1.06x)** | 0.030 | **the closest length match of anything tested, and still rejected** — `sealuzh/app_reviews` is tagged `license:unknown`, which declares no known grant. MARC is Apache-2.0 and scored *better* anyway |
| `vitamins_tr` ↔ `app_reviews` | author's stars, both | 12.1 vs 18.8 w (1.6x) | 0.021 | no better than the pair in use |
| SIB-200 tur ↔ eng | identical, parallel | identical | — | **structurally dead**: 1,004 rows total, ~14K token ceiling |
| XNLI tr ↔ en | identical, parallel | identical | — | **structurally dead**: 7,500 human-translated rows; the 393K train split is machine-translated |

**The lesson from the last two rows is worth stating plainly.** Parallel corpora
give a record-matched twin for free, which is the strongest possible design, but
human translation is expensive so they are all small, and this benchmark needs a
large pool for independent draws at 100K–1M tokens. MASSIVE, at 16.5K parallel
utterances, is the largest such Turkish resource in existence and it is already
used here. Full search in `DATASET_REVIEW.md`.

## 11b. Screening a candidate pair automatically

`--audit` screens ONE source. What decides a cross-lingual claim is the **gap**
between two, and both halves can pass separately while the pair still cannot
support the claim. `scripts/check_pair.py` runs the §11 criteria as a script:

```bash
python scripts/check_pair.py configs/musteri_tr.json configs/marc_en.json
```

It checks declared label provenance, label-space size, mean record length, the
surface-shape gap, class balance, whether each half reaches its own length tiers
under its own reference tokenizer, entity-axis symmetry, and the licence veto.
The verdict is **COMPATIBLE** / **COMPATIBLE WITH CAVEATS** / **INCOMPATIBLE**,
each failure naming the number that caused it. `--strict` turns every caveat into
a failure; `--json` writes the report.

Two fields must be **declared** in the config, because neither can be measured
from the data and one of them withdrew a whole pair in v0.5.0:

```json
"licence": "cc-by-sa-4.0",
"label_provenance": "author_stars"
```

On the pairs in this repo it reproduces the verdicts §11 reached by hand:

| pair | verdict |
|---|---|
| `musteri_tr` ↔ `marc_en` | **COMPATIBLE** |
| `vitamins_tr` ↔ `amazon_hpc_en` | COMPATIBLE WITH CAVEATS (3.3× length, Amazon licence) |
| `tr_intent` ↔ `en_intent` | COMPATIBLE WITH CAVEATS |
| `tr_intent` ↔ `marc_en` | **INCOMPATIBLE** (provenance, label space, 6.1× length) |

**It screens sources, not questions.** Only the post-build gates can certify a
family — source-level numbers have already been shown not to predict
question-level exploitability (§4d).

## 12. Repository layout

```
tr-oolong/
├── README.md
├── ROADMAP.md          # tracked checklist — this is where progress lives
├── DESIGN_DECISIONS.md # why the benchmark is built this way, with the evidence
├── DATACARD.md         # per-axis source, license, label-noise, construction
├── COMPARISON.md       # OOLONG vs TR-OOLONG, for a reader without the code
├── DATASET_REVIEW.md   # every source considered, the twin search, and each verdict
├── PAPER_NOTES.md      # claims to carry into the paper, and what is not yet true
├── REVIEW.md           # adversarial read: the weak parts, ranked
├── ADVISOR_QUESTIONS.md # standing questions and their current answers
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
ships `amazon_hpc_en` as questions-and-answers only — its
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
(mean majority baseline 0.61), and it is the only family the surface-format
solver beats: +0.400 on `amazon_hpc_en`, +0.300 on `vitamins_tr`, +0.267 on
`musteri_tr` and `marc_en`, +0.100 on `en_intent` (§4d). Length correlates with label, and
length also correlates with position once drift is injected, so format alone
partly recovers the direction. The fix is a real dated timeline axis of the kind
OOLONG has, which is blocked on data rather than code: no Turkish source examined
carries dates (see §9 and `DATASET_REVIEW.md`). **Until then, do not report
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
| `tr_intent` | 100K | 0.279 | 0.403 |
| `amazon_hpc_en` | 1M | 0.213 | 0.310 |

Overlap is negligible at the shortest tiers (`tr_intent` 50K: J≈0.05) and grows
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
