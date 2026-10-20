#!/usr/bin/env python3
"""Score model responses for TR-OOLONG (Python 3.9+, standard library only).

The answer is read from the part of the response after the last answer prefix
the question asks for ("Answer:", "Label:", "User:", "Date:"; Turkish
"Cevap:", "Etiket:", "Kullanıcı:", "Tarih:"):

- comparisons: the first allowed relation found there, longest first
  ("more common than", "less common than", "same frequency as", "more common",
  "less common", "the same frequency"; Turkish "daha fazla", "daha az",
  "eşit sayıda", "daha yüksek", "daha düşük", "aynı"), so the English sentence
  form "Answer: A is less common than B" is read as "less common than";
- labels: the text up to the end of the line, without quotes, brackets and a
  final full stop, lower-cased;
- users and numbers: the first number, which must be a whole number written in
  digits ("1234", or with thousands grouping "1,234" / "1.234"); a number with a
  fractional part ("65.5", "65,5") is not a readable answer;
- dates: MM/DD/YYYY, GG.AA.YYYY or YYYY-MM-DD, compared as dates;
- months: "March 2022" / "Mart 2022", lower-cased.

A response is correct if the extracted answer equals any listed answer. A
response without the prefix or without a readable answer is wrong. Numbers
are scored exactly; `--partial` also reports OOLONG's partial score
(0.75 ** |error|), which is not an accuracy.

    python score_responses.py data/main/musteri_tr/test/questions.jsonl.gz responses.jsonl
    python score_responses.py --self-test data      # canonical right, wrong and malformed completions for every question

responses.jsonl: one {"uid": ..., "response": ...} per line.
"""
import argparse
import datetime
import gzip
import json
import re
import sys
from pathlib import Path

AYLAR = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım",
         "aralık"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
RELATIONS = {"en": ["more common than", "less common than", "same frequency as", "the same frequency",
                    "more common", "less common"],
             "tr": ["eşit sayıda", "daha yüksek", "daha düşük", "daha fazla", "daha az", "aynı"]}
PREFIX = {("en", "COMPARISON"): "answer:", ("en", "NUMERIC"): "answer:", ("en", "MONTH_YEAR"): "answer:",
          ("en", "LABEL"): "label:", ("en", "USER"): "user:", ("en", "DATE"): "date:",
          ("tr", "COMPARISON"): "cevap:", ("tr", "NUMERIC"): "cevap:", ("tr", "MONTH_YEAR"): "cevap:",
          ("tr", "LABEL"): "etiket:", ("tr", "USER"): "kullanıcı:", ("tr", "DATE"): "tarih:"}


