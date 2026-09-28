# TR-OOLONG datacard

Covers **v0.8.0**: 11
subsets, 195 documents, 2,277 questions, 7 question types, Turkish and English
(1,558 / 719 questions). Every answer is computed
from the source dataset's labels, twice, by two independent pieces of code
that must agree. No answer was written by hand.

For what the benchmark is and how to use it, see the [README](README.md).

## Versions

| version | date | change |
|---|---|---|
| 0.7.0 | 2026-09-16 | 11 subsets, rare-label counts, difficulty grades; `shift` removed |
| 0.7.1 | 2026-09-20 | adds `uid`, `dataset`, `haystack_uid`. No question, answer, document or grade changed |
| 0.8.0 | 2026-09-28 | adds 174 close comparisons (`core`); removes the 137 brand questions; adds `role` to every question; stops releasing difficulty grades. Documents and all other questions unchanged |

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
| `sinema_tr` | turkish-nlp-suite/BuyukSinema | film reviews | the writer's own 1-10 rating | 10 |
| `sikayet_tr` | Kaggle savasy/multiclass-classification-data-for-turkish-tc32 | consumer complaints | product category, chosen by the person filing | 29 |
| `interpress_tr` | Interpress Turkish news, 270k | news articles | newspaper section, set by the publisher | 16 |

Star ratings map to sentiment as 1-2 negative, 3 neutral, 4-5 positive.

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
- **`interpress_tr`.** Records are full articles (median 1,650 characters), so a
  100K-token document holds about 200 of them. 35.1% of articles were removed
  because they name their own section, so the shipped articles are a filtered
  subset of the corpus. `savunma` fell below the size floor, leaving 16 of 17
  sections. The source has daily publication dates (2010-2017); they are kept
  but not used by any question.
- **`sinema_tr`.** Ratings are uneven (2.4% at 3 stars, 24.4% at 8 stars), so
  some labels are naturally rare in a document.
- **`vitamins_tr` / `amazon_hpc_en`.** The only pair with a brand per record,
  printed in the text as `[[Brand]]`. Questions about brands were removed in
  v0.8.0 because searching for the printed name answers them; the markers stay
  in the text so the documents are unchanged. English brands come from joining reviews
  to product metadata. English reviews name a different brand than their own
  13.8% of the time (Turkish: 0.66%), mostly because some brand names are
  ordinary words. Questions use the printed marker, so answers are unaffected.

Records removed for containing a label name: MASSIVE 0.0%, `sinema_tr` 0.3%,
`sikayet_tr` 24.6%, `interpress_tr` 35.1%.

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

**What each role measures.** Every question type was attacked by sampling
(reading a random part of the document) and by search (finding the relevant
records by a word or topic), using simulated readers that are told the true
label of each record they read. Full setup and examples:
`experiments/REPORT.md` in the GitHub repository.

| role | questions | strongest shortcut found | reader of everything |
|---|---:|---|---|
| core: close comparisons | 174 | 0.64 (top 10% by topic search); sampling half the document 0.63; guessing 0.50 | 0.85 at 95% labelling accuracy, 0.77 at 90% |
| retrieval: rare-label counts | 265 | topic search reading 5%: 0.53 under `partial` | depends strongly on labelling accuracy |
| control: counts, proportions, rankings, wide comparisons | 1,838 | sampling 5%: about 0.8 under `relative` | about 0.9 or more |

- Control questions show whether a model can classify the records; a 5% sample
  answers them almost as well as the whole document, so they are not evidence
  of reading. Under `relative`, a reader that opens nothing and divides the
  record count by the number of labels already scores 0.43 to 0.55 on counts,
  and longer documents are not harder.
- On the two paired intent sets, where the compared categories hold about 60
  records each, topic search gets 0.73 (Turkish) and 0.81 (English) on core
  questions.
- The 3-label review sets contribute one core question in total: once
  "neutral" is excluded, their two remaining labels are rarely close.
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
| `interpress_tr`, `sinema_tr` | `most_common`, `least_common`, `second_most` | section shares and adjacent ratings are too close to rank with the required 15% margin |
| `vitamins_tr`, `musteri_tr`, `amazon_hpc_en` | close comparisons | with "neutral" excluded, the two remaining labels are rarely close (`marc_en` has one) |

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
