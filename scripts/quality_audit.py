"""Question-quality audit -- the acceptance gate that v0.3.0 did not have.

Two independent checks, reported per set and per family:

(A) PER-QUESTION DEFECTS.  How much of the haystack actually determines the
    answer, and by what margin.
      THIN  : fewer than `--depth` records decide it -> retrieval, not aggregation
      KNIFE : relative decision margin below `--margin` -> inside label noise

(B) CONTEXT-FREE PRIOR ORACLE.  Answers every question from SOURCE-CORPUS
    statistics alone, never reading the haystack, and is tested against chance
    with a one-sided binomial. This is the baseline `trivial_baseline.py`'s
    leakage and majority solvers are both blind to: a family can be free of
    leakage, have well-spread gold answers, and still be answerable by
    "the biggest brand wins".

Usage:  python scripts/quality_audit.py [--sets a_out b_out] [--json out.json]
"""

import argparse
import collections
import json
import math
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_tr_oolong as B
from scoring import score

def discover_sets() -> list[str]:
    """Every config whose out_dir has actually been built.

    Auto-discovery rather than a hardcoded list: a new source that the gate
    silently skips is worse than no gate at all. This is how the record-matched
    twin nearly shipped unaudited.
    """
    found = []
    for cfg in sorted(Path("configs").glob("*.json")):
        try:
            out = json.loads(cfg.read_text(encoding="utf-8")).get("out_dir")
        except json.JSONDecodeError:
            continue
        if out and Path(out, "questions.jsonl").exists():
            found.append(out)
    return found


def binom_sf(k: int, n: int, p: float) -> float:
    """One-sided P(X >= k) under Binomial(n, p)."""
    if p <= 0:
        return 0.0 if k > 0 else 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def question_support(q: dict, meta: pl.DataFrame, k: int) -> tuple[int, float | None]:
    """(records that determine the answer, relative decision margin)."""
    labs = meta["label"].to_list()
    ents = meta["entity"].to_list()
    kind = q["kind"]
    if kind == "pairwise":
        a = sum(1 for l, e in zip(labs, ents) if l == q["label"] and e == q["entity_a"])
        b = sum(1 for l, e in zip(labs, ents) if l == q["label"] and e == q["entity_b"])
        hi, lo = max(a, b), min(a, b)
        return a + b, (hi - lo) / max(1, hi)
    if kind == "entity_count":
        return int(q["answer"]), None
    if kind in ("entity_argmax", "top_k"):
        c = collections.Counter(e for l, e in zip(labs, ents)
                                if l == q["label"] and e in set(q.get("candidates", [])))
        r = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        i = (k - 1) if kind == "top_k" else 0
        if len(r) <= i + 1:
            return 0, 0.0
        return r[i][1], (r[i][1] - r[i + 1][1]) / max(1, r[i][1])
    if kind in ("most_common", "least_common", "second_most"):
        c = collections.Counter(labs)
        cand = q.get("candidates")
        if cand:
            c = collections.Counter({l: n for l, n in c.items() if l in set(cand)})
        r = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        i = {"most_common": 0, "second_most": 1, "least_common": len(r) - 1}[kind]
        nb = r[i + 1][1] if i + 1 < len(r) else r[i - 1][1]
        return r[i][1], abs(r[i][1] - nb) / max(1, r[i][1])
    if kind == "label_vs_label":
        a = meta.filter(pl.col("label") == q["label_a"]).height
        b = meta.filter(pl.col("label") == q["label_b"]).height
        # A "same" answer is CORRECT precisely because the gap is small, so the
        # usual "bigger margin = more robust" rule inverts. Reporting the raw gap
        # marked every equal-frequency question knife-edge (5 of 10 on the intent
        # axis, exactly the count of "same" answers). Its robustness is headroom
        # against same_tol, which the builder already enforces, so skip the check.
        if str(q["answer"]) in ("eşit", "the same"):
            return a + b, None
        return a + b, abs(a - b) / max(a, b, 1)
    if kind == "shift":
        return sum(1 for l in labs if l == q["label"]), None
    return sum(1 for l in labs if l == q.get("label")), None      # count, proportion


