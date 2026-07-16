"""Shortcut-floor baseline: answers every question using ONLY surface label-token
leakage (no classification, no model). A record 'has' label L if the label
string (underscores as spaces) appears in its text. Reported per-family scores
are the floor a real solver must beat; the TR-vs-EN gap in this floor is the
label-leakage asymmetry claimed in README section 4.

Implementation note: per-record label and entity hits are precomputed once per
haystack as int bitmasks, so entity ranking over thousands of brands is a
bitwise AND + popcount instead of repeated substring scans.

Usage:
    python scripts/trivial_baseline.py --sets tr_intent_out en_intent_out ...
"""

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl

from build_tr_oolong import SHIFT_ANSWER, tr_casefold
from scoring import score


def fold(s: str, language: str) -> str:
    return tr_casefold(s) if language == "tr" else s.casefold()


def leak_tokens(label: str, language: str) -> set[str]:
    return {fold(label, language), fold(label.replace("_", " "), language)}


def vocab_from_set(d: Path, questions: list[dict]) -> tuple[list[str], list[str]]:
    """Label and entity vocabularies. Prefer the meta parquets (exact); fall
    back to what the questions mention."""
    labels, entities = set(), set()
    metas = sorted(d.glob("meta_*.parquet"))
    if metas:
        for m in metas:
            df = pl.read_parquet(m, columns=["label", "entity"])
            labels.update(df["label"].to_list())
            entities.update(df["entity"].to_list())
    else:
        for q in questions:
            if q.get("label"):
                labels.add(q["label"])
            for key in ("entity", "entity_a", "entity_b"):
                if q.get(key):
                    entities.add(q[key])
            if q["kind"] in ("most_common", "least_common", "second_most"):
                labels.add(q["answer"])
            if q["kind"] == "top_k":
                entities.update(q["answer"])
    entities.discard("__none__")
    return sorted(labels), sorted(entities)


def bitmask(flags: list[bool]) -> int:
    m = 0
    for i, f in enumerate(flags):
        if f:
            m |= 1 << i
    return m


class Haystack:
    """Folded records plus precomputed hit bitmasks (bit i = record i)."""

    def __init__(self, text: str, sep: str, labels, entities, language: str):
        self.records = [fold(r, language) for r in text.split(sep)]
        self.n = len(self.records)
        self.lab = {}
        for l in labels:
            toks = leak_tokens(l, language)
            self.lab[l] = bitmask([any(t in r for t in toks) for r in self.records])
        self.ent = {}
        for e in entities:
            ef = fold(e, language)
            self.ent[e] = bitmask([ef in r for r in self.records])
        self.first_half = (1 << (self.n // 2)) - 1          # bits of records 0..n//2-1

    def count(self, label, entity=None):
        m = self.lab[label]
        if entity is not None:
            m &= self.ent[entity]
        return m.bit_count()


def answer(q, hs: Haystack, labels, entities, language):
    kind = q["kind"]
    if kind == "count":
        return str(hs.count(q["label"]))
    if kind == "proportion":
        scale = {"percent": 100, "per_mille": 1000}[q["unit"]]
        return str(math.floor(scale * hs.count(q["label"]) / max(1, hs.n) + 0.5))
    if kind == "entity_count":
        return str(hs.count(q["label"], q["entity"]))
    if kind in ("most_common", "least_common", "second_most"):
        ranked = sorted(labels, key=lambda l: (-hs.count(l), l))
        return {"most_common": ranked[0], "least_common": ranked[-1],
                "second_most": ranked[1] if len(ranked) > 1 else ranked[0]}[kind]
    if kind == "entity_argmax":
        return max(entities, key=lambda e: (hs.count(q["label"], e), e)) if entities else ""
    if kind == "top_k":
        ranked = sorted(entities, key=lambda e: (-hs.count(q["label"], e), e))
        return " > ".join(ranked[: q.get("k", 3)])
    if kind == "pairwise":
        a, b = hs.count(q["label"], q["entity_a"]), hs.count(q["label"], q["entity_b"])
        return q["entity_a"] if a >= b else q["entity_b"]
    if kind == "shift":
        m = hs.lab[q["label"]]
        h0 = hs.n // 2
        c0 = (m & hs.first_half).bit_count()
        c1 = m.bit_count() - c0
        s0 = c0 / max(1, h0)
        s1 = c1 / max(1, hs.n - h0)
        return SHIFT_ANSWER[language]["rose" if s1 > s0 else "fell"]
    raise ValueError(kind)


CHANCE = {"shift": 0.5, "pairwise": 0.5}


def run_set(d: Path) -> dict:
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    sep = man["config"]["separator"]
    questions = [json.loads(l) for l in (d / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    labels, entities = vocab_from_set(d, questions)
    haystacks = {}
    for line in (d / "haystacks.jsonl").read_text(encoding="utf-8").splitlines():
        h = json.loads(line)
        haystacks[h["haystack_id"]] = Haystack(h["haystack"], sep, labels, entities, h["language"])

    ex, pa = defaultdict(list), defaultdict(list)
    for q in questions:
        pred = answer(q, haystacks[q["haystack_id"]], labels, entities, q["language"])
        s = score(q, pred)
        ex[q["kind"]].append(s["exact"])
        pa[q["kind"]].append(s["partial"])

    fam = {}
    for k in sorted(ex):
        chance = CHANCE.get(k, 1 / len(labels) if k in ("most_common", "least_common", "second_most") else 0.0)
        fam[k] = {"n": len(ex[k]), "exact": sum(ex[k]) / len(ex[k]),
                  "partial": sum(pa[k]) / len(pa[k]), "chance_floor": round(chance, 3)}
    all_ex = [v for vs in ex.values() for v in vs]
    all_pa = [v for vs in pa.values() for v in vs]
    return {"set": d.name, "n_questions": len(all_ex),
            "exact": sum(all_ex) / len(all_ex), "partial": sum(all_pa) / len(all_pa),
            "families": fam}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True, help="built set directories")
    ap.add_argument("--out", default="baseline_report.json")
    args = ap.parse_args()
    report = []
    for dname in args.sets:
        r = run_set(Path(dname))
        report.append(r)
        print(f"\n== {r['set']}  ({r['n_questions']} q)  "
              f"exact={r['exact']:.3f}  partial={r['partial']:.3f}")
        for k, v in r["families"].items():
            print(f"   {k:<14} n={v['n']:<4} exact={v['exact']:.3f} "
                  f"partial={v['partial']:.3f} chance={v['chance_floor']}")
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nreport -> {args.out}")


if __name__ == "__main__":
    main()