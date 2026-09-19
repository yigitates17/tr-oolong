# TR-OOLONG: Week 4

*Updated 2026-09-20. Carries over the items the week 3 meeting ran out of time for. Section 5 reports a shortcut check built on the 16th and the rebuild that followed it. Sections 0, 5 and 6 were revised on the 20th after an independent review of the published files, which found one defect worth correcting before the meeting.*

---

## 0. Where the benchmark stands

**Rebuilt and extended on 16 September.** The benchmark is now **11 datasets · 195 documents · 2,240 questions · 9 question types · 2 languages**, documents from 3,000 records to one million tokens. Three Turkish datasets were added this week specifically to fix a weakness described in section 5, and every question now carries a measured difficulty grade.

**The current version is published.** All eleven datasets went to Hugging Face on 16 September, and the files served there are byte-for-byte the ones described here. An earlier draft of this summary said the upload had not happened; that was wrong, and it is corrected here.

| | previous (15 Sep) | published (16 Sep) | corrected (20 Sep) |
|---|---|---|---|
| datasets | 8 | **11** | 11 |
| documents | 110 | **195** | 195 |
| questions | 1,254 | **2,240** | 2,240 |
| question types | 10 | **9** | 9 |
| largest label space | 48 | 48 | 48 |
| difficulty grades | none | **per question** | per question |

**One defect was found on 20 September and has been repaired.** Each dataset numbered its own questions from scratch, so the same question number was used by several datasets at once. Across the whole benchmark the 2,240 questions carried only 955 distinct numbers. A person who loaded all eleven datasets into one table and used those numbers would have lost well over half the benchmark without any warning or error message. Every question and every document now also carries a name that includes its dataset, which cannot collide, and an automatic check refuses any future release that repeats the mistake. Nothing else changed: every question, every answer and every difficulty grade is identical to what was published on the 16th. Section 6 gives the detail.

**This correction needs to be uploaded.** The repaired files are ready and verified locally. Until they are uploaded, anyone downloading the benchmark gets the version with the colliding numbers.

**Figures that are easy to quote wrongly, and the correct framing:**

- *"2,240 questions."* Correct as a count, misleading as evidence. **71.8% of them can be answered by a reader that sees a twentieth of the document.** The number to quote is the 259 graded very hard, or the pair of band scores. Section 5, finding 9.
- *"Documents up to 1 million tokens."* True as a length. Under the proportional scoring rule a longer document is not a harder one.
- *"Eleven datasets."* Correct, but two of them contain essentially no hard questions and exist for the matched Turkish/English comparison rather than for difficulty.
- *"A model forced to truncate the document does worse."* **Not supported.** A reader spending the same budget on the two ends of a document loses almost nothing.
- *"The benchmark requires a model to process every record."* **Withdrawn.** It requires classifying Turkish records and combining the results, which is narrower and still substantial.
- *"Difficulty grades show the benchmark is hard."* **No.** They show which questions are hard, measured against four specific shortcut strategies. They are a disclosure and an instrument, not a difficulty claim.
- *"Grading fixed the sampling problem."* **No, and this is the easiest one to get wrong.** Grading measured the problem; it changed no question. 71.8% are still skimmable. What reduced that share was adding rare-category questions and three new datasets, in findings 7 and 8. Grading only labels.
- *"2,240 questions is 2,240 pieces of evidence."* **No.** 674 of them cover 337 facts, because the same document and category is asked about both as a count and as a share. Section 6.3.

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

### Divide and conquer, concretely

Break a problem into smaller problems of the same kind, solve each, combine the results. What makes it *divide and conquer* rather than just splitting work is that each smaller piece is solved by **applying the same procedure again**.

Counting a national election is the clearest case. The national total is the sum of regional totals, each region the sum of its districts, each district the sum of its ballot boxes. Every level does the same thing: add up what the level below reports.

**That example also shows what this method does and does not do.** An election could be counted with many levels, or with one: every ballot box reports straight to the centre. Both give the identical answer. The multi-level version only earns its place when a single centre cannot handle the number of reports arriving at once.

**The method as evaluated is the single-level version.** That works whenever the fan-out is manageable, which it is at the document sizes tested. It is why depth 1 suffices and why a second level adds cost without adding capability.

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

### Decisions required, in the order they block things

