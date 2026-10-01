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
| **close comparisons (v0.8.0 and v0.9.0)** | **418 built (174 + 244; 261 simulated first)** | **sampling 50% or search 10%: 0.61** | **the only type that needs the whole document** |

## Recommendations (decisions for the thesis owner and advisor)

*Status, 28 September: recommendations 1 to 6 were carried out in version
0.8.0 (see experiment 8). Recommendation 7 remains a stated limitation.*

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

---

## Experiment 8: the fix, as actually built (v0.8.0)

**What was changed** (branch `explore/anti-hacking`, version 0.8.0):

- **New question type, "close comparison"**: *"Which are there more of in these
  records: records labelled A or records labelled B?"* Asked only when both
  categories are frequent (at least 30 records and 2% of the document) and their
  counts are close, with the allowed gap set from the size of the counts
  (between 0.35 and 0.60 divided by the square root of the smaller count; for
  example 2% to 3.5% for counts near 300). Categories that annotators often
  disagree on are excluded ("neutral" sentiment; film ratings less than 3 stars
  apart). Which label is named first is random. The answer is a label, scored
  right or wrong.
- **Brand questions removed** (137 questions, from `vitamins_tr` and
  `amazon_hpc_en`).
- **Every question gets a role**: `core` (close comparisons), `retrieval`
  (rare-category counts), `control` (everything else).
- **Per-question difficulty grades are no longer released.**
- **Nothing else changed.** The 195 documents are byte-identical to v0.7.1, and
  every one of the 2,103 remaining earlier questions has the same text, answer
  and id. This was checked question by question after the rebuild.

**Result of the rebuild.** 2,277 questions: 174 core, 265 retrieval, 1,838
control. Close comparisons come mostly from the intent sets (129) and complaints
(33); the 3-category review sets almost never contain two close categories once
"neutral" is excluded (1 question in total). The Turkish and English paired
intent sets received the identical 35 close comparisons, with identical
answers.

**The attacks, on the 174 built close comparisons** (share answered correctly;
guessing gets 0.50):

| reader | correct |
|---|---:|
| always pick the first-named label | 0.54 |
| pick whichever is more common in the whole source corpus | 0.58 |
| skimmer reading 5% / 25% / 50% | 0.53 / 0.58 / 0.63 |
| topic search reading the top 10% | 0.64 |
| reads everything, 95% of labels right | **0.85** |
| reads everything, 90% of labels right | 0.77 |
| reads everything, weak word-count classifier | 0.57 |

**Example.** A news document of 266 articles: *"Bu kayıtlarda hangisi daha
çok: 'turizm' etiketli kayıtlar mı, 'magazin' etiketli kayıtlar mı?"* There are
41 tourism and 44 celebrity-news articles; the answer is *magazin*. Skimmers get
it right about 55% to 60% of the time and topic search gets it wrong; a reader
that reads everything and labels 95% of articles correctly gets it right 85% of
the time.

**What it means.**

- The fix works: the best shortcut found reaches 0.64, while reading everything
  accurately reaches 0.85.
- **Limitation 1.** On the two paired intent sets, topic search does better
  (0.73 Turkish, 0.81 English): the two categories there hold only about 60
  records each, so a good search can find most of them in 10% of the document.
  Those questions sit between "core" and "retrieval".
- **Limitation 2.** 174 questions answered right or wrong give a margin of error
  of about ±0.07 on a model's core score. Enough to separate a reader from a
  skimmer (0.85 against 0.64), not enough for fine comparisons between similar
  models.
- **Standard release checks** (run after the rebuild, all pass): searching for
  label names gets 0.42 to 0.65 per dataset on close comparisons, and guessing
  from record length and punctuation stays near a coin flip. Answering from the
  source dataset's overall shares gets 0.52 to 0.68 per dataset, highest on
  `en_intent` (0.68 on 28 questions, borderline significant). The intent
  documents are built with label mixes close to the whole corpus, which likely
  explains it; it is disclosed rather than fixed.
- **Limitation 3.** Close comparisons reward models that label records very
  accurately; a weak classifier fails them even when it reads everything. This is
  intended: the question measures careful reading of everything.

---

## Experiment 9: core documents (v0.9.0)

**Question.** Version 0.8.0 had only 174 core questions. Almost none came from
the Turkish/English review pairs, and on the paired intent sets a targeted topic
search did well (0.74 to 0.79), because the compared categories were small.
Can we get more core questions, in both languages, with large categories?

**What was done.** New documents were added to nine datasets, built from exact
label counts instead of a random mix. In each, one or two pairs of labels get a
fixed share of the document with counts inside the close-comparison window, and
the other labels share the rest:

| datasets | documents added | designed pair(s) |
|---|---|---|
| paired intent, Turkish and English | 10 of 3,000 records (identical in both languages) | 2 pairs of intents, about 210 records each |
| `musteri_tr` / `marc_en`, `vitamins_tr` / `amazon_hpc_en` | 18 each: 6 at 2,500, 6,000 and 12,000 records | positive vs negative, about 40% each |
| `sikayet_tr`, `sinema_tr` | 24 each, up to about 1M tokens | 2 pairs, 15% each (film ratings at least 3 stars apart) |
| `interpress_tr` | 18, up to about 1M tokens | 2 pairs, 15% each |

