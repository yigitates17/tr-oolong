"""Package TR-OOLONG for Hugging Face and (optionally) push it.

LICENSING IS THE POINT OF THIS SCRIPT. The eleven instance sets do NOT share one
license, and THREE of them must not have their text redistributed at all
(amazon_hpc_en, sikayet_tr, interpress_tr). Shipping them as one undifferentiated
dataset would breach Amazon's Conditions of Use, redistribute two corpora that
carry no license grant, and force share-alike onto sets that are not share-alike.
So each set is packaged into its own config, tagged with its own license, and the
sets that cannot be redistributed ship as *questions and answers only* -- the
haystack text is withheld and the user rebuilds it locally from the public source
with the committed config.

Two of the three withheld sets (sikayet_tr, interpress_tr) declare no licence
at all. Do not flip `full_text` on either without a written grant.

    # dry run: build the payload, print what would be pushed, push nothing
    python scripts/publish_hf.py --out hf_release

    # push (needs `pip install huggingface_hub` and a WRITE token)
    huggingface-cli login          # or: export HF_TOKEN=hf_...
    python scripts/publish_hf.py --out hf_release --repo <user>/tr-oolong --push
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Per-set redistribution policy. VERIFY EACH BEFORE FLIPPING full_text ON.
# ---------------------------------------------------------------------------
POLICY = {
    "tr_intent_out": dict(
        license="cc-by-4.0", full_text=True,
        source="AmazonScience/massive (tr-TR)",
        note="MASSIVE is CC-BY-4.0: redistribution of derived data is permitted "
             "with attribution and a statement of changes."),
    "en_intent_out": dict(
        license="cc-by-4.0", full_text=True,
        source="AmazonScience/massive (en-US)",
        note="As above; this is the parallel English twin."),
    "tr_intent_paired_out": dict(
        license="cc-by-4.0", full_text=True,
        source="AmazonScience/massive (tr-TR), record-matched",
        note="Record-matched with en_intent_paired: the same utterances in the "
             "same order, so all 155 questions have the same answer in both "
             "languages (word answers via answer_key)."),
    "en_intent_paired_out": dict(
        license="cc-by-4.0", full_text=True,
        source="AmazonScience/massive (en-US), record-matched",
        note="The English half of the record-matched pair. Sized in records, not "
             "tokens, so its documents are shorter in tokens than the Turkish "
             "half (1.34x under the Qwen3-8B tokenizer)."),
    "vitamins_tr_out": dict(
        license="cc-by-sa-4.0", full_text=True,
        source="turkish-nlp-suite/vitamins-supplements-reviews (Vitaminler.com)",
        note="CC-BY-SA-4.0 is SHARE-ALIKE: this subset and anything derived from "
             "it must stay CC-BY-SA-4.0. Cite Altinok (ACL 2023)."),
    "musteri_tr_out": dict(
        license="cc-by-sa-4.0", full_text=True,
        source="turkish-nlp-suite/MusteriYorumlari (Hepsiburada, Trendyol)",
        note="CC-BY-SA-4.0 is SHARE-ALIKE: this subset and anything derived from "
             "it must stay CC-BY-SA-4.0. Labels are the customer's own 1-5 star "
             "rating."),
    "marc_en_out": dict(
        license="apache-2.0", full_text=True,
        source="SetFit/amazon_reviews_multi_en (Multilingual Amazon Reviews Corpus)",
        note="Apache-2.0: redistribution permitted. The English half of the "
             "cleanest pair; labels are the reviewer's own 1-5 star rating."),
    "amazon_hpc_en_out": dict(
        license="other", full_text=False,
        source="McAuley-Lab/Amazon-Reviews-2023 (Health_and_Personal_Care)",
        note="Review text is governed by Amazon's Conditions of Use, not by the "
             "repository's license. Text withheld; rebuild locally with "
             "scripts/health.py + configs/amazon_hpc_en.json."),
    # --- v0.7.0 additions. All three exist because the 3-class review sets
    # cannot host a small answer (DESIGN_DECISIONS D21b), and two of the three
    # cannot ship their text.
    "sikayet_tr_out": dict(
        license="other", full_text=False,
        source="Kaggle savasy/multiclass-classification-data-for-turkish-tc32",
        note="29 categories of Turkish consumer complaints. The uploader declares "
             "NO license and the text is scraped from a complaints site, so the "
             "text is withheld. Rebuild locally with scripts/sikayet_tr.py, which "
             "takes the path to a copy of ticaret-yorum.csv downloaded from Kaggle. "
             "Three of the original 32 categories were dropped because their names "
             "appear in over 30% of their complaints."),
    "interpress_tr_out": dict(
        license="other", full_text=False,
        source="Interpress Turkish news category corpus, 270k",
        note="16 sections of Turkish news (17 in the source), with daily publication dates. The "
             "upstream card declares no license. Text withheld; rebuild locally "
             "with scripts/interpress_tr.py, which fetches the archive the "
             "Hugging Face loading script points at and verifies its sha256. The "
             "Apache header on that loading script covers the SCRIPT, not the "
             "data, and must not be cited as the data's license."),
    "sinema_tr_out": dict(
        license="cc-by-sa-4.0", full_text=True,
        source="turkish-nlp-suite/BuyukSinema",
        note="Turkish film reviews labelled with the reviewer's own 10-point "
             "rating. The only large-label-space Turkish source found with a "
             "declared license, so unlike the other two v0.7.0 additions its text "
             "ships. Share-alike: anything derived from this subset stays CC-BY-SA-4.0."),
}

CARD = """---
license: {licenses}
language: [tr, en]
task_categories: [question-answering]
tags: [long-context, aggregation, turkish, benchmark, oolong, cross-lingual]
configs:
{configs}
---

