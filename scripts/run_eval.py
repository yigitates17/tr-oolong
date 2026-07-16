"""Direct-model evaluation harness for TR-OOLONG.

Feeds haystack + question to any OpenAI-compatible /v1/chat/completions
endpoint and scores predictions with the FROZEN metric in src/scoring.py.
  Ollama:  --base-url http://localhost:11434/v1
  vLLM:    --base-url http://localhost:8000/v1
Resumable: predictions append to <set>/predictions_<model>.jsonl; answered
question ids are skipped on rerun. Errors and timeouts are recorded as
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

    safe_model = re.sub(r"[^\w.-]", "_", args.model)
    pred_path = d / f"predictions_{safe_model}.jsonl"
    done = set()
    if pred_path.exists():
        for line in pred_path.read_text(encoding="utf-8").splitlines():
            done.add(json.loads(line)["id"])

    if args.max_questions:
        questions = questions[: args.max_questions]

    n_err = 0
    with pred_path.open("a", encoding="utf-8") as f:
        for q in questions:
            if q["id"] in done:
                continue
            prompt = PROMPT[q["language"]].format(
                sep=sep.strip(), haystack=haystacks[q["haystack_id"]], question=q["question"])
            t0 = time.time()
            row = {"id": q["id"], "model": args.model}
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
        preds[r["id"]] = r
    ex, pa = defaultdict(list), defaultdict(list)
    errors = 0
    for q in questions:
        r = preds.get(q["id"])
        if r is None:
            continue
        if "error" in r:
            errors += 1
            continue
        ex[q["kind"]].append(r["exact"])
        pa[q["kind"]].append(r["partial"])
    fam = {k: {"n": len(v), "exact": sum(v) / len(v), "partial": sum(pa[k]) / len(pa[k])}
           for k, v in sorted(ex.items())}
    all_ex = [v for vs in ex.values() for v in vs]
    return {"set": d.name, "model": args.model, "n_scored": len(all_ex), "n_errors": errors,
            "exact": sum(all_ex) / max(1, len(all_ex)),
            "partial": sum(v for vs in pa.values() for v in vs) / max(1, len(all_ex)),
            "families": fam, "predictions": str(pred_path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--api-key", default="")
    ap.add_argument("--max-questions", type=int, default=0, help="pilot cap, 0 = all")
    ap.add_argument("--max-tokens", type=int, default=64)
    ap.add_argument("--timeout", type=int, default=300, help="per-query ceiling, seconds")
    ap.add_argument("--out", default="eval_report.json")
    args = ap.parse_args()
    report = []
    for d in args.sets:
        print(f"\n== {d} / {args.model}")
        report.append(run_set(Path(d), args))
    for r in report:
        print(f"\n== {r['set']}  scored={r['n_scored']} errors={r['n_errors']}  "
              f"exact={r['exact']:.3f} partial={r['partial']:.3f}")
        for k, v in r["families"].items():
            print(f"   {k:<14} n={v['n']:<4} exact={v['exact']:.3f} partial={v['partial']:.3f}")
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nreport -> {args.out}")


if __name__ == "__main__":
    main()