# TR-OOLONG — Roadmap

> **Note on set names in completed items.** Entries below Phase 6 may name
> `tr_oolong` (Turkish brand reviews) and `en_twin` (airline tweets). That pair
> was **withdrawn in v0.5.0**. The entries are kept as a work log — the
> measurements that motivated each fix are still the reason the fix exists.

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
- [x] `.jsonl` source support (any {text, label} lines; ready for OOLONG's splits
      if they are released)

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

## Phase 1.5 — v0.3.0 validity fixes  ✅ done

- [x] `VERSION` actually bumped to 0.3.0 (v0.3.0 tag had shipped with `VERSION = "0.2.1"`)
- [x] Leakage eliminated at the source (`drop_label_leakage`): TR review axis
      `most_common` leakage baseline 0.733 → 0.133
- [x] Leakage drop rate recorded per corpus — this *is* the asymmetry measurement
      (MASSIVE en 0.68% vs tr 0.00%)
- [x] `least_common` degeneracy fixed (`min_class_support=100`): was `cooking_query`
      in 10/10 haystacks in both languages; now majority 0.20, 8–9 distinct
- [x] Leakage + support filters applied as a **union over the locale pair**, so the
      intent twin keeps an identical label space (49) and row set
- [x] Majority-class baseline added to `trivial_baseline.py` — the real acceptance
      gate; leakage score alone is blind to prior-driven degeneracy
- [x] `scripts/airline.py` — the last unscripted source; all six sets now rebuild
      from public datasets
- [x] Golden test made platform-independent (absolute `source_path` in manifest)
- [x] `run_eval.py`: errored questions no longer marked done, so resume retries them
- [x] Cross-platform reproducibility verified (Windows → macOS/arm64, all six sets)
- [x] README §1/§3/§4/§5 and DATACARD updated to match measurements
- [x] Intent twin made **exactly** row-parallel (was 15,250 tr vs 15,765 en);
      both locales now 15,075 rows / 48 intents
- [x] Maximum haystack length **derived** per set (`R_max = min_class_pool × K`),
      warned on at build time, recorded in the manifest
- [x] Length gradient extended 500K → **1M** where the pool allows
      (amazon 1M, vitamins 750K, tr_oolong 500K, airline 50K/100K); 900 → 1,020 questions
- [x] `DESIGN_DECISIONS.md` — rationale + evidence for every construction choice


## Phase 1.6 — v0.4.0 question-quality overhaul  ✅ done

Driven by a per-question audit that v0.3.0 had no gate for. The headline: a
**context-free prior oracle** (answers from corpus statistics, never reads the
haystack) solved `pairwise` 0.73–1.00 and `entity_argmax` 0.55–0.87, and the
median `tr_oolong` `pairwise` question was decided by **8 records out of 3,919**.

- [x] `scripts/quality_audit.py` — third acceptance gate: per-question depth and
      margin, plus a prior oracle tested against **correctly modelled chance**
      (1/60 for ordering 3 of 5, majority baseline for numeric families)
- [x] Certify the **generator**, not the shipped sample — hundreds of deduplicated
      draws per family (at n=13, `tr_oolong` pairwise measured 0.85; at n=235, 0.53)
- [x] `draw_entity_jitter` — per-haystack log-normal perturbation of the entity
      distribution (the label axis had this since v0.2.0; the entity axis did not)
- [x] `pick_entity_candidates` — entity questions name a candidate set matched on
      the **pool count for the asked label** to within 5%
- [x] Label-ranking families name their candidates too — well-posed on a 48-class
      axis, and no longer decided by a 7-record tail
- [x] Depth + margin floors enforced in **both** GT paths (`_margin_ok`)
- [x] `families_disabled` — a set drops a family that fails its gate
      (`vitamins_tr` loses `top_k`; `en_twin` cannot form a prior-neutral 5-set)
- [x] **Record-matched twin** (`pair_seed` + `haystack_target_records`):
      `tr_intent_paired` / `en_intent_paired` are record-identical, 110/120
      questions share a gold answer → paired tests (McNemar)
- [x] Morphology tax measured directly: Turkish costs **1.30–1.34×** the tokens
      of English at identical record counts
- [x] Turkish correctness: vowel-harmony question particle (mı/mi/mu/mü),
      `arttı`/`azaldı`, `notr`→`nötr`, language-neutral `<<<###>>>` separator
- [x] `scoring.py`: added scale-free `relative` metric — OOLONG's `0.75^|y-ŷ|`
      is degenerate at counts of ~1,000 (kept unchanged for comparability)
- [x] `pytest tests/` collected **zero** tests; added a real test function
- [x] Builder clears `out_dir` (a removed 250K tier was still shipping in `en_twin_out`)
- [x] `scripts/publish_hf.py` — per-subset licensing, text withheld where the
      source forbids redistribution
- [x] Source licenses **resolved** (see DATACARD): MASSIVE CC-BY-4.0, We-Bears
      Apache-2.0, vitamins CC-BY-SA-4.0, airline CC-BY-NC-SA-4.0 (text withheld),
      Amazon governed by Amazon's terms (text withheld). No permission emails needed.
