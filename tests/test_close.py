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
from build_tr_oolong import Config, close_comparisons, question_role  # noqa: E402


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
    print("CLOSE-COMPARISON TEST PASSED")


if __name__ == "__main__":
    main()
