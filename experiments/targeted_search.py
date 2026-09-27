"""Experiment: can a model find the relevant records by searching, and skip the rest?

Setup (2026-09-28). No language model. Two search-then-read attacks:

  brand search   for brand questions (entity_count, entity_argmax, pairwise):
                 read only records whose printed marker [[Brand]] matches a
                 brand named in the question, with their true labels, and answer
                 from those. Cost = share of the document containing the brand.
  topic search   for count and proportion questions: rank every record by how
                 likely it is to carry the asked label, using the out-of-fold
                 word-count classifier from honest_reader.py (a stand-in for a
                 good keyword or embedding search). Read the top B% of records
                 with their true labels, count the matches, and assume there
                 are none in the unread part. B = 2%, 5%, 10%.

Both are told the true label of what they read, so they show what targeted
reading makes possible, not what a real model does.

Usage: python experiments/targeted_search.py
"""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "experiments"))
from sampling_solver import load_set, answer_from_sample          # noqa: E402
from scoring import score                                         # noqa: E402
from honest_reader import SETS, train_predict                      # noqa: E402

BUDGETS = (0.02, 0.05, 0.10)


def main():
    res = defaultdict(lambda: defaultdict(list))   # family -> reader -> [(rel, part, exact, cost)]
    examples = []
    for s in SETS:
        d = ROOT / f"{s}_out"
        qs, metas = load_set(d)
        grades = {r["uid"]: r for r in map(json.loads, open(d / "difficulty.jsonl"))}
        pool = {}
        for m in metas.values():
            pool.update(zip(m["text"].to_list(), m["label"].to_list()))
        texts = list(pool)
        _, labs, _ = train_predict(texts, [pool[t] for t in texts], qs[0]["language"])
        post = train_predict.last_post
        li = {l: i for i, l in enumerate(labs)}
        for q in qs:
            fam = grades[q["uid"]]["family"]
            m = metas[q["haystack_id"]]
            tx, lab, ent, half = (m["text"].to_list(), m["label"].to_list(),
                                  m["entity"].to_list(), m["half"].to_list())
            N = len(tx)
            rows = list(zip(lab, ent, half))
            if q["kind"] in ("entity_count", "entity_argmax", "pairwise"):
                brands = {q.get("entity")} | set(q.get("candidates") or [])
                brands.discard(None)
                idx = [i for i in range(N) if ent[i] in brands]
                pred = answer_from_sample(q, [rows[i] for i in idx], 1.0)
                sc = score(q, pred)
                res[fam]["brand search"].append((sc["relative"], sc["partial"], sc["exact"], len(idx) / N))
                if len(examples) < 3 and q["kind"] == "entity_count":
                    examples.append((q["uid"], q["question"], q["answer"], pred, len(idx), N))
            if q["kind"] in ("count", "proportion") and q["label"] in li:
                k = li[q["label"]]
                order = np.argsort([-post[t][k] for t in tx])
                for B in BUDGETS:
                    top = order[: max(1, round(N * B))]
                    found = sum(1 for i in top if lab[i] == q["label"])
                    if q["kind"] == "count":
                        pred = str(found)
                    else:
                        unit = 1000 if q.get("unit") == "per_mille" else 100
                        pred = str(round(found / N * unit))
                    sc = score(q, pred)
                    res[fam][f"topic search {int(B*100)}%"].append(
                        (sc["relative"], sc["partial"], sc["exact"], B))
        print(f"{s} done", flush=True)

    print(f"\n{'family':14}{'reader':20}{'n':>6}{'relative':>10}{'partial':>10}{'exact':>8}{'read':>8}")
    for fam in sorted(res):
        for rd, v in sorted(res[fam].items()):
            print(f"{fam:14}{rd:20}{len(v):>6}" + "".join(
                f"{statistics.mean(x[i] for x in v):>10.3f}" for i in range(3))
                + f"{100 * statistics.mean(x[3] for x in v):>7.1f}%")
    print("\nexamples (brand search):")
    for e in examples:
        print("  ", e)
    json.dump({f: {r: [list(x) for x in v] for r, v in d.items()} for f, d in res.items()},
              open(ROOT / "experiments" / "targeted_search.json", "w"))


if __name__ == "__main__":
    main()
