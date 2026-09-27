# TR-OOLONG

A long-context **aggregation** benchmark for Turkish, with English counterparts
built by the same pipeline.

Each document is thousands of real records (reviews, complaints, news
articles, voice-assistant commands) joined into one long text, from 36K to 1M
tokens. Each question asks about the whole collection:

> *Bu kayıtlarda kaç tane 'ulaşım' etiketli kayıt var?* → **166**
> *Which label is the least common in these records?* → **play_audiobook**

The label of a record is never written in the text, so a model has to decide
what each record is about and then count. Every answer is computed from the
source dataset's own labels, so no one writes an answer key by hand.

The construction follows OOLONG (Bertsch et al., 2025, arXiv:2511.02817), whose
build code was not released; this is an independent implementation.

- **Data:** <https://huggingface.co/datasets/yigitates17/tr-oolong> (v0.7.1)
- **Datacard:** [`DATACARD.md`](DATACARD.md), sources, licences, known issues
- **Why each choice was made:** [`DESIGN_DECISIONS.md`](DESIGN_DECISIONS.md)

Developed at the Institute for Data Science & Artificial Intelligence (DSAI),
Boğaziçi University, as MSc thesis work.

## At a glance

**11 subsets · 195 documents · 2,240 questions · 50.7M tokens · 9 question types**
(1,515 Turkish, 725 English questions). Lengths are counted with the
`Qwen/Qwen3-8B` tokenizer.

| subset | lang | records are | labels | docs | questions | longest doc | text shipped |
|---|---|---|---:|---:|---:|---:|:---:|
| `sikayet_tr` | tr | consumer complaints | 29 | 25 | 300 | 1.0M | no |
| `interpress_tr` | tr | news articles | 16 | 25 | 300 | 1.0M | no |
| `sinema_tr` | tr | film reviews (1-10 stars) | 10 | 20 | 240 | 497K | yes |
| `vitamins_tr` | tr | supplement reviews (sentiment) | 3 | 20 | 236 | 497K | yes |
| `musteri_tr` | tr | shopping reviews (sentiment) | 3 | 20 | 199 | 496K | yes |
| `tr_intent` | tr | voice commands (intent) | 48 | 10 | 120 | 100K | yes |
| `tr_intent_paired` | tr | voice commands (intent) | 48 | 10 | 120 | 99K | yes |
| `amazon_hpc_en` | en | health product reviews (sentiment) | 3 | 25 | 292 | 988K | no |
| `marc_en` | en | shopping reviews (sentiment) | 3 | 20 | 193 | 492K | yes |
| `en_intent` | en | voice commands (intent) | 48 | 10 | 120 | 100K | yes |
| `en_intent_paired` | en | voice commands (intent) | 48 | 10 | 120 | 75K | yes |

