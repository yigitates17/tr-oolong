"""Unit test for the v0.8.0 close-comparison family, on hand-made label counts.

The golden fixture's small documents never contain two labels with close
counts, so the family is tested here directly.

    python tests/test_close.py
"""
import random
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from build_tr_oolong import (Config, close_comparisons, core_document_counts,  # noqa: E402
                             question_role)


def meta(counts):
    labels = [l for l, n in counts.items() for _ in range(n)]
    return pl.DataFrame({"label": labels, "entity": ["__none__"] * len(labels),
                         "half": [0] * len(labels)})


def cfg(**kw):
    c = Config(source_path="", language="en")
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def main():
    # 300 vs 291: gap 3.0%, window for 291 is [2.05%, 3.52%] -> askable.
    # 300 vs 200: far apart -> not askable. 40 records: below 2% share of 1,000? no,
    # 40 >= 30 and 40 >= 2% of 831, but no partner in its window.
    m = meta({"a": 300, "b": 291, "c": 200, "d": 40})
    qs = close_comparisons(m, cfg(), random.Random(1))
    assert len(qs) == 1, qs
    q = qs[0]
    assert set(q["candidates"]) == {"a", "b"} and q["answer"] == "a", q
    assert q["answer_key"] == "a" and question_role(q) == "core"

    # excluded label is never used
    assert close_comparisons(m, cfg(close_exclude_labels=["b"]), random.Random(1)) == []

    # ordinal labels one point apart are skipped when a gap of 3 is required
    m2 = meta({"7 stars": 300, "8 stars": 291})
    assert close_comparisons(m2, cfg(close_ordinal_gap=3), random.Random(1)) == []
    assert len(close_comparisons(m2, cfg(), random.Random(1))) == 1

    # a tie is never asked
    assert close_comparisons(meta({"a": 300, "b": 300}), cfg(), random.Random(1)) == []

    # the named order is random, the answer follows the counts
    firsts = {close_comparisons(m, cfg(), random.Random(s))[0]["label_a"] for s in range(20)}
    assert firsts == {"a", "b"}, firsts
    # --- v0.9.0 core documents -------------------------------------------
    pool = {"pos": 5000, "neg": 5000, "neu": 5000}
    c1, pairs1 = core_document_counts(pool, 3000, cfg(core_pairs=[["pos", "neg"]], core_share=0.4),
                                      random.Random(3))
    assert sum(c1.values()) == 3000, c1
    big, small = max(c1["pos"], c1["neg"]), min(c1["pos"], c1["neg"])
    assert big == 1200 and 0.35 / small ** 0.5 <= (big - small) / big <= 0.60 / small ** 0.5, c1
    # the designed pair is asked, and answered by the larger count
    m3 = meta(c1)
    q3 = close_comparisons(m3, cfg(), random.Random(0))
    assert len(q3) == 1 and q3[0]["answer"] == max(c1, key=lambda l: c1[l] if l != "neu" else -1)
    # same seed key -> same counts in both languages, with each language's labels
    c_en, _ = core_document_counts({"positive": 5000, "negative": 5000, "neutral": 5000}, 3000,
                                   cfg(core_pairs=[["positive", "negative"]], core_share=0.4),
                                   random.Random(3))
    assert (c_en["positive"], c_en["negative"]) == (c1["pos"], c1["neg"]), (c_en, c1)
    # a pool too small for the design is refused, not silently shrunk
    assert core_document_counts({"a": 100, "b": 100}, 3000, cfg(core_share=0.4),
                                random.Random(1)) is None
    # automatic pairs never use an excluded label
    c4, p4 = core_document_counts({"a": 900, "b": 900, "x": 900, "d": 900}, 2000,
                                  cfg(core_share=0.2, core_pairs_per_doc=2, close_exclude_labels=["x"]),
                                  random.Random(5))
    assert all("x" not in p for p in p4) and c4.get("x", 0) < 400, (c4, p4)
    # with a counter, the larger label alternates in the rhythm big, big, small, small
    # relative to the pool-larger label (automatic pairs) ...
    bc, wins = [0], []
    for s_ in range(8):
        cc, pp = core_document_counts({"a": 900, "b": 800, "c": 900}, 1000,
                                      cfg(core_share=0.2, core_pairs_per_doc=1), random.Random(s_), bc)
        x, y = pp[0]
        ref = x if {"a": 900, "b": 800, "c": 900}[x] >= {"a": 900, "b": 800, "c": 900}[y] else y
        wins.append(cc[ref] > cc[x if ref == y else y])
    assert wins == [True, True, False, False] * 2, wins
    # ... and between the first and second listed label (explicit pairs)
    bc, firsts = [0], []
    for s_ in range(4):
        cc, _ = core_document_counts(pool, 3000, cfg(core_pairs=[["pos", "neg"]], core_share=0.4),
                                     random.Random(s_), bc)
        firsts.append(cc["pos"] > cc["neg"])
    assert firsts == [True, True, False, False], firsts
    # with a balance counter the answer is first-named in alternating questions
    bal = [0]
    firsts = [close_comparisons(m, cfg(), random.Random(s), bal)[0] for s in range(10)]
    assert [q["answer"] == q["label_a"] for q in firsts] == [True, False] * 5, firsts
    # only pairs listed in close_allowed_pairs_file are ever asked
    import json, tempfile
    tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"allowed_pairs": [["c", "d"]]}, tf)
    tf.close()
    assert close_comparisons(m, cfg(close_allowed_pairs_file=tf.name), random.Random(1)) == []
    both = meta({"a": 300, "b": 291, "c": 250, "d": 244})
    got = close_comparisons(both, cfg(close_allowed_pairs_file=tf.name), random.Random(1))
    assert [set(q["candidates"]) for q in got] == [{"c", "d"}], got
    print("CLOSE-COMPARISON TEST PASSED")


if __name__ == "__main__":
    main()
