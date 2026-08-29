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

## 5. Cross-lingual label leakage is asymmetric, and Turkish morphology hides labels

On MASSIVE, English surface text contains its own intent label in **0.68%** of
utterances. Turkish contains it in **0.00%** of 16,521. English says "play music"
for `play_music`; Turkish inflection never surfaces the label form once.

**Use it as:** a small, striking, genuinely linguistic result — and note it is
the *opposite* direction from the tokenization penalty. Turkish costs more tokens
under most tokenizers but leaks less label information. That tension is
interesting rather than awkward.

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

## 8b. FUTURE WORK — the two-release plan

**The idea, and it is a good one: this project can produce two datasets, not one.**

| | release 1 — the benchmark | release 2 — the trajectories |
|---|---|---|
| when | now, before any model runs | after the evaluation |
| what | 1,221 questions over 110 haystacks, gold answers derived from labels | the decompositions that produced those answers, plus what models actually did |
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

## 9. Headline numbers, current

8 sets · 110 haystacks · **1,221 questions** · **28.2M tokens** ·
36,250–986,533 tokens per haystack · label spaces 3 and 48 · **9 question
families** · 2 languages · 4 acceptance gates · byte-identical rebuilds.

Twin asymmetries (lower is cleaner): `musteri_tr`↔`marc_en` **0.010** ·
`vitamins_tr`↔`amazon_hpc_en` 0.015 · intent record-matched 0.017 · intent
token-matched 0.033. **Every shipping pair is at or under 0.033**; the pair that
sat at 0.108 was withdrawn in v0.5.0.

---

## 10. What is NOT yet true and must not be claimed

- **No model has ever been run.** No baseline numbers exist. Do not write
  anything about difficulty that is not a chance rate or a solver ceiling.
- **Label noise ε is unmeasured.** Its *consequence* is bounded (§4); its
  *magnitude* is not.
- **`--certify` has never been run at scale.** The committed audit is n=8–56 per
  family, and README's own text says n=10–20 certifies nothing. One family
  (`en_intent` `most_common`, p=0.033, n=10) is flagged and unresolved.
- **No human ceiling.** Nobody knows what a Turkish reader scores.
- **Haystacks within a tier are not independent** (20–38% record overlap at the
  longest tiers), so tier-level confidence intervals need clustered errors.
