# Literature review

Checked 2026-09-28 against arXiv abstracts and paper pages. Each entry says
what the work is and why it matters here. "New" marks work not yet cited in
the project notes or the thesis proposal.

## 1. The two works this thesis builds on

- **Recursive Language Models.** Zhang, Kraska, Khattab. arXiv:2512.24601
  (v1 Dec 2025, v3 May 2026). The long input is stored as a variable in a
  Python environment; the model writes code to inspect it and calls smaller
  models on pieces. v3 adds **RLM-Qwen3-8B**, a Qwen3-8B post-trained to work
  this way, which beats its base model by 28.3% on average. *Why it matters:*
  an 8B RLM that fits the planned hardware already exists, and it has only been
  tested in English. A blog post calls RLM accepted at NeurIPS 2026; the arXiv
  page does not say so, so do not cite a venue until one is confirmed.
- **OOLONG.** Bertsch, Pratapa, Mitamura, Neubig, Gormley. arXiv:2511.02817.
  Long-context aggregation benchmark: classify many records, then count. Frontier
  models stay under 50% at 128K tokens. TR-OOLONG follows its synthetic half.

## 2. Follow-ups to RLM (all English only)

| work | what it shows | effect on this thesis |
|---|---|---|
| Wang, *Think, But Don't Overthink*, arXiv:2603.02615 (Mar 2026) | depth-2 recursion lowers accuracy and multiplies runtime; depth 1 loses to a plain model on simple retrieval | already cited; supports using depth 1 |
| **New.** Alizadeh et al. (Apple), *SRLM: Self-Reflective Program Search*, arXiv:2603.15653 (Mar 2026) | "recursion itself is not the primary driver of performance"; picking among candidate programs by the model's own uncertainty matches or beats RLM, by up to 22% | **the important one.** The gains come from working on the text through code, not from recursion. A thesis titled around "recursive" models should test a non-recursive code baseline |
| **New.** Roy et al., *λ-RLM*, arXiv:2603.20105 (Mar 2026) | replaces free-form code with a fixed set of verified operations; beats RLM in 29 of 36 comparisons, up to 4.1x faster | same direction: structure beats open-ended recursion |
| **New.** Ehrlich, Blackman, *LCM: Lossless Context Management*, arXiv:2605.04050 (2026) | engine-managed map and summarise steps instead of model-written loops; evaluated on OOLONG from 32K to 1M; their agent beats **Claude Code** on OOLONG | shows Claude Code is already used as an OOLONG baseline |
| **New.** Lumer et al., *Recursive Agent Harnesses*, arXiv:2606.13643 (Jun 2026) | parent agents spawn parallel sub-agents with files and code; OOLONG-synth up to 4M tokens; GPT-5 72% to 81%, Claude Sonnet 4.5 90%. Notes that coding agents "reduce per-entry reasoning to regex heuristics" on OOLONG, yet such an agent (Codex) still scores 71.75% | the closest published remark on OOLONG shortcuts, framed as an agent weakness, not a benchmark flaw. No paper found measures how much of OOLONG a shortcut can answer |
| **New.** Gandhi, Chakraborty, Wang, Kumar, Neubig, *Recursive Agent Optimization*, arXiv:2605.06639 (May 2026) | reinforcement learning to teach agents when to spawn sub-instances of themselves | relevant to the planned training-from-trajectories idea; same group as OOLONG |
| Kim, Ahmad, *Reinforcing Recursive Language Models*, alphaXiv blog (May 2026) | trains 4B models as RLMs with one shared policy for parent and child | cited in the proposal; it is a **blog post, not a paper**, so cite it as such |

## 3. Multilingual long-context benchmarks (none covers Turkish)

| work | languages | aggregation? |
|---|---|---|
| ONERULER, Kim et al., arXiv:2503.01996 | 26, **no Turkish** | yes, but by counting words (lexical), not by classifying records |
| mLongRR, arXiv:2409.18006 | en, vi, id, sw, so | retrieval and reasoning |
| **New.** MLRBench, Hengle et al., arXiv:2504.12845 | en, de, es, hi, ar, vi, zh | yes (multi-hop, aggregation, "is it absent"), over explicit facts |
| **New.** MGAL, Li et al., arXiv:2608.20853 (Aug 2026) | the six UN languages | position and granularity of information, 8K-128K |

All four report that the gap between high- and low-resource languages grows
with context length. None is Turkish, and none asks the model to classify
records whose label is not in the text. The novelty claim, "first Turkish
long-context aggregation benchmark, with latent labels", still holds.

## 4. Turkish evaluation (none is long-context aggregation)

- Cetvel, arXiv:2508.16431 (EACL 2026): 23 Turkish tasks, short context.
- TurkBench, arXiv:2601.07020: Turkish benchmark, short context.
- **New.** *Evaluating Open-Weight LLMs for Turkish Domain Documents Under
  Retrieval and Hardware Constraints*, arXiv:2609.28007 (Sep 2026): 100
  questions over one 109-page Turkish report, five 7-8B models, retrieval
  setting. Closest recent Turkish long-document work; it is retrieval QA, not
  aggregation. Worth citing as neighbouring work.

## 5. What this changes

1. **The word "recursive" is now a weak point.** Three independent 2026 papers
   (Wang; SRLM; λ-RLM) find that deeper or free-form recursion does not help,
   and SRLM says recursion is not what drives the gains. The defensible framing
   is "language models that work on long text through code (RLM and its
   variants)", with RLM as one of the systems compared.
2. **The cross-lingual gap is still open.** No RLM or agent-harness paper found
   evaluates any language other than English. That is the thesis's strongest
   claim, and it does not depend on recursion.
3. **Code-using systems can skim.** Every system above can write code that
   reads a sample of the document. None of these papers reports whether their
   systems actually read everything. TR-OOLONG's measurements of what sampling
   achieves (and the finding that difficulty grades can be gamed by guessing
   small numbers) can be turned into a question none of them asks: *do these
   systems read the whole document, and does that differ by language?* Logging
   the code each system writes answers it directly.
4. **RLM-Qwen3-8B** is a cheap, directly relevant model to test on Turkish.

## 6. Corrections needed in the thesis proposal

- The reference list says ONERULER covers "26 languages incl. Turkish". It does
  not; the proposal's own revision note already corrects this, but the
  reference entry was not updated.
- Kim & Ahmad and Patel (commodity hardware) are blog posts or unrefereed
  write-ups; cite them as such.