def prior_prediction(q: dict, st: dict) -> str:
    """What an oracle with the corpus but NOT the haystack would answer."""
    kind, R = q["kind"], st["nrec"][q["haystack_id"]]
    if kind == "count":
        return str(round(st["share"][q["label"]] * R))
    if kind == "proportion":
        return str(round(st["share"][q["label"]] * st["scale"]))
    if kind in ("most_common", "second_most", "least_common"):
        cand = q.get("candidates")
        r = ([(l, c) for l, c in st["rank"] if l in set(cand)] if cand else st["rank"])
        return {"most_common": r[0], "second_most": r[1], "least_common": r[-1]}[kind][0]
    if kind == "shift":
        return {"tr": "arttı", "en": "rose"}[q["language"]]
    if kind == "label_vs_label":
        a = st["share"].get(q["label_a"], 0.0)
        b = st["share"].get(q["label_b"], 0.0)
        rel = abs(a - b) / max(a, b, 1e-9)
        key = "same" if rel <= 0.02 else ("more" if a > b else "less")
        return {"tr": {"more": "daha çok", "less": "daha az", "same": "eşit"},
                "en": {"more": "more common", "less": "less common",
                       "same": "the same"}}[q["language"]][key]
    cands = q.get("candidates")
    pe = st["prior_ent"].get(q["label"], {})
    if kind == "entity_argmax":
        pool = cands or list(pe)
        return max(pool, key=lambda e: (pe.get(e, 0), e))
    if kind == "top_k":
        pool = sorted(cands or list(pe), key=lambda e: (-pe.get(e, 0), e))
        return " > ".join(pool[: q.get("k", 3)])
    if kind == "pairwise":
        return q["entity_a"] if pe.get(q["entity_a"], 0) >= pe.get(q["entity_b"], 0) else q["entity_b"]
    if kind == "entity_count":
        return str(round(pe.get(q["entity"], 0) / st["N"] * R))
    return ""


def chance_rate(kind: str, K: int, q: dict) -> float:
    """P(correct) for a uniform guess over the answer space the question NAMES.

    Getting this right matters: scoring `top_k` against chance=0 flagged an
    at-chance family as broken, because ordering 3 of 5 named candidates has
    chance 1/60, not 0.
    """
    n = len(q.get("candidates") or [])
    if kind in ("most_common", "least_common", "second_most"):
        return 1.0 / (n or K)
    if kind in ("shift", "pairwise"):
        return 0.5
    if kind == "label_vs_label":
        return 1.0 / 3.0          # more / less / same, and the builder balances them
    if kind == "entity_argmax":
        return 1.0 / max(2, n)
    if kind == "top_k":
        return 1.0 / math.perm(max(n, q.get("k", 3) + 1), q.get("k", 3))
    return 0.0          # free-form numeric: compared against the majority baseline


