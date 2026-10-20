---
license:
- cc-by-sa-4.0
- cc-by-4.0
- cc-by-nc-4.0
- cc-by-2.5
- other
language:
- tr
- en
pretty_name: TR-OOLONG
size_categories:
- 1K<n<10K
task_categories:
- question-answering
- text-classification
tags:
- long-context
- aggregation
- turkish
- cross-lingual
- benchmark
configs:
- config_name: musteri_tr
  data_files: [{split: test, path: data/main/musteri_tr/test/questions.jsonl.gz}]
- config_name: musteri_tr_documents
  data_files: [{split: test, path: data/main/musteri_tr/test/documents.jsonl.gz}]
- config_name: sinema_tr
  data_files: [{split: test, path: data/main/sinema_tr/test/questions.jsonl.gz}]
- config_name: sinema_tr_documents
  data_files: [{split: test, path: data/main/sinema_tr/test/documents.jsonl.gz}]
- config_name: doktor_tr
  data_files: [{split: test, path: data/main/doktor_tr/test/questions.jsonl.gz}]
- config_name: doktor_tr_documents
  data_files: [{split: test, path: data/main/doktor_tr/test/documents.jsonl.gz}]
- config_name: trnews2025_tr
  data_files: [{split: test, path: data/main/trnews2025_tr/test/questions.jsonl.gz}]
- config_name: trnews2025_tr_documents
  data_files: [{split: test, path: data/main/trnews2025_tr/test/documents.jsonl.gz}]
- config_name: tez_tr
  data_files: [{split: test, path: data/main/tez_tr/test/questions.jsonl.gz}]
- config_name: tez_tr_documents
  data_files: [{split: test, path: data/main/tez_tr/test/documents.jsonl.gz}]
- config_name: tez_en
  data_files: [{split: test, path: data/main/tez_en/test/questions.jsonl.gz}]
- config_name: tez_en_documents
  data_files: [{split: test, path: data/main/tez_en/test/documents.jsonl.gz}]
- config_name: massive_tr
  data_files: [{split: test, path: data/main/massive_tr/test/questions.jsonl.gz}]
- config_name: massive_tr_documents
  data_files: [{split: test, path: data/main/massive_tr/test/documents.jsonl.gz}]
- config_name: massive_en
  data_files: [{split: test, path: data/main/massive_en/test/questions.jsonl.gz}]
- config_name: massive_en_documents
  data_files: [{split: test, path: data/main/massive_en/test/documents.jsonl.gz}]
- config_name: amazon_hpc_en
  data_files: [{split: test, path: data/main/amazon_hpc_en/test/questions.jsonl.gz}]
- config_name: amazon_hpc_en_documents
  data_files: [{split: test, path: data/main/amazon_hpc_en/test/documents.jsonl.gz}]
- config_name: amazon_movies_en
  data_files: [{split: test, path: data/main/amazon_movies_en/test/questions.jsonl.gz}]
- config_name: amazon_movies_en_documents
  data_files: [{split: test, path: data/main/amazon_movies_en/test/documents.jsonl.gz}]
- config_name: amazon_shop_en
  data_files: [{split: test, path: data/main/amazon_shop_en/test/questions.jsonl.gz}]
- config_name: amazon_shop_en_documents
  data_files: [{split: test, path: data/main/amazon_shop_en/test/documents.jsonl.gz}]
- config_name: wikinews_en
  data_files: [{split: test, path: data/main/wikinews_en/test/questions.jsonl.gz}]
- config_name: wikinews_en_documents
  data_files: [{split: test, path: data/main/wikinews_en/test/documents.jsonl.gz}]
- config_name: vitamins_tr
  data_files: [{split: test, path: data/main/vitamins_tr/test/questions.jsonl.gz}]
- config_name: vitamins_tr_documents
  data_files: [{split: test, path: data/main/vitamins_tr/test/documents.jsonl.gz}]
- config_name: ext_musteri_tr
  data_files: [{split: test, path: data/extension/musteri_tr/test/questions.jsonl.gz}, {split: dev, path: data/extension/musteri_tr/dev/questions.jsonl.gz}]
- config_name: ext_musteri_tr_documents
  data_files: [{split: test, path: data/extension/musteri_tr/test/documents.jsonl.gz}, {split: dev, path: data/extension/musteri_tr/dev/documents.jsonl.gz}]
- config_name: ext_sinema_tr
  data_files: [{split: test, path: data/extension/sinema_tr/test/questions.jsonl.gz}]
- config_name: ext_sinema_tr_documents
  data_files: [{split: test, path: data/extension/sinema_tr/test/documents.jsonl.gz}]
- config_name: ext_doktor_tr
  data_files: [{split: test, path: data/extension/doktor_tr/test/questions.jsonl.gz}, {split: dev, path: data/extension/doktor_tr/dev/questions.jsonl.gz}]
- config_name: ext_doktor_tr_documents
  data_files: [{split: test, path: data/extension/doktor_tr/test/documents.jsonl.gz}, {split: dev, path: data/extension/doktor_tr/dev/documents.jsonl.gz}]
