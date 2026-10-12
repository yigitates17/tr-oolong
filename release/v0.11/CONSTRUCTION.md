# How TR-OOLONG v0.11 is built

This file describes every step from the source datasets to the released
documents and answers, in enough detail to check any answer by hand.
`recompute_answers.py` implements the answer definitions in section 5.

## 1. Sources and cleaning

| set | language | source (pinned revision in `provenance.json`) | what a record is |
|---|---|---|---|
| `musteri_tr` | Turkish | MusteriYorumlari (Hepsiburada, Trendyol) | a shopping review |
| `sinema_tr` | Turkish | BuyukSinema (Beyazperde) | a film review |
| `marc_en` | English | Multilingual Amazon Reviews Corpus, English part | a product review |
| `amazon_hpc_en` | English | Amazon Reviews 2023, Health and Personal Care | a health product review |
| `massive_tr`, `massive_en` | Turkish, English | MASSIVE (tr-TR, en-US), the same utterances | a voice-assistant request |
| `vitamins_tr` | Turkish | Vitamins and Supplements Reviews | a supplement review (outside the main results, see the card) |

Selection from each source (before cleaning):

- `musteri_tr`: the train split, randomly cut to the size of its smallest
  star class (seed 42).
- `sinema_tr`: the train split, reviews of 80 to 3,000 characters.
- `vitamins_tr`: the train split, at most 20,000 reviews per sentiment class
  (random, seed 42).
- `marc_en`: the train split of the copy named in `provenance.json`, randomly
  cut to the size of its smallest sentiment class (seed 42).
- `amazon_hpc_en`: reviews in file order whose product has a brand in the
  category's product metadata, until each sentiment class (negative, neutral,
  positive) has 20,000.
- MASSIVE: all three partitions, both locales. A pair is dropped if either
  utterance contains the name of its intent; only pairs that survive cleaning
  in both languages are kept; intents with fewer than 100 utterances are
  dropped.

Cleaning, in order:

1. HTML tags become spaces and HTML entities are decoded (review sets);
   whitespace is collapsed to single spaces.
2. Length limits: 3 to 400 words (film reviews: 15 to 400 words; MASSIVE: 1 to
   400 words).
