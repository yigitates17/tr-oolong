"""Native-speaker check of XNLI's Turkish translation, one pair at a time.

Shows each English pair, its Turkish translation and the English label, and
asks how good the translation is and whether the label still holds for the
Turkish text. The 50 pairs are the same random sample Claude judged
(notes/xnli_translation_check.md); those verdicts are not shown here.

    .venv/bin/python scripts/xnli_check.py

At the prompt:
    1            fine: same meaning, natural Turkish
    2            awkward: literal or clumsy, but the meaning is kept
    3            wrong: the meaning changed
    2 ; text     any answer can carry a note after ";"
    q            save and quit (it resumes where you stopped)
After 2 or 3 it asks whether the English label still holds for the Turkish
pair (y / n). Saves after every answer to
scratch/prefreeze/human_review_xnli/xnli_check.csv.
"""
import csv
import os
import random
import shutil
import textwrap
from pathlib import Path

import polars as pl

OUT = Path("scratch/prefreeze/human_review_xnli/xnli_check.csv")
FIELDS = ["n", "pair_id", "label", "en", "tr", "quality", "label_holds", "notes"]
QUALITY = {"1": "fine", "2": "awkward", "3": "wrong"}


def make_sheet():
    tr = pl.read_parquet("datasets/xnli_tr.parquet")
    en = pl.read_parquet("datasets/xnli_en.parquet")
    idx = sorted(random.Random("xnli-translation-check").sample(range(tr.height), 50))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"n": k, "pair_id": tr["pair_id"][i], "label": tr["label"][i], "en": en["text"][i],
             "tr": tr["text"][i], "quality": "", "label_holds": "", "notes": ""}
            for k, i in enumerate(idx, 1)]
    save(rows)


def save(rows):
    tmp = OUT.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, OUT)


def main():
    if not OUT.exists():
        make_sheet()
    with open(OUT, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    width = min(100, shutil.get_terminal_size((100, 30)).columns)
    for row in rows:
        if row["quality"]:
            continue
        while True:
            done = sum(1 for r in rows if r["quality"])
            print("\033[2J\033[H", end="")
            print(f"[{done}/{len(rows)}]  pair {row['n']}  label: {row['label']}\n")
            for name in ("en", "tr"):
                print(name.upper() + ":")
                for part in row[name].split(" -> "):
                    print(textwrap.fill(part, width, initial_indent="  ", subsequent_indent="  "))
                print()
            print(" 1 fine   2 awkward (meaning kept)   3 wrong (meaning changed)   q quit")
            choice, _, note = (x.strip() for x in input("> ").partition(";"))
            if choice == "q":
                save(rows)
                print(f"Saved. {done}/{len(rows)} done.")
                return
            if choice not in QUALITY:
                continue
            holds = "y"
            if choice in ("2", "3"):
                while (holds := input(f"Does '{row['label']}' still hold for the Turkish pair? y/n > ").strip().lower()) not in ("y", "n"):
                    pass
            row["quality"], row["label_holds"] = QUALITY[choice], holds
            if note:
                row["notes"] = note
            save(rows)
            break
    print(f"All {len(rows)} pairs done. Results in {OUT}")


if __name__ == "__main__":
    main()
