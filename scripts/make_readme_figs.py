"""
make_readme_figs.py -- regenerate the two README figures from built outputs.

Reads each set's manifest.json (question-family distribution) and haystacks.jsonl
(examples per haystack vs token length). Data visualization only, so this is the
one script in the project written with pandas + matplotlib rather than Polars.

Usage:
    python scripts/make_readme_figs.py --sets tr_oolong_out en_twin_out tr_intent_out en_intent_out
"""

import argparse
import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

FAMILY_ORDER = ["count", "proportion", "shift",
                "most_common", "least_common", "second_most",
                "entity_count", "entity_argmax", "top_k", "pairwise"]


def load_sets(dirs):
    dist_rows, hay_rows = [], []
    for d in dirs:
        d = Path(d)
        man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        axis = d.name
        for fam, n in man.get("kind_distribution", {}).items():
            dist_rows.append({"set": axis, "family": fam, "count": n})
        for line in (d / "haystacks.jsonl").read_text(encoding="utf-8").splitlines():
            h = json.loads(line)
            hay_rows.append({
                "set": axis,
                "language": h["language"],
                "target_tokens": h["target_tokens"],
                "n_examples": h["n_examples"],
            })
    return pd.DataFrame(dist_rows), pd.DataFrame(hay_rows)


def fig_family_counts(dist: pd.DataFrame, out: Path):
    pivot = (dist.pivot_table(index="family", columns="set", values="count",
                              aggfunc="sum", fill_value=0)
             .reindex([f for f in FAMILY_ORDER if f in dist["family"].unique()]))
    ax = pivot.plot(kind="bar", figsize=(9, 5), width=0.8)
    ax.set_ylabel("questions")
    ax.set_xlabel("question family")
    ax.set_title("Question-family counts per set")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out / "family_counts.png", dpi=150)
    plt.close()


def fig_examples_vs_length(hay: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(9, 5))
    agg = (hay.groupby(["language", "target_tokens"])["n_examples"]
           .mean().reset_index())
    for lang, g in agg.groupby("language"):
        g = g.sort_values("target_tokens")
        ax.plot(g["target_tokens"] / 1000, g["n_examples"], marker="o", label=lang)
    ax.set_xlabel("haystack length (K tokens)")
    ax.set_ylabel("examples per haystack (mean)")
    ax.set_title("Examples per haystack vs length -- morphology at the tokenizer")
    ax.legend(title="language")
    plt.tight_layout()
    plt.savefig(out / "examples_vs_length.png", dpi=150)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True, help="output directories")
    ap.add_argument("--out", default="figures")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    dist, hay = load_sets(args.sets)
    fig_family_counts(dist, out)
    fig_examples_vs_length(hay, out)
    print(f"wrote {out/'family_counts.png'} and {out/'examples_vs_length.png'}")


if __name__ == "__main__":
    main()