These are the questions this work cannot settle on its own, phrased as questions rather than as recommendations. A recommendation is given under each, with what it costs.

**1. When should the corrected files be uploaded?** This has replaced the question that stood here before. The earlier question was whether to publish at all; that was answered by publishing on 16 September, and the question no longer applies. What is now outstanding is narrower: the published version numbers its questions in a way that makes the eleven datasets unsafe to combine, the repair is built and verified, and it has not been uploaded. Section 6.1.
*Recommendation: upload before the benchmark is mentioned publicly anywhere.* It is a replacement of the same files, it changes no question and no answer, and the cost of delay is that anyone who downloads in the meantime gets the version that silently loses data when its datasets are combined.

**2. Should one matched Turkish/English pair be replaced?** The two three-category pairs exist to support the cross-lingual comparison, and they do that well. They contribute almost nothing else: of 259 questions graded very hard, those two pairs supply twenty-one, and one of the four datasets supplies none at all. A replacement partner has been found for the new Turkish complaints dataset: the US consumer-complaints corpus, which is public-domain, has the same register, carries a comparable category space, and additionally has company and date fields.
*Recommendation: build it and compare before deciding.* This is the largest change on the table, because the matched pair is the centre of the cross-lingual claim, and it should not be swapped on the strength of a table alone.

**3. Should the two licence enquiries be sent, and by whom?** Two of the three new Turkish datasets declare no licence, so their text is not redistributed and is rebuilt locally by a script. That arrangement is already in place and is the safe position either way; nothing about the release depends on an answer.

*Position taken: the source datasets will be used exactly as they are, with no further correspondence about their contents.* The only thing still worth doing is a short enquiry asking whether redistribution is permitted, from the university address, because the difference it makes is one sentence in the write-up: "no licence is declared, so the text is withheld" becomes "no licence is declared, the uploaders were contacted and did not respond, so the text is withheld". Silence is a perfectly good outcome; not having asked is the weaker position. If the enquiries are not sent, the release is unaffected and the two sets stay questions-only permanently.

**4. How should a score be reported, now that questions carry difficulty grades?** The options are a single pooled figure over all questions, or the two band scores plus the gap between them.
*Recommendation: the two bands and the gap, never the pooled figure.* A pooled figure over a question set that is 71.8% easy mostly measures whether the model can read Turkish. Section 5, finding 9.

**5. Is eleven datasets within the scope this thesis should carry?** Three were added in one week to fix a measured weakness. That is defensible on its own terms, but it enlarges what has to be described, gated and maintained.
*No recommendation; this one is genuinely a supervision question.*

### Previously open, and where they stand

| item | status |
|---|---|
| Publication | ✅ Published 15 September; all eleven datasets on 16 September. A correction to how questions are numbered is built, verified and uploaded (6.1). |
| The sampling shortcut detector | ✅ Built, run, and it found something material. Section 5. |
| The entity-mention audit | ✅ A review names a brand other than its own in 0.66% of the Turkish set and 13.8% of the English one, the latter inflated by brand names that are ordinary words. Correctness is unaffected: records are grouped by the printed marker, not by free-text mentions. |
| The brand-question length constraint | ✅ Recorded in the datacard. |
| Turkish dictionary-form label variant | Open: does it replace the current Turkish intent dataset or stay a side experiment? |
| How counting questions are scored | Position taken: keep the scoring rule, report every counting score as improvement over the guess-without-reading floor, and record separately how well the model classifies single records. Changes nothing frozen. |
| The 150-row re-check separating translation from annotation errors | Open, needs a native speaker. Affects the cross-lingual claim only. |
| Build-time source-pool partition | Open, needed only before trajectory data is used for training. |
| Whether any source corpus is shared with OOLONG | Open, determines whether it is a clean transfer target. |
| Retrieval baseline | Queued. |
| The optional-decomposition experiment (§3) | Queued. |
| The positional-shift question type | Blocked: needs a Turkish corpus with real dates. |

## 5. Can a question be answered by reading only part of the document?

The four existing checks ask whether a question can be answered *without opening the document*. None asked whether it can be answered by reading only **part** of it. That check now exists, it was run here and on OOLONG, and it changed both the benchmark and what it claims.

### How these numbers were produced

**No model was involved.** Each "reader" is a short program, not an AI. It is handed the document's records together with the correct category of each one, and it counts. It cannot read Turkish and cannot misclassify.

