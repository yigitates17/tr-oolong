#!/usr/bin/env python3
"""Acceptance gate (e): the partial-coverage solvers.

The other four solvers ask whether a question can be answered WITHOUT reading
the haystack -- by substring search, by answer skew, from corpus statistics, or
from surface formatting. This one asks something the other four are structurally
blind to: **can it be answered by reading only PART of the haystack?**

Why that matters here specifically. This benchmark's answers are large (the
median `count` is near 1,000), and under the scale-free `relative` metric a
few percent off scores very well. Four partial readers are modelled, because
they are the four things a real system actually does:

  random    classify a uniformly random FRACTION of the records and scale up.
            What an agent with code execution can do deliberately.
  prefix    classify the FIRST k records and scale up. What a context-limited
            model does by default when the document exceeds its window.
  headtail  classify k/2 records at the START and k/2 at the END, and scale up.
            What a model does when it is told the document has a beginning and
            an end and it can afford to look at both. Costs exactly what
            `prefix` costs.
  stride    classify k records EVENLY SPACED through the document. What a
            chunking harness gets by accident: split into chunks, look at a
            little of each.

**`headtail` and `stride` were added 2026-09-16, and they are the honest
readers.** Until then this gate modelled only `random` and `prefix`, and the
conclusion drawn from that pair -- that truncation degrades badly with length,
so the length axis bites -- was an artifact of `prefix` being the single
dumbest way to spend a reading budget. The haystack is assembled as two
internally-shuffled blocks split at n//2 (`order_and_assemble`), so every label
except the drift target is exchangeable across the whole document and the drift
target is exchangeable within each half. A contiguous head prefix is therefore
the ONLY cheap reader that is biased, and it is biased for a reason that has
nothing to do with length. Any reader that touches both halves recovers the
document, and `headtail` at 100 records matches `random` at 100 records on
`count` and `proportion`, and scores 1.000 on `shift`. Report all four or the
gate flatters the benchmark.

Both are run at fixed fractions AND at fixed absolute sizes. The absolute-size
run is the one that tests the length axis: if reading 1,000 records scores the
same at 100K tokens as at 1M, the length gradient is not measuring aggregation
under this metric.

**Coverage is reported next to every score.** A reader that cannot answer a
family at all is not the same as a reader that answers it badly, and the
difference was invisible before: `prefix` returns no answer for `shift`
(every record it reads is in the first half), so `shift` silently had no
prefix number in any shipped manifest rather than an honest one. `cov` is the
fraction of the family's questions the reader could answer; the score is the
mean over exactly those. Read a score with cov < 1.00 as conditional.

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
  python scripts/sampling_solver.py --fractions 0.05 0.10 0.25 --absolute 100 500 1000
  python scripts/sampling_solver.py --readers random headtail
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



# ---------------------------------------------------------------------------
# The four readers. Each spends the SAME budget of k records; they differ only
# in WHERE in the document those records are taken from.
#
# `random` is the only stochastic one, so it is the only one averaged over
# trials; the other three are deterministic given the document, which is the
# point -- a model does not need a random number generator to run them.
# ---------------------------------------------------------------------------

def read_random(rows: list[tuple], k: int, rng: random.Random) -> list[tuple]:
    return rng.sample(rows, k)


def read_prefix(rows: list[tuple], k: int, rng: random.Random) -> list[tuple]:
    return rows[:k]


def read_headtail(rows: list[tuple], k: int, rng: random.Random) -> list[tuple]:
    """k//2 from the start, the rest from the end. Costs exactly what `prefix`
    costs and is the reader the earlier version of this gate omitted."""
    h = k // 2
    return rows[:h] + rows[len(rows) - (k - h):]


def read_stride(rows: list[tuple], k: int, rng: random.Random) -> list[tuple]:
    """k evenly spaced records spanning the whole document, endpoints included.
    What a chunk-and-sample harness produces without intending to sample."""
    n = len(rows)
    if k < 2:
        return rows[:1]
    return [rows[round(i * (n - 1) / (k - 1))] for i in range(k)]


READERS = {
    "random": read_random,
    "prefix": read_prefix,
    "headtail": read_headtail,
    "stride": read_stride,
}
STOCHASTIC = {"random"}


def run_set(d: Path, fractions: list[float], absolutes: list[int], trials: int,
            seed: int, accuracies: list[float], readers: list[str]) -> dict:
    qs, metas = load_set(d)

    def F():
        return {"gold": [], "blind": [],
                # reader -> fraction -> list of per-question scores
                "frac": defaultdict(lambda: defaultdict(list)),
                # reader -> fraction -> number of questions the reader could answer
                "frac_n": defaultdict(lambda: defaultdict(int)),
                "fullread": defaultdict(list),
                "tier": defaultdict(lambda: defaultdict(list))}

    fam: dict[str, dict] = defaultdict(F)

    def sample_score(q, rows_all, k, frac, name, tag):
        """Mean `relative` score for one reader at one budget, or None if the
        reader cannot answer this question at all."""
        fn = READERS[name]
        n_trials = trials if name in STOCHASTIC else 1
        got = []
        for t in range(n_trials):
            rng = random.Random(f"{seed}-{q['id']}-{tag}-{name}-{t}")
            pred = answer_from_sample(q, fn(rows_all, k, rng), frac)
            if pred is not None:
                got.append(score(q, pred)["relative"])
        return (sum(got) / len(got)) if got else None

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
            k = max(1, min(N, int(round(N * frac))))
            for name in readers:
                s = sample_score(q, rows_all, k, k / N, name, f"frac{frac}")
                if s is not None:
                    f["frac"][name][frac].append(s)
                f["frac_n"][name][frac] += 1

        for k in absolutes:
            if k >= N:
                continue
            for name in readers:
                s = sample_score(q, rows_all, k, k / N, name, f"abs{k}")
                if s is not None:
                    f["tier"][tier][f"{name}@{k}"].append(s)

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
        rd = {}
        for name in readers:
            by_frac, cov = {}, {}
            for frac, v in sorted(f["frac"][name].items()):
                by_frac[str(frac)] = round(_mean(v), 3)
            for frac, n in sorted(f["frac_n"][name].items()):
                answered = len(f["frac"][name].get(frac, []))
                cov[str(frac)] = round(answered / n, 3) if n else 0.0
            rd[name] = {"by_fraction": by_frac, "coverage": cov}
        out[kind] = {
            "n": len(f["gold"]),
            "majority_baseline": round(majority, 3),
            "blind_baseline": None if blind is None else round(blind, 3),
            "reference": round(max(majority, blind or 0.0), 3),
            "readers": rd,
            # kept as aliases so older prose citing these names stays valid
            "by_fraction": rd.get("random", {}).get("by_fraction", {}),
            "prefix_by_fraction": rd.get("prefix", {}).get("by_fraction", {}),
            "fullread_by_accuracy": {str(k): round(_mean(v), 3)
                                     for k, v in sorted(f["fullread"].items())},
            "by_tier": {str(t): {name: round(_mean(v), 3) for name, v in sorted(dd.items())}
                        for t, dd in sorted(f["tier"].items(), key=lambda kv: kv[0])},
        }
    return {"set": d.name, "families": out}

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", nargs="+", default=None)
    ap.add_argument("--fractions", nargs="+", type=float, default=[0.05, 0.10, 0.25])
    ap.add_argument("--absolute", nargs="+", type=int, default=[100, 500, 1000],
                    help="fixed record counts, reported per length tier. 100 is here "
                         "because it is the budget at which headtail already matches "
                         "a uniform random sample on count and proportion.")
    ap.add_argument("--readers", nargs="+", default=list(READERS),
                    choices=list(READERS),
                    help="which partial readers to model (default: all four)")
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
                       args.accuracies, args.readers) for s in sets]

    fr = [str(f) for f in sorted(args.fractions)]
    acc = [str(a) for a in sorted(args.accuracies)]

    def cell(v, cov):
        """Score, with a trailing * when the reader could not answer every
        question in the family. A conditional mean is not a comparable mean."""
        if v is None:
            return f"{'-':>9}"
        return f"{v:>8.3f}{'*' if cov is not None and cov < 0.999 else ' '}"

    # --- one block per reader: same shape as the single table this replaces ---
    for name in args.readers:
        print(f"=== reader: {name} ===")
        head = "".join(f"{(name[:3] + ' ' + f):>9}" for f in fr)
        print(f"{'set':22}{'family':15}{'major':>7}{'blind':>7}{head}")
        print("-" * (51 + 9 * len(fr)))
        for r in reports:
            for kind, v in sorted(r["families"].items()):
                rd = v["readers"].get(name, {})
                bf, cv = rd.get("by_fraction", {}), rd.get("coverage", {})
                cells = "".join(cell(bf.get(f), cv.get(f)) for f in fr)
                bl = "     -" if v["blind_baseline"] is None else f"{v['blind_baseline']:6.3f}"
                print(f"{r['set'][:21]:22}{kind:15}{v['majority_baseline']:7.3f} {bl}{cells}")
        print()

    # --- the reviewer-facing table: the BEST partial reader for each family ---
    print("=== worst case: the best partial reader for each family, and which one it is ===")
    print(f"{'set':22}{'family':15}{'ref':>7}{'best':>8}{'reader':>10}{'at':>7}{'lift':>8}")
    print("-" * 77)
    worst = []
    for r in reports:
        for kind, v in sorted(r["families"].items()):
            best, who, at = 0.0, "-", "-"
            for name in args.readers:
                for f, s in v["readers"].get(name, {}).get("by_fraction", {}).items():
                    if s > best:
                        best, who, at = s, name, f
            lift = best - v["reference"]
            worst.append((lift, r["set"], kind, who, at))
            flag = "  <== " if args.fail_over is not None and lift > args.fail_over else ""
            print(f"{r['set'][:21]:22}{kind:15}{v['reference']:7.3f}{best:8.3f}"
                  f"{who:>10}{at:>7}{lift:>+8.3f}{flag}")
        print()

    print("=== fixed record budget, by length tier (count) -- does the length axis bite? ===")
    names = [f"{m}@{k}" for k in args.absolute for m in args.readers]
    print(f"{'set':22}{'tier':>9}" + "".join(f"{n:>15}" for n in names))
    for r in reports:
        fam = r["families"].get("count")
        if not fam:
            continue
        for t, d in fam["by_tier"].items():
            row = "".join((f"{d[n]:>15.3f}" if n in d else f"{'-':>15}") for n in names)
            print(f"{r['set'][:21]:22}{t:>9}{row}")
        print()

    # --- the guard that would have caught `shift` -----------------------------
    # A reader that cannot ATTEMPT a family prints an empty cell, and an empty
    # cell looks exactly like a family no reader could crack. That is how
    # `shift` passed this gate until 2026-09-16: `prefix` returns no answer for
    # it, so its only positional cell was blank. Untested is not the same as
    # resistant, and the difference must be loud.
    blind_spots = []
    for r in reports:
        for kind, v in sorted(r["families"].items()):
            for name in args.readers:
                cov = v["readers"].get(name, {}).get("coverage", {})
                if cov and max(cov.values()) == 0.0:
                    blind_spots.append((r["set"], kind, name))
    if blind_spots:
        print("\n[blind spot] a reader could not ATTEMPT these at any fraction. An empty\n"
              "             cell here means UNTESTED, not resistant. Before shipping such a\n"
              "             family, check it against a reader that CAN attempt it:")
        for st, kind, name in blind_spots:
            print(f"   {st} / {kind}: `{name}` has zero coverage")

    Path(args.json).write_text(json.dumps(reports, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    print(f"report -> {args.json}")
    print("\nHOW TO READ THIS\n"
          "  random f    perfect classifier, uniformly random f of the records, scaled up\n"
          "  prefix f    perfect classifier, the FIRST f of the records, scaled up\n"
          "  headtail f  perfect classifier, f/2 at the start and f/2 at the end\n"
          "  stride f    perfect classifier, f of the records evenly spaced end to end\n"
          "  full@a      every record read, classifier correct with probability a\n"
          "  major       exact-match frequency of the most common gold answer\n"
          "  blind       reads nothing; answers N/K (count) or 100/K (proportion)\n"
          "  lift        best partial reader minus max(major, blind)\n"
          "  *           the reader could not answer every question in the family; the\n"
          "              score is a mean over the ones it could, so it is conditional.\n"
          "              `prefix` on `shift` is the case this marker exists for.\n"
          "  The sampling solvers are handed the TRUE label of every record they read, so\n"
          "  they are upper bounds. A real model scores lower on the reading it does do.\n"
          "  `prefix` is the only reader biased by document order, and `headtail` costs\n"
          "  exactly the same. Do not quote a prefix number as evidence that truncation\n"
          "  is costly without the headtail number beside it.")

    if args.fail_over is not None:
        bad = [w for w in worst if w[0] > args.fail_over]
        if bad:
            print(f"\nFAIL: a partial reader beats the reference by more than {args.fail_over} on:")
            for lift, s, k, who, at in sorted(bad, reverse=True):
                print(f"   {s} / {k}: {lift:+.3f}  ({who} at {at})")
            return 1
        print(f"\nPASS: no family is partially-readable beyond +{args.fail_over} over its reference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
