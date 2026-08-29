# Critical review — reading this repo as a jury member would

Written 2026-08-25 against `main`. The tone is adversarial on purpose. Findings
are ordered by how much damage they would do in a viva or a review, and each says
plainly whether it is fixable, expensive, or a dead end.

---

## Finding 1 — CRITICAL. The morphology premise is a tokenizer artifact

**The claim.** README and the thesis proposal both state that at identical
record counts Turkish costs **1.30–1.34x** the tokens of English, and treat this
as the "morphology tax" motivating RQ4.

**The problem.** I measured the same 3,000 pair-aligned MASSIVE utterances under
four tokenizers:

| tokenizer | TR tokens | EN tokens | TR/EN |
|---|---|---|---|
| GPT-2 | 45,970 | 21,278 | **2.16x** |
| Qwen3-8B | 31,767 | 20,824 | 1.53x |
| mBERT (cased) | 30,887 | 23,904 | 1.29x |
| **BERTurk (`dbmdz/bert-base-turkish-cased`)** | 19,418 | 34,265 | **0.57x** |

Under a Turkish-native tokenizer, **Turkish uses 43% fewer tokens than English
for identical content.** The ratio does not measure agglutination. It measures
how much Turkish was in the tokenizer's training data.

**Why this is the most dangerous finding here.** RQ4's stated mechanism is
"Turkish is agglutinative → more meaning per token → recursive compression
degrades faster." If the token cost inverts with the tokenizer, that mechanism is
not a property of the language. An examiner who knows tokenization will ask this
in the first five minutes, and the current framing has no answer.

**Fixable, and the fix improves the thesis.** Three steps, none expensive:
1. Stop calling it a morphology tax. Call it what it is: **the tokenization
   penalty a given model pays on Turkish**, which is a real and consequential
   property *of the model*, not of the language.
2. Report the ratio under **every tokenizer used in the evaluation**, not one.
   The spread from 0.57x to 2.16x is itself a publishable observation and nobody
   has reported it for Turkish long-context work.
3. Re-anchor RQ4 on the **record-matched** regime, which is already built. There,
   TR and EN contain the same utterances with the same gold answers, so any
   accuracy gap is not confounded by token budget at all. That regime exists
   precisely for this and should be the headline, with the token-matched regime
   demoted to a secondary analysis.

**Verdict: doable, roughly a day of rewriting plus one measurement script.**

---

## Finding 2 — CRITICAL. No model has ever been run

Zero baseline numbers exist. Every difficulty claim in the repo is *a priori*:
chance rates, majority baselines, and solver ceilings. OOLONG's paper leads with
"no frontier model exceeds 50% at 128K." TR-OOLONG cannot currently say whether
its questions are hard, easy, or broken.

**Why it matters more than it looks.** A benchmark with no baselines is a dataset
generator. Reviewers at a datasets track will ask for at least: one frontier API
model, one mid-size open model, and the trivial baselines, across the length
gradient. Without them there is no evidence the length axis *does* anything —
which is the entire premise.

**Also unverified without it:** that questions are answerable at all. Nothing has
confirmed a competent reader can score above chance on, say, `count` at 500K.

**Verdict: doable and it is the single highest-value remaining task.** Cost is
modest: 1,506 questions, most under 500K tokens. A pinned API model over the
100K tier alone would produce the missing headline. Do this before anything else.

---

## Finding 3 — SERIOUS. The construct-validity claim rests on undersized samples

README §4 states the rule itself: "Per-family samples of 10–20 cannot certify a
family, so the audit runs on hundreds of deduplicated candidate draws." But the
committed `manifests/quality_audit.json` is **n = 8–56 per family**, mostly
10–20. The `--certify` path exists and has never been run at scale and committed.

One family is currently flagged in that manifest — `en_intent` `most_common`,
prior 0.50 against chance 0.20, p = 0.033, n = 10 — and is unresolved in either
direction.

**Verdict: doable, it is a compute run.** `--certify 250` across ten sets. Until
it is committed, the flagship "four acceptance gates" claim is weaker than the
prose implies, and the discrepancy is visible to anyone who opens the manifest.

---

## Finding 4 — SERIOUS. `shift` is measurably broken and should not ship as-is

Across the eight shipping sets it is the only family the format solver beats:
**+0.400** (`amazon_hpc_en`), **+0.300** (`vitamins_tr`), **+0.267**
(`musteri_tr`, `marc_en`), +0.100 (`en_intent`). Its majority baseline is also
the highest in the suite (mean 0.61, up to 0.73).

The mechanism is understood: length correlates with label, and length correlates
with position once drift is injected, so formatting partly recovers the
direction. It is a binary question, so the ceiling for a shortcut is high by
construction.

**Options, in order of cost:**
- **Cheapest, do it now:** drop `shift` from headline reporting and say why. Costs
  nothing, removes a known-weak family from the numbers people will quote.
- **Medium:** make it 3-way (rose / fell / unchanged) with a margin band, which
  lowers the shortcut ceiling from 0.50 to 0.33.
- **Proper:** replace it with a real dated timeline axis. **Blocked on data** —
  see Finding 8.

**Verdict: the first two are doable today. The third is currently a dead end.**

---

## Finding 5 — SERIOUS. Haystacks within a tier are not independent

