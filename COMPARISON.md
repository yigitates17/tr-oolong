# OOLONG vs TR-OOLONG

**A reader with no access to the code should finish this page understanding both
benchmarks.** Every number and every example below is taken from the actual
released data, not from a paper summary. Verified 2026-08-25.

---

## 1. The one-paragraph version

**OOLONG** (Bertsch et al., 2025, arXiv:2511.02817) asks: can a model read a very
long document and answer questions about *the distribution of what is in it*? It
builds the document by gluing together rows from an ordinary labelled dataset,
then asks things like "which label is most common?" Answering requires
classifying every row and adding up the results, so searching the text does not
help. It is English-only.

**TR-OOLONG** (this work) applies the same construction principle to **Turkish**,
and pairs every Turkish set with an English twin built by the identical pipeline,
so that any difference measured between the two is a property of the language
rather than of the benchmark. It extends the question typology along an
**entity** axis and adds proportion questions, but it currently lacks OOLONG's
**timeline** axis.

---

## 2. How each one builds a haystack

Both concatenate labelled records. The difference is what metadata rides along.

**OOLONG** attaches a synthetic date and user ID to every record:

```
The following lines contain 10 text messages, one per line. Each text message
can be classified as spam or ham (i.e., not spam).

You will be asked to answer questions about the aggregate label statistics
across all 10 examples in this dataset. Do not try to guess, estimate, or
approximate the result. Calculate the exact answer given these datapoints.

Date: Dec 28, 2022 || User: 76063 || Instance: Todays Vodafone nu...
Date: Mar 02, 2023 || User: 41288 || Instance: ...
```

**TR-OOLONG** prints the entity in a symbol-only marker, then joins with a fixed
delimiter. The marker carries no natural-language word, because `Marka:` and
`Brand:` tokenize differently and would confound the matched twin:

```
[[Nutraxin]] urun güzel fakat kokusu çok agır, insanı bile rahatsız ettiriyor

<<<###>>>

[[GetDirect]] orjinal ürün. güvenilir mağaza.

<<<###>>>

[[Newvit]] içimi kolay değil, çok şekerli bir tadı var
```

---

## 3. The structure of the question sets

OOLONG's design is best read as **task types × conditioning axes**. The same
handful of question shapes is asked three times: over all the data, over a
subset of users, and over a subset of dates.

|  | over everything | conditioned on **user** | conditioned on **time** |
|---|:---:|:---:|:---:|
| most frequent label | ✅ | ✅ | ✅ |
| least frequent label | ✅ | ✅ | ✅ |
| label A vs B (more/less/same) | ✅ | ✅ | ✅ |
| how many have label X | ✅ | ✅ | ✅ |
| which *user* / *date* appears most | — | ✅ | ✅ |
| which appears second-most | — | ✅ | ✅ |
| how many dates appear exactly *n* times | — | — | ✅ |

TR-OOLONG has the same idea but a different second axis, and no third:

|  | over everything | conditioned on **entity** | conditioned on **time** |
|---|:---:|:---:|:---:|
| most frequent label (`most_common`) | ✅ | — | ❌ |
| least frequent label (`least_common`) | ✅ | — | ❌ |
| second most frequent label (`second_most`) | ✅ | — | ❌ |
| how many have label X (`count`) | ✅ | ✅ `entity_count` | ❌ |
| **what share** have label X (`proportion`) | ✅ | — | ❌ |
| **label A vs label B** (`label_vs_label`) | ✅ **added v0.6.0** | — | ❌ |
| which entity has the most X (`entity_argmax`) | — | ✅ | ❌ |
| A or B, which has more X (`pairwise`) | — | ✅ | ❌ |
| ~~ordered top-k entities (`top_k`)~~ | — | ~~✅~~ **withdrawn v0.5.0** | ❌ |
| did X's share rise or fall (`shift`) | ✅ | — | ⚠️ positional halves, not dates |

**Read the two tables together and the picture is:** we match their counting
group **including their label-vs-label comparison as of v0.6.0**, we replace
their user axis with a real entity axis, we add normalised proportions, and
**we are missing their entire timeline
axis** — which their paper reports as the hardest of the three.

---

## 4. Real questions, side by side

### Counting, over everything

> **OOLONG** (spam, 2 labels)
> *"In the above data, which of the labels is the most common? Give your final
> answer in the form 'Label: answer' where answer is one of the labels: ham,
> spam."* → `spam`

> **TR-OOLONG** (`vitamins_tr`, 3 labels, 100K tokens)
> *"Bu yorumlarda en sık görülen etiket hangisi? Etiketler: 'nötr', 'olumlu',
> 'olumsuz'. Sadece etiket adını yaz."* → `olumlu`

