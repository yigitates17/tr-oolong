# Experiment log: can TR-OOLONG be cheated, and how to stop it

Branch `explore/anti-hacking`, started 2026-09-28. Written so the results can be
explained without reading code. Each experiment says: the question, what was
done, one real example, the result, and what it means. Scripts are in this
folder; each has the same setup written at its top.

**No AI model was run in any experiment here.** Every "reader" is a short
program. Most are told the correct label of each record they look at, so they
show what is *possible* with a given reading strategy, not what a real model
does. Everything ran on a MacBook Air.

## Words used below

- **Record**: one review, complaint, article or voice command inside a document.
- **Skimmer**: a program that looks at only a small random part of the
  document (here 5% of the records) and answers from that.
- **Honest reader**: a program that looks at every record.
- **Scores**, for a numeric question with true answer 30 and a reply of 25:
  - `exact`: 1 if the reply is exactly right, else 0. Here 0.
  - `partial` (OOLONG's rule): 0.75 multiplied by itself once per unit of
    error. Here 0.75^5 = 0.24. Harsh: each unit of error costs about 25%.
  - `relative` (added in TR-OOLONG for big answers): 1 minus error divided by
    the true answer. Here 1 - 5/30 = 0.83. Lenient.

---

## Experiment 1: a skimmer that guesses small numbers

**Question.** The published difficulty grades call 259 questions "very hard"
because four skimmers failed on them. Is that because the questions need the
whole document, or because of how those four skimmers were written?

**What was done.** The four original skimmers read 5% of the records and scale
their count up by 20. If they see no matching record, they answer 0. A fifth
skimmer was written that does the same, except that when it sees 0 or 1
matching records it answers "12" instead. 12 was chosen before running, as the
middle of the published range for rare categories (5 to 30). Each question was
run 200 times with different random samples, and the scores averaged.

**Example.** A document of 990 consumer complaints asks how many are about
transport. True answer: 11. A 5% sample is about 50 complaints and usually
holds 0 or 1 transport complaints, so the original skimmers answer 0 or 20 and
score about 0.2; the question is graded very hard. The new skimmer answers 12
and averages 0.81.

**Result.** 145 of the 226 very-hard counting questions (64%) stop being very
hard. With a guess of 8 instead of 12, 198 (88%) do.

**What it means.** Every very-hard counting question has a small answer (24 or
less). The four skimmers failed on them because they answer 0 when they see
nothing, not because the questions need the whole document.

## Experiment 2: does the easy vs very-hard gap show how much a model read?

**Question.** Week 4 proposed judging a model by the gap between its score on
easy questions and on very-hard ones: a large gap would mean it skimmed. Does
that work?

**What was done.** Three readers were scored on every question, 24 runs each:
the guessing skimmer from experiment 1, and two honest readers that look at
every record but give each one the right label only 90% or 95% of the time
(when wrong, they pick another label at random).

**Result** (`relative` score):

| reader | easy questions | very-hard questions |
|---|---:|---:|
| guessing skimmer (reads 5%) | 0.77 | 0.48 |
| honest reader, 90% right | 0.85 | 0.41 |
| honest reader, 95% right | 0.91 | 0.58 |

**Example.** A one-million-token document of 9,847 complaints asks how many
are about tourism; true answer 18. The honest reader that is wrong one time in
ten makes about 985 mistakes; spread over 28 other categories, about 35 land in
"tourism", so it answers 45 to 61 and scores 0. The guessing skimmer often
answers 12 and scores 0.67.

**What it means.** The skimmer beats the 90% honest reader on very-hard
questions and shows a smaller gap. The gap cannot be read as "how much was
read". That proposal is withdrawn.

## Experiment 3: the best score any skimmer can get

**Question.** Experiments 1 and 2 used one clever skimmer. A reviewer can
always invent a cleverer one. What is the most any skimmer can score?

**What was done.** For every numeric question (1,500 of them) a program works
out, exactly, what the best possible 5% skimmer would score on average. That
skimmer counts the records in its sample like the others, and is additionally
handed the full list of true answers of all similar questions (same dataset,
same question type, same document length). It then picks the reply with the
best expected score. No real model could know that list, so no skimming
strategy can beat this on average: it is a ceiling. The calculation covers
every possible sample, so there is no randomness in the result.

A first version gave the skimmer only a blurred version of that list. The
simple "guess 12" skimmer beat it, which showed it was not a real ceiling, so
it was replaced.

**Result** (5% of records read, average over each question type):

| question type | questions | `relative` | `partial` | `exact` |
|---|---:|---:|---:|---:|
| ordinary counts (answers in the hundreds or thousands) | 656 | 0.78 | 0.22 | 0.10 |
| rare-category counts (answers 5 to 30) | 265 | 0.55 | 0.36 | 0.16 |
| brand counts | 87 | 0.71 | 0.45 | 0.28 |
| proportions | 492 | 0.80 | 0.59 | 0.39 |

For comparison, on counting questions with answers of 30 or fewer, honest
readers score under `partial`: 0.80 if right 99% of the time, 0.49 at 95%,
0.34 at 90%.

**What it means.**

- Under the lenient `relative` score, skimming gets 0.55 to 0.80 on every
  question type. That score cannot separate reading from skimming anywhere.
- Under `partial`, large counts are hopeless for skimmers (0.22), but they are
  also nearly hopeless for honest readers, because one wrong label in a
  thousand-record count already costs points. Large counts under `partial`
  measure nothing.
- On rare counts under `partial`, an honest reader beats the ceiling only if it
  labels about 95% or more of records correctly. Rare counts therefore test
  *very accurate* complete reading, not reading alone.
- A per-question grade is not meaningful for small answers: on any single
  question, some lucky fixed guess is right. Only averages over many questions
  can be compared against a ceiling.

The next experiment replaces the "90% right with random mistakes" reader with a
real text classifier, because how mistakes are distributed decides how much
they hurt rare counts.

## Experiment 4: a realistic reader that reads everything

**Question.** Experiments 2 and 3 used readers whose mistakes land on random
labels. A real classifier confuses *similar* labels. What does a realistic
reader score, and does reading more of the document help it?

**What was done.** A simple word-count classifier (Naive Bayes) was trained for
each dataset. Every record was labelled by a copy of the classifier that had
never seen that record (the records were split into 5 parts; each part was
labelled by a model trained on the other 4). The classifier then answered every
question three times: from a random 5% of the records, from 25%, and from all
of them (20 random samples each for 5% and 25%). A second version corrects its
counts for its own known error rates ("adjusted classify and count", a standard
method for estimating counts with an imperfect classifier).

Records labelled correctly by this classifier: 28% (`sinema_tr`), 53%
(`interpress_tr`), 63% to 77% elsewhere. A good language model should do much
better; this is a weak reader on purpose.

**Result** (`relative` score; same classifier, reading more of the document):

| question type | 5% | 25% | 100% | 100%, corrected |
|---|---:|---:|---:|---:|
| brand counts | 0.28 | 0.59 | 0.75 | 0.75 |
| brand "which has most" | 0.31 | 0.46 | 0.67 | 0.67 |
| brand "which of two" | 0.66 | 0.78 | 0.91 | 0.91 |
| rare-category counts | 0.14 | 0.33 | 0.38 | 0.43 |
| most / least / second most common | 0.52 to 0.73 | 0.58 to 0.79 | 0.63 to 0.83 | same |
| ordinary counts | 0.50 | 0.56 | 0.58 | 0.69 |
| proportions | 0.50 | 0.55 | 0.57 | 0.67 |
| "is X more or less common than Y" | 0.71 | 0.74 | 0.74 | 0.74 |

**Example.** "How many reviews of 'Supradyn' are neutral?" (true answer 10).
Reading 5% of the document, the classifier scores 0.0 on average: it rarely
meets a Supradyn review. Reading everything, it answers 9 and scores 0.90.

**What it means.**

- A realistic reader that reads everything scores *below* the 5% skimmer of
  experiment 3 on every numeric question type. With these scores, labelling
  mistakes cost more than skipping 95% of the document.
- Holding the classifier fixed, reading more helps a lot on brand questions and
  rare counts, somewhat on ranking questions, and almost not at all on "is X
  more or less common than Y" (0.71 to 0.74). That question type (292
  questions, 13% of the benchmark) is answered as well from 5% as from
  everything, because the builder only asks it when the two counts differ by at
  least 15%.