- [x] `DESIGN_DECISIONS.md` D9–D13; D4's overstated claim corrected in place

## Phase 2 — Baselines and pilot

- [x] `trivial_baseline.py` (regex/lexicon over label-token leakage) on all four sets
- [x] Report the shortcut floor per set; quantify the EN label-leakage asymmetry
- [x] Metric parity with OOLONG taken from the paper: they use `score = 0.75^|y-ŷ|`,
      which `partial` implements unchanged. Their scoring script is **not released**,
      so parity rests on the published formula, not on running their code. Say so.
- [ ] Add OOLONG's validated English splits as extra anchor sets — **blocked**: not
      released yet (their repo lists the splits, construction code and scoring
      scripts as pending, checked 2026-08-25). The `.jsonl` loader is ready for them.
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

## Open questions

- [x] We-Bears license — **Apache-2.0**, distributable (verified 2026-08-24)
- [ ] Confirm this repo is the public release repo (assumed yes)
- [x] `top_k` k value — kept at 3, but the family now ships only where it passes
      the prior gate (`tr_oolong`, `amazon_hpc_en`)
- [ ] **`TR-OOLONG-Pairs`** — the RLM paper uses OOLONG-Pairs as one of its four
      evaluation tasks, so a quadratic-complexity family would let Turkish results
      sit on the same constant/linear/quadratic ladder as the published numbers.
      Recommended. Note the naming clash: the current `pairwise` family is *not*
      OOLONG-Pairs and should probably be renamed to avoid confusion.
- [x] **Source label noise — consequence bounded** (2026-08-25). It is a
      *per-family* ceiling, not a global one: ranking families are effectively
      immune, `proportion` scores 0.92 at ε=10%, and raw `count` is capped at
      0.36 by even 2% noise at the 100K tier. Table in `DATACARD.md`. Headline
      results go on ranking and `proportion`.
- [ ] **Measure ε itself** — n=400 per corpus gives ±3 pts at ε≈0.10. `--audit` writes a
      200-row slice per set; needs a native speaker (i.e. you). Highest-value
      open item: it is the first thing a jury will ask about label-derived truth.

## Notes for the supervisor

- The benchmark's core validity claim is the **dual-path ground truth**: every
  answer is computed twice by independent code and asserted equal.
- The **matched twin** (identical pipeline, parallel corpus intent utterances)
  isolates Turkish-vs-English degradation from pipeline artifacts.
- No fine-tuning anywhere in the thesis; hardware constraint is a single V100 16 GB.


## Phase 5 — opened 2026-08-25

- [x] Fourth acceptance gate: `scripts/style_solver.py` (D15). All 8 sets pass;
      `manifests/style_audit.json` committed.
- [x] Per-class surface-shape diagnostic in `--audit`, warning above 2.0x spread.
- [x] Twin search completed and closed (D16, `DATASET_REVIEW.md`). The primary
      pair needs no replacement. **Do not re-run this search.**
- [ ] **Dated timeline axis — the highest-value open item.** OOLONG has six
      timeline families and reports them as its hardest type; TR-OOLONG has one
      binary `shift`, which is also the only family the format solver beats.
      Blocked on data: `app_reviews` and Amazon-Reviews-2023 carry dates, no
      examined Turkish source does. **Finding a dated labelled Turkish corpus is
      the unblocking step.**
- [ ] Label-vs-label comparison family (`Is A more common than B?`) — a cheap
      OOLONG family we do not implement; our `pairwise` compares entities.
- [ ] Entity-frequency family (`which entity appears most often?`, label-free).

## Phase 6 — the clean pair (2026-08-25)

- [x] `musteri_tr` ↔ `marc_en` added. 272 questions, 6 families, 100K/250K/500K.
      Both pools perfectly balanced (entropy 1.000). **Twin asymmetry 0.010, the
      lowest in the benchmark.** Both halves redistributable.
- [x] `sealuzh/app_reviews` rejected on licence (`license:unknown`) despite a
      closer length match. See `DATACARD.md` licensing section.
- [x] Full licensing audit written up: which sets ship text, which ship
      questions-and-answers only, and why share-alike forces a per-source config
      split rather than one flat dataset.
- [x] **Decided 2026-08-30: `tr_oolong` (We-Bears) and its `en_twin` partner are
      withdrawn.** Undocumented label provenance was the deciding factor and is
      the one defect filtering cannot fix. `top_k` withdrawn with it. Configs,
      fetch scripts and built outputs removed so nothing dangles.

## Phase 7 — after the withdrawal (2026-08-30)

- [ ] **Restore an ordered-ranking family** if a corpus turns up with a clean
      licence, documented labels, and an entity axis orthogonal to the label.
      None of the candidates in `DATASET_REVIEW.md` has all three.
- [ ] Consider whether the entity axis resting on `vitamins_tr` alone is
      acceptable, or whether a second orthogonal-entity Turkish corpus is needed.
