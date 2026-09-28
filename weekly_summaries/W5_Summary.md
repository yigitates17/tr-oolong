# TR-OOLONG: Weeks 4 and 5

*29 September 2026. There was no meeting in week 4, so this summary covers both
weeks. The main text is one page; the appendices hold the detail.*

## 1. Summary

In week 4 three Turkish datasets were added (consumer complaints, news, film
reviews) and the benchmark was published on Hugging Face. In week 5 a review
found that most questions could be answered **without reading the whole
document**: for example, "which label is most common?" was answered correctly
96% of the time from a random 5% of the records, and OOLONG turned out to have
the same weakness. A new kind of question was built that cannot be answered that way,
"are there more negative or more positive reviews?" when the document holds
1,000 negative and 986 positive ones, and the benchmark was republished as
version 0.9 with 418 such questions.

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
| pick the label more common in the source dataset | 0.49 |
| read a random 5% / 25% / 50% of the document | 0.53 / 0.58 / 0.64 |
| read the 10% of records most related to the two labels | 0.49 |
| **read everything, label 95% of records correctly** | **0.85** |

*(Figures for the 244 questions from documents built for this purpose; all 418
core questions are in appendix B.)*

## 4. Where the benchmark stands (version 0.9.0, published 29 September)

| | week 3 meeting | now |
|---|---:|---:|
| datasets | 8 | 11 (3 Turkish only) |
| documents | 110 | 353 |
| questions | 1,254 | 2,521 |
| total length | 28.3M tokens | 106.4M tokens |
| questions that need the whole document | not measured | 418 |

Every question now states what it shows:

| role | Turkish | English | what it shows |
|---|---:|---:|---|
| **core** | 298 | 120 | that a model read and judged the whole document |
| retrieval | 213 | 52 | that it can find a few records by meaning |
| control | 1,235 | 603 | that it can classify the records at all |

**Cross-lingual:** comparisons are made inside each Turkish/English pair, never
between totals. **91 core questions are the same question with the same answer
in both languages**, from three different pairs of corpora.

**No AI model has been run yet.** That is the next step.

## 5. Still open

- **Model runs.** First each model's accuracy on single records, then whole
  documents in one prompt, then code-using systems (RLM, RLM-Qwen3-8B, Claude
  Code), recording the code each one writes.
- **A check of the source labels.** Some source labels are wrong (3% to 9% on
  the intent data), and when two counts differ by a few records a few wrong
  labels can flip the answer, so even a perfect model scores below 1.0 on core
  questions (about 0.85 with 5% of labels wrong). A native-speaker check of 200
  Turkish records is prepared.

## 6. Decisions required

1. **Thesis title.** Current: *Recursive Language Models for Turkish
   Long-Context Aggregation: A Matched-Twin Benchmark and a Cross-Lingual
   Study.* Three 2026 papers find that recursion itself is not what makes RLM
   work (appendix D), so a title that does not rest on "recursive" is safer, for
   example *Do Long-Context Models Read in Turkish? A Matched Turkish-English
   Aggregation Benchmark and a Cross-Lingual Study.*
2. **Target venue.** On the current CORE ranking (ICORE2026), ACL, EMNLP,
   NeurIPS (including its Datasets and Benchmarks track), ICLR and ICML are A*;
   NAACL and EACL are A; COLING and LREC are B. With model results, NAACL or EACL
   is realistic and ACL, EMNLP or NeurIPS Datasets and Benchmarks is the stretch.
   Whether "Findings" papers count for graduation needs checking.

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
- **Close comparisons added** (version 0.8, 174 questions from ordinary
  documents; version 0.9, 244 more from documents built for them).
- **All earlier documents and questions are unchanged** in every rebuild,
  checked one by one.

`W4_Summary.md` sections 1 to 3 (answers to the week 3 questions on recursion
depth, parallel sub-calls, string-search exploits, test targets and publishing)
still stand; its other sections are replaced by this summary.

## Appendix B. The full check of the core questions

| angle of attack | result |
|---|---|
| answers wrong | none: every answer recomputed by independent code |
| label written in the text | none of the shipped records |
| sampling 5% / 25% / 50% | 0.53 / 0.58 / 0.63 (all 418) |
| searching the most related 10% | 0.56 (all), 0.49 (built documents) |
| label more common in the source dataset | 0.54 (all), 0.49 (built), 0.61 (the 174 older ones) |
| always the first-named label | 0.52 (all), 0.50 (built) |
| two counts differ by 3 records or fewer | none in built documents (at least 5); 12 older ones |
| documents sharing records | at most 22% |
| length coverage | 210 core questions up to 100K tokens, 156 between 100K and 600K, 52 above |
| Turkish vs English length on matched documents | intent: Turkish 1.3x longer; reviews: Turkish 0.6-0.9x |
| reader of everything, 95% / 90% labelling accuracy | 0.85 / 0.76 |

The first pass of this check found three problems, all fixed before release:
some gaps of only 1-3 records, too few core questions on long documents, and a
chance alignment that let "pick the rarer label" score 0.70 on one dataset.
Details: `experiments/REPORT.md`, experiment 10.

## Appendix C. TR-OOLONG and OOLONG

| | OOLONG | TR-OOLONG |
|---|---|---|
| languages | English | Turkish, with English counterparts built the same way |
| document length | 1K to 4M tokens | 36K to 1M tokens |
| labels per dataset | 2 to 10 | 3 to 48 |
| questions that resist sampling and search | none found | 418 |
| same question and answer in two languages | no | yes (91 core questions) |
| shortcut checks published | none | yes |

## Appendix D. Literature (details in `LITERATURE_REVIEW.md`)

- Three 2026 papers find that recursion itself is not what makes RLM work; the
  gains come from working on the document through code.
- Several new code-using systems are tested on OOLONG, all in English only, and
  none checks whether its system read the whole document.
- No other benchmark covers Turkish long-context aggregation.
- The RLM authors released an 8-billion-parameter model trained to work this
  way; it has not been tested in Turkish.

## Appendix E. Later: training data and further releases

Logs of successful model runs can be checked step by step here, because the
correct label of every record is known, which makes them useful for training
models to work through long Turkish documents (provided only logs that actually
read everything count as successful, and training documents use records never
used in the test set). The benchmark, a training split, the run logs and the
shortcut-testing programs could each be published as separate datasets.
