# TR-OOLONG — Week 3

*Updated 2026-09-15.*

> **Methodology diagrams** — how the recursion works, why it runs at depth 1, and how it compares to divide-and-conquer and to multi-hop retrieval:
> **https://claude.ai/code/artifact/468f8d1e-f38c-4fd6-aaac-bbc46561056d**

---

## 0. Where the benchmark stands

| | |
|---|---|
| **Official / publishable** | **8 datasets · 110 documents · 1,254 questions · 28.3M tokens** (unchanged) |
| **Built but deliberately not shipped** | 3 experimental variants · 30 documents · 360 questions |
| **Publishable?** | Yes, unchanged from Week 2 |
| **Current focus** | The dataset itself. Evaluation runs are not scheduled for the next two weeks |

**Is 8 datasets / 1,254 questions still the correct figure?** Yes, for what ships. Three Turkish-label experiments (§2) are built and on disk, which would make 11 datasets and 1,614 questions if everything were counted. They are excluded from the official figure deliberately.

There is also a reason beyond bookkeeping not to fold them in. Those variants are not new data — they are the *same Turkish sentences* as the existing intent dataset with the category names rewritten. Adding them to the headline would count the same underlying text twice and overstate the benchmark's size. They are an ablation, not a ninth dataset. If one is ever adopted, it should *replace* the existing Turkish intent set rather than be added alongside it.

Week 3 covered the questions raised in discussion (§1 and §2), one experiment arising from the label-leakage question, and a documentation audit that caught two errors.

---

## 1. Methodology questions

### Does the method run its sub-calls in parallel?

Checked against both the paper and the released library, because the two differ. The paper's own experiments run sub-calls **one at a time and blocking** — the lack of asynchrony is named there as the reason a single query can take minutes. The **published library does support parallel batched sub-calls**, bounded by a configurable limit on how many run at once.

The practical consequence: our experiments should use the parallel path. The chunks are independent, so concurrency changes wall-clock time only, never the answers.

### Is the method genuinely recursive, or is it root → child → root?

**This objection is correct, and conceding it is a stronger position than defending the name.** In the original paper's experiments the children are ordinary language models: they answer about their chunk and stop. Nothing calls itself. The authors state this directly:

> *"in our experiments we only consider a recursive depth of 1 — i.e. the root LM can only call LMs, not other RLMs."*

What makes the name defensible is the interface. A sub-call takes a prompt and returns an answer, which is exactly what the whole system does, so a child *can* be replaced by a full copy of the system with its own environment, nesting without limit. The library supports this. But it is a capability, not what gets run. A separate reproduction study (Wang, 2026) found that going to depth 2 makes accuracy worse and runtime roughly a hundred times longer, so depth 1 is also the right practical choice.

**How to state it:** recursive in design, depth 1 in practice. The setup evaluated here is one level of divide-and-conquer, and the recursion should not be oversold beyond that.

**The plainest description of what the paper actually runs is an agent with sub-agents.** A root model receives the question and orchestrates; a set of worker models each handle one piece and report back; the root combines what they return. That is the sub-agent pattern, and describing it that way is both accurate and immediately recognisable. It also makes the naming question answer itself, since sub-agents are not recursion.

Two refinements keep that description precise. First, **the workers are not merely restricted — they were never given the option.** At depth 1 the environment exposes no facility for a worker to spawn its own workers, so the model could not have recursed had it been useful. The judgement that one level suffices was the authors', made in advance, and they scope it explicitly to "most modern long context benchmarks." Second, **the root is not blind.** It cannot see the whole document, but it can print slices of it and read short excerpts back, so it works from samples and summaries rather than from nothing.

### How does this compare to divide-and-conquer?

Divide-and-conquer breaks a problem into smaller problems of the same kind, solves each, and combines the results. Merge sort is the textbook case: to sort a list, sort each half, then merge. The defining feature is that "solve each" means *applying the same procedure again*, repeatedly, until the pieces are trivial.

This method performs the first and third steps identically but not the middle one: it splits once, hands each piece to a plain model that cannot split further, and combines. That shape has its own established name — **map-reduce**.

Two differences are worth claiming as genuinely novel:

- **The split is decided at runtime.** In classic divide-and-conquer the programmer fixes the splitting strategy when the algorithm is written. Here the model writes the chunking code itself and can vary it per question.
- **The sub-problems are independent**, which is what permits the concurrency described above.

### Is there an established way to categorise long-context tasks, or is ours invented?

There is an established one, and it is close enough to use directly rather than proposing our own. **RULER** (NVIDIA, arXiv:2404.06654) defines **four task categories across thirteen tasks**: retrieval (needle-in-a-haystack), multi-hop tracing (variable tracking), **aggregation**, and question answering. So "aggregation" is not a category invented here — it is a recognised class of long-context task with a published definition behind it.

