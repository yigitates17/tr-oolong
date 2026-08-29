# Advisor questions — status and answers

Five questions, checked against the repo 2026-08-25.
**Two are fully answered, one is partly answered, two were not started.**

| # | question | status |
|---|---|---|
| 1 | Label noise rates, can we check them ourselves? | ⚠️ **half** — consequence bounded and protocol written; **the rate itself is not measured** |
| 2 | OOLONG question types, difficulty vs OOLONG | ✅ **done** — `COMPARISON.md` |
| 3 | OOLONG vs TR-OOLONG comparison table | ✅ **done** — `COMPARISON.md` |
| 4 | What if an LLM were fine-tuned on this? Uses beyond benchmarking? | ❌ **was not started** — answered below |
| 5 | Barcelona Supercomputing Center application | ❌ **was not started** — answered below |

---

## 1. Label noise — what is settled and what is not

**Settled: the consequence.** Label noise does not make an answer wrong (ground
truth is the label, and a count over labels is exact). What it does is cap the
score a semantically perfect model could reach, and that cap is
**family-dependent**. Under OOLONG's `0.75^|y-ŷ|` with symmetric flips at rate ε:

| family | ε=2% | ε=5% | ε=10% |
|---|---|---|---|
| `count`, N=3,919 | 0.36 | 0.25 | 0.19 |
| `proportion` (percent) | — | 0.95 | 0.92 |
| ranking families | P(flip) < 1e-6 at every ε tested | | |

So ranking and `proportion` carry headline results and `count` is read through
the scale-free `relative` metric. Full table in `DATACARD.md`.

**Also settled: most of our labels are not annotations at all.** This reframes
the question and is worth saying to the advisor directly:

| source | label is… | classical noise? |
|---|---|---|
| `vitamins_tr`, `musteri_tr`, `marc_en`, `amazon_hpc_en` | **the writer's own star rating** | **~0 by construction** — the label is a recorded fact about the record, not an estimate of a latent truth |
| MASSIVE (`tr_intent`/`en_intent`) | professional annotation | low, unmeasured |
| `en_twin` (airline) | crowd annotation | measurable: **17.1%** of duplicate-text rows carry conflicting labels |
| `tr_oolong` (We-Bears) | **undocumented provenance** | unknown and unknowable |

For a star-derived set there is no annotator to disagree with. The benchmark asks
"how many records carry label X", and that is exact. What varies is the
*relationship* between a star and the sentiment expressed — but the benchmark
never asks about sentiment.

**Not settled: the rate ε on the annotated sets.** The protocol is written and
the slices are generated (`*_out/label_noise_slice.csv`, 200 rows each).
**n = 400 per corpus gives ±3 points at ε ≈ 0.10.** This needs a Turkish speaker
reading rows; no code closes it. Roughly 4–5 hours across the annotated sources.

---

## 2 & 3. OOLONG question types, difficulty, comparison table

**Done — `COMPARISON.md`.** Written for a reader with no access to the code. It
contains both benchmarks' haystack formats, questions quoted verbatim from each,
per-set token statistics, and a scorecard in both directions.

The framing that makes it legible: **OOLONG's design is task types × conditioning
axes** — the same question shapes asked over everything, over a user subset, and
over a date subset. We match their counting group, replace the user axis with a
richer entity axis (real brands, prior-neutral candidates, plus ordered ranking),
add normalised proportions, and **lack their timeline axis entirely**.

**Difficulty, honestly, in both directions.**

Harder here: label space **48** against their 2–10; haystacks to **987K tokens
and 22,259 records** against a reporting focus at 128K; counts large enough that
their metric degenerates (median `count` near 1,000, so `0.75^50 ≈ 6e-7`), which
is why `relative` was added.

Easier here: **the timeline axis**, which their paper reports as their hardest
group. Ours is one binary rose/fell over positional halves. It is also the only
family our format solver beats. This is the honest deficit and it is blocked on
data — no Turkish source examined carries dates.

---

## 4. Fine-tuning on this data — would it help? Other uses?

Not started before; here is the answer.

### Would fine-tuning on TR-OOLONG improve Turkish long-context ability?

**There is a positive precedent, and it is close to this case.** Xiong et al.,
*From Artificial Needles to Real Haystacks* (ICLR 2025), fine-tune GPT-3.5-Turbo
and Mistral-7B on a **synthetic numerical key-value retrieval** task and report
transfer to *real* long-context benchmarks — +10.5% on MDQA at 20 documents.
Critically they also report that general-benchmark performance stays flat, while
other long-context augmentation data **encouraged hallucination**. So synthetic,
mechanically-generated long-context data can transfer without the usual damage.

**Two caveats specific to us, and they are real.**

1. **Their task is retrieval; ours is aggregation.** OOLONG's own result is that
   giving models the gold labels for free improves scores only marginally — the
   bottleneck is the *aggregation*, not the per-item classification. So the skill
   being trained here is arithmetic-over-many-items, which is plausibly harder to
   instil than "find the needle" and has no published transfer result.
