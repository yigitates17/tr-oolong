# Advisor questions — status and answers

Five questions, checked against the repo 2026-08-25.
**Two are fully answered, one is partly answered, two were not started.**

| # | question | status |
|---|---|---|
| 1 | Label noise rates, can we check them ourselves? | ✅ **done 2026-09-04** — **ε = 9.3%, n=150, 95% CI [5.6%, 15.1%]**; second review puts the defensible range at [2.7%, 9.3%]. Part of it is *mistranslation*, not misannotation, and that part is asymmetric across the twin — see `DATACARD.md` |
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
| ~~airline / We-Bears~~ | crowd annotation / **undocumented** | **both withdrawn 2026-08-30** — the We-Bears provenance problem is the one defect filtering cannot fix |

For a star-derived set there is no annotator to disagree with. The benchmark asks
"how many records carry label X", and that is exact. What varies is the
*relationship* between a star and the sentiment expressed — but the benchmark
never asks about sentiment.

**✅ Settled 2026-09-04: ε is measured.** A native speaker judged 150
pair-aligned MASSIVE rows (`scripts/make_noise_slice.py` to generate,
`scripts/annotate_noise.py` to annotate). **14 of 150 rejected → ε = 9.3%,
95% Wilson CI [5.6%, 15.1%].** A second review overturned 3 of the 14 as correct
per the corpus's own use of `calendar_query` / `email_querycontact`, so the
defensible range is **[2.7%, 9.3%]**, point estimate ~7.3%.

