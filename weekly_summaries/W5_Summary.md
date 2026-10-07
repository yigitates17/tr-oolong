# TR-OOLONG: Weeks 4 and 5

*1 October 2026, updated 6 October. There was no meeting in week 4, so this summary covers both
weeks. The main text is one page; the appendices hold the detail.*

## 1. Summary

In week 4 three Turkish datasets were added (consumer complaints, news, film
reviews) and the benchmark was published on Hugging Face. In week 5 a review
found that most questions could be answered **without reading the whole
document**: for example, "which label is most common?" was answered correctly
96% of the time from a random 5% of the records, and OOLONG turned out to have
the same weakness. A new kind of question was built that the shortcuts tested do not answer,
"are there more negative or more positive reviews?" when the document holds
1,000 negative and 986 positive ones. A native-speaker check of the labels then
led to a final cleaning round, and the benchmark was republished as version
0.10 with 309 such questions, 77 of them identical in Turkish and English.

## 2. The problem

A model that works on a document through code, as RLM does, has two ways to
avoid reading all of it:

- **Sampling**: read a small random part and scale up. *Example:* "which label
  is most common?" If one label clearly leads, it also leads in a 5% sample. On
  the published TR-OOLONG questions of this type, a 5% reader answered exactly
  right 96% of the time; on OOLONG's "which label is more frequent" questions,
  78% of the time.
- **Search**: find the few relevant records and read only those. *Example:*
  OOLONG asks "among records from user 41076, which label is most common?" and
  prints the user id on every record. Searching for it reads 15 of 1,772 records
  and gives the exact answer; across OOLONG such questions need 0.8% of the
  document and are answered exactly 99% of the time.

In the published version, most TR-OOLONG questions had one of these two
weaknesses. The answers were correct; the questions did not prove that a model
read the document. No published work had measured this for OOLONG either.

## 3. The fix

**Close comparisons**: "which are there more of, A or B?", where A and B are
both large and their counts are very close. Sampling cannot resolve a small
difference, and there are too many relevant records to find by search.

*Example:* a document of 2,500 health-product reviews contains 1,000 negative
and 986 positive reviews. "Which are there more of, negative or positive?"
Answer: negative. The Turkish document built alongside it has 1,000 *olumsuz*
and 986 *olumlu* reviews and asks the same question in Turkish.

Every shortcut found was tried on these questions (short programs, not AI
models, told the correct label of each record they read):

| reader | correct (guessing = 0.50) |
|---|---:|
| always pick the first-named label | 0.50 |
| pick the label more common in the source dataset | 0.50 |
| read a random 5% / 25% / 50% of the document | 0.53 / 0.57 / 0.62 |
| read the 10% of records most related to the two labels | 0.49 |
| **read everything, label 95% of records correctly** | **0.85** |

*(Figures for the 214 questions from documents built for this purpose; all 309
core questions are in appendix B.)*

**A further rule, from the label check.** A comparison is only asked between
two categories that can actually be told apart from the text, measured with a
simple classifier. *Example of what this excludes:* a complaint about a refund,
with no product named, filed under "furniture and home textiles"; or news filed
under "tourism" vs "travel". For the same reason the film reviews now use
sentiment (negative, neutral, positive) instead of exact 1-10 ratings: "loved
it" can be a 7 or a 10, and no reader can tell which.

## 4. Where the benchmark stands (version 0.10.0, published 1 October)

| | week 3 meeting | now |
|---|---:|---:|
| datasets | 8 | 11 (3 Turkish only) |
| documents | 110 | 347 |
| questions | 1,254 | 2,362 |
| total length | 28.3M tokens | 102.5M tokens |
| questions no tested shortcut answers (core) | not measured | 309 |

Every question now states what it shows:

| role | Turkish | English | what it shows |
|---|---:|---:|---|
| **core** | 217 | 92 | that a model read and judged the whole document |
| retrieval | 185 | 52 | that it can find a few records by meaning |
| control | 1,213 | 603 | that it can classify the records at all |

*Examples.* Core: "more positive or more negative reviews?" when the document
holds 1,000 and 986; no shortcut tested scores above 0.62, against 0.50 for a
coin toss. Retrieval: "how many complaints are about insurance?" with an answer
between 5 and 30. Control: counts, percentages and rankings, which a 5% sample
answers almost as well as the whole document.