**The useful part is what fills that category.** RULER's two aggregation tasks are *common words extraction* and *frequent words extraction*: the model finds the most frequently occurring words in synthetic text. That is string-level counting. Nothing has to be understood, only matched and tallied. ONERULER, the nearest multilingual benchmark, has the same shape — its aggregation tasks are most-frequent-word extraction.

**So the category exists and is respectable, and every published instance of it is lexical.** This benchmark's questions require deciding what each record *means* before it can be counted — a sentiment or an intent that is nowhere written in the text. Same category name, different task underneath.

That is a cleaner way to state the contribution than claiming a new taxonomy: *we adopt RULER's category and fill it with latent-label aggregation rather than word counting.*

**One caution on how to phrase it.** Avoid "there are exactly four kinds of long-context task" — a closed list invites counterexamples, and RULER's four are not strictly parallel. The claim that actually carries the argument is a single axis: **how much of the document must be read before the question can be answered?** Needle retrieval needs one passage, multi-hop needs a few linked ones, aggregation needs all of them. That axis is hard to argue with and is the only part the design depends on.

### Could these tasks be solved by multi-hop reasoning instead?

Multi-hop reasoning chains a few facts together — "who directed the film she starred in?" requires finding the film, then the director. It works by *narrowing*: score the pieces of a document, keep the best few, reason over those.

**Narrowing is precisely the wrong operation for an aggregation question.** A counting question has no small subset that determines the answer; every record contributes. A retrieval system that keeps the best 10 chunks out of 400 and counts within them returns a figure roughly 40 times too small. It does not fail by being imprecise — it fails by answering a different question.

So the two are not competitors; they suit different task shapes. Multi-hop and retrieval methods address questions answerable from a small subset, and this benchmark is built specifically around questions that are not. Put at its shortest: **multi-hop succeeds by narrowing, and these questions cannot be narrowed — no subset of the document determines the answer, so discarding any part of it discards part of the answer.**

**A retrieval baseline is nonetheless worth running, precisely because it should fail predictably.** A result of the form "retrieval-based methods undercount by roughly 30x, and the gap widens as the document grows" is a genuine finding, and the clearest available evidence that this benchmark measures something existing tools do not handle. It costs little — same questions, same scorer, no new data — and it addresses the objection before a reviewer raises it. Added to the experiment plan.

### How the original authors scoped their own experiments

Worth setting out plainly, because it frames what follows as filling gaps the authors disclosed rather than as criticism of their work.

Four restrictions, all stated openly in the paper:

- **Recursion depth fixed at one level.** As above, the root was given no way to call another copy of the system.
- **Sub-calls run one at a time.** The absence of parallelism is named as the reason a single query can take minutes.
- **A strong model at the root, a cheaper one for the pieces.** This was an engineering choice, not a variable they varied and measured.
- **English only.** Every task evaluated is English.

And three things they name as not yet attempted: deeper recursion (described as "a relatively easy change"), parallel dispatch ("the obvious next implementation step"), and *adaptive* depth — letting the model decide for itself, case by case, whether a piece is worth breaking down further.

**The position this work takes.** Restricting an architecture is normal and correct practice, and these authors disclosed their restrictions rather than obscuring them. The one criticism that lands is narrow and about naming only: the title claims a capability the experiments do not exercise. This work should not lead with that. It should instead state its own restrictions with the same explicitness — depth 1, a single reference tokenizer, a frozen scoring metric, no fine-tuning — because the failure to avoid is not restricting the design, it is claiming more than the restriction supports.

### On whether larger correct answers make this benchmark harder

This benchmark's counting answers run to the thousands where OOLONG's are single digits, and it is tempting to read that as evidence of greater difficulty. **It is not, and under one of the three scoring metrics used here it points the other way.**

Consider a model that is off by two records. Against a correct answer of 4, that is a 50% error. Against a correct answer of 1,046, it is a 0.2% error. Under the scale-free metric — the one intended to carry the counting results — **large correct answers are systematically more forgiving, not less.** Under strict exact-match they are considerably harsher, since thousands of individual judgements must all be right. So the direction of the claim depends entirely on which metric is quoted.

What is defensibly harder here, and should carry the claim instead, are three properties of the task rather than of the answer:

- **How many records must be classified** — up to 22,259 per document, against tens.
- **Document length** — 36,000 to 988,000 tokens, against a reporting range of 8,000 to 128,000.
- **How many categories** — 48 against 2 to 10.

All three describe coverage and confusability, which is what actually makes aggregation difficult. Answer magnitude describes the output, and interacts with the scorer rather than with the task.

