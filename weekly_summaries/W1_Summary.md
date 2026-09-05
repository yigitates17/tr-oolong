# TR-OOLONG — Week 1 summary

*Prepared 2026-08-31. Every number below was recomputed from the built dataset on
this date, not copied from an earlier note. Written for a reader who has not seen
the code.*

---

## 0. The one-minute version

The dataset is **finished, checked and published to our repo**: 8 sets, 110
documents, 1,221 questions, 28.2 million tokens, in Turkish and English.

Four things are worth your time in this meeting:

1. **OOLONG's own code was never released.** We rebuilt everything from their
   paper. This is a limitation to state, not a problem to fix.
2. **We are ahead of OOLONG on length, label-space size and cross-lingual
   design; we are behind on one thing — they have real calendar dates and we do
   not.** That gap is blocked on data, not on effort.
3. **We dropped one Turkish corpus (We-Bears)** — not because of label noise, but
   because we could not establish where its labels came from. Separately, we
   measured and gated the "long comment = negative" problem that affects every
   review corpus (§4).
4. **New proposal (§8): publish a second dataset — the trajectories.** Worth doing,
   and it is nearly free **if we decide now**. Two engineering decisions have to be
   taken before anything is run (§8.6), or the dataset is either unusable for
   training or open to an unanswerable leakage objection.

**Still missing, and it is the same item as last time: no model has ever been run
on the benchmark.** Every difficulty claim we make today is a theoretical chance
rate, not a measurement.

---

## 1. OOLONG's pipeline code is not available to us

OOLONG (Bertsch et al., 2025, arXiv:2511.02817) is the benchmark this work is
modelled on. Checked 2026-08-25 and again this week:

| what we hoped to reuse | status |
|---|---|
| their haystack construction code | **not released** |
| their scoring script | **not released** |
| their analysis code | **not released** |
| their validated English splits | **not released** (their repo lists them as pending) |

**What this means in practice.** Everything in TR-OOLONG was implemented from the
descriptions and formulas printed in their paper. Three specific consequences:

- Our scoring formula matches theirs because we implemented the published
  equation (`0.75^|error|`), **not** because we ran their script against ours. We
  say this explicitly in the paper rather than claiming verified parity.
- We cannot drop their English data in as a control set. Our loader is already
  written for the day they release it.
- Any difference between our numbers and theirs could be a real finding or an
  implementation difference, and we currently cannot tell which.

This is normal for a benchmark-vs-benchmark comparison and reviewers accept it,
provided we say it out loud. We do.

---

## 2. OOLONG vs TR-OOLONG

### 2.1 What both benchmarks are trying to measure

Both ask a question that **cannot be answered by searching the text**. You paste a
very long document made of thousands of short labelled records, then ask something
about the *distribution* of the whole thing — "which label is most common?", "how
many are negative?". To answer, a model has to read and classify every single
record and then do arithmetic over thousands of results. Finding one passage does
not help.

### 2.2 Structure: the same idea, a different second axis

OOLONG's design is best read as **question shapes × conditioning axes** — the same
handful of questions asked three times: over everything, over a subset of *users*,
and over a subset of *dates*.

| question shape | OOLONG | TR-OOLONG |
|---|---|---|
| most frequent label | ✅ | ✅ `most_common` |
| least frequent label | ✅ | ✅ `least_common` |
| **second** most frequent **label** | ❌ | ✅ `second_most` *(our extension)* |
| how many carry label X | ✅ | ✅ `count` |
| **what share** carry label X | ❌ | ✅ `proportion` *(our extension)* |
| label A vs label B — more/less/same | ✅ | ❌ *(their extension)* |
| conditioned on a **user** | ✅ synthetic IDs | replaced by **entity** |
| which entity has most X | ❌ | ✅ `entity_argmax` |
| how many X does entity E have | ❌ | ✅ `entity_count` |
| entity A vs entity B | ❌ | ✅ `pairwise` |
| **conditioned on real calendar dates** (6 shapes) | ✅ | ❌ **we have none** |
| did a label's share rise or fall | ✅ across real dates | ⚠️ `shift` — across document *position* |

**Summary in one line:** we match their counting group, we replace their synthetic
user axis with a real entity axis, we add proportions and second-most-label, and
**we are missing their entire timeline axis**, which their paper reports as their
hardest group.

#### What "real dates" actually means, since this is the row that needs unpacking

When OOLONG builds a document, it stamps **a calendar date and a user ID onto
every single line**, and prints them where the model can read them:

```
Date: Dec 28, 2022 || User: 76063 || Instance: Todays Vodafone nu...
Date: Mar 02, 2023 || User: 41288 || Instance: ...
```

Those dates are invented at build time — but once printed, they behave like real
dates: they can be compared, sorted, filtered and grouped. That gives them six
question shapes we cannot ask at all. Three examples:

- *"only consider instances that occur in **October of any year** — among those,
  which label is most common?"* → filter the document by month, **then** aggregate.
- *"was 'spam' more common **before 2024-07-24** than after?"* → split the
  document at an arbitrary date the model has to locate itself.
- *"how many dates are represented **exactly once**?"* → aggregate over the
  *date column itself*, not over the labels. A different kind of question
  entirely: it counts a metadata field rather than a latent class.

**We can ask none of these, because our records carry no date column.** Our
sources are `product, brand, text, star` and `text, label`. There is no time in
the data to ask about.

