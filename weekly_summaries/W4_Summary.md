# TR-OOLONG: Week 4

*Updated 2026-09-16. Carries over the items the week 3 meeting ran out of time for. Section 5 reports a shortcut check built on the 16th and the rebuild that followed it.*

---

## 0. Where the benchmark stands

**Rebuilt and extended on 16 September.** The benchmark is now **11 datasets · 195 documents · 2,240 questions · 9 question types · 2 languages**, documents from 3,000 records to one million tokens. Three Turkish datasets were added this week specifically to fix a weakness described in section 5, and every question now carries a measured difficulty grade.

**What is published is still the previous version.** Hugging Face and the GitHub tag serve the 15 September release: 8 datasets, 110 documents, 1,254 questions, 10 question types. Nothing has been uploaded since. The published version contains one question type that has since been withdrawn.

| | published (15 Sep) | current build (16 Sep) |
|---|---|---|
| datasets | 8 | **11** |
| documents | 110 | **195** |
| questions | 1,254 | **2,240** |
| question types | 10 | **9** |
| largest label space | 48 | 48 |
| difficulty grades | none | **per question** |

**Figures that are easy to quote wrongly, and the correct framing:**

- *"2,240 questions."* Correct as a count, misleading as evidence. **71.8% of them can be answered by a reader that sees a twentieth of the document.** The number to quote is the 259 graded very hard, or the pair of band scores. Section 5, finding 9.
- *"Documents up to 1 million tokens."* True as a length. Under the proportional scoring rule a longer document is not a harder one.
- *"Eleven datasets."* Correct, but two of them contain essentially no hard questions and exist for the matched Turkish/English comparison rather than for difficulty.
- *"A model forced to truncate the document does worse."* **Not supported.** A reader spending the same budget on the two ends of a document loses almost nothing.
- *"The benchmark requires a model to process every record."* **Withdrawn.** It requires classifying Turkish records and combining the results, which is narrower and still substantial.
- *"Difficulty grades show the benchmark is hard."* **No.** They show which questions are hard, measured against four specific shortcut strategies. They are a disclosure and an instrument, not a difficulty claim.

---

## 1. Method questions

### If depth 2 is harmful, should depth never exceed 1? And does that make the method "just agents and sub-agents"?

**On not exceeding 1: yes, and nothing in the current plan changes.** Depth 1 was already the configuration in use, matching the original paper. The reproduction study simply confirms it was the right setting.

**On whether the method is therefore unremarkable: no, and this is worth being fair about.** What the method contributes is not the recursion. It is two things that do hold at depth 1:

- The document is never placed in a prompt. It is loaded into a programming environment as a variable, and the model writes code against it. This is what avoids degradation on very long inputs.
- The model decides how to break the document up, at run time, in code it writes itself, rather than following a splitting rule fixed in advance by a programmer.

Those produce the reported results, which are substantial: median improvements of 26% over context compaction, 130% over a coding-agent scaffold, and 13% over a commercial coding assistant, across four long-context tasks at comparable cost.

**On "depth 2 proves recursion is unnecessary": that overstates the evidence.** One reproduction tested depth 2 on two benchmarks with two models and found it degraded accuracy while inflating runtime roughly a hundredfold. That is good evidence it does not help *on those tasks*. It is not a general proof that recursion is useless. The defensible sentence is the factual one: *a reproduction found depth 2 degrades accuracy and inflates runtime from 3.6 to 344.5 seconds, so depth 1 is the configuration in use.*

### Does the method's paper contain an architecture figure?

**Yes.** Figure 2 shows it: the prompt is treated as part of the environment, loaded as a variable inside a programming environment, with the model writing code to inspect and decompose it.

A separate figure is still worth having for this work, because it needs to show something the original does not: the difference between one level of delegation and genuine nesting, and why the first is what actually runs. The existing diagram set covers that.

### Do the worker models each receive the same amount of context?

**No, and this turned out to be more interesting than expected.** The root writes the splitting code itself, so chunk sizes are decided per query by the model rather than fixed by the system. There is no uniform chunk size.

**The original authors report this becoming unstable with weaker models.** Their system prompt for the open-weight coding model differs from the frontier one by a single added line warning it not to make too many sub-calls, because without that warning, in their words, the model "will try to perform a subcall on everything, leading to thousands of LM subcalls for basic tasks." They also adjusted prompts for a smaller model whose context window is 32,000 tokens against the frontier model's 272,000.