## Experiment 5: finding the relevant records by search

**Question.** Brand questions and rare counts reward reading in experiment 4,
but only against a *random* sample. A model with code can search instead. Can
it find the few records that matter and skip the rest?

**What was done.** Two attacks, both told the true label of what they read:

- *Brand search*: the brand is printed in the text as `[[Brand]]`. For brand
  questions, read only the records carrying a brand named in the question.
- *Topic search*: for count questions, rank every record by how likely it is
  to belong to the asked category (using the classifier's word statistics from
  experiment 4, standing in for a good keyword or meaning-based search), read
  only the top 2%, 5% or 10%, and assume the rest contain none.

**Result.**

| question type | attack | share of document read | `relative` | `partial` | `exact` |
|---|---|---:|---:|---:|---:|
| brand counts (87) | brand search | 1.9% | 1.00 | 1.00 | 1.00 |
| brand "which has most" (15) | brand search | 1.6% | 1.00 | 1.00 | 1.00 |
| brand "which of two" (35) | brand search | 3.0% | 1.00 | 1.00 | 1.00 |
| rare-category counts (265) | topic search | 5% | 0.73 | 0.53 | 0.20 |
| rare-category counts | topic search | 10% | 0.79 | 0.61 | 0.29 |
| ordinary counts (656) | topic search | 10% | 0.51 | 0.13 | 0.04 |