> **TR-OOLONG** (`tr_intent`, 48 labels, 50K tokens)
> *"Bu kayıtlarda en sık görülen etiket hangisi? Etiketler: 'alarm_remove',
> 'general_joke', 'iot_cleaning', 'iot_hue_lightup', 'recommendation_movies'.
> Sadece etiket adını yaz."* → `iot_cleaning`

### Counting a single label

> **OOLONG**: *"how many data points should be classified as label 'ham'?"* → `4`
>
> **TR-OOLONG** (`musteri_tr`, 100K): *"Bu yorumlardan kaç tanesi 'olumlu'
> etiketli? Sadece sayıyı yaz."* → `881`

**Note the magnitude.** OOLONG's counts are single or double digits at the
lengths they report. Ours run into the thousands, which breaks their metric —
see §6.

### Conditioned on an entity / user

> **OOLONG**: *"only consider the subset of instances associated with user IDs
> 76063. Among instances associated with these users, which of the labels is the
> least common?"* → `ham`

> **TR-OOLONG** (`vitamins_tr`, 250K): *"Şu markalardan hangisi en çok 'olumlu'
> yorum aldı: 'Beeo', 'NBL', 'Nbt İlaç', 'Smartcaps', 'Suda Collagen'? Sadece
> marka adını yaz."* → `Smartcaps`

> **TR-OOLONG** (`amazon_hpc_en`, 500K): *"Which of these brands received the most
> 'negative' reviews: 'More of Me to Love', 'Panasonic', 'Professor Amos',
> 'Zenda Naturals', 'eHouse'?"* → `Professor Amos`

The difference matters: OOLONG's users are synthetic IDs attached at build time,
so the question is pure bookkeeping. Our entities are real brands drawn from the
corpus, and the candidate set is chosen so the five options have near-identical
corpus-level counts — meaning the answer cannot be guessed from world knowledge
or from corpus statistics, only from this haystack.

### Ordered ranking — implemented, then withdrawn

TR-OOLONG implemented `top_k` (order the 3 highest of 5 named candidates, chance
1/60). OOLONG has no ordered-ranking family, so it was a genuine extension. It
survived prior-neutrality on exactly one corpus, and **that corpus was withdrawn
in v0.5.0 over undocumented label provenance**, so `top_k` went with it. Exact
ordering is intrinsically the hardest family to make prior-neutral: flipping one
position is easy to randomise, permuting three independently is not.

### Time — theirs is real, ours is not

> **OOLONG**: *"was label 'spam' more common, less common, or the same frequency
> before 2024-07-24, as compared to after 2024-07-24?"* → `more common`
>
> **OOLONG**: *"only consider instances that occur in October of any year. Among
> instances occurring in October, which of the labels is the most common?"* → `spam`
>
> **OOLONG**: *"how many dates are represented exactly 1 times?"* → `10`

> **TR-OOLONG** (`vitamins_tr`, 100K): *"Yorumların ikinci yarısında 'olumsuz'
> oranı ilk yarıya göre arttı mı azaldı mı? 'arttı' veya 'azaldı' yaz."* → `arttı`

Ours is a **binary** question about the first versus second half of the
document, not about real calendar dates. It is the weakest family in the suite
and the honest gap against OOLONG. See §7.

### The matched twin — ours only

Because the intent axis is built from a parallel corpus, the same question exists
in both languages with the **same gold answer**:

> **Turkish**: *"Bu kayıtlarda kaç tane 'transport_taxi' etiketli kayıt var?"* → `18`
>
> **English**: *"How many utterances have the intent 'transport_taxi'?"* → `18`

100 of 120 questions in the record-matched pair share a byte-identical answer.
OOLONG has no cross-lingual dimension at all.

---

## 5. Size, side by side

| | OOLONG | TR-OOLONG |
|---|---|---|
| languages | English | **Turkish + matched English** |
| questions | 6,500 (synth) + 10,810 (real) | **1,254** |
| haystacks | not reported per split | **110** |
| context lengths | 1K–4M, reported at 8K–128K | 36K–987K |
| **shortest haystack** | — | **36,250 tokens** |
| **mean haystack** | — | **256,882 tokens** |
| **longest haystack** | — | **987,623 tokens** |
| total tokens built | — | **28.2 million** |
| records per haystack | not reported | 1,523 – 19,774 |
| label spaces | 2–10 | **3 and 48** |
| source corpora | 10 classification sets + D&D transcripts | 6 corpora on 2 axes |

Per set:

