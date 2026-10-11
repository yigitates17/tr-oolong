**Pre-freeze candidate, 7 October 2026.** The public dataset remains v0.10.0.
The current builder is v0.11.0-rc1. Private candidate data live under
`scratch/prefreeze/`; they are not a published or human-validated release.

This document is the completion checklist for dataset creation. Model runs,
paper writing and submission preparation are outside this checklist.

| Item | Automated work | Remaining human dependency |
|---|---|---|
| Answer balancing | Independent shuffled schedules for winner and option position; periodic attacks measured | None |
| Question contracts | Candidate-scoped rankings, exact equality, explicit half-up rounding, strict integer scoring | None |
| Conflicting duplicates | Exclude normalized texts with conflicting final task labels; retain multiple star values mapping to the same sentiment | Review remaining ambiguity |
| Keyword policy | Measure filtered/unfiltered pools; retain ordinary topic words in candidate; retain boilerplate, explicit-rating and HTML cleaning | Naturalness and label review |
| Partitions | Group normalized duplicates globally and MASSIVE translations jointly; reserve 10% development / 90% prospective test | None |
| Shortcut audit | Question-only, metadata, source-prior, fixed/adaptive oracle sampling, lexical matching and development-trained NB | Interpret alongside human label quality |
| Annotation | Blind Turkish/English sheets, source key kept separate, completion and question-impact reports | Fill sheets; adjudicate uncertain cases |
| Answer stability | Compute observed corrected margins and conservative bounds without treating unreviewed labels as correct | Depends on completed annotations; additional review may be necessary |
| Protocol | Task descriptions, role/origin grouping, coverage and all-eligible scores, revision-specific resume | Human review of taxonomy ambiguities |
| Candidate verification | Independent answer recomputation, question contracts, paired labels/questions, published-file hashes, deterministic rebuild checks | Source access on another machine; final validation after annotations |

**Reproduce the candidate.** Use the pinned environment and the original local
source files described in DATACARD. `prepare_prefreeze.py` records full source
hashes, excludes conflicting labels after sentiment conversion, and writes
partitioned sources/configs. It refuses to overwrite an existing candidate.

```sh
.venv/bin/python scripts/prepare_prefreeze.py --out scratch/prefreeze
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false .venv/bin/python src/build_tr_oolong.py --config scratch/prefreeze/configs/test/*.json --build --index scratch/prefreeze/reports/index_test.json
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false .venv/bin/python src/build_tr_oolong.py --config scratch/prefreeze/configs/dev/*.json --build --index scratch/prefreeze/reports/index_dev.json
.venv/bin/python scripts/prefreeze_audit.py --split test
.venv/bin/python scripts/prefreeze_audit.py --split dev --no-classifiers
.venv/bin/python scripts/prefreeze_review.py
.venv/bin/python scripts/prefreeze_review.py --stats
.venv/bin/python -m pytest -q tests
```

Build datasets sequentially, in smaller groups if needed. Never run two heavy
build/audit jobs concurrently. Source acquisition still follows DATACARD;
the candidate does not grant additional redistribution rights. A rebuild from
available source bytes is distinct from proving that a third party can obtain
all upstream sources.

**Your review.** Open `scratch/prefreeze/human_review/README.md`, then the task
definitions and the two CSVs. Enter one permitted label, or `uncertain`, for
each record. Do not open `private_key.json` during blind annotation. Previous
review sheets are preserved. This is a stratified quality screen, including
background classes; its raw error rate is not a population error estimate.

**Fixed protocol for later use.** Models receive task instructions, label
names, document text and one question. They do not receive source files,
source labels, manifests, question IDs/order or other questions' answers.
Keep sessions independent; count preprocessing/search work separately from
tokens given to a language model. Allow valid sampling and search strategies.
Report core-document and ordinary-document core separately, alongside retrieval
and control groups. Do not average their heterogeneous primary metrics.

Report input-length eligibility in each model's actual tokenizer before a run;
never silently truncate. Record failures, retry policy and completion coverage.
The harness reports both successful-response scores and all-eligible scores,
counting missing/failed responses as zero in the latter. Classify transport
errors separately from model refusals and context-capacity limits during run
analysis. A cached answer is valid only for the matching data/protocol/model
configuration fingerprint.

Use parallel intent data for paired language comparisons. Matched-count review
corpora support comparisons across language AND corpus, not language alone.
Cluster uncertainty by document pair and report source-overlap sensitivity.
Gold-label and small-context conditions are diagnostic variants; their scores
must not be pooled into the main benchmark. The development documents provide
small-context plumbing checks, not a matched length-effect experiment.

**Limits on completion claims.** All source pools and legacy eligible label
pairs have already been inspected. The new split is prospective, not evidence
that the authors never saw its records. Normalized exact duplicates are grouped;
semantic near-duplicates require a separate sensitivity audit. Public source
data may be in model pretraining. The representative condition restores words
only within the existing local pools; upstream source selection remains.

Oracle attacks reveal gold labels for selected records, so they demonstrate
what a strategy can do given those labels, not observed LLM behavior. NB topic
ranking scans all text before selecting its 10% oracle budget. Noise simulations
are conditional analyses, not human performance ceilings. A close-comparison
winner is not certified merely because a weak classifier separates its labels.

The candidate may be frozen only after the human review, any required
adjudication and resulting regeneration/verification. No automatic structural
PASS substitutes for that decision. The previously authorized publication step
applies only after the release checks and human-dependent checks pass.