3. Reviews that state their own score in the text ("7/10", "5 yıldız
   veriyorum", "1 star") are removed, since the score decides the label.
4. Texts that occur with two different labels are removed; exact duplicates
   are kept together for the split (section 3).

| set | removed: score in text | removed: conflicting labels | records after cleaning (dev / test) |
|---|---:|---:|---|
| `musteri_tr` | 639 | 61 | 3,585 / 32,756 |
| `sinema_tr` | 6,129 | 4 | 4,578 / 40,603 |
| `vitamins_tr` | 449 | 894 | 3,929 / 34,588 |
| `marc_en` | 3,570 | 282 | 11,562 / 104,229 |
| `amazon_hpc_en` | 1,488 | 317 | 5,482 / 48,887 |
| MASSIVE (per language) | 0 | 0 | 1,515 / 13,560 |

These counts include the middle ratings. When documents are built, records with
a middle rating or MASSIVE's `general` scenario are left out, and Turkish
reviews that a language identifier marks as English or Azerbaijani are removed
(0.1-0.2%); those two counts are in each `manifest.json` (`source_report`).

## 2. Labels

`label_maps.json` gives the map from each source label to the released label.

- Reviews: the reviewer's own rating. 1-2 stars (film: 1-4 of 10) =
  negative (`olumsuz` / `negative`); 4-5 stars (film: 7-10) = positive
  (`olumlu` / `positive`); middle ratings are not used.
- MASSIVE: the utterance's scenario, with related scenarios grouped into 11
  labels: `time` (alarm, calendar, datetime), `media` (play, music, audio),
  `food` (cooking, takeaway), `lists_recommendation` (lists, recommendation),
  `email`, `iot`, `news`, `qa`, `social`, `transport`, `weather`. The
  `general` scenario (jokes and small talk) is not used. Turkish and English
  documents use the same English label names.

The groupings were fixed by a rule written down before a fresh blind review of
Turkish records (keep MASSIVE's 18 scenarios if a native speaker agrees with at
least 70% of their labels, otherwise use the coarser groups if they reach 70%;
the scenarios reached 67%, the groups 79%, on 33 records). The `general`
scenario was removed after this check; on the 31 records left, the groups
reach 84%.

## 3. Development and test split

Each cleaned source is split 10% development / 90% test by a SHA-256 hash of
its normalised text. Exact duplicates, and a MASSIVE utterance and its
translation, fall on the same side. No record text appears in both splits.
This release contains the test split of the main set and both splits of the
close-comparison extension.

## 4. Main set: documents

Documents and questions were built with an adapted version of the OOLONG-synth
generator (Bertsch et al., 2025), with Turkish record lines and question
templates. The adapted code is released with the paper.

A document is a header, one line per record, and a closing reminder:

    Date: Oct 12, 2023 || User: 41076 || Instance: <record text>
    Tarih: 12 Ekim 2023 || Kullanıcı: 41076 || Kayıt: <record text>

`text` has these lines; `text_with_labels` is the same text with
` || Label: <label>` (Turkish: ` || Etiket: <label>`) at the end of every
line. Everything else (header, order, dates, users) is identical.

1. **Lengths.** Target lengths are the powers of two from 1,024 to 4,194,304
   tokens, two documents per length. The number of records is
   floor((0.95 x target - header tokens - 250) / mean tokens per record line),
   with token counts measured by the Qwen3-8B tokenizer. `context_len` is the
   target; `n_tokens` is the measured length of `text`. Lengths the source
   cannot fill are skipped and listed in the manifest.
2. **Label mix.** Every label of the set may appear. Each label gets a weight
   softmax(r^(1/T)), with r a random integer from 1 to 30 per label and the
   temperature T a random integer from 2 to 6 (field `temperature`); counts are
   the rounded weights times the number of records, adjusted to sum exactly to
   it. A label can get 0 records. `label_counts` gives the counts.
3. **Records.** Each label's records are drawn at random without replacement:
   no record appears twice in a document. If a mix needs more records of a
   label than the source has, a new mix is drawn (up to 50 times; field
   `attempt`); if none fits, the length is skipped. At the longest lengths the
   mixes are therefore those the sources can fill.
4. **Order, users, dates.** Records are put in random order. User IDs are
   5-digit numbers: a pool of frequent users (one per 10 records) supplies each
   record's user with probability 0.8, otherwise a random other ID. Dates are
   uniform between 16 Feb 2022 and 21 Jun 2025. Users and dates are drawn
   independently of the labels.
5. **Parallel MASSIVE.** Each MASSIVE document is planned once and rendered in
   Turkish and English: same records, order, users, dates, questions and
   answers. It is sized in English, so the Turkish version has more tokens.
6. **Seeds.** Every random choice is seeded from a SHA-256 of the document's
   identifiers; `seed` is recorded and rebuilding gives byte-identical files.

## 5. Main set: questions

Up to 25 questions per document, spread evenly over the question kinds that
exist for that document (a seeded round-robin over group and kind). Questions
are in three groups: `counting`, `user`, `timeline`. Turkish questions are
reviewed translations of the English ones; every question also carries its
English wording and answer (`question_en`, `answer_en`).

**Scope.** Many questions first restrict the records: to a list of user IDs, to
one calendar month of any year ("occur in March of any year"), or to a date
range (inclusive). The answer is computed on those records only.

| kind | answer | asked when |
|---|---|---|
| how many records have label X | the count | always |
| most common label | the label with the highest count | it is unique and at least 2 percentage points ahead |
| least common label | every label with the lowest count among those listed (0 counts) | always |
| is X more common, less common or the same frequency as Y | by the two counts | the shares differ by more than 2 points, or are equal |
| which user appears most / second most often | that user | the rank is unique |
| which user has most records with label X | that user | unique |
| which user has more records with label X: A or B | the user with more | the counts differ by at least 2 |
| which date appears most / second most often | that date (`YYYY-MM-DD`) | the rank is unique |
| how many dates appear exactly n times | the number of dates | n is the count of the 4th most frequent date |
| was X more common, less common or the same before date d than after | compares X's share among records strictly before d with its share strictly after d (records on d count on neither side) | the shares differ by more than 2 points, or are equal |
| for how many months is X the single most frequent label | months (year + month) where X's count is above every other label's | for each label present |
| for how many months is X more frequent than Y | months where X's count is above Y's | for each pair of labels present |
| in which month was X first more frequent than Y | the earliest such month (`March 2022`) | for each pair of labels present, when such a month exists |

Months are calendar months of a specific year unless the question says "of any
year". Turkish answers translate comparison words (`daha fazla`, `daha az`,
`eşit sayıda`; `daha yüksek`, `daha düşük`, `aynı`) and month names; labels,
users, numbers and dates are unchanged.

