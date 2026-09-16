# TR-OOLONG — Week 4

*Updated 2026-09-16. Carries over the items the week 3 meeting ran out of time for. Sections 6 and 7 were added on the 16th; section 7 corrects a conclusion stated in section 6.*

---

## 0. Where the benchmark stands

Unchanged from week 3: **8 datasets · 110 documents · 1,254 questions · 28.3M tokens**, plus 3 experimental variants built but deliberately not shipped. Focus remains the dataset itself; evaluation runs are not scheduled yet.

**Published.** The dataset is public on Hugging Face and tagged `v0.6.3` on GitHub (16 September). The data has not changed since the first release; the revision corrects how the benchmark describes itself, after the check described in section 6.

**Three figures that are easy to quote wrongly, and the correct framing:**

- *"1,254 questions."* Correct as a count. As evidence it overstates: on the three-category review sets, the twelve questions on each document are largely the same two numbers asked in different ways. The unit of evidence is the document, 15 to 20 per set.
- *"The same question has the same answer in both languages."* 100 of 120 answers are identical character for character; the other 20 are the same fact written in each language's word ("rose" against "arttı"). All 120 are paired.
- *"Documents up to 1 million tokens."* True as a length. Under the proportional scoring rule, a longer document is not a harder one; see section 6.
- *"Ten question types."* Correct for the published version. One of the ten has been removed from the builder and will not appear in the next version; see section 7.
- *"A model forced to truncate the document does worse."* **Not supported.** A reader that spends the same budget on the two ends of the document rather than on its beginning loses almost nothing; see section 7.

---

## 1. Method questions

### If depth 2 is harmful, should depth never exceed 1? And does that make the method "just agents and sub-agents"?

**On not exceeding 1: yes, and nothing in the current plan changes.** Depth 1 was already the configuration in use, matching the original paper. The reproduction study simply confirms it was the right setting.

**On whether the method is therefore unremarkable: no, and this is worth being fair about.** What the method contributes is not the recursion. It is two things that do hold at depth 1:

- The document is never placed in a prompt. It is loaded into a programming environment as a variable, and the model writes code against it. This is what avoids degradation on very long inputs.
- The model decides how to break the document up, at run time, in code it writes itself — rather than following a splitting rule fixed in advance by a programmer.

Those produce the reported results, which are substantial: median improvements of 26% over context compaction, 130% over a coding-agent scaffold, and 13% over a commercial coding assistant, across four long-context tasks at comparable cost.

**On "depth 2 proves recursion is unnecessary": that overstates the evidence.** One reproduction tested depth 2 on two benchmarks with two models and found it degraded accuracy while inflating runtime roughly a hundredfold. That is good evidence it does not help *on those tasks*. It is not a general proof that recursion is useless. The defensible sentence is the factual one: *a reproduction found depth 2 degrades accuracy and inflates runtime from 3.6 to 344.5 seconds, so depth 1 is the configuration in use.*

### Does the method's paper contain an architecture figure?

**Yes.** Figure 2 shows it: the prompt is treated as part of the environment, loaded as a variable inside a programming environment, with the model writing code to inspect and decompose it.

A separate figure is still worth having for this work, because it needs to show something the original does not: the difference between one level of delegation and genuine nesting, and why the first is what actually runs. The existing diagram set covers that.

### Do the worker models each receive the same amount of context?

**No, and this turned out to be more interesting than expected.** The root writes the splitting code itself, so chunk sizes are decided per query by the model rather than fixed by the system. There is no uniform chunk size.

**The original authors report this becoming unstable with weaker models.** Their system prompt for the open-weight coding model differs from the frontier one by a single added line warning it not to make too many sub-calls — because without that warning, in their words, the model "will try to perform a subcall on everything, leading to thousands of LM subcalls for basic tasks." They also adjusted prompts for a smaller model whose context window is 32,000 tokens against the frontier model's 272,000.

**This is directly relevant to two planned research questions** — which models are capable enough to act as a root, and whether giving weak models explicit guidance helps. The original authors encountered exactly that problem and solved it with a prompt line. That is a finding to build on rather than rediscover.

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
- **Counting votes in a national election.** The national total is the sum of regional totals; each regional total is the sum of district totals; each district total is the sum of individual ballot boxes. Every level performs the same operation — add up what the level below reports.

