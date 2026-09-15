"""Package TR-OOLONG for Hugging Face and (optionally) push it.

LICENSING IS THE POINT OF THIS SCRIPT. The six instance sets do NOT share one
license, and two of them must not have their text redistributed at all. Shipping
them as one undifferentiated dataset would breach Amazon's review terms and the
Amazon set's withheld text and the share-alike Turkish sets. So each set is packaged into its own
config, tagged with its own license, and the sets that cannot be redistributed
ship as *questions and answers only* -- the haystack text is withheld and the
user rebuilds it locally from the public source with the committed config.

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
        note="RECORD-MATCHED twin: the same utterances, in the same order, as "
             "en_intent_paired. 110 of 120 questions share a gold answer, so the "
             "two can be compared with a paired test."),
    "en_intent_paired_out": dict(
        license="cc-by-4.0", full_text=True,
        source="AmazonScience/massive (en-US), record-matched",
        note="The English half of the record-matched pair. Sized in RECORDS, not "
             "tokens, so its token counts are lower than the Turkish half by the "
             "morphology factor (1.30-1.34x)."),
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
             "rating. No entity column, so six families ship."),
    "marc_en_out": dict(
        license="apache-2.0", full_text=True,
        source="SetFit/amazon_reviews_multi_en (Multilingual Amazon Reviews Corpus)",
        note="Apache-2.0: redistribution permitted. The English half of the "
             "cleanest pair; labels are the reviewer's own 1-5 star rating, and "
             "the entity families are omitted to stay parallel with musteri_tr."),
    "amazon_hpc_en_out": dict(
        license="other", full_text=False,
        source="McAuley-Lab/Amazon-Reviews-2023 (Health_and_Personal_Care)",
        note="Review text is governed by Amazon's Conditions of Use, not by the "
             "repository's license. Text withheld; rebuild locally with "
             "scripts/health.py + configs/amazon_hpc_en.json."),
}

CARD = """---
license: {licenses}
language: [tr, en]
task_categories: [question-answering]
tags: [long-context, aggregation, turkish, benchmark, oolong, rlm, cross-lingual]
configs:
{configs}
---

# TR-OOLONG

