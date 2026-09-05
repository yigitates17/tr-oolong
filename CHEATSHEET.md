# TR-OOLONG — cheat sheet

For when you come back after a month and can't remember what any of it is for.
Read top to bottom the first time; after that use it as a lookup.

---

## 1. What this repo is, in four sentences

It is a **generator**, not a pile of files. You give it a *labeled* dataset
(text + label, optionally + entity) and it produces very long documents plus
questions about those documents whose answers it computes exactly from the
labels. Nobody ever annotates anything. The point is to test whether a model
actually *reads* a 500K-token context or just skims it, because the only way to
answer "how many of these records are negative?" is to classify all of them.

The finished thing is a **benchmark**; the files it emits are a **dataset**.
See §7 for how to say that in the paper.

---

## 2. Vocabulary — every term you will forget

| Term | What it means here |
|---|---|
| **atom / record** | One row of the source data — one review, one tweet, one utterance. The indivisible unit that gets classified. |
| **haystack** | Hundreds-to-tens-of-thousands of atoms concatenated into one giant string, separated by a marker. This is what goes in the model's context. |
| **separator** | The marker between atoms (`\n\n<<<###>>>\n\n`) — deliberately language-neutral, so it costs the same tokens in Turkish and English. Lets a model (or a script) split the haystack back into atoms. |
| **tier / target_tokens** | The length setting: 50K, 100K, 250K, 500K, 750K, 1M tokens. Five haystacks are built per tier. |
| **instance set / "set"** | One source corpus, fully built → one `*_out/` directory. There are six: `tr_intent`, `en_intent`, `tr_oolong`, `en_twin`, `vitamins_tr`, `amazon_hpc_en`. |
| **axis** | A group of sets sharing a label type. Two axes: **review/sentiment** (3 classes, brand entity) and **intent** (48 classes, scenario entity). |
| **twin** | The English set built by the identical pipeline from the parallel corpus, so TR-vs-EN differences aren't pipeline artifacts. |
| **family / kind** | A question type: `count`, `proportion`, `shift`, `most_common`, `least_common`, `second_most`, `entity_count`, `entity_argmax`, `top_k`, `pairwise`. |
| **entity** | A second, non-label attribute of each atom — brand, airline, scenario. Enables "which brand got the most negative reviews". |
| **orthogonal vs nested entity** | *Orthogonal*: every brand has all 3 sentiments → entity questions are meaningful. *Nested*: each MASSIVE intent belongs to exactly one scenario → entity questions are trivial. The builder detects this and omits the entity families automatically. |
| **askable entity** | An entity with at least `min_entity_examples` (15) atoms in the haystack. Only these are eligible. |
| **candidate set** | The options a ranking question *names* ("which of these 5 brands…"). Chosen so their corpus-level counts are near-identical, which is what stops the question being answerable from the corpus alone. |
| **prior oracle** | A solver that answers from source-corpus statistics and never reads the haystack. The third acceptance gate (`scripts/quality_audit.py`). |
| **thin / knife-edge** | A question decided by too few records (thin) or by too small a margin (knife-edge). Both are rejected at build time. |
| **entity jitter** | A per-haystack random perturbation of the brand distribution, so brand rankings are a property of the haystack rather than of the corpus. |
| **paired / record-matched** | A twin sized in *records* rather than tokens, so both languages contain the same records and share gold answers. |
| **singleton family** | A family where only one question per haystack makes sense (`shift`, `most_common`, `least_common`, `second_most`) — asking twice would be the same question. Quota-capped at 1. |
| **quota** | How many questions of each family to make per haystack (12 total, split evenly, remainder to `count`/`proportion`). |
| **drift** | Deliberately over-representing one label in the second half of the haystack so `shift` questions have a real signal. `drift_target` = which label; `drift_ok` = the signal was detectable. |
| **per-mille** | When there are >10 labels, percentages round to 0, so `proportion` switches to parts-per-thousand automatically. |
| **meta parquet** | `meta_<tier>-<k>.parquet` — the exact atom list of one haystack (row_id, text, label, entity, char offsets, which half). This is the evidence the answers were computed from. |
| **manifest** | `manifest.json` per set — version, config, source hash, tokenizer, cleaning stats, realized family counts. The reproducibility record. |
| **pool** | The source rows left after cleaning; what haystacks are sampled from. |
| **label leakage** | An atom whose text literally contains a label word ("olumsuz bir deneyim" in a record labeled `olumsuz`). Makes the benchmark grep-solvable. Dropped at build time. |

