"""Independent logic audit of the 11 released subsets (local *_out dirs).
Checks things verify_release.py does not: source fidelity of labels, conflicting
duplicate texts, ties/knife-edges, question-text consistency, twin alignment."""
import collections, glob, json, math, re, sys
from pathlib import Path
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
SETS = ["amazon_hpc_en", "en_intent", "en_intent_paired", "interpress_tr", "marc_en",
        "musteri_tr", "sikayet_tr", "sinema_tr", "tr_intent", "tr_intent_paired", "vitamins_tr"]
out = collections.defaultdict(list)

def norm(s): return re.sub(r"\s+", " ", s).strip().casefold()

for name in SETS:
    d = ROOT / f"{name}_out"
    man = json.loads((d / "manifest.json").read_text())
    cfg = man["config"]
    qs = [json.loads(l) for l in open(d / "questions.jsonl")]
    metas = {f.name[5:-8]: pl.read_parquet(f) for f in d.glob("meta_*.parquet")}
    P = out[name]

    # --- A. source fidelity: does each (text,label) exist in the source? -------
    src = pl.read_parquet(ROOT / cfg["source_path"])
    tcol, lcol = cfg["text_col"], cfg["label_col"]
    tr = cfg.get("label_translation") or {}
    src_lab = collections.defaultdict(set)
    for t, l in zip(src[tcol].to_list(), src[lcol].to_list()):
        if t is None: continue
        src_lab[norm(t)].add(tr.get(str(l), str(l)))
    nomatch = mismatch = conflict_src = rows = 0
    mism_ex = []
    for hid, m in metas.items():
        for t, l in zip(m["text"].to_list(), m["label"].to_list()):
            rows += 1
            labs = src_lab.get(norm(t))
            if labs is None: nomatch += 1; continue
            if l not in labs:
                mismatch += 1
                if len(mism_ex) < 3: mism_ex.append((t[:80], l, labs))
            elif len(labs) > 1: conflict_src += 1
    P.append(f"A source: {rows} rows, {nomatch} text not found verbatim in source (cleaned text?), "
             f"{mismatch} label NOT among source labels {mism_ex}, "
             f"{conflict_src} rows whose text has >1 label in source")

    # --- B. duplicates inside one haystack ------------------------------------
    dup_same = dup_conf = 0; conf_ex = []
    for hid, m in metas.items():
        g = collections.defaultdict(list)
        for t, l in zip(m["text"].to_list(), m["label"].to_list()): g[norm(t)].append(l)
        for t, ls in g.items():
            if len(ls) > 1:
                if len(set(ls)) > 1:
                    dup_conf += len(ls)
                    if len(conf_ex) < 4: conf_ex.append((hid, t[:60], collections.Counter(ls)))
                else: dup_same += len(ls) - 1
    P.append(f"B dup texts in a haystack: {dup_same} extra identical copies; "
             f"{dup_conf} records in same-text-different-label groups {conf_ex}")

    # --- C. per-question logic -------------------------------------------------
    issues = collections.Counter(); ex = collections.defaultdict(list)
    def flag(k, q, info=""):
        issues[k] += 1
        if len(ex[k]) < 3: ex[k].append(f"{q['id']} {info}")
    for q in qs:
        m = metas[q["haystack_id"]]
        c = collections.Counter(m["label"].to_list()); n = m.height
        text = q["question"]; k = q["kind"]
        # every named label/candidate appears in the question text in quotes
        named = [x for x in [q.get("label"), q.get("label_a"), q.get("label_b")] if x] + (q.get("candidates") or [])
        for x in set(named):
            if f"'{x}'" not in text: flag("label not quoted in question", q, x)
        if k in ("most_common", "least_common", "second_most"):
            cand = q["candidates"]
            r = sorted(((l, c[l]) for l in cand), key=lambda kv: -kv[1])
            missing = set(c) - set(cand)
            if missing: flag("ranking: haystack labels missing from candidate list", q, f"{len(missing)} missing")
            i = {"most_common": 0, "second_most": 1, "least_common": len(r) - 1}[k]
            nb = [j for j in (i - 1, i + 1) if 0 <= j < len(r)]
            gap = min(abs(r[i][1] - r[j][1]) for j in nb)
            if gap == 0: flag("ranking TIE", q, str(r[max(0,i-1):i+2]))
            elif gap <= 2: flag("ranking gap <=2 records", q, str(r[max(0,i-1):i+2]))
            if r[i][0] != q["answer"]: flag("ranking answer wrong", q)
        if k == "label_vs_label":
            a, b = c[q["label_a"]], c[q["label_b"]]
            if q["answer_key"] == "same":
                flag("lvl 'same' answer", q, f"{a} vs {b}")
                if a != b: flag("lvl 'same' but counts differ", q, f"{a} vs {b}")
        if k == "close_comparison":
            a, b = c[q["label_a"]], c[q["label_b"]]
            if a == b: flag("close TIE", q, f"{a}={b}")
            if min(a, b) < 30 or min(a, b) < 0.02 * n: flag("close below size floor", q, f"{a},{b},n={n}")
            if abs(a - b) < 5 and q.get("core_document"): flag("core doc gap <5", q, f"{a},{b}")
            if "neutral" in (q["label_a"], q["label_b"]) or "nötr" in (q["label_a"], q["label_b"]):
                flag("close uses neutral", q)
            if q["answer"] not in (q["label_a"], q["label_b"]): flag("close answer not an option", q)
        if k == "count":
            if int(q["answer"]) == 0: flag("count answer 0", q)
            if q["role"] == "retrieval" and not (5 <= int(q["answer"]) <= 30): flag("retrieval outside 5-30", q, q["answer"])
            if q["label"] not in c: flag("count label absent from haystack", q)
        if k == "proportion":
            scale = 1000 if q.get("unit") == "per_mille" else 100
            x = scale * c[q["label"]] / n
            if abs(x - math.floor(x) - 0.5) < 0.02: flag("proportion within 0.02 of .5 rounding edge", q, f"{x:.3f}")
            unit_word = {"per_mille": ("binde", "per thousand", "per mille"), "percent": ("yüzde", "percentage", "percent")}[q.get("unit", "percent")]
            if not any(w in text.lower() for w in unit_word): flag("proportion unit not stated in question", q, q.get("unit"))
    # questions duplicated in the same haystack
    seen = collections.Counter((q["haystack_id"], q["kind"], q.get("label"), q.get("label_a"), q.get("label_b")) for q in qs)
    dups = sum(v - 1 for v in seen.values() if v > 1)
    if dups: issues["duplicate question in same haystack"] = dups
    P.append(f"C questions ({len(qs)}): " + (", ".join(f"{k}={v}" for k, v in issues.most_common()) or "clean"))
    for k, v in ex.items(): P.append(f"     ex[{k}]: {v}")

# --- D. paired twins: identical label sequences? -------------------------------
for a, b in [("tr_intent_paired", "en_intent_paired")]:
    da, db = ROOT / f"{a}_out", ROOT / f"{b}_out"
    for fa in sorted(da.glob("meta_*.parquet")):
        hid = fa.name[5:-8]; hb = "en" + hid[2:]
        fb = db / f"meta_{hb}.parquet"
        if not fb.exists(): out["D twins"].append(f"{hid}: no twin {hb}"); continue
        A, B = pl.read_parquet(fa), pl.read_parquet(fb)
        if A["label"].to_list() != B["label"].to_list():
            same = sum(x == y for x, y in zip(A["label"].to_list(), B["label"].to_list()))
            out["D twins"].append(f"{hid}: label sequence differs ({same}/{A.height} positions agree; heights {A.height}/{B.height})")
    if not out["D twins"]: out["D twins"].append("all paired haystacks have identical label sequences")

for k, v in out.items():
    print(f"== {k}")
    for line in v: print("  ", line)
