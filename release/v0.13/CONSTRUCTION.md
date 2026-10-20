# How TR-OOLONG v0.13 is built

This file describes every step from the source datasets to the released
documents and answers, in enough detail to check any answer by hand.
`recompute_answers.py` implements the answer definitions in section 5.

## 1. Sources and cleaning

| set | language | source (pinned revision or file hash in `provenance.json`) | what a record is |
|---|---|---|---|
| `musteri_tr` | Turkish | MusteriYorumlari (Hepsiburada, Trendyol) | a shopping review |
| `sinema_tr` | Turkish | BuyukSinema | a film review |
| `doktor_tr` | Turkish | doktorsitesi.com questions (Hugging Face: alibayram/doktorsitesi) | a patient's question to a doctor |
| `trnews2025_tr` | Turkish | TRNEWS-2025 (Kaggle) | a news article (its lead) |
| `tez_tr`, `tez_en` | Turkish, English | Turkish academic theses (YÖK, via Hugging Face) | the Turkish and the English abstract of the same thesis |
| `massive_tr`, `massive_en` | Turkish, English | MASSIVE (tr-TR, en-US), the same utterances | a voice-assistant request |
| `amazon_hpc_en` | English | Amazon Reviews 2023, Health and Personal Care | a product review |
| `amazon_movies_en` | English | Amazon Reviews 2023, Movies and TV | a film review |
| `amazon_shop_en` | English | Amazon Reviews 2023, six everyday categories | a product review |
| `wikinews_en` | English | English Wikinews (Wikimedia dump) | a news article (its lead) |
| `vitamins_tr` | Turkish | Vitamins and Supplements Reviews | a supplement review (outside the main results, see the card) |

### Selection

- `musteri_tr`: the train split, randomly cut to the size of its smallest star
  class (seed 42). `sinema_tr`: the train split, 80 to 3,000 characters.
  `vitamins_tr`: at most 20,000 reviews per class (seed 42).