**That last example is the clearest way to see what this method does and does not do.** Counting an election could be organised with many levels, or with a single one: every ballot box reports straight to the centre, and the centre adds them up. Both give the identical answer. The multi-level version only earns its place when a single centre cannot handle the number of reports arriving at once.

**The method as evaluated is the single-level version** — one centre, many boxes reporting directly. That works whenever the fan-out is manageable, which it is for documents of the sizes tested. It is the reason depth 1 suffices, and the reason a second level adds cost without adding capability.

---

## 2. Benchmark-design questions

### Is exploitation by string search a recognised problem in benchmarks, and is a sub-1% leak rate negligible?

**It is recognised, and it has a literature.** The general phenomenon is a model scoring well by exploiting a surface regularity rather than performing the intended task — studied as annotation artifacts, shortcut learning, and "right answers for the wrong reasons." The standard diagnostic is to run a deliberately impoverished solver that *cannot* do the real task and check it fails.

**On whether under 1% is negligible: this project's own evidence says firmly no.** An earlier version of the Turkish review data leaked its label in **0.84%** of records. A solver doing nothing but substring search scored **73%** on "which label is most common" against a chance rate of 33%. Under one percent of records was enough to determine the answer outright, because the leaks correlate with the quantity being asked about.

**So the rule to state is: leak rate does not predict exploitability.** A small, correlated leak can fully determine an aggregate. This is why leaking records are removed at build time rather than reported as a caveat — and why the shipped leak rate is zero rather than small.

For the Turkish-label variant, the 0.14% figure is the *cost* of the filter, not residual risk: those records are dropped, so what ships still leaks nothing.

### For a future training dataset built from solving trajectories, which benchmark should it be tested against?

**The reasoning is correct: not this one.** A model trained on trajectories from this benchmark and then tested on it would be scored on documents drawn from the same pool of records it trained on. Documents within a single length tier already share 21–39% of their records, so even a train/test split of documents does not separate them. The model could be rewarded for having memorised individual records rather than for learning to aggregate.

**Testing against the English benchmark this one is modelled on is the right instinct**, with one check to perform first: **confirm the source corpora do not overlap.** That benchmark is built from ten classification datasets, and at least one corpus considered here was identified as among them. If any shared source exists, that route is not clean either and the overlap must be stated.

**A stronger control is already available:** train on English review trajectories and test on the Turkish review sets. Those are genuinely different corpora — different text, different brands, different answers — so nothing transfers except the skill being claimed.

### If the dataset is published now, are permissions needed, can it be updated, and does it establish priority?

**No permissions are needed.** Every source licence is resolved. Seven of the eight sets can be redistributed as they are. The eighth cannot redistribute its text, so it ships as questions and answers only, with the text rebuilt locally by a script — a standard arrangement that requires no correspondence with anyone.

**Yes, it can be updated.** Dataset repositories on the intended platform are version-controlled, so corrections can be published later and any specific version can be cited by revision. This is already the recommended citation practice for this project: cite the tag, the version recorded in the manifest, and the source hash together.

**Yes, publishing establishes priority** — that is the main argument for doing it now rather than waiting for evaluation results.

**One caution on the wording of the claim.** "First Turkish long-context benchmark" is broader than what the evidence supports; Turkish long-context work does exist. The supported claim is narrower and still strong: **the first Turkish long-context *aggregation* benchmark**, and the first with a matched English twin built by an identical pipeline. Keep the qualifier.

---

## 3. A proposed experiment worth more than the one it replaces

**The idea:** rather than forcing a second level of decomposition, *offer* it — give the worker models the ability to decompose further if they judge it useful — and then measure how often they take it, comparing Turkish against English.

**This is unexplored, and better founded than the forced-depth experiment it replaces.** The original authors list adaptive depth explicitly as future work: letting the root decide whether a sub-answer is itself worth decomposing, instead of fixing depth in advance. The reproduction study tested *forced* depth 2, not *optional* depth 2. Nobody has measured what a model chooses when the choice is available.

**Why the cross-lingual version is the interesting one.** On the record-matched pair the same question has the same correct answer in both languages, so a difference in how often a model chooses to decompose further is attributable to the language rather than the task. That is the same design already proposed for a separate observation — whether models reach for shortcuts more readily in a language they handle less well.

**One caution on interpretation.** A choice to decompose further should not be read directly as low confidence. It may reflect the difficulty of the chunk, the phrasing of the prompt, or simple verbosity. It is a behavioural measurement, and it should be reported as what a model *does*, not as what it *believes*.

