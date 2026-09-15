# TR-OOLONG — Week 4

*Updated 2026-09-15. Carries over the items the week 3 meeting ran out of time for.*

---

## 0. Where the benchmark stands

Unchanged from week 3: **8 datasets · 110 documents · 1,254 questions · 28.3M tokens**, plus 3 experimental variants built but deliberately not shipped. Focus remains the dataset itself; evaluation runs are not scheduled yet.

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

- Whether to publish the dataset now. Unchanged recommendation: yes.
- Whether the Turkish dictionary-form label variant replaces the current Turkish intent dataset or remains a side experiment.

**Can be done now, no model required:**

- The 150-row re-check separating translation errors from annotation errors.
- A shortcut detector for sampling-and-extrapolating.
- The entity-mention audit.
- Recording the brand-based question types as long-document-only in the datacard.
- The build-time source-pool partition, required before any trajectory data is used for training.
- Confirming whether any source corpus is shared with the English benchmark, which determines whether it is a clean transfer target.

**Queued for evaluation:**

- A retrieval baseline.
- The optional-decomposition experiment described in §3.

**Blocked on data:**

- The positional-shift question type, pending a Turkish corpus with real dates.