def read_jsonl(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def lower(s, lang="en"):
    if not s:
        return s
    return s.replace("I", "ı").replace("İ", "i").lower() if lang == "tr" else s.lower()


def kind(q):
    return q.get("answer_type", "COMPARISON")      # extension questions are comparisons


def after_prefix(response, q):
    text = lower(response or "", q["language"])
    p = PREFIX[(q["language"], kind(q))]
    i = text.rfind(p)
    return None if i < 0 else text[i + len(p):].strip()


def parse_date(s):
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return datetime.date(int(m[1]), int(m[2]), int(m[3]))
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", s)
    if not m:
        return None
    a, b, y = int(m[1]), int(m[2]), int(m[3])
    return datetime.date(y, a, b)


def extract(response, q):
    tail = after_prefix(response, q)
    if tail is None:
        return None
    k = kind(q)
    if k == "COMPARISON":
        hits = [(tail.find(r), r) for r in RELATIONS[q["language"]] if r in tail]
        return min(hits, key=lambda h: (h[0], -len(h[1])))[1] if hits else None   # earliest, then longest
    if k in ("USER", "NUMERIC"):
        m = re.search(r"-?\d+(?:[.,]\d+)*", tail)
        if not m:
            return None
        tok = m.group(0)
        if re.fullmatch(r"-?\d+", tok):
            return tok
        if re.fullmatch(r"-?\d{1,3}(?:,\d{3})+|-?\d{1,3}(?:\.\d{3})+", tok):   # thousands grouping
            return re.sub(r"[.,]", "", tok)
        return None                                                          # fractional: not a whole number
    if k == "DATE":
        try:
            if q["language"] == "tr":
                m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", tail)
                if m:
                    return datetime.date(int(m[3]), int(m[2]), int(m[1])).isoformat()
            d = parse_date(tail)
            return d.isoformat() if d else None
        except ValueError:
            return None
    line = tail.split("\n")[0]
    return re.sub(r"[\"'`*\[\]]", "", line).strip().rstrip(".").strip()


def correct(response, q):
    got = extract(response, q)
    gold = [lower(str(x), q["language"]) for x in q["answer"]]
    return got is not None and lower(got, q["language"]) in gold, got


def partial(response, q):
    got = extract(response, q)
    try:
        return 0.75 ** abs(int(got) - int(q["answer"][0]))
    except (TypeError, ValueError):
        return 0.0


def canonical(q, value):
    """A response in exactly the form the question asks for, with `value` filled in."""
    k, lang, s = kind(q), q["language"], q["question"]
    if k == "COMPARISON" and lang == "en":
        m = re.search(r"form 'Answer: (.*?) is \[X\] (.*?)'", s)
        return f"Answer: {m.group(1)} is {value} {m.group(2)}"
    if k == "DATE":
        d = datetime.date.fromisoformat(value)
        return f"Date: {d:%m/%d/%Y}" if lang == "en" else f"Tarih: {d:%d.%m.%Y}"
    word = {("en", "LABEL"): "Label", ("en", "USER"): "User", ("tr", "LABEL"): "Etiket",
            ("tr", "USER"): "Kullanıcı"}.get((lang, k), "Answer" if lang == "en" else "Cevap")
    return f"{word}: {value}"


def wrong_value(q):
    k, lang, gold = kind(q), q["language"], [str(x) for x in q["answer"]]
    if k == "COMPARISON":
        opts = [r for r in RELATIONS[lang] if r not in [lower(g) for g in gold]]
        same_family = [r for r in opts if (" than" in r or " as" in r) == any(" than" in g or " as" in g for g in gold)]
        return (same_family or opts)[0]
    if k in ("USER", "NUMERIC"):
        return str(int(gold[0]) + 1)
    if k == "DATE":
        return (datetime.date.fromisoformat(gold[0]) + datetime.timedelta(days=1)).isoformat()
    if k == "MONTH_YEAR":
        name, year = gold[0].split()
        return f"{name} {int(year) + 1}"
    m = re.search(r"one of the labels: (.*)\.$", q["question_en"].strip())
    labels = [x.strip() for x in m.group(1).split(", ")] if m else []
    others = [l for l in labels if l not in gold]
    return others[0] if others else None


def malformed(q):
    """Responses that must be scored wrong whatever the gold answer."""
    k, gold = kind(q), str(q["answer"][0])
    prefix = canonical(q, gold).split(":")[0] + ":"
    out = [None, "", gold, prefix, f"{prefix} ", canonical(q, gold).replace(":", "", 1)]
    if k in ("USER", "NUMERIC"):
        out += [f"{prefix} {gold}.5", f"{prefix} {gold},5", f"{prefix} {gold}.25", f"{prefix} about {gold}.5"]
    return out


def grouped(q):
    """A correct numeric answer written with thousands grouping, or None below 1000."""
    gold = str(q["answer"][0])
    if kind(q) not in ("USER", "NUMERIC") or len(gold.lstrip("-")) < 4:
        return None
    return canonical(q, f"{int(gold):,}")


def self_test(data):
    right = wrong = n = n_wrong = 0
    n_bad = bad = n_group = group = 0
    failures = []
    for qf in sorted(Path(data).glob("**/questions.jsonl.gz")):
        for q in read_jsonl(qf):
            n += 1
            ok, got = correct(canonical(q, str(q["answer"][0])), q)
            right += ok
            if not ok and len(failures) < 5:
                failures.append((q["uid"], canonical(q, str(q["answer"][0])), got, q["answer"]))
            w = wrong_value(q)
            if w is not None:
                n_wrong += 1
                wrong += not correct(canonical(q, w), q)[0]
            for r in malformed(q):
                n_bad += 1
                ok_bad = not correct(r, q)[0]
                bad += ok_bad
                if not ok_bad and len(failures) < 10:
                    failures.append((q["uid"], r, "malformed but accepted"))
            g = grouped(q)
            if g is not None:
                n_group += 1
                group += correct(g, q)[0]
    print(f"correct completions accepted: {right}/{n}; wrong completions rejected: {wrong}/{n_wrong}; "
          f"malformed responses rejected: {bad}/{n_bad}; grouped numbers accepted: {group}/{n_group}")
    for f in failures:
        print("  FAILED:", f)
    return 0 if right == n and wrong == n_wrong and bad == n_bad and group == n_group else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("questions", help="questions.jsonl(.gz), or the data folder with --self-test")
    ap.add_argument("responses", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--partial", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test(a.questions)
    qs = {q["uid"]: q for q in read_jsonl(a.questions)}
    res = {r["uid"]: r["response"] for r in read_jsonl(a.responses)}
    scores, parts = [], []
    for uid, q in qs.items():
        ok, _ = correct(res.get(uid), q)
        scores.append(ok)
        if kind(q) == "NUMERIC":
            parts.append(partial(res.get(uid), q))
    print(f"accuracy {sum(scores) / len(scores):.4f} on {len(scores)} questions ({len(qs) - len(res)} without a response)")
    if a.partial and parts:
        print(f"OOLONG partial score on numeric questions: {sum(parts) / len(parts):.4f} (not an accuracy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
