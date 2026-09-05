"""Independent post-hoc verification of the WRITTEN artifacts.

Every other check in this repo runs INSIDE the builder, on in-memory objects.
This one re-reads what was actually written to disk and re-derives every answer
from scratch, so it catches a class of failure the build-time checks cannot:
serialization bugs, stale files, id drift, questions that reference a haystack
that no longer exists, candidate lists that do not match the haystack.

It shares no code path with the builder's ground truth: answers are recomputed
here with plain Python from the meta parquet, and compared byte-for-byte with the
strings in questions.jsonl.

Run before any release, and after any change to the builder:

    python scripts/verify_release.py
"""

import argparse
import collections
import json
import math
import sys
import unicodedata
from pathlib import Path

import polars as pl


def fold_tr(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def recompute(kind, meta, q, k, unit):
    """Recompute the answer from the parquet with an implementation that shares
    nothing with src/build_tr_oolong.py."""
    labels = meta["label"].to_list()
    ents = meta["entity"].to_list()
    halves = meta["half"].to_list()
    n = len(labels)
    lab = q.get("label")
    cand = q.get("candidates")

    if kind == "count":
        return str(labels.count(lab))
    if kind == "proportion":
        scale = 1000 if unit == "per_mille" else 100
        return str(math.floor(scale * labels.count(lab) / n + 0.5))
    if kind == "entity_count":
        return str(sum(1 for l, e in zip(labels, ents) if l == lab and e == q["entity"]))
    if kind == "shift":
        n0 = halves.count(0)
        n1 = n - n0
        s0 = sum(1 for l, h in zip(labels, halves) if h == 0 and l == lab) / max(1, n0)
        s1 = sum(1 for l, h in zip(labels, halves) if h == 1 and l == lab) / max(1, n1)
        return "rose" if s1 > s0 else "fell"
    if kind in ("most_common", "least_common", "second_most"):
        c = collections.Counter(labels)
        if cand:
            c = collections.Counter({l: v for l, v in c.items() if l in set(cand)})
        r = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        return {"most_common": r[0], "second_most": r[1], "least_common": r[-1]}[kind][0]
    if kind in ("entity_argmax", "top_k"):
        c = collections.Counter(e for l, e in zip(labels, ents)
                                if l == lab and e in set(cand or []))
        r = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        return r[0][0] if kind == "entity_argmax" else [e for e, _ in r[:k]]
    if kind == "pairwise":
        a = sum(1 for l, e in zip(labels, ents) if l == lab and e == q["entity_a"])
        b = sum(1 for l, e in zip(labels, ents) if l == lab and e == q["entity_b"])
        return q["entity_a"] if a > b else q["entity_b"]
    if kind == "label_vs_label":
        a = labels.count(q["label_a"])
        b = labels.count(q["label_b"])
        rel = abs(a - b) / max(a, b, 1)
        key = "same" if rel <= q.get("same_tol", 0.02) else ("more" if a > b else "less")
        return {"tr": {"more": "daha çok", "less": "daha az", "same": "eşit"},
                "en": {"more": "more common", "less": "less common",
                       "same": "the same"}}[q["language"]][key]
    raise ValueError(kind)


def verify(name: str) -> list[str]:
    d = Path(name)
    problems: list[str] = []

    def bad(msg):
        problems.append(f"{name}: {msg}")

    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    qs = [json.loads(l) for l in (d / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    hays = [json.loads(l) for l in (d / "haystacks.jsonl").read_text(encoding="utf-8").splitlines()]
    hay_by_id = {h["haystack_id"]: h for h in hays}
    metas = {f.name.split("meta_")[1][:-8]: pl.read_parquet(f) for f in d.glob("meta_*.parquet")}
    k = man.get("top_k_k", 3)
    unit = man["proportion_unit"]
    sep = man["config"]["separator"]
    lang = man["config"]["language"]

    # --- structural -------------------------------------------------------
    if man["questions_written"] != len(qs):
        bad(f"manifest says {man['questions_written']} questions, file has {len(qs)}")
    if len(man["haystacks"]) != len(hays):
        bad(f"manifest lists {len(man['haystacks'])} haystacks, file has {len(hays)}")
    ids = [q["id"] for q in qs]
    if len(set(ids)) != len(ids):
        bad(f"{len(ids) - len(set(ids))} duplicate question ids")
    stale = set(metas) - set(hay_by_id)
    if stale:
        bad(f"stale meta parquet(s) not referenced by haystacks.jsonl: {sorted(stale)}")
    missing = set(hay_by_id) - set(metas)
    if missing:
        bad(f"haystacks with no meta parquet: {sorted(missing)}")

    render_entity = bool(man["config"].get("render_entity", False))
    entity_render = man["config"].get("entity_render", "[[{entity}]] ")

    def render(text: str, entity) -> str:
        if not render_entity or entity in (None, "", "__none__"):
            return text
        return entity_render.format(entity=entity) + text

    label_space = set()
    for hid, h in hay_by_id.items():
        if hid not in metas:
            continue
        m = metas[hid]
        label_space |= set(m["label"].to_list())
        # the haystack string must be exactly the RENDERED meta rows joined by the
        # separator. v0.6.0: an entity-bearing set prints "[[brand]] " before each
        # record, so reconstructing from `text` alone no longer reproduces it.
        rows = [render(t, e) for t, e in zip(m["text"].to_list(), m["entity"].to_list())]
        rebuilt = sep.join(rows)
        if rebuilt != h["haystack"]:
            bad(f"{hid}: haystack text does not match its meta parquet")
        if m.height != h["n_examples"]:
            bad(f"{hid}: n_examples {h['n_examples']} != meta rows {m.height}")
        # char offsets must actually locate each record in the haystack
        cs, ce = m["char_start"].to_list(), m["char_end"].to_list()
        for i in (0, m.height // 2, m.height - 1):
            if h["haystack"][cs[i]:ce[i]] != rows[i]:
                bad(f"{hid}: char offsets wrong at row {i}")
                break

    if len(label_space) != man["label_space"]:
        bad(f"manifest label_space={man['label_space']}, haystacks contain {len(label_space)}")

    # --- grep-proofness, verified on the SHIPPED text ----------------------
    forms = set()
    for l in label_space:
        forms.add(fold_tr(l) if lang == "tr" else l.casefold())
        forms.add(fold_tr(l.replace("_", " ")) if lang == "tr" else l.replace("_", " ").casefold())
    for hid, h in hay_by_id.items():
        folded = fold_tr(h["haystack"]) if lang == "tr" else h["haystack"].casefold()
        hits = sorted(f for f in forms if f in folded)
        if hits:
            bad(f"{hid}: LABEL LEAKAGE in shipped text: {hits[:5]}")
            break

    # --- every answer recomputed independently ----------------------------
    checked = 0
    for q in qs:
        hid = q["haystack_id"]
        if hid not in metas:
            bad(f"{q['id']}: references unknown haystack {hid}")
            continue
        m = metas[hid]
        if cands := q.get("candidates"):
            present = set(m["label"].to_list()) | set(m["entity"].to_list())
            absent = [c for c in cands if c not in present]
            if absent:
                bad(f"{q['id']}: names candidates absent from the haystack: {absent}")
        try:
            got = recompute(q["kind"], m, q, k, unit)
        except Exception as e:
            bad(f"{q['id']}: recompute failed: {type(e).__name__}: {e}")
            continue
        if q["kind"] == "shift":                      # answers are language-mapped
            got = {"tr": {"rose": "arttı", "fell": "azaldı"}, "en": {"rose": "rose", "fell": "fell"}}[lang][got]
        want = q["answer"]
        if isinstance(want, list):
            if list(got) != list(want):
                bad(f"{q['id']}: answer {want} != recomputed {got}")
        elif str(got) != str(want):
            bad(f"{q['id']}: answer {want!r} != recomputed {got!r}")
        checked += 1
    return problems + [f"{name}: __checked__ {checked} answers, {len(hays)} haystacks"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=None)
    args = ap.parse_args()
    sets = args.sets
    if not sets:
        sets = []
        for c in sorted(Path("configs").glob("*.json")):
            try:
                out = json.loads(c.read_text(encoding="utf-8")).get("out_dir")
            except json.JSONDecodeError:
                continue
            if out and Path(out, "questions.jsonl").exists():
                sets.append(out)
    if not sets:
        sys.exit("no built sets found")

    all_problems = []
    for s in sets:
        res = verify(s)
        note = [r for r in res if "__checked__" in r][0]
        probs = [r for r in res if "__checked__" not in r]
        all_problems += probs
        status = "OK " if not probs else f"{len(probs)} PROBLEM(S)"
        print(f"{status:>14}  {note.replace('__checked__ ', '')}")
        for p in probs[:10]:
            print(f"                 - {p}")
    print()
    if all_problems:
        print(f"FAIL: {len(all_problems)} problem(s) in the written artifacts", file=sys.stderr)
        sys.exit(1)
    print("PASS: every shipped answer independently recomputed and matched; no leakage "
          "in shipped text; no stale, missing or mismatched files.")


if __name__ == "__main__":
    main()