#### And what our `shift` family does instead

Since we cannot split by date, we split by **position**: the first half of the
document versus the second half. To guarantee there is something to detect, the
builder **deliberately injects drift** when assembling each document — one label
is over-represented in the second half — and records which label and how much in
the manifest. The question is then:

> *"Kayıtların ikinci yarısında 'olumsuz' oranı ilk yarıya göre arttı mı azaldı
> mı?"* — "In the second half of the records, did the share of 'olumsuz' rise or
> fall compared to the first half?" → **arttı** (rose)

So "rise or fall over time" is shorthand: **for OOLONG it genuinely is over time;
for us it is over document position, which we use as a stand-in for time.**

**Three reasons ours is the weaker version, and we should state all three:**

1. **It is binary.** Guessing scores 50%. Their date questions have many possible
   answers, so guessing scores near zero.
2. **It is one question shape, not six** — and none of ours can filter, group or
   count over a time field.
3. **It is the only family a deliberately stupid program can partly beat.** Our
   format solver (§4.1), which reads nothing but sentence length and punctuation,
   scores **+0.10 to +0.40** above the majority baseline on `shift`. The reason is
   a chain: length correlates with label, and label correlates with position once
   we inject drift — so length leaks position. **Because of this, `shift` will
   not carry a headline result in the paper.**

### 2.3 Size, side by side

| | OOLONG | TR-OOLONG |
|---|---|---|
| languages | English only | **Turkish + a matched English twin** |
| questions | 17,310 total (6,500 synthetic + 10,810 real) | **1,221** |
| documents (haystacks) | not reported per split | **110** |
| **shortest document** | — | **36,250 tokens** |
| **mean document** | reporting focused at 8K–128K | **256,882 tokens** |
| **longest document** | up to 4M claimed | **987,623 tokens** |
| total tokens built | — | **28,257,099** |
| records inside one document | not reported | 1,523 – 19,774 |
| number of possible labels | 2–10 | **3 and 48** |
| source corpora | 10 classification sets + D&D transcripts | 6 corpora on 2 axes |

Per set, ours (recomputed today):

| set | lang | labels | docs | questions | min tok | mean tok | max tok |
|---|---|---|---|---|---|---|---|
| `tr_intent` | tr | 48 | 10 | 120 | 49,981 | 74,992 | 99,998 |
| `en_intent` | en | 48 | 10 | 120 | 49,921 | 74,880 | 99,871 |
| `tr_intent_paired` | tr | 48 | 10 | 120 | 47,629 | 73,182 | 99,057 |
| `en_intent_paired` | en | 48 | 10 | 120 | 36,250 | 55,547 | 75,187 |
| `vitamins_tr` | tr | 3 | 20 | 235 | 99,217 | 397,122 | 744,785 |
| `amazon_hpc_en` | en | 3 | 20 | 234 | 98,672 | 456,691 | 987,623 |
| `musteri_tr` | tr | 3 | 15 | 138 | 99,137 | 281,100 | 496,238 |
| `marc_en` | en | 3 | 15 | 134 | 98,232 | 278,551 | 491,821 |

**Is that 1,221 questions in each language, or 1,221 in total?** In **total** —
and it splits almost exactly in half:

| language | questions | over how many documents |
|---|---|---|
| Turkish | **613** | 55 |
| English | **608** | 55 |
| **total** | **1,221** | **110** |

Every question exists in exactly one language, asked about one document in that
language. The near-even split is by design, not luck: every Turkish set has an
English twin built by the identical pipeline. On the record-matched intent pair
the correspondence is exact — **110 of 120 question pairs are the same question
about the same records with the same gold answer**, once in Turkish and once in
English. On the review pairs the two halves are different corpora, so questions
correspond in *type and length tier* but not one-for-one.

And our 1,221 questions split by type:

| type | n | | type | n |
|---|---|---|---|---|
| `count` | 355 | | `second_most` | 90 |
| `proportion` | 352 | | `entity_count` | 42 |
| `shift` | 110 | | `entity_argmax` | 41 |
| `most_common` | 99 | | `pairwise` | 35 |
| `least_common` | 97 | | | |

### 2.4 The same question in both benchmarks, so the difference is visible

**Counting — "which label is most common?"**

> **OOLONG** (spam detection, 2 possible labels, ~10 records shown)
> *"In the above data, which of the labels is the most common? … answer is one of
> the labels: ham, spam."* → **spam**

> **TR-OOLONG** (`tr_intent`, **48 possible labels**, 50,000 tokens)
> *"Bu kayıtlarda en sık görülen etiket hangisi? Etiketler: 'alarm_remove',
> 'general_joke', 'iot_cleaning', 'iot_hue_lightup', 'recommendation_movies'.
> Sadece etiket adını yaz."* → **iot_cleaning**

**Counting one label — note the magnitude difference**

> **OOLONG**: *"how many data points should be classified as label 'ham'?"* → **4**
>
> **TR-OOLONG** (`musteri_tr`, 100K tokens): *"Bu yorumlardan kaç tanesi 'olumlu'
> etiketli?"* → **1,699**

Their answers are single digits. Ours run into the thousands. This is not a
cosmetic difference — see §2.6.

**Conditioning on a person / a thing**