**This is directly relevant to two planned research questions**: which models are capable enough to act as a root, and whether giving weak models explicit guidance helps. The original authors encountered exactly that problem and solved it with a prompt line. That is a finding to build on rather than rediscover.

### Does running sub-calls in parallel rather than sequentially affect results?

**Accuracy: no.** The pieces are independent, so the order they are processed in cannot change the combined answer.

**Token cost: no.** The same calls are made either way, with the same content.

**Elapsed time: substantially.** The paper names the absence of parallelism as the reason a single query can take minutes, and estimates concurrency would compress total time by a factor of two to three.

The one indirect risk is that dispatching many calls at once can hit provider rate limits, which changes retry behaviour. Worth watching, not worth worrying about.

### Divide and conquer, explained more concretely

Three steps: **break the problem into smaller problems of the same kind, solve each, combine the results.** What makes it *divide and conquer* rather than simply "splitting the work" is that solving each smaller piece means **applying the very same procedure again**, repeatedly, until the pieces are trivial.

Three examples, increasingly close to this work:

- **Sorting a list.** To sort it, sort the left half, sort the right half, then merge the two sorted halves. Each half is sorted by the same method, which sorts *its* halves, and so on down to single items.
- **Looking up a word in a dictionary.** Open to the middle, decide which half the word is in, discard the other, then repeat on what remains. Each step is the same operation on a smaller range.
- **Counting votes in a national election.** The national total is the sum of regional totals; each regional total is the sum of district totals; each district total is the sum of individual ballot boxes. Every level performs the same operation: add up what the level below reports.

**That last example is the clearest way to see what this method does and does not do.** Counting an election could be organised with many levels, or with a single one: every ballot box reports straight to the centre, and the centre adds them up. Both give the identical answer. The multi-level version only earns its place when a single centre cannot handle the number of reports arriving at once.

**The method as evaluated is the single-level version**: one centre, many boxes reporting directly. That works whenever the fan-out is manageable, which it is for documents of the sizes tested. It is the reason depth 1 suffices, and the reason a second level adds cost without adding capability.

---

## 2. Benchmark-design questions

### Is exploitation by string search a recognised problem in benchmarks, and is a sub-1% leak rate negligible?

**It is recognised, and it has a literature.** The general phenomenon is a model scoring well by exploiting a surface regularity rather than performing the intended task, studied as annotation artifacts, shortcut learning, and "right answers for the wrong reasons." The standard diagnostic is to run a deliberately impoverished solver that *cannot* do the real task and check it fails.

**On whether under 1% is negligible: this project's own evidence says firmly no.** An earlier version of the Turkish review data leaked its label in **0.84%** of records. A solver doing nothing but substring search scored **73%** on "which label is most common" against a chance rate of 33%. Under one percent of records was enough to determine the answer outright, because the leaks correlate with the quantity being asked about.

**So the rule to state is: leak rate does not predict exploitability.** A small, correlated leak can fully determine an aggregate. This is why leaking records are removed at build time rather than reported as a caveat, and why the shipped leak rate is zero rather than small.

For the Turkish-label variant, the 0.14% figure is the *cost* of the filter, not residual risk: those records are dropped, so what ships still leaks nothing.

### For a future training dataset built from solving trajectories, which benchmark should it be tested against?

**The reasoning is correct: not this one.** A model trained on trajectories from this benchmark and then tested on it would be scored on documents drawn from the same pool of records it trained on. Documents within a single length tier already share 21–39% of their records, so even a train/test split of documents does not separate them. The model could be rewarded for having memorised individual records rather than for learning to aggregate.

**Testing against the English benchmark this one is modelled on is the right instinct**, with one check to perform first: **confirm the source corpora do not overlap.** That benchmark is built from ten classification datasets, and at least one corpus considered here was identified as among them. If any shared source exists, that route is not clean either and the overlap must be stated.

**A stronger control is already available:** train on English review trajectories and test on the Turkish review sets. Those are genuinely different corpora (different text, different brands, different answers), so nothing transfers except the skill being claimed.

### If the dataset is published now, are permissions needed, can it be updated, and does it establish priority?

