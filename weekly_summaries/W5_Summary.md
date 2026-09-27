# TR-OOLONG: Week 5

*28 September 2026. Covers a full review of the published benchmark, two new
experiments on the difficulty grades, a literature update, and the plan for
the first model runs.*

## 1. Where the benchmark stands

- **Published and correct.** The Hugging Face release matches the local build
  file for file, including the 20 September fix to question numbering.
- **Every answer re-checked.** All 2,240 answers were recomputed by an
  independent route and matched. No shipped record contains its own label.
  The build still reproduces byte for byte.
- **Documentation rewritten.** The README went from 1,830 lines to about 280,
  and the datacard from 1,047 to about 230. Two published statements were
  wrong and are corrected: the card said the removed `shift` questions were
  still in the data (they are not), and it said 100 of the 120 paired
  questions share an answer (all 120 do).
- **No model has been run yet.** Everything below comes from simulated
  readers: short programs that are told the true label of each record they
  read.

## 2. Finding: the difficulty grades overstate how many questions resist skimming

### Background

Each question carries a grade (very hard, hard, moderate, easy), set by how
well four "skimming" programs answer it after reading 5% of the records. 259
questions are graded very hard. Week 4 proposed reading a model's score on the
easy questions against its score on the very-hard ones, as a measure of how
much of the document it read.

### What was found

**Every very-hard counting question has a small answer** (24 records or fewer,
typically 10). The four skimmers fail on them for one reason: when their 5%
sample contains no matching record, they answer 0, and 0 always scores
nothing.

**Experiment 1: a skimmer that guesses small.** Same 5% sample, one change: if
it sees 0 or 1 matching records, it answers "about 12" instead of 0. The value
12 was fixed in advance as the middle of the published rare range (5 to 30),
not tuned. Each question was run 200 times with different samples.

| guess used | very-hard counting questions that stop being very hard |
|---|---:|
| 8 | 198 of 226 (88%) |
| 12 (chosen in advance) | 145 of 226 (64%) |
| 20 | 39 of 226 (17%) |

*Example.* A document of 990 consumer complaints; the question asks how many
are about transport. The true answer is 11. A 5% sample holds about 50
complaints, so it usually contains 0 or 1 transport complaints. Scaling up
gives 0 or 20, which scores about 0.2: graded very hard. Answering 12 scores
0.9 on that question. Averaged over samples, the guessing skimmer scores 0.81.

**Experiment 2: can the easy/very-hard gap tell a skimmer from an honest
reader?** Three kinds of reader were run on every question: the guessing
skimmer above, and "honest" readers that open every record but label each one
correctly only 90% or 95% of the time.

| reader | easy questions | very-hard questions |
|---|---:|---:|
| guessing skimmer (reads 5%) | 0.77 | 0.48 |
| honest reader, 90% accurate | 0.85 | 0.41 |
| honest reader, 95% accurate | 0.91 | 0.58 |

The skimmer scores higher than the 90%-accurate honest reader on the very-hard
questions, and shows a *smaller* gap. So the gap does not measure how much
was read, and the week 4 recommendation to report it that way is withdrawn.

*Example.* A one-million-token document of 9,847 complaints; the question asks
how many are about tourism. The true answer is 18. The honest reader that is
wrong one time in ten makes about 985 mistakes, spread over 28 other
categories, so roughly 35 wrong records land in "tourism" and it answers
45 to 61: score 0. The guessing skimmer often answers 12: score 0.67.

**A second weakness in the grades.** Three of the four skimmers read fixed
positions (the start, both ends, evenly spaced), so each gets one draw. On a
small answer, one draw can land close by luck. The tourism question above is
graded *easy* for that reason. Of 265 rare-category counts, 123 are graded
above very hard by one of these fixed readers, and for 44 of them the random
skimmer's average says very hard.

### Why it happens

Small answers resist sampling, and that part holds. But the grading and the
scoring rule (partial credit in proportion to the error) reward any answer of
roughly the right size, and the grade depends on single lucky draws. The
problem is in how questions are graded and scored, not in the data or the
answers.

### Proposed fix (decision required)

On the 420 counting questions with answers of 30 or fewer, OOLONG's own
scoring rule, which gives little credit for being off, separates the readers
properly:

| reader | OOLONG's rule | current rule |
|---|---:|---:|
| guessing skimmer | 0.27 | 0.51 |
| honest, 90% accurate | 0.34 | 0.56 |
| honest, 95% accurate | 0.49 | 0.71 |
| honest, 99% accurate | 0.80 | 0.92 |

**Proposal:** define the hard subset by a simple rule, "the answer is 30
records or fewer", instead of by the skimmer grades, and score that subset with
OOLONG's rule. Keep the current grades in the release as a description only.
This changes no question or answer, only which file defines the hard subset and
how it is scored. To tell "did not read" apart from "read but misjudged", the
model runs should also measure each model's accuracy on single records
directly.

## 3. Literature update (details in `LITERATURE_REVIEW.md`)

- **Three 2026 papers find that recursion is not what makes these methods
  work.** A reproduction found deeper recursion harmful; an Apple paper (SRLM)
  states that "recursion itself is not the primary driver of performance";
  another (λ-RLM) beats RLM with a fixed set of operations. The gains come
  from letting the model work on the document through code.
- **Several new systems are evaluated on OOLONG**, including one compared
  against Claude Code. **All are English-only.** No work found evaluates any of
  these systems in another language, so the cross-lingual question is still
  open.
- **No new benchmark covers Turkish long-context aggregation.** Two new
  multilingual long-context benchmarks (7 and 6 languages) exclude Turkish.
- The RLM authors released an 8-billion-parameter model trained to work this
  way (RLM-Qwen3-8B). It fits the planned hardware and has never been tested
  in Turkish.

## 4. Next step: first model runs

The dataset is ready for evaluation once the scoring decision in section 2 is
made. Planned order:

1. **Per-record accuracy probe.** Ask each model to label a few hundred single
   records per dataset. Cheap, and it is what lets every later score be read.
2. **Whole document in one prompt**, on the documents up to about 130K tokens
   (1,270 of the 2,240 questions), with one hosted frontier model and one
   open model.
3. **A code-using agent** (Claude Code, RLM, RLM-Qwen3-8B) on the same
   questions, recording the code each one writes, to see whether it reads the
   whole document or samples it, and whether that differs between Turkish and
   English.

Cost note: sending each question with its own document amounts to about 580
million input tokens for the full benchmark; asking all of a document's
questions together reduces that to about 51 million.

## 5. Decisions required

1. **Hard subset and scoring:** adopt the proposal in section 2, or keep the
   current grades.
2. **Thesis title.** Current: *Recursive Language Models for Turkish
   Long-Context Aggregation: A Matched-Twin Benchmark and a Cross-Lingual
   Study.* Given section 3, a title that does not rest on "recursive" is
   safer, for example *Do Long-Context Models Read in Turkish? A Matched
   Turkish-English Aggregation Benchmark and a Cross-Lingual Study.*
3. **Target venue.** Under the current CORE ranking (ICORE2026): ACL, EMNLP,
   NeurIPS (including its Datasets and Benchmarks track), ICLR and ICML are
   A*; NAACL and EACL are A; COLING and LREC are B. Realistic targets once model
   results exist: NAACL or EACL (A), with ACL, EMNLP or NeurIPS Datasets and
   Benchmarks as the stretch. Whether "Findings" papers count for the
   graduation requirement needs checking with the institute.