# TR-OOLONG

A long-context **aggregation** benchmark for Turkish, with English counterparts
built by the same pipeline. Each document joins thousands of real records
(reviews, complaints, news articles, voice commands) into one text of 36K to 1M
tokens, and each question asks about the whole collection:

```
Bu kayıtlarda hangisi daha çok: 'turizm' etiketli kayıtlar mı,
'magazin' etiketli kayıtlar mı?                              -> magazin  (44 vs 41 of 266)
Bu kayıtlarda kaç tane 'ulaşım' etiketli kayıt var?          -> 166
```

The label of a record is never written in the text, so a model has to decide
what each record is about and then count. The core questions (the first
example) compare two categories whose counts are so close that neither
sampling part of the document nor searching for the relevant records answers
them. Every answer is computed from the
source dataset's own labels, twice, by independent code. The construction
follows [OOLONG](https://arxiv.org/abs/2511.02817) (Bertsch et al., 2025).

Built with [`tr-oolong`]({repo_url}) v{version}. Developed at the Institute for
Data Science & Artificial Intelligence (DSAI), Boğaziçi University, as MSc
thesis work. Full details: `DATACARD.md` in this repository.

## At a glance

**11 subsets · 195 documents · 2,277 questions · 50.7M tokens · 7 question types**

{glance_table}

Lengths are tokens under `Qwen/Qwen3-8B`. `classes` is the number of labels.

**Question types and roles.** Every question has a `role`:

| role | question types | questions | what it shows |
|---|---|---:|---|
| `core` | `close_comparison`: which are there more of, A or B? (both frequent, counts very close) | 174 | that the model read and judged the whole document |
| `retrieval` | `count` with `"rare": true` (answer 5 to 30) | 265 | that it can find a few records by meaning |
| `control` | `count` 656, `proportion` 492, `label_vs_label` 292, `most_common` 138, `least_common` 132, `second_most` 128 | 1,838 | that it can classify the records at all |

**Turkish/English pairs.** `tr_intent_paired` and `en_intent_paired` contain the
same 3,000 utterances (MASSIVE is a human translation) in the same order, so all
155 questions have the same answer in both languages and the two can be compared
with a paired test. `tr_intent`/`en_intent` match on token budget instead.
`musteri_tr`/`marc_en` and `vitamins_tr`/`amazon_hpc_en` are different corpora
with the same task. `sikayet_tr`, `interpress_tr` and `sinema_tr` are Turkish
only.

### Why the Turkish intent questions use English label names

In `tr_intent` and `tr_intent_paired` the question is Turkish but the label is
MASSIVE's English identifier (`transport_taxi`, `play_music`). Translating the
labels would put the answer back into the text: Turkish is verb-final, so a
label like `alarm_kur` appears word for word in utterances such as *"iki saat
sonrasına alarm kur"*. On all 15,075 utterances, records containing their own
label: English identifiers (shipped) 0.00%, Turkish imperative (`müzik_çal`)
3.13%, Turkish dictionary form (`müzik_çalmak`) 0.14%. The Turkish is in the
text being classified; the label only names the bucket.

## Relation to OOLONG

| | OOLONG | TR-OOLONG |
|---|---|---|
| languages | English | Turkish, with English counterparts built the same way |
| document length | 1K to 4M tokens (synthetic split) | 36K to 1M tokens |
| labels per dataset | 2 to 10 | 3, 10, 16, 29, 48 |
| narrowing to a subset | to users or months printed on every record | none |
| questions over dates | yes, its hardest group | none yet (`interpress_tr` has dates) |
| same question, same answer in two languages | no | yes (`*_intent_paired`) |
| numeric score | `partial` (0.75 per unit of error) | `partial`, plus `relative` for large answers |
| questions that resist sampling and search | none found | 174 close comparisons |
| published shortcut checks | none | yes, in the GitHub repository |

OOLONG's construction code was not released; this is an independent
implementation from the paper. OOLONG narrows questions to listed users or a
month, both printed on every record, so a string search finds the relevant
records: for user-narrowed questions it reads a median of 0.8% of the document
and gets the exact answer 99% of the time. Its whole-document comparisons have a
median gap of 38% between the two counts, so sampling answers them.

## Loading and scoring

```python
from datasets import load_dataset
qs = load_dataset("yigitates17/tr-oolong", "sikayet_tr", split="test")
```

- **Join and pool on `uid`.** `id` is unique only inside one subset.
- Give the model only the `haystack` text and the `question`.
- Score with `src/scoring.py` from the GitHub repository. It returns `exact`,
  `partial` (OOLONG's `0.75 ** |error|`), `relative` (`1 - |error| / answer`)
  and `primary`, the one to report: `exact` for word answers (all core
  questions), `partial` for rare-label counts, `relative` for other numbers.
- Report the `primary` score per role, never pooled, and state how the model
  saw the document (one prompt, or an agent with code tools that can sample or
  search it).

## Files

- `questions.jsonl`: `uid`, `dataset`, `id`, `haystack_uid`, `haystack_id`,
  `language`, `target_tokens`, `kind`, `label` / `candidates` / `label_a` /
  `label_b`, `unit`, `answer`, `answer_key`, `rare`, `question`, `role`.
- `haystacks.jsonl` (where the licence allows): `uid`, `haystack_id`,
  `haystack`, plus build metadata.
- `manifest.json`: seed, config, source hash, tokenizer, per-document lengths.

## Subsets and licences

Each subset keeps the licence of its source.

{table}

### Subsets without text

{withheld}

For these, the text is rebuilt locally. The build is deterministic, so the
result is byte-identical:

```bash
git clone {repo_url} && cd tr-oolong
python scripts/<fetch_script>.py
python src/build_tr_oolong.py --config configs/<set>.json --build
```

## What each role measures, and limitations

No model has been run on this benchmark yet. The statements below come from
simulated readers: short programs that are told the true label of every record
they read, so they show what a reading strategy can achieve.

| role | strongest shortcut found | reader of everything |
|---|---|---|
| core | 0.64 (the 10% most relevant records by topic search); sampling half the document 0.63; guessing 0.50 | 0.85 at 95% labelling accuracy, 0.77 at 90% |
| retrieval | topic search reading 5%: 0.53 under `partial` | depends strongly on labelling accuracy |
| control | sampling 5%: about 0.8 under `relative` | about 0.9 or more |

- Every release also passes four checks: searching the text for label names
  (0 of 856,798 shipped records contain one), always giving the most common
  answer, answering from the source corpus's label shares, and guessing labels
  from record length and punctuation.
- Control questions are not evidence of reading: a 5% sample answers them
  almost as well as the whole document, and under `relative` a longer document
  is not harder.
- Only 174 questions are core (margin of error about ±0.07 on a model's core
  score). They come mostly from the intent and complaint sets; on the two paired
  intent sets topic search gets 0.73 and 0.81. The 3-label review sets have one.
- Brand questions (in v0.7.x) were removed in v0.8.0: searching for the printed
  brand answered all of them. The v0.7.x per-question difficulty grades were
  withdrawn as well.
- Questions on one document overlap (337 are a count and a proportion of the
  same thing); treat the document as the unit of evidence.
- Documents of the same subset and length share 20-39% of their records.
- Intent labels: 2.7-9.3% judged wrong on a 150-record check, partly from
  translation, which affects only the Turkish half.
- Every record comes from a public dataset; a model that memorised a dataset's
  labels could label records without reading them (not tested).
- No time-based questions. Lengths use one tokenizer; the Turkish/English token
  ratio on the same sentences ranges from 0.57x to 2.16x across tokenizers.

## Citation

```bibtex
@misc{{troolong,
  title  = {{TR-OOLONG: A Turkish Long-Context Aggregation Benchmark}},
  author = {{Ate{{\\c{{s}}}}, Yi{{\\u{{g}}}}it}},
  year   = {{2026}},
  note   = {{Bo{{\\u{{g}}}}azi{{\\c{{c}}}}i University, Institute for Data Science \\& Artificial Intelligence}},
  url    = {{{repo_url}}}
}}
```

Please also cite OOLONG (Bertsch et al., 2025, arXiv:2511.02817) and the source
corpus of each subset you use.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="hf_release")
    ap.add_argument("--repo", default="", help="e.g. yigitates/tr-oolong")
    # NOT cosmetic: `amazon_hpc_en` ships without haystack text, and the card
    # tells users to clone THIS url and rebuild it locally. A wrong link makes
    # that subset unusable rather than merely unattributed.
    ap.add_argument("--repo-url", default="https://github.com/yigitates17/tr-oolong")
    ap.add_argument("--push", action="store_true", help="actually upload")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # An unregistered set must be a hard error, never a silent omission: POLICY is
    # the only place a subset's license is declared, so a set missing from it
    # would either ship unlicensed or vanish from the release without a word.
    declared = set(POLICY)
    configured = set()
    for c in sorted((ROOT / "configs").glob("*.json")):
        try:
            # NOT `out` -- that is the release directory, and rebinding it here
            # shadowed it with a config's out_dir string, so the first packaging
            # step died on `str / str`.
            out_dir = json.loads(c.read_text(encoding="utf-8")).get("out_dir")
        except json.JSONDecodeError:
            continue
        if out_dir and (ROOT / out_dir / "questions.jsonl").exists():
            configured.add(out_dir)
    missing = sorted(configured - declared)
    if missing:
        sys.exit(f"refusing to package: {missing} are built but have no entry in "
                 f"POLICY in this file. Declare each one's license and whether its "
                 f"text may be redistributed before releasing it.")

    version, rows, cfg_lines, withheld, licenses = None, [], [], [], set()
    # The at-a-glance table is DERIVED, never typed. It was hand-maintained
    # until 2026-09-16 and had drifted badly: it listed eight subsets after
    # eleven were built, and four of the eight carried doc and question
    # counts from an older build. A published card that misstates what is in
    # the files is worse than no table.
    glance = []
    for name, pol in POLICY.items():
        src = ROOT / name
        if not (src / "questions.jsonl").exists():
            print(f"[skip] {name}: not built", file=sys.stderr)
            continue
        man = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
        version = man["version"]
        dst = out / name.removesuffix("_out")
        dst.mkdir()
        shutil.copy(src / "questions.jsonl", dst / "questions.jsonl")
        shutil.copy(src / "manifest.json", dst / "manifest.json")
        # v0.8.0: the per-question difficulty grades are no longer released.
        # They depended on which skimming programs were chosen and were partly
        # luck (experiments/REPORT.md, experiments 1-3); each question's `role`
        # replaces them.
        if pol["full_text"]:
            shutil.copy(src / "haystacks.jsonl", dst / "haystacks.jsonl")
        else:
            withheld.append(f"- **{dst.name}** ({pol['source']}) -- {pol['note']}")
        licenses.add(pol["license"])
        cfg_lines.append(f"  - config_name: {dst.name}\n    data_files:\n"
                         f"      - split: test\n        path: {dst.name}/questions.jsonl")
        rows.append(f"| `{dst.name}` | {man['config']['language']} | {pol['source']} | "
                    f"`{pol['license']}` | {'yes' if pol['full_text'] else '**no**'} | "
                    f"{man['questions_written']} | {pol['note']} |")
        hs = man["haystacks"]
        tok = [h["n_tokens"] for h in hs]
        recs = [h["n_examples"] for h in hs]
        lang = man["config"]["language"]
        k = man["label_space"]
        glance.append((max(tok), f"| `{dst.name}` | {lang} | "
                                 f"{'**' + str(k) + '**' if k >= 10 else k} | {len(hs)} | "
                                 f"{man['questions_written']} | {min(tok):,} | "
                                 f"{max(tok):,} | {max(recs):,} |"))
        print(f"[ok] {dst.name}: {man['questions_written']} questions, "
              f"{pol['license']}, text={'included' if pol['full_text'] else 'WITHHELD'}")

    if not rows:
        sys.exit("nothing built -- run the builder first")

    table = ("| subset | lang | source | license | text included | questions | note |\n"
             "|---|---|---|---|---|---|---|\n" + "\n".join(rows))
    card = CARD.format(
        # A block sequence cannot follow "license:" on the same line -- that is
        # invalid YAML and the card's front matter silently fails to parse on
        # the Hub. Flow style keeps it on one line and valid for both cases.
        licenses=("[" + ", ".join(sorted(licenses)) + "]") if len(licenses) > 1
                 else sorted(licenses)[0],
        configs="\n".join(cfg_lines), table=table,
        glance_table=(
            "| subset | lang | classes | docs | questions | shortest | longest "
            "| max records in one doc |\n"
            "|---|---|---:|---:|---:|---:|---:|---:|\n"
            + "\n".join(r for _, r in sorted(glance, key=lambda g: -g[0]))),
        withheld="\n".join(withheld) or "_(none)_",
        repo_url=args.repo_url, version=version)
    (out / "README.md").write_text(card, encoding="utf-8")
    shutil.copy(ROOT / "DATACARD.md", out / "DATACARD.md")
    print(f"\npackaged -> {out}/   (card: {out}/README.md)")

    if not args.push:
        print("\ndry run. Re-run with --repo <user>/<name> --push to upload.")
        return
    if not args.repo:
        sys.exit("--push needs --repo")
    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("pip install huggingface_hub")
    api = HfApi()           # token from `huggingface-cli login` or $HF_TOKEN
    api.create_repo(args.repo, repo_type="dataset", exist_ok=True)
    api.upload_folder(folder_path=str(out), repo_id=args.repo, repo_type="dataset")
    print(f"pushed -> https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