---

## 4. Open items

**Needs a decision:**

- ✅ Published on 15 September; corrected description published on the 16th.
- Whether the Turkish dictionary-form label variant replaces the current Turkish intent dataset or remains a side experiment.
- **Decision required before the first model run: how counting questions are scored and reported.** Section 6 explains why. The position this work takes: keep the scoring rule as it is, but report every counting score as improvement over the guess-without-reading floor, draw the reference readers (guess only, first 1,000 records, random 5%) as lines on every chart, and record separately how well the model classifies single records, so that reading coverage and classification quality can be told apart. This changes nothing that is frozen.

**Done since the last summary:**

- ✅ **The sampling shortcut detector is built and run** — and it found something material. See §5.
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

## 5. A fifth shortcut check was built, and it found a real limitation

The four existing checks all ask whether a question can be answered *without reading the document*. None asks whether it can be answered by reading only **part** of it. That gap is now closed, and the answer is uncomfortable.

**A model that reads a random 5% of a document and scales the result up scores 0.95 on counting questions** for the Turkish supplement set, against a baseline of 0.05 for always guessing the most common answer. On "which label is most common" for the e-commerce set it scores 0.99. In other words, for most question types, reading a twentieth of the document is nearly as good as reading all of it.

**Why.** The gap between the most and second-most common label is much wider than it needs to be — a median of 38% and 48% on the two review sets, against a required minimum of 10%. A small sample settles a 38% gap almost every time. The 48-category intent dataset has a median gap of 14% and is correspondingly harder to sample, which confirms the mechanism.

**One question type resists it**, and instructively so: the "is A more common than B, or equal" type, but only on the 48-category dataset, where its 2% "equal" band is narrower than sampling error can resolve. On the three-category sets that band never triggers and the resistance disappears.

**Three qualifications that must accompany this.**

1. **It is an upper bound, not a model result.** The checker is given the correct label of every record it samples. A real model would still have to read and judge them. It measures what a *perfect* reader of a fraction could achieve.
2. **It applies to the proportional scoring metric.** Under strict exact-match a sampled count of 1,712 against a true 1,600 scores zero. The question types where the two metrics coincide — all the ranking ones — are genuinely exposed.
3. **It is a consequence of scale.** A benchmark whose answers are single digits cannot be sampled at all. Ours can *because* its answers run to thousands. The large answers are not a difficulty advantage; they are what admits this shortcut.

**What this changes.** Ground truth is untouched — every answer remains exactly correct for its document. What narrows is the claim. This benchmark demonstrably requires *classifying Turkish records and combining them*; it does **not** demonstrably require reading all of them. Any statement that a model "must process every record" should be withdrawn.

**A fix exists for a future version.** The builder currently rejects questions whose deciding margin is too *narrow*. It should also reject those whose margin is too *wide*, since a 38% gap is free to a sampler. That uses machinery already present, but it changes the shipped questions and requires a rebuild, so it is not in this release.

**Recommendation: publish anyway, with this documented.** It is a limitation rather than an error, it was found by our own audit rather than by a reviewer, and a release that reports five shortcut checks including one that partly succeeds is more credible than one reporting four that all fail. The dataset is version-controlled, so the margin-band fix can ship as a later revision.

*Section 6 revisits this finding one day later, with a wider check. The 0.95 figure above stands, but the 0.05 it is compared against turns out to be the wrong comparison, and the margin-band fix turns out to help only some question types.*

---

## 6. The sampling check was a symptom. The scoring rule is the cause

A second, wider check was run on 16 September. Nothing in the data changed. What changed is the understanding of what a score on this benchmark can and cannot show, and the public description was corrected the same day.

### The scoring rule gives partial credit, and that is where everything below comes from

Counting questions ("how many of these 3,919 reviews are negative?") are scored proportionally: an answer of 1,600 against a true 1,650 earns about 97% credit, an answer of 800 earns about 48%. This rule was chosen because exact-match scoring is hopeless at these sizes; no reader lands on 1,650 exactly. The rule is sensible. Its consequences were not fully measured until now.

### Finding 1: a model that reads nothing already scores about half

Every document uses a fixed marker between records, so counting the records takes no reading. A model that counts the markers, divides by three (there are three categories) and answers that number for every counting question scores **0.43 to 0.63** depending on the set. That is the floor, and it is what a counting score must be measured against.

