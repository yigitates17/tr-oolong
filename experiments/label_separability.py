"""Which pairs of labels can be told apart from the text? (v0.10.0)

Setup (2026-09-30). No language model. For every dataset that has close
comparisons, a word-count classifier (multinomial Naive Bayes, the same one as
honest_reader.py) is trained on the cleaned source pool with 5-fold
out-of-fold predictions. For each pair of labels A and B, it looks only at the
records whose true label is A or B and asks the classifier which of the two is
more likely. The share it gets right is the pair's SEPARABILITY.

Why it matters. A close comparison ("more A or more B?") is decided by a few
records. If A and B cannot be told apart from the text (news filed under
"turizm" vs "seyahat", a refund complaint filed under "mobilya ve ev tekstili"
vs "alışveriş"), the answer depends on which box the filer or the editor
ticked, not on reading. Such pairs are not used for core questions.

A pair must also consist of labels that are IDENTIFIABLE on their own: a
close comparison counts records of A and of B inside a document that also holds
every other label, so each of A and B must be recognised among all labels, not
only against each other. A label qualifies when the classifier finds at least
--min-recall of its records (one-vs-rest recall, all labels competing). Without
this, "more 2-star or more 8-star film reviews?" passed the pair test even
though nobody can tell an exact 2 from a 1 or a 3.

The classifier is deliberately weak; a good language model separates labels
better. So a pair it separates is safely separable, and the threshold is a
conservative floor, not a claim about what models can do.

Output: experiments/separable_pairs/<dataset>.json with every pair's score and
the list of pairs at or above --threshold. The builder reads that list
(`close_allowed_pairs_file`), so the rule is fixed and checkable.

Usage: python experiments/label_separability.py [--threshold 0.8]
"""
import argparse
import dataclasses
import json
import random
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
from build_tr_oolong import Config, load_source, clean          # noqa: E402
from honest_reader import train_predict                          # noqa: E402

SETS = ["tr_intent_paired", "en_intent_paired", "tr_intent", "en_intent",
        "sikayet_tr", "interpress_tr", "sinema_tr",
        "musteri_tr", "marc_en", "vitamins_tr", "amazon_hpc_en"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--min-recall", type=float, default=0.6)
    ap.add_argument("--max-records", type=int, default=60000)
    args = ap.parse_args()
    outdir = ROOT / "experiments" / "separable_pairs"
    outdir.mkdir(parents=True, exist_ok=True)
    import os
    os.chdir(ROOT)
    fields = {f.name for f in dataclasses.fields(Config)}
    for name in SETS:
        c = json.load(open(ROOT / "configs" / f"{name}.json"))
        cfg = Config(**{k: v for k, v in c.items() if k in fields})
        df = clean(load_source(cfg), cfg, {})
        rows = list(zip(df["text"].to_list(), df["label"].to_list()))
        random.Random(0).shuffle(rows)
        rows = rows[: args.max_records]
        texts, labs = [t for t, _ in rows], [l for _, l in rows]
        _, L, conf = train_predict(texts, labs, cfg.language)
        recall = {l: float(conf[i, i] / conf[i].sum()) for i, l in enumerate(L)}
        post = train_predict.last_post
        li = {l: i for i, l in enumerate(L)}
        by = {}
        for t, l in zip(texts, labs):
            by.setdefault(l, []).append(post[t])
        scores = {}
        for a, b in combinations(sorted(L), 2):
            ia, ib = li[a], li[b]
            ok = n = 0
            for lab, other in ((a, ib), (b, ia)):
                own = li[lab]
                for p in by.get(lab, []):
                    ok += p[own] > p[other]
                    n += 1
            scores[f"{a} | {b}"] = round(ok / n, 4) if n else None
        allowed = sorted(k for k, v in scores.items()
                         if v is not None and v >= args.threshold
                         and all(recall[x] >= args.min_recall for x in k.split(" | ")))
        (outdir / f"{name}.json").write_text(json.dumps(
            {"dataset": name, "threshold": args.threshold, "min_recall": args.min_recall,
             "records": len(texts),
             "recall": {l: round(r, 4) for l, r in sorted(recall.items(), key=lambda kv: kv[1])},
             "allowed_pairs": [k.split(" | ") for k in allowed],
             "separability": dict(sorted(scores.items(), key=lambda kv: kv[1] or 0))},
            indent=1, ensure_ascii=False), encoding="utf-8")
        vals = [v for v in scores.values() if v is not None]
        weak = [l for l, r in recall.items() if r < args.min_recall]
        print(f"{name:18} labels {len(L):>2} (identifiable {len(L) - len(weak):>2})  pairs {len(vals):>4}  allowed {len(allowed):>4} "
              f"({100 * len(allowed) / len(vals):.0f}%)  median separability {np.median(vals):.2f}",
              flush=True)


if __name__ == "__main__":
    main()