**This also exposes a gap in the existing quality checks.** Large answers make a strategy viable that small ones do not: classify a random sample of the records and scale the result up. Reading roughly a tenth of a document would land within about 10% of the right answer — which under the scale-free metric could score better than an honest full pass by a weak model. That would undercut the central claim that these questions force a model to process every record. The four existing shortcut detectors cannot see this, because none of them samples the document. Adding a fifth that does is now on the list (§4). **Nothing here has been measured yet — this is an arithmetic argument, not a result.**

---

## 2. Dataset and tooling questions

### Can a single row carry more than one entity?

No, and this was verified in the pipeline rather than assumed. Every record carries exactly one product/brand and one label. Where a source dataset tags a record with two categories at once, the pipeline discards that row — this removed over a third of one corpus that was rejected for other reasons as well.

One gap remains unmeasured: a review may still *mention* a competitor's brand in its text ("better than Brand X") while being filed under a different brand. This does not affect correctness, since the ground truth comes from the metadata column rather than the text, but the frequency has not been measured.

### If the model's solving steps are logged, what can be claimed from them?

The plan is to log every step taken while solving a question, in both languages, and retain only the runs that reached the correct final answer. That becomes a second, reusable dataset.

What can honestly be claimed: it would teach a future model the general skill of decomposing a large problem into steps, with the secondary benefit that the material being processed is real Turkish. What should not be claimed: that it would make a model broadly "better at Turkish," or that gains would be large — the closest comparable English result was a few percentage points, not a dramatic improvement.

No training is performed in this study; this remains a documented design for future work. Any resulting model should also be tested against the *original* English OOLONG benchmark, not only this one, to establish that an improvement is not an artifact specific to this data.

**One correction to the plan as previously recorded.** Earlier notes proposed training on English trajectories and testing on Turkish, described as leak-free because the two languages are matched twins. That reasoning is inverted and the design would not survive review. On the record-matched pair the two languages contain the same sentences in the same order with the same labels, and 100 of 120 questions share an identical correct answer — so training on the English side reveals the answer to the Turkish question, and a model could score well without reading Turkish at all.

The control is still available, but it has to run on the **review datasets** instead, where the Turkish and English halves are genuinely different corpora with different text and different answers. The general lesson is worth stating in the paper: *the property that makes a matched twin the best evaluation control — identical answers in both languages, which is what permits paired statistical testing — is the same property that makes it unusable as a training control.*

### Turkish label leakage — is this simply how language works?

No. It follows from Turkish sentence structure specifically, where the verb falls at the end, and is not a general property of languages.

Measured directly. Translating the category codes into natural Turkish commands ("play music" → *müzik çal*) causes the category name to appear verbatim inside the text it is meant to be hidden from, in **3.1%** of records. Using the dictionary form of the same words (*müzik çalmak*) reduces this to **0.14%** — twenty times cheaper, with identical meaning.

This is retained as an experiment and not added to the official datasets. Whether to adopt it remains open (§4).

### Why this benchmark is built with the Qwen tokenizer, and whether to rebuild with a newer one

Worth having a settled answer, because it is an easy question to ask and an easy one to answer badly.

**Two defensible reasons, and one that must not be given.**

The defensible ones: the tokenizer should match the model family the benchmark is actually evaluated on, and the reproducible core here is open-weight models rather than hosted ones. And it must be open and work offline — Anthropic publishes no tokenizer at all, only a counting service over the network, so building with it would make the build depend on a company's server and stop being reproducible offline.

**The reason not to give is that it makes the token counts larger.** Choosing a measuring instrument because it produces a bigger headline number is indefensible, and a reviewer would rightly attack it. The larger counts are a *consequence* of the choice, never a reason for it. The better move is to state the opposite proactively: under OpenAI's current tokenizer the same Turkish documents measure about 10% shorter, and the paper should say so rather than wait to be asked.

**Should the dataset be rebuilt with a newer tokenizer?** There is no strong case for it.

- Rebuilding to the same targets would fit roughly 10% more Turkish reviews per document, which is genuinely harder — but it invalidates every figure already recorded, forces a full rebuild, and requires re-running every quality check.
- Simply relabelling the existing documents makes them *look* smaller for no gain at all.
- Most importantly, **the problem is already solved without rebuilding.** Every document records its character count alongside its token count, so any reader can re-derive lengths under whichever tokenizer they care about. That is the real answer to "why this one?" — the choice does not need to be universally correct, it needs to be named and reversible.

The position: *the tokenizer defines only how long a document is. One is chosen, named, and reported; character counts are recorded so anyone can convert.*

### Does Mistral publish a tokenizer?

Yes, and it was added to the comparison. Mistral's tokenizer is public and works offline, as is the case for several other vendors. Re-running the Turkish-versus-English token-cost measurement with it reproduces the existing pattern: Mistral's older tokenizer makes Turkish look expensive, its current one does not. Two vendors now show the same generational trend independently, which is stronger evidence than one.

### Is a separate checking tool needed for Turkish-only contributions?