That is deliberate. Because it is handed the right answers, it does **better** than any real model could on the same amount of reading, so every score here is a **ceiling**. If the program fails at a question, no model succeeds by that route.

One of the four readers picks records at random, so each question is run **200 times with different draws and averaged**. The other three always pick the same records, so they run once. Largest uncertainty on any average: **0.035** out of 1.00. Fixed seeds, reproducible.

**Scores run 0 to 1. These are cheaters' scores, so high is bad.** A cheater at 0.90 means the question can be answered without doing the work.

### The four readers

| reader | what it does | why it is modelled |
|---|---|---|
| **blind** | opens nothing; counts separators, divides by number of categories | the floor every score must be read against |
| **random 5%** | reads a random one-in-twenty, scales up | what a model with code execution can do deliberately |
| **prefix 5%** | reads the first one-in-twenty | what a model does when the document exceeds its window |
| **head-and-tail 5%** | half the budget at each end | costs the same as prefix, and is far better |

### The one rule that explains everything below

**How large the true answer is decides whether a shortcut works.** Not document length, not category balance, not record order.

Two real questions, same document, 2,449 complaint records:

| | "how many are `sağlık`?" | "how many are `enerji`?" |
|---|---:|---:|
| true answer | 833 | 6 |
| reader that opens nothing | 0.13 | **0.00** |
| reader that sees 5% (122 records) | **0.94** | **0.00** |
| grade | easy | **very hard** |

122 records contain about 42 `sağlık`, and 42 × 20 = 840 against a true 833. The same 122 contain zero or one `enerji`, and 0 or 20 against a true 6 is hopeless. No cleverness repairs it; the information is not in the sample.

### Why 5%, and why it is not a flattering choice

5% is roughly what a model with a code tool samples on its own. To show nothing was tuned to it, every question was graded at six budgets:

| budget | very hard | hard | moderate | easy |
|---|---:|---:|---:|---:|
| 1% | 771 (34.4%) | 117 | 133 | 1,219 |
| 2% | 584 (26.1%) | 122 | 166 | 1,368 |
| **5% (reported)** | **259 (11.6%)** | **140** | **232** | **1,609** |
| 10% | 105 (4.7%) | 103 | 222 | 1,810 |
| 25% | 38 (1.7%) | 34 | 142 | 2,026 |
| 50% | 28 (1.2%) | 2 | 38 | 2,172 |

**5% is the conservative end.** At 1% the benchmark could advertise 771 hard questions instead of 259. The decline is smooth, so no budget is a cliff someone could have chosen to sit past. **28 questions resist a reader seeing half the document.**

### The nine findings

| # | finding |
|---|---|
| 1 | **A reader that opens nothing already scores 0.43 to 0.55** on counting, by counting separators and dividing. Every counting score must be reported as improvement over that floor. |
| 2 | **A longer document is not a harder one** under this scoring. A reader classifying 1,000 records scores 0.94 to 0.97 at every length from 100K to 1M tokens. The length axis tests whether a model can take the document in at all, which is real but different. |
| 3 | **A single score cannot say whether a model read more or judged better.** A perfect reader of 5% scores 0.89; a reader of everything that misjudges one in ten scores 0.74 to 0.90. Indistinguishable. |
| 4 | **Reading the two ends works as well as reading everywhere.** On the largest documents a beginning-only reader scores 0.53 and a two-ends reader 0.92, for the same cost. Document order protects nothing. |
| 5 | **One question type was removed.** `shift` asked whether a category grew in the second half. Fifty records from each end answer it perfectly on all eight datasets. It is withdrawn; results on it should be discarded, not explained. |
| 6 | **OOLONG obeys the same rule and is less exposed.** All 41 of its files were processed. Its counting questions trace the same curve, from 0.00 at answers under 10 to 0.96 above 1,000. It is less exposed because most of its questions are restricted to a subset first, which makes answers small. **No published work on OOLONG reports either floor.** |
| 7 | **The fix removes the read-nothing floor entirely.** Counting questions about rare categories (5 to 30 records) were added, worded identically to any other. Ordinary question: floor 0.46, 5% reader 0.54. Rare question: floor **0.00**, 5% reader **0.27**. A band of [5,50] was built and rejected: it lets the floor back to 0.11 and returns half the resistance. |
| 8 | **Three Turkish datasets were added**, because three categories over thousands of records cannot produce a small answer. `sikayet_tr` (29 categories), `interpress_tr` (17), `sinema_tr` (10). |
| 9 | **Every question now carries a measured difficulty grade.** 259 very hard (11.6%), 140 hard, 232 moderate, 1,609 easy (71.8%). |

