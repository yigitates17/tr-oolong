"""Label the pre-freeze review sheets: blind first, then see the source label.

For each record you choose a label without seeing the source label. The tool
then reveals the source label. If yours matches, it moves on. If not, you say
who is right. The blind answer is what measures label quality (seeing a label
first inflates agreement); the verdict after the reveal says whether a
disagreement is a source error or an ambiguous text.

Writes `human_label` (blind), `notes`, `after_reveal` and `revised_after_reveal`
into review_tr.csv / review_en.csv, saving after every answer, and resumes at
the first unlabeled row.

    .venv/bin/python scripts/label_tool.py                 # Turkish sheet
    .venv/bin/python scripts/label_tool.py --sheet en      # English sheet
    .venv/bin/python scripts/label_tool.py --dataset sikayet_tr
    .venv/bin/python scripts/label_tool.py --skip interpress_tr

Blind step:
    3            choose label 3
    3 ; text     choose label 3 and keep a note
    u            uncertain: the text does not determine one label
    taxi         list only the labels containing "taxi" (numbers stay the same)
    s            skip for now
    q            save and quit

After the reveal (only when you disagreed or were uncertain):
    s            the source label is right (I misread)
    m            my label is right; the source label is wrong
    b            both are plausible; the text is ambiguous
    n            (after uncertain) still cannot tell from the text
    z            I mistyped; redo my label (recorded as revised)
"""
import argparse
import csv
import json
import os
import shutil
import textwrap
from pathlib import Path

SENTIMENT_ORDER = ["olumsuz", "nötr", "olumlu", "negative", "neutral", "positive"]
EXTRA_FIELDS = ["after_reveal", "revised_after_reveal"]
VERDICTS = {"s": "source_right", "m": "source_wrong", "b": "ambiguous", "n": "still_uncertain"}


def load(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames) + [x for x in EXTRA_FIELDS if x not in reader.fieldnames]
        rows = [{k: r.get(k) or "" for k in fields} for r in reader]
    return fields, rows


def save(path, fields, rows):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def label_menu(available):
    labels = [x.strip() for x in available.split("|") if x.strip() and x.strip() != "uncertain"]
    if all(x in SENTIMENT_ORDER for x in labels):
        labels.sort(key=SENTIMENT_ORDER.index)
    return labels


def show_labels(labels, only=None):
    width = shutil.get_terminal_size((100, 30)).columns
    items = [f"{i:>2} {lab}" for i, lab in enumerate(labels, 1) if only is None or lab in only]
    col = max(len(s) for s in items) + 3
    per_line = max(1, width // col)
    for k in range(0, len(items), per_line):
        print("".join(s.ljust(col) for s in items[k:k + per_line]))
    print(" u uncertain")


def progress(rows, dataset):
    done = sum(1 for r in rows if r["human_label"].strip())
    in_set = [r for r in rows if r["dataset"] == dataset]
    set_done = sum(1 for r in in_set if r["human_label"].strip())
    return f"{done}/{len(rows)} overall · {dataset} {set_done}/{len(in_set)}"


def show_record(row, rows, tasks, width, last):
    print("\033[2J\033[H", end="")
    if last:
        print(last, "\n")
    print(f"[{progress(rows, row['dataset'])}]  {row['dataset']}  id {row['review_id']}")
    print(textwrap.fill(tasks.get(row["dataset"], ""), width), "\n")
    for para in row["text"].splitlines() or [""]:
        print(textwrap.fill(para, width))
    print()


def blind_label(row, labels, rows, tasks, width, last):
    """Returns (label, note), or 'q' / 's'."""
    only = None
    while True:
        show_record(row, rows, tasks, width, last)
        show_labels(labels, only)
        choice, _, note = (x.strip() for x in input("> ").strip().partition(";"))
        if choice in ("q", "s"):
            return choice
        if choice == "u":
            return "uncertain", note
        if choice.isdigit() and 1 <= int(choice) <= len(labels):
            return labels[int(choice) - 1], note
        only = [lab for lab in labels if choice and choice.lower() in lab.lower()] or None


def reveal(row, source, rows, tasks, width):
    """Returns a verdict code, or 'z' to redo the blind label."""
    allowed = "snz" if row["human_label"] == "uncertain" else "smbz"
    while True:
        show_record(row, rows, tasks, width, "")
        print(f"your label:   {row['human_label']}")
        print(f"source label: {source}\n")
        if row["human_label"] == "uncertain":
            print(" s  source label fits, now that I see it")
            print(" n  still cannot tell from the text")
        else:
            print(" s  source is right (I misread)")
            print(" m  mine is right; source is wrong")
            print(" b  both plausible; text is ambiguous")
        print(" z  I mistyped; redo my label")
        ans = input("> ").strip().lower()
        if ans in allowed:
            return ans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("scratch/prefreeze/human_review"))
    ap.add_argument("--sheet", choices=["tr", "en"], default="tr")
    ap.add_argument("--dataset", help="label only this subset")
    ap.add_argument("--skip", nargs="+", default=[], help="leave these subsets unlabeled")
    args = ap.parse_args()

    path = args.root / f"review_{args.sheet}.csv"
    fields, rows = load(path)
    tasks = json.loads((args.root / "task_definitions.json").read_text(encoding="utf-8"))
    key = json.loads((args.root / "private_key.json").read_text(encoding="utf-8"))
    selected = lambda r: (not args.dataset or r["dataset"] == args.dataset) and r["dataset"] not in args.skip
    todo = [r for r in rows if not r["human_label"].strip() and selected(r)]
    width = min(100, shutil.get_terminal_size((100, 30)).columns)
    last = ""

    for row in todo:
        labels = label_menu(row["available_labels"])
        source = key[row["review_id"]]["source_label"]
        revised = False
        while True:
            got = blind_label(row, labels, rows, tasks, width, last)
            if got == "q":
                save(path, fields, rows)
                print(f"Saved. {progress(rows, row['dataset'])}")
                return
            if got == "s":
                break
            row["human_label"], note = got
            if note:
                row["notes"] = note
            row["revised_after_reveal"] = "yes" if revised else ""
            if row["human_label"] == source:
                row["after_reveal"] = "match"
                last = f"previous: match ({source})"
            else:
                verdict = reveal(row, source, rows, tasks, width)
                if verdict == "z":
                    row["human_label"] = ""
                    revised = True
                    continue
                row["after_reveal"] = VERDICTS[verdict]
                last = f"previous: yours {row['human_label']}, source {source}, {VERDICTS[verdict]}"
            save(path, fields, rows)
            break
    save(path, fields, rows)
    left = sum(1 for r in rows if not r["human_label"].strip() and selected(r))
    print(f"End of sheet. {left} rows in this selection still unlabeled.")


if __name__ == "__main__":
    main()
