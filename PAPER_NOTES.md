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

**Status, checked 2026-09-09: mostly applied, two spots were not.** README §4
and the box at the top both name the tokenizer every time and carry the full
generational-trend table; `thesis_proposal_revised.md` §4.4.0 already states
the tokenizer-confound correction. **`COMPARISON.md` and `DATACARD.md` still
had the bare, unqualified "1.30–1.34x" claim — fixed today** (both now name
Qwen3-8B explicitly and point here for the full spread). No `.tex` exists yet
in the repo; when one is started, check it against this section before the
first draft goes out.

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

### NEW 2026-09-09 — Mistral has a public tokenizer too, and it shows the same generational trend

**Mistral is like Qwen and OpenAI, not like Anthropic**: `mistral-common` is
open-sourced and downloadable, works fully offline, no network dependency. Added
to the comparison via a new saved, seeded script (`scripts/tokenizer_spread.py`
— the earlier table's sampling seed was never recorded anywhere, so this also
fixes that; the numbers below use `--n 3000 --seed 42` and are reproducible on
demand).

| tokenizer | generation | TR/EN |
|---|---|---|
| Mistral SentencePiece (`mistral-large-2411`) | v3, pre-Tekken | **2.07×** |
| Mistral Tekken (`mistral-small-2409`) | current family | **1.47×** |

**A second, independent vendor shows the same pattern already claimed for
OpenAI**: Mistral's own older tokenizer pays nearly the GPT-3-era penalty
(2.07× vs 2.16×), and its current one (Tekken, the tokenizer behind Large 2 /
Nemo / Small since mid-2024) is close to Qwen3-8B (1.53×) and mBERT (1.32×).
**This strengthens the "training diet, not morphology" claim** — it is no
longer a single vendor's trend, it is two vendors independently improving
their Turkish coverage across tokenizer generations while nothing about
Turkish itself changed. Worth a sentence citing both vendors rather than
OpenAI alone.

Re-running the full six-tokenizer comparison with the new script's fixed seed
reproduces the previously reported figures closely (p50k 2.16× exact match;
cl100k 1.76× vs. 1.73×; o200k 1.37× vs. 1.35×; Qwen 1.53× exact match; mBERT
1.32× vs. 1.29×; BERTurk 0.58× vs. 0.57×) — the small deltas are exactly what
you'd expect from a different (previously undocumented) sample, not a
methodology change.

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

## 5c. HYPOTHESIS, NOT A RESULT — does the shortcut reflex differ by language?

**Observed once, in a trial run that timed out.** Same question, both languages,
same model. The English root reasoned that the intent is not written in the text
and dispatched sub-calls to classify each utterance. The Turkish root instead ran
`context.count('transport_taxi')` and then searched for that string inside each
record before abandoning it.

**If it replicates it is a genuine result**, and one only a matched-twin design
can detect: models may fall back on lexical heuristics more readily in languages
they are weaker at. That is precisely the behaviour `drop_label_leakage` exists to
block, and it would connect directly to the ONERULER critique (their aggregation
tasks are lexical and therefore cannot see this at all).

**Three reasons it is currently worth nothing:**

1. **n = 1 per language.**
2. **Confounded by a harness bug.** The question string — which contains the label
   `'transport_taxi'` — was concatenated into the context, so the label WAS
   present and greppable. A correct run has no such invitation. Bug fixed.
3. **Unequal depth.** Turkish reached iteration 4, English iteration 2, before the
   timeout. English may never have got to the point of trying it.

**To test it properly:** correct harness, both languages, n >= 20 per language,
and a simple coded outcome per run — did the root attempt string matching on the
label before dispatching a classification sub-call? Report as a proportion with a
paired test across the record-matched pair.

**Do not put this in a paper as anything but future work until that run exists.**

---

## 6. `shift` is style-solvable and should not carry a headline. SUPERSEDED: the family is withdrawn (see 13d)

The only family the format solver beats: **+0.400** (`amazon_hpc_en`), **+0.300**
(`vitamins_tr`), **+0.267** (`musteri_tr`, `marc_en`), +0.100 (`en_intent`). Highest majority baseline in the
suite (mean 0.61, up to 0.73).

~~**Use it as:** an honest limitation, paired with the explanation (length
correlates with label, and with position once drift is injected) and the fix
(a real dated timeline axis, blocked on finding a dated Turkish corpus).~~

**Superseded 2026-09-16.** Style-solvability was the smaller problem. A
`headtail` reader scores 1.000 on every set at a 25% budget. `shift` is withdrawn
in v0.7.0 rather than disclosed. **Use it as:** a worked example of a shortcut
that four gates missed because all four constrained answer *values* and this
family's answer is one bit. See 13d.

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
| what | 2,240 questions over 195 haystacks, gold answers derived from labels | the decompositions that produced those answers, plus what models actually did |
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

### ⚠️ 8b-ii. THE TRAIN-EN/TEST-TR CONTROL MUST NOT RUN ON THE INTENT AXIS

