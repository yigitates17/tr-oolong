#!/usr/bin/env python3
"""Acceptance gate (e): the sampling-and-extrapolating solver.

The other four solvers ask whether a question can be answered WITHOUT reading
the haystack -- by substring search, by answer skew, from corpus statistics, or
from surface formatting. This one asks something the other four are structurally
blind to: **can it be answered by reading only a FRACTION of the haystack?**

Why that matters here specifically. This benchmark's central claim is that its
questions force a model to process every record. That claim is safe when gold
answers are small: you cannot estimate "4" by sampling. It is NOT obviously safe
at our magnitudes, where the median `count` answer is near 1,000. A model that
classifies a random 10% of records and multiplies by ten lands within a few
percent -- and under the scale-free `relative` metric a few percent off scores
very well. If that beats an honest full pass by a weak model, the benchmark is
measuring estimation rather than aggregation on those families.

This is the statistical dual of D1's lesson. There, a 0.84% lexical leak was
enough to determine an aggregate. Here the question is whether a 10% *sample* is.

What it does NOT model, deliberately: the classification step. The solver is
given the true label of every record it samples, so it is an UPPER BOUND -- a
perfect classifier that reads only a fraction. A real model would do worse. An
upper bound is the right tool: if even the perfect-classifier version cannot
beat the majority baseline, no sampling strategy threatens the family.

Ranking families get a second, harder test: the sample must reproduce the gold
ORDERING, where the builder already enforces a 10% margin between adjacent
ranks. Sampling error of the same size as that margin turns those into coin
flips, which is the interesting case.

Usage:
  python scripts/sampling_solver.py --sets vitamins_tr_out musteri_tr_out
  python scripts/sampling_solver.py --fractions 0.05 0.10 0.25 --trials 20
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scoring import score           # noqa: E402  the frozen metric, unchanged


def load_set(d: Path):
    qs = [json.loads(l) for l in (d / "questions.jsonl").open(encoding="utf-8")]
    metas = {f.name.split("meta_")[1][:-8]: pl.read_parquet(f)
             for f in d.glob("meta_*.parquet")}
    return qs, metas


def answer_from_sample(q: dict, rows: list[tuple], frac: float) -> str | None:
    """Answer the question from a SAMPLE of (label, entity, half), scaling
    counts back up by 1/frac. Returns None when the family cannot be attacked
    this way at all."""
    kind = q["kind"]
    labels = [r[0] for r in rows]
    scale = 1.0 / frac

    if kind == "count":
        return str(round(sum(1 for l in labels if l == q["label"]) * scale))

    if kind == "proportion":
        if not labels:
            return None
        share = sum(1 for l in labels if l == q["label"]) / len(labels)
        unit = 1000 if q.get("unit") == "per_mille" else 100
        return str(round(share * unit))

    if kind in ("most_common", "least_common", "second_most"):
        cand = q["candidates"]
        c = Counter(l for l in labels if l in cand)
        ranked = sorted(cand, key=lambda x: (-c[x], x))
        if kind == "most_common":
            return ranked[0]
        if kind == "least_common":
            return ranked[-1]
        return ranked[1] if len(ranked) > 1 else ranked[0]

    if kind == "label_vs_label":
        a, b = q["label_a"], q["label_b"]
        ca, cb = labels.count(a), labels.count(b)
        lang = q["language"]
        # the gold "same" band is 2% relative; a sample cannot resolve that, so
        # the solver answers the strict comparison and eats the ties it misses.
        if ca > cb:
            return "daha çok" if lang == "tr" else "more common"
        if ca < cb:
            return "daha az" if lang == "tr" else "less common"
        return "eşit" if lang == "tr" else "the same"

    if kind == "entity_count":
        n = sum(1 for l, e, _ in rows if l == q["label"] and e == q["entity"])
        return str(round(n * scale))

    if kind in ("entity_argmax", "pairwise"):
        cand = q["candidates"]
        c = Counter(e for l, e, _ in rows if l == q["label"] and e in cand)
        return sorted(cand, key=lambda x: (-c[x], x))[0]

    if kind == "shift":
        first = [l for l, _, h in rows if h == 0]
        second = [l for l, _, h in rows if h == 1]
        if not first or not second:
            return None
        p1 = first.count(q["label"]) / len(first)
        p2 = second.count(q["label"]) / len(second)
        lang = q["language"]
        rose = p2 > p1
        return ("arttı" if rose else "azaldı") if lang == "tr" else ("rose" if rose else "fell")

    return None


def run_set(d: Path, fractions: list[float], trials: int, seed: int) -> dict:
    qs, metas = load_set(d)
    by_kind: dict[str, dict[float, list[float]]] = defaultdict(lambda: defaultdict(list))
    gold_by_kind: dict[str, list] = defaultdict(list)

    for q in qs:
        meta = metas.get(q["haystack_id"])
        if meta is None:
            continue
        rows_all = list(zip(meta["label"].to_list(),
                            meta["entity"].to_list(),
                            meta["half"].to_list()))
        a = q["answer"]
        gold_by_kind[q["kind"]].append(tuple(a) if isinstance(a, list) else a)
        for frac in fractions:
            rng = random.Random(f"{seed}-{q['id']}-{frac}")
            k = max(1, int(round(len(rows_all) * frac)))
            best = []
            for _ in range(trials):
                sample = rng.sample(rows_all, k)
                pred = answer_from_sample(q, sample, frac)
                if pred is None:
                    continue
                best.append(score(q, pred)["relative"])
            if best:
                by_kind[q["kind"]][frac].append(sum(best) / len(best))

    fam = {}
    for kind, per_frac in by_kind.items():
        counts = Counter(gold_by_kind[kind])
        majority = max(counts.values()) / len(gold_by_kind[kind])
        fam[kind] = {
            "n": len(gold_by_kind[kind]),
            "majority_baseline": round(majority, 3),
            "by_fraction": {str(f): round(sum(v) / len(v), 3) for f, v in sorted(per_frac.items())},
        }
    return {"set": d.name, "families": fam}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", nargs="+", default=None)
    ap.add_argument("--fractions", nargs="+", type=float, default=[0.05, 0.10, 0.25])
    ap.add_argument("--trials", type=int, default=10,
                    help="random samples averaged per question per fraction")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json", default="manifests/sampling_audit.json")
    ap.add_argument("--fail-over", type=float, default=0.15,
                    help="fail if sampling beats the majority baseline by more than this")
    args = ap.parse_args()

    sets = args.sets
    if not sets:
        sets = []
        for cfg in sorted((ROOT / "configs").glob("*.json")):
            try:
                o = json.loads(cfg.read_text(encoding="utf-8"))["out_dir"]
            except (json.JSONDecodeError, KeyError):
                continue
            if (ROOT / o / "questions.jsonl").exists():
                sets.append(o)

    reports = [run_set(ROOT / s, args.fractions, args.trials, args.seed) for s in sets]

    fr = [str(f) for f in sorted(args.fractions)]
    head = "".join(f"{('f=' + f):>9}" for f in fr)
    print(f"{'set':22}{'family':15}{'major':>7}{head}{'   worst lift':>13}")
    print("-" * (44 + 9 * len(fr) + 13))
    worst_overall = []
    for r in reports:
        for kind, v in sorted(r["families"].items()):
            cells = "".join(f"{v['by_fraction'].get(f, float('nan')):>9.3f}" for f in fr)
            lift = max(v["by_fraction"].values()) - v["majority_baseline"]
            worst_overall.append((lift, r["set"], kind))
            flag = "  <== " if lift > args.fail_over else ""
            print(f"{r['set'][:21]:22}{kind:15}{v['majority_baseline']:7.3f}{cells}{lift:>+13.3f}{flag}")
        print()

    Path(args.json).write_text(json.dumps(reports, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    print(f"report -> {args.json}")
    print("\nNOTE: the solver is handed the TRUE label of every record it samples, so it is\n"
          "      an upper bound -- a perfect classifier reading only a fraction. A real\n"
          "      model scores lower. Read a family as threatened only if THIS beats the\n"
          "      majority baseline comfortably.")

    bad = [w for w in worst_overall if w[0] > args.fail_over]
    if bad:
        print(f"\nFAIL: sampling beats the majority baseline by more than {args.fail_over} on:")
        for lift, s, k in sorted(bad, reverse=True):
            print(f"   {s} / {k}: {lift:+.3f}")
        return 1
    print(f"\nPASS: no family is sampling-solvable beyond +{args.fail_over} over majority.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
