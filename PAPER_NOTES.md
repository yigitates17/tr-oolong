# Claims to carry into the paper

Findings that are measured, defensible, and easy to lose track of between
sessions. Each says what the number is, where it came from, and what it is good
for in a write-up.

---

## ⚠️ 1. THE MORPHOLOGY TAX IS A TOKENIZER ARTIFACT — DO NOT WRITE THE OLD CLAIM

**Never write "Turkish costs 1.30–1.34x the tokens of English" without naming the
tokenizer.** Measured on the same 3,000 pair-aligned MASSIVE utterances:

| tokenizer | TR tokens | EN tokens | TR/EN |
|---|---|---|---|
| GPT-2 | 45,970 | 21,278 | **2.16x** |
| Qwen3-8B | 31,767 | 20,824 | 1.53x |
| mBERT cased | 30,887 | 23,904 | 1.29x |
| **BERTurk** (`dbmdz/bert-base-turkish-cased`) | 19,418 | 34,265 | **0.57x** |

Under a Turkish-native tokenizer Turkish uses **43% fewer** tokens than English
for identical content. The ratio does not measure agglutination; it measures how
much Turkish was in the tokenizer's training data.

**How to write it instead.** Three moves, all of which strengthen the paper:

1. Call it the **tokenization penalty a given model pays on Turkish**. That is a
   real, consequential property *of the model*, and it is what actually costs
   money and context window in practice.
2. **Report the ratio for every tokenizer used in the evaluation.** The 0.57x–2.16x
   spread is itself a finding, and it does not appear to have been reported for
   Turkish long-context work. It is a small, self-contained contribution.
3. **Anchor the cross-lingual claim on the record-matched regime**, which is
   already built. There TR and EN contain the same utterances with the same gold
   answers, so any accuracy gap carries no token-budget confound at all. The
   token-matched regime becomes a secondary analysis answering a different
   question ("at equal cost") rather than the headline.

**Why this matters more than it looks.** The thesis mechanism as currently
written is "Turkish is agglutinative → more meaning per token → recursive
compression degrades faster." If the token cost inverts with the tokenizer, that
mechanism is not a property of the language. An examiner who knows tokenization
asks this in the first five minutes.

**Status: NOT YET APPLIED** to the README's §4 morphology paragraph, to
`thesis_proposal_revised.md`, or to the `.tex`. All three still carry the old
claim.

---


### NEW 2026-09-07 — the generational trend, and it is the better claim

Measured on the same 3,000 pair-aligned MASSIVE utterances, across three
generations of OpenAI tokenizer (`tiktoken`, open source, free, offline):

| tokenizer | generation | TR/EN |
|---|---|---|
| `p50k_base` | GPT-3 | **2.16×** |
| `cl100k_base` | GPT-3.5 / GPT-4 | **1.73×** |
| `o200k_base` | GPT-4o / GPT-5 | **1.35×** |

**The penalty halves across generations of the same vendor.** That is much
stronger evidence than the cross-vendor spread alone: it is the same organisation,
the same language pair, the same sentences — only the training diet changed.

**Write it as:** *"the Turkish token penalty is a property of the tokenizer's
training data, not of Turkish morphology; it fell from 2.16× to 1.35× across three
generations of OpenAI tokenizer and reverses entirely (0.57×) under a
Turkish-specific one."* That is a small, self-contained, defensible finding.

**Measured on the built haystacks, not just the source utterances** (2026-09-07).
On the record-matched pair, which holds the *same 3,000 utterances* in both
languages, the penalty is **1.34x under Qwen3-8B and 1.22x under `o200k_base`**.
Per-language re-measurement of identical text: Turkish falls to **91%** of its
Qwen count, English to **99%**. So the choice of reference tokenizer moves the
headline cross-lingual number by 12 points, and shifts Turkish roughly five times
more than English. **Any paper sentence quoting a TR/EN token ratio must name the
tokenizer in the same sentence.**