**`W1_Summary.md` §8.5 lists "train on English traces, test on Turkish" as the
strongest control, with "zero Turkish leakage by construction." That is exactly
backwards and must not be repeated.** (W1 is kept unedited as a historical
snapshot; this entry supersedes it.)

On the record-matched pair the two languages hold **the same utterances, in the
same order, with the same labels**, and **100 of 120 questions have a
byte-identical gold answer**. Training on the English trajectory therefore shows
the model the answer to the Turkish question. A model could score well on the
Turkish half without reading any Turkish.

| pair | train EN → test TR | why |
|---|---|---|
| `tr_intent_paired` / `en_intent_paired` | **fatal** | identical records, identical gold answers |
| `tr_intent` / `en_intent` | **contaminated** | different samples, but one shared pool of mutually-translated utterances — per-utterance labels memorised in EN transfer to their TR twins |
| `vitamins_tr` ↔ `amazon_hpc_en` | **clean** | different corpora, different text, different answers |
| `musteri_tr` ↔ `marc_en` | **clean** | same |

**The generalisable point, and it is worth a sentence in the paper because it is
counterintuitive:** the property that makes a matched twin the best *evaluation*
control is the same property that disqualifies it as a *training* control.
Identical gold answers across languages are what license paired tests (McNemar)
on the evaluation side, and are answer leakage on the training side. Any
benchmark that builds a parallel twin inherits this, and nobody appears to have
written it down.

**What to run instead:** train on English *review* trajectories
(`marc_en` / `amazon_hpc_en`), test on the Turkish review sets
(`musteri_tr` / `vitamins_tr`). Different corpus and different language, so
neither records nor answers carry over. Combine with the build-time disjoint
source-pool partition (still not implemented, §8.5) before any transfer claim
is made.

**Sequencing:** release 1 now (it is finished and gated); run the evaluation;
release 2 with the paper that analyses it. Two artifacts, two citable objects,
and the second is the one that answers "what is this for beyond a leaderboard."

---

## 8b-bis. WHAT THE HARNESS MUST LOG FROM THE VERY FIRST RUN

**None of this is recoverable afterwards.** Re-running to add a field costs the
whole evaluation again, and on a rented GPU that is the difference between one
experiment and two. Decide once, before the first real run.

| Field | Why it cannot wait | Feeds |
|---|---|---|
| **Full trajectory** — every code cell, REPL output, sub-call prompt and sub-call answer | it *is* release 2 | §8b |
| **Both roles**, root and child, not just the root | the Turkish signal lives almost entirely in the child calls; root traces are language-neutral | §8b |
| **Per-chunk sub-call inputs and outputs** | lets us verify *intermediate* steps against known record labels — the one thing π² cannot do | §8a |
| **`shortcut_attempted`** — did the root try string-matching a label before dispatching any classification sub-call? | one boolean; settles §5c. At n≥20 per language it is a paired test on the record-matched pair | §5c |
| **Iterations used, and why the run ended** (answer / timeout / error / max-iterations) | the first trial's two languages ended at different depths, which is itself a confound to control | §5c |
| **Wall-clock and token cost per run** | the EuroHPC resource estimate must be computed, not guessed | HPC application |
| **Model, prompt condition, seed** | the TR/EN prompt-language ablation is meaningless without it | §8b |

**The cheapest of these is `shortcut_attempted`** — a regex over the root's emitted
code for any label string, evaluated before the first sub-call. It costs one field
and turns an anecdote into a measurable proportion.

**Rule of thumb:** if a question about *how* the model solved it could ever be
interesting, log it now. Storage is free; GPU hours are not.

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

## 8d. OOLONG's DATA is public, including per-record labels (2026-09-16)

Section 8c is about their *construction pipeline*, which is still unreleased.
Their **built data is not**, and the distinction matters because it unblocks the
cross-benchmark check:

- `oolongbench/oolong-synth`, 41 test shards, pinned revision `f0d59eaf`.
  8 source corpora (metaphors, negation, formality, imdb, app_reviews, yahoo,
  multinli, agnews), label spaces K = 2, 3, 4, 10, contexts 1K to 4M tokens.
- `oolongbench/oolong-real` (revision `6bc9ef04`), **checked and NOT usable for
  this.** Four JSONL files (`dnd/`, `toy_dnd/`), D&D session transcripts, with
  questions like "Total number of rolls in this episode?". There is **no
  `context_window_text_with_labels` column and no per-record label of any kind**;
  the gold answers come from parsing events out of transcript prose. Running the
  partial-coverage readers on it would require reimplementing their extraction,
  and the task is closer to lexical extraction than to latent-label aggregation,
  so it is out of scope. Do not re-check this.
- Critically, every row carries **`context_window_text_with_labels`**: the gold
  label of every record in the context window, one per line, formatted
  `Date: .. || User: .. || Instance: .. || Label: ..`.