**No permissions are needed.** Every source licence is resolved. Seven of the eight sets can be redistributed as they are. The eighth cannot redistribute its text, so it ships as questions and answers only, with the text rebuilt locally by a script, a standard arrangement that requires no correspondence with anyone.

**Yes, it can be updated.** Dataset repositories on the intended platform are version-controlled, so corrections can be published later and any specific version can be cited by revision. This is already the recommended citation practice for this project: cite the tag, the version recorded in the manifest, and the source hash together.

**Yes, publishing establishes priority**: that is the main argument for doing it now rather than waiting for evaluation results.

**One caution on the wording of the claim.** "First Turkish long-context benchmark" is broader than what the evidence supports; Turkish long-context work does exist. The supported claim is narrower and still strong: **the first Turkish long-context *aggregation* benchmark**, and the first with a matched English twin built by an identical pipeline. Keep the qualifier.

---

## 3. A proposed experiment worth more than the one it replaces

**The idea:** rather than forcing a second level of decomposition, *offer* it: give the worker models the ability to decompose further if they judge it useful, and then measure how often they take it, comparing Turkish against English.

**This is unexplored, and better founded than the forced-depth experiment it replaces.** The original authors list adaptive depth explicitly as future work: letting the root decide whether a sub-answer is itself worth decomposing, instead of fixing depth in advance. The reproduction study tested *forced* depth 2, not *optional* depth 2. Nobody has measured what a model chooses when the choice is available.

**Why the cross-lingual version is the interesting one.** On the record-matched pair the same question has the same correct answer in both languages, so a difference in how often a model chooses to decompose further is attributable to the language rather than the task. That is the same design already proposed for a separate observation: whether models reach for shortcuts more readily in a language they handle less well.

**One caution on interpretation.** A choice to decompose further should not be read directly as low confidence. It may reflect the difficulty of the chunk, the phrasing of the prompt, or simple verbosity. It is a behavioural measurement, and it should be reported as what a model *does*, not as what it *believes*.

---

## 4. Open items

**Needs a decision:**

- ✅ Published on 15 September; corrected description published on the 16th.
- Whether the Turkish dictionary-form label variant replaces the current Turkish intent dataset or remains a side experiment.
- **Decision required before the first model run: how counting questions are scored and reported.** Section 6 explains why. The position this work takes: keep the scoring rule as it is, but report every counting score as improvement over the guess-without-reading floor, draw the reference readers (guess only, first 1,000 records, random 5%) as lines on every chart, and record separately how well the model classifies single records, so that reading coverage and classification quality can be told apart. This changes nothing that is frozen.

**Done since the last summary:**

- ✅ **The sampling shortcut detector is built and run**, and it found something material. See §5.
- ✅ **The entity-mention audit.** A review names a brand other than its own in 0.66% of the Turkish set and 13.8% of the English one, though the English figure is inflated by brand names that are ordinary words. Correctness is unaffected either way, since records are grouped by the printed marker rather than by free-text mentions.
- ✅ **The brand-question length constraint is recorded in the datacard.**

**Still outstanding, and needs a native speaker:**

- The 150-row re-check separating translation errors from annotation errors.

**Still outstanding, not blocking publication:**

- The build-time source-pool partition, required only before trajectory data is used for training.
- Confirming whether any source corpus is shared with the English benchmark, which determines whether it is a clean transfer target.

**Queued for evaluation:**

- A retrieval baseline.
- The optional-decomposition experiment described in §3.

**Blocked on data:**

- The positional-shift question type, pending a Turkish corpus with real dates.

---

## 5. A fifth check: can a question be answered by reading only part of the document?

The four existing checks all ask whether a question can be answered *without opening the document*. None asked whether it can be answered by reading only **part** of it. That check now exists, it was run on this benchmark and on OOLONG, and it changed both the benchmark and what it claims.

### The four readers, in plain terms

Each reader is given a budget, say 5% of the records, and is told the correct category of every record it reads. They differ only in **which** records they get.

| name | what it does | why it is modelled |
|---|---|---|
| **blind** | opens nothing. Counts the separators between records, divides by the number of categories, answers that. | the floor. Any score must be read against this. |
| **random 5%** | reads a random one-in-twenty records, scales the result up | what a model with code execution can deliberately do |
| **prefix 5%** | reads the first one-in-twenty records | what a model does by default when the document is longer than its window |
| **head-and-tail 5%** | reads half its budget at the start and half at the end | what a model does if it is told the document has two ends. Costs the same as prefix. |

