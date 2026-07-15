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

## Phase 1 — Configs and full rebuild

- [ ] Set `haystacks_per_length: 5` on all four configs (→ ~50 questions / cell)
- [ ] Set `reference_tokenizer: "Qwen/Qwen3-8B"` on **all** axes (review axis included)
- [ ] Confirm per-mille proportions on the intent axis (currently `auto`)
- [ ] `--audit` each config, sanity-check counts/feasibility
- [ ] Full rebuild of all four sets as **v0.2.0**; commit manifests to `manifests/`
- [ ] Delete duplicate `amazon.py`; set real tokenizer in `sample_compare.py`

## Phase 2 — Baselines and pilot

- [ ] `trivial_baseline.py` (regex/lexicon over label-token leakage) on all four sets
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
