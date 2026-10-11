"""Experiment 13: how many wrong labels flip an answer, OOLONG-synth vs TR-OOLONG.

For each whole-document "which is more common" question, count how many records
would have to carry the other label for the answer to tie or flip: half the gap
between the two counts, rounded up. Compared with the share of records whose
label a careful reader disagrees with, this shows how much a question depends on
label noise rather than on reading.

OOLONG-synth questions limited to one user or one month are skipped, as are
"same frequency" answers. The OOLONG shards are read from a local folder:

    curl -L -o <dir>/test-000NN.parquet \
      https://huggingface.co/datasets/oolongbench/oolong-synth/resolve/f0d59eaf0febf130664cfceb710436c8e3216b2b/data/test-000NN-of-00041.parquet
    .venv/bin/python -I experiments/flip_margin.py <dir>

Run on 11 Oct 2026 with shards 08, 09, 12, 16, 17, 19, 24, 33, 34 (contexts 1K
to 1M; formality, imdb, app_reviews, yahoo, multinli, agnews, metaphors), and
on the v0.11.0-rc1 test split in scratch/prefreeze/test.
"""
import collections, glob, json, math, re, statistics as st, sys
import polars as pl

REC = re.compile(r"^Date:.*?\|\|\s*User:.*?\|\|\s*Instance:.*?\|\|\s*Label:\s*(?P<label>.*?)\s*$")
PAIR = re.compile(r"label '(.+?)' more common, less common, or the same frequency as label '(.+?)'")

def summarize(name, rows):
    k = [r[0] for r in rows]; frac = [r[1] for r in rows]
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]
    print(f"{name:34} n={len(rows):4}  records to flip: median {q(k,.5):5.0f} (p10 {q(k,.1):4.0f})"
          f"   as % of document: median {100*q(frac,.5):5.2f}% (p10 {100*q(frac,.1):4.2f}%)")

oolong = collections.defaultdict(list)
for f in sorted(glob.glob(sys.argv[1] + "/*.parquet")):
    d = pl.read_parquet(f, columns=["context_len", "context_window_text_with_labels", "question", "task", "input_subset"])
    for r in d.iter_rows(named=True):
        if str(r["input_subset"]) == "True" or r["task"] not in ("TASK_TYPE.MOST_FREQ", "TASK_TYPE.RELATIVE_FREQ"):
            continue
        labs = [m["label"] for line in r["context_window_text_with_labels"].splitlines() if (m := REC.match(line))]
        if len(labs) < 50:
            continue
        c = collections.Counter(labs); n = len(labs)
        if r["task"] == "TASK_TYPE.MOST_FREQ":
            top = c.most_common(2); gap = top[0][1] - (top[1][1] if len(top) > 1 else 0)
        else:
            m = PAIR.search(r["question"])
            if not m: continue
            gap = abs(c[m[1]] - c[m[2]])
            if gap == 0: continue  # 'same frequency' answers have no winner to flip
        k = math.ceil(gap / 2)
        oolong[r["task"].split(".")[1]].append((k, k / n))
for t, rows in oolong.items():
    summarize("OOLONG-synth " + t.lower(), rows)

tr = collections.defaultdict(list)
for d in sorted(glob.glob("scratch/prefreeze/test/*_out")):
    qs = [json.loads(l) for l in open(d + "/questions.jsonl")]
    metas = {}
    for q in qs:
        if q["role"] != "core": continue
        h = q["haystack_id"]
        if h not in metas:
            metas[h] = collections.Counter(pl.read_parquet(f"{d}/meta_{h}.parquet", columns=["label"])["label"].to_list())
        c = metas[h]; n = sum(c.values()); gap = abs(c[q["label_a"]] - c[q["label_b"]])
        k = math.ceil(gap / 2)
        tr["core_document" if q.get("core_document") else "ordinary"].append((k, k / n))
for t, rows in tr.items():
    summarize("TR-OOLONG rc1 core, " + t, rows)