**A worked example.** A document holds 6,000 reviews, 1,700 of them negative. The question is "how many are negative?"

- **blind** answers 6,000 ÷ 3 = 2,000. That is 18% off, which under proportional scoring is worth about **0.82**. It read nothing.
- **random 5%** reads 300 reviews, finds 85 negative, answers 85 × 20 = 1,700. Almost exact, worth about **0.89**.
- The same reader on a question whose true answer is **20** reads 300 records and finds **one**, answers 20 × 1 = 20 by luck or 0 by bad luck. Worth about **0.27** on average.

That last line is the whole finding.

### What the numbers mean, and which direction is good

**All scores in this document run from 0 to 1, not out of 100.** 1.00 is a perfect answer, 0.50 is halfway, 0.00 is completely wrong.

**Every score in this section is a cheater's score, so a high number is bad news.** These are not results for any model. They are what a deliberately impoverished solver achieves, and the purpose of building such a solver is that it should fail. A model scoring 0.90 would be excellent; a cheater scoring 0.90 means the question can be answered without doing the work.

| a cheater scores | verdict | what it means |
|---|---|---|
| 0.00 to 0.35 | **good** | the shortcut fails. The document has to be read. |
| 0.35 to 0.60 | acceptable | partial credit, but real reading still wins clearly |
| 0.60 to 0.80 | weak | the question is doing little work |
| 0.80 to 1.00 | **bad** | the question is answerable without reading |

Two thresholds are enforced automatically: a solver that beats its floor by more than 0.15 fails the formatting check, and a corpus-knowledge score above 0.70 at any document length raises a warning.

**Where the benchmark stands against that scale, after the rebuild:**

| dataset | question type | reads nothing | reads 5% | verdict |
|---|---|---:|---:|---|
| the four intent sets | **rare-category counts** | **0.00** | **0.26 to 0.29** | **good** |
| `amazon_hpc_en`, `vitamins_tr` | **brand counts** | n/a | **0.24 to 0.34** | **good** |
| the four intent sets | ordinary counts | 0.46 to 0.47 | 0.54 to 0.63 | acceptable to weak |
| the four review sets | ordinary counts | 0.44 to 0.55 | **0.88 to 0.91** | **bad** |

Two things follow. First, read the *reads nothing* column: on the Turkish supplement set a solver that never opens the document scores 0.55 on counting, which is why results must be reported as improvement over that floor rather than as raw scores. Second, on rare-category questions that same floor is 0.00, which is what the rebuild bought.

The last row is the honest weak point. Three categories over several thousand records means every answer is around 2,000, and an answer that large is always estimable from a sample. No wording change repairs it; it needs a corpus with more categories.

### The rule that explains every number below

One quantity decides how well a partial reader does: **how large the true answer is**. Not the document's length, not how balanced the categories are, not the order the records are in. The arithmetic is a poll's margin of error. To estimate "how many are negative" within a few percent, a reader needs to see a few hundred negative examples. If the true answer is 2,000 it will see plenty in any sample. If the true answer is 20 it will see one, and the estimate is worthless.

### Finding 1: a reader that opens nothing already scores about half

Every document uses a fixed marker between records, so counting the records takes no reading. A reader that counts markers, divides by the number of categories and answers that scores **0.43 to 0.55** on counting questions. That is the floor, and every counting score must be reported as improvement over it.

A figure quoted in earlier weeks, "a 5% sample scores 0.95 against a baseline of 0.05", compared two different scoring rules. Under the same rule the honest contrast is 0.89 against 0.44.

### Finding 2: under this rule, a longer document is not a harder document

A poll of 1,000 voters predicts a national result to within about three points whether the country has one million voters or eighty million. The error depends on how many people were asked, not how many exist.

The same holds here. A reader that classifies 1,000 records and scales up scores **0.94 to 0.97** on counting at every document length from 100,000 tokens to one million. On the counting and proportion questions, a proportional score cannot tell a model that read 1,000 records from one that read 16,000. The length axis still tests whether a model can take the document in at all without breaking, which is real but different.

### Finding 3: a single score cannot say whether a model read more or judged better