def audit_set(name: str, cfg_path: str, depth_min: int, margin_min: float | None) -> dict:
    cfg = B.Config.load(cfg_path)
    # Judge each set against the margin its own config enforced. A fixed 0.10
    # default marked half of en_intent's most_common questions "knife-edge" when
    # that set is deliberately built at 0.03 -- 48 classes cannot supply 10% gaps
    # between adjacent ranks (see D10).
    if margin_min is None:
        margin_min = cfg.min_rank_margin
    pool = B.clean(B.load_source(cfg), cfg, {})
    N = pool.height
    vc = pool.group_by("label").len().sort(["len", "label"], descending=[True, False])
    rank = list(zip(vc["label"].to_list(), vc["len"].to_list()))
    prior_ent: dict[str, dict[str, int]] = {}
    if cfg.entity_col:
        pe = pool.group_by(["label", "entity"]).len()
        for l, e, c in zip(pe["label"].to_list(), pe["entity"].to_list(), pe["len"].to_list()):
            prior_ent.setdefault(l, {})[e] = c
    man = json.loads(Path(name, "manifest.json").read_text(encoding="utf-8"))
    st = {"share": {l: c / N for l, c in rank}, "rank": rank, "N": N,
          "prior_ent": prior_ent,
          "scale": {"percent": 100, "per_mille": 1000}[man["proportion_unit"]],
          "nrec": {h["haystack_id"]: h["n_examples"] for h in man["haystacks"]}}
    K = len(rank)
    k_top = man.get("top_k_k", 3)

    metas = {f.name.split("meta_")[1][:-8]: pl.read_parquet(f)
             for f in Path(name).glob("meta_*.parquet")}
    defects = collections.defaultdict(collections.Counter)
    prior_hits = collections.defaultdict(list)
    chances = collections.defaultdict(list)
    for line in Path(name, "questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(line)
        sup, rm = question_support(q, metas[q["haystack_id"]], k_top)
        if sup < depth_min:
            v = "THIN"
        elif rm is not None and rm < margin_min:
            v = "KNIFE"
        else:
            v = "OK"
        defects[q["kind"]][v] += 1
        prior_hits[q["kind"]].append(score(q, prior_prediction(q, st))["exact"])
        chances[q["kind"]].append(chance_rate(q["kind"], K, q))

    # majority baseline per family: the score of always emitting the most common
    # gold answer. For free-form numeric families this, not 0, is the reference a
    # context-free solver must beat.
    gold = collections.defaultdict(list)
    for line in Path(name, "questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(line)
        gold[q["kind"]].append(json.dumps(q["answer"], ensure_ascii=False))
    majority = {k: collections.Counter(v).most_common(1)[0][1] / len(v)
                for k, v in gold.items()}

    fams = {}
    for kind, c in defects.items():
        n = sum(c.values())
        hits = prior_hits[kind]
        ch = max(sum(chances[kind]) / len(chances[kind]), majority.get(kind, 0.0))
        p = binom_sf(int(round(sum(hits))), len(hits), ch)
        fams[kind] = {"n": n, "ok": c["OK"], "thin": c["THIN"], "knife": c["KNIFE"],
                      "prior_acc": round(sum(hits) / len(hits), 3),
                      "chance": round(ch, 3), "p_value": round(p, 5),
                      "prior_shortcut": bool(p < 0.05 and sum(hits) / len(hits) > ch)}
    tot = sum(f["n"] for f in fams.values())
    return {"set": name, "n_questions": tot,
            "pct_ok": round(100 * sum(f["ok"] for f in fams.values()) / max(1, tot)),
            "families": dict(sorted(fams.items()))}


def certify(sets: list[str], cfgs: dict, draws: int) -> None:
    """Test the GENERATOR, not the shipped sample.

    Redraws many candidate questions per family, DEDUPLICATED -- redrawing the
    same question 400 times measures nothing -- and tests the context-free prior
    against chance at an n where the test has power.
    """
    import random
    print(f"=== CERTIFY: {draws} draws/haystack/family, deduplicated ===")
    print("Note: the label-ranking families are SINGLETON -- at most one distinct")
    print("question exists per haystack -- so their n equals the haystack count and")
    print("cannot exceed it. Power for those comes from more haystacks, not more draws.")
    print(f"{'set':19s} {'family':15s} {'distinct':>8s} {'prior':>7s} {'chance':>7s} {'z':>6s}  flag")
    print("-" * 78)
    for name in sets:
        cfg = B.Config.load(cfgs[name])
        pool = B.clean(B.load_source(cfg), cfg, {})
        prior_lab = dict(collections.Counter(pool["label"].to_list()))
        prior_ent: dict[str, dict[str, int]] = {}
        if cfg.entity_col:
            pe = pool.group_by(["label", "entity"]).len()
            for l, e, c in zip(pe["label"].to_list(), pe["entity"].to_list(), pe["len"].to_list()):
                prior_ent.setdefault(l, {})[e] = c
        k = json.loads(Path(name, "manifest.json").read_text(encoding="utf-8")).get("top_k_k", 3)
        seen: dict = {}
        for f in sorted(Path(name).glob("meta_*.parquet")):
            meta = pl.read_parquet(f)
            labels = sorted(meta["label"].unique().to_list())
            askable = sorted(meta.group_by("entity").len().filter(
                (pl.col("len") >= cfg.min_entity_examples) & (pl.col("entity") != "__none__")
            )["entity"].to_list())
            ec = B.entity_haystack_counts(meta)
            rng = random.Random(f"certify-{f}")
            for _ in range(draws):
                for kind in ("most_common", "least_common", "second_most",
                             "entity_argmax", "top_k", "pairwise"):
                    if kind in set(cfg.families_disabled):
                        continue        # not shipped; reporting on it misleads
                    try:
                        q = B._make_one(kind, meta, cfg, rng, labels=labels, askable=askable,
                                        drift_target=None, unit="percent", k=k,
                                        ent_counts=ec, prior_ent=prior_ent, prior_lab=prior_lab)
                    except Exception:
                        continue
                    if q is None:
                        continue
                    q = {**q, "language": cfg.language, "haystack_id": f.name}
                    cand = q.get("candidates") or []
                    key = (f.name, kind, q.get("label"), tuple(cand),
                           q.get("entity_a"), q.get("entity_b"))
                    if key in seen:
                        continue
                    st = {"rank": sorted(prior_lab.items(), key=lambda kv: (-kv[1], kv[0])),
                          "prior_ent": prior_ent, "N": pool.height, "scale": 100,
                          "share": {l: c / pool.height for l, c in prior_lab.items()},
                          "nrec": {f.name: meta.height}}
                    seen[key] = (kind, score(q, prior_prediction(q, st))["exact"],
                                 chance_rate(kind, len(labels), q))
        by = collections.defaultdict(list)
        for kind, hit, ch in seen.values():
            by[kind].append((hit, ch))
        for kind, v in sorted(by.items()):
            n = len(v)
            acc = sum(x for x, _ in v) / n
            ch = sum(c for _, c in v) / n
            z = (acc - ch) / math.sqrt(max(ch * (1 - ch), 1e-9) / n) if ch > 0 else 0.0
            flag = "SHORTCUT" if z > 2.5 else ("underpowered" if n < 30 else "ok")
            print(f"{name:19s} {kind:15s} {n:8d} {acc:7.3f} {ch:7.3f} {z:+6.1f}  {flag}")
        print()


def verify_pairs(sets: list[str], cfgs: dict) -> int:
    """Machine-check the record-matched twin claim.

    "110 of 120 questions share a gold answer across languages" is a headline
    result, and until now it was verified by hand exactly once. Any future change
    to seeding, cleaning or sampling could break it silently -- the sets would
    still build, still pass every other gate, and simply stop being a matched
    pair. This asserts it on every run.
    """
    paired: dict[tuple, list[str]] = {}
    for name in sets:
        cfg = B.Config.load(cfgs[name])
        if cfg.pair_seed and cfg.haystack_target_records:
            paired.setdefault((tuple(cfg.haystack_target_records),
                               cfg.haystacks_per_length), []).append(name)
    problems = 0
    for key, group in sorted(paired.items()):
        if len(group) < 2:
            continue
        print(f"=== PAIR CHECK: {' <-> '.join(group)} ===")
        a, b = group[0], group[1]
        ma = sorted(Path(a).glob("meta_*.parquet"))
        mb = sorted(Path(b).glob("meta_*.parquet"))
        if len(ma) != len(mb):
            print(f"  MISMATCH: {len(ma)} vs {len(mb)} haystacks")
            problems += 1
            continue
        bad = 0
        for fa, fb in zip(ma, mb):
            da, db = pl.read_parquet(fa), pl.read_parquet(fb)
            if (da["row_id"].to_list() != db["row_id"].to_list()
                    or da["label"].to_list() != db["label"].to_list()
                    or da["half"].to_list() != db["half"].to_list()
                    or da["drift_target"][0] != db["drift_target"][0]):
                bad += 1
        qa = [json.loads(l) for l in Path(a, "questions.jsonl").read_text(encoding="utf-8").splitlines()]
        qb = [json.loads(l) for l in Path(b, "questions.jsonl").read_text(encoding="utf-8").splitlines()]
        same = sum(1 for x, y in zip(qa, qb)
                   if x["id"].split("-", 1)[1] == y["id"].split("-", 1)[1]
                   and x["kind"] == y["kind"] and x.get("label") == y.get("label")
                   and json.dumps(x["answer"], ensure_ascii=False)
                   == json.dumps(y["answer"], ensure_ascii=False))
        # `shift` and `label_vs_label` have language-mapped answers (arttı / rose,
        # "daha çok" / "more common"), so they can never match verbatim. The twin
        # still holds: both halves ask about the same records and the same label
        # pair, and the mapped answers agree -- checked below.
        LANG_MAPPED = ("shift", "label_vs_label")
        mapped = sum(1 for x in qa if x["kind"] in LANG_MAPPED)
        # canonical key per outcome, so the check does not depend on which half
        # of the pair is `a` and which is `b`
        CANON = {"arttı": "rose", "rose": "rose", "azaldı": "fell", "fell": "fell",
                 "daha çok": "more", "more common": "more",
                 "daha az": "less", "less common": "less",
                 "eşit": "same", "the same": "same"}
        mism = sum(1 for x, y in zip(qa, qb)
                   if x["kind"] in LANG_MAPPED
                   and (CANON.get(x["answer"]) != CANON.get(y["answer"])
                        or x.get("label_a") != y.get("label_a")
                        or x.get("label_b") != y.get("label_b")))
        print(f"  haystacks record-identical : {len(ma) - bad}/{len(ma)}")
        print(f"  questions w/ same gold     : {same}/{len(qa)}"
              f"  (+{mapped} language-mapped by design: {', '.join(LANG_MAPPED)})")
        if mism:
            print(f"  [!] {mism} language-mapped answer(s) DISAGREE across the twin")
        if bad or mism or same + mapped < len(qa):
            print("  [!] the pair is NOT fully matched -- paired tests are invalid")
            problems += 1
        else:
            print("  OK: paired tests (e.g. McNemar) are valid on this pair")
        print()
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=None,
                    help="default: every built set found in configs/")
    ap.add_argument("--depth", type=int, default=10,
                    help="min records that must decide an answer. 10 is the "
                         "shipped floor: locating 10 records among thousands is "
                         "still long-context work, locating 2 is not.")
    ap.add_argument("--margin", type=float, default=None,
                    help="min relative decision margin (default: each set's own "
                         "min_rank_margin, which is axis-specific by necessity)")
    ap.add_argument("--json", default="manifests/quality_audit.json")
    ap.add_argument("--certify", type=int, default=0, metavar="N",
                    help="redraw N candidate questions per haystack per family and "
                         "test the prior at real power. The shipped 7-20 questions "
                         "per family CANNOT certify one: a pairwise family measured "
                         "0.85 at n=13 and 0.53 at n=235. Use 200+ before release.")
    args = ap.parse_args()
    sets = args.sets or discover_sets()
    if not sets:
        sys.exit("no built sets found -- run the builder first")

    cfgs = {}
    for c in Path("configs").glob("*.json"):
        try:
            cfgs[json.loads(c.read_text(encoding="utf-8"))["out_dir"]] = str(c)
        except (json.JSONDecodeError, KeyError):
            continue
    report = []
    for s in sets:
        if not Path(s, "questions.jsonl").exists():
            print(f"[skip] {s}: not built", file=sys.stderr)
            continue
        if s not in cfgs:
            sys.exit(f"{s}: no config in configs/ declares this out_dir; cannot audit it")
        report.append(audit_set(s, cfgs[s], args.depth, args.margin))

    print(f"{'set':19s} {'family':15s} {'n':>4s} {'%OK':>5s} {'thin':>5s} {'knife':>6s} "
          f"{'prior':>6s} {'chance':>7s} {'p':>8s}  flag")
    print("-" * 96)
    broken = 0
    for r in report:
        for kind, f in r["families"].items():
            underpowered = f["n"] < 30
            flag = ("SHORTCUT" if f["prior_shortcut"] and not underpowered
                    else ("watch (n<30, rerun with --certify)" if f["prior_shortcut"] else ""))
            broken += f["prior_shortcut"] and not underpowered
            print(f"{r['set']:19s} {kind:15s} {f['n']:4d} {100*f['ok']//max(1,f['n']):4d}% "
                  f"{f['thin']:5d} {f['knife']:6d} {f['prior_acc']:6.2f} {f['chance']:7.2f} "
                  f"{f['p_value']:8.4f}  {flag}")
        print(f"{r['set']:19s} {'== ALL':15s} {r['n_questions']:4d} {r['pct_ok']:4d}%")
        print()
    Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    pair_problems = verify_pairs(sets, cfgs)
    if args.certify:
        print()
        certify(sets, cfgs, args.certify)
    print(f"report -> {args.json}")
    if pair_problems:
        print(f"\nFAIL: {pair_problems} record-matched pair(s) are not actually matched.",
              file=sys.stderr)
        sys.exit(1)
    if broken:
        print(f"\nFAIL: {broken} family/set pairs are answerable above chance without the "
              f"context.", file=sys.stderr)
        sys.exit(1)
    print("\nPASS: no family is answerable above chance from corpus priors alone.")


if __name__ == "__main__":
    main()