---

## 3. The safety mechanisms, and what each one is defending against

These are the parts that make it a benchmark instead of a text dump. Each exists
because a specific shortcut was found and measured. **Do not remove one without
re-running its evidence.**

1. **Dual-path ground truth** — every answer is computed twice, once in Polars
   (`gt_primary`) and once in pure Python (`gt_check`), and the two must be equal
   or the build raises. *Defends against:* a silent bug in the answer key. This
   is the benchmark's single strongest validity claim; a new family cannot ship
   without an independent second implementation.

2. **Label-leakage filter** (`drop_label_leakage`) — drops any atom whose text
   contains *any* label's surface form, across the whole label space.
   *Defends against:* grep-solvability. Evidence: a solver that only did substring
   search scored 0.733 on `most_common` before the filter and 0.133 after.
   Only 0.84% of records leaked — the lesson is that leakage *rate* doesn't
   predict exploitability.

3. **Class support floor** (`min_class_support`) — drops labels with too few
   source rows. *Defends against:* `least_common` being answerable from the corpus
   prior. Evidence: `cooking_query` had 6 rows in 16,521 and was the gold answer
   in 10/10 haystacks. Intent label space went 60 → 48.

4. **Prior randomization** (`draw_label_weights`, Dirichlet) — each haystack draws
   its own random label distribution instead of inheriting the corpus's.
   *Defends against:* "the biggest class in the corpus is always the answer."
   Working correctly: realized label shares range 0.003–0.93 across haystacks.

5. **Ranking length ceiling** (`R_max = min_class_pool × K`) — a haystack can't be
   so long that rare classes are mathematically pinned to the bottom of every
   ranking. *Defends against:* long contexts silently making ranking questions
   trivial. The builder warns above 0.85× and records the ceiling per set.

6. **Prior-neutral candidate sets + entity jitter** (`pick_entity_candidates`,
   `draw_entity_jitter`) — ranking questions name candidates whose *corpus*
   counts are near-identical, and each haystack perturbs the entity distribution.
   *Defends against:* "the biggest brand always wins." Evidence: the prior oracle
   scored 1.00 on `vitamins_tr` `pairwise` before this, and chance after.

7. **Depth and margin floors** (`_margin_ok`, `min_answer`) — no answer may rest
   on a handful of records or on a gap of one. *Defends against:* the median
   `pairwise` question being decided by 8 records out of 3,919.

---

## 4. What the golden test is and why it exists

**What it does.** `tests/test_golden.py` rebuilds a tiny committed fixture
(`tests/fixture_source.csv`, ~1000 rows) and byte-compares the result against
`tests/golden/`. Pass = the builder produces exactly the same bytes as when the
golden files were frozen.

**Why.** Everything in this benchmark depends on the build being deterministic.
If sampling, ordering, question generation, or ground truth changes *at all* —
even accidentally, even from a library upgrade — every published number becomes
unreproducible and the manifests start lying. The golden test turns that into a
loud failure instead of a silent one. It is a **regression tripwire**, not a
correctness test: it doesn't check the answers are *right* (the dual-path GT does
that), only that they haven't *changed*.

**How to run.**
```bash
python tests/test_golden.py           # verify — exit 0 = pass
python tests/test_golden.py --regen   # accept the change as the new baseline
```

**The rule.** If it fails and you did not mean to change the builder, you have a
bug. If it fails and you *did* mean to change the builder, bump `VERSION` in
`src/build_tr_oolong.py` **and** run `--regen`, in the same commit. Version and
golden files move together, always. (There was one incident where the `v0.3.0`
tag shipped with `VERSION = "0.2.1"` — that is the failure mode this rule
prevents.)

---

## 5. Workflows

### 5.1 Add a new source dataset  ← the common one

A dataset is a **config file, not code**. You never touch the builder.

1. **Write a fetch script** in `scripts/` that downloads the public dataset and
   writes `datasets/<name>.parquet` (or `.csv` / `.jsonl`). Every source needs
   one so a rebuild starts from the public data, not from a file on your disk.
2. **Write `configs/<name>.json`.** The required fields:
   ```json
   { "source_path": "datasets/<name>.parquet",
     "text_col": "...", "label_col": "...", "entity_col": "",
     "language": "tr",
     "haystack_target_tokens": [100000, 250000],
     "reference_tokenizer": "Qwen/Qwen3-8B",
     "out_dir": "<name>_out" }
   ```
   `entity_col: ""` means no entity axis → the four entity families are skipped.
   Override `question_templates` if the domain word matters ("reviews" vs
   "records"); otherwise the built-in templates are used.