| set | lang | classes | haystacks | questions | min tok | mean tok | max tok | max records |
|---|---|---|---|---|---|---|---|---|
| `tr_intent` | tr | 48 | 10 | 120 | 49,981 | 74,992 | 99,998 | 6,169 |
| `en_intent` | en | 48 | 10 | 120 | 49,921 | 74,880 | 99,871 | 8,122 |
| `tr_intent_paired` | tr | 48 | 10 | 120 | 47,629 | 73,182 | 99,057 | 6,000 |
| `en_intent_paired` | en | 48 | 10 | 120 | 36,250 | 55,547 | 75,187 | 6,000 |
| `vitamins_tr` | tr | 3 | 20 | 237 | 99,217 | 397,122 | 744,785 | 19,774 |
| `amazon_hpc_en` | en | 3 | 20 | 236 | 98,672 | 456,691 | 987,623 | 16,116 |
| `musteri_tr` | tr | 3 | 15 | 153 | 99,137 | 281,100 | 496,238 | 13,618 |
| `marc_en` | en | 3 | 15 | 148 | 98,232 | 278,551 | 491,821 | 11,080 |

The `en_intent_paired` set is shorter in tokens than its Turkish twin at the same
record count. That gap **is** the measurement: at identical content, Turkish
costs **1.30–1.34x** the tokens of English.

---

## 6. Scoring, and why we added a metric

OOLONG scores numeric answers with `0.75^|y-ŷ|` — full credit when exact, decaying
as the answer drifts. That works when counts are small.

At our lengths it collapses. A typical `count` answer here is around 1,000 and
the largest is 12,225. `0.75^50` is about 6e-7, so a model off by 50 and a model
off by 5,000 both score zero. The metric stops distinguishing near-misses from
nonsense.

So we report **both**:

| metric | formula | purpose |
|---|---|---|
| `partial` | `0.75^\|y-ŷ\|` | **comparability with OOLONG.** Frozen, never changed |
| `relative` | `max(0, 1 - \|y-ŷ\|/max(y,1))` | **information.** Scale-free, so 2% off scores 0.98 |
| `exact` | 1 if equal | the strict reading |

---

## 7. Honest scorecard

**Where TR-OOLONG is ahead**

- Only cross-lingual long-context aggregation benchmark; the intent axis is a
  true record-matched twin.
- Much longer: to 987K tokens and 19,774 records per haystack.
- Larger label space: 48 classes against their 2–10.
- Real entities instead of synthetic user IDs, with candidate sets constructed to
  be prior-neutral.
- Normalised proportions, which OOLONG does not have. (Ordered top-k was also
  implemented and is described above; it was withdrawn with its only surviving
  corpus in v0.5.0.)
- Four shortcut solvers with committed manifests. OOLONG reports no such audit.
- Ground truth computed twice by independent code paths and asserted equal.

**Where OOLONG is ahead**

- **A real timeline axis** with six question shapes over calendar dates. Their
  paper reports it as the hardest group. Ours is one binary rose/fell over
  positional halves, and it is the only family our format solver beats
  (+0.400 / +0.300 / +0.267 / +0.100 across sets). **This is the real gap.**
- ~~A label-vs-label comparison family~~ — **implemented in v0.6.0** as
  `label_vs_label`, on all eight sets. It is 3-way at 48 classes and collapses to
  2-way at 3, where near-equality does not occur (D18).
- A "which user appears most often" family with no label conditioning at all.
- Far more questions: 17,310 against our 1,254.
- Two task flavours — synthetic plus real D&D transcripts. We have only the
  synthetic style.

**Why the timeline gap is not laziness.** It is blocked on data. Adding it needs
a labelled corpus with real dates in **both** languages. English has several
(`app_reviews` carries dates 2014–2017; Amazon-Reviews-2023 carries `timestamp`).
**No Turkish source examined carries dates** — `vitamins-supplements-reviews` is
`product_name, brand, text, star`, and MüşteriYorumları is `text, label`. Finding
a dated labelled Turkish corpus is the unblocking step. See `DATASET_REVIEW.md`.

---

## 8. What is taken from OOLONG, precisely

From the **paper**, since their construction, scoring and analysis code are all
still listed as unreleased:

- the **construction principle** — concatenate rows from a labelled dataset and
  derive every answer from the labels, so ground truth needs no annotation;
- the **counting typology** — `most_common` and `least_common` mirror their
  `MOST_FREQ` and `LEAST_FREQ`. (`second_most` is an **extension**: they have
  second-most *user* and second-most *date*, but no second-most *label*.)
- the **numeric metric** `0.75^|y-ŷ|`, implemented from its published definition.

Everything else — the generator, Turkish handling, the matched twin, the entity
axis, per-string tokenizer measurement, dual-path ground truth, the four
acceptance gates, the reproducible manifests — is built here.
