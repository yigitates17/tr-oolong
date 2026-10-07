# TR-OOLONG datacard

Covers **v0.10.0**: 11
subsets, 347 documents, 2,362 questions, 7 question types, Turkish and English
(1,615 / 747 questions). Every answer is computed
from the source dataset's labels, twice, by two independent pieces of code
that must agree. No answer was written by hand.

For what the benchmark is and how to use it, see the [README](README.md).

## Versions

| version | date | change |
|---|---|---|
| 0.7.0 | 2026-09-16 | 11 subsets, rare-label counts, difficulty grades; `shift` removed |
| 0.7.1 | 2026-09-20 | adds `uid`, `dataset`, `haystack_uid`. No question, answer, document or grade changed |
| 0.8.0 | 2026-09-28 | adds 174 close comparisons (`core`); removes the 137 brand questions; adds `role` to every question; stops releasing difficulty grades. Documents and all other questions unchanged |
| 0.9.0 | 2026-09-29 | adds 158 core documents with 244 close comparisons (418 core in total), 91 core questions identical in Turkish and English. All earlier documents and questions unchanged |
| 0.10.0 | 2026-10-01 | cleaning (newspaper mastheads, reviews that write their score, HTML); close comparisons only between label pairs that can be told apart from the text; film ratings converted to sentiment. 309 core questions, 77 identical across languages. Six datasets' documents changed; the intent and complaint documents did not |

## Fields

`questions.jsonl`, one question per line:

| field | meaning |
|---|---|
| `uid` | globally unique id, `<dataset>:<id>`. **Join and pool on this.** |
| `dataset` | subset name |
| `id` | question id, unique only within its subset |
| `haystack_uid` / `haystack_id` | the document the question is about (global / within subset) |
| `language` | `tr` or `en` |
| `target_tokens` / `target_records` | the document's length tier (by tokens, or by records for the paired sets) |
| `kind` | question type |
| `label`, `candidates`, `label_a`, `label_b` | what the question asks about |
| `unit` | `percent` or `per_mille`, on `proportion` questions |
| `answer` | the gold answer |
| `answer_key` | language-neutral form of a word answer (`label_vs_label`, `close_comparison`), for matching the Turkish and English pair |
| `rare` | true on a rare-label count (answer between 5 and 30) |
| `core_document` | true on questions (and documents) from core documents, built from exact label counts |
| `question` | the full question text |
| `role` | `core`, `retrieval` or `control`: what the question measures (see Known issues) |

`haystacks.jsonl`, one document per line: `uid`, `dataset`, `haystack_id`,
`haystack` (the text), `n_examples`, `drift_target`. **Give the model only
`haystack`.** The other fields are build metadata.

`manifest.json`: seed, full config, source hash, tokenizer, per-document token
and record counts, and the question-type counts.

## Sources

| subset | source | records | label, and who chose it | labels |
|---|---|---|---|---:|
| `tr_intent`, `tr_intent_paired` | Amazon MASSIVE, `tr-TR` | voice-assistant commands | intent, professional annotators (text is a human localization of English) | 48 |
| `en_intent`, `en_intent_paired` | Amazon MASSIVE, `en-US` | voice-assistant commands | intent, professional annotators | 48 |
| `vitamins_tr` | turkish-nlp-suite/vitamins-supplements-reviews (Vitaminler.com) | supplement reviews + brand | sentiment from the writer's own 1-5 stars | 3 |
| `amazon_hpc_en` | McAuley-Lab/Amazon-Reviews-2023, Health & Personal Care | product reviews + brand | sentiment from the writer's own stars | 3 |
| `musteri_tr` | turkish-nlp-suite/MusteriYorumlari (Hepsiburada, Trendyol) | shopping reviews | sentiment from the writer's own stars | 3 |
| `marc_en` | SetFit/amazon_reviews_multi_en (MARC) | shopping reviews | sentiment from the writer's own stars | 3 |
| `sinema_tr` | turkish-nlp-suite/BuyukSinema | film reviews | sentiment from the writer's own 1-10 rating | 3 |
| `sikayet_tr` | Kaggle savasy/multiclass-classification-data-for-turkish-tc32 | consumer complaints | product category, chosen by the person filing | 29 |
| `interpress_tr` | Interpress Turkish news, 270k | news articles | newspaper section, set by the publisher | 16 |

