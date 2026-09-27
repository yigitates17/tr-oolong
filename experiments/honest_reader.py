"""Experiment: what does a realistic reader that reads EVERYTHING score?

Setup (2026-09-28). No language model. The reader is a word-count classifier
(multinomial Naive Bayes, Laplace smoothing) that labels every record in the
document, then answers from its own labels.

  * Training data: all distinct records used anywhere in that subset's
    documents, split into 5 parts by a hash of the text. Each record is
    labelled by a model trained on the other 4 parts, so it never labels a
    record it was trained on.
  * Two readers:
      nb        counts its own predicted labels ("classify and count")
      nb_adj    the same, corrected for its known error rates: for each label,
                estimated count = (predicted count - false-positive rate * N)
                / (true-positive rate - false-positive rate), rates measured on
                held-out records ("adjusted classify and count", Forman 2008).
                Only numeric answers are corrected.
  * Scored with relative, partial and exact on every question.

Its per-record accuracy is printed per subset: it is a weak reader compared to
a good language model, which is the point of including it. Mistakes made by a
real classifier cluster on similar labels instead of spreading evenly, which
is what the random-mistake readers in band_gap.py could not show.

Usage: python experiments/honest_reader.py
Writes experiments/honest_reader.jsonl (one row per question).
"""
import json
import re
import statistics
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from build_tr_oolong import tr_casefold                          # noqa: E402
from sampling_solver import load_set, answer_from_sample         # noqa: E402
from scoring import score                                        # noqa: E402

SETS = ["amazon_hpc_en", "en_intent", "en_intent_paired", "interpress_tr", "marc_en",
        "musteri_tr", "sikayet_tr", "sinema_tr", "tr_intent", "tr_intent_paired",
        "vitamins_tr"]
TOK = re.compile(r"\w+", re.UNICODE)
FOLDS = 5


def tokens(text, lang):
    t = tr_casefold(text) if lang == "tr" else text.lower()
    return TOK.findall(t)


def train_predict(texts, labels, lang):
    """Out-of-fold NB predictions for every text, plus out-of-fold confusion."""
    labs = sorted(set(labels))
    li = {l: i for i, l in enumerate(labs)}
    y = np.array([li[l] for l in labels])
    toks = [tokens(t, lang) for t in texts]
    df = Counter(w for ts in toks for w in set(ts))
    vocab = {w: i for i, (w, c) in enumerate(df.items()) if c >= 2}
    vocab = {w: i for i, w in enumerate(vocab)}
    V, K = len(vocab), len(labs)
    ids = [np.array([vocab[w] for w in ts if w in vocab], dtype=np.int64) for ts in toks]
    fold = np.array([zlib.crc32(t.encode()) % FOLDS for t in texts])
    per_fold = np.zeros((FOLDS, K, V))
    for i, a in enumerate(ids):
        if len(a):
            np.add.at(per_fold[fold[i], y[i]], a, 1)
    total = per_fold.sum(0)
    class_n = np.array([[np.sum((fold != f) & (y == k)) for k in range(K)] for f in range(FOLDS)])
    pred = np.empty(len(texts), dtype=np.int64)
    post = np.empty((len(texts), K))
    for f in range(FOLDS):
        cnt = total - per_fold[f]
        logp = np.log(cnt + 1.0) - np.log(cnt.sum(1, keepdims=True) + V)
        prior = np.log(class_n[f] + 1.0) - np.log(class_n[f].sum() + K)
        for i in np.nonzero(fold == f)[0]:
            lp = prior + logp[:, ids[i]].sum(1)
            post[i] = lp - np.logaddexp.reduce(lp)
            pred[i] = int(np.argmax(lp))
    conf = np.zeros((K, K))
    np.add.at(conf, (y, pred), 1)
    train_predict.last_post = {t: post[i] for i, t in enumerate(texts)}
    return {t: labs[p] for t, p in zip(texts, pred)}, labs, conf