The week 3 comparison, "a 5% sample scores 0.95 against a baseline of 0.05", compared two different scoring rules. The 0.05 was strict exact-match; the 0.95 was proportional. Under the same rule the honest contrast is 0.92 against 0.63. The sampling finding stands, but it is a smaller gap than it looked.

The same mistake sat inside one of the four acceptance checks. The check that asks "can this be answered from general knowledge of the source corpus, without opening the document" scored the counting questions with the strict rule, where a guess can never hit the exact number, and so passed them automatically. It now scores them under both rules.

### Finding 2: under this rule, a longer document is not a harder document

An election analogy makes this concrete. A poll of 1,000 voters predicts a national result to within about three points whether the country has one million voters or eighty million. The error depends on how many people were asked, not on how many exist.

The same arithmetic holds here. A reader that classifies 1,000 randomly chosen records and scales up scores **0.94 to 0.97** on counting questions at every document length, from 100,000 tokens to one million. A reader that takes only the *first* 1,000 records, which is what any model with a limited window does by default when the document is longer than the window, scores 0.65 to 0.88 and degrades only mildly with length.

**What this means.** On the counting and proportion questions, which are 64% of the benchmark, a proportional score cannot tell a model that read 1,000 records from one that read 16,000. The length axis still tests something real, whether a model can take the document in at all without breaking, but it does not test whether the model aggregated over more of it.

### Finding 3: a single score cannot say whether a model read more or judged better

A perfect classifier that reads a random 5% of the document scores 0.89 to 0.92 on counting. A classifier that reads *every* record but misjudges one in ten scores 0.74 to 0.90. The two are indistinguishable from the score alone. This is why the position in section 4 asks for a separate measurement of how well the model classifies single records: once that is known, the aggregate score reveals how much was read.

### Finding 4: what actually resists sampling is a small answer, not a wide margin

Week 3 attributed the sampling exposure to the gap between the top two categories being too wide, and proposed rejecting questions with wide gaps. That mechanism is real for the ranking questions. It does nothing for counting and proportion questions, and those are most of the benchmark.

What does resist sampling is a question whose answer is small. "How many negative reviews does brand X have?" (answers of 10 to 50) is the most sampling-resistant question type shipped: a 5% sample scores only 0.24 to 0.35 on it. And counting questions about rare categories on the 48-category intent sets, which the current build deliberately excludes because their answers are under 30, score 0.29 at a 5% sample against 0.55 for the counts that ship. Every record still has to be judged to answer them ("is this one of the rare ones or not"), so they are genuine aggregation. Adding such questions is the main item planned for the next data version.

### Two smaller things found by the same check

- **The largest Turkish supplement documents look like their source.** A 750,000-token document uses 54% of the available reviews, so its mix of categories cannot drift far from the source's mix. A reader that knows the source's overall proportions and never opens the document scores 0.75 on counting at that length. The other seven sets stay at or below 0.60 at every length. That tier is now labelled as exposed.
- **The twelve questions on each three-category document are mostly the same two numbers.** Every document is asked "how many" for all three categories and "what percentage" for the same three; the "most common", "second most", "least common" and "is A more common than B" questions follow from those same numbers. For any statistical claim, the unit is the document, not the question.

### What was corrected on 16 September

1. The public dataset card, the datacard and the README now state the guess-without-reading floor, the flat length axis, the reading-versus-judging ambiguity, the exposed tier, and the question redundancy, with the numbers above.
2. The twin claim is stated the same way everywhere. It had been given as 100, as 110, and as "the other 20 are shift" in three different places.
3. Every data-fetching script now fixes the exact upstream version it downloads. Without this, if a source were changed upstream, the one dataset whose text is not redistributed (the English supplement reviews, for licence reasons) could no longer be rebuilt.
4. The acceptance check described under finding 1 scores counting questions under both rules.

### What this does and does not mean for the thesis

The data is sound and every answer is still exactly correct for its document. What narrows is the claim: the benchmark demonstrably requires *classifying Turkish records and combining the results*; it does not demonstrate that a model read the whole document, and under proportional scoring it does not demonstrate that longer was harder.

For the method under study this matters in one specific way. Its expected advantage is on documents a plain model cannot take in at once. That advantage will show against a model that is *truncated* (which degrades) but not against one that is allowed to *sample* (which does not). The evaluation must therefore state which the baseline is, and report scores as improvement over the guess floor.

