"""Experiment: do close comparisons between two frequent labels need the whole document?

Setup (2026-09-28). No language model, and no new documents: questions are
generated from the documents already in the release.

Question: "are there more records labelled A or labelled B?" for label pairs
where both labels are frequent (at least 30 records and 2% of the document)
and their counts differ by 0.5% to 5% (relative to the larger). Up to 4 pairs
per document, chosen at random with a fixed seed.

Readers (score = share answered correctly; chance = 0.5):
  skim f           random f of the records, perfect labels, 40 samples
  topic search     rank records by how likely they are to be A or B (the
                   classifier's word statistics) and read the top 10% with true
                   labels, then compare what was found
  full, random-err every record, right with probability a, else a random label
  full, NB         every record, labelled by the word-count classifier
  full, NB adj     the same, counts corrected for the classifier's error rates
  full, NB 2-way   the same, but the confusion correction only between A and B

Usage: python experiments/close_comparisons.py
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

LO, HI = 0.005, 0.05


def adj_count(pred_counts, conf, labs, N, lab):
    li = {l: i for i, l in enumerate(labs)}
    k = li[lab]
    pos = conf[k].sum()
    neg = conf.sum() - pos
    tpr = conf[k, k] / pos
    fpr = (conf[:, k].sum() - conf[k, k]) / neg
    return (pred_counts[lab] - fpr * N) / (tpr - fpr)


def main():
    rng = random.Random(7)
    res = defaultdict(list)
    per_set = defaultdict(lambda: defaultdict(list))
    examples = []
    for s in SETS:
        d = ROOT / f"{s}_out"
        qs, metas = load_set(d)
        pool = {}
        for m in metas.values():
            pool.update(zip(m["text"].to_list(), m["label"].to_list()))
        texts = list(pool)
        pred_of, labs, conf = train_predict(texts, [pool[t] for t in texts], qs[0]["language"])
        post = train_predict.last_post
        li = {l: i for i, l in enumerate(labs)}
        for hid, m in sorted(metas.items()):
            tx, lab = m["text"].to_list(), m["label"].to_list()
            N = len(lab)
            c = Counter(lab)
            freq = [l for l, n in c.items() if n >= max(30, 0.02 * N)]
            pairs = [(a, b) for i, a in enumerate(sorted(freq)) for b in sorted(freq)[i + 1:]
                     if LO <= abs(c[a] - c[b]) / max(c[a], c[b]) <= HI]
            rng.shuffle(pairs)
            space = sorted(c)
            predl = [pred_of[t] for t in tx]
            pc = Counter(predl)
            for a, b in pairs[:4]:
                truth = c[a] > c[b]
                out = {}
                for f in (0.05, 0.25, 0.5):
                    k = round(N * f)
                    ok = 0
                    for t in range(40):
                        smp = random.Random(f"{s}{hid}{a}{b}{f}{t}").sample(lab, k)
                        ca, cb = smp.count(a), smp.count(b)
                        ok += (ca > cb) == truth if ca != cb else 0.5
                    out[f"skim {int(f*100)}%"] = ok / 40
                ka, kb = li[a], li[b]
                order = np.argsort([-max(post[t][ka], post[t][kb]) for t in tx])[: round(N * 0.10)]
                ca = sum(1 for i in order if lab[i] == a)
                cb = sum(1 for i in order if lab[i] == b)
                out["topic search 10%"] = float((ca > cb) == truth) if ca != cb else 0.5
                for acc in (0.95, 0.90):
                    ok = 0
                    for t in range(10):
                        nl = noisy_labels(lab, acc, space, random.Random(f"n{s}{hid}{a}{b}{acc}{t}"))
                        na, nb_ = nl.count(a), nl.count(b)
                        ok += (na > nb_) == truth if na != nb_ else 0.5
                    out[f"full, {int(acc*100)}% random-err"] = ok / 10
                out["full, NB"] = float((pc[a] > pc[b]) == truth) if pc[a] != pc[b] else 0.5
                ea, eb = adj_count(pc, conf, labs, N, a), adj_count(pc, conf, labs, N, b)
                out["full, NB adj"] = float((ea > eb) == truth)
                for k2, v in out.items():
                    res[k2].append(v)
                    per_set[s][k2].append(v)
                if len(examples) < 4 and s in ("sikayet_tr", "interpress_tr", "tr_intent_paired", "vitamins_tr") \
                        and not any(e[0] == s for e in examples):
                    examples.append((s, hid, a, c[a], b, c[b], N, out))
        print(f"{s:18} close pairs: {len(per_set[s].get('skim 5%', []))}", flush=True)

    print(f"\nall sets, {len(res['skim 5%'])} close comparisons (chance = 0.50)")
    for k2, v in res.items():
        print(f"   {k2:24} {statistics.mean(v):.3f}")
    print("\nby set (skim 25% / full NB adj / full 90% random-err):")
    for s, d in per_set.items():
        if d:
            print(f"   {s:18} n={len(d['skim 5%']):>3}  {statistics.mean(d['skim 25%']):.2f} / "
                  f"{statistics.mean(d['full, NB adj']):.2f} / {statistics.mean(d['full, 90% random-err']):.2f}")
    print("\nexamples:")
    for e in examples:
        print("  ", e)
    json.dump({"all": {k: statistics.mean(v) for k, v in res.items()}, "n": len(res["skim 5%"]),
               "by_set": {s: {k: statistics.mean(v) for k, v in d.items()} for s, d in per_set.items() if d}},
              open(ROOT / "experiments" / "close_comparisons.json", "w"), indent=2)


if __name__ == "__main__":
    main()