- config_name: ext_trnews2025_tr
  data_files: [{split: test, path: data/extension/trnews2025_tr/test/questions.jsonl.gz}, {split: dev, path: data/extension/trnews2025_tr/dev/questions.jsonl.gz}]
- config_name: ext_trnews2025_tr_documents
  data_files: [{split: test, path: data/extension/trnews2025_tr/test/documents.jsonl.gz}, {split: dev, path: data/extension/trnews2025_tr/dev/documents.jsonl.gz}]
- config_name: ext_tez_tr
  data_files: [{split: test, path: data/extension/tez_tr/test/questions.jsonl.gz}, {split: dev, path: data/extension/tez_tr/dev/questions.jsonl.gz}]
- config_name: ext_tez_tr_documents
  data_files: [{split: test, path: data/extension/tez_tr/test/documents.jsonl.gz}, {split: dev, path: data/extension/tez_tr/dev/documents.jsonl.gz}]
- config_name: ext_tez_en
  data_files: [{split: test, path: data/extension/tez_en/test/questions.jsonl.gz}, {split: dev, path: data/extension/tez_en/dev/questions.jsonl.gz}]
- config_name: ext_tez_en_documents
  data_files: [{split: test, path: data/extension/tez_en/test/documents.jsonl.gz}, {split: dev, path: data/extension/tez_en/dev/documents.jsonl.gz}]
- config_name: ext_massive_tr
  data_files: [{split: test, path: data/extension/massive_tr/test/questions.jsonl.gz}]
- config_name: ext_massive_tr_documents
  data_files: [{split: test, path: data/extension/massive_tr/test/documents.jsonl.gz}]
- config_name: ext_massive_en
  data_files: [{split: test, path: data/extension/massive_en/test/questions.jsonl.gz}]
- config_name: ext_massive_en_documents
  data_files: [{split: test, path: data/extension/massive_en/test/documents.jsonl.gz}]
- config_name: ext_amazon_hpc_en
  data_files: [{split: test, path: data/extension/amazon_hpc_en/test/questions.jsonl.gz}, {split: dev, path: data/extension/amazon_hpc_en/dev/questions.jsonl.gz}]
- config_name: ext_amazon_hpc_en_documents
  data_files: [{split: test, path: data/extension/amazon_hpc_en/test/documents.jsonl.gz}, {split: dev, path: data/extension/amazon_hpc_en/dev/documents.jsonl.gz}]
- config_name: ext_amazon_movies_en
  data_files: [{split: test, path: data/extension/amazon_movies_en/test/questions.jsonl.gz}, {split: dev, path: data/extension/amazon_movies_en/dev/questions.jsonl.gz}]
- config_name: ext_amazon_movies_en_documents
  data_files: [{split: test, path: data/extension/amazon_movies_en/test/documents.jsonl.gz}, {split: dev, path: data/extension/amazon_movies_en/dev/documents.jsonl.gz}]
- config_name: ext_amazon_shop_en
  data_files: [{split: test, path: data/extension/amazon_shop_en/test/questions.jsonl.gz}, {split: dev, path: data/extension/amazon_shop_en/dev/questions.jsonl.gz}]
- config_name: ext_amazon_shop_en_documents
  data_files: [{split: test, path: data/extension/amazon_shop_en/test/documents.jsonl.gz}, {split: dev, path: data/extension/amazon_shop_en/dev/documents.jsonl.gz}]
- config_name: ext_wikinews_en
  data_files: [{split: test, path: data/extension/wikinews_en/test/questions.jsonl.gz}]
- config_name: ext_wikinews_en_documents
  data_files: [{split: test, path: data/extension/wikinews_en/test/documents.jsonl.gz}]
---

# TR-OOLONG v0.13 (provisional)

> **Status: provisional, data only.** This release contains the documents,
> questions, answers, label maps, construction rules, hashes and standalone
> scripts that recompute every answer and score responses. The generation code
> will be available to reviewers with the paper's submission and published on
> GitHub together with the paper; until then every answer can be checked, but
> the documents cannot be regenerated by others. Until the
> paper, file formats may still change; the version number will change with
> them, and files are never changed in place.

TR-OOLONG tests whether a model can aggregate over a long document: thousands
of short labelled records (reviews, news articles, patients' questions, thesis
abstracts, voice-assistant requests) are joined into one document, and each
question asks about label counts over the whole document, over some users, or
over some dates. It follows the design of OOLONG-synth (Bertsch et al., 2025)
and adds Turkish: Turkish sets, Turkish-English pairs, English sets with
documents of up to 16 million tokens, and a close-comparison extension where
two label counts differ by 0-10%. **Every set ships its text.**

## Sets

Three tracks. Lengths are target lengths of the document in tokens (Qwen3-8B
tokenizer); the prompt adds the question and the model's answer on top, so
budget for them. No record appears twice within a document; records do recur
across documents, and near-duplicates (different records with almost the same
text) are not ruled out.