3. **Audit before building.** This is where a new source gets calibrated — the
   difficulty floors are NOT one-size-fits-all, and defaults tuned on a 3-class
   axis will silently reject every ranking question on an 18-class one:
   ```bash
   python src/build_tr_oolong.py --config configs/<name>.json --audit
   ```
   It reports class balance and imbalance, entity concentration, the **observed
   adjacent-rank gaps on three trial haystacks**, and **recommended values for
   `min_rank_margin` and `min_answer_count`** — plus the chance rate each family
   hands a solver for free. Apply the recommendations to the config before
   building. It also writes the 200-row label-noise slice.
4. **Set the tiers from the ceiling.** The audit and the manifest report
   `ranking_feasibility`. Do not set a tier above 0.85× the ceiling.
5. **Build:**
   ```bash
   python src/build_tr_oolong.py --config configs/<name>.json --build
   ```
6. **Watch the build output for `[starved]`.** A family that produces zero
   questions is now loud. Silence used to be the failure mode: an 18-class source
   lost `most_common`, `least_common` and `second_most` entirely and the quota
   just spilled into `count`/`proportion` with no indication anything was gone.

7. **Run BOTH acceptance gates** — not optional:
   ```bash
   python scripts/trivial_baseline.py --sets <name>_out   # leakage + majority
   python scripts/quality_audit.py --sets <name>_out      # prior oracle + depth/margin
   ```
   `quality_audit.py` **auto-discovers** every built set from `configs/`, so a new
   source cannot be forgotten by the gate. Reject the set if it exits non-zero, or
   if a family's leakage score beats `max(majority, chance)`.

8. **Certify before release.** The 7–20 questions per family that ship CANNOT
   certify a family — a `pairwise` family measured 0.85 at n=13 and 0.53 at
   n=235. Run the generator at real power:
   ```bash
   python scripts/quality_audit.py --certify 250
   ```
   Anything flagged `watch (n<30)` in the normal run must be settled here.
   If a family fails on this source and cannot be repaired, switch it off with
   `"families_disabled": ["top_k"]` and say so in the datacard — that is what
   `vitamins_tr` does.
9. **Commit** the config, the fetch script, and `manifests/<name>_out.json`.
   Never the data (`*_out/`, `datasets/` are gitignored).

Build several at once and get a combined index:
```bash
python src/build_tr_oolong.py --config configs/*.json --build \
    --index manifests/benchmark_index.json
```

### 5.2 Add a new question family

This *is* code, in four places in `src/build_tr_oolong.py`:

1. `Q_TEMPLATES` — the question wording, **both** `"tr"` and `"en"`.
2. `gt_primary` (Polars) **and** `gt_check` (pure Python) — two independent
   implementations. This is enforced; there is no way to ship one.
3. `_make_one` — how to draw a question of this kind, and when to reject a
   degenerate draw (return `None`).
4. `generate_questions` — add the name to `families`; add to
   `SINGLETON_FAMILIES()` if only one per haystack makes sense.

Then: `python tests/test_golden.py --regen` + bump `VERSION`.

### 5.3 Full rebuild of everything
```bash
python src/build_tr_oolong.py --config configs/tr_intent.json configs/en_intent.json \
  configs/vitamins_tr.json configs/musteri_tr.json configs/marc_en.json \
  configs/amazon_hpc_en.json --build --index manifests/benchmark_index.json
python scripts/trivial_baseline.py
python tests/test_golden.py
```
⚠️ This is the **GPU-machine job** (tokenizer + 1M-token haystacks). Push before
switching machines.

### 5.4 Run a model against it
```bash
python scripts/run_eval.py --sets tr_intent_out --model qwen3:8b \
  --base-url http://localhost:11434/v1
```
Resumable — answered question ids are skipped on rerun; errored ones are retried.
Scores with the **frozen** metric in `src/scoring.py`.

---

## 6. File map

