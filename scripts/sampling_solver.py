#!/usr/bin/env python3
"""Acceptance gate (e): the partial-coverage solvers.

The other four solvers ask whether a question can be answered WITHOUT reading
the haystack -- by substring search, by answer skew, from corpus statistics, or
from surface formatting. This one asks something the other four are structurally
blind to: **can it be answered by reading only PART of the haystack?**

Why that matters here specifically. This benchmark's answers are large (the
median `count` is near 1,000), and under the scale-free `relative` metric a
few percent off scores very well. Two partial readers are modelled, because
they are the two things a real model actually does:

  random   classify a uniformly random FRACTION of the records and scale up.
           This is what an agent with code execution can do deliberately.
  prefix   classify the FIRST k records and scale up. This is what every
           context-limited model does by default when the document is longer
           than its window -- truncation, not sampling.

Both are run at fixed fractions AND at fixed absolute sizes. The absolute-size
run is the one that tests the length axis: if reading 1,000 records scores the
same at 100K tokens as at 1M, the length gradient is not measuring aggregation
under this metric.

Two references are printed next to every number, because the wrong one was
used once. `majority` is the exact-match frequency of the most common gold
answer; it is the right reference for categorical families and the WRONG one
for numeric families under `relative`, where a solver that reads nothing but
knows the record count (N/K for `count`, 100/K for `proportion`) already earns
substantial partial credit. That `blind` reference is what a numeric family's
score must be read against.

A third reference, `fullread@acc`, is a perfect-coverage reader with a noisy
classifier (symmetric confusion at the given accuracy). It is here to make the
attribution problem visible: when a 5% perfect-label sample outscores a 90%
accurate full read, a single `relative` score cannot say whether the model read
more or classified better.

What none of these models, deliberately: the classification step. The
sampling solvers are given the true label of every record they read, so they
are UPPER BOUNDS -- a perfect classifier reading a fraction. A real model does
worse. An upper bound is the right tool: if even the perfect-classifier version
cannot beat the reference, no partial-reading strategy threatens the family.

Usage:
  python scripts/sampling_solver.py                       # every built set
  python scripts/sampling_solver.py --sets vitamins_tr_out musteri_tr_out
  python scripts/sampling_solver.py --fractions 0.05 0.10 0.25 --absolute 500 1000
  python scripts/sampling_solver.py --fail-over 0.15      # turn the report into a gate
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

NUMERIC = ("count", "proportion", "entity_count")


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


def blind_prediction(q: dict, n_records: int, n_labels: int) -> str | None:
    """A reader that opens nothing but knows how many records there are (the
    separator count) and how many labels the question space has. This is the
    floor a numeric family must be judged against under `relative`."""
    if q["kind"] == "count":
        return str(round(n_records / n_labels))
    if q["kind"] == "proportion":
        unit = 1000 if q.get("unit") == "per_mille" else 100
        return str(round(unit / n_labels))
    return None            # entity_count: no blind estimate without the entity size


def noisy_labels(labels: list[str], acc: float, space: list[str], rng: random.Random) -> list[str]:
    """Symmetric confusion: keep the label with p=acc, else a uniformly random
    OTHER label. Deliberately the most benign noise model there is -- real
    models confuse neighbouring classes, which is worse for counts."""
    out = []
    for l in labels:
        if rng.random() < acc or len(space) < 2:
            out.append(l)
        else:
            o = rng.choice(space)
            while o == l:
                o = rng.choice(space)
            out.append(o)
    return out


def _tier(q: dict):
    return q.get("target_tokens") or q.get("target_records")


def _mean(v):
    return sum(v) / len(v) if v else None


def run_set(d: Path, fractions: list[float], absolutes: list[int], trials: int,
            seed: int, accuracies: list[float]) -> dict:
    qs, metas = load_set(d)
    F = lambda: {"gold": [], "blind": [], "random": defaultdict(list),   # noqa: E731
                 "prefix": defaultdict(list), "fullread": defaultdict(list),
                 "tier": defaultdict(lambda: defaultdict(list))}
    fam: dict[str, dict] = defaultdict(F)

    for q in qs:
        meta = metas.get(q["haystack_id"])
        if meta is None:
            continue
        rows_all = list(zip(meta["label"].to_list(),
                            meta["entity"].to_list(),
                            meta["half"].to_list()))
        labels_all = [r[0] for r in rows_all]
        space = sorted(set(labels_all))
        N, K, tier = len(rows_all), len(space), _tier(q)
        f = fam[q["kind"]]
        a = q["answer"]
        f["gold"].append(tuple(a) if isinstance(a, list) else a)

        b = blind_prediction(q, N, K)
        if b is not None:
            f["blind"].append(score(q, b)["relative"])

        for frac in fractions:
            rng = random.Random(f"{seed}-{q['id']}-{frac}")
            k = max(1, int(round(N * frac)))
            got = []
            for _ in range(trials):
                pred = answer_from_sample(q, rng.sample(rows_all, k), frac)
                if pred is not None:
                    got.append(score(q, pred)["relative"])
            if got:
                f["random"][frac].append(sum(got) / len(got))
            pred = answer_from_sample(q, rows_all[:k], frac)
            if pred is not None:
                f["prefix"][frac].append(score(q, pred)["relative"])

        for k in absolutes:
            if k >= N:
                continue
            frac = k / N
            rng = random.Random(f"{seed}-{q['id']}-abs{k}")
            got = []
            for _ in range(trials):
                pred = answer_from_sample(q, rng.sample(rows_all, k), frac)
                if pred is not None:
                    got.append(score(q, pred)["relative"])
            if got:
                f["tier"][tier][f"random@{k}"].append(sum(got) / len(got))
            pred = answer_from_sample(q, rows_all[:k], frac)
            if pred is not None:
                f["tier"][tier][f"prefix@{k}"].append(score(q, pred)["relative"])

        for acc in accuracies:
            rng = random.Random(f"{seed}-{q['id']}-acc{acc}")
            got = []
            for _ in range(max(1, trials // 3)):
                nl = noisy_labels(labels_all, acc, space, rng)
                nrows = [(nl[i], rows_all[i][1], rows_all[i][2]) for i in range(N)]
                pred = answer_from_sample(q, nrows, 1.0)
                if pred is not None:
                    got.append(score(q, pred)["relative"])
            if got:
                f["fullread"][acc].append(sum(got) / len(got))

    out = {}
    for kind, f in fam.items():
        counts = Counter(f["gold"])
        majority = max(counts.values()) / len(f["gold"])
        blind = _mean(f["blind"])
        out[kind] = {
            "n": len(f["gold"]),
            "majority_baseline": round(majority, 3),
            "blind_baseline": None if blind is None else round(blind, 3),
            "reference": round(max(majority, blind or 0.0), 3),
            "by_fraction": {str(k): round(_mean(v), 3) for k, v in sorted(f["random"].items())},
            "prefix_by_fraction": {str(k): round(_mean(v), 3) for k, v in sorted(f["prefix"].items())},
            "fullread_by_accuracy": {str(k): round(_mean(v), 3) for k, v in sorted(f["fullread"].items())},
            "by_tier": {str(t): {name: round(_mean(v), 3) for name, v in sorted(d.items())}
                        for t, d in sorted(f["tier"].items(), key=lambda kv: kv[0])},
        }
    return {"set": d.name, "families": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", nargs="+", default=None)
    ap.add_argument("--fractions", nargs="+", type=float, default=[0.05, 0.10, 0.25])
    ap.add_argument("--absolute", nargs="+", type=int, default=[500, 1000],
                    help="fixed record counts, reported per length tier")
    ap.add_argument("--accuracies", nargs="+", type=float, default=[0.7, 0.9],
                    help="classifier accuracies for the full-read reference")
    ap.add_argument("--trials", type=int, default=10,
                    help="random samples averaged per question per fraction")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json", default="manifests/sampling_audit.json")
    ap.add_argument("--fail-over", type=float, default=None,
                    help="exit 1 if the best partial reader beats the reference by more "
                         "than this. Off by default: this solver is REPORTED as a "
                         "limitation, not passed as a gate (README 4e).")
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

    reports = [run_set(ROOT / s, args.fractions, args.absolute, args.trials, args.seed,
                       args.accuracies) for s in sets]

    fr = [str(f) for f in sorted(args.fractions)]
    acc = [str(a) for a in sorted(args.accuracies)]
    head = ("".join(f"{('rnd ' + f):>9}" for f in fr) + "".join(f"{('pfx ' + f):>9}" for f in fr)
            + "".join(f"{('full@' + a):>9}" for a in acc))
    print(f"{'set':22}{'family':15}{'major':>7}{'blind':>7}{head}{'   lift':>8}")
    print("-" * (51 + 9 * (2 * len(fr) + len(acc)) + 8))
    worst = []
    for r in reports:
        for kind, v in sorted(r["families"].items()):
            cells = "".join(f"{v['by_fraction'].get(f, float('nan')):>9.3f}" for f in fr)
            cells += "".join(f"{v['prefix_by_fraction'].get(f, float('nan')):>9.3f}" for f in fr)
            cells += "".join(f"{v['fullread_by_accuracy'].get(a, float('nan')):>9.3f}" for a in acc)
            best = max(list(v["by_fraction"].values()) + list(v["prefix_by_fraction"].values()) + [0.0])
            lift = best - v["reference"]
            worst.append((lift, r["set"], kind))
            flag = "  <== " if args.fail_over is not None and lift > args.fail_over else ""
            bl = "     -" if v["blind_baseline"] is None else f"{v['blind_baseline']:6.3f}"
            print(f"{r['set'][:21]:22}{kind:15}{v['majority_baseline']:7.3f} {bl}{cells}{lift:>+8.3f}{flag}")
        print()

    print("=== fixed record budget, by length tier (count) -- does the length axis bite? ===")
    names = [f"{m}@{k}" for k in args.absolute for m in ("random", "prefix")]
    print(f"{'set':22}{'tier':>9}" + "".join(f"{n:>13}" for n in names))
    for r in reports:
        fam = r["families"].get("count")
        if not fam:
            continue
        for t, d in fam["by_tier"].items():
            print(f"{r['set'][:21]:22}{t:>9}" + "".join(f"{d.get(n, float('nan')):>13.3f}" for n in names))
        print()

    Path(args.json).write_text(json.dumps(reports, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    print(f"report -> {args.json}")
    print("\nHOW TO READ THIS\n"
          "  rnd f     perfect classifier, uniformly random f of the records, scaled up\n"
          "  pfx f     perfect classifier, FIRST f of the records (truncation), scaled up\n"
          "  full@a    every record read, classifier correct with probability a\n"
          "  major     exact-match frequency of the most common gold answer\n"
          "  blind     reads nothing; answers N/K (count) or 100/K (proportion) under `relative`\n"
          "  lift      best partial reader minus max(major, blind)\n"
          "  The sampling solvers are handed the TRUE label of every record they read, so\n"
          "  they are upper bounds. A real model scores lower on the reading it does do.")

    if args.fail_over is not None:
        bad = [w for w in worst if w[0] > args.fail_over]
        if bad:
            print(f"\nFAIL: a partial reader beats the reference by more than {args.fail_over} on:")
            for lift, s, k in sorted(bad, reverse=True):
                print(f"   {s} / {k}: {lift:+.3f}")
            return 1
        print(f"\nPASS: no family is partially-readable beyond +{args.fail_over} over its reference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
