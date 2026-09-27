"""Experiment: can a skimmer that guesses "a small number" crack very-hard questions?

Setup (2026-09-27). No model is involved; the reader is a short program.
  * It reads a random 5% of a document's records and is told the true label of
    each one it reads (the same reader `grade_questions.py` uses).
  * For count, entity_count and proportion questions: if the sample contains
    0 or 1 matching records, it answers G records (in the question's unit)
    instead of scaling the sample up. Otherwise it scales up as usual.
  * G = 12 is fixed in advance: roughly the geometric middle of the rare band
    [5, 30] that the datacard publishes. Other G values are reported to show
    the result does not hinge on that choice.
  * Averaged over 200 random samples per question (64 for the other G values),
    scored with the `relative` metric, as the grades are.

A question "leaves very hard" if max(old grade score, this reader's score) is
0.35 or more.

Usage: python experiments/small_guess.py
"""
import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from scoring import score                                        # noqa: E402
from sampling_solver import load_set, read_random                # noqa: E402
from grade_questions import band                                 # noqa: E402

SETS = ["amazon_hpc_en", "en_intent", "en_intent_paired", "interpress_tr", "marc_en",
        "musteri_tr", "sikayet_tr", "sinema_tr", "tr_intent", "tr_intent_paired",
        "vitamins_tr"]
NUMERIC = ("count", "entity_count", "proportion")
FRAC = 0.05


def hits(q, rows):
    if q["kind"] == "entity_count":
        return sum(1 for l, e, _ in rows if l == q["label"] and e == q["entity"])
    return sum(1 for l, _, _ in rows if l == q["label"])


def guess_answer(q, sample, k, n, G):
    """Scale the sample up, unless it saw 0-1 matches: then answer ~G records."""
    h = hits(q, sample)
    if q["kind"] in ("count", "entity_count"):
        return str(G if h <= 1 else round(h * n / k))
    unit = 1000 if q.get("unit") == "per_mille" else 100
    if h <= 1:
        return str(max(1, round(G / n * unit)))
    return str(round(h / k * unit))


def run(G, trials):
    res = []
    for s in SETS:
        d = ROOT / f"{s}_out"
        qs, metas = load_set(d)
        grades = {r["uid"]: r for r in map(json.loads, open(d / "difficulty.jsonl"))}
        for q in qs:
            if q["kind"] not in NUMERIC:
                continue
            m = metas[q["haystack_id"]]
            rows = list(zip(m["label"].to_list(), m["entity"].to_list(), m["half"].to_list()))
            n = len(rows)
            k = max(1, round(n * FRAC))
            got = [score(q, guess_answer(q, read_random(rows, k, random.Random(f"guess-{q['uid']}-{t}")),
                                         k, n, G))["relative"] for t in range(trials)]
            g = grades[q["uid"]]
            res.append({"uid": q["uid"], "set": s, "family": g["family"],
                        "old": g["difficulty"], "old_score": g["shortcut_score"],
                        "new_score": round(sum(got) / len(got), 4), "answer": q["answer"],
                        "question": q["question"], "n_records": n})
    return res


def main():
    summary = {}
    for G in (8, 10, 12, 15, 20):
        res = run(G, 200 if G == 12 else 64)
        vh = [r for r in res if r["old"] == "very hard"]
        new = [band(max(r["old_score"], r["new_score"])) for r in vh]
        left = sum(b != "very hard" for b in new)
        easy = sum(b in ("moderate", "easy") for b in new)
        mean_new = statistics.mean(r["new_score"] for r in vh)
        print(f"G={G:>2}: {left}/{len(vh)} very-hard numeric questions leave the band "
              f"({100 * left / len(vh):.0f}%), {easy} reach moderate or easy; "
              f"mean score {mean_new:.2f} (four graded readers: "
              f"{statistics.mean(r['old_score'] for r in vh):.2f})")
        summary[G] = {"very_hard_numeric": len(vh), "leave_band": left,
                      "reach_moderate_or_easy": easy, "mean_score": round(mean_new, 3)}
        if G == 12:
            fam = Counter((r["family"], b == "very hard") for r, b in zip(vh, new))
            print("   still very hard / left, by family:",
                  {f: (fam[(f, True)], fam[(f, False)]) for f in sorted({r["family"] for r in vh})})
            (ROOT / "experiments" / "small_guess_G12.jsonl").write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in vh) + "\n", encoding="utf-8")
    (ROOT / "experiments" / "small_guess.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