### Grading measured the problem. It did not fix it.

**The 71.8% are still answerable from a twentieth of the document.** Not one question became harder. The same shortcuts work exactly as well.

What grading bought is that the benchmark can now report them apart. Before: one score over 2,240 questions, most skimmable, no way to tell a model that read everything from one that skimmed. After: two scores, and the gap between them estimates how much was read.

- 0.90 on easy, 0.30 on very hard: the model is **sampling**.
- 0.40 on both: the model **cannot read Turkish**, and its long-document result says nothing about long documents.
- Good on both: it is doing the task.

**What actually reduced the skimmable share** was findings 7 and 8, not grading. Grading only labels.

Grades are averaged over 200 samples, worst uncertainty 0.035, and the 10.7% near a band boundary are flagged rather than presented as settled. Every document length contains very hard questions (3% to 15%), so the headline can still be a curve over length.

### What a reviewer will attack, and what to say first

1. **"Most of your benchmark is easy."** True, 71.8%. They are labelled, reported separately, and serve as the classification control that makes the hard ones interpretable.
2. **"Your grades only reflect your own readers."** True. A fifth reader was added and moved 28 of 215. Disclosed in 6.2.
3. **"Your readers are given the correct label of every record."** True and deliberate. They are upper bounds; a real model does worse.
4. **"Two datasets have no licence."** True. Their text is not redistributed.
5. **"Two datasets contain no hard questions."** True: `musteri_tr` zero, `marc_en` one. They exist for the matched comparison and as the classification control, never as evidence of difficulty.
6. **"This is a property of the metric."** Partly, and it was measured. See 6.6.

### What else changed in this rebuild

- **A tier was removed.** The largest Turkish supplement documents used 48% of the available reviews, so a reader knowing the source proportions scored 0.75 without opening anything.
- **A pool-fraction cap was tried and rejected.** It removed six document lengths including the longest. One dataset uses 53% of its source and passes the corpus-knowledge check while another uses 48% and fails it, so the share is reported as a warning and the check remains the test.
- **More documents at the shortest length** on the review sets, since statistical power comes from documents rather than questions.
- **The matched pair now agrees on all 120 questions** rather than 100, because word answers carry a language-neutral key.

### What this means for the thesis

Every answer remains exactly correct for its document. What narrows is the claim: the benchmark demonstrably requires **classifying Turkish records and combining the results**. It does not demonstrate that a model read the whole document, and under this scoring it does not demonstrate that longer was harder.

For the method under study: its expected advantage is on documents a plain model cannot take in at once. That will show against a baseline that is *truncated*, which degrades, but not against one allowed to *sample*, which does not. The evaluation must state which the baseline is.

### Open from this section

- **One document length is flagged and kept.** On the English intent set at 100K, a reader knowing the source corpus scores 0.73 on proportion questions; its Turkish counterpart scores 0.45. The gap indicates sampling noise on ten questions, so the length is kept and labelled. Removing it would halve that dataset and break the pairing.
- **No suitable additional corpus was found.** A search for a Turkish corpus with many categories and per-record dates returned nothing usable. Dates would allow questions restricted to a time period, which is what makes OOLONG's answers small.

## 6. An independent review of the published files, 20 September

Every check above was written alongside the benchmark by the person who built it. On 20 September the published files were examined separately, starting from the data rather than the code, to find what the existing checks cannot see.

**How each result was produced**, because that decides how much weight it carries:

| finding | how | trust |
|---|---|---|
| 6.1 repeated numbers | counted distinct identifiers in the published files | **certain**, arithmetic |
| 6.2 fifth shortcut | a program that searches text for category names and counts matches | **certain** for that one strategy |
| 6.3 repeated facts | computed each count answer from its proportion twin | **certain**, arithmetic |
| 6.4 the ceiling | **a simulation.** A random number generator corrupted one in ten categories | **indicative only**, no model was run |
| 6.6 scoring comparison | the existing shortcut program, scored under both rules | **certain** as a comparison |