**On tokenizer choice, for the methods section:** we build with Qwen3-8B because it
is the family evaluated and it is open and offline. OpenAI's `tiktoken` is equally
usable (free, open) and is what the table above uses. **Anthropic publishes no
tokenizer** — only a network token-counting endpoint — so it cannot be a build
dependency without making the build unreproducible offline. We record `n_chars`
per haystack so any reader can re-derive lengths under their own tokenizer.

## 2. Source-level shortcut measurements do not predict question-level ones

This is the strongest methodological finding in the project and it has a
controlled experiment behind it.

The Turkish brand-review corpus has a **+0.120** surface-format shortcut at the
source-pool level against its English twin's **+0.017** — a 7x asymmetry. That
looks fatal for a cross-lingual comparison. A full replacement pair was built and
gate-tested on the strength of that number, and the question-level twin asymmetry
moved from **0.108 to 0.106**, i.e. not at all. Prior-randomised sampling absorbs
the source-level signal.

**Use it as:** a methods-section warning other benchmark builders can act on.
"Audit the built questions, not the source pool" is a transferable rule, and the
before/after numbers make it concrete rather than hand-wavy.

---

## 3. The four-solver audit is a contribution independent of Turkish

Each solver exists because a specific version of the benchmark was solvable by
it. That provenance is what makes the section persuasive.

| solver | what it caught |
|---|---|
| leakage | 0.84% leaking records gave a substring solver **73%** on `most_common` against 33% chance |
| majority baseline | a `least_common` family with a majority baseline of **1.00** (same gold answer in 10/10 haystacks) |
| corpus-prior oracle | `pairwise` answerable with **no context at all** (1.00 on `vitamins_tr`), and getting *worse* with length |
| surface format | the label recoverable from length and punctuation alone; caught the `shift` family |

OOLONG reports no such audit. **Use it as:** the construct-validity section, and
argue the methodology generalises to any label-derived benchmark.

---

## 4. Label-derived ground truth has a per-family noise ceiling

Under OOLONG's `0.75^|y-ŷ|` with symmetric label flips at rate ε, a semantically
perfect oracle scores:

| family | ε=2% | ε=5% | ε=10% |
|---|---|---|---|
| `count`, N=3,919 | 0.36 | 0.25 | 0.19 |
| `proportion` (percent) | — | 0.95 | 0.92 |
| ranking families | P(flip) < 1e-6 at every ε tested | | |

**Use it as:** the justification for which families carry headline results, and
as a reusable argument. Any label-derived aggregation benchmark inherits this,
and nobody seems to have written it down.

---

## ⚠️ 5. THE LEAKAGE-ASYMMETRY CLAIM IS WITHDRAWN — DO NOT WRITE IT

**The old claim was:** English surface text contains its own intent label in
0.68% of MASSIVE utterances against Turkish's 0.00%, read as Turkish morphology
hiding labels where English gives them away.

**It does not survive.** Two independent problems:

1. **It is not in the shipped build.** Both intent sets record
   `label_leakage_rate: 0.0`. The 0.68% came from a 16,521-row pool; the pool
   that ships is 15,075 and leaks nothing on either side.
2. **It was confounded even when it held.** Both locales are matched against the
   *English* label vocabulary (`play_music`), so a Turkish utterance cannot
   contain a label form regardless of its morphology. 0.00% was a tautology about
   language mismatch, not a finding about Turkish.

**What is actually true, measured on the same 15,075 aligned utterances:**

| | leak rate |
|---|---|
| EN text vs English labels (`alarm_set`) | **0.00%** |
| TR text vs Turkish labels (`alarm_kur`) | **0.91%** (137) |