| set | track | lang | labels | main docs / questions | lengths | label check* (agreement per annotator; kappa between them) |
|---|---|---|---|---|---|---|
| `musteri_tr` | Turkish; pair with `amazon_shop_en` | tr | olumlu, olumsuz | 20 / 500 | 2K-1M | 96% / 96%; 1.00 |
| `sinema_tr` | Turkish; pair with `amazon_movies_en` | tr | olumlu, olumsuz | 24 / 590 | 2K-4M | 86% / 89%; 1.00 |
| `doktor_tr` | Turkish | tr | 9 specialties | 20 / 500 | 4K-2M | 89% / 91%; 0.92 |
| `trnews2025_tr` | Turkish; pair with `wikinews_en` | tr | 9 sections | 22 / 550 | 4K-4M | 89% / 96%; 0.92 |
| `tez_tr`, `tez_en` | parallel pair | tr, en | 8 fields | 22 / 550 per language | 4K-4M | 88% / 88%; 0.80** |
| `massive_tr`, `massive_en` | parallel pair | tr, en | 11 scenario groups | 18 / 450 per language | 1K-256K | 90% / 91%; 0.92 |
| `amazon_hpc_en` | English | en | positive, negative | 28 / 697 | 2K-16M | 95% / 100%; 0.89 |
| `amazon_movies_en` | English; pair with `sinema_tr` | en | positive, negative | 28 / 700 | 2K-16M | 95% (one annotator so far) |
| `amazon_shop_en` | English; pair with `musteri_tr` | en | positive, negative | 28 / 700 | 1K-8M | 95% (one annotator so far) |
| `wikinews_en` | English; pair with `trnews2025_tr` | en | 5 sections | 18 / 450 | 2K-512K | 95% (one annotator so far) |
| `vitamins_tr` | outside the main results | tr | olumlu, olumsuz | 20 / 500 | 2K-1M | 92%; 40% of reviews state no opinion |

*Native speakers labelled a sample blind (20-48 records per set) and were then
shown the source label; agreement is on records they could decide. A set enters
if each annotator agrees on at least 85% and is unsure on at most 25%. The
rule was 70% when the checks started (fixed before the first review) and was
raised to 85% after most results were known; every set kept passes both.
Sets that failed were dropped, not repaired: a complaint set (62%), product
types (31-33% unsure), a 42K news set (76%), Voice of America news (83%).
Samples are small: 25 of 26 decided records has a 95% interval of 81-99%.
The annotators are the author and two of the author's siblings (paid, blind to the
source labels and to each other's answers). A second annotator for the three
single-annotator sets is in progress.
**Thesis fields: mathematics was joined to physics and engineering after one
observed confusion; without that merge, a pessimistic bound on agreement is
79% (a bound, not an observed agreement on unmerged labels).

**Pairs.** `massive_tr`/`massive_en` are the same requests, translated;
`tez_tr`/`tez_en` are author-provided Turkish and English abstracts of the
same thesis; their semantic equivalence is unverified. Both parallel pairs are
the same documents in two languages (same records, order, users, dates,
answers); they are sized by the Turkish version, which needs more tokens for
these paired texts under the Qwen3-8B tokenizer (MASSIVE about 1.22x, theses
about 1.48x), so both versions fit the stated length and the English one is
shorter. The other pairs are the same task on
independent texts.

**Overlap with OOLONG.** No set uses any of OOLONG-synth's ten source
datasets. Against the three closest of them (full sources, not only OOLONG's
filtered subsets), the share of our English records that share a run of 12
words with any of their texts: Amazon films vs IMDB 611 of 456,973 (0.13%; 7
identical texts), Wikinews vs AG News 2 of 11,962 (none identical), the other
Amazon sets vs IMDB or app reviews at most 12 (generic short texts identical:
at most 216, such as "love it love it ...").

Main set: 228 documents and 5,687 questions in the main results (parallel
pairs counted once, `vitamins_tr` left out); 7,187 questions in all files. Up
to 25 questions per document, in three groups (counting, user, timeline).
Lengths are powers of two from 1,024 tokens; a set stops where its records run
out.

