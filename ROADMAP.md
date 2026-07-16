# TR-OOLONG — Roadmap

Progress tracker. Tick boxes as items land. Ordered by priority; later phases
assume earlier ones are done.

## Phase 0 — Builder (v0.2.0)  ✅ done

- [x] Separator-aware sampling; drift ordering applied *after* trimming (shift signal survives)
- [x] Loud drift-detectability assertion; `drift_ok` recorded per haystack
- [x] Shift answers language-mapped (`rose/fell` ↔ `artti/azaldi`) and validated
- [x] `entity_count` samples label-then-valid-entity (no starvation)
- [x] Stratified per-family quotas; realized distribution in the manifest
- [x] Per-mille proportions on axes with >10 labels (auto); unit recorded per question
- [x] Readable string-seeded RNG; canonical ordering → byte-identical rebuilds
- [x] `drift_target` persisted to meta + manifest
- [x] Normalized output: `haystacks.jsonl` + `questions.jsonl`
- [x] New families `top_k` and `pairwise`, both with dual-path ground truth
- [x] Nested-entity detection (entity families auto-omitted on the intent axis)
- [x] Label-distribution families `most_common` / `least_common` / `second_most` (OOLONG typology)
- [x] Multi-dataset build: `--config *.json` + combined `benchmark_index.json`
- [x] `.jsonl` source support (OOLONG validated English splits usable directly)

## Phase 1 — v0.2.1 fixes and full rebuild

- [x] Randomize drift direction per haystack (shift answers were 100% 'rose' by construction)
- [x] Randomize drift-target choice among eligible labels (was always the majority label)
- [x] Half-up rounding in both GT paths (banker's-rounding mismatch with question wording)
- [x] verified_gt and drift invariant raise real exceptions (asserts are stripped under -O)
- [x] Spill rotation in allocate_quota (count/proportion quota no longer skewed)
- [x] Move benchmark_index.json out of configs/ (the configs/*.json glob swallowed it)
- [x] `--audit` each of the six configs, sanity-check counts and feasibility
- [x] Full rebuild of all six sets as **v0.2.1**; recommit manifests to `manifests/`
- [x] Regenerate `examples/sample_questions_review.jsonl` from the v0.2.1 build
- [ ] Regenerate README figures from the v0.2.1 manifests
- [x] Delete duplicate `amazon.py`; set real tokenizer in `sample_compare.py`

## Phase 2 — Baselines and pilot

- [x] `trivial_baseline.py` (regex/lexicon over label-token leakage) on all four sets
- [ ] Report the shortcut floor per set; quantify the EN label-leakage asymmetry
- [ ] Align the frozen metric to OOLONG's `src/eval/` scoring script (provable parity)
- [ ] Optionally add OOLONG's validated English splits as extra anchor sets (jsonl configs)
- [ ] Frontier reference point: one haystack per axis via a **pinned API model**
      (record model string + access date); chat-UI runs are informal only

## Phase 3 — Release

- [ ] `README.md` figures via `scripts/make_readme_figs.py` (from the real manifests)
- [ ] `git init`; first commit `v0.1 builder + manifests (pre-rebuild snapshot)`
      to preserve the buggy-but-real state in history
- [ ] Commit `v0.2.0 rebuild`; tag `v0.2.0`; push (public — release timestamps establish priority)
- [ ] Hugging Face dataset: **intent axis first** (MASSIVE is CC-BY-4.0 — verify at release)
- [ ] Review axis stays *built, not distributed* until the We-Bears license clears

## Phase 4 — Datacard and harness

- [ ] Label-noise self-annotation of the 200-row slices (native speaker)
- [ ] `DATACARD.md` completed with per-axis label-noise numbers
- [ ] Evaluation harness with the **frozen** dual metric (exact match + `0.75^|y−ŷ|`)
- [ ] Freeze the metric *before* any model runs

## Open questions (decide before Phase 1 rebuild)

- [ ] We-Bears review-dataset license clarification — status?
- [ ] Confirm this repo is the public release repo (assumed yes)
- [ ] `top_k` k value — default 3; keep?
- [ ] Whether to add a `TR-OOLONG-Pairs` (quadratic-complexity) extension later,
      to slot into the RLM paper's constant/linear/quadratic ladder

## Notes for the supervisor

- The benchmark's core validity claim is the **dual-path ground truth**: every
  answer is computed twice by independent code and asserted equal.
- The **matched twin** (identical pipeline, parallel-translated intent utterances)
  isolates Turkish-vs-English degradation from pipeline artifacts.
- No fine-tuning anywhere in the thesis; hardware constraint is a single V100 16 GB.