> **OOLONG**: *"only consider instances associated with user IDs 76063. Among
> these, which label is the least common?"* → **ham**
> *(the user ID is a random number we would have invented at build time)*

> **TR-OOLONG** (`vitamins_tr`, 250K tokens): *"Şu markalardan hangisi en çok
> 'olumlu' yorum aldı: 'Beeo', 'NBL', 'Nbt İlaç', 'Smartcaps', 'Suda Collagen'?"*
> → **Smartcaps**
> *(real brands from the corpus; the five candidates are deliberately chosen to
> have near-identical overall review counts, so the answer cannot be guessed from
> world knowledge or from corpus statistics — only from this document)*

**Time — theirs is real, ours is a substitute**

> **OOLONG**: *"was label 'spam' more common, less common, or the same frequency
> before 2024-07-24, as compared to after 2024-07-24?"* → **more common**
> **OOLONG**: *"how many dates are represented exactly 1 times?"* → **10**

> **TR-OOLONG**: *"Yorumların ikinci yarısında 'olumsuz' oranı ilk yarıya göre
> arttı mı azaldı mı?"* → **arttı**

Ours is a **binary** question about the first half vs the second half of the
document. It is the weakest family we have.

**The thing only we have — the same question in two languages with the same answer**

> **Turkish**: *"Bu kayıtlarda kaç tane 'transport_taxi' etiketli kayıt var?"* → **18**
> **English**: *"How many utterances have the intent 'transport_taxi'?"* → **18**

110 of 120 questions in our record-matched pair have a **byte-identical gold
answer** in both languages. This is possible because that axis is built from a
parallel corpus — the same utterances, translated, in the same order. Any score
difference between the two is therefore a property of *the language*, not of the
question. **OOLONG has no cross-lingual dimension at all.**

### 2.5 Can we compare difficulty? Yes, in both directions

**Important caveat first: no model has been run on either benchmark by us, so
these are structural difficulty arguments, not measured ones.**

**Harder in TR-OOLONG:**

| | OOLONG | TR-OOLONG | why it is harder |
|---|---|---|---|
| label space | 2–10 | **48** | random guessing scores 1/48 = 2% instead of 1/2 = 50% |
| document length | reported at 8K–128K | **up to 987K** | 7.7× their reporting ceiling |
| records to classify | tens | **up to 19,774** | the arithmetic is over thousands of items |
| answer magnitude | single/double digits | up to 12,225 | no room for "eyeballing it" |

**Harder in OOLONG:**

- **The timeline axis.** Six question shapes over real calendar dates, which their
  paper reports as their hardest group. Ours is one binary question. It is also the
  only family that our own "cheating detector" can partly beat — a dumb program
  that looks only at surface formatting scores +0.10 to +0.40 above chance on it.
  **This is our real deficit and we should name it before a reviewer does.**