Yes, and it is built. The existing tool screens a *pair* of datasets for cross-lingual comparability, which a contributor offering a single Turkish dataset cannot use. The new tool checks one dataset on its own: whether it has labels at all (failing immediately, with a stated reason, if not), whether the labels or text are declared as machine-generated or synthetic, whether the licence permits publication, and whether it clears the same quality gates the existing datasets clear.

### A constraint on the brand-based questions that had not been written down

Found while testing an unrelated idea. The three question types that group reviews by brand are not evenly available across document lengths:

| Document length | Turkish set (count / most-of-label / head-to-head) | English set |
|---|---|---|
| 100,000 tokens | 5 / **0** / 5 | 4 / **0** / **0** |
| 250,000 | 5 / 2 / 5 | 5 / **0** / 5 |
| 500,000 | 5 / 5 / 5 | 5 / 3 / 5 |
| 750,000 – 1M | 5 / 5 / 5 | 5 / 5 / 5 |

**This is the quality gate behaving correctly, not a fault in the data.** A question like "which of these brands received the most negative reviews" is only meaningful if each brand has enough reviews that the answer does not rest on a one-review margin. Short documents do not contain enough reviews per brand to meet that bar, so the builder declines to generate the question. An earlier version of this project did ship such questions, and they were found to be decided by as few as 8 reviews out of 3,919 — which is why the bar exists.

Two things do follow from it, though:

- **The brand-based questions are effectively 500,000-token-and-above question types**, and nothing in the documentation said so. They are now recorded as such.
- **At the shortest length the two languages are not comparable on these question types** — the Turkish set has five head-to-head questions there and the English set has none, because the English review corpus averages about 1.4 reviews per brand at that length against roughly 15 for the Turkish one. Results for these question types should not be compared across languages at 100,000 tokens, and any chart of accuracy against document length needs to state which question types exist at each length.

One genuine shortcoming sits behind this: the automatic warning for a question type producing nothing checks each dataset as a whole rather than each length, so it stayed silent while a type was absent at two of four lengths. Making that check per-length is a small fix and is now on the list.

**The tempting fix should be avoided.** Lowering the minimum-reviews-per-brand bar would make these questions appear at the shortest length, at the cost of reintroducing exactly the one-review-margin problem the bar was added to remove. The current behaviour is preferable to that.

---

## 3. Issues found and corrected

1. **An unqualified claim in two documents.** Both stated "Turkish costs 30% more tokens" without naming which vendor's tokenizer produced that figure. Since the number inverts depending on the tokenizer used (§2), this is exactly the kind of claim a reviewer would challenge. Corrected in both places.
2. **The build now reports question-type availability per document length.** Prompted by the constraint described in §1: the existing warning fired once per document with no indication of which length it referred to, so a question type missing only from the short documents produced a wall of identical messages and read as a fault affecting everything. The build now prints one grouped summary instead, naming which types are absent at which lengths and stating that this means length-gating rather than breakage. Output files are unchanged — this is diagnostic reporting only.

3. **A near-miss with the new experimental files.** The three Turkish-label variants were stored alongside the eight official datasets. Any "build everything" or "publish everything" command would have swept them into the official release unnoticed. They have been moved to a separate directory.

---

## 4. Open items

**Current focus is the dataset itself.** Model runs are not planned for the next two weeks, so the items below are ordered by what can be done without them.

**Needs a decision, not more analysis:**

- **Whether to publish the dataset now.** Carried over from week 2, still undecided. It is finished, every check passes, nothing in the licensing blocks it, and a release timestamp establishes priority at no cost. The recommendation is unchanged.
- **Whether the Turkish dictionary-form label variant (§2) replaces the current Turkish intent dataset, or stays a side experiment.**

**Can be done now, no model or GPU required:**

- **The 150-row re-check**, separating translation errors from annotation errors — roughly 30 minutes of annotation by a native speaker.
- **A fifth shortcut detector**, testing whether a model can sample a fraction of the records and extrapolate rather than reading all of them (§1).
- **An entity-mention audit** — how often a review names a brand other than the one it is filed under (§2).
- **Record the brand-based question types as 500,000-token-and-above** in the datacard (§1).
- **The build-time source-pool partition**, which must exist before any trajectory data is used for training (§2).

**Queued for whenever evaluation begins:**

- A retrieval baseline, and a second-level-decomposition run (both §1). Neither is urgent.

**Blocked on data, not effort:**

- **The positional-shift question type** remains the weakest family, pending a Turkish corpus carrying real dates. None examined so far has them.

*The full experiment queue, with rationale and cost for each item, is recorded in `PAPER_NOTES.md` §11.*
- **Decision required:** whether the Turkish dictionary-form label variant (§2) should replace the current Turkish intent dataset, or remain a side experiment permanently.
