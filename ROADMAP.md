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
- [x] Leakage drop rate recorded per corpus. ⚠️ The *asymmetry* reading
      (MASSIVE en 0.68% vs tr 0.00%) was **withdrawn in v0.6.0**: the shipped
      build measures 0.00% on both, and the comparison was confounded anyway.
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
      `tr_intent_paired` / `en_intent_paired` are record-identical, 100/120 gold strings identical (120/120 facts)
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

- [x] **Label-noise annotation done** (2026-09-04). n=150 pair-aligned MASSIVE
      rows, native speaker: **ε = 9.3%, 95% CI [5.6%, 15.1%]**; second review
      overturned 3 of 14, so the defensible range is [2.7%, 9.3%]. Recorded in
      `DATACARD.md`. ⚠️ Part of it is *translation* error, not annotation error,
      and it is asymmetric across the twin — see `PAPER_NOTES.md` §5b.
- [ ] Two-column re-pass (does the label fit the EN / the TR separately) to split
      translation noise from annotation noise on the same 150 rows
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

## v0.6.0 (2026-09-03)

- [x] **Entity rendering** — all 118 entity questions were unanswerable; the
      brand was never printed (D17). Fixed, rebuilt, all five gates re-run green.
- [x] Build-time **guard**: emitting an entity family with `render_entity=false`
      now raises rather than shipping unanswerable questions.
- [x] Leakage filter extended to the **rendered** record (caught
      `The Pressure Positive Co.` in `amazon_hpc_en`).
- [x] **`label_vs_label`** — OOLONG's label-vs-label comparison, on all eight
      sets. Closes the last family gap against their typology except the timeline.
- [x] **`scripts/check_pair.py`** — pairwise compatibility screening for
      contributors; reproduces the §11 verdicts on our own pairs.
- [x] `licence` + `label_provenance` declared in all eight configs.
- [ ] **Run one model.** Still the top open item, and now demonstrably so: a
      single 4B run over 20 entity questions would have caught D17 in an hour.
- [x] `quality_audit.py --certify 250` run at scale 2026-09-05 — every family on
      every set passes; the `en_intent` `most_common` flag resolved (z=+1.9, ok).
      ~2 min. **Re-run before the actual release.**

## v0.6.1 / v0.6.2 (2026-09-09)

- [x] **`label_translation`** config field + `configs/experimental/` variants —
      measures the cost of Turkish-labeling the intent axis: 3.13% (natural
      imperative) vs 0.14% (infinitive form). Kept out of `configs/*.json` on
      purpose so no release script sweeps them in. D19/D19b.
- [x] **`text_provenance`** declared per source (`human_written` /
      `human_translated` / `machine_translated` / `synthetic_generated`),
      backfilled on all 8 shipping configs. `check_pair.py`/`check_solo.py` now
      read it.
- [x] **`scripts/check_solo.py`** — single-dataset acceptance report for a
      contributor with no partner language; bundles declared-metadata checks
      with the three gates that were already twin-agnostic. Catches a missing
      label column as a named error, not a stack trace.
- [x] **`scripts/tokenizer_spread.py`** — the tokenizer-spread table (README §0,
      PAPER_NOTES §1) as a saved, seeded script. Added Mistral: 2.07x
      (SentencePiece, older) vs 1.47x (Tekken, current) — a second vendor
      confirming the generational trend already claimed for OpenAI.
- [ ] **Apply the tokenizer-is-not-morphology correction everywhere it's still
      owed** (PAPER_NOTES §1 flags this "NOT YET APPLIED" to the README §4
      paragraph and the thesis proposal — now also true of the new Mistral
      finding).
- [ ] Decide whether a `configs/experimental/` variant ever graduates to a
      shipping config, or stays a measured-but-unshipped ablation permanently.

## v0.6.3 (2026-09-15)

- [x] **Fifth acceptance gate: `scripts/sampling_solver.py`.** Tests whether a
      question can be answered from a FRACTION of the haystack. It can: a 5%
      sample scores 0.95 on `count` (`vitamins_tr`) and 0.99 on `most_common`
      (`musteri_tr`). Cause is margin width — median rank-1/rank-2 gap is 38-48%
      on the review sets against a 10% floor. `manifests/sampling_audit.json`.
- [x] Entity-mention audit: a review names a brand other than its own in 0.66%
      (`vitamins_tr`) / 13.8% (`amazon_hpc_en`, inflated by common-word brands).
      Correctness unaffected — grouping uses the rendered marker, not free text.
- [x] Entity families recorded as LENGTH-GATED in `DATACARD.md`; `entity_argmax`
      is a 500K+ family, and the twin is incomparable on `pairwise` at 100K.