A perfect reader of a random 5% scores 0.89 on counting. A reader that opens **every** record but misjudges one in ten scores 0.74 to 0.90. The two are indistinguishable from the score alone. This is why the harness must separately record how well the model classifies single records.

### Finding 4: reading the two ends works as well as reading everywhere

Each document is built as two halves, each internally shuffled, with one category deliberately made more common in the second half. A reader confined to the beginning therefore sees a distorted sample. A reader that spends the *same* budget on the first fifty records and the last fifty sees both halves and is not distorted at all: on the largest documents the beginning-only reader scores 0.53 and the two-ends reader scores 0.92.

Document order protects nothing. No arrangement of records defeats a reader that samples across the whole document, because sampling ignores order.

### Finding 5: one question type was removed from the benchmark

One of the ten question types asked whether a category became more or less common in the second half. Against the two-ends reader, fifty records from each end answer it **perfectly on all eight datasets**. The question has two possible answers and the change happens at a known point, so a reader that looks at each end reads the answer off directly. Widening the change or making it gradual would not help, because the question asks only for a direction.

It has been removed. It is still present in the published version, and results on it should be discarded rather than explained.

**How it passed four checks.** Every difficulty rule in the builder constrains either how large an answer must be or how wide a margin must be. Both are rules about *quantities*, and this question's answer is a direction, so it fell between them. The fifth check could not catch it either: its only position-sensitive reader cannot answer that question type at all, so the result table showed an empty cell, and an empty cell was read as "nothing solved this" rather than "nothing tried". The check now reports, for every reader and question type, what fraction it could even attempt.

### Finding 6: the same measurement was run on OOLONG, and both benchmarks obey the same rule

OOLONG is the English benchmark this one follows and the one the method under study reports its results on. Its construction code is unreleased, but **its built data is public and includes the correct category of every record**, so the same readers run on it directly. All 41 of its files were processed: eight source corpora, category counts from 2 to 10, documents from one thousand to four million tokens. A question was included only where a perfect reader of the whole document reproduces OOLONG's own published answer exactly, which held for 3,553 questions.

Its counting questions trace the rule exactly:

| OOLONG's true answer | questions | score of a reader seeing 5% |
|---|---:|---:|
| 1 to 9 | 284 | **0.00** |
| 10 to 29 | 72 | 0.21 |
| 30 to 99 | 76 | 0.60 |
| 100 to 299 | 80 | 0.76 |
| 300 to 999 | 108 | 0.88 |
| 1,000 and above | 197 | 0.96 |

This benchmark's own sets fall on the same line at the same answer sizes.

**Three conclusions, in order of importance.**

1. The exposure is a property of counting over a large collection under a forgiving score. It was not introduced by this pipeline, corpus or language.
2. **OOLONG is less exposed than this benchmark, and the reason is the fix.** Most of its questions are restricted to a subset before being asked, such as "among the entries belonging to this one user" or "among the entries from April", which makes the answers small. 284 of its counting questions have answers below ten and score zero for every partial reader.
3. **No published work on OOLONG reports either floor.** Neither the read-nothing floor nor any partial-reading measurement appears in its documentation, so results reported on it are not separated into how much was read and how well it was judged. On its largest question type, 1,097 comparison questions, a reader seeing a random 5% scores 0.78 under OOLONG's own strict scoring.

**How to state it.** Not "OOLONG has the same problem, so ours is acceptable". The defensible statement is: this is a measurable property of the task family; it was measured here on both benchmarks; OOLONG mitigates it by restricting questions to subsets; this benchmark now adopts the same mitigation.

### Does strict scoring solve it?

Partly, and not usefully. Under strict exact-match a partial reader scores essentially zero on counting questions, on both benchmarks. But six of the nine remaining question types are answered with a category name rather than a number, and those are *already* scored by exact match: a reader seeing 5% answers them correctly 78 to 100 percent of the time.

More decisively, strict scoring does not only defeat the partial reader, it defeats everyone. A reader that opens every one of 6,469 records and misjudges only one in a hundred scores **0.015** on counting. A near-perfect full reader and a 5% sampler become indistinguishable, because both score zero. That is why the proportional rule exists.

### Finding 7: the fix is built, and it removes the read-nothing floor entirely