---

## 7. The sampling check itself was incomplete, and a second benchmark was used to test that

Section 6 reported what a partial reader can score. Later on 16 September the check was found to be measuring only two of the four ways a reader can spend a limited budget, and correcting it removed a question type from the benchmark. A comparison against OOLONG, the English benchmark this one follows, was then run to establish whether the underlying problem is specific to this work.

### The rule that explains every number in sections 6 and 7

One quantity decides how well a partial reader does on a counting question: **how large the true answer is**. Not the length of the document, not the number of categories, not how the records are ordered. A reader that classifies a fraction of the records and scales up is doing what a pollster does, and its error follows the same arithmetic as a poll's margin of error.

The practical form: to answer "how many are negative" within a few percent, a reader needs to see a few hundred examples of that category. If the true answer is 2,000, a 5% sample already contains 100 of them and the estimate is close. If the true answer is 20, a 5% sample contains one, and the estimate is worthless.

This is why the counting questions on the three-category review sets are the weak ones. Their answers average 1,200 to 2,700. It is also why the 48-category intent sets hold up: their answers average 73 to 85, and there a 5% sample scores no better than guessing without reading.

### Finding 5: reading the two ends of a document costs the same as reading the beginning, and works far better

The check in section 6 modelled a reader that samples randomly across the document and a reader that reads it from the beginning until it runs out of room. The second reader is the one that stands for a model with a limited window, and it scored poorly, which was read as evidence that being forced to truncate is costly.

That conclusion was an artefact. Each document is built as two halves, each internally shuffled, with one category deliberately made more common in the second half. A reader confined to the beginning therefore sees a distorted sample, but only because its window sits inside one half. A reader that spends the *same* budget on the first fifty records and the last fifty records sees both halves and is not distorted at all. On the largest documents, the beginning-only reader scores 0.53 on counting while the two-ends reader on an identical budget scores 0.92.

**Consequence.** The statement "truncation degrades with length" has been withdrawn from the public description. Document ordering protects nothing: no arrangement of records defeats a reader that samples across the whole document, because sampling ignores order by construction.

### Finding 6: one question type was removed from the benchmark

One of the ten question types asked whether a category became more or less common in the second half of the document. Against the two-ends reader it is not a hard question: fifty records from each end answer it **perfectly on all eight datasets**, and correctly nine times in ten on a budget of a hundred records out of sixteen thousand.

The reason is that the question has only two possible answers and the change it asks about happens at a known point, so a reader that looks at each end reads the answer off directly. Widening the change, moving where it happens, or making it gradual would not help, because the question asks only for a direction.

This question type had already been flagged in week 3 as the weakest in the suite and was being reported as a disclosed limitation. That was the wrong response. It has been removed from the builder and will not appear in the next data version. It is still present in the published version, and any result on it should be discarded rather than explained.

**How it passed four separate checks.** Every difficulty rule in the builder constrains either how large an answer must be or how wide a margin must be at a boundary. Both are rules about *values*, and this question's answer is a direction, so it fell between them. The check that should have caught it could not: the only position-sensitive reader it modelled is unable to answer this question type at all, so the result table showed an empty cell, and an empty cell was read as "no reader could solve this" rather than "no reader tried". The check now reports, for every question type and every reader, what fraction of questions that reader could even attempt.

### Finding 7: the same measurement was run on OOLONG, and both benchmarks obey the same rule

The obvious question is whether any of this is specific to this benchmark or to Turkish. OOLONG's construction code is unreleased, but **its built data is public and includes the correct label of every record in every document**, so the same readers can be run on it directly with nothing reimplemented. All 41 of its test files were processed: eight source corpora, category counts of 2, 3, 4 and 10, documents from one thousand to four million tokens. A question was included only where a perfect reader of the whole document reproduces OOLONG's own published answer exactly, which held for 3,553 questions; 197 were dropped as unverifiable.

Its counting questions trace the entire rule:

| OOLONG's true answer | number of questions | score of a reader seeing 5% |
|---|---:|---:|
| 1 to 9 | 284 | **0.00** |
| 10 to 29 | 72 | 0.21 |
| 30 to 99 | 76 | 0.60 |
| 100 to 299 | 80 | 0.76 |
| 300 to 999 | 108 | 0.88 |
| 1,000 and above | 197 | 0.96 |

