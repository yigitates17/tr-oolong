#!/usr/bin/env python3
"""Is this ONE dataset usable as a TR-OOLONG source, on its own -- no partner
language required?

    python scripts/check_solo.py configs/new_tr_set.json
    python scripts/check_solo.py configs/new_tr_set.json --build

Why this exists, and why it is not check_pair.py. check_pair.py answers "CAN
THESE TWO HALVES BE COMPARED" -- record length, licence, label provenance,
surface-shape GAP between two configs. A contributor who wants to add a
Turkish (or any single-language) dataset with no English twin and no
cross-lingual claim does not have a second config to hand it, and forcing them
to invent a fake partner just to get a report is the wrong ask.

What actually needs a partner and what does not, precisely:
  - check_pair.py            -- NEEDS a partner (that is its whole subject).
  - build_tr_oolong --audit  -- already single-config. No twin involved.
  - trivial_baseline.py      -- already takes `--sets` (any number, any mix).
  - quality_audit.py         -- already takes `--sets`. Its ONE pair-aware
                                 step (verify_pairs, McNemar-readiness) simply
                                 finds nothing to check when there is no
                                 matching *_paired set, and says so.
  - style_solver.py          -- already takes `--config` (any number).

So three of the four acceptance gates were never twin-specific; nobody had
wired them into one contributor-facing report for the solo case. This script
is that thin front end: declared-metadata checks (licence, provenance) plus
the three per-set gates, rendered as one PASS/WARN/FAIL table in check_pair's
style, for exactly the criteria OOLONG-style aggregation requires: labels
exist and are documented, the corpus is big enough to reach a real long-context
tier, nothing shortcuts the aggregation (leakage / prior / format), and the
licence permits shipping the text.

Verdicts: SOLO OK / SOLO WITH CAVEATS / SOLO INCOMPATIBLE.
Exit code 0 for the first two, 1 for the third.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_tr_oolong as b        # noqa: E402
import check_pair as cp            # noqa: E402  (reuse Report + stats() -- one dataset's numbers)
import trivial_baseline as tb      # noqa: E402
import quality_audit as qa         # noqa: E402
import style_solver as ss          # noqa: E402

MIN_ROWS_FOR_LONG_CONTEXT = 5_000   # below this, no config can reach a 100K+ tier at all
FORMAT_LIFT_WARN = 0.08             # style_solver's own FAIL line is 0.15; warn earlier, solo

# Substrings that mean "a machine assigned this, not a person" when they show up
# in a declared provenance string. This is the exact defect that sank We-Bears
# (undocumented provenance, D#We-Bears) and winvoker (DATASET_REVIEW.md: rejected
# for "random text inputs marked as neutral" -- programmatic labelling, stated
# openly on its own dataset card). A regex over the declared VALUE cannot detect
# an UNDISCLOSED synthetic origin -- that is why "undeclared" is its own, harder
# failure below -- but it catches the case where someone declares it honestly and
# the check should still make them look twice.
SYNTHETIC_PROVENANCE_HINTS = ("synthetic", "generated", "llm", "gpt", "machine-label",
                              "machine_label", "auto-label", "auto_label", "programmatic")
KNOWN_TEXT_PROVENANCE = {"human_written", "human_translated", "machine_translated",
                         "synthetic_generated"}


def declared_metadata(s: dict, name: str, r: cp.Report) -> None:
    prov = s["provenance"]
    if not prov:
        r.add("label provenance", "FAIL", "undeclared",
              'add "label_provenance" to the config -- undocumented provenance is the '
              "one defect filtering cannot fix (see DESIGN_DECISIONS.md D#We-Bears)")
    elif any(h in prov for h in SYNTHETIC_PROVENANCE_HINTS):
        r.add("label provenance", "WARN", prov,
              "declared as machine/programmatic labelling -- this is exactly why "
              "winvoker/turkish-sentiment was rejected (DATASET_REVIEW.md: its own card "
              "states 'random text inputs marked as neutral'). The benchmark then measures "
              "agreement with the labelling process, not ground truth. Needs a human "
              "sign-off, not just a declaration, before this ships as an answer key.")
    else:
        r.add("label provenance", "PASS", prov)

    tprov = s["text_provenance"]
    if not tprov:
        r.add("text provenance", "WARN", "undeclared",
              'add "text_provenance" to the config: "human_written" | "human_translated" | '
              '"machine_translated" | "synthetic_generated". Undeclared does not mean '
              "human-written -- state it rather than leaving it implicit.")
    elif tprov == "synthetic_generated":
        r.add("text provenance", "FAIL", tprov,
              "AI-generated text measures the generator, not the language -- it would "
              "destroy the cross-lingual claim this benchmark exists to make (README: "
              "'real vs synthetic data'). A synthetic CONTROL experiment is legitimate; "
              "shipping synthetic text as the corpus itself is not.")
    elif tprov == "machine_translated":
        r.add("text provenance", "WARN", tprov,
              "machine-translated text risks idiom/meaning loss under a word-by-word "
              "translation (PAPER_NOTES.md 5b: 'put a record on' -> 'bir kayıt koy' lost "
              "its meaning entirely, and it landed asymmetrically on one side of a twin). "
              "If this pairs with another language, check whether the error is symmetric.")
    elif tprov == "human_translated":
        r.add("text provenance", "WARN", tprov,
              "human translation is far safer than machine translation but is not immune "
              "(PAPER_NOTES.md 5b measured 9.3% label noise on MASSIVE, some of it exactly "
              "this kind of idiom loss, despite human translators). Still real text; note "
              "it as a lesser version of the same limitation.")
    elif tprov not in KNOWN_TEXT_PROVENANCE:
        r.add("text provenance", "WARN", tprov,
              f"not one of the recognised values ({', '.join(sorted(KNOWN_TEXT_PROVENANCE))}); "
              "verify by hand what this actually means")
    else:
        r.add("text provenance", "PASS", tprov)

    lic = s["licence"]
    if not lic:
        r.add("licence", "FAIL", "undeclared",
              'add "licence" to the config; silence upstream is not permission')
    elif lic in ("unknown", "none", "license:unknown"):
        r.add("licence", "WARN", lic,
              "no known grant, so the TEXT cannot be redistributed. Still buildable and "
              "shippable: publish questions and answers, withhold the text, ship a fetch "
              "script (this is how amazon_hpc_en ships).")
    elif lic not in cp.KNOWN_LICENCES:
        r.add("licence", "WARN", lic, "not a recognised redistributable licence; verify by hand")
    else:
        note = " (share-alike: this cannot be merged flat into another licence's release)" \
            if "sa" in lic.split("-") else ""
        r.add("licence", "PASS", lic + note)


def source_shape(s: dict, name: str, r: cp.Report) -> None:
    if s["K"] < 2:
        r.add("label space", "FAIL", f"{s['K']} class(es)",
              "there is nothing to aggregate over with fewer than 2 labels")
    else:
        r.add("label space", "PASS", f"{s['K']} classes, {s['rows']:,} rows")

    if s["rows"] < MIN_ROWS_FOR_LONG_CONTEXT:
        r.add("corpus size", "WARN", f"{s['rows']:,} rows",
              f"under {MIN_ROWS_FOR_LONG_CONTEXT:,} rows rarely reaches a real long-context "
              "tier without heavy resampling; expect only short tiers to build cleanly")
    else:
        r.add("corpus size", "PASS", f"{s['rows']:,} rows")

    if s["spread"] >= cp.SPREAD_ABS_WARN:
        r.add("length spread", "WARN", f"{s['spread']:.2f}x",
              "the label is partly readable from record length alone (D15) -- "
              "confirm with style_solver.py after building")
    else:
        r.add("length spread", "PASS", f"{s['spread']:.2f}x")

    for n, s_tiers in ((name, s),):
        rmax = s_tiers["smallest_class"] * s_tiers["K"]
        tiers = s_tiers["tiers"] or s_tiers["records"]
        if not tiers:
            continue
        need = (max(tiers) / max(s_tiers["mean_tokens"], 1)) if s_tiers["tiers"] else max(tiers)
        ratio = need / max(rmax, 1)
        if ratio <= 0.85:
            v, why = "PASS", ""
        elif ratio <= 1.0:
            v, why = "WARN", "close to the ranking ceiling (D6); expect some ranking draws rejected"
        else:
            v, why = "WARN", ("past the ranking ceiling: most_common/least_common will starve "
                               "at the top tier. Lower it, raise min_class_support, or accept "
                               "fewer ranking questions there.")
        r.add("reaches its configured tiers", v,
              f"R_max={rmax:,} records, longest tier needs ~{need:,.0f} ({ratio:.2f}x)", why)

    if s["has_entity"]:
        r.add("entity axis", "PASS", f"{s['n_entities']:,} entities -- entity_count/"
              "entity_argmax/pairwise become available")
    else:
        r.add("entity axis", "PASS", "none -- ships the 7 label-only families")


def built_gates(cfg_path: str, out_dir: str, r: cp.Report) -> None:
    qdir = Path(out_dir)
    if not (qdir / "questions.jsonl").exists():
        r.add("trivial_baseline (leakage/majority)", "WARN", "not built",
              f"run `python src/build_tr_oolong.py --config {cfg_path} --build`, "
              "or pass --build to this script, then re-run to get the three post-build gates")
        r.add("quality_audit (prior-oracle shortcut)", "WARN", "not built", "")
        r.add("style_solver (format shortcut)", "WARN", "not built", "")
        return

    base = tb.run_set(qdir)
    bad, degenerate = [], []
    for kind, f in base["families"].items():
        floor = max(f["majority_baseline"], f["chance_floor"])
        if f["exact"] > floor + 0.05:
            bad.append(f"{kind} (leak {f['exact']:.2f} > floor {floor:.2f})")
        elif f["degenerate"]:
            degenerate.append(kind)
    if bad:
        r.add("trivial_baseline (leakage/majority)", "FAIL", "; ".join(bad),
              "a substring/majority solver beats the floor -- the question is answerable "
              "without reading the context")
    elif degenerate:
        r.add("trivial_baseline (leakage/majority)", "WARN",
              f"degenerate (majority>=0.9): {', '.join(degenerate)}",
              "one gold answer dominates >=9/10 haystacks -- raise min_class_support or "
              "widen the label space (D3)")
    else:
        r.add("trivial_baseline (leakage/majority)", "PASS",
              f"{base['n_questions']} questions, no family above its floor")

    audit = qa.audit_set(qdir.name, cfg_path, depth_min=10, margin_min=None)
    shortcut = [k for k, f in audit["families"].items() if f["prior_shortcut"] and f["n"] >= 30]
    watch = [k for k, f in audit["families"].items() if f["prior_shortcut"] and f["n"] < 30]
    if shortcut:
        r.add("quality_audit (prior-oracle shortcut)", "FAIL", ", ".join(shortcut),
              "answerable above chance from corpus statistics alone, never reading the "
              "haystack -- rerun the generator with --certify 200+ to confirm at power")
    elif watch:
        r.add("quality_audit (prior-oracle shortcut)", "WARN",
              f"underpowered at shipped n, watch: {', '.join(watch)}",
              "rerun `quality_audit.py --certify 200` before trusting this family")
    else:
        r.add("quality_audit (prior-oracle shortcut)", "PASS",
              f"{audit['pct_ok']}% of {audit['n_questions']} questions clear depth+margin")

    baselines = {}
    br = Path("manifests/baseline_report.json")
    if br.exists():
        for entry in json.loads(br.read_text()):
            baselines[entry["set"]] = entry["families"]
    baselines[qdir.name] = base["families"]     # the run above, in case this set isn't committed yet
    style = ss.run_set(cfg_path, baselines)
    lift = style["mean_lift"] if style else None
    if lift is None:
        r.add("style_solver (format shortcut)", "WARN", "solver ran but no family had a "
              "usable majority baseline to compare against", "")
    elif lift > 0.15:
        r.add("style_solver (format shortcut)", "FAIL", f"mean lift {lift:+.3f}",
              "length/punctuation alone recovers the label well beyond the majority "
              "baseline (D15) -- this is not a reading-comprehension task")
    elif lift > FORMAT_LIFT_WARN:
        r.add("style_solver (format shortcut)", "WARN", f"mean lift {lift:+.3f}",
              "some format signal present; note it, and if a twin exists later check "
              "the GAP between the two halves, not this number alone")
    else:
        r.add("style_solver (format shortcut)", "PASS", f"mean lift {lift:+.3f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("--build", action="store_true",
                    help="build this config first, then run the post-build gates")
    ap.add_argument("--json", help="write the report here")
    args = ap.parse_args()

    if args.build:
        subprocess.run([sys.executable, str(ROOT / "src" / "build_tr_oolong.py"),
                        "--config", args.config, "--build"], check=True)

    cfg = b.Config.load(args.config)
    name = Path(args.config).stem
    r = cp.Report()

    try:
        df = b.clean(b.load_source(cfg), cfg)
    except b.MissingColumnError as e:
        print(f"SOLO CHECK: {name} ({cfg.language}, out_dir={cfg.out_dir})")
        r.add("source has the declared columns", "FAIL", str(e))
        r.render()
        print("\n=== SOLO INCOMPATIBLE ===\nCannot even load the source -- fix the config "
              "or confirm the source genuinely has no labels (see ROADMAP.md check #1).")
        return 1

    s = cp.stats(cfg, df)

    print(f"SOLO CHECK: {name} ({cfg.language}, {s['rows']:,} rows, out_dir={cfg.out_dir})")
    declared_metadata(s, name, r)
    source_shape(s, name, r)
    built_gates(args.config, cfg.out_dir, r)
    r.render()

    if r.fail:
        verdict, code = "SOLO INCOMPATIBLE", 1
        tail = f"{r.fail} check(s) failed -- fix them before this ships as an OOLONG-style source."
    elif r.warn:
        verdict, code = "SOLO WITH CAVEATS", 0
        tail = f"{r.warn} caveat(s). Usable; state each one as a limitation."
    else:
        verdict, code = "SOLO OK", 0
        tail = "All checks pass in isolation."

    print(f"\n=== {verdict} ===\n{tail}")
    print("\nNOTE: this certifies the dataset ON ITS OWN. Adding it as a matched twin to "
          "an existing language (or to another contribution) is a SEPARATE question -- "
          "run scripts/check_pair.py against the partner config before building that pair.")

    if args.json:
        Path(args.json).write_text(json.dumps({
            "config": name, "verdict": verdict, "failures": r.fail, "caveats": r.warn,
            "checks": [{"check": c, "verdict": v, "measured": d, "why": w}
                       for c, v, d, w in r.rows],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nreport -> {args.json}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
