# Turkish source review — the short version

**One document for every source question.** Absorbs the former
`PAIRING_SEARCH.md` and `MUSTERI_TRIAL.md`.

**Question asked:** is We-Bears good enough, and is anything better available?
**Answer:** We-Bears is the weakest source in the repo and is already labelled
secondary. Nothing found beats the primary pair. One candidate would improve on
We-Bears specifically, at the cost of four question families.

Measured 2026-08-25 across `ytu-ce-cosmos`, `turkish-nlp-suite` and `Trendyol`.

---

## The table

`R_max` = largest haystack the pool can support (`smallest_class × K` records).
`style` = how much of the label a length-and-punctuation-only classifier
recovers, over the majority baseline. `spread` = longest class's mean word count
÷ shortest's.

| source | rows | classes | imbalance | ceiling | style | spread | licence |
|---|---|---|---|---|---|---|---|
| **`vitamins_tr`** (in use, primary) | 43,043 | 3 | 2.3x | 602K | +0.048 | 1.5x | CC-BY-SA-4.0 |
| ~~We-Bears~~ (**withdrawn v0.5.0**) | 25,186 | 3 | 4.1x | 527K | **+0.120** | **3.6x** | Apache-2.0 |
| MüşteriYorumları | 73,920 | 3 | 3.4x | **970K** | **+0.004** | **1.2x** | CC-BY-SA-4.0 |
| BüyükSinema | 67,328 | **10** | 10.1x | **1.5M** | +0.000 | 1.6x | CC-BY-SA-4.0 |
| TurkishHateMap | 42,175 | 4 | 32.9x | 414K | +0.000 | **6.8x** | CC-BY-SA-4.0 |
| guardrail-tr (top-5 classes) | 114,353 | 5 | **59.2x** | **259K** | +0.000 | 1.4x | Apache-2.0 |

---

## Verdicts, one line each

**`vitamins_tr` — keep as primary.** Not because it wins on every number, but
because it is the only Turkish source with a **brand column that is statistically
independent of the label** (normalised MI 0.022). That independence is what makes
`entity_count`, `entity_argmax`, `pairwise` and `top_k` possible. Every other
candidate has no entity column or a correlated one.

