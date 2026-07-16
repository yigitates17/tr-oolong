"""
build_tr_oolong.py -- TR-OOLONG benchmark constructor (v0.2.0)

Label-derived long-context AGGREGATION benchmark builder, following the
OOLONG-synth recipe (Bertsch et al., 2025): concatenate labeled examples into a
controlled-length haystack and auto-generate distributional questions whose
ground truth is computed exactly from the source labels. The label never
appears verbatim in the text, so nothing is grep-solvable.

Design guarantees preserved from v0.1 (do not remove):
  * Every question requires the LATENT LABEL, never surface string matching.
  * Ground truth is computed by two independent code paths (Polars + pure
    Python) and asserted equal -- differential testing, extended to every family.
  * All randomness flows from a single readable string seed; a manifest records
    seed, config, source hash, tokenizer, and the realized question distribution.
  * ONE reference tokenizer per axis measures every reported length.
  * Config-driven: a new axis or the matched twin is a config file, not a script.
  * Turkish-safe casefolding (I->i, I-with-dot->i) and the combining-dot repair.

What v0.2.0 fixes / adds versus v0.1:
  1. Drift survives trimming: fit-to-budget FIRST, then apply the 30/70 ordering
     to the kept rows, then assert shift detectability (loud, never silent).
  2. Shift answers are language-mapped (rose/fell -> artti/azaldi) and validated.
  3. entity_count samples the label first, then an entity with a non-degenerate
     count -- no more starvation on many-class axes.
  4. Stratified per-family quotas replace uniform rng.choice; realized
     distribution is written to the manifest.
  5. proportion switches to per-mille on axes with >10 labels (auto), so the
     0.75^|y-yhat| metric keeps signal; the unit is recorded per question.
  6. Readable string-seeded RNG (deterministic under PYTHONHASHSEED salting).
  7. drift_target persisted; token estimate is separator-aware.
  8. Normalized output: haystacks.jsonl (id -> text) + questions.jsonl, so the
     haystack is stored once, not once per question.
  + Two new families: top_k (ordered) and pairwise (comparison), both dual-path.

Usage:
    python build_tr_oolong.py --config tr_intent.json --audit
    python build_tr_oolong.py --config tr_intent.json --build
    python build_tr_oolong.py --init            # writes an example config
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import platform
import random
import re
import sys
import unicodedata
from collections import Counter
from importlib.metadata import version as pkg_version
from datetime import date
from pathlib import Path
from typing import Callable

import polars as pl

VERSION = "0.2.1"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class Config:
    # source data
    source_path: str
    text_col: str = "utt"
    label_col: str = "intent"
    entity_col: str = "scenario"          # "" if the axis has no entity dimension
    language: str = "tr"                  # "tr" or "en"
    # cleaning
    min_words: int = 1
    max_words: int = 400
    # haystack construction
    seed: int = 42
    haystack_target_tokens: list[int] = dataclasses.field(
        default_factory=lambda: [50_000, 100_000]
    )
    haystacks_per_length: int = 5         # >=5 -> ~50 questions per (length x axis)
    questions_per_haystack: int = 12
    separator: str = "\n\n<<<KAYIT>>>\n\n"
    drift_mode: bool = True
    min_entity_examples: int = 8
    dirichlet_alpha: float = 0.0          # >0: per-haystack Dirichlet label priors
    # question families
    proportion_unit: str = "auto"         # "auto" | "percent" | "per_mille"
    top_k_k: int = 3
    question_templates: dict[str, str] = dataclasses.field(default_factory=dict)
    # tokenizer
    reference_tokenizer: str = ""         # e.g. "Qwen/Qwen3-8B"; empty -> char approx
    chars_per_token: float = 3.4
    # output
    out_dir: str = "tr_oolong_out"

    @staticmethod
    def load(path: str) -> "Config":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        known = {f.name for f in dataclasses.fields(Config)}
        dropped = sorted(set(raw) - known)
        if dropped:
            print(f"[config] ignoring unknown keys: {dropped}", file=sys.stderr)
        return Config(**{k: v for k, v in raw.items() if k in known})


# ---------------------------------------------------------------------------
# Reference tokenizer -- one per axis, recorded in the manifest
# ---------------------------------------------------------------------------

def make_token_counter(cfg: Config) -> Callable[[str], int]:
    if cfg.reference_tokenizer:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(cfg.reference_tokenizer)
        return lambda s: len(tok.encode(s, add_special_tokens=False))
    cpt = cfg.chars_per_token
    return lambda s: max(1, round(len(s) / cpt))


# ---------------------------------------------------------------------------
# Turkish-safe normalization
# ---------------------------------------------------------------------------

def tr_casefold(s: str) -> str:
    """Casefold respecting Turkish dotless-i: 'I' -> 'i-dotless', dotted-I -> 'i'."""
    return s.replace("I", "\u0131").replace("\u0130", "i").lower()


def normalize_for_dedup(s: str, language: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = tr_casefold(s) if language == "tr" else s.casefold()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^\w\s]", "", s)
    return s


# ---------------------------------------------------------------------------
# Load + clean
# ---------------------------------------------------------------------------

def load_source(cfg: Config) -> pl.DataFrame:
    p = Path(cfg.source_path)
    if p.suffix in (".jsonl", ".ndjson"):
        df = pl.read_ndjson(p)          # e.g. OOLONG validated splits: {"input","label"}
    elif p.suffix == ".parquet":
        df = pl.read_parquet(p)
    else:
        df = pl.read_csv(p)
    keep = [cfg.text_col, cfg.label_col] + ([cfg.entity_col] if cfg.entity_col else [])
    df = df.select(keep).drop_nulls()
    df = df.rename({cfg.text_col: "text", cfg.label_col: "label"})
    if cfg.entity_col:
        df = df.rename({cfg.entity_col: "entity"})
    else:
        df = df.with_columns(pl.lit("__none__").alias("entity"))
    return df


def clean(df: pl.DataFrame, cfg: Config) -> pl.DataFrame:
    df = df.with_columns(
        pl.col("text").str.replace_all(r"\s+", " ").str.strip_chars().alias("text"),
        pl.col("label").str.strip_chars().str.to_lowercase().alias("label"),
        pl.col("entity").cast(pl.Utf8).str.strip_chars().alias("entity"),
    )
    # repair the combining-dot artifact (i followed by U+0307)
    df = df.with_columns(pl.col("text").str.replace_all("i\u0307", "i").alias("text"))
    df = df.with_columns(
        pl.col("text").str.split(" ").list.len().alias("n_words"),
        pl.col("text")
        .map_elements(lambda t: normalize_for_dedup(t, cfg.language), return_dtype=pl.Utf8)
        .alias("_norm"),
    )
    df = df.filter(
        pl.col("n_words").is_between(cfg.min_words, cfg.max_words)
        & ~pl.col("text").str.contains(re.escape(cfg.separator.strip()), literal=False)
    )
    df = df.filter(~pl.col("label").str.contains(",") & ~pl.col("entity").str.contains(","))
    df = df.unique(subset=["_norm"], keep="first", maintain_order=True).drop("_norm")
    return df.with_row_index("row_id")


# ---------------------------------------------------------------------------
# Proportion unit resolution
# ---------------------------------------------------------------------------

def resolve_proportion_unit(cfg: Config, n_label_space: int) -> str:
    if cfg.proportion_unit in ("percent", "per_mille"):
        return cfg.proportion_unit
    return "per_mille" if n_label_space > 10 else "percent"


PROP_SCALE = {"percent": 100, "per_mille": 1000}


# ---------------------------------------------------------------------------
# Audit mode
# ---------------------------------------------------------------------------

def audit(df: pl.DataFrame, cfg: Config, count_tokens: Callable[[str], int]) -> None:
    n = df.height
    labels = df.group_by("label").len().sort("len", descending=True)
    entities = df.group_by("entity").len().sort("len", descending=True)
    askable = entities.filter(pl.col("len") >= cfg.min_entity_examples)
    sample = df.sample(min(n, 500), seed=0)["text"]
    mean_tok = sum(count_tokens(t) for t in sample) / len(sample)
    sep_tok = count_tokens(cfg.separator)
    unit = resolve_proportion_unit(cfg, labels.height)
    print(f"rows after cleaning        : {n}")
    print(f"label space                : {labels.height} classes")
    print(f"entities total / askable   : {entities.height} / {askable.height}")
    print(f"mean tokens/example + sep  : {mean_tok:.1f} + {sep_tok} (reference tokenizer)")
    print(f"proportion unit            : {unit}")
    for tgt in cfg.haystack_target_tokens:
        need = round(tgt / (mean_tok + sep_tok))
        ok = "OK" if need <= n else "NOT ENOUGH DATA"
        print(f"  haystack {tgt:>7,} tokens ~ {need:>6,} examples  [{ok}]")
    noise = df.sample(min(n, 200), seed=1).select("row_id", "text", "label", "entity")
    out = Path(cfg.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    noise.write_csv(out / "label_noise_slice.csv")
    print(f"wrote 200-row self-annotation slice -> {out / 'label_noise_slice.csv'}")


# ---------------------------------------------------------------------------
# Haystack assembly: fit-to-budget FIRST, then drift-order the kept rows
# ---------------------------------------------------------------------------

def draw_label_weights(pool_labels: list[str], alpha: float, rng: random.Random) -> dict[str, float]:
    """Per-haystack label priors: Dirichlet(alpha) target shares, converted to
    per-row weights (divide by pool count so the target share is met regardless
    of how skewed the pool is)."""
    counts = Counter(pool_labels)
    g = {l: rng.gammavariate(alpha, 1.0) for l in sorted(counts)}
    z = sum(g.values())
    return {l: (g[l] / z) / counts[l] for l in counts}


def sample_candidate_rows(df: pl.DataFrame, need: int, rng: random.Random,
                          label_weights: dict[str, float] | None = None) -> pl.DataFrame:
    k = min(need, df.height)
    if label_weights is None:
        idx = rng.sample(range(df.height), k)
        return df[idx]
    # Efraimidis-Spirakis A-Res: weighted sampling without replacement via
    # u**(1/w) keys; top-k keys are the sample, key order is the neutral order.
    labels = df["label"].to_list()
    # exponential-race form of the same keys: rank by -Exp(1)/w instead of
    # u**(1/w), which underflows to 0.0 for the tiny per-row weights of large pools
    keyed = sorted(((-rng.expovariate(1.0) / label_weights[l], i)
                    for i, l in enumerate(labels)), reverse=True)
    return df[[i for _, i in keyed[:k]]]


def select_rows_to_fit(
    cand: pl.DataFrame, target: int, count_tokens: Callable[[str], int], sep: str
) -> pl.DataFrame:
    """Greedily keep candidate rows (neutral order) until the token budget is hit.
    No drift ordering here -- so nothing drift-relevant can be trimmed later."""
    sep_tok = count_tokens(sep)
    total = 0
    kept = 0
    for text in cand["text"]:
        cost = count_tokens(text) + (sep_tok if kept > 0 else 0)
        if total + cost > target and kept > 0:
            break
        total += cost
        kept += 1
    return cand.head(kept)


def eligible_drift_targets(kept: pl.DataFrame, min_share: float = 0.03) -> list[str]:
    counts = Counter(kept["label"].to_list())
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [l for l, c in ranked if c / kept.height >= min_share]


def order_and_assemble(
    kept: pl.DataFrame,
    drift_target: str | None,
    cfg: Config,
    count_tokens: Callable[[str], int],
    rng: random.Random,
) -> tuple[str, pl.DataFrame]:
    """Order the ALREADY-FITTED rows (optionally with a 30/70 drift split), then
    concatenate and record char spans + half + drift_target."""
    n = kept.height
    if drift_target is None:
        order = list(range(n))
        rng.shuffle(order)
        boundary = n // 2
    else:
        lbls = kept["label"].to_list()
        tgt = [i for i in range(n) if lbls[i] == drift_target]
        oth = [i for i in range(n) if lbls[i] != drift_target]
        rng.shuffle(tgt)
        rng.shuffle(oth)
        h0 = n // 2
        share = rng.choice((0.3, 0.7))               # drift direction randomized per haystack
        cut = max(1, min(h0 - 1, round(len(tgt) * share)))
        first = tgt[:cut] + oth[: h0 - cut]          # exactly h0 rows when others suffice
        second = tgt[cut:] + oth[h0 - cut:]
        rng.shuffle(first)
        rng.shuffle(second)
        order = first + second
        boundary = len(first)                        # half label follows the real split

    ordered = kept[order]
    sep = cfg.separator
    parts: list[str] = []
    spans: list[tuple[int, int]] = []
    pos = 0
    for i, text in enumerate(ordered["text"]):
        if i > 0:
            parts.append(sep)
            pos += len(sep)
        start = pos
        parts.append(text)
        pos += len(text)
        spans.append((start, pos))
    hay = "".join(parts)
    meta = ordered.with_columns(
        pl.Series("char_start", [s for s, _ in spans]),
        pl.Series("char_end", [e for _, e in spans]),
        pl.Series("half", [0 if i < boundary else 1 for i in range(ordered.height)]),
        pl.lit(drift_target if drift_target is not None else "__none__").alias("drift_target"),
    )
    return hay, meta


# ---------------------------------------------------------------------------
# Question templates -- config overrides the 5 base families; script owns the rest
# ---------------------------------------------------------------------------

Q_TEMPLATES = {
    "tr": {
        "count": "Bu kayıtlarda kaç tane '{label}' etiketli kayıt var? Sadece sayıyı yaz.",
        "proportion_percent": "Kayıtların yüzde kaçı '{label}' etiketli? En yakın tam sayıya yuvarla, sadece sayıyı yaz.",
        "proportion_per_mille": "Kayıtların binde kaçı '{label}' etiketli? En yakın tam sayıya yuvarla, sadece sayıyı yaz.",
        "entity_count": "'{entity}' grubundaki kayıtlardan kaç tanesi '{label}' etiketli? Sadece sayıyı yaz.",
        "entity_argmax": "En çok '{label}' etiketli kayıt hangi grupta var? Sadece grup adını yaz.",
        "shift": "Kayıtların ikinci yarısında '{label}' etiketli kayıtların oranı ilk yarıya göre arttı mı azaldı mı? 'artti' veya 'azaldi' yaz.",
        "top_k": "En çok '{label}' etiketli kayıt içeren ilk {k} grup hangileri? Çoktan aza doğru, aralarına ' > ' koyarak yaz.",
        "pairwise": "'{label}' etiketli kayıt hangisinde daha çok: '{entity_a}' mı yoksa '{entity_b}' mi? Sadece grup adını yaz.",
        "most_common": "Bu kayıtlarda en sık görülen etiket hangisi? Sadece etiket adını yaz.",
        "least_common": "Bu kayıtlarda en az görülen etiket hangisi? Sadece etiket adını yaz.",
        "second_most": "Bu kayıtlarda ikinci en sık görülen etiket hangisi? Sadece etiket adını yaz.",
    },
    "en": {
        "count": "How many records are labeled '{label}'? Answer with the number only.",
        "proportion_percent": "What percentage of records are labeled '{label}'? Round to the nearest integer, answer with the number only.",
        "proportion_per_mille": "How many per thousand (per-mille) of records are labeled '{label}'? Round to the nearest integer, answer with the number only.",
        "entity_count": "How many records in the '{entity}' group are labeled '{label}'? Answer with the number only.",
        "entity_argmax": "Which group contains the most records labeled '{label}'? Answer with the group name only.",
        "shift": "Did the share of '{label}' records rise or fall in the second half compared to the first? Answer 'rose' or 'fell'.",
        "top_k": "Which {k} groups contain the most records labeled '{label}'? List them from most to fewest, separated by ' > '.",
        "pairwise": "Which group has more '{label}' records: '{entity_a}' or '{entity_b}'? Answer with the group name only.",
        "most_common": "Which label is the most common in these records? Answer with the label name only.",
        "least_common": "Which label is the least common in these records? Answer with the label name only.",
        "second_most": "Which label is the second most common in these records? Answer with the label name only.",
    },
}

SHIFT_ANSWER = {
    "tr": {"rose": "artti", "fell": "azaldi"},
    "en": {"rose": "rose", "fell": "fell"},
}


def resolve_template(cfg: Config, kind: str, unit: str | None = None) -> str:
    lang = cfg.language
    if kind == "proportion":
        if unit == "percent":
            return cfg.question_templates.get("proportion") or Q_TEMPLATES[lang]["proportion_percent"]
        return Q_TEMPLATES[lang]["proportion_per_mille"]
    return cfg.question_templates.get(kind) or Q_TEMPLATES[lang][kind]


# ---------------------------------------------------------------------------
# Ground truth -- dual path (Polars primary, pure-Python check), asserted equal
# ---------------------------------------------------------------------------

def _rank_entities(meta: pl.DataFrame, label: str, askable: list[str]) -> list[tuple[str, int]]:
    """(entity, count) for the label over askable entities, sorted count desc, name asc."""
    agg = (
        meta.filter((pl.col("label") == label) & pl.col("entity").is_in(askable))
        .group_by("entity")
        .len()
        .sort(["len", "entity"], descending=[True, False])
    )
    return list(zip(agg["entity"].to_list(), agg["len"].to_list()))


def gt_primary(meta, kind, *, label=None, entity=None, entity_a=None, entity_b=None,
               unit="percent", k=3, askable=None):
    askable = askable or []
    if kind == "count":
        return str(meta.filter(pl.col("label") == label).height)
    if kind == "proportion":
        scale = PROP_SCALE[unit]
        return str(math.floor(scale * meta.filter(pl.col("label") == label).height / meta.height + 0.5))
    if kind == "entity_count":
        return str(meta.filter((pl.col("entity") == entity) & (pl.col("label") == label)).height)
    if kind == "entity_argmax":
        ranked = _rank_entities(meta, label, askable)
        if not ranked:
            return None
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            return None
        return ranked[0][0]
    if kind == "top_k":
        ranked = _rank_entities(meta, label, askable)
        if len(ranked) < k + 1:
            return None
        window = ranked[: k + 1]
        for a, b in zip(window, window[1:]):
            if a[1] == b[1]:            # any tie inside the top-(k+1) boundary -> reject
                return None
        return [e for e, _ in ranked[:k]]
    if kind == "pairwise":
        a = meta.filter((pl.col("entity") == entity_a) & (pl.col("label") == label)).height
        b = meta.filter((pl.col("entity") == entity_b) & (pl.col("label") == label)).height
        if a == 0 or b == 0 or a == b:
            return None
        return entity_a if a > b else entity_b
    if kind == "shift":
        h0 = meta.filter(pl.col("half") == 0)
        h1 = meta.filter(pl.col("half") == 1)
        s0 = h0.filter(pl.col("label") == label).height / max(1, h0.height)
        s1 = h1.filter(pl.col("label") == label).height / max(1, h1.height)
        base = meta.filter(pl.col("label") == label).height / meta.height
        if abs(s1 - s0) < max(0.5 * base, 0.02):
            return None
        return "rose" if s1 > s0 else "fell"
    if kind in ("most_common", "least_common", "second_most"):
        agg = meta.group_by("label").len().sort(["len", "label"], descending=[True, False])
        ranked = list(zip(agg["label"].to_list(), agg["len"].to_list()))
        return _label_stat(ranked, kind)
    raise ValueError(kind)


def _label_stat(ranked, kind):
    """Shared tie-rejection over a (label, count) ranking sorted count desc, name asc.
    ranked is built independently by each GT path, so the aggregation is still
    differentially tested; only this small decision rule is shared."""
    if kind == "most_common":
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            return None
        return ranked[0][0]
    if kind == "least_common":
        if len(ranked) > 1 and ranked[-1][1] == ranked[-2][1]:
            return None
        return ranked[-1][0]
    if kind == "second_most":
        if len(ranked) < 2 or ranked[0][1] == ranked[1][1]:
            return None
        if len(ranked) > 2 and ranked[1][1] == ranked[2][1]:
            return None
        return ranked[1][0]
    raise ValueError(kind)


def gt_check(meta, kind, *, label=None, entity=None, entity_a=None, entity_b=None,
             unit="percent", k=3, askable=None):
    askable = set(askable or [])
    labels = meta["label"].to_list()
    ents = meta["entity"].to_list()
    halves = meta["half"].to_list()
    if kind == "count":
        return str(sum(1 for l in labels if l == label))
    if kind == "proportion":
        scale = PROP_SCALE[unit]
        return str(math.floor(scale * sum(1 for l in labels if l == label) / len(labels) + 0.5))
    if kind == "entity_count":
        return str(sum(1 for l, e in zip(labels, ents) if l == label and e == entity))
    if kind in ("entity_argmax", "top_k"):
        c = Counter(e for l, e in zip(labels, ents) if l == label and e in askable)
        ranked = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        if kind == "entity_argmax":
            if not ranked:
                return None
            if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
                return None
            return ranked[0][0]
        if len(ranked) < k + 1:
            return None
        window = ranked[: k + 1]
        for a, b in zip(window, window[1:]):
            if a[1] == b[1]:
                return None
        return [e for e, _ in ranked[:k]]
    if kind == "pairwise":
        a = sum(1 for l, e in zip(labels, ents) if l == label and e == entity_a)
        b = sum(1 for l, e in zip(labels, ents) if l == label and e == entity_b)
        if a == 0 or b == 0 or a == b:
            return None
        return entity_a if a > b else entity_b
    if kind == "shift":
        n0 = sum(1 for h in halves if h == 0)
        n1 = len(halves) - n0
        s0 = sum(1 for l, h in zip(labels, halves) if h == 0 and l == label) / max(1, n0)
        s1 = sum(1 for l, h in zip(labels, halves) if h == 1 and l == label) / max(1, n1)
        base = sum(1 for l in labels if l == label) / len(labels)
        if abs(s1 - s0) < max(0.5 * base, 0.02):
            return None
        return "rose" if s1 > s0 else "fell"
    if kind in ("most_common", "least_common", "second_most"):
        c = Counter(labels)
        ranked = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        return _label_stat(ranked, kind)
    raise ValueError(kind)


def verified_gt(meta, kind, **kw):
    """Both paths must agree; the assertion is the benchmark's validity claim."""
    g1 = gt_primary(meta, kind, **kw)
    g2 = gt_check(meta, kind, **kw)
    if g1 != g2:
        raise ValueError(f"GT mismatch [{kind}] {kw}: {g1!r} vs {g2!r}")
    return g1