**6.4 is the only one produced by a random number generator rather than by counting something real.** Do not quote it as a measurement.

### 6.1 A defect, now fixed: the same question number in several datasets

Each dataset numbered its questions from scratch, so `tr-100000-0-q0` named three different questions:

| dataset | question | answer |
|---|---|---:|
| news | how many are tagged `aktuel`? | 13 |
| film reviews | how many are tagged `8 yıldız`? | 31 |
| complaints | how many are tagged `kişisel bakım ve kozmetik`? | 14 |

2,240 questions carried only 955 distinct numbers; 195 documents only 80. Within one dataset nothing was wrong, which is why every gate passed: all of them looked within one dataset. Combining the eleven, which is the ordinary way to use a benchmark with subsets, silently discards 57% of it with no error message. That happened during this review to a script analysing the benchmark.

**Fixed.** Every row now carries a name including its dataset, which cannot collide. The old numbers are untouched. The release check now verifies uniqueness across the whole benchmark, and was confirmed to catch a deliberately planted collision. **Nothing else changed:** the benchmark was rebuilt and compared field by field, and every question, answer, document and grade is identical.

### 6.2 A fifth shortcut moves 28 questions out of the hardest band

A reader that searches the text for category names and their component words, ignoring Turkish spelling marks, never classifying anything. Of the 215 hardest questions it can attempt, **28 leave the band**, mostly on the news and complaints sets where a category name such as `iletişim` genuinely appears in articles filed under it.

This is the predicted behaviour of grading against a declared set of strategies, now tested rather than left as a caveat. The eight sets shipping unmodified text are unaffected.

### 6.3 337 questions ask the same fact twice

For 337 combinations of document and category, the benchmark asks both "how many" and "what share". Working one answer out from the other succeeds at **0.97**, and for 16 questions graded among the hardest it works from an easier question in the same dataset.

It does not affect a model answering one question at a time. It matters if a harness puts all of a document's questions in one prompt, and it means **2,240 questions are not 2,240 pieces of evidence**: 674 of them cover 337 facts. Use the smaller number for any claim about statistical strength.

### 6.4 The realistic ceiling on the hardest questions

On the complaints and news sets a "wrong label" is not really the right idea: the complaints category is chosen by the person filing, and the news category is the section the article was printed in. Neither is an opinion about content, so neither can be mistaken. What varies is how easily that fact can be worked out from the text.

That was already being measured. A reader that opens every record but judges each correctly only nine times in ten scores:

| dataset | ordinary counting | rare-category counting |
|---|---:|---:|
| complaints | 0.82 | **0.38** |
| news | 0.86 | **0.58** |
| intent | 0.91 | **0.53** |

**Quote this as the ceiling.** Rare-category questions are demanding because small answers punish small error rates, not because the data is poor. Report results on that family against 0.38, not against a perfect 1.00, or it looks impossible when it is merely hard.

### 6.5 Checked and found clean

- **Word-search leakage in what ships**: none. 0 of 856,798 records contain a category name.
- **Repeated records inside a document**: none.
- **Published files versus local**: byte for byte identical.
- **All 2,240 answers**: recomputed by a separate route and matched.
- **Difficulty grades**: reproduced exactly after the rebuild.

### 6.6 Would OOLONG's own scoring remove the problem? Partly, and not where it matters

OOLONG scores a numeric answer by how exactly it matches, with almost no credit for being close. Measured on the real questions, the same 5% cheater beside an honest reader that opens everything and is right 99 times in 100:

| question type | OOLONG: cheat | OOLONG: honest | ours: cheat | ours: honest |
|---|---:|---:|---:|---:|
| counting | 0.17 | 0.61 | 0.80 | 0.98 |
| rare counting | 0.22 | 0.78 | 0.36 | 0.90 |
| **which is most common** | **0.96** | **1.00** | **0.96** | **1.00** |
| **comparing two categories** | **0.92** | **0.91** | **0.92** | **0.91** |

1. **On counting questions OOLONG's rule genuinely separates cheat from honest, by a wider margin than ours.** Concede this.
2. **On the three-category datasets it destroys the honest reader too.** A reader of all six thousand records, right 99 times in 100, scores **0.18**. Indistinguishable from doing nothing. That is why the second measure exists.
3. **Where the answer is a category name rather than a number, the choice makes no difference at all.** Six of the nine question types, 740 questions, a third of the benchmark. The cheater ties the honest reader.