- `amazon_hpc_en`: every review with a rating in the category file.
- `amazon_movies_en`: 1 in 16 reviews, chosen by the SHA-256 of the review
  text; matched to `sinema_tr`: at least 15 words (`sinema_tr`'s shortest) and
  no mention of the disc, DVD/Blu-ray, shipping, packaging, case, delivery,
  seller, region, subtitles, refunds or returns (reviews of the product, not
  the film).
- `amazon_shop_en`: Electronics, Home and Kitchen, Clothing Shoes and Jewelry,
  Beauty and Personal Care, Cell Phones and Accessories, Toys and Games; about
  120,000 lines per category, chosen by the SHA-256 of the raw line; matched to
  `musteri_tr`: 3 to 37 words (its 5th to 95th percentile).
- `doktor_tr`: the question text; the doctor's specialty grouped as in
  `label_maps.json`; 5 to 150 words; only the 9 specialties a non-doctor can
  recognise from the question (section 2).
- `trnews2025_tr`: the article body, 30 to 150 words.
- `tez_tr`/`tez_en`: theses from 2005 on (older ones are scanned and carry
  OCR errors) with a single subject among the 12 used (section 2), a Turkish
  abstract of 30 to 150 words and an English abstract of 20 to 250 words whose
  word count is 0.8 to 2.0 times the Turkish one (outside that range one side
  was cut off). A Turkish abstract listed with two different English abstracts
  is dropped.
- `wikinews_en`: published articles with exactly one of five categories
  (section 2); the lead: the first paragraphs until at least 30 words, at most
  150.
- MASSIVE: all three partitions, both locales. A pair is dropped if either
  utterance contains the name of its intent; only pairs that survive cleaning
  in both languages are kept; intents with fewer than 100 utterances are
  dropped.

### Cleaning, all sets

1. HTML tags become spaces and HTML entities are decoded; whitespace is
   collapsed to single spaces.
2. Length limits as above (reviews otherwise 3 to 400 words; film reviews 15
   to 400).
3. Reviews that state their own score in the text ("7/10", "5 yıldız",
   "1 star") are removed, since the score decides the label.
4. Texts that occur with two different labels are removed; exact duplicates
   are kept together for the split (section 3).
5. Turkish records that a language identifier marks as English or Azerbaijani
   are removed (0.1-0.2%).

### Cleaning, set by set

Each rule below was found by profiling the text without its labels, and is
applied to every record of the set.

- `doktor_tr`, **personal names.** Patients address doctors by name, and each
  doctor answers in one specialty, so a name can give the label away. A known
  first name with any following surname is replaced next to a form of address
  ("Aylin hanım" -> "doktor hanım", "Suphi hocam" -> "hocam") or after a
  title ("Prof. Dr. Ahmet Yılmaz" -> "doktor"), and removed when it stands on
  its own ("Sağolun. Ali." -> "Sağolun."); cities and test names that are
  also first names are kept. Questions with an e-mail address or a
  self-introduction ("adım Serdar") are dropped. Numbers and identifiers were
  already masked by the site ("*** *** **").
- `trnews2025_tr`, **site text and fragments.** The source stores a window of
  about 1,024 characters of each article, often starting or ending mid-word.
  In order: articles containing a link prompt ("TIKLAYIN", "tıklayınız") or
  the marker "Haberin Devamı" are dropped; articles with two or more words
  glued without a space ("ediliyorMarmaris'te") hold pasted lists of other
  headlines and are dropped; one glued join gets its space; a cut-off start
  and end are trimmed to complete sentences, and the 30-150 word range is
  applied again; quote and dash styles are unified and doubled quotes
  undone; missing spaces after sentence ends and around all-capital headings
  are restored; articles with a sentence of 5+ words that occurs in 10 or more
  articles (site notices, and agency stories syndicated to many sites) are
  dropped.
- `tez_tr`/`tez_en`, **front matter and broken text.** A pair is dropped if
  either abstract names the department, institute, advisor, degree or page
  count ("Eğitim Bilimleri Bölümü", "Tez Danışmanı:", "Yüksek Lisans Tezi",
  "Department of", "Supervisor"), or the author's full name, since these give
  the field away; and if either abstract is garbled (under 60% letters,
  mis-decoded bytes, or not detected as its language).
- `wikinews_en`: wiki markup removed (link templates keep their text, image
  blocks and references removed); a leading dateline is removed; the 22 texts
  with broken markup left are dropped.

| set | records after cleaning (dev / test) |
|---|---|
| `musteri_tr` | 3,585 / 32,756 |
| `sinema_tr` | 4,578 / 40,603 |
| `doktor_tr` | 7,434 / 66,047 |
| `trnews2025_tr` | 34,410 / 308,842 |
| `tez_tr` / `tez_en` (pairs) | 4,295 / 38,335 |
| MASSIVE (per language) | 1,515 / 13,560 |
| `amazon_hpc_en` | 43,411 / 387,528 |
| `amazon_movies_en` | 45,871 / 411,102 |
| `amazon_shop_en` | 44,962 / 405,566 |
| `wikinews_en` | 1,156 / 10,806 |
| `vitamins_tr` | 3,929 / 34,588 |

These counts include the middle ratings of the review sets and MASSIVE's
`general` scenario, which are left out when documents are built (the counts
actually used are in each `manifest.json`, `source_report`).

## 2. Labels

`label_maps.json` gives the map from each source label to the released label.

- Reviews: the reviewer's own rating. 1-2 stars (film: 1-4 of 10) = negative
  (`olumsuz` / `negative`); 4-5 stars (film: 7-10) = positive (`olumlu` /
  `positive`); middle ratings are not used.
- `doktor_tr`: the specialty of the doctor the patient chose (a routing label,
  not a clinical diagnosis), among nine:
  kadın hastalıkları ve doğum, çocuk sağlığı, ruh sağlığı, diş, göz,
  dermatoloji, kulak burun boğaz, kalp ve damar, üroloji.
- `trnews2025_tr`: the section the article was filed under (9).
- `tez_tr`/`tez_en`: the thesis subject, 12 subjects grouped into 8 fields a
  non-expert can tell apart: `matematik-fizik-mühendislik` (mathematics,
  physics, civil and mechanical engineering), `ekonomi ve işletme`, `din`,
  `hukuk`, `kimya`, `tarih`, `türk dili ve edebiyatı`, `ziraat`. Both
  languages use the Turkish label names.
- `wikinews_en`: the article's one category among Politics and conflicts,
  Sports, Culture and entertainment, Economy and business, Science and
  technology (other categories are ignored).
- MASSIVE: the scenario, grouped into 11 labels (`time` = alarm, calendar,
  datetime; `media` = play, music, audio; `food` = cooking, takeaway;
  `lists_recommendation`; `email`, `iot`, `news`, `qa`, `social`, `transport`,
  `weather`); `general` is not used. Both languages use the English names.

Every set passed a blind check by a native speaker before it entered (rule and
results in the dataset card).

## 3. Development and test split

Each cleaned source is split 10% development / 90% test by a SHA-256 hash of
its normalised text. Exact duplicates, a MASSIVE utterance and its
translation, and a thesis's two abstracts fall on the same side. No record
text appears in both splits. This release contains the test split of the main
set and both splits of the close-comparison extension.

## 4. Main set: documents

Documents and questions were built with an adapted version of the OOLONG-synth
generator (Bertsch et al., 2025), with Turkish record lines and question
templates. The adapted code will be available to reviewers with the paper's
submission and released with the paper.

A document is a header, one line per record, and a closing reminder:

    Date: Oct 12, 2023 || User: 41076 || Instance: <record text>
    Tarih: 12 Ekim 2023 || Kullanıcı: 41076 || Kayıt: <record text>

`text` has these lines; `text_with_labels` is the same text with
` || Label: <label>` (Turkish: ` || Etiket: <label>`) at the end of every
line. Everything else (header, order, dates, users) is identical.

1. **Lengths.** Target lengths are the powers of two from 1,024 tokens to
   4,194,304 (16,777,216 for the Amazon sets), two documents per length. The
   number of records is floor((0.95 x target - header tokens - 250) / mean
   tokens per record line), with token counts measured by the Qwen3-8B
   tokenizer. `context_len` is the target; `n_tokens` is the measured length
   of `text`, which never exceeds the target (a draw that does not fit is
   redrawn). Lengths the source cannot fill are skipped and listed in the
   manifest.
2. **Label mix.** Every label of the set may appear. Each label gets a weight
   softmax(r^(1/T)), with r a random integer from 1 to 30 per label and the
   temperature T a random integer from 2 to 6 (field `temperature`); counts are
   the rounded weights times the number of records, adjusted to sum exactly to
   it. A label can get 0 records. `label_counts` gives the counts.
3. **Records.** Each label's records are drawn at random without replacement:
   no record appears twice within a document (records do recur across
   documents; near-duplicates are not ruled out). If a mix needs more records of a
   label than the source has, or the drawn records do not fit the length, a new
   mix is drawn (up to 50 times; field `attempt`); if none fits, the length is
   skipped.
4. **Order, users, dates.** Records are put in random order. User IDs are
   5-digit numbers: a pool of frequent users (one per 10 records) supplies each
   record's user with probability 0.8, otherwise a random other ID. Dates are
   uniform between 16 Feb 2022 and 21 Jun 2025. Users and dates are drawn
   independently of the labels.
5. **Parallel sets (MASSIVE, theses).** Each document is planned once and
   rendered in Turkish and English: same records, order, users, dates,
   questions and answers. It is sized in Turkish, which needs more tokens for
   these paired texts under the Qwen3-8B tokenizer, so the Turkish version is at its target length and the
   English version is shorter (MASSIVE about 1/1.22, theses about 1/1.48).
6. **Seeds.** Every random choice is seeded from a SHA-256 of the document's
   identifiers; `seed` is recorded and rebuilding gives byte-identical files.

## 5. Main set: questions

Up to 25 questions per document, spread evenly over the question kinds that
exist for that document (a seeded round-robin over group and kind). Questions
are in three groups: `counting`, `user`, `timeline`. Turkish questions are
reviewed translations of the English ones; every question also carries its
English wording and answer (`question_en`, `answer_en`). Label lists in
questions are in random order.

**Scope.** Many questions first restrict the records: to a list of user IDs, to
one calendar month of any year ("occur in March of any year"), or to a date
range (inclusive). The answer is computed on those records only.

| kind | answer | asked when |
|---|---|---|
| how many records have label X | the count | always |
| most common label | the label with the highest count | the scope holds at least two labels, and the top label is unique and at least 2 percentage points ahead |
| least common label | every label with the lowest count among those listed (0 counts) | the scope holds at least two labels, and they are not all tied |
| is X more common, less common or the same frequency as Y | by the two counts | the shares differ by more than 2 points, or are equal |
| which user appears most / second most often | that user | the rank is unique |
| which user has most records with label X | that user | unique |
| which user has more records with label X: A or B | the user with more | the counts differ by at least 2, and both users have the same total number of records in the document |
| which date appears most / second most often | that date (`YYYY-MM-DD`) | the rank is unique |
| how many dates appear exactly n times | the number of dates | n is the count of the 4th most frequent date |
| was X more common, less common or the same before date d than after | compares X's share among records strictly before d with its share strictly after d (records on d count on neither side) | the shares differ by more than 2 points, or are equal |
| for how many months is X the single most frequent label | months (year + month) where X's count is above every other label's | for each label present |
| for how many months is X more frequent than Y | months where X's count is above Y's | for each pair of labels present |
| in which month was X first more frequent than Y | the earliest such month (`March 2022`) | X has fewer records than Y in the whole document, and such a month exists |

Questions that need no labels (most frequent user or date, second most
frequent, dates appearing n times) test counting over the metadata; the
question about the user with most records of a label is also partly answered
by the most active user overall.

Months are calendar months of a specific year unless the question says "of any
year". Turkish answers translate comparison words (`daha fazla`, `daha az`,
`eşit sayıda`; `daha yüksek`, `daha düşük`, `aynı`) and month names; labels,
users, numbers and dates are unchanged.

