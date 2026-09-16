#!/usr/bin/env python3
"""Cross-benchmark check: run TR-OOLONG's partial-coverage solvers on OOLONG.

Why this exists. `scripts/sampling_solver.py` shows that most TR-OOLONG
families can be answered by classifying a fraction of the records and scaling
up. The obvious reviewer question is whether that is a defect we introduced or
a property of label-aggregation benchmarks in general. OOLONG (Bertsch et al.,
arXiv:2511.02817) is the benchmark TR-OOLONG follows and the one the RLM
results are reported on, so it is the right comparison.

It is answerable without reimplementing their pipeline, because OOLONG ships
`context_window_text_with_labels`: the per-record gold label of every record in
every context window is public. Their records are one per line, formatted

    Date: Aug 05, 2024 || User: 44106 || Instance: <text> || Label: incorrect

so the same four readers apply directly.

**The discipline that makes these numbers citable.** We re-derive each gold
answer from the parsed records with a PERFECT full reader. A question is
included only if that reproduces their published answer exactly. Anything our
adapter parses or scopes wrongly scores below 1.0 on the full read and is
DROPPED, not reported. The counts of kept and dropped questions are in the
output, so the coverage of the claim is visible.

Three metrics per question:
  exact     their headline convention for categorical answers
  oolong    0.75 ** |y - yhat| for numerics, which is their numeric metric
  relative  max(0, 1 - |y-yhat|/y), the scale-free metric TR-OOLONG added in
            v0.4.0 because `oolong` is degenerate at four-figure answers

Usage:
  python scripts/oolong_crosscheck.py                    # the default coverage set
  python scripts/oolong_crosscheck.py --shards 4 21 25   # specific shards
  python scripts/oolong_crosscheck.py --list             # what each shard holds
"""

from __future__ import annotations

import argparse
import ast
import datetime
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]

REPO = "oolongbench/oolong-synth"
# Pinned exactly as the five fetch scripts pin their Hub sources (DATACARD,
# "Source revisions are pinned"). This is the revision that was HEAD when the
# cross-check was run; their card records a correction on 2026-06-20.
REVISION = "f0d59eaf0febf130664cfceb710436c8e3216b2b"
N_SHARDS = 41

# All 8 source corpora, label spaces 2/3/4/10, contexts 1K to 1M. The 2M and 4M
# shards are excluded on download size alone (0.4 to 1.3 GB each), not on
# principle; --shards overrides this.
DEFAULT_SHARDS = [3, 4, 5, 8, 9, 11, 12, 16, 17, 18, 19, 20, 21, 22,
                  24, 25, 26, 28, 29, 30, 33, 34]

REC = re.compile(r"^Date:\s*(?P<date>.*?)\s*\|\|\s*User:\s*(?P<user>.*?)\s*\|\|\s*"
                 r"Instance:\s*(?P<inst>.*?)\s*\|\|\s*Label:\s*(?P<label>.*?)\s*$")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}


def shard_url(i: int) -> str:
    return (f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}"
            f"/data/test-{i:05d}-of-{N_SHARDS:05d}.parquet")


def parse_records(text: str) -> list[tuple]:
    """(label, user, date) per record line. The header and the 'Recall:' footer
    do not match and are skipped."""
    out = []
    for line in text.split("\n"):
        m = REC.match(line.strip())
        if not m:
            continue
        try:
            d = datetime.datetime.strptime(m["date"], "%b %d, %Y").date()
        except ValueError:
            d = None
        out.append((m["label"], m["user"], d))
    return out


def parse_gold(a):
    """Their answers are stringified singleton lists: "['incorrect']", '[7]',
    '[datetime.date(2023, 1, 3)]'."""
    s = str(a)
    m = re.match(r"^\[datetime\.date\((\d+),\s*(\d+),\s*(\d+)\)\]$", s)
    if m:
        return datetime.date(*(int(x) for x in m.groups()))
    try:
        v = ast.literal_eval(s)
        return v[0] if isinstance(v, list) and v else v
    except (ValueError, SyntaxError):
        return s


def scope_of(q: str):
    """The subset a question restricts itself to, as a predicate + a name."""
    mu = re.search(r"user IDs ([\d,\s]+?(?:and\s*\d+)?)\.", q)
    if mu:
        ids = set(re.findall(r"\d+", mu.group(1)))
        return (lambda r: r[1] in ids), "user-scoped"
    mm = re.search(r"instances that occur in (\w+) of any year", q)
    if mm and mm.group(1) in MONTHS:
        mo = MONTHS[mm.group(1)]
        return (lambda r: r[2] is not None and r[2].month == mo), "month-scoped"
    return (lambda r: True), "global"