Counting questions about **rare categories** were added: categories holding between five and thirty records in that particular document. They are worded exactly like any other counting question, so a model is not told the answer is small.

| | reads nothing | sees 5% | sees 25% |
|---|---:|---:|---:|
| ordinary counting question (typical answer 74) | 0.46 | 0.54 | 0.81 |
| **rare-category question** (answers 5 to 30) | **0.00** | **0.27** | 0.65 |

**The first column is the more important result.** A reader that opens nothing and divides by the number of categories scores about 0.46 on an ordinary question and **zero** on a rare one, because dividing by 48 gives roughly 62 when the true answer is 20. The floor is not reduced, it is removed. A reader that knows the source corpus's overall proportions but never opens the document falls the same way, from 0.41-0.50 to 0.06-0.12.

A wider band of five to fifty was also built and measured, and rejected: it lets the read-nothing score back up to 0.11 and returns half the resistance.

**What it does not reach.** The two three-category review datasets without a brand column cannot host this question type: with three categories over several thousand records no category is ever that small, and they have no second axis to narrow by. Their counting questions remain the most exposed in the suite. This is a property of a three-category label space, not something question wording can repair.

### Finding 8: three new datasets were added, because the old ones cannot be repaired

The weakness above is concentrated in the four three-category datasets, and it is arithmetic rather than a defect. To answer "how many of these records are negative" within a few percent, a reader needs to see a few hundred negative examples. With three categories over several thousand records every answer is around 1,500, so a one-in-twenty sample already contains 75 of them and the estimate is close. Getting answers small enough requires **more categories**, which requires a different corpus.

Three were found and built, all Turkish:

| dataset | what it is | categories |
|---|---|---:|
| `sikayet_tr` | consumer complaints | **29** |
| `interpress_tr` | news articles, with publication dates | **17** |
| `sinema_tr` | film reviews on a 10-point rating | **10** |

The benchmark is now 11 datasets, 195 documents, 2,240 questions.

Two of the three cannot redistribute their text, because neither uploader states a licence. They ship as questions and answers with a script that rebuilds the text locally, which is the arrangement one existing dataset already uses. The third is under a clear licence and ships normally.

### Finding 9: every question now carries a measured difficulty, and this is the part that matters

The measurements above were made per question *type*. Averaging over a type hides the spread: a type that looks resistant still contains individually trivial questions. Every one of the 2,240 questions was therefore graded on its own, by running all four readers against it and recording the best score any of them achieved.

| grade | meaning | questions | share |
|---|---|---:|---:|
| **very hard** | no reader seeing 5% got close | 259 | 11.6% |
| hard | | 140 | 6.2% |
| moderate | | 232 | 10.4% |
| **easy** | a reader seeing 5% answers it | 1,609 | **71.8%** |

**Grading does not make the 71.8% smaller, and it is not meant to.** What it buys is a measuring instrument the benchmark did not have.

An easy question can be answered from a twentieth of the document, so what it tests is whether a model can **classify Turkish records at all**. A very hard question cannot, so what it tests is whether the model **worked through the whole document**. Those are different abilities, and until now a single score mixed them, which is exactly the problem stated in finding 3.

With graded questions they separate:

- A model scoring 0.90 on easy and 0.30 on very hard is **sampling**: it reads Turkish well and does not read much of the document.
- A model scoring 0.40 on both **cannot read Turkish**, and its poor long-document result says nothing about long documents.
- A model scoring well on both is doing the task.

The gap between the two band scores is an estimate of how much of the document the model actually read. No comparable benchmark reports this, OOLONG included.

Every document length contains very hard questions, between 3% and 15%, so the headline result can still be reported as a curve over length.

**The grades are stable enough to publish.** Each is averaged over 200 samples; the largest remaining uncertainty on any single question is 0.035. The 10.7% of questions close enough to a boundary that the grade could move are marked as such rather than presented as settled.

### What a reviewer will attack, and what has to be said before they do

Each of these is true, and each is worse if it is found rather than declared.

1. **"Most of your benchmark is easy."** True: 71.8% of questions can be answered by reading a twentieth of the document. The answer is not a denial. It is that the easy questions are labelled as such, are reported separately, and serve as the classification control that makes the hard ones interpretable.