| Path | What it is |
|---|---|
| `src/build_tr_oolong.py` | The whole generator. Clean → sample → assemble → ask → verify → write. |
| `src/scoring.py` | The **frozen** metric. Do not edit after the first model run. |
| `configs/*.json` | One per instance set. This is where a "new dataset" lives. |
| `scripts/massive.py`, `webears.py`, `airline.py`, `vitamins.py`, `health.py` | Fetch scripts — one per source. |
| `scripts/trivial_baseline.py` | Shortcut solvers. The acceptance gate. |
| `scripts/run_eval.py` | Model evaluation harness. |
| `scripts/make_readme_figs.py` | Figures from the manifests. |
| `tests/test_golden.py` | Reproducibility tripwire (§4). |
| `manifests/*.json` | Committed build records. The reproducibility evidence. |
| `*_out/` | Generated data — **gitignored**, distributed via Hugging Face. |
| `README.md` | The public pitch. |
| `DESIGN_DECISIONS.md` | Why each safety mechanism exists, with the evidence. Read this before defending anything. |
| `DATACARD.md` | Provenance, licenses, known selection effects. |
| `ROADMAP.md` | What's done, what's next. |

---

## 7. "Is it a dataset or a benchmark?" — how to say it

Both words are correct about different things, and mixing them up is the kind of
imprecision a reviewer notices.

- **Benchmark** = the *task definition*: the question families, the construction
  procedure, the ground-truth derivation, and the frozen metric. That is the
  contribution. TR-OOLONG **is a benchmark**.
- **Dataset** = the *files* one particular run of the generator produced — 1,254
  questions over 110 haystacks. That is an *instantiation* of the benchmark, and
  it is what goes on Hugging Face.

Use it like this:

> "We introduce **TR-OOLONG**, a Turkish long-context aggregation **benchmark**,
> and release a **dataset** of N questions over M haystacks instantiating it."

Say "instance set" for one `*_out/` directory, "instance" for one
(haystack, question, answer) triple. Never call the whole thing "a dataset" in
the title — it undersells the construction work, which is the actual novelty.

---

## 8. What is mechanically verified — the "is there another hole?" answer

Every defect found in this benchmark so far had the same shape: **a property the
benchmark asserted, with no measurement behind it.** Leakage was assumed until a
solver tested it. Entity rankings were assumed contested until a prior oracle
tested them. Haystacks were assumed to hit their length until someone compared
`n_tokens` to the target. The twin was assumed matched because it was checked by
hand once.

So the defence is not "we looked hard", it is a **standing check per claim**.
Run all four before any release:

```bash
python tests/test_golden.py           # the build is deterministic
python scripts/quality_audit.py       # + pair check; add --certify 250 pre-release
python scripts/trivial_baseline.py --sets *_out
python scripts/style_solver.py --config configs/*.json   # gate (d), added 2026-08-25
python scripts/verify_release.py      # the written files are what they claim
```

> **Gate (d) is the newest and the least obvious.** It answers a question the
> other three structurally cannot: can the label be recovered from a record's
> *shape* — length, final period, `!`/`?` — with no words at all? A corpus can
> hand its labels over through formatting and every other solver will pass it.
> See `DESIGN_DECISIONS.md` D15. The number to read is not either half's lift but
> **the gap between a twin's two halves**, since an asymmetric bias is what
> confounds the cross-lingual claim.

| Claim the benchmark makes | What proves it | Where |
|---|---|---|
| Every answer is correct for its haystack | recomputed from the parquet by an implementation sharing no code with the builder, compared byte-for-byte | `verify_release.py` |
| Answers computed twice at build time | Polars path and pure-Python path asserted equal | `verified_gt` |
| Rebuilds are byte-identical | fixture rebuilt and byte-compared | `test_golden.py` |
| Nothing is grep-solvable | label surface forms searched in the **shipped** haystack text | `verify_release.py` |
| No shortcut solver beats the answer distribution | leakage + majority baselines | `trivial_baseline.py` |
| Nothing is answerable without the context | context-free prior oracle vs correctly-modelled chance | `quality_audit.py` |
| Questions need aggregation, not retrieval | depth and margin measured per question | `quality_audit.py` |
| A family is certified, not just sampled | hundreds of deduplicated generator draws | `--certify` |
| The paired twin really is record-identical | row-ids, labels, halves, drift target, gold answers | `quality_audit.py` |
| Haystacks reach their advertised length | `n_tokens` vs target, per haystack | manifest + `[short-haystack]` |
| Families are not silently missing | quota vs realized | `[starved]` warning |
| The haystack matches its metadata | text re-joined from the parquet and compared; char offsets spot-checked | `verify_release.py` |
| No stale or orphaned files ship | meta parquets cross-checked against `haystacks.jsonl` | `verify_release.py` |
| Every set is licensed before release | configs cross-checked against the policy table | `publish_hf.py` |