Already documented in Limitations, but its consequence is understated. At the
longest tiers a single haystack consumes 20–38% of the pool, so haystacks
necessarily share records. Any statistical test treating the 15–20 haystacks in a
tier as independent samples is wrong, and confidence intervals computed that way
will be too narrow.

**Verdict: partly fixable.** Either cap the top tier at a pool fraction that
keeps overlap under ~10%, or report tier-level results with a clustered variance
estimate and say so. The second is free and honest; the first costs length,
which is the thing the benchmark sells. **Recommend: report the overlap
alongside every tier-level number and use clustered errors.**

---

## Finding 6 — MODERATE. The label-space axis has only two points

Label spaces are 3 and 48. Two points do not make a curve, and "label-space
difficulty" is claimed as one of the two axes. OOLONG spans 2–10 across ten
corpora.

**Verdict: doable and cheap.** `guardrail-tr` gives 5–11 classes (Turkish-native
rows, Apache-2.0, capped at ~259K tokens — fine for a mid-length axis), and
`BuyukSinema` gives 10. Adding one 5-class and one 10-class Turkish set would
turn two points into four. Both were already measured; see `DATASET_REVIEW.md`.

---

## Finding 7 — MODERATE. The entity axis rests on one corpus

Four of the ten families need an entity that is statistically independent of the
label. Only `vitamins_tr` has one (normalised MI 0.022). `tr_oolong`'s brand
column is correlated (MI 0.226) and `en_twin` has six airlines. The new pair has
no entity column at all.

So `entity_argmax`, `top_k`, `pairwise` and `entity_count` effectively rest on a
single Turkish corpus, and `top_k` ships on `tr_oolong` alone.

**Verdict: doable but not cheap.** `sealuzh/app_reviews` has 392 apps at MI 0.044
and would fix it — but is `license:unknown`, which is exactly why it was passed
over. Finding a second Turkish corpus with a clean licence *and* an orthogonal
entity column is an open search. **Until then, state plainly that entity families
are single-corpus and do not generalise a claim across them.**

---

## Finding 8 — MODERATE, and the honest dead end for now

No timeline axis, because no Turkish source examined carries dates. English has
several. A parallel timeline axis needs both halves.

**Verdict: dead end until a dated labelled Turkish corpus is found.** Do not
promise it in the proposal. Do state it as the named limitation and future work —
it is a much better look than leaving reviewers to notice the missing column
themselves, especially since OOLONG reports timeline as its hardest group.

---

## Finding 9 — RESOLVED 2026-08-30. We-Bears withdrawn

The Turkish brand-review corpus and its airline twin were removed from the
release. Its label provenance was undocumented upstream, its length spread was
3.6x, and **0 of 262 duplicate-text groups carried conflicting labels** where the
human-annotated airline set had 17.1% — labels being a deterministic function of
text is not something human annotation produces.

**Price paid:** `top_k` withdrawn (it survived prior-neutrality on that corpus
alone), 285 questions, and one of three review pairs. **Bought:** every remaining
label is either a professional annotation (MASSIVE) or the writer's own star
rating, so classical label noise is near zero by construction on five of eight
sets; every shipping pair now has a twin asymmetry at or under 0.033 against that
pair's 0.108; and the release no longer carries any non-commercial clause.

## Finding 10 — MINOR but will be asked. No human ceiling

Nobody knows what a competent Turkish reader scores on these tasks. For `count`
over 500K tokens the honest answer is "a human cannot do this at all," which is
defensible — the task is deliberately machine-scale — but it needs saying rather
than being discovered by a reviewer.

**Verdict: doable and cheap.** Take the smallest tier, have one reader attempt
ten questions, report it. Even n=10 is better than silence, and the finding
("humans cannot do this either, by design") is itself worth a paragraph.

---

## Finding 11 — MINOR. The `relative` metric is novel and unfrozen

It was added because OOLONG's `0.75^|y-ŷ|` degenerates at our count magnitudes,
which is correct and well argued. But it is a bespoke metric, and a reviewer will
ask why not a standard one (MAE, MAPE, or symmetric MAPE), all of which have
literature behind them.

**Verdict: trivially fixable.** Either justify `relative` against the standard
alternatives in one paragraph, or report MAPE alongside. Do it before freezing.

---

## What is genuinely strong, and should be foregrounded

Stated because a review that only lists faults is not useful for deciding what to
defend.

1. **The shortcut-audit methodology is better than the benchmark it extends.**
   Four solvers, each added after a real defect, with committed manifests. OOLONG
   reports no such audit. This is a contribution independent of Turkish.
2. **"Source-level shortcut measurements do not predict question-level
   exploitability"** is a real methodological finding with a controlled
   experiment behind it (a full replacement pair built, tested, and rejected).
   Other benchmark builders would use this. It deserves its own section in the
   paper.
3. **The record-matched twin** is a genuinely strong design and is the correct
   answer to Finding 1.
4. **Dual-path ground truth with byte-identical rebuilds.** Few benchmarks can
   claim this.
5. **The derived length ceiling** (`R_max = smallest_class × K`) is a small,
   correct, reusable piece of reasoning.

---

## If only three things get done

1. **Run a model.** Nothing else in this list matters until there are baselines.
2. **Fix the morphology framing** (Finding 1) and re-anchor RQ4 on the
   record-matched regime.
3. **Commit a `--certify 250` run** so the validity claims match the manifests.