So TR-OOLONG's partial-coverage solvers run on OOLONG directly, with no
reimplementation of their pipeline. `scripts/oolong_crosscheck.py` does exactly
that. It includes a question only if a perfect full reader re-derives their
published gold answer exactly, so anything our adapter parses or scopes wrongly
is dropped rather than reported, and the kept/dropped counts ship in
`manifests/oolong_crosscheck.json`.

**Correct the README and DATACARD sentences that say their splits are
unreleased and the solver "would be a direct follow-up if they are".** It has
been run.

### Third-party RLM reproductions on OOLONG, worth reading before writing §12

- **`Rickesh/rlm-oolong-reproduction`** (Hub dataset, MIT, Aug 2026). A
  **negative** reproduction of Recursive Language Models on OOLONG-synth, run
  with Claude Haiku 4.5 as both root and recursive model. Headline: wrapping the
  model in an RLM made it **worse** than reading the same context straight
  through, **0.269 vs 0.428 on OOLONG-131k**. Treat as an unrefereed Hub
  artifact, not a paper, and verify its protocol before citing. It is
  nonetheless the second independent signal that the RLM advantage is
  configuration-sensitive, alongside Wang (arXiv:2603.02615) on depth 2 (§12b).
- Relevant to §12 because the open question there is what the RLM advantage
  actually comes from. Our cross-check adds a third possibility neither
  reproduction controls for: **on the OOLONG families that admit a partial-
  reading shortcut, a score cannot separate coverage from classification.**

## 9. Headline numbers, current

**v0.7.0, built and published 2026-09-16.** 11 sets · 195 haystacks ·
**2,240 questions** · **50.7M tokens** · 36,250–999,625 tokens per haystack ·
label spaces 3, 10, 16, 29 and 48 · **9 question families** · 2 languages ·
5 acceptance gates · byte-identical rebuilds · every question difficulty-graded
(259 very hard, 11.6%).

⚠️ **2,240 is a count, not a difficulty claim.** 71.8% of those questions are
answerable by a reader that sees 5% of the records. Quote the 259 very-hard
figure, or the easy/very-hard band pair and the gap between them, never the
pooled total. §13d.

*(Superseded, for reference: v0.6.3 was 8 sets · 110 haystacks · 1,254 questions ·
28.3M tokens · 10 families, with no difficulty grades.)*

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
- ⚠️ **Per-tier entity-family comparisons are NOT like-for-like at the short
  tiers, and this was previously undocumented.** Measured on the shipped v0.6.x
  build (2026-09-13):

  | tier | `vitamins_tr` (count / argmax / pairwise) | `amazon_hpc_en` |
  |---|---|---|
  | 100K | 5 / **0** / 5 | 4 / **0** / **0** |
  | 250K | 5 / 2 / 5 | 5 / **0** / 5 |
  | 500K | 5 / 5 / 5 | 5 / 3 / 5 |
  | 750K–1M | 5 / 5 / 5 | 5 / 5 / 5 |

  Two separate problems. **(a) `entity_argmax` is length-gated on both halves** —
  effectively absent below 500K — because `min_entity_examples` is an absolute
  threshold while the number of brands clearing it scales with haystack size, so
  a prior-matched 5-candidate set cannot be formed in a short haystack.
  **(b) At 100K the twin is asymmetric**: `pairwise` emits 5 on Turkish and 0 on
  English, because `amazon_hpc_en` averages ~1.4 records per brand at that tier
  (1,146 brands over 1,622 records) against ~15.6 for `vitamins_tr`.

  **No warning fired**, because the builder's `[starved]` check is per *set* and
  these families are non-empty at the long tiers. **Consequence: do not report an
  entity-family accuracy-versus-length curve without stating which tiers actually
  carry which families**, and do not compare the two halves' entity results at
  100K at all. The fix, if one is wanted, is to make `min_entity_examples`
  relative to haystack size rather than absolute, and to make the starvation
  check per tier.

---

## 10b. RULER gives us the task taxonomy — cite it instead of inventing one

**Verified 2026-09-15.** RULER (Hsieh et al., NVIDIA, **arXiv:2404.06654**) defines
**four task categories over thirteen tasks**: retrieval (NIAH), **multi-hop
tracing** (variable tracking), **aggregation**, and question answering. Its
abstract states it "introduces new task categories multi-hop tracing and
aggregation to test behaviors beyond searching from context."

**So `aggregation` is an established category with a published definition.** Do
not present the needle / multi-hop / aggregate / summarise split as our own
taxonomy — adopt RULER's and cite it.

**And the category is filled only with lexical tasks, which is the opening.**
RULER's two aggregation tasks are **common words extraction (CWE)** and
**frequent words extraction (FWE)** — extract the most frequently occurring
*words*. String-level matching and tallying; nothing is classified. ONERULER
(arXiv:2503.01996) is the same shape, its aggregation being most-frequent-word
extraction.

