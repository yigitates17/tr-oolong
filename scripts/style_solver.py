"""Acceptance gate (d): the surface-format solver.

The other three solvers ask whether a question can be answered without reading
the haystack. This one asks something narrower and, for a cross-lingual
benchmark, sharper: can the label be recovered from how a record is *shaped* --
its length, whether it ends in a period, whether it contains ! or ? -- with no
lexical knowledge at all?

It exists because a corpus can encode its labels in formatting without any of the
other solvers noticing. The leakage solver looks for label words, the majority
baseline looks at answer skew, and the prior oracle looks at corpus statistics.
None of them sees "negative reviews are long and positive ones are short."

A format-solvable corpus still yields a valid aggregation task -- the model must
still classify every record and add up the results. What it stops being is a test
of reading the *language*. And if the effect is asymmetric across a TR/EN twin,
the cross-lingual comparison is confounded: a model can score well on the Turkish
half by measuring sentence lengths rather than by understanding Turkish. The
number to watch is therefore not either half's lift but the gap between them.

Reported per family as lift over that family's majority baseline, because a raw
score is uninterpretable for families whose majority baseline is already high.

Usage:
  python scripts/style_solver.py --config configs/*.json --json manifests/style_audit.json
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from scoring import score

SEP = "\n\n<<<###>>>\n\n"
RISE = {"tr": "arttı", "en": "rose"}
FALL = {"tr": "azaldı", "en": "fell"}


def style_key(text: str):
    """The entire feature set. Deliberately crude: if this is enough, that is the finding."""
    nw = len(text.split())
    bucket = 0 if nw <= 8 else 1 if nw <= 15 else 2 if nw <= 30 else 3
    return (text.rstrip().endswith("."), bool(re.search(r"[!?]", text)), bucket)


def fit(rows, text_col, label_col):
    """Learn label-per-shape from the SOURCE pool. The haystack is never inspected."""
    table = defaultdict(Counter)
    for r in rows:
        table[style_key(str(r[text_col]))][r[label_col]] += 1
    fallback = Counter(r[label_col] for r in rows).most_common(1)[0][0]
    return {k: c.most_common(1)[0][0] for k, c in table.items()}, fallback


def predict(q, counts, records, table, fallback):
    lang = q["language"]
    n = sum(counts.values()) or 1
    ranked = [lab for lab, _ in counts.most_common()]
    kind = q["kind"]
    if kind == "count":
        return str(counts.get(q["label"], 0))
    if kind == "proportion":
        return str(round(100 * counts.get(q["label"], 0) / n))
    if kind == "most_common":
        return ranked[0] if ranked else ""
    if kind == "least_common":
        return ranked[-1] if ranked else ""
    if kind == "second_most":
        return ranked[1] if len(ranked) > 1 else ""
    if kind == "shift":
        half = len(records) // 2

        def share(part):
            c = Counter(table.get(style_key(r), fallback) for r in part)
            return c.get(q["label"], 0) / max(len(part), 1)

        return RISE[lang] if share(records[half:]) > share(records[:half]) else FALL[lang]
    return None  # entity families need the entity axis, which format cannot supply


def run_set(cfg_path, baselines):
    cfg = json.loads(Path(cfg_path).read_text())
    out = Path(cfg["out_dir"])
    if not (out / "questions.jsonl").exists():
        return None

    import polars as pl
    src = cfg["source_path"]
    df = pl.read_csv(src) if src.endswith(".csv") else pl.read_parquet(src)
    rows = df.select([cfg["text_col"], cfg["label_col"]]).drop_nulls().to_dicts()
    table, fallback = fit(rows, cfg["text_col"], cfg["label_col"])

    hay, recs = {}, {}
    for line in (out / "haystacks.jsonl").open():
        h = json.loads(line)
        parts = [r.strip() for r in h["haystack"].split(SEP) if r.strip()]
        recs[h["haystack_id"]] = parts
        hay[h["haystack_id"]] = Counter(table.get(style_key(r), fallback) for r in parts)

    per = defaultdict(lambda: [0.0, 0])
    for line in (out / "questions.jsonl").open():
        q = json.loads(line)
        p = predict(q, hay[q["haystack_id"]], recs[q["haystack_id"]], table, fallback)
        if p is None:
            continue
        per[q["kind"]][0] += score(q, p)["exact"]
        per[q["kind"]][1] += 1

    base = baselines.get(out.name, {})
    fams, lifts = {}, []
    for k, (s, n) in sorted(per.items()):
        st = s / n
        mb = base.get(k, {}).get("majority_baseline")
        lift = None if mb is None else st - mb
        fams[k] = {"n": n, "style_exact": round(st, 3),
                   "majority_baseline": mb, "lift": None if lift is None else round(lift, 3)}
        if lift is not None:
            lifts.append(lift)
    return {"set": out.name, "language": cfg["language"],
            "families": fams,
            "mean_lift": round(sum(lifts) / len(lifts), 3) if lifts else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", nargs="+", required=True)
    ap.add_argument("--baseline", default="manifests/baseline_report.json",
                    help="trivial_baseline.py output, for the majority baselines")
    ap.add_argument("--json", default="manifests/style_audit.json")
    ap.add_argument("--fail-over", type=float, default=0.15,
                    help="fail if any set's mean lift exceeds this")
    a = ap.parse_args()

    baselines = {}
    if Path(a.baseline).exists():
        for s in json.loads(Path(a.baseline).read_text()):
            baselines[s["set"]] = s["families"]

    reports = [r for r in (run_set(c, baselines) for c in a.config) if r]
    print(f"{'set':22}{'family':15}{'style':>7}{'major':>8}{'lift':>8}")
    print("-" * 60)
    for r in reports:
        for k, v in r["families"].items():
            mb = "  n/a" if v["majority_baseline"] is None else f"{v['majority_baseline']:8.3f}"
            lf = "  n/a" if v["lift"] is None else f"{v['lift']:+8.3f}"
            print(f"{r['set'][:21]:22}{k:15}{v['style_exact']:7.3f}{mb}{lf}")
        print(f"{r['set'][:21]:22}{'== MEAN':15}{'':15}{r['mean_lift']:+8.3f}\n")

    by_lang = defaultdict(list)
    for r in reports:
        by_lang[r["language"]].append((r["set"], r["mean_lift"]))
    print("twin asymmetry is the number that matters for the cross-lingual claim:")
    for lang, items in sorted(by_lang.items()):
        print(f"  {lang}: " + ", ".join(f"{s}={m:+.3f}" for s, m in items))

    Path(a.json).write_text(json.dumps(reports, indent=2, ensure_ascii=False))
    print(f"\nreport -> {a.json}")

    bad = [r for r in reports if r["mean_lift"] is not None and r["mean_lift"] > a.fail_over]
    if bad:
        print("\nFAIL: format alone beats the majority baseline by more than "
              f"{a.fail_over} on: " + ", ".join(r["set"] for r in bad))
        sys.exit(1)
    print(f"\nPASS: no set is format-solvable beyond +{a.fail_over} over majority.")


if __name__ == "__main__":
    main()
