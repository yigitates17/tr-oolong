"""
make_readme_figs.py -- regenerate the two README figures from built outputs.

Reads each set's manifest.json (question-family distribution) and haystacks.jsonl
(examples per haystack vs token length). Data visualization only, so this is the
one script in the project written with pandas + matplotlib rather than Polars.

Usage:
    python scripts/make_readme_figs.py --sets vitamins_tr_out amazon_hpc_en_out tr_intent_out en_intent_out
"""

import argparse
import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# The nine families that ship in v0.7.0, in report order. `shift` (withdrawn
# v0.7.0) and `top_k` (withdrawn v0.5.0 with the corpus it shipped on) are
# deliberately absent: a figure that reserves a slot for a family nobody
# receives invites the reader to ask which sets have it.
FAMILY_ORDER = ["count", "proportion", "most_common", "least_common",
                "second_most", "label_vs_label",
                "entity_count", "entity_argmax", "pairwise"]


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
             .reindex([f for f in FAMILY_ORDER if f in dist["family"].unique()]
                      # a family absent from FAMILY_ORDER was previously dropped
                      # from the figure without a word -- append it instead
                      + sorted(set(dist["family"].unique()) - set(FAMILY_ORDER))))
    # 11 sets against matplotlib's 10-colour default cycle silently wraps, and
    # the two that collide are amazon_hpc_en and vitamins_tr -- the twin pair a
    # reader is most likely to be comparing. tab20 gives every set its own hue.
    colors = plt.get_cmap("tab20")(range(len(pivot.columns)))
    ax = pivot.plot(kind="bar", figsize=(11, 5), width=0.8, color=colors)
    ax.set_ylabel("questions")
    ax.set_xlabel("question family")
    ax.set_title("Question-family counts per set")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out / "family_counts.png", dpi=150)
    plt.close()


# How many records fit in a token budget is a property of the CORPUS as much as
# of the language: an interpress_tr news article is ~1,650 characters and a
# MASSIVE utterance is ~30. Pooling every set by language therefore does not
# measure morphology, it measures which corpora happen to sit at each tier, and
# when this was run over all eleven sets it produced a line that doubled back on
# itself and a Turkish curve that fell at 1M. Restricted to the DOMAIN-MATCHED
# pairs, where the two languages hold the same kind of record, the comparison is
# real.
LENGTH_PAIR_SETS = ["tr_intent_out", "en_intent_out",
                    "vitamins_tr_out", "amazon_hpc_en_out"]


def fig_examples_vs_length(hay: pd.DataFrame, out: Path):
    pairs = hay[hay["set"].isin(LENGTH_PAIR_SETS)]
    if pairs.empty:
        print("  [skip] examples_vs_length: none of the matched-pair sets were "
              "passed; the figure is only interpretable on those.")
        return
    dropped = sorted(set(hay["set"].unique()) - set(LENGTH_PAIR_SETS))
    fig, ax = plt.subplots(figsize=(9, 5))
    agg = (pairs.groupby(["language", "target_tokens"])["n_examples"]
           .mean().reset_index())
    for lang, g in agg.groupby("language"):
        g = g.sort_values("target_tokens")
        ax.plot(g["target_tokens"] / 1000, g["n_examples"], marker="o", label=lang)
    ax.set_xlabel("haystack length (K tokens)")
    ax.set_ylabel("examples per haystack (mean)")
    ax.set_title("Examples per haystack vs length, domain-matched pairs only")
    ax.legend(title="language")
    fig.text(0.5, 0.005,
             "MASSIVE intent + supplement/health reviews. Other sets are excluded: "
             "their records are a different size,\nso pooling them would show the "
             "corpus mix, not the language. Token ratios are tokenizer-specific "
             "(0.57x-2.16x).",
             ha="center", fontsize=7, color="0.35")
    plt.tight_layout(rect=(0, 0.06, 1, 1))
    plt.savefig(out / "examples_vs_length.png", dpi=150)
    plt.close()
    if dropped:
        print(f"  [note] examples_vs_length excludes {len(dropped)} set(s) whose "
              f"record size is not comparable: {', '.join(dropped)}")


def _discover():
    """Every config whose out_dir has been built (mirrors quality_audit.py)."""
    out = []
    for c in sorted(Path(__file__).resolve().parents[1].joinpath("configs").glob("*.json")):
        try:
            d = json.loads(c.read_text(encoding="utf-8")).get("out_dir")
        except json.JSONDecodeError:
            continue
        if d and Path(d, "manifest.json").exists():
            out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True, help="output directories")
    ap.add_argument("--out", default="figures")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    dist, hay = load_sets((args.sets or _discover()))
    fig_family_counts(dist, out)
    fig_examples_vs_length(hay, out)
    print(f"wrote {out/'family_counts.png'} and {out/'examples_vs_length.png'}")


if __name__ == "__main__":
    main()