The two configs of each Turkish/English pair share their random draws. So the
paired intent documents contain the same utterances, and each review pair's
documents have identical sizes and identical positive/negative counts. Every
core question on them is the same question, with the same answer, in both
languages. Only the designed pairs are asked, the two counts differ by at least
5 records, and two things are balanced by design (experiment 10 explains why):
which label is larger, and whether the answer is named first.

**Result of the build.** 158 documents and 244 core questions added. All 195
earlier documents and all 2,277 earlier questions are byte-identical, checked
one by one. Totals: 353 documents, 2,521 questions, 418 core, 106.4M tokens.
**91 core questions are identical across the two languages** (55 intent, 18
per review pair).

**The attacks, on the 244 new core questions** (guessing 0.50):

| reader | correct |
|---|---:|
| always the first-named label | 0.50 |
| more common in the whole source dataset | 0.49 |
| skimmer reading 50% | 0.64 |
| topic search, top 10% of records | 0.49 |
| reads everything, 95% right | **0.85** |
| reads everything, 90% right | 0.76 |

**Example.** A 2,500-review English health-products document has 1,000
negative and 986 positive reviews: *"Which are there more of in these records:
records labeled 'negative' or records labeled 'positive'?"*, answer *negative*.
The Turkish supplement-review document built alongside it has the same counts
of *olumsuz* and *olumlu* reviews and asks the same question in Turkish, with
the answer *olumsuz*.

**What it means.** The core set is large enough for a margin of error of about
±0.05, the Turkish/English comparison rests on 91 identical core questions from
three different corpora, and on the new questions every shortcut tried stays at
or near a coin flip except reading half of the document (0.64).

## Experiment 10: a full audit, question by question of a reviewer

**Question.** Each earlier round found a new problem because only one part was
examined at a time. What does a systematic pass over every angle of attack
find?

**What was done.** Every way a reviewer could attack the core questions was
listed, and each was checked on the built data. The first pass (on a draft of
v0.9.0) found three problems, which were fixed and the data rebuilt; the table
shows the final state.

| angle of attack | how it was checked | result |
|---|---|---|
| answers wrong | every answer recomputed by independent code | all match |
| label written in the text | search of every shipped record | none |
| sampling | random readers of 5%, 25%, 50% | at most 0.64 |
| search | read the 10% of records most related to the two labels | 0.56 overall, 0.49 on core documents |
| source-dataset shares | pick the label more common in the source | 0.54 overall, 0.49 on core documents (0.61 on the older 174) |
| answer position | always pick the first-named label | 0.52 overall, 0.50 on core documents |
| record length and punctuation | standard style check | see release checks |
| repeated records in a document | exact duplicate search | none |
| documents sharing records | overlap between documents of one size | at most 22% (use clustered errors) |
| gap decided by a few wrong labels | smallest gap between the two counts | core documents: at least 5 records; 12 older questions have 3 or fewer |
| hard questions only on short documents | document length of core questions | 210 up to 100K tokens, 79 to 300K, 77 to 600K, 52 above |
| Turkish and English documents differ in length | tokens per matched pair | intent: Turkish 1.31-1.34x longer; reviews: Turkish 0.62-0.86x (shorter) |
| wrong source labels | native-speaker check | prepared (200 Turkish records), not yet done |
| memorised labels | cannot test without models | a model still has to go through every record and count |

**The three problems the first pass found, and the fixes.**

1. *Gaps of 1 to 3 records* in 14 new questions. Source labels are 3% to 9%
   wrong, so such a gap is decided by label noise. Fix: core documents now
   require a gap of at least 5 records.
2. *Core questions mostly on short documents* (28 above 600K tokens). Fix: core
   documents of about 1M tokens for complaints and films (now 52 above 600K).
3. *"Pick the label rarer in the source dataset" scored 0.70 on the intent
   core documents.* Which label came out larger had been a coin toss, and with
   few questions the tosses lined up against the source shares. Fix: only the
   designed pairs are asked, and which label is larger alternates by design
   (now 0.49).

**What it means.** On the core-document questions, no angle found gives more
than reading half the document (0.64). The older 174 core questions from v0.8.0
keep a mild exposure to source-dataset shares (0.61) and are reported as a
separate group. The remaining open item is the label check, which sets how far
below 1.0 even a perfect model scores.

## Experiment 11: cleaning the data, and which label pairs can be told apart (v0.10.0)

**How it started.** During the native-speaker label check (30 September), three
problems were spotted in the records themselves.

**Problem 1: records that are not content.** 1.9% of news records in the
documents were a newspaper's masthead (publisher, editors, printing house), not
an article. *Example:* "İMTİYAZ SAHİBİ Ayşe OĞUZ YAZI İŞLERİ MÜDÜRÜ Hüseyin OĞUZ
YÖNETİM YERİ ... KARAMAN". **Fix:** a record is dropped if it contains 3 or more
masthead job titles, or 2 together with an issue header ("Yıl: 3 Sayı: 1531").
Checked by hand on samples at each threshold: at 3 every sample was a masthead;
at 2 some real articles appeared, hence the extra condition. Removed 4,133 news
records (2.1%).