**So:** changing the rule would help on counting, break the three-category datasets, and do nothing for a third of the benchmark. Reporting both rules plus the difficulty bands is the better answer.

### 6.7 The verdict

**The dataset is finished.** Construction is coherent, every answer is verified, limitations are measured rather than asserted, and the one defect an outside pass found is repaired and guarded against.

**Two things remain true and are not resolved by any of the above:** most questions are answerable from a sample, and two datasets contain almost no hard questions. Both are stated in section 0.

**One thing to report rather than fix:** the ceiling in 6.4. Quote it alongside any result on the hardest family.

## 7. Every number we chose, and the one-line reason

A reference table, because the reasons are spread across several documents and none of them is memorable on its own. Each row is a choice that could have gone differently. The last column says where the full argument lives.

### Choices about what makes a question hard

| choice | value | why this and not something else | where |
|---|---|---|---|
| rare-category band | answers of **5 to 30** | [5,50] was built and measured. It lets a reader who opens nothing score 0.11 instead of 0.00, and returns half the resistance. Below 5 the question becomes "find two records", which is searching, not counting. | datacard, D21b |
| the cheater's budget | **5%** of records | Roughly what a model with a code tool samples by itself. Graded at six budgets to show nothing was tuned: 1% would let us claim 771 hard questions instead of 259. | §5, PAPER_NOTES 9a |
| difficulty bands | very hard <0.35, hard <0.60, moderate <0.80 | Cut points on the cheater's score. 0.35 is where a cheater is clearly failing and 0.80 where it clearly wins. The middle two bands are unstable (half the "hard" questions could move) and should not be quoted separately. | §5 finding 9 |
| how a grade is computed | best of **four** cheaters, 200 random draws | A shortcut only has to work once, so the best result counts, not the average. 200 draws because a single draw on a small answer swings between 0 and 1. | §5 |
| smallest countable answer | **10** | Below this a count is retrieval rather than aggregation. Rare-category counts are the deliberate exception, for the reason in row 1. | D3, D21 |
| smallest ranking margin | **0.15** | Two categories within 15% of each other make "which is more common" a coin flip that no amount of reading settles. | D3 |

### Choices about the documents

| choice | value | why | where |
|---|---|---|---|
| separator between records | a **symbol**, not a word | A Turkish word like "KAYIT" appeared inside English documents and tokenizes differently per language, which corrupts a matched comparison. Symbols tokenize the same in both. | README §2.5 |
| brand marker | printed as **[[Brand]]** | Before v0.6.0 the brand existed only in a column the model never saw, so brand questions asked about something absent from the document. | D17 |
| category never printed | enforced by **dropping** records | Any record containing a category name is removed at build time. Verified: 0 of 856,798 shipped records contain one. | D1 |
| smallest category kept | **1,000 rows** | A category too small to sample is automatically the rarest in every document, so "which is least common" becomes answerable without reading. | D3 |
| length measured with | **Qwen3-8B** tokenizer | One tokenizer for every set, so lengths are comparable. Turkish costs more tokens than English for the same content, and that difference is a measurement, not an error. | README §13 |

### Choices about scoring

| choice | value | why | where |
|---|---|---|---|
| two metrics reported | `partial` and `relative` | `partial` is OOLONG's own formula, kept unchanged so results are comparable with it. `relative` was added because `partial` collapses at our answer sizes: on the three-category sets a reader who opens every record and is right 99 times out of 100 scores **0.18** under `partial`. | §6.6, scoring.py |
| scores reported as | **lift over the read-nothing floor** | A reader that opens nothing already scores about 0.5 on counting questions, so a raw score mostly measures the floor. | §5 finding 1 |
| reported as | **two bands and the gap**, never pooled | A pooled score over a question set that is 71.8% easy mostly measures whether the model reads Turkish. | §4, decision 4 |

### The three things that are open, and their status

| item | status |
|---|---|
| Most questions answerable from a sample | Measured, disclosed, and the reason the bands exist. Not fixable by wording. |
| Label accuracy on the complaints and news sets | Not measured. Bounded by the ceiling in §6.4, so it refines rather than blocks. Tool and samples ready. |
| No model has been run yet | Every cheater is a simulation and an upper bound. Whether a real model takes these shortcuts is the next experiment. |
