"""Experiment: every attack, on the close comparisons as actually built in v0.8.0.

Setup (2026-09-28). No language model. Reads the rebuilt release and scores
every `close_comparison` question with each reader below (share answered
correctly; guessing gets 0.50):

  first named        always answer the first label in the question
  corpus shares      answer whichever label is more common in the whole source
                     corpus, without opening the document
  skim 5/25/50%      random share of the records, true labels, 40 samples
  topic search 10%   the 10% of records the word-count classifier finds most
                     likely to be either label, true labels
  full, 95/90%       every record, right with that probability, otherwise a
                     random other label; 20 runs
  full, classifier   every record, labelled by the word-count classifier of
                     honest_reader.py (out-of-fold)

Usage: python experiments/attack_v08.py
"""
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "experiments"))
from sampling_solver import load_set, noisy_labels                 # noqa: E402
from honest_reader import SETS, train_predict                      # noqa: E402


def main():
    res = defaultdict(list)
    per_set = defaultdict(lambda: defaultdict(list))
    examples = []
    for s in SETS:
        d = ROOT / f"{s}_out"
        qs, metas = load_set(d)
        cq = [q for q in qs if q["kind"] == "close_comparison"]
        if not cq:
            print(f"{s:18} no close comparisons")
            continue
        pool = {}
        for m in metas.values():
            pool.update(zip(m["text"].to_list(), m["label"].to_list()))
        texts = list(pool)
        pred_of, labs, _ = train_predict(texts, [pool[t] for t in texts], qs[0]["language"])
        post = train_predict.last_post
        li = {l: i for i, l in enumerate(labs)}
        corpus = Counter(pool.values())
        for q in cq:
            m = metas[q["haystack_id"]]
            tx, lab = m["text"].to_list(), m["label"].to_list()
            N, a, b, gold = len(lab), q["label_a"], q["label_b"], q["answer"]
            space = sorted(set(lab))

            def right(ca, cb):
                if ca == cb:
                    return 0.5
                return float((a if ca > cb else b) == gold)

            out = {"first named": float(a == gold),
                   "corpus shares": right(corpus[a], corpus[b])}
            for f in (0.05, 0.25, 0.5):
                k = round(N * f)
                v = []
                for t in range(40):
                    smp = random.Random(f"{q['uid']}{f}{t}").sample(lab, k)
                    v.append(right(smp.count(a), smp.count(b)))
                out[f"skim {int(f * 100)}%"] = statistics.mean(v)
            order = np.argsort([-max(post[t][li[a]], post[t][li[b]]) for t in tx])[: round(N * 0.10)]
            out["topic search 10%"] = right(sum(lab[i] == a for i in order),
                                            sum(lab[i] == b for i in order))
            for acc in (0.95, 0.90):
                v = []
                for t in range(20):
                    nl = noisy_labels(lab, acc, space, random.Random(f"n{q['uid']}{acc}{t}"))
                    v.append(right(nl.count(a), nl.count(b)))
                out[f"full, {int(acc * 100)}% right"] = statistics.mean(v)
            pl_ = [pred_of[t] for t in tx]
            out["full, classifier"] = right(pl_.count(a), pl_.count(b))
            for k2, v in out.items():
                res[k2].append(v)
                per_set[s][k2].append(v)
            if len(examples) < 3 and not any(e[0] == s for e in examples):
                examples.append((s, q["uid"], q["question"], gold, lab.count(a), lab.count(b), N,
                                 {k2: round(v, 2) for k2, v in out.items()}))
        print(f"{s:18} {len(cq):>3} close comparisons", flush=True)

    n = len(res["first named"])
    print(f"\nall sets: {n} close comparisons (guessing = 0.50)")
    for k2, v in res.items():
        print(f"   {k2:20} {statistics.mean(v):.3f}")
    print("\nby set: skim 50% / topic search / full 95% right / full classifier")
    for s, d in per_set.items():
        print(f"   {s:18} n={len(d['skim 5%']):>3}  {statistics.mean(d['skim 50%']):.2f} / "
              f"{statistics.mean(d['topic search 10%']):.2f} / "
              f"{statistics.mean(d['full, 95% right']):.2f} / {statistics.mean(d['full, classifier']):.2f}")
    print("\nexamples:")
    for e in examples:
        print("  ", e)
    json.dump({"n": n, "all": {k: statistics.mean(v) for k, v in res.items()},
               "by_set": {s: {k: statistics.mean(v) for k, v in d.items()} for s, d in per_set.items()}},
              open(ROOT / "experiments" / "attack_v08.json", "w"), indent=2)


if __name__ == "__main__":
    main()
