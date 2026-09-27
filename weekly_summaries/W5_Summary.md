# TR-OOLONG: Weeks 4 and 5

*28 September 2026. There was no meeting in week 4, so this summary covers
both weeks and can be read without the week 4 file.*

**How to read the two files.** `W4_Summary.md` sections 1 to 3 answer the
questions raised at the week 3 meeting (recursion depth, parallel sub-calls,
string-search exploits, where to test a model trained on this data, publishing)
and those answers still stand. Its sections 0 and 4 to 7 are replaced by this
summary: several of their claims about difficulty were tested this week and do
not hold.

## 1. Where the benchmark stands

| | at the week 3 meeting | now |
|---|---:|---:|
| datasets | 8 | 11 |
| documents | 110 | 195 |
| questions | 1,254 | 2,240 |
| question types | 10 | 9 |
| total length | 28.3M tokens | 50.7M tokens |

- **Published** on Hugging Face (16 September), with a correction on 20
  September: question numbers repeated across datasets, so combining datasets
  could silently lose 57% of questions; every question now carries a unique id.
  The published files match the local build exactly.
- **Three Turkish datasets were added**: consumer complaints (29 categories),
  news articles (16 sections, with dates) and film reviews (10-point ratings).
  They were added because a 3-category dataset cannot produce questions with
  small answers.
- **One question type was removed** (`shift`, "did X rise or fall in the second
  half"): reading 50 records at each end answers it.
- **Every answer was re-checked** by an independent computation. No record
  contains its own label.
- **Documentation rewritten** so it can be read without the code: the main
  README from 1,830 to about 370 lines, the datacard from 1,047 to about 230.
- **No AI model has been run on the benchmark yet.**

## 2. What was tested this week

The question behind every experiment: *can a question be answered without
reading the whole document?* A model with code tools has two ways to try:
**sampling** (read a small random part, scale up) and **search** (find the
relevant records by a word or a topic, read only those). Every "reader" below is
a short program, not an AI model; most are told the correct label of each
record they read, so they show what a strategy *can* achieve. Full details,
with setup and examples for each experiment: `experiments/REPORT.md`.

Two scoring rules matter. For a true answer of 30 and a reply of 25: the
**lenient** rule (`relative`, 1 minus the error as a share of the answer) gives
0.83; OOLONG's **strict** rule (`partial`, 0.75 raised to the size of the
error) gives 0.24.

### Finding 1: the difficulty grades were misleading

Each question had been graded by how well four skimming programs answered it.
259 were graded "very hard".

- **Every very-hard counting question has a small answer** (typically 10). The
  four skimmers failed because they answer 0 when their sample contains no
  match. A skimmer that answers "about 12" instead takes 145 of 226 out of the
  "very hard" grade.
  *Example: 990 complaints, "how many are about transport?", true answer 11.
  A 5% sample usually holds 0 or 1 transport complaints. Answering 12 scores
  0.91.*
- **The grades were partly luck.** Three of the four skimmers read fixed
  positions, so each got one try per question; a lucky try made 123 of the 265
  rare-category questions look easier than they are.
- **The proposed "easy minus very-hard gap shows how much a model read" does not
  work.** A guessing skimmer scored 0.48 on very-hard questions, above an honest
  reader that reads everything but mislabels one record in ten (0.41).
- An exact calculation of the **best possible skimmer** (one that also knows the
  distribution of true answers) confirmed it: under the lenient rule, skimming
  5% of the document scores 0.55 to 0.80 on every numeric question type.

### Finding 2: what each question type actually measures

| question type | share of benchmark | best shortcut found | what it measures |
|---|---:|---|---|
| counts and proportions of common categories | 51% | sampling 5%: about 0.8 | classifying records, not reading everything |
| most / least / second most common | 18% | sampling | classifying records |
| "is X more or less common than Y" | 13% | sampling 5%: 0.71 even with a weak classifier | classifying records; the two counts must differ by 15%, so sampling suffices |
| rare-category counts (answer 5 to 30) | 12% | searching by topic and reading the top 5%: 0.53 (strict rule) | finding a few records by meaning |
| brand questions | 6% | searching for the printed brand name, reading about 2%: **1.00** | retrieval, not aggregation |

*Example of the brand problem: "How many reviews of 'FASH Limited' are
negative?" (answer 19). The brand is printed as `[[FASH Limited]]`; 21 of the
1,685 reviews carry it; reading those 21 gives exactly 19.*

**The core tension:** small answers can be found by search; large answers can be
estimated by sampling. A question that truly needs the whole document needs
neither weakness.

### Finding 3: one question type resists every shortcut

**Close comparisons**: "are there more records of A or of B?" where both
categories are frequent and their counts are very close. Sampling cannot
resolve a small difference, and there are too many relevant records to find by
search. Tested on 261 such questions generated from the existing documents
(guessing gets 0.50):