Three subsets ship questions and answers only, because their sources grant no
right to redistribute the text. The build is deterministic, so the text can be
rebuilt locally byte for byte (see [Building](#building-and-adding-a-dataset)).

### Turkish/English pairs

| pair | what is matched | use it for |
|---|---|---|
| `tr_intent_paired` / `en_intent_paired` | **the same 3,000 utterances** (MASSIVE is a human translation), same order, same labels. All 120 questions have the same answer in both languages. | a paired test: any score gap is not caused by the questions |
| `tr_intent` / `en_intent` | same corpus, same **token budget** | comparing languages at equal cost |
| `musteri_tr` / `marc_en` | different corpora, same task (star-rating sentiment), similar record length | comparing languages on natural text |
| `vitamins_tr` / `amazon_hpc_en` | different corpora, same task, both carry a brand per record | brand questions in both languages |

`sikayet_tr`, `interpress_tr` and `sinema_tr` have no English partner. They were
added because 3-label sets cannot produce questions with small answers, and
small answers are what resist skimming (see [What is measured](#what-is-measured-about-difficulty)).

## Question types

| type | example | answer | count |
|---|---|---|---:|
| `count` | how many records have label X? | a number | 921 |
| `proportion` | what percent (or per mille) have label X? | a number | 492 |
| `label_vs_label` | is X more common, less common, or as common as Y? | a word | 292 |
| `most_common` / `least_common` / `second_most` | which label is most / least / second most common? | a label | 398 |
| `entity_count` | how many reviews of brand B have label X? | a number | 87 |
| `entity_argmax` / `pairwise` | which brand has the most X? which of two brands? | a brand | 50 |

265 of the `count` questions are **rare-label counts** (`"rare": true`): the true
answer is between 5 and 30. They are worded exactly like any other count.

A tenth type, `shift` ("did X rise or fall in the second half?"), was removed
in v0.7.0 because reading 50 records at each end answers it.

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
| grouping | synthetic user ids and dates added to each record | real brands printed in the text (one pair) |
| questions over dates | yes, and reported as the hardest group | none yet (`interpress_tr` has dates) |
| same question, same answer in two languages | no | yes (`*_intent_paired`) |
| numeric score | `partial` (0.75 per unit of error) | `partial`, plus `relative` for large answers |
| published shortcut checks | none | five, with reports in `manifests/` |

OOLONG's answers are usually small because most questions are first narrowed
to one user or one date range. Here most answers are large (hundreds to
thousands), which is what makes sampling work so well; see below.

## Using it

```python
from datasets import load_dataset
qs = load_dataset("yigitates17/tr-oolong", "sikayet_tr", split="test")
```

Each subset has `questions.jsonl`, `difficulty.jsonl`, `manifest.json` and,
where the licence allows, `haystacks.jsonl`. Field-by-field description:
[`DATACARD.md`](DATACARD.md#fields).

- **Join and pool on `uid`**, never on `id`. `id` is unique only within one
  subset; pooling on it silently drops 57% of the benchmark.
- **Send the model only the haystack text and the question.** Other haystack
  fields are build metadata.
- **Score with [`src/scoring.py`](src/scoring.py).** It returns three numbers per
  question:
  - `exact`: 1 if correct, else 0.
  - `partial`: OOLONG's own formula, `0.75 ** |error|`, kept for comparability.
  - `relative`: `1 - |error| / answer`, floored at 0. Added because most answers
    here are in the hundreds or thousands, where `partial` gives almost nothing
    for being 2% off.
- [`scripts/run_eval.py`](scripts/run_eval.py) runs any OpenAI-compatible
  endpoint (vLLM, Ollama, hosted APIs) and resumes after interruption.

**How to report a score.** Always state how the model saw the document (whole
document in one prompt, or an agent with code tools that can sample it). Report
per question type and per difficulty band next to the reference readers in
`manifests/sampling_audit.json`, not as one pooled number. The reasons are in
the next section.

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

## What is measured about difficulty

Every check below uses **simulated readers**: short programs, not AI models.
They are given the true label of every record they look at, so they can only
do better than a real model reading the same records. No model has been run on
the benchmark yet.

**Checks that pass.** Each tries to answer without doing the task, and fails:

| check | result |
|---|---|
| search the text for the label name | 0 of 856,798 shipped records contain their label; records that did were removed at build time |
| always give the most common answer | no better than chance per question type |
| answer from the source corpus's overall label shares, without opening the document | no better than chance (one flagged tier, see datacard) |
| guess the label from record length and punctuation | no gain over the baselines on any subset |

**Checks that partly succeed, and limit what the benchmark shows.**

1. **Most questions can be answered from a sample.** A reader that looks at 5%
   of the records and scales up gets most `count`, `proportion` and ranking
   questions nearly right, because their answers are large. Reading the first
   and last 2.5% works as well as a random 5%, so document order is no defence.
2. **Guessing from the record count scores 0.43-0.55 on counting questions.** A
   reader that opens nothing, counts separators and divides by the number of
   labels gets this much partial credit under `relative`.
3. **Longer is not harder under `relative`.** Reading 1,000 records scores about
   the same at 100K tokens as at 1M.

**Per-question difficulty grades** (`difficulty.jsonl`). Each question was
attacked by four 5%-readers (random, first 5%, first and last 2.5%, evenly
spaced); its grade comes from the best score any of them got:

| grade | best reader's score | questions |
|---|---|---:|
| very hard | below 0.35 | 259 (11.6%) |
| hard | 0.35 to 0.60 | 140 |
| moderate | 0.60 to 0.80 | 232 |
| easy | 0.80 and above | 1,609 (71.8%) |

Read the grades as *"which questions these four readers can answer"*, and
nothing stronger:

- **The very-hard counting questions are the ones with small answers** (every
  one of them is 24 or less). The four readers fail there because seeing no
  matching record makes them answer 0. A reader that instead answers "about 12"
  when it sees 0 or 1 matches moves 145 of the 226 very-hard numeric questions
  out of the band ([`experiments/small_guess.py`](experiments/small_guess.py)).
- **The gap between band scores does not show how much a model read.** On the
  very-hard questions, that guessing 5% reader scores 0.48 while a reader that
  opens every record but mislabels one in ten scores 0.41
  ([`experiments/band_gap.py`](experiments/band_gap.py)).
- `musteri_tr` has no very-hard questions and `marc_en` has one.

What the benchmark does support: a model must **classify latent labels in Turkish
text and combine the results**. Small-answer questions additionally demand very
accurate classification of every relevant record. Separating "did not read" from
"read but misclassified" needs a direct measurement of the model's per-record
accuracy, which is planned alongside the first model runs.

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
4. Build with `--build`, then run the release checks below.
5. **Grade the questions:** `python scripts/grade_questions.py --sets new_out --trials 200`.
   The builder does not do this itself, and `check_solo.py` does not check
   skimming. `publish_hf.py` refuses to package a subset without grades.
6. Add a licence entry for the subset in `POLICY` in `scripts/publish_hf.py`.

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
python scripts/grade_questions.py --trials 200
python scripts/publish_hf.py --out hf_release            # dry run; add --repo ... --push to upload
```

## Limitations

- No model has been run yet. Every difficulty statement comes from simulated readers.
- Most questions can be answered by sampling (above). Report per band and per
  question type, and state the reading setup.
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
- Brand questions rest on one corpus pair and only appear at 500K tokens and above.
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
scripts/                   fetch scripts, release checks, grading, publishing, evaluation
experiments/               one-off analyses with their setup written at the top
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
