"""Direct-model evaluation harness for TR-OOLONG.

Feeds haystack + question to any OpenAI-compatible /v1/chat/completions
endpoint and scores predictions with the FROZEN metric in src/scoring.py.
  Ollama:  --base-url http://localhost:11434/v1
  vLLM:    --base-url http://localhost:8000/v1
Resumable: predictions append to <set>/predictions_<model>.jsonl; answered
questions are skipped on rerun within an identical data/protocol fingerprint,
keyed on `uid`. Errors and timeouts are reported separately and count as zero
in all-eligible scores; successful-response scores are also reported.

Usage:
    python scripts/run_eval.py --sets tr_intent_out --model qwen3:8b
"""

import argparse
import hashlib
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
from task_contract import instructions, PROTOCOL_VERSION

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

    safe_model = re.sub(r"[^\w.-]", "_", args.model)
    run_spec = {"protocol": PROTOCOL_VERSION, "model": args.model,
                "base_url": args.base_url, "max_tokens": args.max_tokens,
                "manifest": hashlib.sha256((d / "manifest.json").read_bytes()).hexdigest(),
                "questions": hashlib.sha256((d / "questions.jsonl").read_bytes()).hexdigest(),
                "haystacks": hashlib.sha256((d / "haystacks.jsonl").read_bytes()).hexdigest(),
                "scorer": hashlib.sha256((ROOT / "src/scoring.py").read_bytes()).hexdigest(),
                "harness": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "prompt": PROMPT, "instructions": instructions(man)}
    run_id = hashlib.sha256(json.dumps(run_spec, sort_keys=True).encode()).hexdigest()[:16]
    pred_path = d / f"predictions_{safe_model}_{run_id}.jsonl"
    (d / f"run_{safe_model}_{run_id}.json").write_text(json.dumps(run_spec, indent=2, ensure_ascii=False))
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
            prompt = instructions(man) + "\n\n" + PROMPT[q["language"]].format(
                sep=sep.strip(), haystack=haystacks[q["haystack_id"]], question=q["question"])
            t0 = time.time()
            row = {"uid": q["uid"], "dataset": q["dataset"], "id": q["id"],
                   "model": args.model, "run_id": run_id}
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
    by_role = defaultdict(list)
    totals = defaultdict(int)
    errors = 0
    for q in questions:
        group = ("core_document" if q.get("core_document") else "core_ordinary") if q.get("role") == "core" else q.get("role", "control")
        totals[group] += 1
        r = preds.get(q["uid"]) or preds.get(q["id"])
        if r is None:
            continue
        if "error" in r:
            errors += 1
            continue
        ex[q["kind"]].append(r["exact"])
        pa[q["kind"]].append(r["partial"])
        rl[q["kind"]].append(r.get("relative", r["exact"]))
        # the primary score is recomputed rather than read from the row, so
        # prediction files written before v0.8.0 are reported the same way
        by_role[group].append(score(q, r["prediction"])["primary"])
    fam = {k: {"n": len(v), "exact": sum(v) / len(v),
               "partial": sum(pa[k]) / len(pa[k]), "relative": sum(rl[k]) / len(rl[k])}
           for k, v in sorted(ex.items())}
    roles = {k: {"n": len(by_role[k]), "n_eligible": n,
                 "coverage": len(by_role[k]) / n,
                 "primary_all_eligible": sum(by_role[k]) / n,
                 "primary_answered": sum(by_role[k]) / len(by_role[k]) if by_role[k] else None}
             for k, n in totals.items()}
    return {"set": d.name, "model": args.model,
            "n_scored": sum(len(v) for v in ex.values()), "n_errors": errors,
            "roles": roles, "families": fam, "predictions": str(pred_path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--api-key", default="")
    ap.add_argument("--max-questions", type=int, default=0, help="pilot cap, 0 = all")
    ap.add_argument("--max-tokens", type=int, default=2048,
                    help="output budget; the answer must follow the strict response contract")
    ap.add_argument("--timeout", type=int, default=300, help="per-query ceiling, seconds")
    ap.add_argument("--out", default="eval_report.json")
    args = ap.parse_args()
    report = []
    for d in args.sets:
        print(f"\n== {d} / {args.model}")
        report.append(run_set(Path(d), args))
    for r in report:
        print(f"\n== {r['set']}  scored={r['n_scored']} errors={r['n_errors']}")
        print("   --- by role (REPORT THESE; never pool the roles) ---")
        for role in ("core_document", "core_ordinary", "retrieval", "control"):
            v = r["roles"].get(role)
            if v:
                print(f"   {role:<14} n={v['n']}/{v['n_eligible']} primary_all={v['primary_all_eligible']:.3f} coverage={v['coverage']:.3f}")
        for k, v in r["families"].items():
            print(f"   {k:<16} n={v['n']:<4} exact={v['exact']:.3f} "
                  f"partial={v['partial']:.3f} relative={v['relative']:.3f}")
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nreport -> {args.out}")


if __name__ == "__main__":
    main()
