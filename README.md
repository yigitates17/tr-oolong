# TR-OOLONG

A long-context **aggregation** benchmark for Turkish, with English counterparts
built by the same pipeline.

Each document is thousands of real records (reviews, complaints, news
articles, voice-assistant commands) joined into one long text, from 36K to 1M
tokens. Each question asks about the whole collection:

> *Bu kayıtlarda hangisi daha çok: 'turizm' etiketli kayıtlar mı, 'magazin' etiketli kayıtlar mı?* → **magazin** (44 against 41, out of 266 articles)
> *Bu kayıtlarda kaç tane 'ulaşım' etiketli kayıt var?* → **166**

The label of a record is never written in the text, so a model has to decide
what each record is about and then count. The core questions (the first
example) compare two categories whose counts are so close that neither
sampling part of the document nor searching for the relevant records answers
them; see [What each question measures](#what-each-question-measures). Every answer is computed from the
source dataset's own labels, so no one writes an answer key by hand.

The construction follows OOLONG (Bertsch et al., 2025, arXiv:2511.02817), whose
build code was not released; this is an independent implementation.

- **Data:** <https://huggingface.co/datasets/yigitates17/tr-oolong> (v0.7.1; v0.8.0 below is built and not yet published)
- **Datacard:** [`DATACARD.md`](DATACARD.md), sources, licences, known issues
- **Why each choice was made:** [`DESIGN_DECISIONS.md`](DESIGN_DECISIONS.md)

Developed at the Institute for Data Science & Artificial Intelligence (DSAI),
Boğaziçi University, as MSc thesis work.

## At a glance

**11 subsets · 195 documents · 2,277 questions · 50.7M tokens · 7 question types**
(1,558 Turkish, 719 English). Every question has a role: **174 core**, 265
retrieval, 1,838 control (see below). Lengths are counted with the
`Qwen/Qwen3-8B` tokenizer.

| subset | lang | records are | labels | docs | questions | core | longest doc | text shipped |
|---|---|---|---:|---:|---:|---:|---:|:---:|
| `sikayet_tr` | tr | consumer complaints | 29 | 25 | 333 | 33 | 1.0M | no |
| `interpress_tr` | tr | news articles | 16 | 25 | 309 | 9 | 1.0M | no |
| `sinema_tr` | tr | film reviews (1-10 stars) | 10 | 20 | 242 | 2 | 497K | yes |
| `vitamins_tr` | tr | supplement reviews (sentiment) | 3 | 20 | 169 | 0 | 497K | yes |
| `musteri_tr` | tr | shopping reviews (sentiment) | 3 | 20 | 199 | 0 | 496K | yes |
| `tr_intent` | tr | voice commands (intent) | 48 | 10 | 151 | 31 | 100K | yes |
| `tr_intent_paired` | tr | voice commands (intent) | 48 | 10 | 155 | 35 | 99K | yes |
| `amazon_hpc_en` | en | health product reviews (sentiment) | 3 | 25 | 222 | 0 | 988K | no |
| `marc_en` | en | shopping reviews (sentiment) | 3 | 20 | 194 | 1 | 492K | yes |
| `en_intent` | en | voice commands (intent) | 48 | 10 | 148 | 28 | 100K | yes |
| `en_intent_paired` | en | voice commands (intent) | 48 | 10 | 155 | 35 | 75K | yes |

Three subsets ship questions and answers only, because their sources grant no
right to redistribute the text. The build is deterministic, so the text can be
rebuilt locally byte for byte (see [Building](#building-and-adding-a-dataset)).

### Turkish/English pairs

| pair | what is matched | use it for |
|---|---|---|
| `tr_intent_paired` / `en_intent_paired` | **the same 3,000 utterances** (MASSIVE is a human translation), same order, same labels. All 155 questions have the same answer in both languages. | a paired test: any score gap is not caused by the questions |
| `tr_intent` / `en_intent` | same corpus, same **token budget** | comparing languages at equal cost |
| `musteri_tr` / `marc_en` | different corpora, same task (star-rating sentiment), similar record length | comparing languages on natural text |
| `vitamins_tr` / `amazon_hpc_en` | different corpora, same task, same product area (supplements, health) | comparing languages on natural text |

`sikayet_tr`, `interpress_tr` and `sinema_tr` have no English partner. They were
added because 3-label sets cannot produce questions with small answers.

**Cross-lingual comparisons are made within a pair, never between the Turkish
and English totals** (which differ because three subsets are Turkish only).
Compare the two halves of a pair on the same length tiers and the same
question types. `amazon_hpc_en` has a 1M tier that `vitamins_tr` lacks, so that
pair is compared up to 500K. Core questions exist in both languages only in
the two intent pairs (35 + 35 identical ones in the paired sets; 31 and 28 in
the token-matched sets); the review pairs carry control questions only.

| role | Turkish | English |
|---|---:|---:|
| core | 110 | 64 |
| retrieval | 213 | 52 |
| control | 1,235 | 603 |

## Question types

| type | example | answer | role | count |
|---|---|---|---|---:|
| `close_comparison` | which are there more of, A or B? (two frequent labels, counts very close) | a label | core | 174 |
| `count` with `"rare": true` | how many records have label X? (true answer 5 to 30) | a number | retrieval | 265 |
| `count` | how many records have label X? | a number | control | 656 |
| `proportion` | what percent (or per mille) have label X? | a number | control | 492 |
| `label_vs_label` | is X more common, less common, or as common as Y? (counts at least 15% apart) | a word | control | 292 |
| `most_common` / `least_common` / `second_most` | which label is most / least / second most common? | a label | control | 398 |

Rare-label counts are worded exactly like any other count.

Removed types: `shift` ("did X rise or fall in the second half?", v0.7.0),
answered by reading 50 records at each end; and the three brand types
(`entity_count`, `entity_argmax`, `pairwise`, v0.8.0), answered perfectly by
searching the text for the printed brand name and reading about 2% of the
document.

### Why the Turkish intent questions use English label names

In `tr_intent` and `tr_intent_paired` the question is in Turkish but the label
is MASSIVE's English identifier (`transport_taxi`, `play_music`). This is
deliberate: **translating the labels puts the answer back into the text.**
Turkish is verb-final, so a label like `alarm_kur` appears word for word inside
utterances such as *"iki saat sonrasına alarm kur"*. Measured on all 15,075
utterances:

| labels used | records containing their own label |
|---|---:|
| English identifiers (**shipped**) | 0.00% |
| Turkish, imperative (`müzik_çal`) | 3.13% (472 records) |
| Turkish, dictionary form (`müzik_çalmak`) | 0.14% (21 records) |

Nothing Turkish is lost: the Turkish is in the text being classified, and the
label is only the name of the bucket. The translated variants are kept in
`configs/experimental/` and are not part of the release.

## Relation to OOLONG

| | OOLONG (Bertsch et al., 2025) | TR-OOLONG |
|---|---|---|
| languages | English | Turkish, with English counterparts built the same way |
| document length | 1K to 4M tokens (synthetic split) | 36K to 1M tokens |
| labels per dataset | 2 to 10 | 3, 10, 16, 29, 48 |
| narrowing to a subset | to users or months printed on every record | none (brand questions removed, see below) |
| questions over dates | yes, and reported as the hardest group | none yet (`interpress_tr` has dates) |
| questions that resist sampling and search | none found | 174 close comparisons |
| same question, same answer in two languages | no | yes (`*_intent_paired`) |
| numeric score | `partial` (0.75 per unit of error) | `partial`, plus `relative` for large answers |
| published shortcut checks | none | yes, reports in `manifests/` and `experiments/` |

OOLONG makes answers small by narrowing questions to listed users or a month.
Both are printed on every record, so a string search finds the relevant
records: for user-narrowed questions it reads a median of 0.8% of the document
and gives the exact answer 99% of the time (month-narrowed: 7.6%, 99%). Its
whole-document comparisons have a median gap of 38% between the two counts, so
sampling answers them. TR-OOLONG's control questions share the sampling
weakness; its core questions were built to avoid both
([`experiments/REPORT.md`](experiments/REPORT.md), experiments 5, 7 and 8).

## Using it

```python
from datasets import load_dataset
qs = load_dataset("yigitates17/tr-oolong", "sikayet_tr", split="test")
```

Each subset has `questions.jsonl`, `manifest.json` and,
where the licence allows, `haystacks.jsonl`. Field-by-field description:
[`DATACARD.md`](DATACARD.md#fields).

- **Join and pool on `uid`**, never on `id`. `id` is unique only within one
  subset; pooling on it silently drops 57% of the benchmark.
- **Send the model only the haystack text and the question.** Other haystack
  fields are build metadata.
- **Score with [`src/scoring.py`](src/scoring.py).** It returns four numbers per
  question:
  - `exact`: 1 if correct, else 0.
  - `partial`: OOLONG's own formula, `0.75 ** |error|`, kept for comparability.
  - `relative`: `1 - |error| / answer`, floored at 0, for large answers, where
    `partial` gives almost nothing for being 2% off.
  - `primary`: the one to report. `exact` for word answers (including every
    core question), `partial` for rare-label counts, `relative` for the other
    numbers.
- [`scripts/run_eval.py`](scripts/run_eval.py) runs any OpenAI-compatible
  endpoint (vLLM, Ollama, hosted APIs) and resumes after interruption.

**How to report a score.** Report the `primary` score **per role** (core,
retrieval, control), never pooled into one number, and state how the model saw
the document (whole document in one prompt, or an agent with code tools that
can sample or search it). `run_eval.py` prints it this way.

## How the benchmark is built

Every subset goes through the same pipeline. Each step can reject a source or
a question, and the rejections are recorded in
[`DATASET_REVIEW.md`](DATASET_REVIEW.md) and [`DESIGN_DECISIONS.md`](DESIGN_DECISIONS.md).

```
1. FIND A LABELLED CORPUS
   The label is the answer key, so unlabelled text is unusable.
   Preferred label sources: the writer's own rating > professional
   annotators > crowd workers. Undocumented labels are rejected.
        |
2. SCREEN IT  (build_tr_oolong.py --audit)
   class balance, the longest document it can fill, whether record
   length or punctuation gives the label away, licence
        |
3. FOR A PAIR: FIND THE ENGLISH PARTNER  (check_pair.py)
   same label source, similar record length, similar surface shape,
   same reachable lengths; a licence that forbids sharing rules it out
        |
4. BUILD  (build_tr_oolong.py --build)
   - remove records whose text contains a label name
   - drop labels with too few examples
   - for each document, draw a random label mix, sample records to the
     target length (counted with the Qwen3-8B tokenizer), join them with
     a symbol separator
   - generate questions; compute every answer twice, by two independent
     pieces of code, and require them to agree
        |
5. CHECK  (the release checks below)
   Can the questions be answered by searching for label names, by always
   giving the most common answer, from the source corpus's overall label
   shares, from record length and punctuation, or by sampling part of the
   document? Question types that a check breaks on a source are switched
   off for that source, and the omission is recorded.
        |
6. PUBLISH  (publish_hf.py)
   one Hugging Face config per source, each with its own licence; text is
   withheld where the licence does not allow sharing it
```

Screening (step 2) and checking (step 5) can disagree, and step 5 decides: a
source can look risky before building and turn out fine once documents are
built with random label mixes. Never accept or reject a source on step 2 alone.

## What each question measures

A model with code tools has two ways to answer without reading everything:
**sampling** (read a small random part and scale up) and **search** (find the
relevant records by a word or topic and read only those). Every question type
was attacked both ways by simulated readers: short programs, not AI models,
told the true label of each record they read, so they show what a strategy can
achieve. Full setup and examples: [`experiments/REPORT.md`](experiments/REPORT.md).
No AI model has been run on the benchmark yet.

| role | question types | strongest shortcut found | a reader of everything |
|---|---|---|---|
| **core** (174) | close comparisons | 0.64 (reading the 10% most relevant records); sampling half the document 0.63 | 0.85 if it labels 95% of records right, 0.77 at 90% |
| **retrieval** (265) | rare-label counts | searching by topic and reading the top 5%: 0.53 under `partial` | depends strongly on labelling accuracy |
| **control** (1,838) | counts, proportions, rankings, wide comparisons | sampling 5%: about 0.8 under `relative` | about 0.9 or more |

- **Core questions** are the evidence that a model read and judged the whole
  document. Guessing gets 0.50. On the two paired intent sets, where the two
  categories are small, topic search does better (0.73 and 0.81).
- **Retrieval questions** show whether a model can find a few records by their
  meaning.
- **Control questions** show whether a model can classify the records at all.
  They are not evidence that it read the whole document: a 5% sample answers
  them almost as well.

**Checks every release passes.** Searching the text for the label name (0 of
856,798 shipped records contain their label; such records are removed at build
time), always giving the most common answer, answering from the source corpus's
overall label shares, and guessing labels from record length and punctuation.

## Building and adding a dataset

Tested with Python 3.12. Pinned versions are in `requirements.txt`; `polars`
and `transformers` affect output bytes.

```bash
pip install -r requirements.txt
python scripts/sinema_tr.py                                   # fetch one source
python src/build_tr_oolong.py --config configs/sinema_tr.json --build
python tests/test_golden.py                                   # build is deterministic
```

Fetch scripts: `massive.py` (intent sets), `vitamins.py`, `musteri.py`,
`marc_en.py`, `health.py` (`amazon_hpc_en`), `sikayet_tr.py` (needs
`ticaret-yorum.csv` downloaded from Kaggle by hand), `interpress_tr.py`,
`sinema_tr.py`.

**To add a new dataset**, you need a labelled corpus with a free-text column, a
label column, at least about 1,000 records per label, and a licence you can
state.

1. Write a config (copy one from `configs/`). The main settings are the text,
   label and optional brand columns, the target lengths, and the declared
   `licence`, `label_provenance` and `text_provenance`.
2. `python src/build_tr_oolong.py --config configs/new.json --audit` reports
   size, balance, leakage and which thresholds the source can support.
3. `python scripts/check_solo.py configs/new.json` (or `check_pair.py a.json b.json`
   for a Turkish/English pair) runs the licence, provenance and shortcut checks
   as one PASS/WARN/FAIL table.
4. Build with `--build`, then run the release checks below. Close comparisons
   and roles are produced by the builder itself; to test a new subset's core
   questions against every shortcut, run `python experiments/attack_v08.py`.
5. Add a licence entry for the subset in `POLICY` in `scripts/publish_hf.py`.

**Choosing an English partner for a Turkish set.** Start from the Turkish
corpus (it is the scarce side) and look for an English one that matches on,
in order of how often each rules a candidate out:

1. **How labels were made.** Both halves should get labels the same way. The
   writer's own star rating on both sides is the strongest option.
2. **Record length.** Large gaps change what one record means to a model.
3. **Surface shape.** The style check (`style_solver.py`) must show a similar
   result on both halves; the gap matters, not either level.
4. **Reachable lengths.** Both halves must fill the same length tiers.

A licence that does not allow redistribution rules a candidate out even if it
matches better. Every candidate considered, and why it was kept or rejected,
is in [`DATASET_REVIEW.md`](DATASET_REVIEW.md).

**Release checks.** A rebuild is accepted when all of these pass (list every
subset's output folder explicitly; zsh does not split a variable into words):

```bash
python tests/test_golden.py
python scripts/verify_release.py            # answers recomputed, no leakage, ids unique
python scripts/trivial_baseline.py --sets <all *_out folders> --out manifests/baseline_report.json
python scripts/quality_audit.py --certify 250 --json manifests/quality_audit.json
python scripts/style_solver.py --config configs/*.json --json manifests/style_audit.json
python scripts/sampling_solver.py --json manifests/sampling_audit.json
python tests/test_close.py
python scripts/publish_hf.py --out hf_release            # dry run; add --repo ... --push to upload
```

## Limitations

- No model has been run yet. Every statement about shortcuts comes from
  simulated readers.
- Only 174 questions are core. Answered right or wrong, they give a margin of
  error of about ±0.07 on a model's core score: enough to tell reading from
  skimming, not enough for fine comparisons between similar models. Almost all
  come from the intent and complaint sets; the 3-label review sets have one.
- Control questions (81%) can be answered by sampling. Report per role.
- Questions on one document are not independent. On 3-label sets, 12 questions
  rest on about two underlying numbers, and 337 document-label pairs are asked
  both as a count and as a proportion. For statistical claims, the unit is the
  document.
- Documents of the same length within a subset share 20-39% of their records;
  confidence intervals over them need clustered errors.
- Label quality: the intent labels were checked on 150 records (2.7-9.3% wrong,
  part of it translation error in the Turkish half). The complaint and news
  categories were set by the filer and the publisher; how predictable they are
  from text is what bounds scores (see datacard).
- Every record comes from a public dataset, so a model that memorised a
  dataset's labels could label records without reading them. Not tested.
- No time-based questions, although `interpress_tr` has publication dates.
- Lengths are counted with one tokenizer. The Turkish/English token ratio on
  the same sentences ranges from 0.57x (BERTurk) to 2.16x (GPT-2), so it
  reflects the tokenizer, not Turkish itself.
- Three subsets cannot ship text; two of them have no declared licence at all.

## Repository

```
src/build_tr_oolong.py     the builder: config in, haystacks + questions + manifest out
src/scoring.py             the metric (freeze before the first model run)
configs/                   one config per subset; configs/experimental/ = Turkish-label variants, not released
scripts/                   fetch scripts, release checks, publishing, evaluation
experiments/               shortcut experiments; REPORT.md explains each in plain language
manifests/                 committed reports from the release checks
tests/                     golden test: a fixed fixture must rebuild byte-identically
weekly_summaries/          progress reports for thesis supervision
```

Working notes: `DESIGN_DECISIONS.md` (reason for each threshold, cited from code
as D1-D22), `PAPER_NOTES.md` (claims for the write-up), `DATASET_REVIEW.md`
(every source considered), `COMPARISON.md` (OOLONG and TR-OOLONG side by side),
`REVIEW.md`, `ROADMAP.md`, `CHEATSHEET.md`.

## Licence and citation

Code: MIT (`LICENSE`). Each data subset keeps its source's licence; see the
datacard. Three are CC-BY-SA-4.0 (share-alike).

```bibtex
@misc{troolong,
  title  = {TR-OOLONG: A Turkish Long-Context Aggregation Benchmark},
  author = {Ate{\c{s}}, Yi{\u{g}}it},
  year   = {2026},
  note   = {Bo{\u{g}}azi{\c{c}}i University, Institute for Data Science \& Artificial Intelligence},
  url    = {https://github.com/yigitates17/tr-oolong}
}
```

Please also cite OOLONG (Bertsch et al., 2025) and the source corpus of each
subset you use.