def answer(task: str, q: str, rows: list[tuple], frac: float):
    """Best answer a reader holding `rows` (a `frac` fraction of the document,
    with true labels) can give. None when the family is not attackable this way."""
    pred, _ = scope_of(q)
    rows = [r for r in rows if pred(r)]
    lab = [r[0] for r in rows]
    scale = 1.0 / frac

    if task == "TASK_TYPE.NUMERIC_ONE_CLASS":
        m = re.search(r"label '([^']+)'", q)
        return None if not m else round(lab.count(m.group(1)) * scale)

    if task == "TASK_TYPE.REPRESENTED_N_TIMES":
        # "how many dates are represented exactly N times". A sampler can only
        # count dates seen exactly N times IN THE SAMPLE and scale. That is a
        # badly biased estimator, which is the point of measuring it.
        m = re.search(r"represented exactly (\d+) times", q)
        if not m:
            return None
        n = int(m.group(1))
        c = Counter(r[2] for r in rows if r[2] is not None)
        return round(sum(1 for v in c.values() if v == n) * (scale if frac < 1 else 1))

    if task in ("TASK_TYPE.MOST_FREQ", "TASK_TYPE.LEAST_FREQ", "TASK_TYPE.SECOND_MOST_FREQ"):
        if "which user" in q:
            m = re.search(r"instances with the label (\S+?)\?", q)
            pool = [u for l, u, _ in rows if l == m.group(1)] if m else [r[1] for r in rows]
        elif "which of the labels" in q:
            pool = lab
        elif "which date" in q:
            pool = [r[2] for r in rows if r[2] is not None]
        else:
            return None
        c = Counter(pool)
        if not c:
            return None
        ranked = sorted(c, key=lambda x: (-c[x], str(x)))
        if task == "TASK_TYPE.MOST_FREQ":
            return ranked[0]
        if task == "TASK_TYPE.LEAST_FREQ":
            return ranked[-1]
        return ranked[1] if len(ranked) > 1 else ranked[0]

    if task == "TASK_TYPE.RELATIVE_FREQ":
        m = re.search(r"is label '([^']+)' more common, less common, or the same "
                      r"frequency as label '([^']+)'", q)
        if m:
            a, b = lab.count(m.group(1)), lab.count(m.group(2))
            return ("more common than" if a > b else
                    "less common than" if a < b else "same frequency as")
        m = re.search(r"which user has more instances with the label (\S+?): "
                      r"User (\d+) or User (\d+)", q)
        if m:
            lb, u1, u2 = m.groups()
            c1 = sum(1 for l, u, _ in rows if l == lb and u == u1)
            c2 = sum(1 for l, u, _ in rows if l == lb and u == u2)
            return u1 if c1 >= c2 else u2
        # OOLONG's analogue of the family TR-OOLONG withdrew as `shift`, but
        # over a REAL date axis rather than positional halves.
        m = re.search(r"was label '([^']+)' more common, less common, or the same "
                      r"frequency before (\d{4}-\d{2}-\d{2})", q)
        if m:
            lb = m.group(1)
            cut = datetime.date.fromisoformat(m.group(2))
            pre = [r for r in rows if r[2] is not None and r[2] < cut]
            post = [r for r in rows if r[2] is not None and r[2] >= cut]
            if not pre or not post:
                return None
            p1 = sum(1 for r in pre if r[0] == lb) / len(pre)
            p2 = sum(1 for r in post if r[0] == lb) / len(post)
            return ("more common" if p1 > p2 else
                    "less common" if p1 < p2 else "the same frequency")
        m = re.search(r"In which month did the label '(\S+?) first occur more often "
                      r"than the label '(\S+?)'", q)
        if m:
            a, b = m.group(1), m.group(2)
            by = defaultdict(lambda: [0, 0])
            for l, _, d in rows:
                if d is None:
                    continue
                if l == a:
                    by[(d.year, d.month)][0] += 1
                elif l == b:
                    by[(d.year, d.month)][1] += 1
            for ym in sorted(by):
                if by[ym][0] > by[ym][1]:
                    names = {v: k for k, v in MONTHS.items()}
                    return f"{names[ym[1]]} {ym[0]}"
            return None
        m = re.search(r"For how many months does the label '([^']+)' occur more "
                      r"frequently than the label '([^']+)'", q)
        if m:
            a, b = m.groups()
            by = defaultdict(lambda: [0, 0])
            for l, _, d in rows:
                if d is None:
                    continue
                if l == a:
                    by[(d.year, d.month)][0] += 1
                elif l == b:
                    by[(d.year, d.month)][1] += 1
            return sum(1 for v in by.values() if v[0] > v[1])
        return None
    return None