Star ratings map to sentiment as 1-2 negative, 3 neutral, 4-5 positive; the
film set's 10-point ratings as 1-4 negative, 5-6 neutral, 7-10 positive.

Notes per source, only where something is not obvious:

- **MASSIVE.** 12 of 60 intents were dropped because they have under 100
  examples; a label that small is the rarest in every document, which makes
  "least common" answerable without reading. Filters are applied to both
  languages together, so the Turkish and English halves keep the same
  utterances and labels. The Turkish text is localized, not literally
  translated: 1.8% of pairs differ in length by more than 2x because names were
  swapped for Turkish ones.
- **`sikayet_tr`.** The text column is really `title,body`. Only the body is
  used, because the title names the company. 89.7% of bodies ended in a
  scraping marker ("Devamını oku"), which was stripped. Three categories were
  dropped because their names appear in over 30% of their complaints
  (`kargo-nakliyat` 84.7%, `cep-telefon-kategori` 73.4%, `anne-bebek` 36.9%).
  The build must run with `leak_label_words: true`. Kaggle needs an account, so
  the fetch script takes a path to a local copy of `ticaret-yorum.csv`.
- **`interpress_tr`.** 2.1% of source records were a newspaper's masthead
  (publisher, editors, printing house) rather than an article; from v0.10.0 a
  record with 3 or more masthead job titles, or 2 plus an issue header ("Yıl: 3
  Sayı: 1531"), is removed. Records are full articles (median 1,650 characters), so a
  100K-token document holds about 200 of them. 35.1% of articles were removed
  because they name their own section, so the shipped articles are a filtered
  subset of the corpus. `savunma` fell below the size floor, leaving 16 of 17
  sections. The source has daily publication dates (2010-2017); they are kept
  but not used by any question.
- **`sinema_tr`.** Used with all 10 ratings as labels until v0.9.0. An exact
  rating cannot be read from the text ("loved it" can be a 7 or a 10), and every
  question type depended on it, so from v0.10.0 the ratings are mapped to
  sentiment. 11.2% of reviews wrote their score in the text ("6/10", "80/100")
  and are removed.
- **`vitamins_tr` / `amazon_hpc_en`.** The only pair with a brand per record,
  printed in the text as `[[Brand]]`. Questions about brands were removed in
  v0.8.0 because searching for the printed name answers them; the markers stay
  in the text so the documents are unchanged. English brands come from joining reviews
  to product metadata. English reviews name a different brand than their own
  13.8% of the time (Turkish: 0.66%), mostly because some brand names are
  ordinary words. Questions use the printed marker, so answers are unaffected.

Records removed for containing a label name: MASSIVE 0.0%, `sinema_tr` 0.3%,
`sikayet_tr` 24.6%, `interpress_tr` 35.1%. Reviews removed because they write
their score ("7/10", "5 yıldız veriyorum", "1 star"), from v0.10.0: film 6,129,
MARC 3,570, Amazon 1,488, shopping 639, supplements 449. HTML ("<br />", in
12.7% of Amazon reviews) is replaced by a space.

## Licences

Each subset keeps its source's licence and is a separate Hugging Face config.

| subset | licence | text shipped |
|---|---|:---:|
| `tr_intent`, `en_intent`, `tr_intent_paired`, `en_intent_paired` | CC-BY-4.0 | yes |
| `vitamins_tr`, `musteri_tr`, `sinema_tr` | CC-BY-SA-4.0 (share-alike: derived data stays CC-BY-SA-4.0) | yes |
| `marc_en` | Apache-2.0 | yes |
| `amazon_hpc_en` | none declared; text under Amazon's Conditions of Use | no |
| `sikayet_tr` | none declared; text scraped from a complaints website | no |
| `interpress_tr` | none declared (the Apache header on the Hub loading script covers the script, not the data) | no |

For the last three, the release contains questions, answers, grades and the
manifest. Counts over a dataset are facts, not copies of its text. The text is
rebuilt locally with the fetch script and config; the build is deterministic.

Source versions are pinned, so a rebuild reads the same bytes:

| source | pinned at |
|---|---|
| McAuley-Lab/Amazon-Reviews-2023 | `2b6d039e` |
| AmazonScience/massive | `ff6bd8e4` |
| turkish-nlp-suite/vitamins-supplements-reviews | `c4c0928e` |
| turkish-nlp-suite/MusteriYorumlari | `7579c679` |
| SetFit/amazon_reviews_multi_en | `ec73b665` |
| turkish-nlp-suite/BuyukSinema | `137d0ff7` |
| Interpress archive (plain download) | sha256 checked by `scripts/interpress_tr.py` |
| Kaggle TC32 | user's own copy; tied to the build by the manifest's source hash |

The code in the GitHub repository is MIT-licensed; the licence does not cover
the data.

## How documents and questions are built

1. Clean the source: length limits, remove duplicates, remove any record whose
   text contains a label name, drop labels with too few examples.
2. For each document, draw label shares at random (so documents differ in
   their label mix), sample records to fill the target length, and join them
   with a symbol separator (`<<<###>>>`). A symbol is used so the separator
   costs the same in both languages.
3. Put one label slightly over-represented in the second half ("drift"), so
   the document is not perfectly uniform from start to end.
4. Generate questions from the labels, with minimum sizes and margins so no
   answer is decided by one or two records: counts are at least 10 or 20
   (except rare counts), and labels being ranked must differ by a set margin
   (3% on the intent sets, 10-20% on the others; see each config).
5. Compute every answer twice with independent code and require agreement.
6. Add close comparisons in a separate pass with its own random seed: pairs of
   labels that each hold at least 30 records and 2% of the document, whose
   counts differ by between 0.35 and 0.60 divided by the square root of the
   smaller count (for counts near 300, a 2% to 3.5% gap). This is the one
   question type allowed small margins, on purpose. Excluded: "neutral"
   sentiment, and film ratings less than 3 stars apart, where annotators often
   disagree. At most 4 per document, with no label used twice. Which label is
   named first is random.
7. Add **core documents** (v0.9.0). Random label mixes rarely put two large
   labels close together, so these documents are built from exact counts: one
   or two pairs of labels each get a set share of the document (40% each for
   positive and negative on the review sets, 35% on the film set, 15% on
   complaints and news, 7% on intent) with a gap inside the step 6 window; the other labels
   share the rest. Sizes are in records (2,500 / 6,000 / 12,000 on the review
   sets, 3,000 on intent, 1,000 to 10,000 elsewhere, reaching about 1M tokens
   on complaints, news and films). The two counts differ by at least 5
   records. The two configs of a Turkish/English pair share their random
   draws, so their core documents have identical sizes and identical counts,
   and each core question is the same question in both languages. Only the
   designed pairs are asked. Two things are balanced by design rather than
   left to chance: which label of the pair is larger (alternating between the
   label more common in the source and the less common one, or between
   positive and negative), and whether the answer is the first-named label
   (every other question).
8. **Only separable label pairs** (v0.10.0). A close comparison may only use two
   labels that a word-count classifier tells apart at 0.8 or more AND that it
   recognises among all labels at least 60% of the time
   (`experiments/separable_pairs/`, one file per dataset; the Turkish and
   English intent sets share the pairs allowed in both languages). This rules
   out pairs decided by which box an editor, reviewer or filer ticked: news
   "turizm" vs "seyahat", or complaints filed under "alışveriş" about a refund
   with no product named. Labels kept for core pairs: 32 of 48 intents, 23 of 29
   complaint categories, 5 of 16 news sections (health, technology, celebrity,
   food, sport), and positive vs negative on every sentiment set.

## Label quality

- **MASSIVE intent.** A native speaker checked 150 Turkish records: 14 labels
  looked wrong, and a second check found 3 of those were in fact consistent
  with how the corpus uses the label. Error rate between 2.7% and 9.3%. Some of
  it comes from translation, not annotation: *"put a record on"* became
  *"bir kayıt koy"*, which no Turkish reader takes as "play music". Those
  errors affect only the Turkish half, so part of any Turkish/English gap on
  the intent sets could be translation noise. Separating the two needs a
  second pass judging each language separately (not done).
- **Star-rating sets.** The label is the writer's own rating, so there is no
  annotator to disagree with. Stars can still be hard to predict from text.
- **`sikayet_tr`, `interpress_tr`.** The label is a fact recorded at filing or
  publication, not an annotator's judgement. What limits scores is how well
  the label can be predicted from the text. A simulated reader that opens every
  record but labels one in ten wrongly scores only 0.38 (`sikayet_tr`) and 0.58
  (`interpress_tr`) on rare-label counts, because a few wrong labels matter a
  lot when the answer is small. That simulation assumes errors spread evenly
  over labels; real model errors may not.

## Known issues

**Found after the v0.10.0 release (5 October), to be fixed in the next
version.** Details and examples: Experiment 12 in `experiments/REPORT.md`.

- Ranking questions on the intent and complaint sets list 5 labels but ask for
  the most common label "in these records"; in 57 of 195 a label not on the
  list is more common than the answer. Read them as "of these labels".
- 19 "more, less or the same" questions are graded "the same" although the two
  counts differ (by up to 2%).
- 10 percentage questions land exactly on a half (2.5% is graded 3).
- Some texts repeat in the source with different labels; one copy is kept, with
  the first copy's label. 35 shipped records carry a minority label (21 of
  them supplements).