| | RULER / ONERULER aggregation | this benchmark |
|---|---|---|
| what is counted | **word occurrences** | **latent labels** (sentiment, intent) |
| written in the text? | yes — match the string | **no** — must be inferred per record |
| solvable by `Counter()` over tokens? | **yes** | no |

**The claim to write:** *aggregation is a recognised long-context category
(RULER), but every published instance of it is lexical word-frequency counting.
We fill it with latent-label aggregation, where the quantity being counted
appears nowhere in the text.* That is stronger and more defensible than claiming
a new category, and it is the same criticism already levelled at ONERULER (§9b,
D17) — now with a second, more prominent benchmark behind it.

**Phrasing caution.** Avoid "there are exactly four kinds of long-context task":
a closed list invites counterexamples and RULER's four are not strictly
parallel. The load-bearing claim is a single axis — **how much of the document
must be read to answer** — on which needle needs one passage, multi-hop needs a
few linked ones, and aggregation needs all of them.

---

## 11. Experiment queue, consolidated (from the week-3 discussion, 2026-09-13)

Each of these came out of a question that had no answer in the repo. All are
cheap relative to the evaluation runs already planned, and each produces a
reportable result whichever way it lands.

> ### ⚠️ NONE OF THIS IS REQUIRED TO GRADUATE. Read this before the table.
>
> The scope ladder in the thesis proposal §5.3 already fixed the floor: **the
> benchmark, the capability screen, and RQ1 on English.** That trio is a
> complete paper on its own, and every item below sits *below* that line.
>
> Treat the table as a menu to draw from if time allows, not a backlog to clear.
> Items 4 and 6 need no model and no GPU, so they can run during a
> dataset-focused stretch; the rest wait until evaluation starts.

| # | Experiment | Why it is worth running | Cost |
|---|---|---|---|
| 1 | **Retrieval / RAG baseline** — top-k chunks, then count | It should fail in a *predictable direction* (systematic undercounting, worsening with length). That is the cleanest evidence the benchmark measures something retrieval cannot do, and it pre-empts the "why not just use RAG" review question | Same questions, same scorer, no new data |
| 2 | ~~**Recursion depth 2**~~ **DOWNGRADED — see §12b** | ~~Untested by anyone~~ **This was wrong.** Wang (arXiv:2603.02615) already ran depth 2, **on OOLONG**, and found it degrades accuracy while inflating runtime 3.6s → 344.5s. The nearest-possible benchmark to ours has answered it | Low value now |
| 3 | **Concurrent vs. sequential sub-calls** | Pure wall-clock measurement, no accuracy effect. Needed anyway for the HPC resource estimate, which must be computed rather than guessed | Free, a by-product of runs already planned |
| 4 | **Sampling-extrapolation solver** (§13 below) | A fifth shortcut solver that the existing four are blind to, and the one most likely to undermine the "must process every record" claim | Half a day, no model needed |
| 5 | **Prompt-language ablation** (EN root/EN child, EN root/TR child, TR root/TR child) | Tests whether matching the instruction language to the content language matters. Small, clean, unpublished for Turkish | Three configs on one set |
| 6 | **Entity-mention audit** | Measures how often a review names a *different* brand than the one it is filed under. Currently unmeasured; affects nothing about correctness but bears on the entity families' lexical cleanliness | An hour, no model needed |

**Sequencing note.** #4 and #6 need no GPU and no model, so they can run now and
close two open construct-validity questions before any evaluation starts.

---

## 12. How the original RLM experiments were scoped, and what that leaves open

Useful in the related-work section, and useful in a viva, because it frames our
contribution as filling disclosed gaps rather than criticising the paper.

**What the authors restricted, deliberately and openly:**

| Restriction | Their words / the evidence | Consequence |
|---|---|---|
| **Recursion depth fixed at 1** | *"in our experiments we only consider a recursive depth of 1 — i.e. the root LM can only call LMs, not other RLMs"* | The root is not *declining* to recurse — no facility for it is exposed. Their results therefore say nothing about whether deeper recursion helps |
| **Sub-calls blocking** | The lack of asynchrony is named as why a query can take minutes | Wall-clock figures in the paper are not a lower bound on what the method costs; the library's concurrent path is faster |
| **Heterogeneous by assumption** | Strong root (GPT-5), cheap children (GPT-5-mini) | Root/child model pairing is an engineering choice they made, not a variable they swept |
| **English only** | Every task evaluated is English | The cross-lingual question is untouched, and the literature names it as open |