TR-OOLONG's own sets fall on the same line at the same answer sizes: the intent sets, with answers near 80, score 0.54 to 0.59, matching OOLONG's 30-to-99 band; the review sets, with answers above 1,000, score 0.89 to 0.92, matching OOLONG's top band.

**Three conclusions follow, and the order matters.**

1. The exposure is a property of counting over a large collection under a forgiving score. It was not introduced by this pipeline, this corpus, or this language.
2. **OOLONG is less exposed than TR-OOLONG, and the reason is instructive rather than embarrassing.** Most of its questions are restricted to a subset before being asked, such as "among the entries belonging to this one user" or "among the entries from April", which makes the answers small. 284 of its counting questions have answers below ten and score zero for every partial reader. TR-OOLONG currently has no questions in that range. Its most resistant question type of all, "how many dates appear exactly three times", scores 0.005 and depends entirely on having real dates.
3. **No published work on OOLONG reports either of these floors.** Neither the guess-without-reading floor described in section 6 nor any partial-reading measurement appears in its documentation, and results reported on it, including those of the method under study, are therefore not separated into how much was read and how well it was judged. On OOLONG's largest question type, 1,097 comparison questions, a reader classifying a random 5% of records scores 0.78 under OOLONG's own strict scoring.

**How to state it.** Not "OOLONG has the same problem, so ours is acceptable". The defensible statement is: this is a measurable property of the task family; it was measured here on both benchmarks; OOLONG mitigates it by restricting questions to subsets; the next version of TR-OOLONG adopts the same mitigation.

### Does strict scoring solve it?

Partly, and not in the way it first appears. Under strict exact-match, a partial reader scores essentially zero on counting questions, on both benchmarks. But two things spoil it as a remedy.

First, six of the nine remaining question types are answered with a category name rather than a number, and those are *already* scored by exact match. A reader seeing 5% of the records answers them correctly 78 to 100 percent of the time. Strict scoring does nothing for them, on either benchmark.

Second, strict scoring does not only defeat the partial reader, it defeats everyone. A reader that opens every one of 6,469 records and misjudges only one in a hundred scores **0.015** on counting. Under strict scoring a near-perfect full reader and a 5% sampler are indistinguishable, because both score zero. That is why the proportional rule exists.

### Finding 8: the first fix is built, and it removes the guess-without-reading floor entirely

The change described above as the main item for the next data version has been built and measured. It adds counting questions about **rare categories**: categories holding between five and thirty records in that particular document. The question is worded exactly like any other counting question, so a model is not told that the answer happens to be small.

Measured on one of the intent datasets, rebuilt into a scratch folder so nothing published was touched:

| | a reader that opens nothing | a reader seeing 5% | a reader seeing 25% |
|---|---:|---:|---:|
| ordinary counting question (typical answer 74) | 0.458 | 0.535 | 0.805 |
| **rare-category question** (answers 5 to 30) | **0.000** | **0.268** | 0.646 |

**The first column is the more important result.** Section 6 reported that a model which opens nothing, counts the record separators and divides by the number of categories already scores about 0.46. Against a rare-category question that same model scores **zero**, because dividing by the number of categories gives roughly 62 when the true answer is 20. The guess floor is not reduced, it is removed. Partial reading also roughly halves.

A wider band of five to fifty was built and measured as well, because the narrow band yields few questions on the longer documents. It was rejected: it lets the guess-without-reading score back up to 0.114 and returns half the resistance. The narrow band stays, and the family simply produces fewer questions on longer documents, which the builder reports.

**What it does not reach.** The two three-category review datasets without a brand column cannot host this question type at all: with three categories over several thousand records, no category is ever that small, and they have no second axis to narrow by. Their counting questions remain the most exposed in the suite. This is a property of a three-category label space, not something question wording can repair, and it should be stated that way rather than implying the fix is general.

### What this changes about the plan

The next data version was already going to add counting questions about rare categories. The measurements above make that the central change rather than one of six, and add a second: questions restricted to a subset before being asked, which is available immediately on the two supplement-review sets because they already carry a brand for every record.

**Decision required.** The one thing that cannot be built from the current sources is a date. Dates would supply subset-restriction for free and would enable the single most sampling-resistant question type observed in either benchmark. No Turkish source examined so far carries them. The planned search for an additional Turkish corpus is currently specified as "ten or more categories"; it is worth respecifying as "ten or more categories **and a usable date on every record**", since the second property is worth more than the first.