def score3(g, pred) -> tuple | None:
    """(exact, oolong, relative). None when the reader gave no answer."""
    if pred is None:
        return None
    if isinstance(g, datetime.date):
        return None                      # date-valued golds: formatting, not reading
    gs = str(g).strip()
    if gs.lstrip("-").isdigit():
        try:
            y, yhat = int(gs), int(pred)
        except (TypeError, ValueError):
            return None
        e = abs(y - yhat)
        return (float(e == 0), 0.75 ** min(e, 400), max(0.0, 1 - e / max(abs(y), 1)))
    s = float(gs.lower() == str(pred).strip().lower())
    return (s, s, s)


def blind(task: str, q: str, n_records: int, n_labels: int):
    """Their read-nothing reference, same construction as ours: N/K."""
    if task == "TASK_TYPE.NUMERIC_ONE_CLASS" and scope_of(q)[1] == "global":
        return round(n_records / n_labels)
    return None


def readers(rows: list[tuple], k: int, rng: random.Random) -> dict:
    n, h = len(rows), k // 2
    return {"random": rng.sample(rows, k),
            "prefix": rows[:k],
            "headtail": rows[:h] + rows[n - (k - h):],
            "stride": ([rows[round(i * (n - 1) / (k - 1))] for i in range(k)]
                       if k > 1 else rows[:1])}


def fetch_shard(i: int, cache: Path) -> Path:
    """Download one shard to `cache`. The caller deletes it; the biggest shards
    are 0.4 to 1.4 GB and there are 41 of them."""
    from huggingface_hub import hf_hub_download
    f = hf_hub_download(repo_id=REPO, repo_type="dataset", revision=REVISION,
                        filename=f"data/test-{i:05d}-of-{N_SHARDS:05d}.parquet",
                        local_dir=str(cache))
    return Path(f)


# Everything except `context_window_text`, which is the SAME text without the
# label suffix. Dropping it roughly halves the read, and on a 16 GB machine the
# 4M-token shards do not fit otherwise.
NEEDED = ["id", "context_len", "dataset", "num_labels", "task_group", "task",
          "question", "answer", "context_window_text_with_labels"]


def run_shard(i: int, fractions, seed, min_records, cache: Path, keep: bool) -> list[dict]:
    """Stream the shard one parquet row group at a time, so peak memory is one
    row group rather than the whole file."""
    import pyarrow.parquet as pq

    path = fetch_shard(i, cache)
    rows_out = []
    try:
        pf = pq.ParquetFile(path)
        for rg in range(pf.num_row_groups):
            tbl = pf.read_row_group(rg, columns=NEEDED)
            for r in tbl.to_pylist():
                rows_out.extend(score_question(r, i, fractions, seed, min_records))
            del tbl
    finally:
        if not keep:
            try:
                path.unlink()
            except OSError:
                pass
    return rows_out