**Close-comparison extension:** one question per document ("is label A more
common, less common, or the same frequency as label B?") at margins of 0, 0.1,
0.5, 2 and 10% of the records, with 2,048, 8,192 or 32,768 records. 20 test
documents per cell: 105 test cells (each parallel pair's two languages counted
once), 2,100 test questions; 4 development documents per cell where the
development split can fill it (50 cells, 200 questions). Every document has a
labels-hidden and a labels-shown rendering of the same text.

| set | test: 2,048 / 8,192 / 32,768 records | development |
|---|---|---|
| `musteri_tr`, `sinema_tr` | yes / yes / no | `musteri_tr`: 2,048 |
| `amazon_hpc_en`, `amazon_movies_en`, `amazon_shop_en` | yes / yes / yes | 2,048, 8,192 |
| `massive_tr` / `massive_en` | yes / no / no | none |
| `doktor_tr`, `trnews2025_tr`, `tez_tr` / `tez_en` | yes / yes / no | 2,048 |
| `wikinews_en` | yes / no / no | none |

A cell exists only if every margin can be built from distinct records of the
pools. The rule was fixed for the positive/negative sets and MASSIVE before
any extension was built: for sets with more than two labels, the two compared
labels together take half of the records and the other labels share the rest.
On 21 October 2026, before these documents were built, the same rule was
applied to the doctor questions, the 2025 news, the theses and Wikinews; this
is a later extension of the rule, not part of the original plan.

## Every annotation round

All blind label checks, in order, failures included. A is the author, B one of
the author's siblings (both native Turkish speakers; B paid). Each sample was
drawn fresh (records never shown before), with the same number of records per
label and a fixed seed; the annotator chose a label or "unsure" without seeing
the source label, which was shown only after the answer. Agreement is on the
records the annotator decided; the interval is a 95% Wilson interval; the bar
is the agreement required when the round was scored (unsure at most 25%
throughout). Where a definition changed after a round (regrouping, a dropped
section), the next row is a new definition checked on fresh records, except
where marked "after seeing these results". The answers of every round are
kept unchanged, with hashes, by the maintainer.

| round | date | set (definition checked) | annotator | agree on decided | 95% interval | unsure | bar | result |
|---|---|---|---|---:|---:|---:|---:|---|
| 1 | 11 Oct | `musteri_tr` | A | 18/18 = 100% | 82-100 | 10% | 70% | pass |
| 1 | 11 Oct | `sinema_tr` | A | 15/17 = 88% | 66-97 | 15% | 70% | pass |
| 1 | 11 Oct | `vitamins_tr` | A | 11/12 = 92% | 65-99 | 40% | 70% | fails the unsure limit; kept outside the main results |
| 1 | 11 Oct | MASSIVE, Turkish, 48 intents | A | 20/34 = 59% | 42-74 | 15% | 70% | fail; regrouped after seeing these results |
| 1 | 11 Oct | complaints (sikayet), 30 categories | A | 19/34 = 56% | 39-71 | 15% | 70% | fail; merged after seeing these results |
| 1 | 12 Oct | MARC (English reviews) | A | 18/18 = 100% | 82-100 | 10% | 70% | pass; later withdrawn by Amazon |
| 1 | 12 Oct | `amazon_hpc_en` | A | 20/20 = 100% | 84-100 | 0% | 70% | pass |
| 1 | 12 Oct | MASSIVE, English, 18 scenarios | A | 30/36 = 83% | 68-92 | n/a | 70% | pass |
| fresh | 12 Oct | MASSIVE, Turkish, 18 scenarios | A | 22/33 = 67% | 50-80 | n/a | 70% | fail |
| fresh | 12 Oct | MASSIVE, Turkish, grouped (as released, 11 groups) | A | 26/33 = 79% | 62-89 | n/a | 70% | pass |
| fresh | 12 Oct | complaints, 12 merged groups | A | 20/32 = 62% | 45-77 | n/a | 70% | fail; set dropped |
| re-check | 12 Oct | `massive_tr` (released) | A | 36/40 = 90% | 77-96 | 9% | 70% | pass |
| re-check | 13 Oct | `massive_tr` (released) | B | 40/44 = 91% | 79-96 | 0% | 70% | pass |
| re-check | 12 Oct | `musteri_tr` | A | 25/26 = 96% | 81-99 | 13% | 70% | pass |
| re-check | 13 Oct | `musteri_tr` | B | 26/27 = 96% | 82-99 | 10% | 70% | pass |
| re-check | 12 Oct | `sinema_tr` | A | 25/29 = 86% | 69-95 | 3% | 70% | pass |
| re-check | 13 Oct | `sinema_tr` | B | 25/28 = 89% | 73-96 | 7% | 70% | pass |
| re-check | 12 Oct | MARC | A | 17/17 = 100% | 82-100 | 15% | 70% | pass |
| re-check | 13 Oct | MARC | B | 18/18 = 100% | 82-100 | 10% | 70% | pass |
| re-check | 12 Oct | `amazon_hpc_en` | A | 18/19 = 95% | 75-99 | 5% | 70% | pass |
| re-check | 13 Oct | `amazon_hpc_en` | B | 20/20 = 100% | 84-100 | 0% | 70% | pass |
| V | 12 Oct | product types, 7 labels | A | 32/33 = 97% | 85-99 | 33% | 70% | fails the unsure limit; dropped |
| V | 12 Oct | Turkish news (Kemik, 42K) | A | 25/33 = 76% | 59-87 | 6% | 70% | pass at 70%; removed when the bar became 85% |
| 2 | 12 Oct | product types, 3 labels | A | 31/31 = 100% | 89-100 | 31% | 70% | fails the unsure limit; dropped |
| 2 | 12 Oct | TR-News, 9 sections | A | 35/43 = 81% | 67-90 | 4% | 70% | pass; section dünya then removed (new definition) |
| 3 | 12 Oct | TR-News, 8 sections | A | 33/35 = 94% | 81-98 | 12% | 70% | pass; later replaced by `trnews2025_tr` |
| 3 | 12 Oct | AG News, 3 sections | A | 38/42 = 90% | 78-96 | 7% | 70% | pass; later replaced by `wikinews_en` |
| 4 | 19 Oct | `doktor_tr`, 9 specialties | A | 40/45 = 89% | 77-95 | 0% | 70% | pass |
| 4 | 19 Oct | `doktor_tr`, 9 specialties | B | 41/45 = 91% | 79-96 | 0% | 70% | pass |
| 4 | 19 Oct | `tez_tr`, 8 fields | A | 42/48 = 88% | 75-94 | 0% | 70% | pass (79% bound without the mathematics merge) |
| 4 | 19 Oct | `tez_tr`, 8 fields | B | 42/48 = 88% | 75-94 | 0% | 70% | pass |
| 5 | 20 Oct | `trnews2025_tr`, 9 sections | A | 40/45 = 89% | 77-95 | 0% | 85% | pass |
| 5 | 20 Oct | `trnews2025_tr`, 9 sections | B | 43/45 = 96% | 85-99 | 0% | 85% | pass |
| 6 | 21 Oct | `amazon_movies_en` | A | 19/20 = 95% | 76-99 | 0% | 85% | pass |
| 7 | 21 Oct | `amazon_shop_en` | A | 18/19 = 95% | 75-99 | 5% | 85% | pass |
| 8 | 21 Oct | Voice of America news, 5 sections | A | 25/30 = 83% | 66-93 | 6% | 85% | fail; dropped |
| 9 | 21 Oct | `wikinews_en`, 5 sections | A | 37/39 = 95% | 83-99 | 3% | 85% | pass |

Second annotator still pending: `amazon_movies_en`, `amazon_shop_en`,
`wikinews_en` (rounds 6, 7, 9).

## Files

```
data/main/<set>/test/{documents,questions}.jsonl.gz, manifest.json
data/extension/<set>/{test,dev}/{documents,questions}.jsonl.gz, manifest.json
CONSTRUCTION.md       how documents, questions and answers are built
label_maps.json       source label -> released label
provenance.json       sources, revisions, file hashes, licences, links and who declared them, tokenizer, seeds
recompute_answers.py  recomputes every answer (standard library only)
score_responses.py    scores model responses (rules in "Scoring"); --self-test
attribution/wikinews_en.jsonl  title, page id and URL of the article behind each Wikinews record
SHA256SUMS            hash of every file in this release
```

**Questions:** `uid`, `doc_id`, `language`, `question`, `answer` (a list; any
listed answer is correct), `question_en`, `answer_en` (English original),
main set also `task_group`, `task`, `answer_type`, `input_subset`; extension
also `n_records`, `margin_target`, `margin_realized`, `tie`.

**Documents:** `doc_id`, `source`, `language`, `split`, `n_records`,
`n_tokens` (Qwen3-8B), `label_counts`, `seed`, `text` (labels hidden),
`text_with_labels`; main set also `context_len` (target length; `n_tokens`
never exceeds it), `temperature`, `attempt`; extension also `pair`, `winner`,
`named_first`, `count_difference`, `margin_target`, `margin_realized`.

Give the model `text` followed by `question`. `text_with_labels` is for
analysis (or for a labels-shown condition), not for the labels-hidden task.
Date answers are stored as `YYYY-MM-DD`; the questions ask for MM/DD/YYYY
(Turkish: GG.AA.YYYY), so parse dates before comparing.

```python
from datasets import load_dataset
q = load_dataset("yigitates17/tr-oolong", "doktor_tr", split="test")
d = load_dataset("yigitates17/tr-oolong", "doktor_tr_documents", split="test")
```

## Licences and attribution

Each set keeps its source's licence, as declared by the source's publisher;
`provenance.json` gives for every set who declared it and a link to the
licence. The underlying rights of the original writers (reviewers, patients,
thesis authors, news sites) were not independently established.

- `musteri_tr`, `sinema_tr`, `vitamins_tr`:
  [CC-BY-SA-4.0](https://creativecommons.org/licenses/by-sa/4.0/), declared by
  the dataset's publisher (Turkish NLP Suite; Altinok, ACL 2023); the reviews
  come from public shopping and film sites. These files are redistributed
  adaptations under the share-alike terms, so they are released under
  CC-BY-SA-4.0.
- `doktor_tr`: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/),
  declared by the dataset's publisher on Hugging Face (alibayram/doktorsitesi);
  the questions were written by users of doktorsitesi.com.
- `tez_tr`, `tez_en`: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/),
  declared by the dataset's publisher on Hugging Face
  (umutertugrul/turkish-academic-theses-dataset); the abstracts are written by
  the thesis authors and published by YÖK's National Thesis Center.