# ---------------------------------------------------------------------------
# One-question generators (each does its own rejection sampling)
# ---------------------------------------------------------------------------

def _make_one(kind, meta, cfg, rng, *, labels, askable, drift_target, unit, k):
    """Return a question dict for `kind`, or None if this draw is degenerate."""
    if kind == "count":
        label = rng.choice(labels)
        gt = verified_gt(meta, kind, label=label)
        if gt in ("0", str(meta.height)):
            return None
        return {"kind": kind, "label": label, "answer": gt,
                "question": resolve_template(cfg, kind).format(label=label)}

    if kind == "proportion":
        label = rng.choice(labels)
        gt = verified_gt(meta, kind, label=label, unit=unit)
        if gt in ("0", str(PROP_SCALE[unit])):
            return None
        return {"kind": kind, "label": label, "answer": gt, "unit": unit,
                "question": resolve_template(cfg, kind, unit).format(label=label)}

    if kind == "entity_count":
        # Bug 3 fix: pick the label first, then an entity with a non-degenerate count.
        label = rng.choice(labels)
        pool = (
            meta.filter((pl.col("label") == label) & pl.col("entity").is_in(askable))
            .group_by("entity").len()
        )
        valid = []
        for e, c in zip(pool["entity"].to_list(), pool["len"].to_list()):
            total = meta.filter(pl.col("entity") == e).height
            if 0 < c < total:
                valid.append(e)
        if not valid:
            return None
        entity = rng.choice(sorted(valid))
        gt = verified_gt(meta, kind, label=label, entity=entity)
        return {"kind": kind, "label": label, "entity": entity, "answer": gt,
                "question": resolve_template(cfg, kind).format(label=label, entity=entity)}

    if kind == "entity_argmax":
        label = rng.choice(labels)
        gt = verified_gt(meta, kind, label=label, askable=askable)
        if gt is None:
            return None
        return {"kind": kind, "label": label, "answer": gt,
                "question": resolve_template(cfg, kind).format(label=label)}

    if kind == "top_k":
        label = rng.choice(labels)
        gt = verified_gt(meta, kind, label=label, k=k, askable=askable)
        if gt is None:
            return None
        return {"kind": kind, "label": label, "k": k, "answer": gt,
                "answer_display": " > ".join(gt),
                "question": resolve_template(cfg, kind).format(label=label, k=k)}

    if kind == "pairwise":
        label = rng.choice(labels)
        if len(askable) < 2:
            return None
        entity_a, entity_b = rng.sample(askable, 2)
        gt = verified_gt(meta, kind, label=label, entity_a=entity_a, entity_b=entity_b)
        if gt is None:
            return None
        return {"kind": kind, "label": label, "entity_a": entity_a, "entity_b": entity_b,
                "answer": gt,
                "question": resolve_template(cfg, kind).format(
                    label=label, entity_a=entity_a, entity_b=entity_b)}

    if kind == "shift":
        label = drift_target
        gt = verified_gt(meta, kind, label=label)
        if gt is None:
            return None
        answer = SHIFT_ANSWER[cfg.language][gt]
        return {"kind": kind, "label": label, "answer": answer,
                "question": resolve_template(cfg, kind).format(label=label)}

    if kind in ("most_common", "least_common", "second_most"):
        gt = verified_gt(meta, kind)
        if gt is None:
            return None
        return {"kind": kind, "label": None, "answer": gt,
                "question": resolve_template(cfg, kind)}

    raise ValueError(kind)