**Problem 2: reviews that write their score.** On a rating-based label the
score written in the text is the label itself, and the label-name filter cannot
see it. *Examples:* "ben 6/10 veriyorum", "80/100", "1 yıldız veriyorum", "I give
this a solid 4-stars". Share of reviews: film 11.2%, MARC 2.9%, Amazon 2.5%,
shopping 1.3%, supplements 0.8%. **Fix:** such reviews are dropped (6,129 film,
3,570 MARC, 1,488 Amazon, 639 shopping, 449 supplement).

**Problem 3: web formatting.** 12.7% of Amazon reviews carried HTML such as
"<br />". **Fix:** tags are replaced by a space and entities unescaped.

**Problem 4: labels that cannot be inferred from the text.** A complaint about
a cancelled order with no product named, filed under "mobilya ve ev tekstili",
cannot be classified by anyone. The question is whether whole categories are
like that.

**What was done for problem 4.** A word-count classifier was trained on each
dataset (5-fold, out-of-fold). For every pair of labels, only records of those
two labels were taken, and the classifier chose the more likely of the two. The
share it got right is the pair's *separability*
(`experiments/label_separability.py`).

**Result.**

| dataset | label pairs | separable at 0.8 or more | weakest pairs |
|---|---:|---:|---|
| complaints | 406 | all | clothing vs internet 0.80; furniture vs shopping 0.85 |
| intent (all four sets) | 1,128 | all | general_quirky vs qa_factoid 0.83 |
| news | 120 | 108 | aktuel vs siyasi 0.69, bilisim vs teknoloji 0.71, ekonomi vs ticaret 0.75 |
| film ratings | 45 | 20 | 5 vs 6 stars 0.59, 7 vs 8 stars 0.61 |
| 3-label reviews | 3 each | positive vs negative only | neutral vs negative 0.69-0.79 |

So the complaint set as a whole is fine: individual records can be
unguessable, but any two categories are told apart at 0.80 or more. The weak
spots are overlapping news sections, neighbouring star ratings, and "neutral".

**A second condition, found the same night.** Pair separability looks only at
records of A and B. But a close comparison counts A and B inside a document that
also holds every other label, so each of them must also be recognised among
*all* labels. *Example:* "more 2-star or more 8-star film reviews?" passed the
pair test (2 vs 8 is easy), yet counting reviews that are *exactly* 2 stars
means telling 2 from 1 and 3, which nobody can do from text ("loved it" can be a
7 or a 10). So a label must also be identifiable on its own: the classifier
finds at least 60% of its records with all labels competing.

| dataset | labels identifiable on their own | allowed pairs |
|---|---|---:|
| intent (each set) | 32 of 48 | 496 of 1,128 |
| complaints | 23 of 29 (not: shopping, personal care, internet, real estate, computers, furniture) | 253 of 406 |
| news | 5 of 16 (health, technology, celebrity, food, sport) | 10 of 120 |
| 3-label reviews, film sentiment | positive and negative (not neutral) | positive vs negative |

The classifier is weak (about 300 examples per intent, for instance), so these
lists are cautious: some excluded labels would be fine for a strong model.

**Film ratings become film sentiment.** Every question on the film set depended
on exact star ratings, which cannot be read from text. The set now uses the
reviewer's rating mapped to sentiment (1-4 negative, 5-6 neutral, 7-10 positive).
Positive vs negative separate at 0.88 and are identifiable (0.87 and 0.61). The
set keeps its shareable text and gains core documents like the other review
sets, but it no longer has 10 labels, so it loses its rare-category counts.

**Fix.** Close comparisons (both kinds of documents) only use pairs that pass
both conditions (`close_allowed_pairs_file` in each config, written by
`experiments/label_separability.py`).

**Result of the rebuild (v0.10.0).** 347 documents, 2,362 questions, 309 core
(217 Turkish, 92 English), 77 core questions identical across languages, 102.5M
tokens. The intent and complaint datasets' non-core questions are unchanged
(780 of 780, checked one by one). No written scores or web formatting remain in
the shipped records; about 3 masthead records remain in the news set (OCR
variants the filter misses).

| on the core questions | all 309 | 214 from core documents |
|---|---:|---:|
| always the first-named label | 0.51 | 0.50 |
| more common in the source dataset | 0.53 | 0.50 |
| skimmer reading 5% / 25% / 50% | 0.53 / 0.58 / 0.62 | 0.53 / 0.57 / 0.62 |
| topic search, top 10% | 0.54 | 0.49 |
| reads everything, 95% / 90% right | 0.86 / 0.76 | 0.85 / 0.76 |

The 95 core questions from ordinary documents remain mildly exposed (source
shares 0.62, topic search 0.67) and are reported as a separate group.

**Remaining.** The native-speaker check measures the share of wrong or
unguessable labels within the allowed pairs; that sets how far below 1.0 even a
perfect model scores.