**⚠️ And the more important half of the result: some of it is mistranslation,
not misannotation.** MASSIVE localizes English SLURP utterances, so a label can
be right for the English and wrong for the Turkish that ships — *"put a record
on"* → *"bir kayıt koy"*, labelled `play_music`, where Turkish `kayıt` is a
clerical record and no reader infers music. **This lands on one half of the twin
only**, so the Turkish half is scored against noisier ground truth than the
English half on records that are supposed to be identical — a direct confound for
the cross-lingual claim. The review axis is unaffected (natively written Turkish,
writer's own star as the label).

**Open:** a two-column re-pass over the same 150 rows — does the label fit the
English, does it fit the Turkish, judged separately — to split translation noise
from annotation noise. ~30 minutes.

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

**No. There is no OOLONG-fine-tuned model.** Nobody has trained a model on OOLONG
data, and nobody has trained one on TR-OOLONG either, because it does not exist
yet. What exists is a *precedent from adjacent work*, and the distinction matters
because it is exactly what an advisor will probe.

### What has actually been done, and by whom

| work | trained on what | result |
|---|---|---|
| Xiong et al., *From Artificial Needles to Real Haystacks* (ICLR 2025) | **synthetic key-value retrieval** — made-up dictionaries like `{"2a8b": "9f1c", …}`, then "what is the value of key 2a8b?" | Fine-tuned GPT-3.5-Turbo and Mistral-7B improved **+10.5%** on a *real* long-context QA benchmark they never trained on. General benchmarks stayed flat, while other long-context augmentation data caused hallucination |
| Zhang, Kraska & Khattab (2026) | 1,000 **recursion trajectories** distilled from a 480B coder, on LongBenchPro tasks | Produced `rlm-qwen3-8b-v0.1`, +28.3% over its base model |
| Kim & Ahmad (2026) | **evidence-selection trajectories** over scientific papers, one shared policy for parent and child roles | A 4B model reached rubric 0.600 against Claude Sonnet's 0.607, at 7 s/query versus 60+ s |

Nobody in that table trained on an aggregation benchmark. Xiong is the closest,
and their task is *retrieval*, not aggregation.

### Why that gap matters

OOLONG's own headline result is that **giving models the gold labels for free
improves scores only 0.79–10.9 points.** The bottleneck is not reading each item,
it is combining thousands of them. So the skill TR-OOLONG would train is
arithmetic-over-many-items, and there is no published evidence that skill
transfers the way retrieval does.

There is also a reason to think training it directly is the wrong move.
Counting 3,919 records is what a `for` loop does perfectly and what next-token
prediction does badly. The entire recursive-language-model literature exists
because *offloading to code* beats doing it in-context. Fine-tuning a model to
count in its head may be optimising the component that should have been replaced.

### The version worth proposing to your advisor

Do not train on **question → answer**. Train on **question → decomposition**.

Concretely, one training example would not be:

> *Bu yorumlardan kaç tanesi 'olumlu' etiketli?* → `1735`

but rather the trajectory that produces it:

> *Bu yorumlardan kaç tanesi 'olumlu' etiketli?*
> → `chunks = split(ctx, 2000)`
> → for each chunk, ask a child: *"how many of these are olumlu?"*
> → `sum(child_answers)` → `1735`

The first target teaches a model to guess a number. The second teaches
**planning**, which is the same shape as chain-of-thought and is the thing that
plausibly transfers. It is also exactly what Kim & Ahmad did, and it worked at 4B.

TR-OOLONG can generate those trajectories mechanically, because the ground truth
is computed by code that already decomposes the problem. That is a real asset:
**the benchmark can emit its own training supervision at zero annotation cost.**

### How to frame it in the thesis

As **future work with a concrete design**, not as a claim. The honest statement:

> The benchmark is constructed so that ground truth is computed by an explicit
> decomposition. That makes it a source not only of evaluation items but of
> *decomposition trajectories*, which prior work suggests are the effective
> training signal for recursive scaffolds (Kim & Ahmad, 2026). Whether such
> training transfers to Turkish long-context tasks generally is an open question
> this resource makes answerable for the first time.

That paragraph is defensible, it is interesting, and it does not overclaim.

**What it would take to actually run it:** a training-capable GPU, a held-out
*real* Turkish long-context evaluation (which does not exist — building one is
itself a contribution), and a control separating "the model got better at
Turkish" from "the model got better at aggregating."

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

### Honest assessment — revised 2026-08-30

**My earlier answer assumed the wrong experiment, and the correction matters.**

I originally said compute is not the binding constraint, because the thesis as
scoped runs on a single 16 GB GPU and a public reproduction already ran this
paradigm on a 6 GB laptop GPU. That reasoning holds **only for inference with
small models**.

If the plan is to evaluate **4B, 30B and larger** models, the picture inverts:

| model size | what it needs to serve | fits 16 GB V100? |
|---|---|---|
| 4B | ~8 GB at bf16, ~3 GB at Q4 | yes, comfortably |
| 8B | ~16 GB at bf16, ~5 GB at Q4 | Q4 only, tight with KV cache |
| 30B | ~60 GB at bf16, ~18 GB at Q4 | **no** |
| 70B+ | ~140 GB at bf16, ~40 GB at Q4 | **no** |

And long-context makes it worse than the parameter count suggests: **KV cache
grows linearly with context**, so a 500K-token haystack costs many GB on top of
the weights. That is the actual wall, and it arrives well before 30B.

**So yes, apply — and the case is stronger than a generic one.** A proposal that
says "evaluate a size ladder from 4B to 30B+ on a released long-context benchmark
at up to 1M tokens" is concrete, has a clear resource estimate, and produces a
result (the capability-versus-size curve) that is useful to others. That is
exactly what Development Access exists for.

**Three practical notes:**

1. **A size ladder is a much better experiment than one big model.** "At what
   size does aggregation over 500K tokens become possible" is a finding; "model X
   scored Y" is a data point. Frame the application around the ladder.
2. **Estimate node-hours from a pilot.** Run the 4B rung locally first, measure
   wall-clock per question, and extrapolate. Reviewers of HPC proposals notice
   whether the resource estimate was computed or guessed.
3. **Do not wait on it to start.** The 4B and 8B rungs run on your V100 today,
   and they produce the baselines the benchmark currently lacks — which is the
   single biggest gap in the project. Apply in parallel; do not treat the
   application as a prerequisite.

**Sequencing that makes both work:** run the 4B/8B rungs locally now → those
numbers become the pilot data in the application → Development Access covers the
30B+ rungs → if the fine-tuning question in §4 is pursued, that is a second
application with a much stronger case behind it.