| reader | correct |
|---|---:|
| skimmer reading 5% / 25% / 50% | 0.53 / 0.57 / 0.61 |
| topic search reading the top 10% | 0.61 |
| reads everything, 90% / 95% of labels right | 0.74 / 0.77 |

*Example: a document of 249 news articles, 78 about communication and 75 about
culture and arts. Skimmers get it right about half the time; every reader that
reads everything gets it right.*

The allowed difference should depend on how large the counts are (about 5% for
counts near 100, 3% near 300, 1% near 4,000). The 3-category review datasets,
weak everywhere else, become the best source of these questions because their
counts are large.

### Finding 4: OOLONG has the same weaknesses

Six OOLONG data files (762 questions) were downloaded and tested the same way.

- 36% of OOLONG's questions are restricted to certain users or a month, and
  OOLONG prints both on every record. Searching for the user reads a median of
  **0.8%** of the document and gives the exact answer **99%** of the time
  (month: 7.6% read, 99% right).
- Its whole-document comparisons have a median difference of 38% between the
  two counts, so sampling answers them.

This has not been reported for OOLONG. It turns the redesign below into an
improvement over OOLONG, not only a Turkish version of it.

## 3. Proposed redesign (decision required)

1. **Make close comparisons the central question type**, with the allowed
   difference set from the counts, using category pairs that are rarely confused
   (for example positive vs negative, not neutral vs positive).
2. **Remove the brand questions**, or report them separately as retrieval.
3. **Keep rare-category counts**, described as "find the few relevant records by
   meaning, then count", scored with the strict rule.
4. **Keep common-category counts and rankings as a control** that shows whether
   a model can classify the records at all; report them separately, never as
   evidence of reading.
5. **Remove the per-question difficulty grades**; replace them with a table per
   question type giving the strongest shortcut found.
6. **Scoring:** exact match for word answers and comparisons, the strict rule
   for small numbers, the lenient rule only for the control.

This means rebuilding the benchmark as version 0.8 and republishing. Nothing has
been changed in the published data yet.

## 4. Literature update (details in `LITERATURE_REVIEW.md`)

- Three 2026 papers find that **recursion itself is not what makes RLM work**:
  a reproduction found deeper recursion harmful; Apple's SRLM states that
  "recursion itself is not the primary driver of performance"; λ-RLM beats RLM
  with a fixed set of operations. The gains come from letting the model work on
  the document through code.
- Several new code-using systems are evaluated on OOLONG, one against Claude
  Code. **All are English-only**; no work found evaluates them in another
  language.
- **No new benchmark covers Turkish long-context aggregation.** Two new
  multilingual long-context benchmarks (7 and 6 languages) exclude Turkish.
- The RLM authors released an 8-billion-parameter model trained to work this
  way (RLM-Qwen3-8B); it has never been tested in Turkish.
- None of these papers checks whether their systems read the whole document or
  sample it. Given finding 4, that is a question this thesis can answer.

## 5. Later: training data and further releases

- **Logs of successful runs** (the code a model writes, each sub-question and
  answer) can be checked step by step here, because the correct label of every
  record is known. That makes them useful for fine-tuning models to work through
  long Turkish documents, including rewards for each correct step. Two
  conditions: only logs that actually read everything count as successful
  (otherwise the data teaches skimming), and training documents must use records
  never used in the test set.
- **More than one dataset can be published**: the benchmark, a training split
  built from separate records, the run logs, and the shortcut-testing programs
  as a reusable audit for any counting benchmark.

## 6. Next steps

1. Decide on the redesign (section 3); then rebuild, re-run every attack on the
   new questions, and republish.
2. First model runs, in this order: measure each model's accuracy on single
   records; give whole documents up to about 130K tokens in one prompt; then run
   code-using systems (RLM, RLM-Qwen3-8B, Claude Code) and record the code they
   write, to see whether they read everything or sample, in Turkish and English.

## 7. Decisions required

1. **The redesign** in section 3.
2. **Thesis title.** Current: *Recursive Language Models for Turkish Long-Context
   Aggregation: A Matched-Twin Benchmark and a Cross-Lingual Study.* Given
   section 4, a title that does not rest on "recursive" is safer, for example
   *Do Long-Context Models Read in Turkish? A Matched Turkish-English Aggregation
   Benchmark and a Cross-Lingual Study.*
3. **Target venue.** Under the current CORE ranking (ICORE2026): ACL, EMNLP,
   NeurIPS (including its Datasets and Benchmarks track), ICLR and ICML are A*;
   NAACL and EACL are A; COLING and LREC are B. Realistic after model results:
   NAACL or EACL, with ACL, EMNLP or NeurIPS Datasets and Benchmarks as the
   stretch. Whether "Findings" papers count toward the graduation requirement
   needs checking with the institute.