**What they explicitly flag as not done:** deeper recursion ("a relatively easy
change"), asynchronous dispatch ("the obvious next implementation step"), and
adaptive depth — letting the root decide per sub-call whether the answer is
worth recursing on, rather than fixing depth in advance.

**The honest framing for our write-up.** Restricting an architecture is normal
and correct practice; the authors disclosed every restriction above rather than
hiding it. The criticism that does land is narrower and purely terminological:
the name claims a capability the experiments do not exercise. We should not lead
with that. What we *should* do is state our own restrictions with the same
explicitness — depth 1, one reference tokenizer, frozen metric, no fine-tuning —
because the failure mode to avoid is not restricting, it is claiming past the
restriction.

---

## 12b. Depth 2 is already measured, on OOLONG — verified 2026-09-15

**Wang, D. (2026), *Think, But Don't Overthink: Reproducing Recursive Language
Models*, arXiv:2603.02615.** A direct reproduction of Zhang et al.'s RLM, not a
generic agent scaffold. Verified against the abstract and listing.

| | |
|---|---|
| compares | pure LLM · RLM **depth 1** · RLM **depth 2** |
| benchmarks | **S-NIAH and OOLONG** |
| models | DeepSeek v3.2, Kimi K2 |
| depth-2 result | **degrades accuracy**; runtime **3.6 s → 344.5 s**; token cost rises sharply |
| stated mechanism | deeper recursion makes models overthink and spawn redundant sub-calls — format collapse, latency, token explosion |

**Consequence, and it corrects an earlier note in this file.** A depth-2 run was
listed in §11 as "untested by anyone." That was wrong. It has been tested, and
tested on **OOLONG** — the benchmark this one is modelled on. Running it here
would be a replication on a Turkish variant, not a new result. Downgraded.

**What is still unexamined, and it is better than the forced-depth experiment:**
**optional** depth. Zhang et al. list adaptive recursion depth as future work —
"whether a sub-call's answer is itself worth recursing on, instead of treating
the recursion depth as fixed at 1" — and Wang tested depth 2 *forced*, not
*offered*. **Nobody has measured what a model chooses when the choice exists.**

Run on the record-matched pair, this becomes a cross-lingual behavioural
measure: same question, same gold answer, different language, so a difference in
how often the model elects to decompose further is attributable to the language.
It is the same design shape as `shortcut_attempted` (§5c) and should be logged
the same way.

⚠️ **Do not interpret "chose to recurse" as "low confidence."** It may track
chunk difficulty, prompt phrasing, or verbosity. Report it as behaviour
observed, not as a belief inferred.

**Also verified from the paper (§12d) and relevant here:** chunk sizes are not
uniform — the root writes the splitting code, so decomposition is a per-query
model decision. Weak roots get this badly wrong, which is why the authors added
a prompt line warning their open-weight model not to sub-call everything.

---

## 12d. Sub-call structure, verified from the paper PDF (2026-09-15)

Three facts extracted directly from arXiv:2512.24601v3, all bearing on planned
experiments:

1. **Chunk sizes are not fixed and not equal.** The root authors the splitting
   code, so the number and size of chunks is decided per query by the model.
2. **Weak roots over-dispatch, and the authors patched it with a prompt.** Their
   system prompt for Qwen3-Coder differs from the GPT-5 one by one added line
   warning it not to use too many sub-LM calls — *"without this warning, the
   model will try to perform a subcall on everything, leading to thousands of LM
   subcalls for basic tasks."* Context windows also differ sharply (GPT-5 272k
   vs Qwen3-8B 32k) and prompts were adjusted accordingly.
   **This is prior evidence for both the capability-floor question and the
   guided-vs-vanilla prompt ablation.** Cite it rather than rediscovering it.
3. **The paper has an architecture figure — Figure 2**, showing the prompt
   treated as part of the environment, loaded as a variable in a REPL. A figure
   is still worth drawing here, for a claim theirs does not make: the difference
   between one level of delegation and genuine nesting.

**Bonus, from Figure 8:** the authors observed RLMs "filtering and interacting
with their context through regex code" as a common trajectory pattern. That is
the same reflex `drop_label_leakage` exists to defeat, and it is independent
support for the grep-proofing design.

**A second finding in that paper, which is more useful to us than the depth
result:** depth-1 RLM **performs worse than a vanilla LLM on simple retrieval
queries**, while improving on complex reasoning. That is a direct argument for
why a benchmark of this shape is needed — the method's advantage only appears on
tasks that genuinely require aggregating over everything, and retrieval-style
benchmarks will systematically understate it. Worth citing in the motivation.

---

## 12c. Can depth 1 be "recursive" at all? No — and the terminology is worth getting exactly right

Recursion, in the ordinary computer-science sense, requires the call graph to
contain a **self-reference**: some node whose child is the same kind of thing as
itself.

At RLM depth 1 the call graph is:

```
RLM root  ──►  LM   (plain model: answers its chunk, returns, stops)
          ──►  LM
          ──►  LM
```

The root is an RLM; the children are plain LMs with no environment and no
ability to dispatch. **No node calls its own kind, so there is no self-reference
and therefore no recursion.** It is a two-level tree: one orchestrator, N
workers — map-reduce, or in current vocabulary an agent with sub-agents.

**The terminology is slightly generous in the source.** "Recursive depth 1"
suggests one level of recursion has occurred. It has not: the number of
*recursive steps* at depth 1 is **zero**. The first genuine self-call appears at
depth 2 (`RLM → RLM → LM`), which is the configuration Wang tested and found
harmful.

