#!/usr/bin/env python3
"""Recompute every answer of TR-OOLONG v0.13 from the labelled records.

Standalone: Python 3.9+ standard library only. For each document the record
lines are parsed out of the labelled text (dates, users, labels) and every
question's answer is recomputed from them, using the definitions written out in
CONSTRUCTION.md. The script also checks that each document's unlabelled text is
its labelled text with the labels removed, that the stated label counts match
the lines, and that every Turkish answer is the translation of the English one.

Every set in v0.13 ships its text. (The --restore option rebuilt the text of
sets shipped without it in v0.11-v0.12; it is not needed for this release.)

    python recompute_answers.py data

Exits with status 1 on any disagreement.
"""
import argparse
import collections
import datetime
import gzip
import hashlib
import html
import json
import re
import sys
from pathlib import Path

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
         "Eylül", "Ekim", "Kasım", "Aralık"]
TR_ANSWER = {"more common than": "daha fazla", "less common than": "daha az", "same frequency as": "eşit sayıda",
             "more common": "daha yüksek", "less common": "daha düşük", "the same frequency": "aynı"}
LINE = re.compile(r"^(?:Date|Tarih): (?P<d>[^|]+) \|\| (?:User|Kullanıcı): (?P<u>\d+) \|\| (?:Instance|Kayıt): "
                  r"(?P<t>.*) \|\| (?:Label|Etiket): (?P<l>[^|]*)$")

# Restoring withheld text: how each source's rows become record text and labels.
TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]{0,40}>")
RESTORE = {
    "marc_en": {"text": "text", "label": "label", "map": {0: "negative", 1: "negative", 3: "positive", 4: "positive"}},
    "amazon_hpc_en": {"text": "text", "label": "rating",
                      "map": {1: "negative", 2: "negative", 4: "positive", 5: "positive"}},
}


def clean(text):
    """The cleaning applied to every record: HTML tags to spaces, entities
    decoded, whitespace collapsed, a dotted capital-I artefact normalised."""
    text = html.unescape(TAG.sub(" ", text or ""))
    return re.sub(r"\s+", " ", text).strip().replace("i̇", "i")


