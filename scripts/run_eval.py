"""Direct-model evaluation harness for TR-OOLONG.

Feeds haystack + question to any OpenAI-compatible /v1/chat/completions
endpoint and scores predictions with the FROZEN metric in src/scoring.py.
  Ollama:  --base-url http://localhost:11434/v1
  vLLM:    --base-url http://localhost:8000/v1
Resumable: predictions append to <set>/predictions_<model>.jsonl; answered
questions are skipped on rerun, keyed on `uid` so that pooling several subsets'
predictions into one table cannot collapse rows (D22). Errors and timeouts are recorded as
error rows, excluded from scores, and reported as a separate count.

Usage:
    python scripts/run_eval.py --sets tr_intent_out --model qwen3:8b
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scoring import score

PROMPT = {
    "tr": ("Aşağıda '{sep}' ile ayrılmış kayıtlar var. Tüm kayıtları oku ve "
           "soruyu yanıtla. Sadece istenen yanıtı yaz, açıklama ekleme.\n\n"
           "{haystack}\n\nSoru: {question}\nYanıt:"),
    "en": ("Below are records separated by '{sep}'. Read all records and "
           "answer the question. Write only the requested answer, no explanation.\n\n"
           "{haystack}\n\nQuestion: {question}\nAnswer:"),
}


def chat(base_url, api_key, model, prompt, max_tokens, timeout):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions",
                                 data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"].strip(), data.get("usage") or {}


def run_set(d: Path, args) -> dict:
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    sep = man["config"]["separator"]
    questions = [json.loads(l) for l in (d / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    haystacks = {}
    for line in (d / "haystacks.jsonl").read_text(encoding="utf-8").splitlines():
        h = json.loads(line)
        haystacks[h["haystack_id"]] = h["haystack"]

    # the difficulty grade per question, if it has been computed for this set.
    # Without it only a pooled score can be reported, and a pooled score over a
    # question set that is 71.8% easy mostly measures whether the model reads
    # Turkish (W4 decision 4). The bands are the point of reporting at all.
    grade = {}
    dpath = d / "difficulty.jsonl"
    if dpath.exists():
        for line in dpath.read_text(encoding="utf-8").splitlines():
            g = json.loads(line)
            grade[g.get("uid") or g["id"]] = g["difficulty"]

    safe_model = re.sub(r"[^\w.-]", "_", args.model)
    pred_path = d / f"predictions_{safe_model}.jsonl"
    done = set()
    if pred_path.exists():
        for line in pred_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            # errored rows are NOT done: a transient timeout would otherwise
            # drop that question permanently from every later resumed run
            if "error" not in row:
                # key on uid, not id: `id` repeats across subsets, so a pooled
                # predictions table keyed on it silently collapses rows (D22).
                # Fall back to id for prediction files written before v0.7.1.
                done.add(row.get("uid") or row["id"])

    if args.max_questions:
        questions = questions[: args.max_questions]

    n_err = 0
    with pred_path.open("a", encoding="utf-8") as f:
        for q in questions:
            if q["uid"] in done:
                continue
            prompt = PROMPT[q["language"]].format(
                sep=sep.strip(), haystack=haystacks[q["haystack_id"]], question=q["question"])
            t0 = time.time()
            row = {"uid": q["uid"], "dataset": q["dataset"], "id": q["id"],
                   "model": args.model}
            try:
                pred, usage = chat(args.base_url, args.api_key, args.model,
                                   prompt, args.max_tokens, args.timeout)
                row.update(prediction=pred, usage=usage, **score(q, pred))
            except Exception as e:
                row["error"] = f"{type(e).__name__}: {e}"
                n_err += 1
            row["seconds"] = round(time.time() - t0, 2)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            tag = "ERR " if "error" in row else f"e={row['exact']:.0f} "
            print(f"  {q['id']:<20} {tag}{row['seconds']:>7.1f}s")

    # score everything answered so far (this run + previous resumed runs)
    preds = {}
    for line in pred_path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        preds[r.get("uid") or r["id"]] = r
    ex, pa, rl = defaultdict(list), defaultdict(list), defaultdict(list)
    band_rl, band_ex = defaultdict(list), defaultdict(list)
    errors = 0
    for q in questions:
        r = preds.get(q["uid"]) or preds.get(q["id"])
        if r is None:
            continue
        if "error" in r:
            errors += 1
            continue
        ex[q["kind"]].append(r["exact"])
        pa[q["kind"]].append(r["partial"])
        rl[q["kind"]].append(r.get("relative", r["exact"]))
        g = grade.get(q["uid"])
        if g:
            band_rl[g].append(r.get("relative", r["exact"]))
            band_ex[g].append(r["exact"])
    fam = {k: {"n": len(v), "exact": sum(v) / len(v),
               "partial": sum(pa[k]) / len(pa[k]), "relative": sum(rl[k]) / len(rl[k])}
           for k, v in sorted(ex.items())}
    all_ex = [v for vs in ex.values() for v in vs]
    n = max(1, len(all_ex))
    bands = {b: {"n": len(v), "relative": sum(v) / len(v),
                 "exact": sum(band_ex[b]) / len(band_ex[b])}
             for b, v in band_rl.items() if v}
    # The headline number. A model high on `easy` and low on `very hard` is
    # sampling; the size of this gap estimates how much of the document it read.
    gap = None
    if "easy" in bands and "very hard" in bands:
        gap = bands["easy"]["relative"] - bands["very hard"]["relative"]
    return {"set": d.name, "model": args.model, "n_scored": len(all_ex), "n_errors": errors,
            "exact": sum(all_ex) / n,
            "partial": sum(v for vs in pa.values() for v in vs) / n,
            "relative": sum(v for vs in rl.values() for v in vs) / n,
            "bands": bands, "easy_minus_veryhard": gap,
            "families": fam, "predictions": str(pred_path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--api-key", default="")
    ap.add_argument("--max-questions", type=int, default=0, help="pilot cap, 0 = all")
    ap.add_argument("--max-tokens", type=int, default=2048,
                    help="reasoning models need headroom; the answer is parsed from the tail")
    ap.add_argument("--timeout", type=int, default=300, help="per-query ceiling, seconds")
    ap.add_argument("--out", default="eval_report.json")
    args = ap.parse_args()
    report = []
    for d in args.sets:
        print(f"\n== {d} / {args.model}")
        report.append(run_set(Path(d), args))
    for r in report:
        print(f"\n== {r['set']}  scored={r['n_scored']} errors={r['n_errors']}  "
              f"exact={r['exact']:.3f} partial={r['partial']:.3f} relative={r['relative']:.3f}")
        for k, v in r["families"].items():
            print(f"   {k:<14} n={v['n']:<4} exact={v['exact']:.3f} "
                  f"partial={v['partial']:.3f} relative={v['relative']:.3f}")
        if r["bands"]:
            print("   --- by measured difficulty (REPORT THESE, not the pooled figure) ---")
            for b in ("very hard", "hard", "moderate", "easy"):
                v = r["bands"].get(b)
                if v:
                    print(f"   {b:<14} n={v['n']:<4} exact={v['exact']:.3f} "
                          f"relative={v['relative']:.3f}")
            if r["easy_minus_veryhard"] is not None:
                print(f"   easy - very hard = {r['easy_minus_veryhard']:+.3f}   "
                      f"(large gap = the model sampled rather than read)")
        else:
            why = ("nothing was scored (every question errored)" if r["n_scored"] == 0
                   else "this set has no difficulty.jsonl -- run scripts/grade_questions.py")
            print(f"   [no difficulty bands: {why}.\n"
                  "    A pooled score alone mostly measures whether the model reads Turkish,\n"
                  "    so do not report this run until the bands are available.]")
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nreport -> {args.out}")


if __name__ == "__main__":
    main()