def score_question(r: dict, shard: int, fractions, seed, min_records) -> list[dict]:
    recs = parse_records(r["context_window_text_with_labels"])
    if len(recs) < min_records:
        return []
    g = parse_gold(r["answer"])
    task, q = r["task"], r["question"]
    full = score3(g, answer(task, q, recs, 1.0))
    rec = {"shard": shard, "dataset": r["dataset"], "context_len": r["context_len"],
           "num_labels": r["num_labels"], "task_group": r["task_group"],
           "task": task.replace("TASK_TYPE.", ""), "scope": scope_of(q)[1],
           "n_records": len(recs), "verified": bool(full and full[0] == 1.0)}
    if not rec["verified"]:
        return [rec]
    rec["gold_magnitude"] = int(str(g)) if str(g).lstrip("-").isdigit() else None
    b = blind(task, q, len(recs), r["num_labels"])
    bs = score3(g, b) if b is not None else None
    rec["blind"] = None if bs is None else bs[2]
    for f in fractions:
        k = max(1, min(len(recs), int(round(len(recs) * f))))
        rng = random.Random(f"{seed}-{r['id']}-{f}")
        for nm, sub in readers(recs, k, rng).items():
            v = score3(g, answer(task, q, sub, k / len(recs)))
            if v is not None:
                rec[f"{nm}@{f}"] = {"exact": v[0], "oolong": v[1], "relative": v[2]}
    return [rec]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shards", nargs="+", type=int, default=DEFAULT_SHARDS)
    ap.add_argument("--fractions", nargs="+", type=float, default=[0.05, 0.25])
    ap.add_argument("--min-records", type=int, default=100,
                    help="skip contexts too short for a 5%% sample to mean anything")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json", default="manifests/oolong_crosscheck.json")
    ap.add_argument("--list", action="store_true", help="print shard contents and exit")
    ap.add_argument("--cache", default=None,
                    help="where shards are downloaded (deleted after, unless --keep)")
    ap.add_argument("--keep", action="store_true", help="do not delete downloaded shards")
    args = ap.parse_args()

    if args.list:
        print(f"{'shard':>6}{'rows':>6}  {'dataset':14}{'K':>4}  context lengths")
        for i in range(N_SHARDS):
            d = pl.read_parquet(shard_url(i),
                                columns=["context_len", "dataset", "num_labels"])
            print(f"{i:>6}{d.height:>6}  {d['dataset'].unique().to_list()[0]:14}"
                  f"{str(sorted(d['num_labels'].unique().to_list())):>8}  "
                  f"{sorted(d['context_len'].unique().to_list())}")
        return 0

    import tempfile
    cache = Path(args.cache) if args.cache else Path(tempfile.mkdtemp(prefix="oolong_"))
    cache.mkdir(parents=True, exist_ok=True)
    allrows, failed = [], []
    for i in args.shards:
        print(f"[shard {i:>2}] downloading and scoring ...", flush=True)
        try:
            allrows.extend(run_shard(i, args.fractions, args.seed, args.min_records,
                                     cache, args.keep))
        except (MemoryError, OSError) as e:
            # The 4M-token shards are 0.4 to 1.4 GB. Losing one to memory or
            # disk must not lose the other forty; the shard list in the manifest
            # records what actually contributed.
            print(f"[shard {i:>2}] SKIPPED: {type(e).__name__}: {e}", flush=True)
            failed.append(i)

    kept = [r for r in allrows if r["verified"]]
    dropped = [r for r in allrows if not r["verified"]]
    print(f"\nquestions reproduced exactly by a perfect full reader: {len(kept)}")
    print(f"dropped (adapter cannot verify the gold, so not reported): {len(dropped)}")
    if dropped:
        c = Counter((r["task"], r["scope"]) for r in dropped)
        for (t, s), n in c.most_common(8):
            print(f"    dropped {n:>4}  {t} / {s}")

    cols = [f"{nm}@{f}" for f in args.fractions
            for nm in ("random", "prefix", "headtail", "stride")]

    def table(rows, group_key, title, metric):
        g = defaultdict(list)
        for r in rows:
            g[group_key(r)].append(r)
        print(f"\n===== {title}  [{metric}] =====")
        print(f"{'group':38}{'n':>5}{'med m':>8}{'blind':>7}"
              + "".join(f"{c:>15}" for c in cols))
        for key in sorted(g, key=str):
            rs = g[key]
            mags = sorted(x["gold_magnitude"] for x in rs if x.get("gold_magnitude") is not None)
            bl = [x["blind"] for x in rs if x.get("blind") is not None]
            cells = ""
            for c in cols:
                v = [x[c][metric] for x in rs if c in x]
                cells += f"{sum(v)/len(v):>15.3f}" if v else f"{'-':>15}"
            print(f"{str(key)[:37]:38}{len(rs):>5}"
                  f"{(str(mags[len(mags)//2]) if mags else '-'):>8}"
                  f"{(f'{sum(bl)/len(bl):.2f}' if bl else '-'):>7}{cells}")

    for metric in ("relative", "exact", "oolong"):
        table(kept, lambda r: f"{r['task']} / {r['scope']}",
              "OOLONG by family and question scope", metric)
    table([r for r in kept if r["task"] == "NUMERIC_ONE_CLASS"],
          lambda r: f"K={r['num_labels']}  ctx={r['context_len']}",
          "OOLONG counting: answer magnitude drives everything", "relative")

    Path(args.json).write_text(json.dumps(
        {"source": REPO, "revision": REVISION, "shards": args.shards,
         "fractions": args.fractions, "seed": args.seed,
         "shards_failed": failed,
         "n_verified": len(kept), "n_dropped": len(dropped),
         "questions": kept}, indent=2, default=str), encoding="utf-8")
    print(f"\nreport -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