**We-Bears — WITHDRAWN 2026-08-30.** Three independent marks against it:
a +0.120 style shortcut (7x its English twin's), a 3.6x length spread, and **0
conflicting labels across 262 duplicate-text groups** where the human-annotated
airline twin has 17.1%. That last one means labels are a deterministic function
of text, which humans do not produce. Its provenance is undocumented upstream.

**MüşteriYorumları — the only genuine upgrade over We-Bears.** Better on every
axis: style +0.004 vs +0.120, spread 1.2x vs 3.6x, ceiling 970K vs 527K, and the
label is the customer's own star rating rather than undocumented. **Cost: no
product or brand column, so it carries 6 of 10 families.** That is the whole
trade-off.

**BüyükSinema — rejected.** 10 classes and a 1.5M ceiling are attractive, but
10x imbalance and **93.7% of duplicate-text rows carry conflicting stars** —
the same review text rated 7 by one user and 8 by another. That is real
subjectivity in a 10-point scale, and it would sit directly under our numeric
metric.

**TurkishHateMap — rejected.** Human-annotated by a professional team, which is a
genuine plus, but 33x imbalance, a 414K ceiling, a **6.8x length spread** (the
worst measured), and target group correlates with label (MI 0.151) so it gives no
usable entity axis. BERTurk reaches only 0.61 on it, meaning the labels are
highly subjective. Distributing hate-speech text is a separate cost.

**guardrail-tr — rejected for this benchmark, and the reasoning is worth reading
because it is not the obvious one.**

---

## guardrail-tr in detail

You asked about this one specifically, and it is a reasonable thing to want: YTU
COSMOS is a serious lab, the licence is Apache-2.0, and 405K rows sounds like
plenty.

**What is genuinely good about it.** The `language` column separates
**140,559 Turkish-origin rows** from the translated ones, which removes the
translation confound I originally rejected it for — that objection was wrong and
is withdrawn. Its style shortcut is +0.000 and its label leakage is 0.12%, both
excellent. A 10-class hazard taxonomy would sit usefully between our 3 and 48.

**Why it still cannot be used here: it is too skewed to make long haystacks.**
The Turkish-origin single-category rows break down as:

| category | rows |
|---|---|
| SAFE | 69,482 |
| HARASSMENT_OFFENSIVE | 34,857 |
| HATE_DISCRIMINATION | 6,668 |
| MISINFORMATION_POLITICAL | 2,173 |
| PRIVACY_VIOLATION | 1,691 |
| VIOLENT_CRIMES | 1,173 |
| SEXUAL_CONTENT_ADULT, SELF_HARM, CSAE, NON_VIOLENT, INJECTION | 21 – 900 each |

A haystack of *R* records over *K* classes gives each class about *R/K* on
average, so a class can only top the ranking if the pool can supply more than
*R/K* of it. The smallest class therefore caps the haystack at
`smallest_class × K` records. Even after cutting to the five largest classes,
that is **5,865 records ≈ 259K tokens**. Our review axis runs to 987K. guardrail
cannot reach the 500K or 1M tiers, which are the whole point of a long-context
benchmark.

**And it has no twin.** Every row is Turkish text, including the ones marked
`language=="en"` — those are translated *from* English, not English. So a twin
would have to be built from the upstream English corpora (OR-Bench, WildGuardMix,
toxic-chat) and relabelled under the same jury. That is real work, and it would
still not fix the length ceiling.

**Where it would fit.** As a third, monolingual axis testing label-space
difficulty in a non-review domain at ≤250K. Not as part of the cross-lingual
comparison.

---

## "If an LLM labels the data, why is that a problem for us?"

Short answer: **for most of our questions it is not a problem at all, and the
one place it bites is not the place people usually worry about.**

**Why it mostly does not matter.** Our ground truth is the label *as the dataset
defines it*. The question "how many records are labelled X" has an exact answer
regardless of whether a human, a star rating, or a jury of three models produced
X. The model being evaluated is being asked to reproduce a stated labelling
convention, not to be right in some absolute sense. So "we used a dataset from a
reputable lab, labelled by an LLM jury, and here is the citation" is a perfectly
defensible sentence, and reviewers accept it routinely.

**Where it does bite — three specific places.**

1. **Circularity, and this is the real one.** If the labels were produced by an
   LLM, then evaluating an LLM on reproducing them measures *agreement with
   another model*, not language understanding. Model families share blind spots.
   A Qwen-based system scored against Gemma/Qwen/GPT jury labels is partly being
   scored on how similar its training distribution is to theirs. For a thesis
   whose whole point is measuring what recursive processing does to *Turkish*,
   that confound sits exactly on the finding. **This is the argument that rules
   guardrail out of the cross-lingual comparison** — more than the skew, honestly.

2. **Asymmetric noise across the twin.** If the Turkish half is model-labelled
   and the English half is human-labelled, the two halves have different
   irreducible error, and the TR-vs-EN gap you measure is partly a gap between
   labelling procedures. Anything used for RQ4 must have matched provenance on
   both sides. This is why the primary pair uses the writer's own star rating on
   *both* halves.

3. **The accuracy ceiling on `count`.** Label noise of any origin caps what a
   perfect model can score. At the 100K tier even 2% noise caps `count` at 0.36
   under the OOLONG metric. Ranking families are immune and `proportion` is
   robust, so this is a metric-selection issue, not a data-rejection issue. Full
   table in `DATACARD.md`.

**Practical rule for this project.** LLM-labelled data is acceptable for a
**monolingual** axis where the task is explicitly "reproduce this convention".
It is not acceptable for the **cross-lingual** axis, where labelling procedure
must be identical on both sides and must not be another LLM's judgement.

---

## Recommendation

1. **Change nothing about the primary pair.** `vitamins_tr` ↔ `amazon_hpc_en`
   is sound and is the only pair with a usable entity axis.
2. **DONE (2026-08-25).** MüşteriYorumları added as a *third* Turkish review set
   alongside the existing ones rather than replacing We-Bears. It costs nothing,
   alongside the existing ones. Its twin is **MARC English**
   (`SetFit/amazon_reviews_multi_en`, Apache-2.0), not `app_reviews`: the latter
   is a closer length match but is tagged `license:unknown`, and MARC reached a
   **better** twin asymmetry anyway — **0.010, the lowest in the benchmark**.
3. **Do not adopt guardrail-tr for the cross-lingual axis**, for the circularity
   reason above and the 259K ceiling. Reconsider it only if a monolingual
   label-space-difficulty axis is wanted.
4. **~~We-Bears stays as a secondary robustness check.~~ WITHDRAWN 2026-08-30.**
   Provenance is the one defect filtering cannot fix — you cannot filter for not
   knowing where the labels came from. `top_k` was withdrawn with it, since that
   corpus was the only one where exact ordering passed prior-neutrality.


---

# The twin search

Every English corpus considered as a partner for a Turkish set, measured rather
than assumed. Target: a Turkish review set averages 12–14 words with a style lift
near zero.

## Amazon-Reviews-2023 — no category works

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

3.5–6.5x too long and +0.05 to +0.10 of style signal in every one, because "long
review = negative" is universal on Amazon. Home_and_Kitchen was near the **best**
of the eight, so re-picking the category does not help.

## Parallel corpora — dead on scale, not on quality

These give a record-matched twin by construction, the strongest possible design.
Both are far too small:

- **SIB-200** (tur/eng, 7 topic classes, FLORES-parallel): **1,004 rows total**,
  ceiling ≈ 14K tokens. Cannot reach even the 50K tier.
- **XNLI** (tr/en, 3 classes): human-translated portion is **7,500 rows**, which
  one 250K haystack would consume entirely. The 392,702-row train split is
  **machine-translated**, the exact confound the morphology claim must avoid.

**This is a ceiling on the design, not a gap in the search.** Human translation
is expensive, so parallel corpora are small, and this benchmark needs a large
pool for independent draws at 100K–1M tokens. MASSIVE, at 16.5K parallel
utterances, is the largest parallel Turkish resource that exists and is already
the intent axis.

## `sealuzh/app_reviews` — the one strong hit

F-Droid app reviews (Grano et al., 2017). 288,065 rows, 14.7 mean words, style
lift +0.000, 392 apps at entity MI 0.044, reaches 750K, and **it is one of
OOLONG's own ten source datasets**. Licence unstated upstream, so text is
withheld and rebuilt locally, the same treatment `amazon_hpc_en` gets.

**Its value is not as a replacement.** Substituted into the primary pair it gives
an asymmetry of 0.021 against the current 0.015, i.e. marginally worse. Its value
is (a) as MüşteriYorumları's twin, and (b) it carries a real **`date` column**
(2014–2017), the substrate for the timeline axis TR-OOLONG lacks.

## Measured pairings, all of them

| pairing | length match | asymmetry | verdict |
|---|---|---|---|
| MASSIVE tr ↔ en | identical | **0.015** | best; true record-matched twin |
| `vitamins_tr` ↔ `amazon_hpc_en` | 12.1 vs 44.8 w | **0.017** | ships as primary review pair |
| **MüşteriYorumları ↔ MARC English** | 13.8 vs 34.1 w | **0.010** | **ships. Lowest asymmetry measured; both halves Apache-2.0 / CC-BY-SA** |
| MüşteriYorumları ↔ `app_reviews` | **13.8 vs 14.7 w** | 0.030 | best *length* match, but `license:unknown` |
| `vitamins_tr` ↔ `app_reviews` | 12.1 vs 14.7 w | 0.021 | no better than the pair in use |
| MüşteriYorumları ↔ Amazon Home | 13.8 vs 67.3 w | 0.106 | rejected |
| ~~We-Bears ↔ airline tweets~~ | 24.2 vs 15.7 w | **0.108** | **withdrawn v0.5.0** |
| SIB-200 / XNLI | identical | — | structurally dead |

---

# A swap that was built, tested, and not adopted

MüşteriYorumları was first paired with Amazon `Home_and_Kitchen`, built in full
(138 questions each, 6 families, all gates passing), specifically to test whether
replacing We-Bears would fix the cross-lingual confound.

**It did not.** Twin asymmetry came out at 0.106 against the We-Bears pair's
0.108 — unchanged.

**The lesson, which cost the most to learn.** We-Bears has a +0.120 style lift at
the **source** level against its twin's +0.017, a 7x gap. That does **not**
propagate to question-level exploitability, because prior-randomised sampling
(D9) absorbs it. The swap was proposed on the source-level number alone and the
number that mattered did not move.

**Always run a solver against the built questions, not the source pool.**

The Amazon `Home_and_Kitchen` half also turned out to carry a `most_common` style
lift of +0.250 on its own, which is how `app_reviews` was found.

---

# Second sweep, 2026-09-04 — candidates raised after the search was closed

A fresh list of Turkish resources was reviewed. **None displaces anything in
use**, and the reasons are recorded here so the search stays closed with evidence
rather than by assertion.

**The structural filter, restated:** we need a **document-level latent class
label** — the label is the answer key, and aggregation is only meaningful if the
class must be *inferred* from the text. That eliminates most Turkish NLP
resources immediately.

| candidate | verdict |
|---|---|
| **SentiTurca** (234K, CC-BY-SA-4.0) | **no new data.** Its own card names the subsets: e-commerce *is* MüşteriYorumları, movies *is* BüyükSinema, hate *is* TurkishHateMap. All three already have verdicts above — one in use, two rejected |
| **winvoker/turkish-sentiment** (490K, CC-BY-SA-4.0) | **rejected.** Largest Turkish sentiment set found, but label provenance is undocumented *and* the card states it includes "random text inputs marked as neutral" — programmatic labelling, the exact We-Bears defect, stated openly |
| **Havadis** (745K, CC-BY-SA-4.0) | **confirms the earlier rejection.** Columns are `url` + `text`. No label, no date |
| **NLI-TR** (SNLI/MultiNLI-tr) | rejected: machine-translated (the reason XNLI's train split was rejected), and records are sentence *pairs*, structurally unlike every other set |
| InstrucTurca, Turkish-Alpaca, WikiRAG-TR, turkish-math-186k | instruction data — no class to count. InstrucTurca is additionally an OpenOrca translation |
| TNC, TS Corpus, TDD, METU, CC-100, OSCAR, BellaTurca, temiz-Wiki, lyrics/poems/idioms | unlabelled |
| UD treebanks, METU-Sabancı, HisTR, turkish-wikiNER | token-level labels; 9.7K–18.7K sentences is two orders too small |
| BosphorusSign22k, PMC-VQA-TR, turkce-kitap | multimodal |
| FSMTSAD | **not fully assessed.** Balanced hotel/movie/product sentiment with a domain column that could serve as an entity axis; GitHub-hosted with no clear licence. The one open thread from this sweep |

## The one real find: Interpress carries dates

[`yavuzkomecoglu/interpress_news_category_tr`](https://huggingface.co/datasets/yavuzkomecoglu/interpress_news_category_tr)
— 273,601 Turkish news articles, 17 categories, and a **`publishdatetime`
field in ISO 8601 spanning 2010–2017**.

**This is the only Turkish labelled source found that carries real dates**, and
dates are the blocker on the timeline axis — OOLONG's hardest question group and
our one honest structural gap. Three obstacles, in order:

1. **Licence: `unknown`.** The same veto that rejected `sealuzh/app_reviews`.
   *But* the pipeline already has a pattern for this — `amazon_hpc_en` ships
   text-withheld, questions and answers only, rebuilt locally from a fetch
   script. So it is not automatically dead; it would mean the **Turkish** half
   ships text-free, which is worse for a Turkish benchmark but not fatal.
2. **Label provenance undocumented.** For news the category is normally the
   publisher's own section — a recorded fact like a star rating rather than an
   annotation. Plausible, unverified, and provenance is exactly what we now fail
   pairs on.
3. **Record length.** `content` is full articles; the usable field is `title`,
   which then matches an English headline corpus well.

**English twin candidate:** HuffPost News Category (~210K, 42 categories, dated
2012–2022, headline + short description). Its licence was not verifiable from the
Kaggle page and must be checked before anyone invests in this.

**Next step is not code.** It is an email to the uploader or to Interpress asking
what terms the data is under. Until that is answered the timeline axis stays
blocked, and the correct thing to do is state it as a limitation.

---

# Third sweep, 2026-09-16: searching specifically for what fixes partial readability

**Why this sweep had a different target from the first two.** Those searched for
a *twin*: a corpus comparable to a Turkish one in provenance and label space.
This one searched for the two properties the partial-coverage measurements
showed actually matter (README 4e, `DESIGN_DECISIONS.md` D21):

1. **Many classes**, because a partial reader's error goes as
   `sqrt((1-f)/(f·m))` in the gold answer magnitude `m`, and more classes make
   every count smaller. A 3-class set over 6,000 records cannot have a small
   answer; a 16-class one can.
2. **Dates**, which are worth more than the class count. Dates give
   subset-scoped questions for free ("among the entries from April"), and they
   are what OOLONG's most sampling-resistant family depends on: its
   `REPRESENTED_N_TIMES` scores **0.005** for a 5% reader
   (`manifests/oolong_crosscheck.json`).

Every candidate below was checked by loading its actual columns, not its card.

| candidate | rows | classes | dates | verdict |
|---|---:|---:|:---:|---|
| `habanoz/haberler-news-tr-v1.0` | **169,603** | **16** (`Tag`) | no | **best Turkish find; blocked on licence** |
| `heegyu/news-category-dataset` (HuffPost) | 209,527 | **42** | **yes, 3,890 distinct** | available, but English only |
| `GoktugD/turkish-topic-classification-1.5m` | 1,500,000 | 20 | no | **rejected: synthetic text** |
| `yankihue/turkish-news-categories` | 24,097 | 7 | no | too few classes, under 30K |
| `savasy/ttc4900` | 4,900 | 7 | no | far too small |
| `anilguven/turkish_news_dataset` | 4,200 | 7 | no | far too small |
| `denizzhansahin/Turkish_News_CNN-News-2024` | 5,600 | 8 | no | too small |
| `oguzinc/turkish-news-articles-sequence-classification` | 68,713 | 2 | no | sentence-pair task, wrong shape |
| `yavuzkomecoglu/interpress_news_category_tr` | n/a | n/a | n/a | **now unloadable** |
| `alibayram/onedio_haberler` | n/a | n/a | n/a | gated repo, 403 |

**The two that decided the sweep.**

`GoktugD/turkish-topic-classification-1.5m` looked ideal on its card: 20 classes,
1.5M rows, Turkish. Its own columns disqualify it. `source_type` is
`synthetic_rule_based`, `provenance` is `synthetic://...`, and `template_id` has
**8 distinct values across 100,000 rows**. The text is template-generated. That
fails the `text_provenance` criterion outright, and 8 templates would be trivially
recoverable by `scripts/style_solver.py`. **Card claims are not evidence; load the
columns.**

`habanoz/haberler-news-tr-v1.0` is the real find and the frustrating one: 169,603
rows of genuine Turkish news, a 16-class `Tag` column that is the publisher's own
section (the same kind of found label as a star rating), and a `Summary` field
that is the right length for a haystack record. It would give the review axis a
third label-space point (3, 16, 48) and would make rare-label counts available
outside the intent axis for the first time. **It declares no licence at all.**
That is the same veto that rejected `sealuzh/app_reviews` and that
`scripts/check_solo.py` fails on. Not adopted.

**The Interpress entry above is now doubly blocked.** The second sweep left it
pending an email about terms. It is now also unloadable: the repository contains
only `README.md` and a loading script, with no data files, and script-based
datasets no longer load under current `datasets` versions.

**Result, and it is a result rather than a gap.** *No Turkish corpus carrying
per-record dates was found among Interpress, Onedio, Habanoz, TTC-4900, the
CNN-Türk and Onedio news dumps, the YTU-CE-COSMOS collection, the Trendyol
collection, and the turkish-nlp-suite collection.* The English side is solved
(HuffPost has 42 categories, dates and an author axis) and the Turkish side is
not, so **the date axis cannot be twinned and stays blocked**. State it that way
in DATACARD rather than as an unexplored direction.

**What would unblock it, in order of cost:** a licence answer from the uploader
of `habanoz/haberler-news-tr-v1.0` (unblocks 16 classes, not dates); a Turkish
news archive with publication dates under a declared licence (unblocks both);
or scraping one, which reintroduces every provenance problem this project has
so far refused.


## Third sweep, continued: what a wider search added

The first pass of this sweep ran about ten keyword queries. A wider one followed,
covering parallel and multilingual corpora containing Turkish, Turkish product and
e-commerce category sets, and the MTEB collection. Two things changed and one
limit of the search itself is worth stating.

**RESOLVED: the HuffPost licence question from the second sweep.** That sweep left
it as *"its licence was not verifiable from the Kaggle page and must be checked
before anyone invests in this."* Checked: `heegyu/news-category-dataset` declares
**`cc-by-4.0`** and credits the Kaggle original. 209,527 rows, **42 categories**,
a `date` column with 3,890 distinct dates, and an `authors` column with 29,169
values, which is a second entity axis. The English side of a dated, many-class
pair is therefore fully available and clean. It is not adopted, because a
Turkish counterpart does not exist and an English-only set cannot be twinned. It
is the partner to reach for the moment one does.

**HARDENED: the Turkish news candidate is rejected on provenance, not just
licence.** `habanoz/haberler-news-tr-v1.0` has a README containing **only the
auto-generated schema block**: no licence, no description, no source attribution,
no statement of where 169,603 Turkish news articles came from. That is not a
missing licence tag, it is the absence of any provenance at all, which is the
same ground on which the Turkish brand-review pair was withdrawn in v0.5.0 and
`sealuzh/app_reviews` was rejected. Firmly out.

**Confirmed dead on scale, with numbers this time:**

| candidate | what it actually is | why not |
|---|---|---|
| `mteb/sib200`, `Davlan/sib200` | 7 categories, genuinely parallel across 200+ languages | **701 rows per language.** A single 100K-token document needs ~1,500 |
| `cis-lmu/Taxi1500-RawData` | 6 categories, bible verses | same scale problem, and the register is wrong |
| `Hulusiaa/turkish-product-category-finetune-openai` | 28,474 rows | chat-format fine-tuning file, a `messages` column of system/user structs, not a labelled corpus |
| `fthbrmnby/turkish_product_reviews`, `asparius/Turkish-Product-Review` | Turkish product reviews | sentiment, 2 to 3 classes: the label space this benchmark already has too much of |

**A limit of this search that should be stated rather than glossed.** Everything
above was searched on the Hugging Face Hub. Kaggle, Zenodo, institutional
repositories, TÜBİTAK collections and datasets released only as paper
supplements were **not** searched. The claim supported by this record is
therefore *"no suitable Turkish corpus was found on the Hugging Face Hub"*, not
*"none exists"*. A targeted look at Turkish university NLP group releases and at
Kaggle is the obvious next step and does not need code.

**Standing conclusion, unchanged by the wider search.** The English side of a
dated, many-class pair is solved and licence-clean. The Turkish side is not. The
date axis therefore cannot be twinned, and the three-category review sets keep
the partial-readability limitation described in README 4e.