**The one caveat, stated for fairness.** The paper's abstract says the model
"recursively call[s] **itself** over snippets," which is a weaker, model-level
sense: the same LLM invoked on smaller inputs. Even that does not hold in the
headline configuration, where the root is GPT-5 and the children are
GPT-5-**mini** — a different, smaller model.

**One-line version:** *at depth 1 no component ever invokes another instance of
itself, so what runs is delegation, not recursion; the recursion the name refers
to begins at depth 2, which the original authors did not run and a reproduction
found harmful.*

---

## 13. ⚠️ "OUR GOLD ANSWERS ARE BIGGER, SO OUR BENCHMARK IS HARDER" — DO NOT WRITE THIS UNQUALIFIED

OOLONG's counting answers are single digits; ours run to the thousands (median
`count` near 1,000, max 12,225). It is tempting to read that as a difficulty
claim. **It is not one, and under one of our own three metrics it points the
other way.**

**The magnitude only becomes "harder" once you name the metric.** Take a model
off by 2 records:

| | gold = 4 (OOLONG) | gold = 1,046 (ours) |
|---|---|---|
| `exact` | wrong | wrong |
| `partial` = `0.75^\|error\|` | 0.5625 | 0.5625 |
| `relative` = `1 − error/gold` | **0.50** | **0.998** |

Off by 2 is a 50% error on a gold of 4 and a 0.2% error on a gold of 1,046. So
under `relative` — the metric we added and the one we intend to report counts
through — **large gold answers are systematically more forgiving, not less.**
Under `exact` they are much harsher (thousands of classifications must all land
right), and under `partial` they are simply degenerate, which is the reason
`relative` exists.

**What is defensibly harder about this benchmark**, and should carry the claim
instead:

- **Records that must be classified**: up to 22,259 per haystack, against tens.
- **Document length**: 36K–988K tokens, against a reporting focus at 8K–128K.
- **Label space**: 48 classes against 2–10 (chance 1/5 after candidate naming,
  against 1/2).

All three are statements about *coverage and confusability*, which is what makes
aggregation hard. Answer magnitude is a statement about the *output*, and it
interacts with the scorer rather than with the task.

### The shortcut this opens, which none of our four solvers can see

Large N makes a strategy viable that is impossible at N = 4: **classify a random
subsample and extrapolate.** Read 300 of 4,000 records, compute the proportion,
multiply back up. The sampling error is governed by √n, so:

| records read | share of document | approx. relative score on `count` |
|---|---|---|
| 300 | 7.5% | ~0.90 |
| 1,140 | 28% | ~0.95 |

A model that reads under a tenth of the haystack could score around 0.90 on
`relative` — plausibly *better* than an honest full pass by a weak model. That
directly undercuts the claim that these questions force processing every record,
and it is worst on exactly the families we chose to headline (`proportion` is
the ideal target for it; ranking families are partly protected by the 10% margin
floor, though 7.5% sampling gives roughly 10% relative error, so close pairs
would become coin flips).

**✅ MEASURED 2026-09-15 — and it is worse than the arithmetic above predicted.**
`scripts/sampling_solver.py` is now the fifth gate. Full numbers in
`manifests/sampling_audit.json` and DATACARD. Headline: a **5% sample** scores
**0.95** on `count` (`vitamins_tr`) and **0.99** on `most_common`
(`musteri_tr`), against majority baselines of 0.05 and 0.545. ⚠️ **The 0.05 is
the wrong reference** for a numeric family under `relative`; the fair one is
the read-nothing N/K guess, which scores 0.63 on that set. See §13c.

**The mechanism is margin width, and this is the useful part.** On
`most_common` the relative gap between the top two classes has a **median of
38%** (`vitamins_tr`) and **48%** (`musteri_tr`) — far above the 10% floor the
builder enforces. A small sample resolves a 38% gap almost always. The 48-class
intent axis has a median gap of **14%** and is correspondingly harder to sample
(`most_common` 0.39 at 5%).

**`label_vs_label` is the only family that resists, and only where its dead
band fires.** On `tr_intent_paired` it scores **+0.02** over majority; on the
3-class review sets, where "equal" never fires (D18) and the family is
effectively binary, it scores **+0.40**. Resistance comes from **requiring a
distinction finer than sampling error can resolve** — which is exactly what a
2% dead band is.

**The fix that follows, for a future version: a margin BAND, not a margin
floor.** The builder rejects questions whose decision margin is below
`min_rank_margin`. It should also reject those *above* an upper bound, because a
38% gap is free to a sampler. That single change would make the ranking families
sampling-resistant by construction, using machinery that already exists. Not
applied — it changes the shipped questions and needs a rebuild.

**Three qualifications that must travel with the number:**

1. **Upper bound, not a model result.** The solver is handed the true label of
   every record it samples. It measures a *perfect classifier reading a
   fraction*, which no real model is.