**And the cause is word order, not morphology.** Turkish is verb-final, so a
`noun_verb` label name reproduces the natural phrase ("iki saat sonrasına **alarm
kur**"); English `verb_noun` labels never surface, because nobody writes "alarm
set". If anything the direction is the opposite of what was claimed.

**Usable version, if it is worth including at all:** a note that label-leakage
audits are sensitive to the language the label vocabulary is written in, so a
cross-lingual benchmark must state which vocabulary it matched against. That is
methodological, small, and defensible. The morphology story is not.

---

## 5b. MASSIVE label noise is measured — and part of it is mistranslation (2026-09-04)

**ε = 9.3%** on a 150-row pair-aligned slice, 95% Wilson CI **[5.6%, 15.1%]**,
judged by a native speaker. A second review overturned 3 of the 14 rejections, so
the defensible range is **[2.7%, 9.3%]** with ~7.3% the point estimate. Report the
range; the disagreement is part of the result.

**The part worth a paragraph in the paper:** some of it is *translation* error,
not annotation error. MASSIVE localizes English SLURP utterances, and the label
can be right for the English while wrong for the Turkish that ships — *"put a
record on"* → *"bir kayıt koy"*, labelled `play_music`, where Turkish `kayıt` is
a clerical record and no reader infers music.

**This is asymmetric, and that is the problem.** It lands on the Turkish half
only, so a Turkish model is scored against noisier ground truth than its English
twin on records that are supposed to be identical. Any TR−EN gap on the intent
axis is therefore (language effect) + (translation noise), and we have not
separated the two.

**Do not claim** a clean cross-lingual difference on the intent axis without this
caveat. **Do claim** the review axis is free of it — `vitamins_tr` and
`musteri_tr` are natively written Turkish with the writer's own star as the
label, so there is no translation step to corrupt. The fix is a two-column
protocol (does the label fit the English / does it fit the Turkish) over the same
150 rows.

---

## 6. `shift` is style-solvable and should not carry a headline

The only family the format solver beats: **+0.400** (`amazon_hpc_en`), **+0.300**
(`vitamins_tr`), **+0.267** (`musteri_tr`, `marc_en`), +0.100 (`en_intent`). Highest majority baseline in the
suite (mean 0.61, up to 0.73).

**Use it as:** an honest limitation, paired with the explanation (length
correlates with label, and with position once drift is injected) and the fix
(a real dated timeline axis, blocked on finding a dated Turkish corpus).

---

## 7. The derived length ceiling

`R_max = smallest_class × K` records. With *K* classes a haystack of *R* records
gives each class about *R/K*, so a class can top a ranking only if the pool can
supply more than that. Exceeding the ceiling silently makes ranking families
unanswerable.

**Use it as:** a small reusable piece of benchmark-construction reasoning. It is
the kind of detail reviewers cite approvingly.

---

## 8. The benchmark can emit its own training data — a future-work angle worth claiming

**No OOLONG-fine-tuned model exists.** Nobody has trained on OOLONG, and the
adjacent precedents trained on something else: Xiong et al. (ICLR 2025) on
synthetic key-value *retrieval* (+10.5% transfer to real long-context QA, with
general benchmarks flat where other augmentation caused hallucination); Zhang et
al. (2026) on 1,000 recursion trajectories; Kim & Ahmad (2026) on
evidence-selection trajectories, reaching Claude-Sonnet-level rubric scores at 4B.

**The claim available to us, which none of them can make:** because ground truth
here is computed by an explicit decomposition (chunk → classify → aggregate), the
benchmark can emit **decomposition trajectories**, not just question–answer
pairs, at zero annotation cost. Training on *question → decomposition* targets
planning; training on *question → answer* targets guessing a number. Kim & Ahmad
show the former works at 4B.

**Write it as future work with a design, never as a result:**

> The benchmark is constructed so that ground truth is computed by an explicit
> decomposition. That makes it a source not only of evaluation items but of
> decomposition trajectories, which prior work suggests are the effective
> training signal for recursive scaffolds. Whether such training transfers to
> Turkish long-context tasks generally is an open question this resource makes
> answerable for the first time.

**The caveat that must accompany it:** OOLONG's own result is that supplying gold
labels improves scores only 0.79–10.9 points, so the bottleneck is aggregation
rather than classification — and aggregation over thousands of items may be a
tool-use problem rather than a weights problem. Counting is what a `for` loop
does perfectly and what next-token prediction does badly.

---

## 8a. ⚠️ RELATED WORK THAT LANDED AFTER WE DESIGNED THIS — cite it, do not ignore it

**π²: Structure-Originated Reasoning Data Improves Long-Context Reasoning Ability
of Large Language Models** (arXiv:2604.05114, 2026).

**What they do:** harvest Wikipedia tables → auto-generate multi-hop analytical
questions over them → **verify each answer by dual-path code execution** →
back-translate step-by-step solution traces → fine-tune. Reports **+4.3% and
+2.7%** average accuracy on long-context benchmarks, plus a **+4.4%**
self-distillation gain. English-only. Code, data and models open-sourced.

**Why this is the closest work to our §8/§8b proposal, and closer than anything in
the RLM literature:**

| | π² | this work |
|---|---|---|
| ground-truth source | structured Wikipedia tables | labelled classification corpora |
| answer verification | **dual-path code execution** | **dual-path, asserted equal** — the same idea, arrived at independently |
| training signal | step-by-step solution traces | decomposition trajectories |
| language | English | **Turkish + record-matched English** |
| intermediate-step verification | ❌ final answer only | ✅ every record's label is known, so any chunk boundary can be checked |
| artifact is primarily | training data | **an evaluation benchmark** that can also emit training data |

**Three consequences for how we write:**

1. **The dual-path ground truth is no longer a distinctive method claim.** π² does
   the same thing. Keep it as a correctness guarantee, drop it as novelty.
2. **Stop implying the trajectory idea is unexplored.** It is published and it
   works. The honest claim is *first in Turkish*, *first from an aggregation
   benchmark*, and *first with verifiable intermediate steps* — that last one is
   the strongest and is genuinely ours.
3. **Anchor expectations at ~+4%, not +28.3%.** The RLM-Qwen3-8B figure came from a
   different training regime. Quoting +28% for our proposal would be overselling.

---

## 8b. FUTURE WORK — the two-release plan

**The idea, and it is a good one: this project can produce two datasets, not one.**

| | release 1 — the benchmark | release 2 — the trajectories |
|---|---|---|
| when | now, before any model runs | after the evaluation |
| what | 1,254 questions over 110 haystacks, gold answers derived from labels | the decompositions that produced those answers, plus what models actually did |
| contains | context, question, answer | `split → classify per chunk → aggregate` traces; per-node inputs, outputs, timings, errors |
| purpose | **evaluation** | **training and error analysis** |
| generated by | the builder | the builder (gold traces) and the evaluation harness (model traces) |

**Why this is worth doing rather than just appealing.**

1. **The gold traces cost nothing.** The builder already computes every answer by
   an explicit decomposition — chunk, classify, sum. That decomposition is
   currently thrown away. Emitting it turns a by-product into an artifact.
2. **It is the training signal the literature says works.** Kim & Ahmad (2026)
   trained 4B models into recursive scaffolds on trajectories, reaching
   Claude-Sonnet-level rubric scores at 7 s/query against 60+. They trained on
   evidence-selection traces. Nobody has published aggregation traces, in any
   language.
3. **It separates two questions that are currently tangled.** Training on
   *question → answer* teaches a model to guess a number, which is probably
   pointless (OOLONG's own result: gold labels help only 0.79–10.9 points, so the
   bottleneck is aggregation, and aggregation is what a `for` loop does
   perfectly). Training on *question → decomposition* teaches planning, which is
   chain-of-thought shaped and plausibly transfers. **Release 2 makes that
   comparison runnable; release 1 alone does not.**
4. **Model traces are an error-analysis dataset in their own right.** Where does
   a model's decomposition diverge from the gold one — wrong chunk size, wrong
   per-chunk classification, correct parts summed wrongly? That is a paper.

**The honest caveats, which belong in the write-up:**

- The gold decomposition is *a* correct decomposition, not the only one. Training
  a model to imitate one strategy may teach the strategy rather than the skill.
- Release 2 depends on release 1 having been evaluated, so it cannot ship first.
- Whether trajectory training transfers to *Turkish* specifically, rather than to
  aggregation generally, needs a control — the same training in English, measured
  the same way.

**Sequencing:** release 1 now (it is finished and gated); run the evaluation;
release 2 with the paper that analyses it. Two artifacts, two citable objects,
and the second is the one that answers "what is this for beyond a leaderboard."

---

## 8c. OOLONG's code status, verified 2026-09-07

Their repository (`github.com/abertsch72/oolong`, MIT) **now exists** and contains
an evaluation script (`src/eval/eval_script_batched.py`). **The construction
pipeline is still unreleased** — the README marks oolong-synth construction,
oolong-real construction, scoring, validated splits and analysis scripts as
"coming soon".

**So the claim to write is precise, not blanket:** *"OOLONG's benchmark
construction code was unreleased at the time of writing; we reimplemented the
construction principle, the counting typology and the numeric metric from the
paper's published description."* Do not write "no code is available" — an eval
script is. Re-check at submission time.

---

## 9. Headline numbers, current

8 sets · 110 haystacks · **1,254 questions** · **28.3M tokens** ·
36,250–987,623 tokens per haystack · label spaces 3 and 48 · **10 question
families** · 2 languages · 4 acceptance gates · byte-identical rebuilds.

Twin asymmetries (lower is cleaner, v0.6.0 build): `musteri_tr`↔`marc_en` **0.030** ·
`vitamins_tr`↔`amazon_hpc_en` **0.020** · intent record-matched **0.014** ·
intent token-matched **0.028**. **Every shipping pair is at or under 0.030**; the
pair that sat at 0.108 was withdrawn in v0.5.0.

---

## 9b. The entity bug, and what it means for the construct-validity claim (v0.6.0)

**Report it, do not hide it.** Until v0.6.0 all 118 entity questions were
unanswerable: the brand was never printed. The finding that generalises beyond
this benchmark is the reason **no gate caught it**:

> Every shortcut solver asks whether a question is answerable *too easily*. None
> asks whether it is answerable *at all*. A shortcut audit is not a validity
> audit, and the two failure modes are opposite: the prior-neutrality fix (D9)
> pushed `entity_argmax` away from guessable and therefore further into
> impossible.

This strengthens §3 rather than weakening it — the four-solver audit is still a
contribution, but the paper must say what it does **not** cover, and that the
cheapest detector of this class of defect was always one model run. It is also
the concrete argument for running a baseline before release rather than after.

## 10. What is NOT yet true and must not be claimed

- **No model has ever been run.** No baseline numbers exist. Do not write
  anything about difficulty that is not a chance rate or a solver ceiling.
- ~~Label noise ε is unmeasured.~~ ✅ **Measured 2026-09-04**: ε = 9.3%, n=150,
  CI [5.6%, 15.1%]; defensible range [2.7%, 9.3%] after a second review. §5b.
  **Still not true:** that the whole of it is *annotation* noise — part is
  mistranslation, and that part is asymmetric across the twin.
- ~~`--certify` has never been run at scale.~~ ✅ **Run 2026-09-05 at 250
  draws/haystack/family.** Every family on every set passes; the `en_intent`
  `most_common` flag resolved at 152 distinct draws (prior 0.263 vs chance 0.200,
  z=+1.9). **Re-run before submission.**
- **No human ceiling.** Nobody knows what a Turkish reader scores.
- **Haystacks within a tier are not independent** (21–39% record overlap at the
  longest tiers), so tier-level confidence intervals need clustered errors. Noted,
  not yet applied.
- **The trajectory proposal is not unexplored territory.** π² (§8a) published a
  close cousin in English. Claim *first in Turkish*, *first from an aggregation
  benchmark*, *first with verifiable intermediate steps* — not *first*.
- **No difficulty-vs-length curve.** We assume 900K is harder than 100K and have
  never measured it. Needs model runs.