def _dedup_key(q: dict) -> tuple:
    if q["kind"] == "pairwise":
        return ("pairwise", q["label"], frozenset((q["entity_a"], q["entity_b"])))
    if q["kind"] == "entity_count":
        return ("entity_count", q["label"], q["entity"])
    return (q["kind"], q["label"])


def SINGLETON_FAMILIES():
    return ("shift", "most_common", "least_common", "second_most")


def allocate_quota(families: list[str], total: int) -> dict[str, int]:
    """Even split across available families; remainder to count/proportion.
    Singleton families (shift + the label-distribution one-shots) are capped at 1
    because only one such question exists per haystack."""
    quota = {f: 0 for f in families}
    base, rem = divmod(total, len(families))
    for f in families:
        quota[f] = base
    priority = [f for f in ("count", "proportion", "entity_argmax", "top_k",
                            "entity_count", "pairwise") if f in families]
    i = 0
    while rem > 0 and priority:
        quota[priority[i % len(priority)]] += 1
        rem -= 1
        i += 1
    for f in SINGLETON_FAMILIES():             # collapse each singleton to <=1, spill rest
        if f in quota and quota[f] > 1:
            spill = quota[f] - 1
            quota[f] = 1
            for _ in range(spill):
                quota[priority[i % len(priority)]] += 1
                i += 1
    return quota