**What is NOT mechanically verifiable, and never will be:**

- **Source label noise.** Requires a human reading Turkish. This is the one
  remaining assumption with no measurement, and it is the benchmark's accuracy
  ceiling.
- **Threshold choices.** Measured and recommended by `--audit`, but a judgement.
- **Whether the task is the right task.** That is the paper's argument, not a test.

If a new defect appears, it will be in one of those three. Anything mechanical is
now covered by a standing check that fails loudly.

## 9. The invariants — break these and the thesis breaks

1. Every answer is computed by two independent code paths and asserted equal.
2. `VERSION` and `tests/golden/` move together, in the same commit.
3. `src/scoring.py` is frozen before the first model run and never touched after.
4. No data in git. Code + configs + manifests reproduce everything.
5. Any filter applied to one language of the intent twin is applied to the other,
   as a **union** over the locale pair — otherwise the "control" isn't one.
6. A family ships only if it beats every shortcut baseline (leakage, majority,
   and — pending — the corpus-prior oracle).

---

## 10. "Why did you remove that?" — the viva crib sheet

Every deletion, filter, and threshold in this benchmark, with the one-line answer
and where the evidence lives. **Nothing here was removed to make numbers look
better; every item makes the benchmark harder or smaller.** Full write-ups in
`DESIGN_DECISIONS.md`.

| What was removed / changed | Why | Cost | Ref |
|---|---|---|---|
| Records whose text contains any label word | Made questions grep-solvable. A substring solver scored 0.733 on `most_common` vs 0.333 chance. | 0.4–0.9% of rows | D1 |
| 12 MASSIVE intents (60 → 48) | Classes with <100 rows are the rarest in *every* haystack, so `least_common` was answerable with no context (`cooking_query` was the gold answer 10/10 times). | ~3% of the intent pool | D3 |
| 15,411 We-Bears rows with multi-aspect labels (`olumsuz,olumlu`) | Ground truth needs exactly one label per record. | 38% of that corpus; retained pool is **not representative** — say so | D7 |
| The airline set's 250K tier | Its corpus is too small: `positive` (2,363 rows) cannot reach a 1/3 share in a 7,400-record haystack, so `most_common` answered itself. | Airline set caps at 100K | D6 |
| `top_k` on `vitamins_tr` and `amazon_hpc_en` | *Exact ordering* stayed predictable from the corpus (z=+5.5 and +3.7) even after entity randomization. Argmax decorrelates easily; permuting three positions does not. Ships on `tr_oolong` only. | One family on two sets | D9 |
| `top_k` everywhere (v0.5.0) | Survived prior-neutrality on one corpus only, and that corpus was withdrawn over undocumented label provenance. A six-entity set also cannot form a candidate set whose corpus counts are near-identical. | Two families on one set | D9 |
| Questions decided by <10 records | Finding 8 records in 3,919 is *retrieval*, not aggregation — the task this benchmark exists to replace. | ~15% of draws rejected | D9 |
| Questions with a margin below the threshold | A gap of 1–2 records is inside source label noise, so the question measures annotation error. | rejected at build time | D9 |
| `<<<KAYIT>>>` separator | A Turkish word inside the **English** haystacks; it also tokenizes differently per language, a confound in a matched-twin design. | none | D12 |
| `notr` → `nötr`, `artti` → `arttı` | Wrong Turkish. Also a scoring hazard: a model answering `nötr` scored **0** on the vitamins set. | none | D12 |
| Hardcoded `mı`/`mi` question particle | Turkish vowel harmony: *"akbank mı yoksa mng kargo **mi**"* is ungrammatical; it must be **mu**. | none | D12 |

### Thresholds — the honest version

These are **calibrated, not derived from first principles**, and a jury may ask.
The defensible answer is that each was *measured* on trial haystacks and the
measurement is reproducible (`--audit` prints it), not that it is optimal.

| Knob | Value | How it was chosen |
|---|---|---|
| `min_entity_examples` | 15 | soft eligibility; the real floor is enforced on the answer |
| `min_answer_count` / `min_entity_answer` | 20 / 10 | below this an answer is spottable rather than countable |
| `min_rank_margin` | 0.10 (K=3), 0.03 (K=48) | **axis-specific because it must be**: at 48 classes a 10% gap between adjacent ranks is rarer than the family can supply, and the family starves |
| `entity_band_tol` | 0.05 | tight — the entity axis has no prior randomization of its own |
| `label_band_tol` | 0.15 | measured across three values: 0.05 → only ~13 distinct ranking questions exist (family starves); 0.25 → ~240 but `most_common` keeps a real edge for the corpus prior (z=+2.8); 0.15 → ~150 and the prior is at chance |
| `entity_jitter_sigma` | 1.0 | large enough to decorrelate haystack rankings from corpus rankings |
| audit `--depth` | 10 | locating 10 records among thousands is long-context work; locating 2 is not |

