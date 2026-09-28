# TR-OOLONG: Weeks 4 and 5

*28 September 2026. There was no meeting in week 4, so this summary covers
both weeks and can be read without the week 4 file.*

**How to read the two files.** `W4_Summary.md` sections 1 to 3 answer the
questions raised at the week 3 meeting (recursion depth, parallel sub-calls,
string-search exploits, where to test a model trained on this data, publishing)
and those answers still stand. Its sections 0 and 4 to 7 are replaced by this
summary: several of their claims about difficulty were tested this week and did
not hold.

## 1. In one paragraph

The benchmark's answers were always correct, but most of its questions could be
answered without reading the whole document: a model can **sample** a small
part and scale up, or **search** for the few relevant records. That is a
problem for this thesis in particular, because the method under study (RLM)
works by writing code over the document, and code can sample and search. The
same weakness was found in OOLONG, the benchmark this work follows. A new
question type was designed that neither sampling nor search can answer, the
questions that searching answers outright were removed, and every question now
states what it measures. The benchmark was rebuilt as version 0.8 and checked;
it is not yet published.

## 2. Where the benchmark stands

| | at the week 3 meeting | published now (v0.7.1) | built, not yet published (v0.8.0) |
|---|---:|---:|---:|
| datasets | 8 | 11 | 11 |
| documents | 110 | 195 | 195 (unchanged) |
| questions | 1,254 | 2,240 | 2,277 |
| question types | 10 | 9 | 7 |
| questions that need the whole document | not measured | not measured | 174 |

Also since the week 3 meeting:

- **Three Turkish datasets added**: consumer complaints (29 categories), news
  articles (16 sections, with dates) and film reviews (10-point ratings).
