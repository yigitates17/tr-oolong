# Week 2 — talking points

**Hold this while you present.** `W2_Summary.md` is the document; this is how to
say it out loud. Each entry is a place the wording is easy to get backwards.

---

## The eight easy mistakes

### 1. Label translation — the direction is the opposite of what it feels like

| ❌ Don't say | ✅ Say |
|---|---|
| *"Translating labels to Turkish is free and makes it more grep-proof."* | *"Translating **creates** leakage. It costs us about 1% of the data."* |

**Why:** today leakage is **0%** *because* the labels are English — a Turkish
sentence can't contain `alarm_set`. Translate to `alarm_kur` and the sentence
*"iki saat sonrasına **alarm kur**"* now contains its own answer.

> **Turkish is verb-final**, so a `noun_verb` label matches natural Turkish
> exactly. English never does — nobody writes "alarm set."

**Numbers:** TR text vs TR labels = **0.91%** (137 rows deleted). EN text vs EN
labels = **0.00%**.

**Verdict:** worth doing, but say the cost.

---

### 2. The bug — what was actually missing

| ❌ Don't say | ✅ Say |
|---|---|
| *"We didn't put the answers in the haystack."* | *"The answer was computable from our data, but not from what the model could see."* |

**Why:** we never put answers in *any* haystack — that's the design. The brand was
in a **metadata column** we had; it just never reached the text.

**One-liner:** *"We asked how many 'Venatura' reviews were neutral — answer 10 —
but the word 'Venatura' appeared zero times in the document."*

---

### 3. Intents are LABELS, not entities

| ❌ Don't say | ✅ Say |
|---|---|
| *"Entities are brands, intents, etc."* | *"Labels are what we count — sentiment **or** intent. Brands are our only entity."* |

The intent sets have **no usable entity axis at all** — `scenario` is nested
inside `intent`, so grouping by it is either trivial or impossible.

---

### 4. The re-check is the SAME 150 rows

| ❌ Don't say | ✅ Say |
|---|---|
| *"I'll annotate another 150 rows."* | *"I'll re-judge the same 150 with **two** columns."* |

**Why:** new rows just re-measure the same combined number with fresh sampling
error. Two columns — *does the label fit the English?* / *does it fit the
Turkish?* — **separate translation errors from labelling errors**, which is the
actual open question.

**And if he asks "how will you make the noise minimal?":**

> *"We can't reduce it — it's in the source data, upstream of us. We measure it
> and bound its consequence. Ranking questions are almost immune to label noise;
> raw counts are not. So headline results go on ranking families."*

---

### 5. What the literature validates — and what it doesn't

| ❌ Don't say | ✅ Say |
|---|---|
| *"Aggregation fine-tuning is validated."* | *"The family of approaches works. Nobody has done **aggregation** trajectories, in any language."* |

- **π²** trained on table-based multi-hop reasoning → +4.3%
- **RLM-Qwen3-8B** trained on recursion trajectories → +28.3%
- **Neither is aggregation.** That gap is still ours.

---

### 6. "Long context" is not just length

| ❌ Don't say | ✅ Say |
|---|---|
| *"Long context basically means a lot of tokens."* | *"Length is necessary but not enough. What matters is **how much of it you must read**."* |

A 1-million-token needle hunt is **easy** — just search. Ours is hard because
**every record must be processed**. Same length, completely different difficulty.

---

### 7. Fewer tokens does not damage the dataset

| ❌ Don't say | ✅ Say |
|---|---|
| *"OpenAI's tokenizer would make our dataset smaller — is that bad?"* | *"Same text either way. If we rebuild to the same target we fit **~10% more Turkish reviews** — a **harder** task."* |

**And "what if we test Claude, OpenAI and Qwen?"** — that isn't a problem:

> *"The tokenizer only defines how long a document is. We pick one, name it,
> report it. The text is then fixed, and each model consumes it however it does."*

---

### 8. We didn't "fix" the long-comment correlation

| ❌ Don't say | ✅ Say |
|---|---|
| *"We handled the length correlation."* | *"We **measured** it. What matters is the gap between the two halves of a pair, not either half's level."* |

On Amazon the **positive** reviews are the longer ones — the direction is a
property of the website, not human nature. Its spread is 1.1×, very mild, and the
twin gap is **0.020**. Nothing needed fixing.

---

## Questions he might ask

**"Why not do the legal cross-reference problem?"**

> *"Three reasons. Our records are independent — shuffle our document and every
> answer is unchanged; shuffle a legal document and it's destroyed. Ours is a bag,
> that's a chain. Second, the correct answers would need a lawyer to mark which
> reference resolves to what, which destroys the thing that makes this work —
> answers that are free and exact at a million tokens. Third, no Turkish legal
> corpus with resolved references exists."*

It is **not** RAG. RAG is retrieval; that's multi-hop reasoning over linked
passages.

**"Should we switch to OpenAI's tokenizer since it's newest?"**

> *"Only if we switch to evaluating GPT models. Match the ruler to what you test.
> It's already a config parameter — a one-line change plus a rebuild."*

**"Does your compatibility tool check class imbalance?"**

> *"Yes — normalised entropy on each side, the gap between them, and the max/min
> class ratio. A set where one class holds 90% fails it."*

**"Is it harder than OOLONG?"**

> *"Harder on three measurable things: 48 categories against their 2–10, documents
> to 988,000 tokens, and counts in the thousands where theirs are single digits —
> which actually broke their scoring formula, so we added a second one. But
> nobody has run a model on ours yet, so I won't claim it's harder overall."*

---

## Numbers worth memorising

| | |
|---|---|
| Documents / questions / tokens | **110 / 1,254 / 28.3M** |
| Turkish vs English questions | **630 / 624** |
| Question types | **10** |
| Longest document | **988,000 tokens** (~2,000 pages) |
| The bug | **118 questions, 9.7%** |
| Label noise | **9.3%**, range 2.7–9.3% |
| Turkish token cost | **1.34×** under Qwen, **1.22×** under OpenAI |
| Automatic checks | **5, all passing** |

---

## If you only say three things

1. **I found a serious bug in my own work and fixed it** — 118 questions, one in
   ten, were impossible to answer. Four automatic checks missed it because they
   all asked *"is this too easy?"* and none asked *"is this possible?"*
2. **I found something more interesting while checking the data by hand** — some
   of our Turkish came from translated English, and idioms broke. *"Put a record
   on"* became *"place a document in a filing cabinet."* That's a real weakness in
   the comparison, and I wrote it down rather than hiding it.
3. **The dataset is finished and could be published tomorrow.** The only thing
   missing is running an AI system on it, and that needs hardware I don't have yet.