## 6. Close-comparison extension

One question per document: "is label A more common, less common, or the same
frequency as label B?", at fixed small margins. Rules were fixed before the
first build.

- **Record counts** N = 2,048, 8,192 and 32,768 records per document.
- **Margins** |nA - nB| / N = 0%, 0.1%, 0.5%, 2% and 10%. The count difference
  is the even number nearest to margin x N (`count_difference`,
  `margin_realized`). 0% is an exact tie, answered "same frequency as".
- **Labels.** Review sets: A + B = N. MASSIVE: A + B = N/2, and the other N/2
  records are split equally over the other 9 groups. MASSIVE pairs rotate over
  all pairs of groups that can fill the document, in a fixed order that is the
  same at every margin (`pair_order` in the manifest).
- **Which cells exist.** A set is built at a record count, at all five margins,
  only if each compared label has enough records for the winner at 10% without
  repeating a record. Built: `musteri_tr`, `sinema_tr`, `amazon_hpc_en` at
  2,048 and 8,192; `marc_en` at all three; MASSIVE at 2,048. The development
  split is smaller, so it has documents only for `musteri_tr`, `marc_en` and
  `amazon_hpc_en` at 2,048. Skipped cells and the reason are in the manifest.
- **Documents per cell.** 20 test and 4 development documents. Which label
  wins and whether the winner is named first or second are balanced
  independently: each of the 4 combinations occurs 5 times (test) / once
  (development). Ties: each label is named first in half the documents.
- **Records, order, users, dates, line format** as in the main set. Records are
  drawn independently for each document, so the same record can occur in
  several documents of a set.
- **Two renderings.** Every document has `text` and `text_with_labels`, which
  differ only by the labels. The two renderings of one document share the
  question and answer; report results per rendering, and treat the two
  renderings (and MASSIVE's two languages) as one document when computing
  intervals.

## 7. Sets without text: `marc_en`, `amazon_hpc_en`

Their licences do not allow redistributing the review text (dataset card). Each
document keeps everything except the text: `header`, `footer`, and
`records` (for each line its date, user and the first 16 hex digits of the
SHA-256 of the record text), plus the SHA-256 of `text` and
`text_with_labels`. To restore the text, download the source file listed in
`provenance.json` and run

    python recompute_answers.py data --restore marc_en=train.jsonl \
        --restore amazon_hpc_en=Health_and_Personal_Care.jsonl --write restored

The script applies the cleaning of section 1 to each source row, matches the
hashes, takes the label from the rating (`label_maps.json`), rebuilds each
document and checks its SHA-256 before recomputing the answers. Five
`amazon_hpc_en` texts occur in the source file more than once with different
ratings; `restore_hints.json` gives the line of the occurrence that was used.

## 8. What was checked

- `recompute_answers.py` recomputes every answer from the labelled lines and
  checks label counts, the hidden/labelled text pair and the Turkish answers.
- Labels: a native speaker labelled records blind (Turkish 140, then 72
  fresh records for the MASSIVE and complaint groupings; English 80); agreement per set is in the dataset card. Translation of the
  questions was reviewed by a native speaker.
- Extension: shortcut checks (sampling, question-only, label prior, keyword,
  metadata, repeated records, label-error sensitivity) are summarised in the
  dataset card.