def short_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def read_jsonl(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def parse_date(s):
    s = s.strip()
    try:
        return datetime.datetime.strptime(s, "%b %d, %Y").date()
    except ValueError:
        day, month, year = s.split()
        return datetime.date(int(year), AYLAR.index(month) + 1, int(day))


def records(text_with_labels):
    rows = []
    for line in text_with_labels.split("\n"):
        m = LINE.match(line)
        if m:
            rows.append((m["l"].strip(), m["u"], parse_date(m["d"])))
    return rows


def strip_labels(text):
    return re.sub(r" \|\| (?:Label|Etiket): [^\n]*", "", text)


# ---------------------------------------------------------------- answers

def scope(q, rows):
    """Restrict to the records a question asks about (users, a month, a date range)."""
    m = (re.search(r"only consider the subset of users with IDs ([\d, ]+)\.", q)
         or re.search(r"associated with user IDs ([\d, ]+)\.", q))
    if m:
        ids = set(re.findall(r"\d+", m.group(1)))
        return [r for r in rows if r[1] in ids]
    m = re.search(r"occur in (\w+) of any year", q)
    if m:
        month = MONTHS.index(m.group(1)) + 1
        return [r for r in rows if r[2].month == month]
    m = re.search(r"occur between (\w{3} \d{2}, \d{4}) and (\w{3} \d{2}, \d{4}), inclusive", q)
    if m:
        d1, d2 = (datetime.datetime.strptime(x, "%b %d, %Y").date() for x in m.groups())
        return [r for r in rows if d1 <= r[2] <= d2]
    return rows


def unique_rank(counter, rank):
    """The item at `rank` (0 = most frequent) when it is strictly separated from
    its neighbours; None otherwise."""
    top = counter.most_common()
    if len(top) <= rank:
        return None
    if rank > 0 and top[rank - 1][1] == top[rank][1]:
        return None
    if len(top) > rank + 1 and top[rank][1] == top[rank + 1][1]:
        return None
    return top[rank][0]


def by_month(rows):
    out = collections.defaultdict(collections.Counter)
    for label, _, d in rows:
        out[(d.year, d.month)][label] += 1
    return out


def recompute(q, rows):
    """All correct answers (a list), or None when the question is not recognised."""
    rows = scope(q, rows)
    labels = [r[0] for r in rows]

    m = re.search(r"how many data points should be classified as label '([^']+)'", q)
    if m:
        return [labels.count(m.group(1))]
    m = re.search(r"which of the labels is the (most|least) common\?.*one of the labels: (.*)\.$", q.strip())
    if m:
        listed = re.findall(r"'([^']+)'", m.group(2)) or [x.strip() for x in m.group(2).split(", ")]
        c = collections.Counter(labels)
        target = (max if m.group(1) == "most" else min)(c.get(l, 0) for l in listed)
        return sorted(l for l in listed if c.get(l, 0) == target)
    m = re.search(r"which user has the most instances with the label (.+?)\?", q)
    if m:
        return [unique_rank(collections.Counter(u for l, u, _ in rows if l == m.group(1)), 0)]
    m = re.search(r"which user is represented (most|the second most) often\?", q)
    if m:
        return [unique_rank(collections.Counter(r[1] for r in rows), 0 if m.group(1) == "most" else 1)]
    m = re.search(r"which date is represented (most|the second most) often\?", q)
    if m:
        d = unique_rank(collections.Counter(r[2] for r in rows), 0 if m.group(1) == "most" else 1)
        return [d.isoformat() if d else None]
    m = re.search(r"how many dates are represented exactly (\d+) times", q)
    if m:
        return [sum(1 for v in collections.Counter(r[2] for r in rows).values() if v == int(m.group(1)))]
    m = re.search(r"is label '([^']+)' more common, less common, or the same frequency as label '([^']+)'", q)
    if m:
        a, b = labels.count(m.group(1)), labels.count(m.group(2))
        return ["more common than" if a > b else "less common than" if a < b else "same frequency as"]
    m = re.search(r"which user has more instances with the label (.+?): User (\d+) or User (\d+)\?", q)
    if m:
        lb, u1, u2 = m.groups()
        c1 = sum(1 for l, u, _ in rows if l == lb and u == u1)
        c2 = sum(1 for l, u, _ in rows if l == lb and u == u2)
        return [u1 if c1 > c2 else u2 if c2 > c1 else None]
    m = re.search(r"was label '([^']+)' more common, less common, or the same frequency before (\d{4}-\d{2}-\d{2})", q)
    if m:
        lb, cut = m.group(1), datetime.date.fromisoformat(m.group(2))
        before = [r[0] for r in rows if r[2] < cut]      # records on the cut date count on neither side
        after = [r[0] for r in rows if r[2] > cut]
        diff = before.count(lb) / len(before) - after.count(lb) / len(after)
        return ["the same frequency" if diff == 0 else "more common" if diff > 0 else "less common"]
    m = re.search(r"For how many months is the label '([^']+)' the single most frequently", q)
    if m:
        x = m.group(1)
        return [sum(1 for c in by_month(rows).values() if all(c[x] > v for k, v in c.items() if k != x))]
    m = re.search(r"For how many months does the label '([^']+)' occur more frequently than the label '([^']+)'", q)
    if m:
        a, b = m.groups()
        return [sum(1 for c in by_month(rows).values() if c[a] > c[b])]
    m = re.search(r"In which month did the label '([^']+)' first occur more often than the label '([^']+)'", q)
    if m:
        a, b = m.groups()
        months = by_month(rows)
        first = next((ym for ym in sorted(months) if months[ym][a] > months[ym][b]), None)
        return [f"{MONTHS[first[1] - 1]} {first[0]}" if first else None]
    return None


def to_turkish(answer):
    out = []
    for a in answer:
        if isinstance(a, str) and a in TR_ANSWER:
            out.append(TR_ANSWER[a])
        elif isinstance(a, str) and re.fullmatch(r"(%s) \d{4}" % "|".join(MONTHS), a):
            name, year = a.split()
            out.append(f"{AYLAR[MONTHS.index(name)]} {year}")
        else:
            out.append(a)
    return out


# ---------------------------------------------------------------- restoring withheld text

def load_source(name, path, wanted):
    """Short hash -> (text, label) for the records the documents need. A few
    texts occur in the source more than once with different ratings;
    restore_hints.json names the line used for each of them."""
    hints_file = Path(__file__).with_name("restore_hints.json")
    hints = json.loads(hints_file.read_text()).get(name, {}) if hints_file.exists() else {}
    spec, found, labels = RESTORE[name], {}, collections.defaultdict(set)
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        rows = ((i, json.loads(line)) for i, line in enumerate(f) if line.strip())
        for i, row in rows:
            text = clean(row.get(spec["text"]))
            h = short_hash(text)
            if h in wanted and hints.get(h, i) == i:
                rating = row.get(spec["label"])
                label = spec["map"].get(int(rating)) if rating is not None else None
                if label:
                    found[h] = text
                    labels[h].add(label)
    ambiguous = [h for h, ls in labels.items() if len(ls) > 1]
    missing = wanted - set(found)
    if ambiguous or missing:
        sys.exit(f"{name}: {len(missing)} records not found and {len(ambiguous)} with conflicting labels in {path}; "
                 f"is this the file and revision listed in provenance.json?")
    return {h: (found[h], labels[h].pop()) for h in found}


def restore(doc, source):
    plan = doc["records"]
    unl, lab = [doc["header"]], [doc["header"]]
    for d, u, h in zip(plan["dates"], plan["users"], plan["text_sha256_16"]):
        text, label = source[h]
        unl.append(f"Date: {d} || User: {u} || Instance: {text}\n")
        lab.append(f"Date: {d} || User: {u} || Instance: {text} || Label: {label}\n")
    text, text_with_labels = "".join(unl) + doc["footer"], "".join(lab) + doc["footer"]
    for field, value in (("text", text), ("text_with_labels", text_with_labels)):
        if hashlib.sha256(value.encode("utf-8")).hexdigest() != doc[f"{field}_sha256"]:
            sys.exit(f"{doc['doc_id']}: restored {field} does not match its SHA-256")
    out = {k: v for k, v in doc.items() if k not in ("records", "header", "footer")}
    return {**out, "text": text, "text_with_labels": text_with_labels}


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("data", type=Path, help="the data/ folder of the release")
    ap.add_argument("--restore", action="append", default=[], metavar="SET=FILE",
                    help="original source file for a text-withheld set")
    ap.add_argument("--write", type=Path, help="save restored documents under this folder")
    a = ap.parse_args()
    sources = dict(x.split("=", 1) for x in a.restore)
    loaded = {}
    bad = checked = docs_checked = 0
    skipped = []

    for qfile in sorted(a.data.glob("**/questions.jsonl.gz")):
        dfile = qfile.with_name("documents.jsonl.gz")
        rel = qfile.parent.relative_to(a.data)
        docs = {}
        restored_out = None
        for doc in read_jsonl(dfile):
            if "records" in doc:
                name = doc["source"]
                if name not in sources:
                    skipped.append(str(rel))
                    break
                if name not in loaded:
                    wanted = set()
                    for f in a.data.glob(f"**/{name}*/**/documents.jsonl.gz"):
                        for d in read_jsonl(f):
                            wanted.update(d["records"]["text_sha256_16"])
                    loaded[name] = load_source(name, sources[name], wanted)
                doc = restore(doc, loaded[name])
                if a.write:
                    if restored_out is None:
                        (a.write / rel).mkdir(parents=True, exist_ok=True)
                        restored_out = gzip.open(a.write / rel / "documents.jsonl.gz", "wt", encoding="utf-8")
                    restored_out.write(json.dumps(doc, ensure_ascii=False) + "\n")
            rows = records(doc["text_with_labels"])
            docs[doc["doc_id"]] = rows
            docs_checked += 1
            counts = collections.Counter(r[0] for r in rows)
            stated = {k: v for k, v in doc["label_counts"].items() if v}
            if len(rows) != doc["n_records"] or dict(counts) != stated:
                bad += 1
                print(f"MISMATCH {doc['doc_id']}: record lines or label counts differ from the stated values")
            if strip_labels(doc["text_with_labels"]) != doc["text"]:
                bad += 1
                print(f"MISMATCH {doc['doc_id']}: unlabelled text is not the labelled text without labels")
        if restored_out:
            restored_out.close()
        if str(rel) in skipped:
            continue
        for q in read_jsonl(qfile):
            got = recompute(q["question_en"], docs[q["doc_id"]])
            gold = [str(x) for x in q["answer_en"]]
            ok = got is not None and None not in got and sorted(gold) == sorted(str(x) for x in got)
            if q["language"] == "tr":
                ok = ok and q["answer"] == to_turkish(q["answer_en"])
            checked += 1
            if not ok:
                bad += 1
                print(f"MISMATCH {q['uid']}: {q['question_en'][:100]} gold={gold} recomputed={got}")

    for s in sorted(set(skipped)):
        print(f"skipped {s}: text withheld; pass --restore with the original source file")
    print(f"{docs_checked} documents and {checked} answers checked, {bad} disagreements")
    return 1 if bad or not checked else 0


if __name__ == "__main__":
    sys.exit(main())