**How answers are scored.** For a true answer of 30 and a reply of 25: *exact*
gives 0 (right or wrong; used for word answers, so for all core questions);
*partial*, OOLONG's rule, gives 0.24 (each unit of error costs about a quarter;
used for small counts); *relative*, added here, gives 0.83 (the error as a share
of the answer; used for large numbers, where OOLONG's rule turns being 3 off
890 into a near-zero score). Results always state the rule used. The answer key
comes from the source datasets' labels, some of which are wrong, so even a
perfect reader scores about 0.85 on core questions.

**Cross-lingual:** comparisons are made inside each Turkish/English pair, never
between totals. **77 core questions are the same question with the same answer
in both languages**, from three different pairs of corpora (the RLM paper's
OOLONG results rest on 50 questions).

**No AI model has been run yet.** Model runs start once the dataset is final.

## 5. Decisions required

1. **Thesis title.** Current: *Recursive Language Models for Turkish
   Long-Context Aggregation: A Matched-Twin Benchmark and a Cross-Lingual
   Study.* Three 2026 papers find that recursion itself is not what makes RLM
   work; working on the document through code is. Apple's SRLM reports that
   "recursion itself is not the primary driver of performance" (choosing among
   several candidate programs does as well or better, by up to 22%); λ-RLM
   replaces free code with fixed building blocks and beats RLM in 29 of 36
   comparisons; a reproduction (Wang) finds that deeper recursion lowers
   accuracy. So a title that does not rest on "recursive" is safer, for
   example *Do Long-Context Models Read in Turkish? A Matched Turkish-English
   Aggregation Benchmark and a Cross-Lingual Study.*
2. **Target venue.** NeurIPS 2027, Evaluations & Datasets track (A*; deadline
   around May 2027), with ACL, EMNLP (A*) or EACL (A) as fallback. Whether
   "Findings" papers count for graduation needs checking. NeurIPS fits because:
   - the track now explicitly covers audits of existing datasets;
   - TR-OOLONG also shows that OOLONG's questions can be answered by sampling
     or search, and its core questions show whether a method read the whole
     document;
   - RLM was accepted at NeurIPS 2026, and such methods are tested only in
     English.

---

## Appendix A. What changed since the week 3 meeting

- **Three Turkish datasets added** (week 4): consumer complaints (29
  categories), news articles (16 sections), film reviews (10-point ratings). A
  3-category dataset cannot produce questions with small answers.
- **Published** on Hugging Face (16 September); a correction on 20 September
  gave every question a unique id (combining datasets had silently lost 57% of
  the questions).