## 6. Close-comparison extension

One question per document: "is label A more common, less common, or the same
frequency as label B?", at fixed small margins. Rules were fixed before the
first build, for the positive/negative sets and MASSIVE. On 21 October 2026,
before they were built, the same rules were applied to every set with more
than two labels (doctor questions, 2025 news, theses, Wikinews): a later
extension of the rules, reported as such.

- **Record counts** N = 2,048, 8,192 and 32,768 records per document.
- **Margins** |nA - nB| / N = 0%, 0.1%, 0.5%, 2% and 10%. The count difference
  is the even number nearest to margin x N (`count_difference`,
  `margin_realized`). 0% is an exact tie, answered "same frequency as".
- **Labels.** Two-label sets: A + B = N. Sets with more labels: A + B = N/2,
  and the other N/2 records are split equally over the other labels (MASSIVE:
  9 groups), the remainder assigned in a fixed order. Pairs rotate over all
  pairs of labels that can fill the document, in a fixed order that is the
  same at every margin (`pair_order` in the manifest).
- **Which cells exist.** A set is built at a record count, at all five margins,
  only if each compared label has enough records for the winner at 10% without
  repeating a record within a document. Skipped cells and the reason are in the
  manifest.
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

## 7. What was checked

- `recompute_answers.py` recomputes every answer from the labelled lines and
  checks label counts, the hidden/labelled text pair and the Turkish answers.
- Labels: every set passed a blind check by native speakers (rule and results
  in the dataset card). Translation of the questions was reviewed by a native
  speaker.
- Shortcut checks on the main set and the extension are summarised in the
  dataset card.