**Example.** "How many reviews about the brand 'FASH Limited' are labeled
negative?" (true answer 19). The document has 1,685 reviews; 21 carry
`[[FASH Limited]]`. Reading those 21 gives exactly 19.

**What it means.**

- **Brand questions are retrieval, not aggregation.** Searching for the printed
  brand and reading about 2% of the document answers every one of them
  perfectly. OOLONG's questions narrowed to one user or one date have the same
  property (checked in a later experiment).
- **Rare counts are mostly retrieval too.** A good topic search reading 5% of
  the document beats both the best random skimmer (0.36 under `partial`) and
  the realistic full reader (0.25).
- Together with experiments 1 to 3 this gives the core tension: **small answers
  can be found by search; large answers can be estimated by sampling.** A
  question that truly needs the whole document must have neither weakness.

## Experiment 6: close comparisons between two frequent categories

**Question.** Is there a question type that neither sampling nor search can
answer? Sampling fails when the answer depends on a small difference; search
fails when the relevant records are too many to pick out. A comparison of two
*frequent* categories whose counts are *very close* has both properties.

**What was done.** No new documents were built. From the existing documents,
261 questions were generated of the form "are there more records labelled A or
labelled B?", where both categories are frequent (at least 30 records and 2% of
the document) and their counts differ by 0.5% to 5%. Readers: random skimmers
reading 5%, 25% and 50% (40 random samples each, true labels); topic search
reading the top 10% most relevant records; full readers right 95% or 90% of the
time; and the realistic classifier from experiment 4, raw and corrected.

**Result** (share answered correctly; guessing gets 0.50):

| reader | correct |
|---|---:|
| skimmer, 5% | 0.53 |
| skimmer, 25% | 0.57 |
| skimmer, 50% | 0.61 |
| topic search, top 10% | 0.61 |
| full reader, 95% right | 0.77 |
| full reader, 90% right | 0.74 |
| realistic classifier, full | 0.58 |