2. **"Your difficulty grades only reflect your own four readers."** Also true. A grade of very hard means these four strategies failed, not that no shortcut exists. A fifth reader could crack questions currently graded hardest, exactly as the third and fourth readers did when they were added partway through this work.

3. **"Your readers are given the correct label of every record they read."** True, and deliberate. They are perfect classifiers reading part of the document, so they are upper bounds: a real model does worse on the same amount of reading. A shortcut that fails even for a perfect classifier is not available to anything.

4. **"Two of your new datasets have no licence."** True. Their text is not redistributed and is rebuilt locally from the original source. The question should be put to both uploaders.

5. **"Two of your datasets contain no hard questions at all."** True and specific: one has zero very hard questions and another has one. Those two exist to support the matched Turkish/English comparison and to serve as the classification control. They should never be cited as evidence of aggregation difficulty.

6. **"This is a property of the metric, not of the data."** True. The proportional scoring rule gives most of the credit for an approximately right answer. Under strict scoring almost every counting question becomes very hard, but so does every honest full reader: a model that opens all 6,469 records and misjudges one in a hundred scores 0.015. Strict scoring does not separate good from bad; it fails everyone.

### How the position changed over the week, in order

Stating this plainly, because each step was caused by a measurement rather than a change of opinion.

1. A fifth check was built, asking whether a question can be answered by reading only part of the document. It could, on most question types.
2. The check was then found to have the wrong reference point. The honest comparison is against a reader that opens nothing, which already scores about half.
3. The check was found to model only two of the four ways to spend a reading budget. Adding the other two withdrew a published claim about document length and removed one question type entirely.
4. The same check was run on OOLONG. Both benchmarks obey the same rule, and OOLONG is less exposed because most of its questions are restricted to a subset before being asked.
5. Question types were added and datasets were found that make small answers possible, which is the only thing the arithmetic allows.
6. Grading was added per question, which does not reduce the exposure but converts it into a measurement.

### What else changed in this rebuild

- **A tier was removed.** The largest Turkish supplement documents used 48% of the available reviews, so their category mix could not differ much from the source's, and a reader who knew the source's proportions and never opened the document scored 0.75. That length is gone.
- **A rule that looked obvious was not adopted.** Capping the share of the source any one document may use was tried as an automatic rule and removed six document lengths across the suite, including the longest. The measurements show why it is the wrong rule: one dataset uses 53% of its source and passes the corpus-knowledge check, while another uses 48% and fails it. A large category space tolerates a share that a small one does not. The share is now reported as a warning and the corpus-knowledge check remains the actual test.
- **More documents at the shortest length** on the four review sets, since statistical power comes from documents rather than questions. Not done on the four intent sets: their documents already overlap each other by 14 to 39 percent, so more of them would be more correlated evidence rather than more evidence.
- **The matched Turkish/English pair now agrees on all 120 questions** rather than 100, because the questions whose answer is a word rather than a number now carry a language-neutral key alongside the word.

### What this does and does not mean for the thesis

Every answer remains exactly correct for its document. What narrows is the claim: the benchmark demonstrably requires **classifying Turkish records and combining the results**; it does not demonstrate that a model read the whole document, and under proportional scoring it does not demonstrate that longer was harder.

For the method under study this matters in one specific way. Its expected advantage is on documents a plain model cannot take in at once. That advantage will show against a model that is *truncated*, which degrades, but not against one that is allowed to *sample*, which does not. The evaluation must state which the baseline is, and report scores as improvement over the read-nothing floor.

### Open items from this section

- **One document length is flagged and kept.** On the English intent set at 100,000 tokens, a reader who knows the source corpus scores 0.73 on proportion questions. Its Turkish counterpart, built the same way, scores 0.45 at the same length. The gap between two halves of the same construction indicates sampling noise on ten questions rather than a real exposure, so the length is kept and labelled rather than removed; removing it would halve that dataset and break the pairing.
- **No suitable additional corpus was found.** A search for a Turkish corpus with many categories and per-record dates returned nothing usable. Dates would be valuable twice over: they allow questions restricted to a time period, which is what makes OOLONG's answers small, and they support the single most sampling-resistant question type observed in either benchmark, which scores 0.005. The one strong Turkish candidate, a 169,000-row news set with 16 categories, declares no licence and was therefore not adopted. A licence answer from its uploader would unblock it.