2. **Aggregation may be a tool-use problem, not a weights problem.** Counting
   3,919 items is exactly what code does well and what next-token prediction does
   badly. The recursive-language-model literature exists precisely because
   offloading to a REPL beats asking the model to do it in-context. Fine-tuning a
   model to count in its head may be optimising the wrong component.

**The genuinely interesting version of the question**, and the one worth putting
in the thesis: **does training on TR-OOLONG teach decomposition rather than
counting?** Kim & Ahmad (2026) train 4B models into native recursive language
models using one shared policy for parent and child roles. If TR-OOLONG
trajectories were used the same way — not "predict the count" but "predict the
decomposition that produces the count" — the target skill is planning, which is
much more like chain-of-thought and much more likely to transfer.

**Honest assessment: this is a follow-up paper, not part of this thesis.** It
needs training compute, a held-out real Turkish long-context evaluation (which
does not exist yet — that is partly what TR-OOLONG is for), and a control for
whether gains come from Turkish exposure rather than from aggregation skill. But
it is a strong "future work" paragraph and a good answer to "why does this
dataset matter beyond a leaderboard."

### Uses beyond benchmarking

1. **Diagnostic for tokenizer choice on Turkish.** We already have the finding
   that the TR/EN token ratio runs 0.57×–2.16× across tokenizers. The pipeline
   measures this on aligned content and generalises to any language pair.
2. **A test-bed for aggregation scaffolds** — chunking strategies, map-reduce
   prompting, RAG-with-counting — independent of recursive language models. The
   benchmark is method-agnostic, which is also its scoop protection.
3. **Training data for the recursive scaffold specifically** (the decomposition
   framing above).
4. **A construct-validity methodology other benchmark builders can reuse.** The
   four solvers and the "audit built questions, not the source pool" finding are
   transferable to any label-derived benchmark in any language.
5. **A recipe for other languages.** The code is language-agnostic; steps 1–2 of
   the pipeline (find two corpora matched on task, label provenance, record
   length and surface shape) are the entire difficulty, and that is documented.

---

## 5. Barcelona Supercomputing Center — can we apply?

Not started before; here is what I found.

### The important finding: apply through EuroHPC, not RES

**RES** (Red Española de Supercomputación) is the Spanish national network. It
allocates MareNostrum time but is oriented to Spanish-affiliated researchers, and
its next HPC deadline is **15 September 2026, 11:00 CET**.

**EuroHPC JU** is the European route to the same machine (MareNostrum 5 is a
EuroHPC system), and **Türkiye is explicitly listed as an eligible country.** The
eligibility list names: *"Albania, Armenia, Austria, … Tunisia, Türkiye, Ukraine,
United Kingdom."* Türkiye has been associated to Horizon Europe since 2021 and is
a EuroHPC JU participating state.

### Which access mode to apply for

| mode | for | allocation | deadlines | time to access |
|---|---|---|---|---|
| **Development** | developing, testing and optimising applications, **including AI methods** | small node-hours, **1 year** | **monthly**, 1st of each month | **~2 weeks** |
| **Benchmark** | scalability tests, testing AI applications | small | monthly | fast |
| Regular | production science | large | periodic cut-offs | months |
| Extreme Scale | very large production | very large | periodic | months |

**Development Access is the right target.** It is explicitly for developing and
optimising AI applications, the allocation runs a year, cut-offs are monthly, and
time-to-access is about two weeks. That fits a thesis timeline in a way Regular
Access does not, and the proposal burden is far lower.

### Steps

1. **Talk to NCC Türkiye first** (`eurocc.truba.gov.tr`), the national competence
   centre under EuroCC. They exist to help national applicants and will review a
   draft. This is free help and the highest-value first step.
2. **Check TRUBA** (the Turkish national HPC) in parallel. For a single-GPU
   inference workload it may be faster than any European route, and it does not
   compete with a EuroHPC application.
3. **Register on the EuroHPC access portal**, pick Development Access, and submit
   before a monthly cut-off.
4. **Proposal needs:** a PI (this normally means the **advisor**, not the MSc
   student), a technical description of the code and its scaling behaviour, and a
   resource estimate in node-hours.
5. **Confirm current terms before writing.** Call conditions and deadlines change;
   the figures above were checked 2026-08-25.

### Honest assessment of whether it is worth it

**Probably not on the critical path, and here is why.** The thesis as scoped runs
on a single 16 GB GPU, and a public reproduction has already run this paradigm on
a 6 GB laptop GPU. The binding constraint on this project is **not compute** — it
is (a) that no model has been run yet, and (b) unmeasured label noise. Neither is
solved by a supercomputer.

**Where it would genuinely help:** if the fine-tuning question in §4 is pursued.
Training even a 4B model into a recursive scaffold is a real compute job, and
that is exactly what Development Access is for. So the sensible sequencing is
**answer §4 first as a research question, then apply if the answer is yes** —
with the added benefit that a proposal citing a released benchmark and a
concrete training plan is far stronger than one citing an intention.