A Turkish long-context **aggregation** benchmark with a matched English twin,
built by an identical pipeline. Questions ask distributional facts about a
50K-1M-token haystack ("how many records are labeled X?", "which label is most
common?"); every gold answer is computed exactly from the source labels by two
independent code paths, so there is no manual annotation and nothing is
grep-solvable.

Built with [`tr-oolong`]({repo_url}) v{version}. See that repository for the
builder, the configs that reproduce every set byte-for-byte, and
`DESIGN_DECISIONS.md` for why each construction choice was made.

## At a glance

**8 subsets · 110 documents · 1,254 questions · 28.3M tokens · 2 languages · 10 question families**

| subset | lang | classes | docs | questions | shortest | longest | max records in one doc |
|---|---|---:|---:|---:|---:|---:|---:|
| `vitamins_tr` | tr | 3 | 20 | 237 | 99,217 | 744,785 | 19,774 |
| `amazon_hpc_en` | en | 3 | 20 | 236 | 98,672 | **987,623** | 16,116 |
| `musteri_tr` | tr | 3 | 15 | 153 | 99,137 | 496,238 | 13,618 |
| `marc_en` | en | 3 | 15 | 148 | 98,232 | 491,821 | 11,080 |
| `tr_intent` | tr | **48** | 10 | 120 | 49,981 | 99,998 | 6,169 |
| `en_intent` | en | **48** | 10 | 120 | 49,921 | 99,871 | 8,122 |
| `tr_intent_paired` | tr | **48** | 10 | 120 | 47,629 | 99,057 | 6,000 |
| `en_intent_paired` | en | **48** | 10 | 120 | 36,250 | 75,187 | 6,000 |

Lengths are tokens under `Qwen/Qwen3-8B`. Every document also records `n_chars`,
so lengths can be re-derived under a different tokenizer without rebuilding —
which matters, because the Turkish/English token ratio on identical content runs
from 0.57x to 2.16x depending on whose tokenizer counts it.

**Question families** (1,254 total): `count` 353 · `proportion` 300 ·
`shift` 110 · `label_vs_label` 109 · `most_common` 99 · `least_common` 98 ·
`second_most` 91 · `entity_count` 39 · `pairwise` 35 · `entity_argmax` 20.

## What the questions look like

Real questions from the release, with their gold answers:

```
[count/tr]         Bu yorumlardan kaç tanesi 'olumlu' etiketli?              -> 1600
[proportion/tr]    Yorumların yüzde kaçı 'olumlu' etiketli?                  -> 62
[most_common/tr]   Bu yorumlarda en sık görülen etiket hangisi?
                   Etiketler: 'nötr', 'olumlu', 'olumsuz'.                   -> olumlu
[entity_count/tr]  'Venatura' markası hakkındaki yorumlardan kaç tanesi
                   'nötr'?                                                    -> 10
[pairwise/tr]      'olumlu' yorumu hangisinde daha çok: 'Shorne' mi yoksa
                   'Tab' mı?                                                  -> Tab
[shift/tr]         Yorumların ikinci yarısında 'olumsuz' oranı ilk yarıya
                   göre arttı mı azaldı mı?                                   -> azaldı

[least_common/en]  Which label is the least common in these records?
                   Labels: 'alarm_set', 'lists_createoradd', 'music_query',
                   'play_audiobook', 'qa_currency'.                          -> play_audiobook
[label_vs_label/en] Are records labeled 'datetime_query' more common, less
                   common, or the same frequency as 'audio_volume_up'?       -> the same
```

None of these answers appears anywhere in the text. The label is latent: a model
has to decide what each record *means* before it can count anything. Records
whose text contains any label's surface form are dropped at build time, so a
substring search returns nothing useful.

### Why the Turkish intent questions name English labels

This is deliberate, not an oversight. In `tr_intent` and `tr_intent_paired` the
question is Turkish but the label is the source corpus's English identifier
(`transport_taxi`, `play_music`), because **translating the labels into Turkish
puts the answer back into the text**. Turkish is verb-final, so a `noun_verb`
label reproduces a natural Turkish phrase: the label `alarm_kur` appears
verbatim inside utterances like *"iki saat sonrasına alarm kur"*.

Measured over the full 48-label space on the same 15,075 utterances:

| labels used | records leaking their own label |
|---|---|
| English identifiers (**what ships**) | **0.00%** |
| Turkish, imperative form (`müzik_çal`) | **3.13%** (472 records) |
| Turkish, dictionary form (`müzik_çalmak`) | 0.14% (21 records) |

Keeping the English identifiers loses no Turkish signal, because the Turkish is
in the *text* being classified — the label is only the name of the bucket. The
translated variants exist in the repository under `configs/experimental/` for
anyone who wants to study the trade-off, and are deliberately not part of this
release.

## The matched twin

`tr_intent_paired` and `en_intent_paired` contain **the same utterances, in the
same order, with the same labels** — one is the translation of the other. So the
same question has the same correct answer in both languages:

```
TR: Bu kayıtlarda kaç tane 'transport_taxi' etiketli kayıt var?   -> 18
EN: How many utterances have the intent 'transport_taxi'?          -> 18
```

**100 of 120 question pairs share a byte-identical gold answer** (the other 20
are `shift`, where the same fact is written `arttı` / `rose`). Any score
difference between the two halves is therefore a property of the language rather
than of the question, and the two can be compared with a paired test.

`tr_intent` / `en_intent` are the same corpus matched on **token budget** instead
of record count — so the two halves hold different numbers of records and their
answers do not correspond. That pair asks "at equal cost"; the paired sets ask
"at equal content".

## Relation to Oolong

This follows the construction principle of
[Oolong](https://arxiv.org/abs/2511.02817) (Bertsch et al., 2025) and extends it.
Their construction code was unreleased at the time of writing, so the pipeline
here is an independent reimplementation from the paper's description.

| | Oolong | TR-OOLONG |
|---|---|---|
| languages | English | **Turkish + a matched English twin** |
| documents | not reported per split | **110**, 28.3M tokens |
| context length | reported at 8K-128K | **36K-988K** |
| label space | 2-10 classes | **3 and 48** |
| grouping axis | synthetic user IDs | **real brands** |
| timeline questions over real dates | **6 families** | ✗ none — no Turkish source carries dates |
| cross-lingual | ✗ | **✓ same question, same answer, two languages** |
| numeric metric | `0.75^\|y-yhat\|` | same **+ a scale-free one** |
| shortcut audit | not reported | **5 solvers, reports shipped** |

**Where Oolong is harder:** it has six question families conditioned on real
calendar dates, which its paper reports as its hardest group. There is no
equivalent here, because no Turkish labelled corpus with dates was found. The
substitute — comparing the first half of a document to the second — is binary
and is the weakest family in this release.

**Where this is harder:** 48 classes against their 2-10, documents to 988K
tokens, and answers in the thousands where theirs are single digits. That last
difference is not purely an advantage — see Limitations.

## Subsets and their licenses

Each subset carries the license of its source corpus. **They differ. Read the
row for the subset you use.**

{table}

### Subsets shipped without haystack text

{withheld}

For these, `questions.jsonl` and the manifest are included but the haystack text
is not, because the source license does not permit redistributing it. Rebuild
locally -- the build is deterministic, so you get byte-identical haystacks:

```bash
git clone {repo_url} && cd tr-oolong
python scripts/<fetch_script>.py
python src/build_tr_oolong.py --config configs/<set>.json --build
```

## Fields

`questions.jsonl` -- one question per line:

| field | meaning |
|---|---|
| `id` | unique question id |
| `haystack_id` | which haystack it refers to |
| `language` | `tr` or `en` |
| `target_tokens` | length tier of the haystack |
| `kind` | question family |
| `label` / `entity` / `candidates` | what the question is about |
| `answer` | gold answer, computed from source labels |
| `question` | the prompt text, self-contained |

`haystacks.jsonl` -- one haystack per line: `haystack_id`, `n_examples`,
`drift_target`, and `haystack` (the concatenated text).

## Scoring

Use `src/scoring.py` from the repository. It reports `exact`, `partial`
(`0.75**|y-yhat|`, matching Oolong) and `relative` (scale-free). Do not
re-implement it; the metric is frozen.

## Limitations

Five shortcut solvers are run against every build. Four fail, as intended:
substring search over label names, always answering the most frequent label,
answering from corpus statistics without opening the haystack, and classifying
records from length and punctuation alone. Their reports ship in the repository
under `manifests/`.

**The fifth partly succeeds, and it bounds what this benchmark shows.** Because
gold answers are large (median `count` near 1,000), most question families can
be answered by classifying a random *sample* of the records and scaling up
rather than by reading all of them. Measured with a solver given the true label
of every record it samples -- an upper bound, not a model result -- a 5% sample
scores 0.95 on `count` and 0.99 on `most_common` on the review sets, against
majority baselines of 0.05 and 0.55. The 48-class intent axis resists better
(0.39 on `most_common`) because its decision margins are narrower.

**So the supported claim is that this benchmark requires classifying latent
Turkish labels and aggregating them. It does not establish that a model has
processed the entire document.** Exact-match scoring is immune to this;
`relative` is not.

Other limitations, with numbers, are in `DATACARD.md`: label noise as a
per-family ceiling (measured 2.7-9.3% on the intent axis, part of it
mistranslation and asymmetric across the twin), documents within a length tier
sharing 21-39% of their records, no timeline axis, `shift` being the weakest
family and the only one the format solver beats, entity families being available
only at 500K tokens and above, small per-family sample sizes, and all lengths
measured under a single tokenizer.

## Citation

```bibtex
@misc{{troolong,
  title  = {{TR-OOLONG: A Turkish Long-Context Aggregation Benchmark}},
  author = {{Ates, Yigit}},
  year   = {{2026}},
  url    = {{{repo_url}}}
}}
```

Please also cite the source corpus of whichever subset you use, and
Bertsch et al. (2025), *Oolong*, arXiv:2511.02817, whose construction principle
this follows.
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