2. **Metric-specific.** Under `exact`, a sampled count of 1,712 against gold
   1,600 scores zero, so exact match is immune. The ranking families, where
   `relative` and `exact` coincide, are genuinely exposed.
3. **A consequence of scale, which ties back to §13.** A benchmark with
   single-digit gold answers cannot be sampled. Ours can *because* its answers
   run to thousands. The magnitude that was going to be advertised as extra
   difficulty is the same property that admits this shortcut. That is a second,
   independent reason not to make the "bigger answers are harder" claim.

**What to write.** The defensible claim shrinks in a specific way: this
benchmark demonstrably requires **classifying Turkish records and aggregating
them**, and does **not** demonstrably require reading all of them. Any sentence
asserting that a model "must process every record" should be withdrawn. Report
the audit alongside the other four — a self-found limitation reported at release
is a strength, and it is the fifth instance of this project's recurring lesson
that a shortcut nobody tested for is a shortcut that works.

~~**One partial defence already exists by accident, and should be measured rather
than assumed:** every haystack carries deliberately injected drift (one label
over-represented in the second half, for `shift`). A model that samples a
*contiguous* region therefore gets a biased estimate. Uniform random sampling
across the whole document is unaffected. Worth measuring both in solver five.~~

**Measured 2026-09-16, and the defence is not real.** A contiguous *prefix* does
get a biased estimate, which is why it scores 0.53 where a random sample scores
0.95. But two contiguous regions, one at each end, cost the same and are
unbiased: `headtail` scores 0.92 on the same budget. The drift buys nothing
against any reader that touches both halves, and it never bought anything
against a uniform sample. Do not write the drift up as a partial defence.

### 13b. A sampling-resistant family was proposed and tested for feasibility — it does not work on this data

**The proposal.** Mirror OOLONG's `REPRESENTED_N_TIMES` on the entity axis:
*"how many brands have exactly one record labelled X?"* Attractive because
estimating a count of singletons from a subsample is the unseen-species problem
and is provably biased, so the family would force full coverage. The
label condition is necessary — *"how many brands appear exactly once"* with no
label is pure string counting over the printed `[[entity]]` markers, solvable by
regex with no classification at all, which is exactly the ONERULER criticism
this project levels at others.

**Measured on the shipped build, and it fails a squeeze.** Without a
minimum-records filter the answers are large but trivial; with one they collapse
to zero:

| | `vitamins_tr` 100K | `amazon_hpc_en` 100K |
|---|---|---|
| brands per haystack | 166 | 1,146 |
| records per brand (mean) | ~15.6 | **~1.4** |
| brands with only 1 record | 20% | **80%** |
| answer, no filter (`olumsuz` / `negative`) | 33 | 573 — but **86% are brands with a single record**, so the question degenerates into "find the singleton brands" |
| answer, brands with ≥10 records | **[15, 1, 0, 0, 0]** | **[0, 0, 0, 1, 2]** |
| answer, brands with ≥15 records | **[6, 0, 0, 0, 0]** | **[0, 0, 0, 0, 1]** |

Answers of 0 and 1 fail `min_answer_count` (10–20) outright, and a family whose
gold answer is frequently 0 hands the majority baseline a free win — the
degeneracy D3 and D5 exist to reject.

**The structural reason, which is worth understanding because it generalises.**
Each brand's label mix roughly tracks the haystack's Dirichlet-drawn prior, so a
brand with 15 records and a 20% negative rate holds about 3 negatives, not 1.
Landing on *exactly* one is a narrow coincidence rather than a stable population.
**The same property that makes the entity axis well-behaved for the other entity
families — brands being label-heterogeneous in proportion to the document — is
what makes "exactly one" rare and noisy.** Withdrawn.

**What survives:** the diagnosis in §13, not this fix. The sampling exposure
should be *measured* (solver five) and reported, which is how every other
shortcut in this project has been handled.

### 13c. ⚠️ Extended 2026-09-16 — the sampling finding is a symptom; the metric is the cause. Four things to write, one not to

`scripts/sampling_solver.py` was extended with a prefix (truncation) reader,
fixed record budgets per tier, a read-nothing reference, and a noisy full-read
reference. **Extended again later the same day with `headtail` (k/2 at each end)
and `stride` (k evenly spaced) readers, which changed item 2 below and killed
the `shift` family outright; see 13d.** `quality_audit.py` now scores the numeric families under `relative`
as well as `exact`. All numbers are in `manifests/sampling_audit.json` and
`manifests/quality_audit.json`; the README §4e tables are the citable form.

**1. WRITE: the correct baseline for the numeric families is `blind`, not the
majority baseline.** A reader that opens nothing, counts the separators and
answers N/K scores **0.43–0.63** on `count`/`proportion` under `relative`. The
"5% sample scores 0.95 against a majority of 0.05" contrast in §13 compared a
`relative` solver to an exact-match reference; the honest contrast is 0.92
against 0.63 on `vitamins_tr`. Every score in the thesis must be reported as
lift over `blind`. The earlier gate (c) scored numeric families under `exact`
and therefore passed them by construction; that is now fixed and stated.

