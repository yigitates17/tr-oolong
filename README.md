# TR-OOLONG

**A long-context aggregation benchmark for Turkish, with English
counterparts.** Status (21 October 2026): **v0.13, provisional, data only**, on
[Hugging Face](https://huggingface.co/datasets/yigitates17/tr-oolong). The
release files (dataset card, construction rules, label maps, provenance,
hashes, Croissant metadata, answer recomputation and scoring scripts) are in
[`release/v0.13/`](release/v0.13/). The generation code will be available to
reviewers with the paper's submission and published here with the paper.

Developed at the Institute for Data Science & Artificial Intelligence (DSAI),
Boğaziçi University, as MSc thesis work.

## What it tests

A model reads one long document made of thousands of short real texts (reviews,
news articles, patients' questions, thesis abstracts, voice-assistant
requests). Every text has a label the model does not see, and each question
asks about the whole document:

> *Yukarıdaki verilerde en sık görülen etiket hangisidir?* (which label is the most common?)
> *Kaç kayıt 'olumsuz' etiketiyle sınıflandırılmalıdır?* (how many records are negative?)
> *Which user has more instances with the label 'sports': User 41076 or User 23810?*

Answering means classifying every record and aggregating exactly. The design
follows OOLONG-synth (Bertsch et al., 2025, arXiv:2511.02817): a random label
mix per document, a user and a date on every record, and counting, user and
timeline questions.

## Datasets

Three tracks. Every dataset ships its text.

| track | dataset | records are | labels | longest document |
|---|---|---|---|---|
| Turkish | `musteri_tr` | shopping reviews | positive / negative | 1M tokens |
| Turkish | `doktor_tr` | patients' questions to doctors | 9 specialties | 2M |
| Turkish | `trnews2025_tr` | news articles | 9 sections | 4M |
| Turkish (reported separately) | `vitamins_tr` | supplement reviews | positive / negative | 1M |
| Turkish-English, parallel | `massive_tr`, `massive_en` | voice-assistant requests (translations) | 11 topics | 256K |
| Turkish-English, parallel | `tez_tr`, `tez_en` | author-provided Turkish and English abstracts of the same thesis | 8 fields | 4M |
| Turkish-English, same task | `sinema_tr` / `amazon_movies_en` | film reviews | positive / negative | 4M / 16M |
| Turkish-English, same task | `musteri_tr` / `amazon_shop_en` | shopping reviews | positive / negative | 1M / 8M |
| Turkish-English, same task | `trnews2025_tr` / `wikinews_en` | news | sections | 4M / 512K |
| English | `amazon_hpc_en` | health product reviews | positive / negative | 16M |

- **No text repeats inside a document** (texts can recur across documents). A length that a dataset cannot fill
  with distinct records is skipped. The longest documents hold up to 236,378
  different reviews (16M tokens).
- **Parallel documents** carry the same records, order, users, dates and
  answers in both languages. They are sized by the Turkish version, which
  needs more tokens for these texts, so both versions fit the stated length.
- **A close-comparison extension** asks whether label A is more or less common
  than label B when their counts differ by 0-10%.

## How the labels were checked

Before a dataset entered, native speakers labelled a sample blind and were then
shown the source label. A dataset enters if each annotator agrees with the
source on at least 85% of the records they could decide and is unsure on at
most 25%; labels that a non-expert cannot tell apart were grouped or removed
first, and datasets that failed were dropped. Two annotators labelled most
samples; agreement between them is reported as Cohen's kappa. Per-dataset
results are in the dataset card.

## Using it

```python
from datasets import load_dataset
q = load_dataset("yigitates17/tr-oolong", "doktor_tr", split="test")
d = load_dataset("yigitates17/tr-oolong", "doktor_tr_documents", split="test")
```

Give the model a document's `text`, then a question. Score with
`score_responses.py` and report results per dataset, per question type and per
length: some question types can be answered from a small sample of the
records, exact counts cannot. `recompute_answers.py` recomputes every answer
from the labelled records (Python standard library only).

## Licences

Each dataset keeps its source's licence, as declared by the source's publisher
(details, links and attribution in the dataset card): Turkish review sets CC-BY-SA-4.0; MASSIVE CC-BY-4.0; doctor
questions and thesis abstracts CC-BY-4.0; TRNEWS-2025 CC-BY-NC-4.0; Wikinews
CC-BY 2.5/4.0; Amazon Reviews 2023 text released with the permission of the
dataset's authors. Questions, answers and documentation written for TR-OOLONG:
CC-BY-4.0, except where a share-alike licence applies.

**Removal requests:** e-mail yigitates1709@gmail.com (please not in a public
issue); confirmed records are removed in the next version.

## Earlier versions

v0.10 (a different construction, with its own code in this repository) is
described in [`README_v0.10.md`](README_v0.10.md) and
[`DATACARD_v0.10.md`](DATACARD_v0.10.md); v0.11's release files are in
[`release/v0.11/`](release/v0.11/). Versions are not comparable question by
question.

## Citation

Cite this dataset (citation added with the paper) and the sources: OOLONG
(Bertsch et al., 2025), MASSIVE (FitzGerald et al., ACL 2023), the Turkish NLP
Suite (Altinok, ACL 2023), Amazon Reviews 2023 (Hou et al., 2024), TRNEWS-2025,
the doctorsitesi.com and Turkish academic theses datasets on Hugging Face, and
Wikinews.