- **One question type removed** (`shift`, "did X rise or fall in the second
  half"): reading 50 records at each end answers it.
- **Difficulty grades withdrawn.** They were based on four skimming programs
  that answer 0 when they see nothing; one that answers "about 12" instead broke
  145 of the 226 "very hard" counting questions. *Example: 990 complaints, "how
  many are about transport?", true answer 11; answering 12 scores 0.91.*
- **Brand questions removed** (137). The brand is printed in the text, so
  searching for it answers them. *Example: "how many reviews of 'FASH Limited'
  are negative?" means reading the 21 reviews with that brand out of 1,685.*
- **Close comparisons added** (version 0.8 from ordinary documents; version 0.9
  from documents built for them).
- **Cleaning** (version 0.10), found during the label check: newspaper
  mastheads instead of articles (2.1% of news records); reviews that write their
  score in the text, which hands over a rating-based label ("ben 6/10
  veriyorum", "1 star"; 11.2% of film reviews, 1-3% elsewhere); leftover web
  formatting in 12.7% of Amazon reviews. All removed.
- **Only categories that can be told apart** are compared (version 0.10, see
  section 3). Kept for comparisons: 32 of 48 intents, 23 of 29 complaint
  categories, 5 of 16 news sections, positive vs negative everywhere.
- **Questions kept unchanged where possible:** every rebuild was compared
  question by question; the intent and complaint datasets' other questions are
  identical to version 0.7.

`W4_Summary.md` sections 1 to 3 (answers to the week 3 questions on recursion
depth, parallel sub-calls, string-search exploits, test targets and publishing)
still stand; its other sections are replaced by this summary.

## Appendix B. The full check of the core questions

| angle of attack | result |
|---|---|
| answers wrong | none: every answer recomputed by independent code |
| label written in the text | none as written; but 8 news labels are spelled without Turkish letters ('saglik'), and the Turkish spelling ('sağlık') still appears in the text. Found 6 October, to be fixed |
| sampling 5% / 25% / 50% | 0.53 / 0.58 / 0.62 (all 309) |
| searching the most related 10% | 0.54 (all), 0.49 (built documents) |
| label more common in the source dataset | 0.53 (all), 0.50 (built), 0.62 (the 95 from ordinary documents) |
| always the first-named label | 0.51 (all), 0.50 (built) |
| score written in the text, masthead, web formatting | removed (version 0.10) |
| categories that cannot be told apart from the text | never compared (version 0.10) |
| two counts differ by 3 records or fewer | none in built documents (at least 5); 6 from ordinary documents |
| documents sharing records | at most 22% |
| length coverage | 150 core questions up to 100K tokens, 117 between 100K and 600K, 42 above |
| Turkish vs English length on matched documents | intent: Turkish 1.3x longer; reviews: Turkish 0.6-0.9x |
| reader of everything, 95% / 90% labelling accuracy | 0.86 / 0.76 |

Earlier passes of this check found and fixed: gaps of only 1-3 records, too few
core questions on long documents, a chance alignment that let "pick the rarer
label" score 0.70 on one dataset, and, during the label check, the leaks and
unreadable categories above. Details: `experiments/REPORT.md`, experiments 10
and 11.

## Appendix C. TR-OOLONG and OOLONG

| | OOLONG | TR-OOLONG |
|---|---|---|
| languages | English | Turkish, with English counterparts built the same way |
| document length | 1K to 4M tokens | 36K to 1M tokens |
| labels per dataset | 2 to 10 | 3 to 48 |
| questions that resist sampling and search | none found | 309 |
| same question and answer in two languages | no | yes (77 core questions) |
| shortcut checks published | none | yes |

**OOLONG's two shortcuts, in one line each.**
- *Search:* OOLONG asks "which label is most common for user 41076?" and prints
  the user on every record, so searching for "41076" finds the 15 relevant
  records out of 1,772, and those give the answer. This is not one case: about
  a third of OOLONG's questions are about one user or one month, and the same
  search answers them exactly 99% of the time.
- *Sampling:* when OOLONG asks which of two labels is more frequent, the counts
  usually differ a lot, so a random 5% of the records picks the right label 78%
  of the time.

Others have noticed that code-using systems sometimes fall back on keyword
search on OOLONG (the RLM paper, an agent paper), but no measurement of how
much of OOLONG it answers was found.

## Appendix D. Literature (details in `LITERATURE_REVIEW.md`)

- Three 2026 papers find that recursion itself is not what makes RLM work; the
  gains come from working on the document through code.
- Several new code-using systems are tested on OOLONG, all in English only.
  None of those checked measures how much of the document was actually read. The RLM
  paper describes it from example runs (RLM labels the records one by one; a
  version without further model calls falls back on keyword searches), and one
  agent paper notes that coding agents use keyword patterns instead of reading.
- No other benchmark covers Turkish long-context aggregation.
- The RLM authors released an 8-billion-parameter model trained to work this
  way, on English tasks only (not OOLONG); it has not been tested in Turkish.
- **Venues (checked 6 October).** The RLM paper is accepted at NeurIPS 2026 and
  OOLONG at COLM 2026. The RLM paper's OOLONG result rests on 50 questions from
  one dataset at one length; TR-OOLONG has 77 hard questions identical in
  Turkish and English. The only new multilingual long-context benchmark found
  (MGAL, August 2026) has no Turkish and does not test aggregation.
- **Why RLM was accepted although recursion is not what helps.** Its main idea
  is that the model works on the long text through code instead of reading it
  directly; the 2026 follow-ups keep that idea and question only the recursion.
  For TR-OOLONG this changes nothing: the benchmark tests whether a method reads
  the whole document, in Turkish and English, whatever the method is.

## Appendix E. Later: training data and further releases

Logs of successful model runs can be checked step by step here, because the
correct label of every record is known, which makes them useful for training
models to work through long Turkish documents (provided only logs that actually
read everything count as successful, and training documents use records never
used in the test set). The benchmark, a training split, the run logs and the
shortcut-testing programs could each be published as separate datasets.
