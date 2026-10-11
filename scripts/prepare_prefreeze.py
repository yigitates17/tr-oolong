"""Prepare a private, source-disjoint review candidate without touching v0.10.

Existing source pools and pair eligibility were examined during development.
The partitions reserve text for PROSPECTIVE evaluation; they cannot undo that
history or establish pretraining decontamination. Exact normalized duplicates
are grouped globally, and MASSIVE translations are joined before partitioning.
"""
import argparse
from collections import Counter
import dataclasses
import hashlib
import json
from pathlib import Path
import sys

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from build_tr_oolong import Config, clean, load_source, normalize_for_dedup

SETS = ["amazon_hpc_en", "en_intent", "en_intent_paired", "interpress_tr",
        "marc_en", "musteri_tr", "sikayet_tr", "sinema_tr", "tr_intent",
        "tr_intent_paired", "vitamins_tr"]


def fingerprint(text, lang):
    return hashlib.sha256((lang + ":" + normalize_for_dedup(text, lang)).encode()).hexdigest()


def prepare(root):
    root.mkdir(parents=True, exist_ok=True)
    if (root / "preparation.json").exists():
        raise SystemExit("Candidate already prepared; use a new --out to preserve annotations.")
    for part in ("sources", "configs/dev", "configs/test", "reports"):
        (root / part).mkdir(parents=True, exist_ok=True)
    configs = {s: Config.load(str(ROOT / "configs" / f"{s}.json")) for s in SETS}
    frames, report = {}, {}
    for s, cfg in configs.items():
        stats = {}
        representative = clean(load_source(cfg), dataclasses.replace(cfg, drop_label_leakage=False), stats)
        filtered = clean(load_source(cfg), cfg, {})
        before = Counter(representative["label"].to_list())
        after = Counter(filtered["label"].to_list())
        frames[s] = representative
        report[s] = {"raw_source_sha256": hashlib.sha256(Path(cfg.source_path).read_bytes()).hexdigest(),
                     "cleaning": stats, "rows_without_keyword_filter": representative.height,
                     "rows_with_keyword_filter": filtered.height,
                     "by_label": {l: {"retained_without": n, "retained_with": after[l]}
                                  for l, n in sorted(before.items())}}
        print(s, representative.height, filtered.height, flush=True)

    # Union normalized duplicate text with its translation's group. Using a
    # stable canonical root also keeps identical texts across source corpora
    # on the same side of the split.
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)
    raw = {}
    for lang in ("tr", "en"):
        source = pl.read_parquet(ROOT / f"datasets/massive_{lang}.parquet")
        raw[lang] = {r["pair_id"]: r for r in source.to_dicts()}
    for pid in sorted(raw["tr"].keys() & raw["en"].keys()):
        union(fingerprint(raw["tr"][pid]["utt"], "tr"), fingerprint(raw["en"][pid]["utt"], "en"))

    # Preserve the SAME rows in both intent languages after local cleaning.
    by_lang = {}
    for lang in ("tr", "en"):
        by_lang[lang] = {normalize_for_dedup(r["text"], lang): r
                        for r in frames[f"{lang}_intent"].to_dicts()}
    aligned = {"tr": [], "en": []}
    used = {"tr": set(), "en": set()}
    for pid in sorted(raw["tr"].keys() & raw["en"].keys()):
        norms = {l: normalize_for_dedup(raw[l][pid]["utt"], l) for l in ("tr", "en")}
        if any(norms[l] not in by_lang[l] or norms[l] in used[l] for l in norms):
            continue
        if by_lang["tr"][norms["tr"]]["label"] != by_lang["en"][norms["en"]]["label"]:
            continue
        for l in norms:
            aligned[l].append(by_lang[l][norms[l]])
            used[l].add(norms[l])
    for l in aligned:
        frame = pl.DataFrame(aligned[l]).drop("row_id").with_row_index("row_id")
        frames[f"{l}_intent"] = frames[f"{l}_intent_paired"] = frame

    membership = {"dev": set(), "test": set()}
    for s, frame in frames.items():
        cfg = configs[s]
        hashes = [find(fingerprint(t, cfg.language)) for t in frame["text"].to_list()]
        # 10% reserved for development; deterministic independently of labels.
        is_dev = [int(hashlib.sha256(("prefreeze-split-v1:" + h).encode()).hexdigest(), 16) % 10 == 0
                  for h in hashes]
        report[s]["split_counts"] = {}
        for split in ("dev", "test"):
            mask = [x if split == "dev" else not x for x in is_dev]
            selected = frame.filter(pl.Series(mask)).select("text", "label", "entity")
            source = root / "sources" / f"{s}_{split}.parquet"
            selected.write_parquet(source)
            membership[split].update(h for h, keep in zip(hashes, mask) if keep)
            report[s]["split_counts"][split] = selected.height
            c = dataclasses.asdict(cfg)
            c.update(source_path=str(source), text_col="text", label_col="label", entity_col="entity",
                     dataset=s, out_dir=str(root / split / f"{s}_out"), seed=20261007 if split == "test" else 20261006,
                     drop_label_leakage=False, lvl_same_tol=0.0, label_translation={},
                     strip_html=False, drop_text_regex=[], boilerplate_keywords=[], min_class_support=0)
            # Already cleaned, but deterministic de-duplication is still checked.
            if split == "dev":
                c.update(haystack_target_tokens=[], haystack_target_records=[250, 500],
                         haystacks_per_length=2, core_doc_records=[], core_docs_per_tier=0, drop_tiers=[])
            path = root / "configs" / split / f"{s}.json"
            path.write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
    assert not membership["dev"] & membership["test"]
    # Preservation evidence for the currently published release.
    published = {}
    for p in sorted((ROOT / "hf_release").glob("*/*.json*")):
        published[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    payload = {"status": "review_candidate_not_frozen", "partition": "10% development / 90% prospective test",
               "limitation": "Source pools and eligibility were previously inspected; not a historically untouched test set. Near-duplicates are audited separately.",
               "keyword_policy": "Retain natural topic words; keep existing upstream source selection and explicit-rating/boilerplate cleaning.",
               "normalized_group_overlap": len(membership["dev"] & membership["test"]),
               "published_sha256": published, "datasets": report}
    (root / "preparation.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print("Prepared", root, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("scratch/prefreeze"))
    prepare(parser.parse_args().out)