- [ ] Two-column re-pass on the same 150 rows (native speaker; unchanged).

## v0.6.3 addendum (2026-09-16) — measure the right thing before claiming it

- [x] **`sampling_solver.py` extended:** prefix (truncation) reader, fixed
      record budgets reported per tier, a read-nothing `blind` reference (N/K
      under `relative`), and a noisy full-read reference. `--fail-over` is now
      off by default: the report is disclosed, not passed. **Superseded the same
      day: modelling only `random` and `prefix` was not enough. See the addendum
      part 2 below.**
- [x] **`quality_audit.py` scores numeric families under `relative` too**
      (`p.rel`, `blind`, per-tier). Gate (c) had passed them under `exact` by
      construction. New watch flag: `vitamins_tr` `count` corpus prior 0.75 at
      750K (haystack consumes 54% of the pool). Reported, not failed.
- [x] **Findings written into README §4e / §13, DATACARD, PAPER_NOTES §13c,
      HF card:** blind floor 0.43–0.63; length axis flat under `relative`
      (1,000 random records score 0.94–0.97 at every tier); a 5% perfect
      sample beats a 90% full read; 3-class question sets carry ~2 degrees of
      freedom per haystack; the twin shares 100/120 gold strings and 120/120
      facts.
- [x] **Source Hub revisions pinned** in all five fetch scripts (the commit that
      was HEAD at fetch time; verified against commit history). Recorded in
      DATACARD.
- [x] Twin count stated consistently everywhere (was 100, 110 and "20 shift"
      in three places).

## v0.6.3 addendum, part 2 (2026-09-16) — the readers the gate was missing

- [x] **`headtail` and `stride` readers added to `sampling_solver.py`.** Both
      cost exactly what the `prefix` reader costs. The haystack is two
      internally-shuffled blocks split at `n//2`, so `prefix` is the only cheap
      reader that document order biases. `headtail` at a 1,000-record budget is
      flat across tiers (0.97 to 0.92 on `amazon_hpc_en`) where `prefix` falls
      0.88 to 0.53.
- [x] **Coverage reported per reader per family.** `prefix` returns no answer
      for `shift`, so `shift` had an empty prefix cell in every shipped manifest
      rather than an honest zero-coverage one, and the family was never tested
      against a partial reader at all.
- [x] **The "truncation degrades with length" reading of §4e is withdrawn.**
      Corrected in README §4e, DATACARD, PAPER_NOTES §13c and the HF card. The
      prefix decay is neither a length effect nor drift resistance.
- [x] **`shift` withdrawn** (`families_disabled` in all eight configs and the
      fixture; `DESIGN_DECISIONS.md` D20, README §4e-i, PAPER_NOTES §13d).
      `headtail` scores 1.000 on all eight sets at 25% and 0.90–1.00 at 5%
      against a majority baseline of 0.50–0.70. Takes effect at the v0.7
      rebuild; shipped v0.6.3 data unchanged.
- [x] **VERSION 0.6.2 → 0.7.0** and `tests/golden/` regenerated together.

## v0.7 (planned) — changes that need a rebuild

- [ ] **Rare-label `count` family** (intent axis): labels holding 5–30 records
      in the haystack. Measured sampling resistance 0.29 at a 5% sample vs 0.55
      for shipped counts. Needs a `count`-specific depth rule: every record is
      judged for a count, so answer magnitude is not depth. On the 3-class sets
      the equivalent is `entity_count`, which already ships.
- [ ] **Cap the pool fraction one haystack may consume** (~0.35) so the top
      tier stays prior-neutral; costs `vitamins_tr` its 750K tier unless the
      pool grows. Alternative: keep the tier and report it as prior-exposed
      (current state).
- [ ] **Canonical `answer_key` field** (`more`/`less`/`same`, `rose`/`fell`)
      beside the language-specific `answer`, so the twin is 120/120 identical
      at the byte level. Non-breaking addition; needs a golden regeneration.
- [ ] **De-duplicate `count`/`proportion` on the 3-class sets**: ask each
      label as one or the other per haystack, and spend the freed quota on
      `entity_count`. Raises the evidence per question without adding questions.
- [ ] **Tolerance-band scoring for numeric families** as a fourth metric,
      calibrated so full-read classifier error passes and 5–10% sampling error
      does not. Must be frozen before the first model run, so decide first.
- [ ] Margin band for the ranking families (reject too-wide as well as
      too-narrow). Helps ranking only; measured cost 384 of 452 questions at a
      0.15 cap. Lowest priority of the five.