**2. WRITE: under `relative`, the length axis is flat.** A fixed budget of 1,000
randomly read records scores 0.94–0.97 on `count` at *every* tier from 100K to
1M, on all four review sets. Standard error depends on records read, not
records present. ~~A 1,000-record prefix reader degrades only mildly, and what
degradation exists is the injected drift, not length.~~ **Struck 2026-09-16:
the prefix decay (0.88 to 0.53 on `amazon_hpc_en`) is not drift resistance and
not a length effect. A `headtail` reader on the identical 1,000-record budget is
flat (0.97 to 0.92). Prefix is the only reader whose window sits inside one
block. Do not write the prefix number without the headtail number.** So the
length gradient,
under the informative metric, tests whether a model survives ingestion, not
whether it aggregates over more. **This is the finding that bears on RQ
design:** an RLM's advantage over a truncating baseline will not show on
`count`/`proportion` under `relative` unless the baseline fails to ingest.
Either score under a tolerance tighter than sampling error, or use families
whose answers are small (see 4), or measure ingestion failure as its own
outcome.

**3. WRITE: a single `relative` score cannot attribute credit between coverage
and classification.** A perfect classifier reading 5% (0.89–0.92 on `count`)
beats a 90%-accurate classifier reading everything (0.74–0.90). Ranking
families are immune to classifier noise (1.00 at 70%) and sampling-solvable.
The harness must therefore log a per-record classification probe (§8b-bis
already asks for this) so coverage can be inferred from the aggregate score
given classification accuracy; without it the two are confounded.

**4. WRITE: resistance comes from answer magnitude, not margin width.**
`entity_count` (small answers) is the most resistant family that ships. Rare
intent labels (5–30 records) score 0.29 at 5% against 0.55 for shipped counts.
This is the constructive result: the `min_answer_count` floor, written to stop
ranking questions from resting on a handful of records, also removes the only
sampling-resistant counts. For `count` every record must be judged (each is
either X or not), so a small answer is still full aggregation. Staged for v0.7.

**Also state:** the corpus prior scored under `relative` reaches **0.75** on
`vitamins_tr` `count` at 750K, because that haystack consumes 54% of the pool
and the Dirichlet prior cannot be realised. Report the 750K tier of that set as
prior-exposed. And: on the 3-class sets, twelve questions per haystack carry
about two degrees of freedom plus one bit (count for all three labels, the same
labels again as proportions, rankings determined by both), so the unit of
evidence is the haystack, not the question.

**DO NOT WRITE** "the benchmark tests long-context aggregation up to 1M tokens"
without the qualifier "under `exact`, or under `relative` as lift over `blind`
with the reading protocol stated". The unqualified sentence is false on 64% of
the questions.

### 13d. ⚠️ 2026-09-16. `shift` is withdrawn, and the reason generalises

**WRITE this as a methods finding, not as an apology.** The partial-coverage
gate modelled only two readers: a uniform random sample and a contiguous head
prefix. Adding two readers that cost exactly the same as the prefix, `headtail`
(k/2 records at each end) and `stride` (k records evenly spaced), changed two
conclusions.

**First, `shift` does not survive.** It scores **1.000 on all eight sets** for a
`headtail` reader at a 25% budget, and 0.90 to 1.00 at 5%, against a majority
baseline of 0.50 to 0.70. Fifty records at each end of a 16,000-record document
answer it perfectly. The haystack is two internally-shuffled blocks split at the
midpoint, so the answer is a step function at a known position and its direction
is a single bit. The family is disabled in every config as of v0.7.0.

**Second, the generalisable point, which is the one worth a paragraph in the
paper.** Every difficulty floor in this project constrains either the magnitude
of an answer or the margin at a boundary. Both are *value* constraints. `shift`
has neither, because its answer space is `{rose, fell}`, and it passed four
gates for that reason. The gate that should have caught it could not, because
the only positional reader it modelled returns *no answer* for `shift`, leaving
an empty cell that read as absence rather than as an untested case. **A
shortcut audit must report coverage, not just score: a reader that cannot
attempt a family looks identical to a family that resists it.** The solver now
reports coverage per reader per family.

**The honest framing for the write-up:** this benchmark's own gate suite was
incomplete, we found the gap ourselves before any model ran, and the family it
condemned was removed rather than disclosed. That is a stronger methods story
than a clean table would have been, and it is the reason the partial-coverage
solver is reported rather than passed.

**What must NOT be claimed:** that document order protects anything. It does
not. Every label except the drift target is exchangeable across the whole
document, and the drift target is exchangeable within each half. The only
protection measured so far is a **small answer** (`entity_count`, rare-label
counts), and that is what v0.7 Task A builds on.