A follow-up calculation checked how large the gap between the two counts
should be. The right gap depends on the counts:

| typical document | each count about | gap | skimmer reading 50% | full reader, 95% right |
|---|---:|---:|---:|---:|
| intent set, 3,000 records | 100 | 5% | 0.65 | 0.90 |
| complaints, 2,500 records | 300 | 3% | 0.65 | 0.88 |
| 3-label review set, 12,000 records | 4,000 | 1% | 0.66 | 0.84 |

**Example.** A news document of 249 articles: 78 are `iletisim`
(communication) and 75 `kultursanat` (culture and arts). Skimmers reading 5%,
25% or 50% answer correctly about half the time. Topic search gets it wrong.
Every full reader, including the weak classifier, gets it right.

**What it means.**

- This is the only question type found where **no shortcut gets much above
  guessing** and **reading everything accurately clearly wins.**
- The existing "is X more or less common than Y" questions are the same kind of
  question but require a gap of at least 15%, which is why sampling answers
  them. Making the gap small, and setting it from the size of the counts,
  turns the weakest question type into the strongest.
- The 3-label review sets, weak everywhere else, are the best hosts, because
  their counts are large.
- Caution: when the two counts are very close, how the original annotators
  labelled borderline records can decide the answer. Pairs should be chosen from
  categories that are rarely confused with each other (for example positive vs
  negative, not neutral vs positive, and not 7 vs 8 stars).

## Experiment 7: the same attacks on OOLONG

**Question.** Do these weaknesses belong to TR-OOLONG alone, or also to OOLONG,
the benchmark it follows?

**What was done.** Six OOLONG data files (762 questions, contexts 8K to 4M
tokens) were downloaded. OOLONG prints a user id and a date on every record
("Date: Aug 05, 2024 || User: 44106 || ..."). For questions restricted to some
users or one month, the program read only the records whose printed user or
month matches, with their true labels, and checked whether that gives the
correct answer. For OOLONG's "which label is more frequent" questions over the
whole document, it measured how close the two counts are. It also counted how
many earlier cross-checked questions (3,553 across all 41 OOLONG files) are
restricted in this way.

**Result.**

- 36% of OOLONG's questions are restricted to listed users or a month.
- User-restricted: searching for the user ids reads a median of **0.8%** of the
  records, and those records alone give the exact answer **99%** of the time.
- Month-restricted: searching for the month reads a median of **7.6%**, and
  gives the exact answer 99% of the time.
- Whole-document comparisons: the two counts differ by a median of **38%**;
  only 6% are within 5%. A 5% random skimmer already scores 0.56 on OOLONG's
  whole-document questions under OOLONG's own scoring (earlier cross-check).

**Example.** A 131K-token document with 1,772 records asks: "among instances
associated with user 41076, which label is most common?" Fifteen records carry
that user id. Reading those fifteen gives the correct answer.

**What it means.** OOLONG makes its answers small by restricting questions to a
user or a date, and both are printed in the text, so a model with code can find
the relevant records by plain string search. Its whole-document questions have
large gaps and large answers, so sampling works on them. **OOLONG has both
weaknesses found in TR-OOLONG.** This has not been reported before, and it
makes a TR-OOLONG built around close comparisons a real improvement over
OOLONG, not only a Turkish version of it.

---

## Summary of what each question type measures

| question type | questions now | best shortcut | verdict |
|---|---:|---|---|
| ordinary counts, proportions | 1,148 | sampling (0.78 to 0.80 under `relative`) | measures classification, not reading. Keep as a clearly labelled control, or reduce |
| "is X more or less common than Y" (gap at least 15%) | 292 | sampling at 5% (0.71 even with a weak classifier) | weak as built. Replace with close comparisons |
| most / least / second most common | 398 | sampling | measures classification; control |
| rare-category counts | 265 | topic search of 5% (0.53 under `partial`) | mostly finding a few records by meaning. Keep only if described as that |
| brand questions | 137 | string search of about 2% (1.00) | retrieval, not aggregation. Remove, or describe as retrieval |
| **close comparisons (proposed)** | **0 (261 simulated)** | **sampling 50% or search 10%: 0.61** | **the only type that needs the whole document** |