- **One question type removed** (`shift`, "did X rise or fall in the second
  half"): reading 50 records at each end answers it.
- **Published** on Hugging Face (16 September), with a correction on 20
  September: question numbers repeated across datasets, so combining datasets
  could silently lose 57% of the questions. Fixed with a unique id per question.
- **Every answer re-checked** by an independent computation; no record contains
  its own label.
- **Documentation rewritten** so it can be read without the code.
- **No AI model has been run on the benchmark yet.**

## 3. What was found

Every "reader" below is a short program, not an AI model. Most are told the
correct label of each record they read, so they show what a reading strategy
*can* achieve. Each experiment, with its setup and a worked example, is in
`experiments/REPORT.md`.

**Finding 1: the earlier difficulty grades were misleading.** Each question had
been graded by how well four skimming programs answered it, and 259 were graded
"very hard". All of those had small answers, and the four programs failed only
because they answer 0 when their sample holds no match. A program that answers
"about 12" instead took 145 of the 226 very-hard counting questions out of that
grade. *Example: 990 complaints, "how many are about transport?", true answer
11; a 5% sample usually holds 0 or 1 transport complaints; answering 12 scores
0.91.* The grades are withdrawn.

**Finding 2: what each question type actually measured.**

| question type | share (v0.7) | shortcut that answers it |
|---|---:|---|
| counts and proportions of common categories | 51% | sampling 5% of the document |
| most / least / second most common | 18% | sampling |
| "is X more or less common than Y" (counts at least 15% apart) | 13% | sampling |
| rare-category counts (answer 5 to 30) | 12% | searching by topic and reading about 5% |
| brand questions | 6% | searching for the printed brand name and reading about 2%: always right |

*Example of the brand problem: "How many reviews of 'FASH Limited' are
negative?" (answer 19). The brand is printed in the text; 21 of the 1,685
reviews carry it; reading those 21 gives exactly 19.*

In short, **small answers can be found by search and large answers can be
estimated by sampling.**

**Finding 3: OOLONG has the same weaknesses.** Six OOLONG files (762 questions)
were tested the same way. 36% of OOLONG's questions are restricted to certain
users or a month, both printed on every record: searching for the user reads a
median of 0.8% of the document and gives the exact answer 99% of the time. Its
whole-document comparisons have a median gap of 38% between the two counts, so
sampling answers them. This has not been reported for OOLONG.

**Finding 4: one question type resists both.** A **close comparison**, "which
are there more of: A or B?", where both categories are frequent and their counts
are very close. Sampling cannot resolve a small difference, and there are too
many relevant records to find by search.

## 4. What was changed (version 0.8.0, built and checked, not yet published)

1. **Close comparisons added**: 174 questions, the new core of the benchmark.
   The allowed gap between the two counts is set from their size (for example 2%
   to 3.5% for counts near 300). Categories that annotators often disagree on
   ("neutral" sentiment; film ratings less than 3 stars apart) are not used.
2. **Brand questions removed** (137 questions).
3. **Every question labelled with what it measures**: *core* (close
   comparisons, 174), *retrieval* (rare-category counts, 265), *control* (the
   rest, 1,838: they show whether a model can classify the records at all, not
   whether it read everything).
4. **Scoring**: right-or-wrong for all word answers, including every core
   question; OOLONG's strict rule for rare-category counts; the lenient rule only
   for the large counts in the control group.
5. **Nothing else changed.** All 195 documents and all 2,103 remaining earlier
   questions are identical, checked one by one.

**The new questions, attacked with every shortcut** (share answered correctly;
guessing gets 0.50):

| reader | correct |
|---|---:|
| always pick the first category named | 0.54 |
| pick the one more common in the whole source dataset | 0.58 |
| read a random 5% / 25% / 50% of the document | 0.53 / 0.58 / 0.63 |
| read the 10% of records most related to the two categories | 0.64 |
| read everything, label 95% of records correctly | **0.85** |
| read everything, label 90% correctly | 0.77 |

*Example: a document of 266 news articles asks whether there are more tourism
or more celebrity-news articles; there are 41 and 44. Partial readers get it
right about 55% to 60% of the time; a reader of everything that labels 95% of
articles correctly gets it right 85% of the time.*

**Known limits of the fix.** 174 core questions give a margin of error of about
±0.07 on a model's score: enough to tell reading from skimming, not enough for
fine comparisons between similar models. They come mostly from the intent and
complaint datasets; the 3-category review datasets contribute one. On the two
paired intent datasets, where the compared categories are small, the targeted
search does better (0.73 and 0.81).

## 5. Is this ready for an A or A* venue?

**The benchmark design: yes, after this fix.** The main objection a reviewer
would raise, "a model can pass without reading the document", is now measured,
answered by the core questions, and turned into a finding about OOLONG.

**The paper: not yet.** Three things are still missing:

1. **Model results.** A benchmark paper at these venues needs several models,
   both reading the document in one prompt and working through it with code.
   This is the next step and the largest piece of work.
2. **More core questions** would help (174 is on the small side). Documents
   could be built so that two categories are deliberately close; this would take
   a few days.
3. **A check that the labels behind the core questions are reliable**, for
   example a native speaker re-labelling a sample of the compared records.

## 6. Literature update (details in `LITERATURE_REVIEW.md`)

- Three 2026 papers find that **recursion itself is not what makes RLM work**:
  a reproduction found deeper recursion harmful; Apple's SRLM states that
  "recursion itself is not the primary driver of performance"; λ-RLM beats RLM
  with a fixed set of operations. The gains come from letting the model work on
  the document through code.
- Several new code-using systems are evaluated on OOLONG, one against Claude
  Code. **All are English-only.** None checks whether its system read the whole
  document or sampled it.
- **No new benchmark covers Turkish long-context aggregation.** Two new
  multilingual long-context benchmarks (7 and 6 languages) exclude Turkish.
- The RLM authors released an 8-billion-parameter model trained to work this way
  (RLM-Qwen3-8B); it has never been tested in Turkish.

## 7. Later: training data and further releases

- **Logs of successful model runs** (the code a model writes, each sub-question
  and answer) can be checked step by step here, because the correct label of
  every record is known. That makes them useful for fine-tuning models to work
  through long Turkish documents. Two conditions: only logs that actually read
  everything count as successful, and training documents must use records never
  used in the test set.
- **More than one dataset can be published**: the benchmark, a training split
  built from separate records, the run logs, and the shortcut-testing programs
  as a reusable audit for any counting benchmark.

## 8. Next steps

1. Publish version 0.8.0 on Hugging Face (after approval).
2. First model runs, in this order: each model's accuracy on single records;
   whole documents up to about 130K tokens in one prompt; then code-using systems
   (RLM, RLM-Qwen3-8B, Claude Code), recording the code they write, in Turkish
   and English.

## 9. Decisions required

1. **Publish version 0.8.0 now**, or first add more core questions (section 5,
   item 2)?
2. **Thesis title.** Current: *Recursive Language Models for Turkish Long-Context
   Aggregation: A Matched-Twin Benchmark and a Cross-Lingual Study.* Given
   section 6, a title that does not rest on "recursive" is safer, for example
   *Do Long-Context Models Read in Turkish? A Matched Turkish-English Aggregation
   Benchmark and a Cross-Lingual Study.*
3. **Target venue.** Under the current CORE ranking (ICORE2026): ACL, EMNLP,
   NeurIPS (including its Datasets and Benchmarks track), ICLR and ICML are A*;
   NAACL and EACL are A; COLING and LREC are B. Realistic after model results:
   NAACL or EACL, with ACL, EMNLP or NeurIPS Datasets and Benchmarks as the
   stretch. Whether "Findings" papers count toward the graduation requirement
   needs checking with the institute.