def generate_questions(meta, cfg, rng, *, drift_target, unit, k):
    labels = sorted(meta["label"].unique().to_list())
    askable = sorted(
        meta.group_by("entity").len()
        .filter((pl.col("len") >= cfg.min_entity_examples) & (pl.col("entity") != "__none__"))
        ["entity"].to_list()
    )
    families = ["count", "proportion", "most_common", "least_common", "second_most"]
    if drift_target is not None:
        families.append("shift")
    # Entity-relational families are only meaningful when the entity axis is
    # ORTHOGONAL to the label (some label spans >=2 askable entities). On a NESTED
    # axis -- e.g. MASSIVE intent within scenario -- entity_argmax/entity_count are
    # trivial and top_k/pairwise are impossible, so we omit them entirely.
    entity_relational = False
    if askable:
        span = (
            meta.filter(pl.col("entity").is_in(askable))
            .group_by("label").agg(pl.col("entity").n_unique().alias("ne"))
        )
        entity_relational = (span.height > 0) and (span["ne"].max() >= 2)
    if entity_relational:
        families += ["entity_count", "entity_argmax"]
        if len(askable) >= 2:
            families.append("pairwise")
        if len(askable) >= k + 1:
            families.append("top_k")

    quota = allocate_quota(families, cfg.questions_per_haystack)
    seen: set[tuple] = set()
    out: list[dict] = []

    def fill(kind: str, n: int, attempt_budget: int) -> int:
        got = 0
        attempts = 0
        while got < n and attempts < attempt_budget:
            attempts += 1
            q = _make_one(kind, meta, cfg, rng, labels=labels, askable=askable,
                          drift_target=drift_target, unit=unit, k=k)
            if q is None:
                continue
            key = _dedup_key(q)
            if key in seen:
                continue
            seen.add(key)
            out.append(q)
            got += 1
        return got

    # first pass: hit each family's quota
    for kind, n in quota.items():
        fill(kind, n, attempt_budget=40 * max(1, n))
    # spill pass: top up any shortfall with count/proportion (large sampling space)
    shortfall = cfg.questions_per_haystack - len(out)
    for kind in ("count", "proportion"):
        if shortfall <= 0:
            break
        shortfall -= fill(kind, shortfall, attempt_budget=60 * max(1, shortfall))
    return out


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(cfg: Config) -> None:
    count_tokens = make_token_counter(cfg)
    df = clean(load_source(cfg), cfg)
    n_label_space = df.select(pl.col("label").n_unique()).item()
    unit = resolve_proportion_unit(cfg, n_label_space)
    k = cfg.top_k_k
    source_hash = hashlib.sha256(
        "\n".join(df.sort("row_id")["text"].head(1000).to_list()).encode()
    ).hexdigest()[:16]

    out = Path(cfg.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sample = df.sample(min(df.height, 500), seed=0)["text"]
    mean_tok = sum(count_tokens(t) for t in sample) / len(sample)
    sep_tok = count_tokens(cfg.separator)

    hay_path = out / "haystacks.jsonl"
    q_path = out / "questions.jsonl"
    kind_counts: Counter = Counter()
    hs_summary: list[dict] = []
    n_q = 0

    with hay_path.open("w", encoding="utf-8") as hf, q_path.open("w", encoding="utf-8") as qf:
        for target in cfg.haystack_target_tokens:
            for ki in range(cfg.haystacks_per_length):
                rng = random.Random(f"{cfg.seed}-{cfg.language}-{target}-{ki}")
                need = round(target / (mean_tok + sep_tok) * 1.05)   # separator-aware
                weights = (draw_label_weights(df["label"].to_list(), cfg.dirichlet_alpha, rng)
                           if cfg.dirichlet_alpha > 0 else None)
                cand = sample_candidate_rows(df, need, rng, weights)
                kept = select_rows_to_fit(cand, target, count_tokens, cfg.separator)

                # Drift: try eligible targets (strongest first); keep the first that
                # yields a DETECTABLE shift. Otherwise build driftless and flag it.
                drift_target, hay, meta, drift_ok = None, None, None, False
                if cfg.drift_mode:
                    eligible = eligible_drift_targets(kept)
                    rng.shuffle(eligible)
                    for cand_tgt in eligible:
                        h, m = order_and_assemble(kept, cand_tgt, cfg, count_tokens, rng)
                        if gt_primary(m, "shift", label=cand_tgt) is not None:
                            drift_target, hay, meta, drift_ok = cand_tgt, h, m, True
                            break
                if hay is None:
                    hay, meta = order_and_assemble(kept, None, cfg, count_tokens, rng)
                    if cfg.drift_mode and eligible_drift_targets(kept):
                        print(f"[warn] {cfg.language}-{target}-{ki}: no detectable drift "
                              f"target; built without shift", file=sys.stderr)
                # invariant: a persisted drift_target is always detectable
                if drift_target is not None:
                    if gt_primary(meta, "shift", label=drift_target) is None:
                        raise RuntimeError(f"persisted drift_target {drift_target!r} is not detectable")

                questions = generate_questions(
                    meta, cfg, rng, drift_target=drift_target, unit=unit, k=k)

                hs_id = f"{cfg.language}-{target}-{ki}"
                meta.write_parquet(out / f"meta_{hs_id}.parquet")
                hf.write(json.dumps({
                    "haystack_id": hs_id, "language": cfg.language,
                    "target_tokens": target, "n_examples": meta.height,
                    "drift_target": drift_target, "drift_ok": drift_ok,
                    "haystack": hay,
                }, ensure_ascii=False) + "\n")

                for qi, q in enumerate(questions):
                    kind_counts[q["kind"]] += 1
                    qf.write(json.dumps({
                        "id": f"{hs_id}-q{qi}", "haystack_id": hs_id,
                        "language": cfg.language, "target_tokens": target,
                        **q,
                    }, ensure_ascii=False) + "\n")
                    n_q += 1

                hs_summary.append({"haystack_id": hs_id, "n_examples": meta.height,
                                   "drift_target": drift_target, "drift_ok": drift_ok,
                                   "n_questions": len(questions)})
                print(f"built {hs_id}: {meta.height} examples, {len(questions)} questions"
                      + (f" (drift={drift_target})" if drift_target else " (no drift)"))

    manifest = {
        "version": VERSION,
        "date": date.today().isoformat(),
        "environment": {
            "python": platform.python_version(),
            "polars": pl.__version__,
            "transformers": pkg_version("transformers") if cfg.reference_tokenizer else None,
        },
        "config": dataclasses.asdict(cfg),
        "source_hash_first1000": source_hash,
        "rows_after_cleaning": df.height,
        "label_space": n_label_space,
        "proportion_unit": unit,
        "top_k_k": k,
        "tokenizer": cfg.reference_tokenizer or f"char_approx({cfg.chars_per_token})",
        "questions_written": n_q,
        "kind_distribution": dict(sorted(kind_counts.items())),
        "haystacks": hs_summary,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {n_q} questions -> {q_path}")
    print(f"haystacks -> {hay_path}")
    print(f"kind distribution: {dict(sorted(kind_counts.items()))}")
    print(f"manifest -> {out / 'manifest.json'}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

EXAMPLE_CONFIG = {
    "source_path": "datasets/massive_tr.parquet",
    "text_col": "utt",
    "label_col": "intent",
    "entity_col": "scenario",
    "language": "tr",
    "min_words": 1,
    "seed": 42,
    "haystack_target_tokens": [50000, 100000],
    "haystacks_per_length": 5,
    "questions_per_haystack": 12,
    "proportion_unit": "auto",
    "top_k_k": 3,
    "reference_tokenizer": "Qwen/Qwen3-8B",
    "out_dir": "tr_intent_out",
}


def build_many(config_paths: list[str], index_path: str = "benchmark_index.json") -> None:
    """Build several sets in one run and write a combined index -- this is how a
    benchmark spanning N Turkish + M English source datasets is assembled: one
    config per (dataset x axis), no code per dataset."""
    summaries = []
    for p in config_paths:
        cfg = Config.load(p)
        build(cfg)
        man = json.loads((Path(cfg.out_dir) / "manifest.json").read_text(encoding="utf-8"))
        summaries.append({
            "config": p, "out_dir": cfg.out_dir, "language": cfg.language,
            "source": cfg.source_path, "tokenizer": man["tokenizer"],
            "questions": man["questions_written"],
            "kind_distribution": man["kind_distribution"],
        })
    index = {
        "version": VERSION, "date": date.today().isoformat(),
        "n_sets": len(summaries),
        "total_questions": sum(s["questions"] for s in summaries),
        "languages": sorted({s["language"] for s in summaries}),
        "sets": summaries,
    }
    Path(index_path).write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nindex -> {index_path}  ({index['n_sets']} sets, "
          f"{index['total_questions']} questions, langs={index['languages']})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", nargs="+", help="one or more config json paths")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--index", default="benchmark_index.json",
                    help="combined index path when building multiple configs")
    args = ap.parse_args()
    if args.init:
        Path("tr_intent.json").write_text(
            json.dumps(EXAMPLE_CONFIG, indent=2), encoding="utf-8")
        print("wrote tr_intent.json -- edit source_path, then run --audit")
        return
    if not args.config:
        ap.error("--config is required (or use --init)")
    if not (args.audit or args.build):
        ap.error("pass --audit and/or --build")
    if args.audit:
        for c in args.config:
            cfg = Config.load(c)
            print(f"\n===== AUDIT {c} =====")
            audit(clean(load_source(cfg), cfg), cfg, make_token_counter(cfg))
    if args.build:
        if len(args.config) == 1:
            build(Config.load(args.config[0]))
        else:
            build_many(args.config, args.index)


if __name__ == "__main__":
    main()