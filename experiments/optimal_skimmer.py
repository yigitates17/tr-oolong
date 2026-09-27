"""Experiment: the best score ANY random-sample reader can get, per question.

Setup (2026-09-28). No model is involved. For every numeric question
(count, entity_count, proportion) we compute, exactly rather than by
simulation, the expected score of the Bayes-optimal skimmer:

  * It reads a uniformly random fraction f of the records and is told the true
    label of each one (a perfect classifier on what it reads).
  * It knows the number of records N (count the separators) and, as an
    oracle, the exact distribution of true answers over all questions of the
    same subset, family and length tier. That is more than any real skimmer
    could know, which is what makes the result a ceiling.
  * Given h matching records in its sample, it answers whatever maximises its
    expected score under the metric being used.

No random-sample strategy can beat this ON AVERAGE over those questions, so
the family-level average is a ceiling for skimming at budget f. It is not a
per-question bound: on any single small-answer question some fixed guess is
exactly right by luck. Deterministic
positional readers (start, ends, stride) see an equally random subset because
records are shuffled, so the ceiling covers them in expectation.

Scores are computed exactly by summing over every possible number of hits h
(hypergeometric probabilities), so there is no sampling noise.

Usage: python experiments/optimal_skimmer.py [--fractions 0.05 0.25]
Writes experiments/optimal_skimmer.jsonl (one row per question and fraction)
and prints a summary.
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from sampling_solver import load_set                             # noqa: E402

SETS = ["amazon_hpc_en", "en_intent", "en_intent_paired", "interpress_tr", "marc_en",
        "musteri_tr", "sikayet_tr", "sinema_tr", "tr_intent", "tr_intent_paired",
        "vitamins_tr"]
NUMERIC = ("count", "entity_count", "proportion")
LOGF = np.concatenate([[0.0], np.cumsum(np.log(np.arange(1, 20001)))])


def log_hyper(h, y, N, k):
    """log P(h hits in a k-sample | y marked among N), vectorised over y."""
    h, y = np.broadcast_arrays(np.asarray(h), np.asarray(y))
    ok = (h <= y) & (k - h <= N - y) & (h >= 0)
    out = np.full(y.shape, -np.inf)
    yy, hh = y[ok], h[ok]
    out[ok] = (LOGF[yy] - LOGF[hh] - LOGF[yy - hh]
               + LOGF[N - yy] - LOGF[k - hh] - LOGF[N - yy - k + hh]
               - (LOGF[N] - LOGF[k] - LOGF[N - k]))
    return out


def metric(a, y, name):
    """a: candidate answers (column), y: true values (row), in answer units."""
    err = np.abs(a[:, None] - y[None, :])
    if name == "partial":
        return 0.75 ** err
    if name == "exact":
        return (err == 0).astype(float)
    return np.maximum(0.0, 1.0 - err / np.maximum(y[None, :], 1))


def prior_counts(gold_counts, N, sigma=0.25, floor=1e-3):
    """Smoothed prior over the true count c in [0, N], from other questions'
    gold counts (log-normal kernel around each), plus a small log-uniform floor
    so no value is impossible."""
    c = np.arange(N + 1)
    lc = np.log(c + 0.5)
    w = np.zeros(N + 1)
    for g in gold_counts:
        w += np.exp(-0.5 * ((lc - math.log(g + 0.5)) / sigma) ** 2)
    w /= w.sum() if w.sum() > 0 else 1.0
    base = 1.0 / (c + 1.0)
    base /= base.sum()
    p = (1 - floor) * w + floor * base
    return p / p.sum()


def ceiling(true_c, N, k, prior, to_answer, gold_answer, metrics):
    """Expected score of the Bayes-optimal skimmer, for each metric."""
    support = np.nonzero(prior > 1e-9)[0]
    if true_c not in set(support.tolist()):
        support = np.union1d(support, [true_c])
    ans_of_c = to_answer(support)                       # answer implied by each c
    cand = np.unique(np.concatenate([ans_of_c, [0]]))
    if len(cand) > 1500:                                 # thin very wide supports
        cand = np.unique(np.quantile(cand, np.linspace(0, 1, 1500)).round().astype(int))
    logpri = np.log(prior[support])
    hs = np.arange(0, min(k, true_c) + 1)
    p_h = np.exp(log_hyper(hs[:, None], np.array([true_c]), N, k)[:, 0])
    keep = p_h > 1e-7
    hs, p_h = hs[keep], p_h[keep] / p_h[keep].sum()
    out = {m: 0.0 for m in metrics}
    for m in metrics:
        S = metric(cand, ans_of_c.astype(float), m)      # cand x support
        own = metric(cand, np.array([float(gold_answer)]), m)[:, 0]
        for h, ph in zip(hs, p_h):
            lp = logpri + log_hyper(h, support, N, k)
            post = np.exp(lp - lp.max())
            post /= post.sum()
            best = int(np.argmax(S @ post))
            out[m] += ph * own[best]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fractions", nargs="+", type=float, default=[0.01, 0.05, 0.10, 0.25])
    ap.add_argument("--metrics", nargs="+", default=["relative", "partial", "exact"])
    args = ap.parse_args()

    rows = []
    for s in SETS:
        d = ROOT / f"{s}_out"
        qs, metas = load_set(d)
        grades = {r["uid"]: r for r in map(json.loads, open(d / "difficulty.jsonl"))}
        info = []
        for q in qs:
            if q["kind"] not in NUMERIC:
                continue
            m = metas[q["haystack_id"]]
            lab, ent = m["label"].to_list(), m["entity"].to_list()
            N = len(lab)
            if q["kind"] == "entity_count":
                c = sum(1 for l, e in zip(lab, ent) if l == q["label"] and e == q["entity"])
            else:
                c = sum(1 for l in lab if l == q["label"])
            info.append((q, N, c))
        # pool for priors: same family and tier, as true counts
        pool = defaultdict(list)
        for q, N, c in info:
            pool[(q["kind"], q.get("target_tokens") or q.get("target_records"))].append((q["uid"], c))
        for q, N, c in info:
            tier = q.get("target_tokens") or q.get("target_records")
            # Oracle prior: the exact distribution of true counts over ALL
            # questions of this subset, family and tier, this one included.
            # Knowing the answer distribution perfectly is the most a skimmer
            # could know, so no strategy based on the sample can beat this on
            # average over these questions. (A blurred leave-one-out prior was
            # tried first and lost to the fixed "guess 12" reader, so it was
            # not a ceiling.)
            everyone = [cc for u, cc in pool[(q["kind"], tier)]]
            prior = prior_counts(everyone, N, sigma=0.02, floor=1e-6)
            if q["kind"] == "proportion":
                unit = 1000 if q.get("unit") == "per_mille" else 100
                to_answer = (lambda cs, N=N, unit=unit: np.round(np.asarray(cs) * unit / N).astype(int))
            else:
                to_answer = (lambda cs: np.asarray(cs).astype(int))
            for f in args.fractions:
                k = max(1, round(N * f))
                sc = ceiling(c, N, k, prior, to_answer, int(q["answer"]), args.metrics)
                rows.append({"uid": q["uid"], "set": s, "family": grades[q["uid"]]["family"],
                             "kind": q["kind"], "tier": tier, "N": N, "true_count": c,
                             "answer": int(q["answer"]), "fraction": f,
                             "old_grade": grades[q["uid"]]["difficulty"],
                             **{f"ceiling_{m}": round(v, 4) for m, v in sc.items()}})
        print(f"{s}: {len(info)} numeric questions done", flush=True)

    (ROOT / "experiments" / "optimal_skimmer.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    for f in args.fractions:
        sub = [r for r in rows if r["fraction"] == f]
        print(f"\n=== fraction {f}: mean ceiling by family ===")
        fams = sorted({r["family"] for r in sub})
        print(f"{'family':14}{'n':>6}" + "".join(f"{m:>11}" for m in args.metrics))
        for fam in fams:
            v = [r for r in sub if r["family"] == fam]
            print(f"{fam:14}{len(v):>6}" + "".join(
                f"{np.mean([r['ceiling_' + m] for r in v]):>11.3f}" for m in args.metrics))


if __name__ == "__main__":
    main()
