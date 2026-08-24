"""Package TR-OOLONG for Hugging Face and (optionally) push it.

LICENSING IS THE POINT OF THIS SCRIPT. The six instance sets do NOT share one
license, and two of them must not have their text redistributed at all. Shipping
them as one undifferentiated dataset would breach Amazon's review terms and the
airline set's non-commercial clause. So each set is packaged into its own
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
    "tr_oolong_out": dict(
        license="apache-2.0", full_text=True,
        source="We-Bears/Turkish-Review-Sentiment-Data",
        note="Apache-2.0: redistribution permitted with the license text and a "
             "notice of modification."),
    "vitamins_tr_out": dict(
        license="cc-by-sa-4.0", full_text=True,
        source="turkish-nlp-suite/vitamins-supplements-reviews (Vitaminler.com)",
        note="CC-BY-SA-4.0 is SHARE-ALIKE: this subset and anything derived from "
             "it must stay CC-BY-SA-4.0. Cite Altinok (ACL 2023)."),
    "en_twin_out": dict(
        license="cc-by-nc-sa-4.0", full_text=False,
        source="Twitter US Airline Sentiment (CrowdFlower / Kaggle)",
        note="NON-COMMERCIAL and share-alike. Text withheld; rebuild locally "
             "with scripts/airline.py + configs/en_twin.json."),
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
tags: [long-context, aggregation, turkish, benchmark, oolong]
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
    ap.add_argument("--repo-url", default="https://github.com/yigitates/tr-oolong")
    ap.add_argument("--push", action="store_true", help="actually upload")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

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
        licenses="\n".join(f"- {l}" for l in sorted(licenses)) if len(licenses) > 1
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