- `trnews2025_tr`: [CC-BY-NC-4.0](https://creativecommons.org/licenses/by-nc/4.0/),
  declared by the dataset's uploader on Kaggle (sengulbayrak/trnews-2025,
  created 2 April 2026); the articles were gathered from Turkish news sites,
  which the page does not name, with students of a university NLP course.
  Non-commercial use only.
- `massive_tr`, `massive_en`: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/),
  by the dataset's authors (MASSIVE; FitzGerald et al., 2023).
- `amazon_hpc_en`, `amazon_movies_en`, `amazon_shop_en`: Amazon Reviews 2023
  (Hou et al., 2024). The dataset declares no licence; its authors agreed by
  email (18 October 2026) that TR-OOLONG may release the review text as
  described here, with attribution, a link to the dataset and a citation. This
  covers this release; it implies no licence for further reuse of the reviews.
- `wikinews_en`: English Wikinews articles ([copyright policy](https://en.wikinews.org/wiki/Wikinews:Copyright)):
  public domain before 25 September 2005,
  [CC-BY 2.5](https://creativecommons.org/licenses/by/2.5/) from then until
  15 December 2024, [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/)
  from 16 December 2024. `attribution/wikinews_en.jsonl` gives each article's
  title and URL, keyed by the SHA-256 of its released text.
- Questions, answers, label maps and documentation written for TR-OOLONG:
  CC-BY-4.0, except where a set's share-alike licence applies.

A licence does not grant permission to process personal data (see below).
Changes made to all sets: cleaning, label grouping and the arrangement of
records into documents with synthetic users and dates (CONSTRUCTION.md). The
synthetic user IDs and dates are random and do not refer to anyone.

## Personal data

`doktor_tr` contains patients' questions about their health. Known-name
patterns were removed: doctors' names next to a form of address or a title are
replaced ("Aylin hanım" -> "doktor hanım"), other first names from the name
lists are removed, and questions with an e-mail address or the writer's own
name are dropped. Residual identifiers and linkable health narratives may
remain. Numbers and identifiers appear masked by the source site
("*** *** **") in the questions we inspected; this was observed, not
guaranteed. The writers were not asked for consent and no ethics review was
performed; the questions were public on the source site. Do not try to
identify anyone. The other sets are public reviews, news articles, thesis
abstracts and voice-assistant requests; they can name public figures and
places.

## Intended and excluded uses

Intended: evaluating long-context aggregation (classify every record, then
count, compare or rank) in Turkish and English, per question type and length,
and Turkish-English comparisons on the parallel sets. Excluded: training or
tuning models that are then evaluated on it, medical advice or triage
(`doktor_tr` labels are routing specialties, the specialty of the doctor the
question was addressed to, not clinical diagnoses), profiling or identifying
the writers, and commercial use of `trnews2025_tr`.

## Collection dates and selection biases

| set | records written or collected |
|---|---|
| `musteri_tr`, `sinema_tr`, `vitamins_tr` | not stated by the source |
| `doktor_tr` | not stated by the source |
| `tez_tr`, `tez_en` | theses dated 1963-2024 in the source |
| `trnews2025_tr` | access dates in the file 4 July - 21 August 2025 (the Kaggle page says collection began in the 2023-2024 academic year) |
| `massive_tr`, `massive_en` | written for MASSIVE (2022) |
| Amazon sets | reviews from May 1996 to September 2023 (Amazon Reviews 2023) |
| `wikinews_en` | articles in the 1 October 2026 dump |

Topics and styles follow the sources: Turkish e-commerce and film sites, one
Turkish doctor-question site, Turkish news sites, YÖK theses with an English
abstract, US Amazon reviews, English Wikinews. The sentiment sets leave out
middle ratings, and each set keeps only records within its length limits and
cleaning rules (CONSTRUCTION.md). Label mixes in documents are random, not the
sources' distributions.

## Maintenance and removal requests

Maintainer: Yiğit Ateş. The dataset is hosted on the Hugging Face Hub in
versioned releases (files are never changed in place). **Removal requests:**
e-mail yigitates1709@gmail.com privately (please do not post personal details
in a public discussion). We aim to reply within 14 days; confirmed records are
removed in the next version, and earlier versions that contain them are taken
down. If maintenance ends, this card will say so.

## Using the results

- Report results per set, per question type and per length; do not pool them.
  Some question types can be answered well from a small sample of the records
  (most/least common label, A vs B at large margins); exact counts and user
  questions were answered poorly by the samplers we tested.
- Some questions need no labels at all: which user or date appears most
  often, how many dates appear n times. They test counting over the
  metadata, not reading the records. Report them separately.
- A correct answer does not prove that a model read the whole document.
- The shortcut checks below show what the tested heuristics achieve; they do
  not show that no other shortcut exists, and the vocabulary readers do not
  show that a model scoring like them did no semantic processing.
- For the parallel pairs, compare languages on the same documents; for the
  other pairs, the texts differ (sources, years, lengths), so a gap is not a
  language effect alone.
- In the extension, report the 0% (tie) cells separately, report the two
  renderings separately, and compute intervals over documents (a document's
  two renderings, and MASSIVE's two languages, are one unit). Labels-hidden
  results at 0%, 0.1% and 0.5% belong in a separate stress test.
- For labels-hidden runs, give the model only `text` and `question`: no
  answers, counts, other documents or source lookup. The dataset is not
  protected against models that have seen these files or the sources.
- The labels are the source's labels, checked on samples; some are wrong (a
  stock-market report filed under `çevre`, a court case filed under
  `science_tech`). At the smallest margins and at ties, a few wrong source
  labels decide the answer.

## Scoring

`score_responses.py` (standard library only) scores responses and documents
every rule; `python score_responses.py --self-test data` checks that a
response written in each question's requested form is accepted, a wrong one
rejected, and malformed ones rejected (no prefix, empty, a prefix without an
answer, a number with a fractional part such as "65.5" for 65).

- The answer is read after the last prefix the question asks for ("Answer:",
  "Label:", "User:", "Date:"; Turkish "Cevap:", "Etiket:", "Kullanıcı:",
  "Tarih:"); a response without it is wrong.
- Comparisons: English prompts ask for a sentence ("Answer: negative is
  [X] positive"); the scorer takes the relation inside it, longest match
  first. Turkish prompts ask for the relation alone.
- Labels: case-insensitive, without quotes or a final full stop. Users and
  numbers: the first number, which must be whole ("1234", or grouped "1,234" /
  "1.234"); "65.5" or "65,5" is not a readable answer. Dates: MM/DD/YYYY, GG.AA.YYYY or ISO,
  compared as dates. Months: "March 2022" / "Mart 2022".
- A response is correct if it matches any listed answer. Numbers are scored
  exactly; OOLONG's partial score (0.75 to the power of the absolute error) can
  be reported as well, labelled as such; it is not an accuracy.

## Shortcut checks on the main set

These show what the tested heuristics achieve, nothing more. All numbers are
computed from the files in this release: test split, main sets only
(`vitamins_tr` left out).

**Readers that never look at a label**, using only the question, dates, users
and line order. Each parallel pair is counted once (its English side). Chance
for a label question is the share of listed options that are accepted,
averaged over questions.

| reader | right | chance |
|---|---:|---:|
| "user A or B with label X": the more active user overall | 56% (57/102) | 50% |
| same, the less active user, or any rule on the ratio of their activity | 44-56% | 50% |
| "most common label": the first label listed | 45% (182/403) | 43% |
| "least common label": the first label listed | 36% (306/856) | 38% |
| "A vs B" within a month, users or dates: the first-named label wins | 47% (254/541) | |
| "A vs B" over the whole document: the first-named label wins | 44% (158/356) | |
| "first month X beats Y": the document's earliest month | 26% (21/82) | |
| "first month X beats Y": always February 2022 | 21% (17/82) | |
| whole document, "user with most records of label X": the most active user | 32% (58/184) | |

In "user A or B" questions both users have the same number of records overall,
so activity says nothing. The last row is built in: users are drawn
independently of labels, so the most active user also tends to have the most
records of any one label. No label question lists only one option, and none
accepts every listed option.

**Readers that label every record without understanding it** (learned on the
development split, an equal number of records per label), then answer exactly:
the most frequent development label everywhere ("none"); 30 keywords per label
("kw"); Naive Bayes over every word ("NB"); and Naive Bayes over formatting
alone, never the words ("format": which punctuation marks occur, share of
capitals, all-caps words, length, numbers). Share of the label questions'
credit (exact match; numbers with OOLONG's partial score):

| set | none | kw | NB | format |
|---|---:|---:|---:|---:|
| `musteri_tr` | 23% | 33% | 62% | 28% |
| `sinema_tr` | 28% | 39% | 55% | 35% |
| `doktor_tr` | 19% | 41% | 62% | 30% |
| `trnews2025_tr` | 24% | 49% | 59% | 35% |
| `tez_tr` / `tez_en` | 20% | 61% / 60% | 74% / 73% | 34% / 36% |
| `massive_tr` / `massive_en` | 20% | 33% / 39% | 51% / 62% | 24% |
| `amazon_hpc_en` | 30% | 36% | 65% | 42% |
| `amazon_movies_en` | 31% | 36% | 65% | 33% |
| `amazon_shop_en` | 24% | 30% | 65% | 48% |
| `wikinews_en` | 20% | 45% | 54% | 42% |

Exact match by question kind (none / kw / NB / format; number of questions in
brackets). The word readers' credit comes mostly from most/least common and
A-vs-B questions; exact counts stay at 0-30%:

| set | exact count | most / least common | A vs B |
|---|---|---|---|
| `amazon_hpc_en` | 1% / 1% / 10% / 3% (184) | 45% / 48% / 77% / 49% (247) | 38% / 51% / 76% / 51% (152) |
| `amazon_movies_en` | 2% / 2% / 8% / 3% (185) | 45% / 44% / 77% / 40% (247) | 34% / 52% / 85% / 41% (157) |
| `amazon_shop_en` | 1% / 2% / 8% / 4% (191) | 34% / 36% / 74% / 61% (259) | 28% / 43% / 78% / 51% (157) |
| `doktor_tr` | 0% / 12% / 19% / 9% (134) | 15% / 33% / 50% / 13% (163) | 13% / 41% / 69% / 36% (119) |
| `massive_en` | 0% / 9% / 24% / 2% (117) | 11% / 26% / 53% / 11% (144) | 16% / 42% / 59% / 26% (108) |
| `massive_tr` | 0% / 9% / 19% / 5% (117) | 11% / 22% / 42% / 12% (144) | 16% / 31% / 50% / 26% (108) |
| `musteri_tr` | 0% / 2% / 7% / 0% (136) | 35% / 38% / 66% / 36% (188) | 23% / 49% / 76% / 35% (103) |
| `sinema_tr` | 2% / 4% / 11% / 1% (152) | 43% / 48% / 64% / 45% (203) | 30% / 51% / 68% / 41% (126) |
| `tez_en` | 1% / 16% / 25% / 8% (143) | 17% / 54% / 72% / 25% (180) | 19% / 63% / 74% / 46% (140) |
| `tez_tr` | 1% / 18% / 30% / 5% (143) | 17% / 54% / 70% / 25% (180) | 19% / 68% / 81% / 39% (140) |
| `trnews2025_tr` | 0% / 9% / 20% / 7% (153) | 18% / 41% / 52% / 22% (174) | 23% / 61% / 68% / 38% (139) |
| `wikinews_en` | 0% / 16% / 16% / 10% (126) | 21% / 34% / 44% / 30% (148) | 17% / 47% / 56% / 49% (120) |

The formatting-only reader labels records from typography and length: on
`trnews2025_tr` it labels 34% of distinct records correctly against 20% for the
most frequent label, and answers 102 of 466 label questions exactly against 63
for the constant label; on `amazon_shop_en` and `wikinews_en` it also clearly
beats "none" on questions (48% and 42% of credit). Formatting differences
between labels remain (sites and sections differ in style); they are a
residual cue, not removed. On identical content the word reader is weaker in
Turkish than in English (MASSIVE: 66% vs 74% of records labelled correctly).
Scores like these do not show that a model processed no meaning.

## Shortcut checks on the extension

Each reader below was run on every test document, given the true labels of
the records it reads (share of documents answered correctly; ranges over sets
and record counts; 20 documents per cell, so 10 of 20 has a 95% interval of
0.30-0.70).

| reader | 0% (tie) | 0.1-0.5% | 2% | 10% |
|---|---:|---:|---:|---:|
| every record | 1.00 | 1.00 | 1.00 | 1.00 |
| random 25% of records | 0.01-0.05 | 0.46-0.70 | 0.68-0.98 | 0.99-1.00 |
| random 5% of records | 0.01-0.09 | 0.44-0.59 | 0.49-0.81 | 0.79-1.00 |
| best answer for the question text, learned from other cells | 0.00 | 0.35-0.65 | 0.25-0.55 | 0.35-0.70 |
| always "same frequency" | 1.00 | 0.00 | 0.00 | 0.00 |
| always "more common than" | 0.00 | 0.50 | 0.50 | 0.50 |
| the label with more source records | 0.00 | 0.35-0.75 | 0.30-0.60 | 0.35-0.60 |
| word-count classifier on every record, then exact count | 0.00 | 0.25-0.70 | 0.30-0.70 | 0.50-1.00 |
| counting mentions of a label's name | 0.00-0.40 | 0.25-0.65 | 0.20-0.65 | 0.30-0.85 |
| every record, 1 in 100 of one label misread | 0.00-0.01 | 0.50-0.72 | 1.00 | 1.00 |
| every record, 5 in 100 of one label misread | 0.00 | 0.50 | 0.50-0.54 | 1.00 |

No record is in both the development and the test documents. Two limits
follow. **Memory:** records are drawn from the same pools for every document,
so nearly every test record also appears, with its label shown, in another
released document (and every label is in the public source dataset); the
labels-hidden condition is meaningful only for models not trained on these
files or the sources. **Label errors:** below about 2%, a few records read
differently from their source label can change the answer; labels-hidden
results at ties and at 0.1-0.5% measure agreement with the source labels
under exact counting, a stress test, not evidence of reliable classification.

## Changes since v0.11

v0.12 was not published; its changes are included here.

- **Every set ships its text.** `marc_en` (withdrawn by Amazon; questions
  only) is replaced by `amazon_shop_en`; the Amazon review text now ships with
  the dataset authors' permission.
- **New sets**, each after a blind label check: `doktor_tr`, `trnews2025_tr`,
  `tez_tr`/`tez_en`, `amazon_movies_en`, `amazon_shop_en`, `wikinews_en`.
  `amazon_hpc_en` now uses the whole Health and Personal Care category.
- **Longer documents:** up to 4M tokens for Turkish sets and 16M for Amazon
  sets, still without repeating a record. Parallel documents are sized by the
  Turkish version (in v0.11 MASSIVE was sized in English and its Turkish
  version ran over the stated length); no document exceeds its target length.
- **Questions (from v0.12):** label lists in random order; "user A or B" asks
  only about two users with the same total number of records; "first month"
  questions only for the label that is rarer overall; label questions with
  one option, or where every option is correct, are gone.
- A scorer, `score_responses.py`, with `--self-test`.

**Question IDs are reused across versions with different content.** Join
results by release and `uid` together, never by `uid` alone.

## Citation

Cite this dataset (citation added with the paper) and the sources: OOLONG
(Bertsch et al., 2025, arXiv:2511.02817), MASSIVE (FitzGerald et al., ACL
2023), the Turkish NLP Suite datasets (Altinok, ACL 2023), Amazon Reviews 2023
(Hou et al., 2024), TRNEWS-2025 (Kaggle), the doktorsitesi.com and Turkish
academic theses datasets on Hugging Face, and English Wikinews.