## Recommendations (decisions for the thesis owner and advisor)

1. **Add close comparisons as the central question type**, with the allowed gap
   set from the size of the two counts (so that a 50% skimmer stays near 0.65),
   restricted to category pairs that are rarely confused. Ask them as "which of
   these is more common" with two, and possibly three or four, categories to
   lower the chance of guessing right.
2. **Drop the brand questions**, or report them separately as retrieval. They
   are answered perfectly by string search.
3. **Keep rare-category counts but describe them honestly**: "find the few
   records about X by meaning, then count", scored with `partial`.
4. **Keep large counts, proportions and most/least common as a control** that
   shows whether a model can classify the records at all. Report it separately,
   never as evidence that a model read the document.
5. **Remove the per-question difficulty grades.** Experiments 1 to 3 show they
   depend on which skimmers were chosen and are partly luck. Replace them with
   the per-type table above, which uses the strongest attack found for each
   type.
6. **Use `exact` for word answers and comparisons, `partial` for small numbers,
   `relative` only for the large-count control.**
7. **Contamination** (not tested, no models were run): every record comes from a
   public dataset, so a model that has memorised a dataset's labels could label
   records without understanding them. This applies equally to OOLONG. State it
   as a limitation.

---

## Ideas: training data from successful runs, and more than one dataset

Not experiments, only proposals, based on the findings above.

### Logs of successful runs ("trajectories")

When a code-using model (RLM, Claude Code, others) answers a question, its log
holds the code it wrote, every sub-question it sent to a smaller model, each
answer it got back, and its final answer. TR-OOLONG knows the correct label of
every record, so **every step of such a log can be checked**, not only the final
answer. That is unusual and is the main value.

What it could be used for:

1. **Fine-tuning models to work through long Turkish documents** (post-training).
   The RLM authors did this in English with a Qwen3-8B model and report a 28%
   gain; Kim & Ahmad and Gandhi et al. (2026) did it with reinforcement
   learning. A Turkish set of checked logs would be new.
2. **Rewards for each step, not only the end.** Because each sub-answer can be
   checked, a training method can reward correct intermediate steps, which is
   more informative than rewarding only the final number.
3. **Turkish pretraining: little value.** The record texts already come from
   public corpora, and the logs add mostly code and short answers.

Two cautions, both from the findings above:

- **A correct final answer does not mean a good log.** On the control questions a
  model that skimmed 5% is often right. Only logs that read every record (which
  the log itself shows) and answered close comparisons correctly should count as
  successful. Otherwise the training data teaches skimming.
- **Training and test records must not overlap.** Documents built from the same
  pool share 20 to 39% of their records. Training logs need their own documents
  built from records never used in the test set. The builder does not support
  that split yet.

Closest existing work: π² (arXiv:2604.05114), which fine-tunes on checked
solution traces for English long-context reasoning and reports gains of about 3
to 4%. Expect gains of that order, not 28%.

### Publishing more than one dataset

Yes. Natural separate releases, each on Hugging Face with its own card:

| release | what it is | when |
|---|---|---|
| TR-OOLONG (test) | the benchmark itself | now; v0.8 after the redesign |
| TR-OOLONG-train | same pipeline on a separate record pool, with per-record labels, for training | when the builder supports the split |
| TR-OOLONG trajectories | checked logs of model runs | after the model experiments |
| shortcut audit | the attack programs from this report, usable on any counting benchmark (OOLONG included) | can go with the benchmark paper |

One paper can present the benchmark with its training split and the audit (a
datasets-and-benchmarks paper). The trajectories fit better with the model
study, as a second paper or a thesis chapter.