- Eight news labels are written without Turkish letters ('saglik', 'gida',
  'yasam', 'egitim', 'iletisim', 'bilisim', 'aktuel', 'kultursanat'), so the
  label-name filter missed their Turkish spelling: "sağlık" appears in 3,147
  news records.

**What each role measures.** Every question type was attacked by sampling
(reading a random part of the document) and by search (finding the relevant
records by a word or topic), using simulated readers that are told the true
label of each record they read. Full setup and examples:
`experiments/REPORT.md` in the GitHub repository.

| role | questions | strongest shortcut found | reader of everything |
|---|---:|---|---|
| core: close comparisons | 309 | sampling half the document 0.62; top 10% by topic search 0.54; guessing 0.50 | 0.86 at 95% labelling accuracy, 0.76 at 90% |
| retrieval: rare-label counts | 237 | topic search reading 5%: 0.53 under `partial` (measured on v0.8) | depends strongly on labelling accuracy |
| control: counts, proportions, rankings, wide comparisons | 1,816 | sampling 5%: about 0.8 under `relative` (measured on v0.8) | about 0.9 or more |

- Control questions show whether a model can classify the records; a 5% sample
  answers them almost as well as the whole document, so they are not evidence
  of reading. Under `relative`, a reader that opens nothing and divides the
  record count by the number of labels already scores 0.43 to 0.55 on counts,
  and longer documents are not harder.