**If asked "did you tune these until the numbers looked good?"** — the opposite.
Every floor *rejects* questions, so each one shrinks the benchmark and lowers
every model's score. The tuning direction was always toward harder. And where a
threshold could not be met, the family was dropped rather than the threshold
lowered (`vitamins_tr` `top_k`).

**If asked "your thresholds differ per dataset — isn't that ad hoc?"** — they
differ because the *sources* differ, and the difference is measured, not assumed.
`--audit` reports the observed rank gaps for any new source and recommends
values; the builder prints a `[starved]` warning if a family produces zero
questions. Both were added precisely so this is not a judgement call.

---

## 11. Versioning — what to cite in the thesis, and how not to break it

**Cite three things, always together:**

1. the **git tag** (`v0.4.0`) — pins the builder, the configs, and the metric;
2. `VERSION` from any `manifest.json` — must equal the tag (it once did not, and
   the tag, manifests, and golden files disagreed);
3. `source_hash_first1000` from the manifest — pins the source corpus, so a
   silently-updated Hugging Face dataset cannot change your numbers unnoticed.

In the thesis, one sentence: *"All results use TR-OOLONG v0.4.0 (git tag v0.4.0,
manifest source hash `…`), scored with the frozen metric in `src/scoring.py`."*

**The rule that prevents a version mismatch.** Once you run the first model:

- **Tag first, then run.** `git tag v0.4.0 && git push --tags` *before* any model
  touches the data. Numbers produced from an untagged working tree cannot be
  reproduced by anyone, including you.
- **Freeze `src/scoring.py`.** Changing the metric after a run silently
  invalidates every earlier score, and nothing will tell you.
- **Improve on a branch, never in place.** Benchmark changes go to a new branch
  and become **v0.5.0** with its own tag. Your thesis keeps citing v0.4.0. Do not
  rebuild the v0.4.0 data directory to "just fix one thing" — the golden test
  will catch the builder change, but it cannot catch results you already wrote
  into a table.
- **If you must upgrade mid-thesis**, re-run *every* model on v0.5.0. Never mix
  results from two versions in one table; a reviewer will ask, and "some rows are
  v0.4.0" is not an answer.

**Hugging Face mirrors this.** Push the dataset with a tag/revision matching the
git tag, and cite `revision=` in the thesis so a reader gets exactly your data.

**Why this matters more here than usual.** The build is deterministic, so a
version mismatch is *silent*: a rebuilt v0.5.0 looks like a perfectly valid
dataset and produces perfectly valid numbers that simply are not comparable to
the ones in your draft.

---

## v0.6.0 — what changed, in one place

**The entity is now printed.** `[[Nutraxin]] <review text>`. Before v0.6.0 the
brand lived only in a metadata column the model never saw, so **all 118 entity
questions were unanswerable** — gold answers of 10–92 against brands appearing
0–11 times. No gate caught it, because all four solvers test whether a question
is answerable *too easily*, never whether it is answerable *at all*. See D17.

- Guard: the builder **raises** if an entity family is emitted while
  `render_entity` is false.
- The leakage filter now masks the **rendered** record, so a brand name
  containing a label word (`The Pressure Positive Co.`) is dropped.
- The label stays latent, so the family is still latent aggregation, not string
  counting.

**New family `label_vs_label`** — OOLONG's "is A more, less, or equally common
than B". Ships on all eight sets. 3-way at 48 classes, 2-way at 3 (D18). It is
the least stable family: `musteri_tr`↔`marc_en` now sits at 0.030, the widest
of the four pairs.

**New tool `scripts/check_pair.py`** — screens a candidate corpus pair before you
build it, against the §11 criteria, with a COMPATIBLE / WITH CAVEATS /
INCOMPATIBLE verdict. Requires `licence` and `label_provenance` declared in each
config.

**Headline after the rebuild:** 8 sets · 110 haystacks · **1,254 questions** ·
**28.3M tokens** · 10 families · 630 tr / 624 en · 36,250–987,623 tokens.