- **A label-vs-label comparison family** ("is A more, less, or equally common than
  B") that we do not implement.
- **Far more questions**: 17,310 against our 1,221.
- **Two task flavours** — synthetic documents *and* real Dungeons-and-Dragons
  transcripts. We only have the synthetic style.

**Why our timeline gap is not laziness.** To add it we need a labelled corpus with
real dates **in both languages**. English has several. **No Turkish source we
examined carries dates** — the vitamin corpus is `product, brand, text, star`; the
e-commerce corpus is `text, label`. Finding a dated, labelled Turkish corpus is the
single unblocking step, and we have searched. It is a data problem.

### 2.6 One place where we had to add a metric

OOLONG scores a numeric answer as `0.75^|your answer − correct answer|` — full
marks if exact, decaying fast as you drift. That works when the correct answer is
"4".

Our typical correct answer is around 1,000. `0.75^50` is about 0.0000006. So a
model that is off by 50 out of 1,700 and a model that answers randomly **both score
zero**. Their metric stops distinguishing a near-miss from nonsense at our lengths.

So we report three numbers:

| metric | what it is | why |
|---|---|---|
| `partial` | `0.75^|error|` | **comparability with OOLONG.** Frozen, never changed |
| `relative` | `1 − error/correct` | **information.** Being 2% off scores 0.98 |
| `exact` | right or wrong | the strict reading |

---

## 3. What the data actually looks like

### 3.1 The Turkish supplement reviews → `vitamins_tr`

Source: `turkish-nlp-suite/vitamins-supplements-reviews` (Vitaminler.com),
CC-BY-SA-4.0. **Raw, as it arrives:**

| product_name | brand | star | text |
|---|---|---|---|
| Vitamin C 500 Mg Takviye Edici Gıda | Venatura | 5 | *güvenilir marka* |
| Plus Efervesan 3'lü Paket | Sambucol | 5 | *Hızlı kargo. Güzel paketlenmiş. Orijinal ürünler.* |
| Damla 30 ml | Sidefer | 5 | *Hızlı gönderi kaliteli paketleme* |

The star becomes the label by a fixed rule (1–2 → `olumsuz`, 3 → `nötr`, 4–5 →
`olumlu`), applied identically to the English twin. **After our script:**

| text | label | entity |
|---|---|---|
| *Indirim zamani buradan alinabilir gayet guzel paketlemesi de* | `olumlu` | Solgar |
| *Başkası İçin aldım ama sürekli kullanıyor 🙏🏻* | `nötr` | Tab İlaç |
| *kargo ve hizmet iyiydi. nutraxin ürünlerinden genel de memnun kaldık.* | `olumlu` | Nutraxin |

### 3.2 Its English twin → `amazon_hpc_en`

Source: Amazon Reviews 2023, Health & Personal Care. Same star rule, English names.

| text | label | entity |
|---|---|---|
| *This review is more to clarify someone else's review bc they didn't un…* | `positive` | Life Nutrition |
| *Love these easy multitasking bleach tablets. Beats carrying home a big…* | `positive` | Evolve |
| *I have been suffering a couple months with heel pain from plantar fasc…* | `positive` | Dr.Foot |

### 3.3 The parallel corpus → `tr_intent` / `en_intent`

Source: Amazon MASSIVE, CC-BY-4.0. **The same utterance exists in both languages
with the same label** — this is what makes the twin possible:

| pair_id | Turkish | English | intent |
|---|---|---|---|
| train:1 | *beni cuma günü sabah dokuzda uyandır* | *wake me up at nine am on friday* | `alarm_set` |
| train:2 | *iki saat sonrasına alarm kur* | *set an alarm for two hours from now* | `alarm_set` |
| train:4 | *olly sessiz ol* | *olly quiet* | `audio_volume_mute` |

### 3.4 The cleanest pair → `musteri_tr` / `marc_en`

Turkish: MüşteriYorumları (Hepsiburada + Trendyol), CC-BY-SA-4.0. English:
Multilingual Amazon Reviews Corpus, Apache-2.0. Both arrive as `text` + a 1–5 star.

| set | label | text |
|---|---|---|
| `musteri_tr` | `olumsuz` | *Ürün aşırı dandik. Görselde fırın ve bulaşık makinesinin orada ışıklı…* |
| `musteri_tr` | `nötr` | *Ürün görseldeki gibi. kalitelisini beğenmeedim…* |
| `marc_en` | `negative` | *Followed directions, did not work as advertised.* |
| `marc_en` | `negative` | *Ordered 2 they shipped 1 promised by certain day, then the next day…* |

### 3.5 What a haystack looks like

**OOLONG** glues records together with a synthetic date and user ID printed on
every line:

```
Date: Dec 28, 2022 || User: 76063 || Instance: Todays Vodafone nu...
Date: Mar 02, 2023 || User: 41288 || Instance: ...
```

**TR-OOLONG** concatenates only the text, separated by a fixed delimiter. Our
entity (the brand) is a real column in the corpus, so it does not need to be
printed inline:

```
Indirim zamani buradan alinabilir gayet guzel paketlemesi de

<<<###>>>

Başkası İçin aldım ama sürekli kullanıyor 🙏🏻

<<<###>>>

kargo ve hizmet iyiydi. nutraxin ürünlerinden genel de memnun kaldık.
```

### 3.6 What our finished benchmark rows look like

This is the actual file we would publish — first lines of `vitamins_tr`:

```json
{"id": "tr-100000-0-q0", "haystack_id": "tr-100000-0", "language": "tr",
 "kind": "count", "label": "nötr", "answer": "903",
 "question": "Bu yorumlardan kaç tanesi 'nötr' etiketli? Sadece sayıyı yaz."}

{"id": "tr-100000-0-q2", "haystack_id": "tr-100000-0", "language": "tr",
 "kind": "proportion", "label": "olumsuz", "answer": "7", "unit": "percent",
 "question": "Yorumların yüzde kaçı 'olumsuz' etiketli? En yakın tam sayıya yuvarla…"}

{"id": "tr-100000-0-q4", "haystack_id": "tr-100000-0", "language": "tr",
 "kind": "most_common", "candidates": ["nötr", "olumlu", "olumsuz"],
 "answer": "olumlu",
 "question": "Bu yorumlarda en sık görülen etiket hangisi? Etiketler: …"}
```

**Every one of those `answer` fields is computed twice, by two pieces of code that
share nothing, and the two results are compared byte for byte before the file is
accepted.** No human wrote any answer; no model assigned any label.

### 3.7 How each English twin was chosen

**Twins were selected by measurement, not by intuition.** Turkish is the scarce
side, so each Turkish corpus came first and we then searched for the English
corpus that matched it on four criteria — listed in the order they actually turned
out to bind:

1. **Same label provenance.** Both halves' labels must be produced the same way.
   Author-assigned star ratings on both sides is the strongest option available.
2. **Comparable record length.** A 4× mismatch changes what "one chunk" means and
   contaminates every compression measurement.
3. **Comparable surface shape** — the "long comment = negative" effect of §4.1.
   What matters is the **gap between the halves**, not either half's level.
4. **Both halves reach the same length tiers.** A corpus whose smallest class is
   too small cannot support a 500K-token document without the ranking questions
   becoming guessable.

Plus **one veto: the licence.** A closer match is not worth a corpus we cannot
redistribute. Then we built both halves and kept the pairing with the lowest
**twin asymmetry**.

| candidate pairing | label provenance | mean record length | twin asymmetry | verdict |
|---|---|---|---|---|
| MASSIVE tr ↔ en | identical (same utterances) | identical by construction | 0.017 | **ships** — the only true record-matched twin |
| `musteri_tr` ↔ `marc_en` | author's stars, both | 13.8 vs 34.1 w (2.5×) | **0.010** | **ships** — lowest measured anywhere |
| `vitamins_tr` ↔ `amazon_hpc_en` | author's stars, both | 12.1 vs 44.8 w (3.7×) | 0.015 | **ships** — the only pair with an entity axis |
| We-Bears ↔ airline tweets | **undocumented** vs crowd humans | 24.2 vs 15.7 w | **0.108** | **withdrawn** (§4.2) |
| MüşteriYorumları ↔ Amazon Home & Kitchen | author's stars, both | 13.2 vs 71.8 w (5.4×) | 0.106 | rejected — no Amazon category is terse enough |
| MüşteriYorumları ↔ `app_reviews` | author's stars, both | **13.8 vs 14.7 w (1.06×)** | 0.030 | **rejected on licence**, despite the closest length match we found |
| SIB-200 tr ↔ en | identical, parallel | identical | — | structurally dead: 1,004 rows total, ~14K token ceiling |
| XNLI tr ↔ en | identical, parallel | identical | — | structurally dead: 7,500 human-translated rows; the large split is machine-translated |

**What "twin asymmetry" means in one sentence:** we run a deliberately stupid
program that ignores meaning entirely against both halves of a pair, and the
asymmetry is the *gap* between how well it does on each half. A large gap means
the two halves are not comparable, which would destroy the cross-lingual claim no
matter how good the models we test are.

**And the ceiling we hit.** A parallel corpus gives a record-matched twin for
free, which is the strongest possible design — but human translation is expensive,
so every parallel corpus is small, and we need a large pool to draw independent
100K–1M-token documents from. **MASSIVE, at 16,521 parallel utterances, is the
largest parallel Turkish resource that exists**, and it is already our intent
axis. That is a ceiling on the design, not a gap in the search.

---

## 4. Two data problems we found, and how we handled them

### 4.1 The "long comment = negative" correlation

In almost every review corpus, unhappy customers write more. That means **record
length partly predicts the label** — which means a program that never reads a
single word, and only measures sentence length and looks for punctuation, can
classify records well enough to aggregate over them.

We built exactly that program (we call it the **format solver**) and ran it
against every source:

| source | longest class | shortest class | spread |
|---|---|---|---|
| `vitamins_tr` | olumsuz 15.0 w | olumlu 9.8 w | 1.5× |
| `musteri_tr` | olumsuz | olumlu | 1.2× |
| `marc_en` | negative | positive | 1.1× |
| `amazon_hpc_en` | **positive** 46.9 w | negative 41.8 w | 1.1× |
| *We-Bears (withdrawn, §4.2)* | *olumsuz 33.1 w* | *olumlu 9.1 w* | ***3.6×*** |

Note that `amazon_hpc_en` runs the *other* way — there the positive reviews are
longer. The correlation is real but its direction is corpus-specific.

**How we reason about this, and it is the part worth explaining to a reviewer.** A
format-solvable corpus still yields a **valid aggregation task**: the model must
still classify thousands of records and combine the results, whichever cue it
leans on. What it stops being is a test of *reading Turkish*.

That is only fatal when the effect is **asymmetric across a twin** — because then
a model could score well on the Turkish half by measuring sentence lengths while
having to genuinely read the English half, and any cross-lingual difference we
measured would be an artifact of formatting rather than of language.

**So the number we gate on is not either half's level — it is the gap.** Every
shipping pair is at or below **0.033**; the pair that sat at **0.108** was
withdrawn. All eight sets also clear an absolute gate (no set exceeds +0.15 mean
lift over the majority baseline), and the full audit is committed to the repo as
evidence rather than asserted.

**One family fails this test everywhere and we report it rather than bury it:**
`shift` (§2.2), where the solver gains +0.10 to +0.40. `shift` therefore carries
no headline result.

**The most expensive lesson we learned here** deserves one line, because it
changed our procedure: source-level style measurements do **not** predict
question-level exploitability. We once built an entire replacement corpus pair
because the source-level number looked disqualifying — and the question-level
asymmetry moved from 0.108 to 0.106, i.e. not at all, because prior-randomised
sampling absorbs most of it. **Always run the solver against the built questions,
never against the raw corpus.**

### 4.2 Why we removed the We-Bears corpus

We had a fifth pair — a Turkish brand-review corpus paired with English airline
tweets. **It was withdrawn on 2026-08-30, and label noise is not the reason.**

The reason is **label provenance**: the upstream dataset card does not document
where its labels came from — who or what assigned them. We then found the
signature that explains why:

| check | We-Bears (Turkish) | airline tweets (its English twin, human-annotated) |
|---|---|---|
| duplicate texts that carry *conflicting* labels | **0 out of 262 groups** | **17.1%** |

**Why that is damning in plain terms:** if you give two people the same sentence,
they sometimes disagree. Human annotation always leaves a trail of contradictions
like that — 17.1% here. A corpus where the identical sentence *always* gets the
identical label is a corpus where the label was computed by a rule, not judged by
a person. We could not find out what that rule was.

Two supporting numbers:

- Its **twin asymmetry** was **0.108**, against 0.010–0.017 for every pair we
  kept. (Twin asymmetry measures how differently a "cheating" program that ignores
  meaning performs on the two halves of a pair. A high number means the two halves
  are not really comparable, which destroys the cross-lingual claim.)
- Its **length spread was 3.6×** — by far the worst case of the §4.1 problem, and
  four times worse than anything we kept.

**Filtering can fix noise. It cannot fix not knowing where a label came from.** So
the pair went, and one question type (`top_k`, ordered ranking) went with it,
because that corpus was the only one where it passed our fairness check.

**What we lost, stated honestly:** ordered-ranking questions, and the fact that our
entity questions now rest on a single corpus (`vitamins_tr`). Both are limitations
we will state in the paper.

---

## 5. Do we need to double-check label noise? Should we run sentiment analysis?

### 5.1 The short answer

**Mostly no, and the reason is structural rather than convenient.** Five of our
eight sets do not have annotations at all.

| source | where the label comes from | is classical label noise possible? |
|---|---|---|
| `vitamins_tr`, `musteri_tr`, `marc_en`, `amazon_hpc_en` | **the star rating the writer of the review gave** | **~0 by construction** |
| MASSIVE (`tr_intent`, `en_intent`, +paired) | professional annotation | low, currently unmeasured |
| ~~We-Bears / airline~~ | undocumented / crowd | **withdrawn, §4.2** |

A star rating is a **recorded fact about the record** — the person typed the text
*and* chose the stars. It is not somebody's later estimate of a hidden truth. There
is no annotator to disagree with, so there is nothing to correct. Our benchmark
asks *"how many records carry label X"*, and that number is exact.

### 5.2 Should we run a sentiment model over the data as a check?

**No — and it is worth being precise about why, because it is the natural instinct
and it is the wrong tool here.**

1. **It would measure the wrong thing.** A sentiment classifier disagreeing with a
   4-star review does not mean the label is wrong. It means the model and the
   customer disagree. On a star-derived set the customer is right by definition.
2. **The benchmark never asks about sentiment.** It asks how many records carry
   label X. Even if a review is sarcastically positive, it *does* carry the label
   `olumlu`, and the count is still correct.
3. **It is circular.** Using a language model to validate labels that we will then
   use to grade language models bakes that model's biases into our ground truth.
4. **On the one set where a check is genuinely needed (MASSIVE), sentiment analysis
   does not apply at all** — the labels are 48 intent categories like
   `alarm_set` and `transport_taxi`, not sentiment.

### 5.3 What we are doing instead, and what it costs

For MASSIVE only, a **human** check: 150 pair-aligned rows, already generated and
sent to you, where a Turkish speaker ticks whether the label is right. It looks
like this:

```
#   pair_id     Turkish utterance                      English utterance                    label            correct? (e/h)
1   dev:15753   sabahattin önderden araba kazası …     when did i get an email from …       email_query
2   train:8176  gelecek pazartesi öğleden sonra …      can you schedule a meeting with …    calendar_set
3   test:15792  bugün kiminle buluşacağım              who am i meeting today               calendar_query
```

150 rows gives us **±4.8 points of precision** if the true error rate is around
10%, and ±3.5 points if it is around 5%. That is enough to write a number in the
datacard. Roughly one to two hours of reading.

### 5.4 We have already bounded the *consequence*, which is the part that matters

Even without knowing the exact noise rate, we know what noise can do. Label noise
never makes an answer wrong; it caps the score a semantically perfect model could
reach, and that cap depends heavily on the question type:

| question type | at 2% noise | at 5% | at 10% |
|---|---|---|---|
| `count` (answer ≈ 3,900) | 0.36 | 0.25 | 0.19 |
| `proportion` | — | 0.95 | 0.92 |
| `most_common`, `pairwise`, ranking | probability the answer flips is **below 1 in a million** at every rate tested | | |

**Conclusion we act on:** headline results are reported on the ranking and
proportion families, which are essentially immune, and raw counts are read through
the scale-free `relative` metric. This is already written into the datacard.

**One thing a sentiment model would legitimately be good for**, as a descriptive
statistic rather than a correction: characterising the 3-star → `nötr` class, which
is the genuinely ambiguous one. Worth a paragraph in the datacard, not a change to
the data.

---

## 6. What the RLM-Qwen model was actually trained on

This matters because it is the direct precedent for §8.

**The model:** `mit-oasys/rlm-qwen3-8b-v0.1`, released by the Recursive Language
Models authors (Zhang, Kraska & Khattab, 2026). It is Qwen3-8B **post-trained on
1,000 "recursion trajectories"** distilled from a much larger 480B coding model, on
LongBenchPro tasks. Result: **+28.3% over the base model**.

**What a "trajectory" is, in plain terms.** In the RLM setup, the long document is
*not* pasted into the prompt. It is put into a Python variable, and the model writes
code to look at it. A trajectory is the **full transcript of that session** — every
piece of code the model wrote, what the code printed back, what it did next, and
the final answer. The model is then trained to imitate those transcripts.

Schematically, one training example looks like this *(illustrative — I have not
inspected their released file format, only the described method)*:

```
PROMPT   How many of these reviews are negative?
         (the document is in the variable `ctx`, 400,000 tokens — not shown to the model)

STEP 1   code:  print(len(ctx), ctx[:300])
         out:   1893422  "Ürün aşırı dandik. Görselde fırın ve …"

STEP 2   code:  chunks = ctx.split("<<<###>>>")
                print(len(chunks))
         out:   9873

STEP 3   code:  answers = [call_child(f"Kaç tanesi olumsuz? {c}")
                           for c in batch(chunks, 200)]
         out:   [37, 41, 33, 45, …]

STEP 4   code:  print(sum(answers))
         out:   1712

ANSWER   1712
```

The training signal is **not** "question → 1712". It is **"question → this
sequence of moves"**. That distinction is the whole point, and it is what §8 is
about.

**How the 1,000 examples were produced:** run a very strong model (the 480B coder)
on the tasks, record its transcripts, **throw away every transcript whose final
answer was wrong**, and train the small model on what survives. This is called
rejection sampling, and it is the standard recipe.

**The two related results in the literature:**

| work | trained on | result |
|---|---|---|
| Zhang et al. (2026) | 1,000 recursion trajectories | `rlm-qwen3-8b-v0.1`, **+28.3%** over base |
| Kim & Ahmad (2026) | evidence-selection trajectories over papers | a **4B** model scored 0.600 vs Claude Sonnet's 0.607, at **7s/query vs 60s+** |
| Xiong et al. (ICLR 2025) | synthetic key-value *retrieval* | **+10.5%** transfer to a real benchmark it never trained on |

**Note carefully: nobody in that table trained on an aggregation task, and nobody
trained in any language other than English.**

---

## 7. Publication — what is settled and what is not

### 7.1 Licences: settled. Nothing blocks us, and no permission emails are needed

| set | licence | can we redistribute the text? |
|---|---|---|
| `tr_intent`, `en_intent` (+paired) | CC-BY-4.0 | yes |
| `vitamins_tr` | CC-BY-SA-4.0 (**share-alike**) | yes |
| `musteri_tr` | CC-BY-SA-4.0 (**share-alike**) | yes |
| `marc_en` | Apache-2.0 | yes |
| `amazon_hpc_en` | **no licence exists** | **no — we withhold the text** |

Three practical consequences, all already handled in code:

1. **Amazon has no licence.** Checked exhaustively on 2026-08-30: no licence tag,
   no licence field, **no LICENSE file among 912 files in the repository**, no terms
   on the dataset card, no terms on the project website. Silence is not permission.
   So for that set we ship **the questions and answers but not the review text**;
   users rebuild it locally with our script. This is a standard pattern.
2. **Share-alike is contagious.** Two Turkish sets are CC-BY-SA-4.0, which would
   infect everything if we shipped one flat dataset. So the release is **one
   configuration per source**, and our publishing script enforces it.
3. **Our repo's MIT LICENSE covers the code only.** One line needs adding to say
   so before release. *(To-do, five minutes.)*

**No non-commercial clause remains anywhere** — the airline corpus was the only one
and it left with the withdrawn pair.

We also **rejected one otherwise-better corpus purely on licence grounds**
(`sealuzh/app_reviews`, tagged `license:unknown`), even though it was a closer
length match to the Turkish data. Worth mentioning as evidence of care.

### 7.2 The real question marks, ranked

| # | issue | is it a blocker? |
|---|---|---|
| 1 | **No model has ever been run on the benchmark.** Every difficulty claim is a chance rate or a theoretical ceiling, never a measurement. | **Blocker for a paper. Not a blocker for releasing the dataset.** |
| 2 | Our fairness certification was run at n=10–20 per family, and our own README says that certifies nothing. One family is flagged unresolved (`en_intent` `most_common`). | Should be re-run at n=250 before release. Cheap. |
| 3 | Label-noise rate unmeasured on the annotated sets (§5) | State it in the datacard. Not a defect. |
| 4 | No timeline axis (§2.2) | State it as a limitation. Blocked on data. |
| 5 | Documents in the same length tier share 20–38% of their records | Means our error bars need a specific statistical treatment. Note it. |

**Recommended sequence: release the dataset now, run the baselines, then submit the
paper.** The release timestamp establishes priority and costs nothing, and item 1
is a paper blocker rather than a release blocker.

---

## 8. NEW — should we also publish a trajectory dataset?

**Main item for discussion.**

### 8.1 What we would do

Exactly the recipe that produced RLM-Qwen3-8B (§6):

> Run models on our benchmark. **Log every step** — every piece of code the root
> writes, every sub-call, every intermediate output. Compare the final answer to
> our gold answer. **Keep only the transcripts that ended up correct.** That is the
> dataset.

Two artifacts: **release 1** the benchmark (finished), **release 2** the
trajectories (after the evaluation). We train nothing ourselves.

### 8.2 Why it is worth doing

1. **It is free.** The transcripts are a by-product of the evaluation we must run
   anyway — *if the harness logs them from the first run.* Instrument it later and
   we pay for the whole evaluation twice.
2. **We can verify every step, not just the answer.** Every existing trajectory
   dataset filters on the final answer only, so a transcript that got the right
   number by luck survives. We built the document, so we know the label of every
   record and where it sits — for any chunk the model picks we can compute the true
   count inside it and check each intermediate step. Nobody can do this on
   LongBench or on papers, because there is no ground truth below the final answer.
3. **The matched twin makes the training question controllable.** The same
   trajectory exists in Turkish and English with the same gold answer, so we can
   test whether what transfers is *aggregation* ability or *Turkish* ability.

### 8.3 Your question: the trajectories will be in English — does that still help Turkish?

**Partly, and the useful part is knowing which layer carries the Turkish.** In the
RLM setup the document is never in the prompt — it sits in a Python variable — so
the two roles get completely different training signal:

| role | what it is trained on | Turkish signal |
|---|---|---|
| **root** | the question, Python code, a few hundred characters of previewed text | **almost none** — the skill (chunk, delegate, combine) is language-neutral, so English narration costs us nothing |
| **child** | a few thousand tokens of Turkish reviews + a short instruction | **this is where all of it is** |

**Consequence: log both roles, not just the root.** If we only keep root traces we
throw the Turkish away. Training a single shared policy over both roles is what
Kim & Ahmad did, and it worked at 4B.

What this teaches is Turkish *understanding under compression*, not Turkish
*generation*. It is **not** pre-training data — those corpora are tens of billions
of tokens; ours is 28M and half English. Post-training is the right frame:
RLM-Qwen3-8B gained +28.3% from **1,000** trajectories, which we could produce.

### 8.4 Should we force the model to think in Turkish?

**No as the default, yes as a cheap ablation.** Against making it default: the
root's job is writing Python, and code models are trained on English-commented
code, so forcing Turkish likely produces worse code and fewer usable trajectories;
it also adds Turkish *generation* as a third variable to the exact confound our
cross-lingual design exists to remove; and it targets the layer with the least
Turkish in it.

But it is worth one small experiment — same documents, same questions:

| condition | root reasons in | child instruction in |
|---|---|---|
| A (default) | English | English |
| B | English | **Turkish** |
| C | Turkish | Turkish |

If B beats A the finding is "match instruction language to content language" —
small, clean, unpublished for Turkish. My prior: B is interesting, C loses.

### 8.5 The objection that has to be answered first: is it just leakage?

**If a trained 1.5B beats an untrained 4B on our own benchmark, that result is
uninterpretable by default.** Two separate deflating explanations:

- **Contamination** — the model saw the answers, or close enough.
- **Protocol familiarity** — the trained model knows how to *be* an RLM root and
  the untrained one does not. That is knowing our scaffold, not aggregating.

**And splitting haystacks train/test does not fix the contamination**, because our
documents are drawn from a shared pool. Measured from the manifests:

| set / tier | mean record overlap between two haystacks | one haystack = this share of the pool |
|---|---|---|
| `en_intent` 100K | **0.389** | **0.531** |
| `vitamins_tr` 750K | 0.378 | — |
| `tr_intent` 100K | 0.279 | 0.403 |
| `amazon_hpc_en` 1M | 0.213 | — |

At the 100K intent tier one document is **53% of the whole corpus**. A model can
memorise per-record labels from training documents and reuse them at test time —
which is learning a classifier over our pool, not learning to aggregate. **This
must be a build-time partition of the source rows, before any document is
assembled.** We do not currently have that flag.

**Controls that would make the claim survive, strongest first:**

1. **Train on English traces, test on Turkish.** Zero Turkish leakage by
   construction. **No other benchmark can run this control** — it exists only
   because of the matched twin.
2. Train on `vitamins_tr`, test on `musteri_tr` — held-out corpus, not just
   held-out records.
3. Disjoint record pools at build time (above).
4. Held-out question family; and, where possible, an English out-of-benchmark eval
   (LongBench, RULER) to show the skill transferred at all.

**And the headline should not be "1.5B beats 4B."** The informative comparisons are
1.5B trained vs 1.5B *untrained*, and 1.5B trained vs 4B *trained* — which reframes
it as "training buys N× effective parameters," a size-ladder result that fits the
existing proposal and is much harder to deflate.

*Worth checking before we lean on it: the +28.3% for RLM-Qwen3-8B came from
LongBenchPro-derived trajectories and I do not know how they split train from test.
If they did not hold out, the same objection applies to their number.*

### 8.6 Verdict

**Good idea, recommend it — as future work, with two engineering decisions taken
now, before anything is built or run:**

> 1. **Log full transcripts, both roles, from the first evaluation run.**
> 2. **Add a build-time train/test split of the source record pool**, so a
>    trajectory set can ever be used for training without contaminating the
>    benchmark.

Both are engineering, not research. A day or two now; a full re-run of every
experiment plus an unanswerable reviewer objection if we skip them.

The thesis paragraph, phrased as a design rather than a result:

> The benchmark is constructed so that ground truth is computed by an explicit
> decomposition. That makes it a source not only of evaluation items but of
> *verifiable decomposition trajectories*, which prior work suggests are the
> effective training signal for recursive scaffolds. Because the record-matched
> intent axis yields identical trajectories in two languages, it further permits a
> controlled test of whether such training transfers as aggregation ability or as
> language ability — an open question this resource makes answerable for the first
> time.

**Sequencing:** release 1 now → evaluate **with logging on** → release 2 with the
paper that analyses it.

---

## 9. Questions I would like your view on

1. Do we release the dataset now (before any model has been run), to establish the
   timestamp — or hold it until we have baselines?
2. Do we approve the two engineering items in §8.6 — transcript logging for both
   roles, and a build-time train/test split of the record pool?
3. Is the three-condition language ablation of §8.4 (English vs Turkish child
   prompts) worth a slot in the experiment plan, or a distraction from the main
   size-ladder result?
4. Is the missing timeline axis (§2.5) something we accept as a stated limitation,
   or do we spend time hunting for a dated Turkish labelled corpus?
5. Should the thesis title lead with the benchmark rather than the method, given
   that the benchmark is the contribution that survives every scope cut?