- Core questions come in two groups. The **214 from core documents**
  (`core_document: true`) are fully balanced: picking the first-named label
  gets 0.50, the label more common in the source dataset 0.50, topic search
  0.49, sampling half the document 0.62. The **95 from ordinary documents** are
  slightly exposed: the label more common in the source dataset wins 62% of the
  time and topic search reaches 0.67, because the compared categories are
  sometimes small. Report the two groups separately.
- Core scores have a ceiling below 1.0: wrong labels in the source data decide
  some close comparisons. With 5% of labels wrong a perfect model scores about
  0.85. A native-speaker check of the Turkish core categories is prepared.
- The difficulty grades released in v0.7.x are withdrawn: they reflected which
  four skimming programs had been chosen, and on small answers a single lucky
  draw decided them.

**Questions overlap.** 337 document-label pairs are asked both as a count and
as a proportion (one answer gives the other). On 3-label sets the 12 questions
of a document rest on about two numbers. Treat the document, not the question,
as the unit of evidence.

**Documents share records.** Within a subset and length tier, documents share
20-39% of their records at the longest tiers.

**Not every question type exists everywhere.**

| subset | missing types | why |
|---|---|---|
| `interpress_tr` | `most_common`, `least_common`, `second_most` | section shares are too close to rank with the required 15% margin |
| `vitamins_tr`, `musteri_tr`, `amazon_hpc_en`, `marc_en` | close comparisons on random-mix documents | with "neutral" excluded, the two remaining labels are rarely close; these sets' core questions come from core documents |

**One flagged tier.** On `en_intent` at 100K tokens, a reader using only the
source corpus's label shares scores 0.73 on `proportion` (Turkish counterpart:
0.45). It is kept and flagged, since removing it would break the pairing.

**Contamination.** Every record comes from a public dataset. A model that has
memorised a dataset's labels could label its records without reading them. Not
tested; the same holds for OOLONG.

**Other.** No time-based questions. Lengths are counted with one tokenizer
(`Qwen/Qwen3-8B`); the Turkish/English token ratio on identical sentences
ranges from 0.57x to 2.16x across tokenizers. `shift` questions exist only in
versions before 0.7.0 and should not be used.