def adjusted(q, pred_labels, true_space, conf, labs, N):
    """Adjusted classify-and-count for count / proportion questions."""
    if q["kind"] not in ("count", "proportion"):
        return None
    li = {l: i for i, l in enumerate(labs)}
    if q["label"] not in li:
        return None
    k = li[q["label"]]
    pos = conf[k].sum()
    neg = conf.sum() - pos
    tpr = conf[k, k] / pos if pos else 1.0
    fpr = (conf[:, k].sum() - conf[k, k]) / neg if neg else 0.0
    raw = sum(1 for l in pred_labels if l == q["label"])
    est = (raw - fpr * N) / (tpr - fpr) if tpr - fpr > 0.05 else raw
    est = max(0.0, est)
    if q["kind"] == "count":
        return str(round(est))
    unit = 1000 if q.get("unit") == "per_mille" else 100
    return str(round(est / N * unit))


def main():
    out = []
    for s in SETS:
        d = ROOT / f"{s}_out"
        qs, metas = load_set(d)
        lang = qs[0]["language"]
        grades = {r["uid"]: r for r in map(json.loads, open(d / "difficulty.jsonl"))}
        pool = {}
        for m in metas.values():
            for t, l in zip(m["text"].to_list(), m["label"].to_list()):
                pool[t] = l
        texts = list(pool)
        pred_of, labs, conf = train_predict(texts, [pool[t] for t in texts], lang)
        acc = np.trace(conf) / conf.sum()
        rows_scored = 0
        for q in qs:
            m = metas[q["haystack_id"]]
            tx, ent, half = m["text"].to_list(), m["entity"].to_list(), m["half"].to_list()
            pl_ = [pred_of[t] for t in tx]
            rows = list(zip(pl_, ent, half))
            fam = grades[q["uid"]]["family"]
            r = {"uid": q["uid"], "set": s, "family": fam, "kind": q["kind"],
                 "answer": q["answer"], "N": len(tx), "reader_accuracy": round(float(acc), 3)}
            for name, pred in (("nb", answer_from_sample(q, rows, 1.0)),
                               ("nb_adj", adjusted(q, pl_, None, conf, labs, len(tx))
                                or answer_from_sample(q, rows, 1.0))):
                sc = score(q, pred) if pred is not None else {"exact": 0, "partial": 0, "relative": 0}
                for k2, v in sc.items():
                    r[f"{name}_{k2}"] = round(v, 4)
                r[f"{name}_pred"] = pred
            # Coverage curve with the SAME classifier: read a random fraction
            # of records, label them with the NB model, scale up (and correct).
            # Isolates what reading more buys when classification is held fixed.
            rng = np.random.default_rng(zlib.crc32(q["uid"].encode()))
            Nq = len(tx)
            for frac in (0.05, 0.25):
                k = max(1, round(Nq * frac))
                acc_s = defaultdict(list)
                for _ in range(20):
                    idx = rng.choice(Nq, k, replace=False)
                    sub = [rows[i] for i in idx]
                    p1 = answer_from_sample(q, sub, k / Nq)
                    p2 = adjusted(q, [rows[i][0] for i in idx], None, conf, labs, k)
                    if p2 is not None and q["kind"] == "count":
                        p2 = str(round(int(p2) * Nq / k))
                    p2 = p2 or p1
                    for name, pred in (("nb", p1), ("nb_adj", p2)):
                        sc = score(q, pred) if pred is not None else {"exact": 0, "partial": 0, "relative": 0}
                        for k2, v in sc.items():
                            acc_s[f"{name}{int(frac*100)}_{k2}"].append(v)
                for key, v in acc_s.items():
                    r[key] = round(sum(v) / len(v), 4)
            out.append(r)
            rows_scored += 1
        print(f"{s:18} records {len(texts):>7}  per-record accuracy {acc:.3f}  questions {rows_scored}",
              flush=True)
    (ROOT / "experiments" / "honest_reader.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")

    for metric in ("relative", "partial", "exact"):
        print(f"\n=== {metric}: same classifier, reading 5% / 25% / 100% of records ===")
        cols = [f"nb5_{metric}", f"nb25_{metric}", f"nb_{metric}",
                f"nb_adj5_{metric}", f"nb_adj25_{metric}", f"nb_adj_{metric}"]
        print(f"{'family':14}{'n':>6}" + "".join(f"{h:>10}" for h in
              ["5%", "25%", "100%", "adj 5%", "adj 25%", "adj 100%"]))
        for fam in sorted({r["family"] for r in out}):
            v = [r for r in out if r["family"] == fam]
            print(f"{fam:14}{len(v):>6}" + "".join(
                f"{statistics.mean(r[c] for r in v):>10.3f}" for c in cols))


if __name__ == "__main__":
    main()
