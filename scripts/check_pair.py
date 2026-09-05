#!/usr/bin/env python3
"""Is this Turkish/English corpus pair usable as a TR-OOLONG matched twin?

    python scripts/check_pair.py configs/musteri_tr.json configs/marc_en.json

Answers one question -- CAN THIS PAIR BE BUILT? -- and, when the answer is no,
says which check failed and by how much. Run it BEFORE building anything.

Why a pair check exists at all. `--audit` in the builder screens ONE source: is
it big enough, balanced enough, does formatting give the label away. All of that
can pass on both halves separately and still leave a pair that cannot support a
cross-lingual claim, because what breaks the claim is the GAP between the halves,
not either half's level. A model that scores well on Turkish by measuring
sentence lengths, while having to actually read the English, produces a
"cross-lingual difference" that is an artifact of formatting.

The four criteria are D16, in the order they actually bind. The licence is a
veto: a closer match is not worth a corpus that cannot be redistributed.

Verdicts: COMPATIBLE / COMPATIBLE WITH CAVEATS / INCOMPATIBLE.
Exit code 0 for the first two, 1 for the third.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import build_tr_oolong as b     # noqa: E402  (load + clean + render, one definition)


# --- thresholds ------------------------------------------------------------
# Each is the value the shipping pairs actually meet, rounded outward. They are
# defaults, not laws: --strict tightens the caveat band into a failure.
LEN_RATIO_WARN = 2.5        # mean words per record, longer / shorter
LEN_RATIO_FAIL = 4.0        # a 4x mismatch changes what "one chunk" means
SPREAD_GAP_WARN = 0.8       # |spread_a - spread_b|, the format-shortcut gap
SPREAD_GAP_FAIL = 1.5
ENTROPY_GAP_WARN = 0.15     # |normalised entropy_a - entropy_b|
SPREAD_ABS_WARN = 2.0       # either half readable from length alone (D15)
KNOWN_LICENCES = {          # redistributable text
    "cc-by-4.0", "cc-by-sa-4.0", "apache-2.0", "mit", "cc0-1.0", "cc-by-3.0",
    "odc-by", "cc-by-sa-3.0", "bsd-3-clause",
}


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, str]] = []
        self.fail = 0
        self.warn = 0

    def add(self, check: str, verdict: str, detail: str, why: str = "") -> None:
        self.rows.append((check, verdict, detail, why))
        if verdict == "FAIL":
            self.fail += 1
        elif verdict == "WARN":
            self.warn += 1

    def render(self) -> None:
        w = max(len(r[0]) for r in self.rows) + 2
        print(f"\n{'check':<{w}}{'':8}{'measured'}")
        print("-" * (w + 58))
        for check, verdict, detail, why in self.rows:
            mark = {"PASS": "  ok  ", "WARN": " warn ", "FAIL": " FAIL "}[verdict]
            print(f"{check:<{w}}{mark}  {detail}")
            if why and verdict != "PASS":
                print(f"{'':<{w}}        -> {why}")


def load(cfg_path: str) -> tuple[b.Config, pl.DataFrame]:
    cfg = b.Config.load(cfg_path)
    df = b.clean(b.load_source(cfg), cfg)
    return cfg, df


def mean_tokens(cfg: b.Config, df: pl.DataFrame) -> float:
    """Tokens per record under the set's OWN reference tokenizer. A words->tokens
    constant is not usable here: the same 12.9-word Turkish record costs ~2.9
    tokens/word under Qwen3-8B and an English one ~1.3, so a fixed factor
    mis-sizes one half of every pair by 2x and invents tier failures."""
    counter = b.make_token_counter(cfg)
    sample = df.sample(min(df.height, 400), seed=0)["text"].to_list()
    body = sum(counter(t) for t in sample) / max(1, len(sample))
    return body + counter(cfg.separator)


def stats(cfg: b.Config, df: pl.DataFrame) -> dict:
    words = df.with_columns(
        pl.col("text").str.split(" ").list.len().alias("_w")
    )
    per_class = (words.group_by("label")
                      .agg(pl.col("_w").mean().alias("mw"))
                      .sort("mw", descending=True))
    mw = per_class["mw"].to_list()
    counts = Counter(df["label"].to_list())
    K = len(counts)
    tot = sum(counts.values())
    ent = 0.0
    if K > 1:
        ent = -sum((c / tot) * math.log2(c / tot) for c in counts.values()) / math.log2(K)
    ents = [e for e in df["entity"].to_list() if e not in (None, "", "__none__")]
    return {
        "rows": df.height,
        "K": K,
        "labels": sorted(counts),
        "counts": counts,
        "entropy": ent,
        "imbalance": max(counts.values()) / max(1, min(counts.values())),
        "mean_words": words["_w"].mean(),
        "mean_tokens": mean_tokens(cfg, df),
        "spread": (max(mw) / min(mw)) if mw and min(mw) > 0 else float("inf"),
        "smallest_class": min(counts.values()) if counts else 0,
        "has_entity": bool(ents),
        "n_entities": len(set(ents)),
        "licence": (cfg.__dict__.get("licence") or "").strip().lower(),
        "provenance": (cfg.__dict__.get("label_provenance") or "").strip().lower(),
        "tiers": list(cfg.haystack_target_tokens or []),
        "records": list(cfg.haystack_target_records or []),
    }


def check(a: dict, b_: dict, na: str, nb: str, strict: bool) -> Report:
    r = Report()

    # 1 -- label provenance. Not measurable from the data; it is the defect that
    # withdrew a whole pair in v0.5.0, so it must be DECLARED or the pair fails.
    pa, pb = a["provenance"], b_["provenance"]
    if not pa or not pb:
        missing = [n for n, p in ((na, pa), (nb, pb)) if not p]
        r.add("label provenance", "FAIL", f"undeclared for {', '.join(missing)}",
              'add "label_provenance" to the config (e.g. "author_stars", '
              '"professional_annotation", "crowd"). An undocumented label is the '
              "one defect filtering cannot fix.")
    elif pa != pb:
        r.add("label provenance", "FAIL", f"{pa} vs {pb}",
              "the halves' labels are produced differently, so a score gap between "
              "them is not attributable to language")
    else:
        r.add("label provenance", "PASS", f"both {pa}")

    # 2 -- label space
    if a["K"] != b_["K"]:
        r.add("label space", "FAIL", f"{a['K']} vs {b_['K']} classes",
              "a twin whose halves have different label spaces cannot share a question")
    else:
        r.add("label space", "PASS", f"both {a['K']} classes")

    # 3 -- record length
    hi, lo = max(a["mean_words"], b_["mean_words"]), min(a["mean_words"], b_["mean_words"])
    ratio = hi / max(lo, 1e-9)
    detail = f"{a['mean_words']:.1f} vs {b_['mean_words']:.1f} words ({ratio:.1f}x)"
    if ratio >= LEN_RATIO_FAIL:
        r.add("record length", "FAIL", detail,
              f"{ratio:.1f}x changes what 'one chunk' means and contaminates every "
              "compression measurement")
    elif ratio >= LEN_RATIO_WARN:
        r.add("record length", "FAIL" if strict else "WARN", detail,
              "usable, but state it as a limitation")
    else:
        r.add("record length", "PASS", detail)

    # 4 -- surface shape. The GAP is the number that bears on the claim (D15).
    gap = abs(a["spread"] - b_["spread"])
    detail = f"spread {a['spread']:.2f}x vs {b_['spread']:.2f}x  (gap {gap:.2f})"
    if gap >= SPREAD_GAP_FAIL:
        r.add("surface-shape gap", "FAIL", detail,
              "an asymmetric length-label correlation lets a model score on one half "
              "without reading it -- this is what breaks the cross-lingual claim")
    elif gap >= SPREAD_GAP_WARN:
        r.add("surface-shape gap", "FAIL" if strict else "WARN", detail,
              "confirm with scripts/style_solver.py AFTER building: source-level "
              "numbers do not predict question-level exploitability")
    else:
        r.add("surface-shape gap", "PASS", detail)

    for n, s in ((na, a), (nb, b_)):
        if s["spread"] >= SPREAD_ABS_WARN:
            r.add(f"  {n} length spread", "WARN", f"{s['spread']:.2f}x",
                  "the label is partly readable from record length alone")

    # 5 -- class balance
    egap = abs(a["entropy"] - b_["entropy"])
    detail = (f"entropy {a['entropy']:.3f} vs {b_['entropy']:.3f} (gap {egap:.3f}); "
              f"imbalance {a['imbalance']:.1f}x / {b_['imbalance']:.1f}x")
    r.add("class balance", "WARN" if egap >= ENTROPY_GAP_WARN else "PASS", detail,
          "cap the larger classes so both halves are comparably balanced"
          if egap >= ENTROPY_GAP_WARN else "")

    # 6 -- reachable length tiers. R_max = smallest_class * K bounds the records a
    # ranking question can still be well-posed over.
    for n, s in ((na, a), (nb, b_)):
        # R_max = smallest_class * K is the RANKING-feasibility ceiling: past it a
        # class can no longer top the ranking, so most_common/least_common start
        # starving. The build still succeeds, which is why the builder itself only
        # warns (above 0.85x). Treat it the same way -- flagging it as a failure
        # rejects tr_intent, which ships.
        rmax = s["smallest_class"] * s["K"]
        need = (max(s["tiers"]) / max(s["mean_tokens"], 1)) if s["tiers"] else 0
        ratio = need / max(rmax, 1)
        if not s["tiers"] or ratio <= 0.85:
            v, why = "PASS", ""
        elif ratio <= 1.0:
            v, why = "WARN", "close to the ranking ceiling; expect some ranking draws to be rejected"
        else:
            v, why = ("FAIL" if strict else "WARN"), \
                ("past the ranking ceiling: the ranking families will starve at the top "
                 "tier. Lower it, raise min_class_support to drop the tail, or accept "
                 "fewer ranking questions there.")
        r.add(f"  {n} reaches its tiers", v,
              f"R_max={rmax:,} records, longest tier needs ~{need:,.0f} ({ratio:.2f}x)",
              why)

    # 7 -- entity axis must be present or absent on BOTH halves
    if a["has_entity"] != b_["has_entity"]:
        have = na if a["has_entity"] else nb
        r.add("entity axis", "WARN",
              f"only {have} has one ({a['n_entities']} vs {b_['n_entities']})",
              "the halves would emit different question families; either drop the "
              "entity families or find a twin that also has one")
    elif a["has_entity"]:
        r.add("entity axis", "PASS",
              f"both ({a['n_entities']:,} vs {b_['n_entities']:,} entities)")
    else:
        r.add("entity axis", "PASS", "neither -- 6 symmetric families")

    # 8 -- licence veto
    for n, s in ((na, a), (nb, b_)):
        lic = s["licence"]
        if not lic:
            r.add(f"  {n} licence", "FAIL", "undeclared",
                  'add "licence" to the config; silence upstream is not permission')
        elif lic in ("unknown", "none", "license:unknown"):
            r.add(f"  {n} licence", "FAIL" if strict else "WARN", lic,
                  "no known grant, so the TEXT cannot be redistributed. The pair is "
                  "still buildable and shippable: publish questions and answers, "
                  "withhold the text, and have users rebuild locally from the "
                  "fetch script (this is how amazon_hpc_en ships).")
        elif lic not in KNOWN_LICENCES:
            r.add(f"  {n} licence", "WARN", lic,
                  "not a recognised redistributable licence; verify by hand and "
                  "consider shipping questions without text")
        else:
            note = " (share-alike is contagious: ship one config per source)" \
                if "sa" in lic.split("-") else ""
            r.add(f"  {n} licence", "PASS", lic + note)
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config_a")
    ap.add_argument("config_b")
    ap.add_argument("--strict", action="store_true",
                    help="treat every caveat as a failure")
    ap.add_argument("--json", help="write the report here")
    args = ap.parse_args()

    cfg_a, df_a = load(args.config_a)
    cfg_b, df_b = load(args.config_b)
    na, nb = Path(args.config_a).stem, Path(args.config_b).stem
    a, b_ = stats(cfg_a, df_a), stats(cfg_b, df_b)

    print(f"PAIR: {na} ({cfg_a.language}, {a['rows']:,} rows) "
          f"<-> {nb} ({cfg_b.language}, {b_['rows']:,} rows)")
    rep = check(a, b_, na, nb, args.strict)
    rep.render()

    if rep.fail:
        verdict, code = "INCOMPATIBLE", 1
        tail = (f"{rep.fail} check(s) failed. Fix them or pick another twin -- a pair "
                "that fails here cannot support a cross-lingual claim.")
    elif rep.warn:
        verdict, code = "COMPATIBLE WITH CAVEATS", 0
        tail = (f"{rep.warn} caveat(s). Buildable; state each one as a limitation, and "
                "re-check with style_solver.py and quality_audit.py after building.")
    else:
        verdict, code = "COMPATIBLE", 0
        tail = "Build both halves, then run the four gates before trusting any number."

    print(f"\n=== {verdict} ===\n{tail}")
    print("\nNOTE: this screens the SOURCES. Only the post-build gates "
          "(trivial_baseline, quality_audit, style_solver, verify_release) can\n"
          "      certify the questions -- source-level numbers have already been "
          "shown not to predict question-level exploitability.")

    if args.json:
        Path(args.json).write_text(json.dumps({
            "pair": [na, nb], "verdict": verdict,
            "failures": rep.fail, "caveats": rep.warn,
            "checks": [{"check": c, "verdict": v, "measured": d, "why": w}
                       for c, v, d, w in rep.rows],
            "stats": {na: {k: v for k, v in a.items() if k != "counts"},
                      nb: {k: v for k, v in b_.items() if k != "counts"}},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nreport -> {args.json}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
