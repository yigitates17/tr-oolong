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
  2. Shift answers are language-mapped (rose/fell -> arttı/azaldı) and validated.
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

VERSION = "0.4.0"


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
    drop_label_leakage: bool = True       # drop rows whose text contains a label surface form
    min_class_support: int = 0            # drop classes with fewer than N rows (0 = keep all)
    # haystack construction
    seed: int = 42
    haystack_target_tokens: list[int] = dataclasses.field(
        default_factory=lambda: [50_000, 100_000]
    )
    # RECORD-matched mode. Set this instead of haystack_target_tokens to fix the
    # number of records rather than the token budget. With pair_seed, a parallel
    # corpus then yields byte-for-byte the same RECORD SET in both locales, so
    # every gold answer is identical and TR-vs-EN can be tested pairwise
    # (McNemar) instead of as two independent samples. Token counts then differ
    # BY LANGUAGE, and that difference is the morphology cost, measured directly.
    haystack_target_records: list[int] = dataclasses.field(default_factory=list)
    haystacks_per_length: int = 5         # >=5 -> ~50 questions per (length x axis)
    questions_per_haystack: int = 12
    # language-neutral by design: a Turkish word here ("KAYIT") appeared inside
    # the ENGLISH haystacks and tokenizes differently in each language, which is
    # a confound in a matched-twin comparison. Symbols tokenize identically.
    separator: str = "\n\n<<<###>>>\n\n"
    drift_mode: bool = True
    min_entity_examples: int = 15         # soft eligibility: records per entity in-haystack
    dirichlet_alpha: float = 0.0          # >0: per-haystack Dirichlet label priors
    # question families
    proportion_unit: str = "auto"         # "auto" | "percent" | "per_mille"
    top_k_k: int = 3
    # --- question-difficulty floors (v0.4.0) --------------------------------
    # Each rejects a class of question that is answerable WITHOUT aggregating.
    min_answer_count: int = 20            # count answers below this are retrieval
    min_entity_answer: int = 10           # entity_count answers below this likewise
    min_rank_margin: float = 0.10         # relative gap needed at a ranking boundary
    entity_candidates: int = 5            # named candidates for entity_argmax/top_k
    label_candidates: int = 5             # named candidates for the label-ranking families
    families_disabled: list[str] = dataclasses.field(default_factory=list)
    entity_band_tol: float = 0.05         # entity candidates' POOL counts agree this closely
    # Label candidates need a much looser band than entity candidates, and the
    # reason is asymmetric: the LABEL axis already gets a fresh Dirichlet prior
    # per haystack (draw_label_weights), which demonstrably neutralises the corpus
    # prior on its own -- `most_common` measures at chance on the 3-class sets,
    # where the candidate set is the whole label space and no matching happens at
    # all. The entity axis has no such prior, so its candidates must be matched
    # tightly. Reusing 0.05 for labels starves the ranking families on any small
    # label space: 18 classes spanning 65-2,313 rows contain no 5 within 5%.
    # 0.15 is measured, not guessed. At 0.05 only ~13 distinct ranking questions
    # exist across 10 haystacks, so the family starves on any small label space.
    # At 0.25 there are ~240 but `most_common` retains a small real edge for the
    # corpus prior (en_intent: 0.271 vs 0.200 chance, z=+2.8 over 247 draws --
    # visible only under --certify, never at the n=10 that ships). At 0.15 there
    # are ~150, which is ample against a quota of 10, and the prior is at chance.
    label_band_tol: float = 0.15
    entity_jitter_sigma: float = 1.0      # per-haystack log-normal entity perturbation
    # --- matched-twin control (v0.4.0) --------------------------------------
    # True: drop `language` from the RNG seed so a parallel corpus yields
    # RECORD-IDENTICAL haystacks in both locales (identical gold answers).
    pair_seed: bool = False
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


TR_VOWELS = "aeıioöuü"
# Turkish question particle by 4-way vowel harmony of the last vowel.
# Written as a separate word, so "akbank mı" / "mng kargo mu" / "ebebek mi".
_SORU = {"a": "mı", "ı": "mı", "e": "mi", "i": "mi",
         "o": "mu", "u": "mu", "ö": "mü", "ü": "mü"}


def soru_eki(word: str) -> str:
    """The Turkish yes/no question particle agreeing with `word`.

    Hardcoding one particle (the pre-0.4.0 behaviour) made most `pairwise`
    questions ungrammatical -- 'akbank mı yoksa mng kargo mi' should be 'mu'.
    Vowel harmony is decided by the last vowel of the written form, which is
    what a Turkish writer applies to loanwords and brand names too.
    """
    for ch in reversed(tr_casefold(unicodedata.normalize("NFC", word))):
        if ch in _SORU:
            return _SORU[ch]
    # No vowel at all -> an acronym, read letter by letter. Every Turkish
    # consonant letter-name ends in 'e' (be, ce, de, ... ze), so "TCDD mi?".
    return "mi"


def normalize_for_dedup(s: str, language: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = tr_casefold(s) if language == "tr" else s.casefold()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^\w\s]", "", s)
    return s


def fold(s: str, language: str) -> str:
    return tr_casefold(s) if language == "tr" else s.casefold()


def leak_surface_forms(label: str, language: str) -> set[str]:
    """Surface strings that would let a solver find a label by substring search.
    Canonical definition: shared with scripts/trivial_baseline.py so that the
    leakage filter and the leakage baseline can never disagree."""
    return {fold(label, language), fold(label.replace("_", " "), language)}


def label_leak_mask(texts: list[str], labels: list[str], language: str) -> list[bool]:
    """True where the text contains ANY label's surface form. Matching on the
    whole label space (not just the row's own label) is what makes the
    grep-proofness claim total: after filtering, a substring solver sees zero
    hits for every label, so its label ranking carries no information."""
    forms = sorted({f for l in labels for f in leak_surface_forms(l, language)})
    return [any(f in fold(t, language) for f in forms) for t in texts]


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


def clean(df: pl.DataFrame, cfg: Config, stats: dict | None = None) -> pl.DataFrame:
    stats = stats if stats is not None else {}
    df = df.with_columns(
        pl.col("text").str.replace_all(r"\s+", " ").str.strip_chars().alias("text"),
        pl.col("label").str.strip_chars().str.to_lowercase().alias("label"),
        pl.col("entity").cast(pl.Utf8).str.strip_chars().alias("entity"),
    )
    # repair the combining-dot artifact (i followed by U+0307). It must be applied
    # to the ENTITY column too: entity names are printed verbatim inside questions,
    # so an unrepaired one ships as "i̇ş bankası" in the released dataset.
    df = df.with_columns(
        pl.col("text").str.replace_all("i\u0307", "i").alias("text"),
        pl.col("entity").str.replace_all("i\u0307", "i").alias("entity"),
    )
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

    # Grep-proofness: drop records whose text contains any label surface form.
    # The drop RATE is itself the label-leakage measurement (see DATACARD) --
    # it is recorded here precisely because the filter removes the phenomenon
    # from the built benchmark.
    before = df.height
    if cfg.drop_label_leakage and before:
        leaking = label_leak_mask(df["text"].to_list(), sorted(set(df["label"].to_list())),
                                  cfg.language)
        df = df.filter(~pl.Series(leaking))
    stats["rows_dropped_label_leakage"] = before - df.height
    stats["label_leakage_rate"] = round((before - df.height) / before, 6) if before else 0.0

    # Class support: a class with too few rows to ever be sampled competitively
    # is deterministically the rarest in every haystack, which makes
    # least_common answerable from corpus priors alone rather than from the
    # context. Such classes are removed from the pool entirely.
    dropped_classes: list[str] = []
    if cfg.min_class_support > 0 and df.height:
        vc = df["label"].value_counts()
        dropped_classes = sorted(vc.filter(pl.col("count") < cfg.min_class_support)["label"].to_list())
        if dropped_classes:
            df = df.filter(~pl.col("label").is_in(dropped_classes))
    stats["classes_dropped_low_support"] = dropped_classes
    stats["min_class_support"] = cfg.min_class_support

    return df.with_row_index("row_id")


# ---------------------------------------------------------------------------
# Proportion unit resolution
# ---------------------------------------------------------------------------

RANKING_CONTESTED_K = 10          # above this, ranking is contested among many classes


def ranking_length_ceiling(df: pl.DataFrame, tokens_per_record: float) -> tuple[int, dict]:
    """Longest haystack for which most_common / least_common / second_most can
    still vary across haystacks, in tokens. Returns (ceiling, diagnostics).

    A haystack of R records over K classes gives each class a 1/K share on
    average, so a class can only become the most frequent one if the pool can
    supply more than R/K of it. The smallest class therefore caps the haystack
    at R = min_class_pool * K records: past that point the rare classes are
    pinned to the bottom of every ranking by the corpus rather than by the
    sampled context, and the ranking families answer themselves.

    Only binding for small label spaces. With many classes the ranking is
    contested among the well-supported ones regardless of the tail, which is
    what `min_class_support` handles instead; 0 is returned to mean "no bound".
    """
    vc = df["label"].value_counts()
    K = vc.height
    if K > RANKING_CONTESTED_K or not K:
        return 0, {"n_classes": K, "binding": False}
    min_class = int(vc["count"].min())
    max_records = min_class * K
    return int(max_records * tokens_per_record), {
        "n_classes": K, "min_class_pool": min_class,
        "max_records": max_records, "binding": True,
    }


# Observed: a set at 0.89x its ceiling still varies (tr_oolong at 500K), one at
# 1.12x is degenerate (airline tweets at 250K). Warn from 0.85x.
CEILING_WARN_RATIO = 0.85


def check_length_feasibility(cfg: Config, ceiling: int) -> None:
    if not ceiling:
        return
    for target in cfg.haystack_target_tokens:
        ratio = target / ceiling
        if ratio > CEILING_WARN_RATIO:
            print(f"[feasibility] {cfg.out_dir}: target {target:,} tokens is "
                  f"{ratio:.2f}x the ranking ceiling ({ceiling:,}). The label-ranking "
                  f"families will be skewed toward the corpus prior at this length.",
                  file=sys.stderr)


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
    _audit_thresholds(df, cfg, count_tokens, mean_tok + sep_tok)

    noise = df.sample(min(n, 200), seed=1).select("row_id", "text", "label", "entity")
    out = Path(cfg.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    noise.write_csv(out / "label_noise_slice.csv")
    print(f"\nwrote 200-row self-annotation slice -> {out / 'label_noise_slice.csv'}")
    print("   ^ THIS IS NOT OPTIONAL. Ground truth is the source labels, so their")
    print("     accuracy is the benchmark's ceiling. Hand-check the slice and record")
    print("     the rate in DATACARD.md.")


def _audit_thresholds(df: pl.DataFrame, cfg: Config, count_tokens, tok_per_rec: float) -> None:
    """Measure what difficulty thresholds this source can actually support.

    The floors that make questions non-trivial (`min_rank_margin`,
    `min_answer_count`, `entity_candidates`) are NOT one-size-fits-all: values
    calibrated on a 3-class axis reject every ranking draw on an 18- or 48-class
    one, and the family starves. Rather than guess, build a couple of trial
    haystacks and report the gaps this source actually produces.
    """
    import statistics
    K = df["label"].n_unique()
    vc = df.group_by("label").len().sort("len", descending=True)
    cnt = vc["len"].to_list()
    ent_norm = 0.0
    if K > 1:
        tot = sum(cnt)
        ent_norm = -sum((c / tot) * math.log2(c / tot) for c in cnt) / math.log2(K)
    print("\n--- class balance ---")
    print(f"  classes                  : {K}")
    print(f"  imbalance (max/min)      : {max(cnt) / min(cnt):.1f}")
    print(f"  normalised entropy       : {ent_norm:.3f}   (1.0 = perfectly balanced)")
    print(f"  largest / smallest class : {max(cnt):,} / {min(cnt):,}")
    if min(cnt) < 100:
        print(f"  [!] smallest class has {min(cnt)} rows -- set min_class_support to drop "
              f"the tail, or least_common becomes answerable from corpus priors (D3)")

    if cfg.entity_col:
        ev = df.group_by("entity").len().sort("len", descending=True)
        ec = ev["len"].to_list()
        print("\n--- entity axis ---")
        print(f"  entities                 : {len(ec):,}")
        print(f"  top-1 / top-10 share     : {ec[0]/sum(ec):.3f} / {sum(ec[:10])/sum(ec):.3f}")
        if len(ec) < cfg.entity_candidates + 1:
            print(f"  [!] only {len(ec)} entities: a prior-neutral {cfg.entity_candidates}-way "
                  f"candidate set cannot exist. Lower entity_candidates, or expect "
                  f"entity_argmax/top_k to be omitted (as for en_twin, 6 airlines).")

    # trial haystacks: measure the adjacent-rank gaps this source actually yields
    target = min(cfg.haystack_target_tokens) if cfg.haystack_target_tokens else 50_000
    need = round(target / tok_per_rec * 1.05)
    gaps_top, gaps_tail, smallest = [], [], []
    for ki in range(3):
        rng = random.Random(f"audit-{cfg.seed}-{cfg.language}-{ki}")
        w = (draw_label_weights(df["label"].to_list(), cfg.dirichlet_alpha, rng)
             if cfg.dirichlet_alpha > 0 else None)
        cand = sample_candidate_rows(df, need, rng, w)
        kept = select_rows_to_fit(cand, target, count_tokens, cfg.separator)
        c = Counter(kept["label"].to_list())
        r = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        if len(r) < 3:
            continue
        gaps_top.append((r[0][1] - r[1][1]) / max(1, r[0][1]))
        gaps_tail.append((r[-2][1] - r[-1][1]) / max(1, r[-2][1]))
        smallest.append(r[-1][1])
    print("\n--- recommended difficulty floors (measured on 3 trial haystacks) ---")
    if gaps_top:
        # take a value most draws clear, so the family does not starve
        rec_margin = max(0.02, round(min(statistics.median(gaps_top),
                                         statistics.median(gaps_tail)) * 0.5, 2))
        rec_answer = max(5, min(20, int(statistics.median(smallest) * 0.5)))
        print(f"  observed rank-1/2 rel. gap   : {statistics.median(gaps_top):.3f} (median)")
        print(f"  observed rank-(K-1)/K gap    : {statistics.median(gaps_tail):.3f} (median)")
        print(f"  rarest class in a haystack   : {int(statistics.median(smallest))} records")
        print(f"  -> min_rank_margin           : {rec_margin}   (config currently "
              f"{cfg.min_rank_margin})")
        print(f"  -> min_answer_count          : {rec_answer}   (config currently "
              f"{cfg.min_answer_count})")
        if cfg.min_rank_margin > statistics.median(gaps_tail):
            print(f"  [!] min_rank_margin exceeds the typical tail gap: least_common and "
                  f"second_most WILL starve. Lower it or disable those families.")
    print("\n--- chance rates a solver gets for free (report these) ---")
    nc = min(K, cfg.label_candidates)
    print(f"  most/least/second_most   : 1/{nc} = {1/nc:.3f}")
    print(f"  shift, pairwise          : 0.500")
    if cfg.entity_col:
        print(f"  entity_argmax            : 1/{cfg.entity_candidates} = "
              f"{1/cfg.entity_candidates:.3f}")
        print(f"  top_k                    : 1/{math.perm(max(cfg.entity_candidates, cfg.top_k_k+1), cfg.top_k_k)}")
    print("\nAfter --build, ALWAYS run:  python scripts/quality_audit.py")


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


def draw_entity_jitter(pool_entities: list[str], sigma: float,
                       rng: random.Random) -> dict[str, float]:
    """Per-haystack log-normal perturbation of the entity distribution.

    The label axis already gets a fresh random prior per haystack
    (`draw_label_weights`); the entity axis did not, so every haystack inherited
    the corpus's entity ranking and "which brand has the most X" was decided by
    "which brand is biggest" -- answerable with no context at all. A mild
    multiplicative jitter keeps big entities big (so support stays adequate)
    while reshuffling the order among comparable ones, which is what makes the
    entity ranking a property of THIS haystack rather than of the corpus.
    """
    if sigma <= 0:
        return {e: 1.0 for e in set(pool_entities)}
    return {e: math.exp(sigma * rng.gauss(0.0, 1.0)) for e in sorted(set(pool_entities))}


def rank_candidate_rows(df: pl.DataFrame, rng: random.Random,
                        label_weights: dict[str, float] | None = None,
                        entity_weights: dict[str, float] | None = None) -> list[int]:
    """Full weighted ranking of every pool row; the first k are a weighted sample
    of size k WITHOUT replacement.

    One key is drawn per pool row regardless of how many rows are wanted, so the
    rankings for different k are NESTED: taking more rows extends the previous
    selection rather than resampling it. That is what lets the haystack top-up
    loop in build() grow a candidate set without perturbing the build.
    """
    if label_weights is None and entity_weights is None:
        idx = list(range(df.height))
        rng.shuffle(idx)
        return idx
    labels = df["label"].to_list()
    ents = df["entity"].to_list()
    lw = label_weights or {}
    ew = entity_weights or {}
    # Efraimidis-Spirakis A-Res in exponential-race form: rank by -Exp(1)/w
    # instead of u**(1/w), which underflows to 0.0 for the tiny per-row weights
    # of large pools. Label and entity weights multiply: on an ORTHOGONAL entity
    # axis (the only axis where the entity families are emitted) this perturbs
    # each marginal independently.
    keyed = sorted(((-rng.expovariate(1.0) / (lw.get(l, 1.0) * ew.get(e, 1.0)), i)
                    for i, (l, e) in enumerate(zip(labels, ents))), reverse=True)
    return [i for _, i in keyed]


def sample_candidate_rows(df: pl.DataFrame, need: int, rng: random.Random,
                          label_weights: dict[str, float] | None = None,
                          entity_weights: dict[str, float] | None = None) -> pl.DataFrame:
    order = rank_candidate_rows(df, rng, label_weights, entity_weights)
    return df[order[: min(need, df.height)]]


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


def entity_haystack_counts(meta: pl.DataFrame) -> dict[str, int]:
    ag = meta.group_by("entity").len()
    return dict(zip(ag["entity"].to_list(), ag["len"].to_list()))


def pick_entity_candidates(hay_counts: dict[str, int], prior_counts: dict[str, int],
                           rng: random.Random, *,
                           n: int, min_support: int, tol: float) -> list[str] | None:
    """A PRIOR-NEUTRAL candidate set of n entities for one label.

    This is the fix for the v0.3.0 entity-family failure: ranging over every
    askable entity made "which brand has the most X" decidable from the corpus
    alone -- a context-free prior oracle scored entity_argmax 0.55-0.87,
    pairwise 0.73-1.00 and top_k up to 0.90.

    Matching candidates on total entity SIZE is not enough, because label counts
    are roughly proportional to size, so the biggest candidate still wins. The
    candidates are therefore matched on their POOL count FOR THE ASKED LABEL:
    if all n candidates have near-identical corpus-level counts for that label,
    the corpus cannot rank them, and the answer is decided only by how this
    haystack's sampling landed (see draw_entity_jitter).

    `min_support` is enforced on counts IN THE HAYSTACK, so the answer never
    rests on a handful of records. Returns None if no such set exists.
    """
    eligible = [e for e, c in hay_counts.items()
                if c >= min_support and e != "__none__" and e in prior_counts]
    if len(eligible) < n:
        return None
    # sort by the pool prior for this label; any window of n adjacent entries is
    # the tightest possible prior-matched set of that size
    ranked = sorted(eligible, key=lambda e: (prior_counts[e], e))
    windows = [ranked[i:i + n] for i in range(len(ranked) - n + 1)]
    ok = [w for w in windows
          if prior_counts[w[0]] > 0
          and (prior_counts[w[-1]] - prior_counts[w[0]]) <= tol * prior_counts[w[0]]]
    if not ok:
        return None
    return sorted(rng.choice(ok))


def fmt_candidates(cands: list[str]) -> str:
    return ", ".join(f"'{c}'" for c in cands)


# ---------------------------------------------------------------------------
# Question templates -- config overrides the 5 base families; script owns the rest
# ---------------------------------------------------------------------------

Q_TEMPLATES = {
    "tr": {
        "count": "Bu kayıtlarda kaç tane '{label}' etiketli kayıt var? Sadece sayıyı yaz.",
        "proportion_percent": "Kayıtların yüzde kaçı '{label}' etiketli? En yakın tam sayıya yuvarla, sadece sayıyı yaz.",
        "proportion_per_mille": "Kayıtların binde kaçı '{label}' etiketli? En yakın tam sayıya yuvarla, sadece sayıyı yaz.",
        "entity_count": "'{entity}' grubundaki kayıtlardan kaç tanesi '{label}' etiketli? Sadece sayıyı yaz.",
        "entity_argmax": "Şu gruplardan hangisi en çok '{label}' etiketli kayıt içeriyor: {candidates}? Sadece grup adını yaz.",
        "shift": "Kayıtların ikinci yarısında '{label}' etiketli kayıtların oranı ilk yarıya göre arttı mı azaldı mı? 'arttı' veya 'azaldı' yaz.",
        "top_k": "Şu gruplar arasında en çok '{label}' etiketli kayıt içeren ilk {k} grup hangileri: {candidates}? Çoktan aza doğru, aralarına ' > ' koyarak yaz.",
        "pairwise": "'{label}' etiketli kayıt hangisinde daha çok: '{entity_a}' {soru_a} yoksa '{entity_b}' {soru_b}? Sadece grup adını yaz.",
        "most_common": "Bu kayıtlarda en sık görülen etiket hangisi? Etiketler: {labels}. Sadece etiket adını yaz.",
        "least_common": "Bu kayıtlarda en az görülen etiket hangisi? Etiketler: {labels}. Sadece etiket adını yaz.",
        "second_most": "Bu kayıtlarda ikinci en sık görülen etiket hangisi? Etiketler: {labels}. Sadece etiket adını yaz.",
    },
    "en": {
        "count": "How many records are labeled '{label}'? Answer with the number only.",
        "proportion_percent": "What percentage of records are labeled '{label}'? Round to the nearest integer, answer with the number only.",
        "proportion_per_mille": "How many per thousand (per-mille) of records are labeled '{label}'? Round to the nearest integer, answer with the number only.",
        "entity_count": "How many records in the '{entity}' group are labeled '{label}'? Answer with the number only.",
        "entity_argmax": "Which of these groups contains the most records labeled '{label}': {candidates}? Answer with the group name only.",
        "shift": "Did the share of '{label}' records rise or fall in the second half compared to the first? Answer 'rose' or 'fell'.",
        "top_k": "Among these groups, which {k} contain the most records labeled '{label}': {candidates}? List them from most to fewest, separated by ' > '.",
        "pairwise": "Which group has more '{label}' records: '{entity_a}' or '{entity_b}'? Answer with the group name only.",
        "most_common": "Which label is the most common in these records? Labels: {labels}. Answer with the label name only.",
        "least_common": "Which label is the least common in these records? Labels: {labels}. Answer with the label name only.",
        "second_most": "Which label is the second most common in these records? Labels: {labels}. Answer with the label name only.",
    },
}

# v0.4.0: proper Turkish orthography. src/scoring.py also accepts the old
# ASCII-folded forms, so 'artti' is still marked correct.
SHIFT_ANSWER = {
    "tr": {"rose": "arttı", "fell": "azaldı"},
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


def _margin_ok(hi: int, lo: int, min_margin: float) -> bool:
    """A ranking boundary is usable only if the winner leads by a real margin.

    A gap of one or two records is inside the label noise of any source corpus,
    so such a question measures annotation noise rather than aggregation. Both
    GT paths call this, so the rule cannot drift between them.
    """
    return hi > lo and (hi - lo) >= max(2, math.ceil(min_margin * hi))


def gt_primary(meta, kind, *, label=None, entity=None, entity_a=None, entity_b=None,
               unit="percent", k=3, askable=None, min_margin=0.0, min_answer=0):
    askable = askable or []
    if kind == "count":
        return str(meta.filter(pl.col("label") == label).height)
    if kind == "proportion":
        scale = PROP_SCALE[unit]
        return str(math.floor(scale * meta.filter(pl.col("label") == label).height / meta.height + 0.5))
    if kind == "entity_count":
        n = meta.filter((pl.col("entity") == entity) & (pl.col("label") == label)).height
        return None if n < min_answer else str(n)
    if kind == "entity_argmax":
        ranked = _rank_entities(meta, label, askable)
        if len(ranked) < 2 or ranked[0][1] < min_answer:
            return None
        if not _margin_ok(ranked[0][1], ranked[1][1], min_margin):
            return None
        return ranked[0][0]
    if kind == "top_k":
        ranked = _rank_entities(meta, label, askable)
        if len(ranked) < k + 1 or ranked[k - 1][1] < min_answer:
            return None
        window = ranked[: k + 1]
        for a, b in zip(window, window[1:]):
            if not _margin_ok(a[1], b[1], min_margin):   # every boundary must be clear
                return None
        return [e for e, _ in ranked[:k]]
    if kind == "pairwise":
        a = meta.filter((pl.col("entity") == entity_a) & (pl.col("label") == label)).height
        b = meta.filter((pl.col("entity") == entity_b) & (pl.col("label") == label)).height
        hi, lo = max(a, b), min(a, b)
        if lo < min_answer or not _margin_ok(hi, lo, min_margin):
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
        if askable:
            ranked = [(l, c) for l, c in ranked if l in set(askable)]
        return _label_stat(ranked, kind, min_margin, min_answer)
    raise ValueError(kind)


def _label_stat(ranked, kind, min_margin=0.0, min_answer=0):
    """Shared margin rule over a (label, count) ranking sorted count desc, name asc.
    ranked is built independently by each GT path, so the aggregation is still
    differentially tested; only this small decision rule is shared."""
    if len(ranked) < 2:
        return None
    if kind == "most_common":
        if not _margin_ok(ranked[0][1], ranked[1][1], min_margin):
            return None
        return ranked[0][0]
    if kind == "least_common":
        if ranked[-1][1] < min_answer:              # too rare to count reliably
            return None
        if not _margin_ok(ranked[-2][1], ranked[-1][1], min_margin):
            return None
        return ranked[-1][0]
    if kind == "second_most":
        if len(ranked) < 3:
            return None
        if not _margin_ok(ranked[0][1], ranked[1][1], min_margin):
            return None
        if not _margin_ok(ranked[1][1], ranked[2][1], min_margin):
            return None
        return ranked[1][0]
    raise ValueError(kind)


def gt_check(meta, kind, *, label=None, entity=None, entity_a=None, entity_b=None,
             unit="percent", k=3, askable=None, min_margin=0.0, min_answer=0):
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
        n = sum(1 for l, e in zip(labels, ents) if l == label and e == entity)
        return None if n < min_answer else str(n)
    if kind in ("entity_argmax", "top_k"):
        c = Counter(e for l, e in zip(labels, ents) if l == label and e in askable)
        ranked = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        if kind == "entity_argmax":
            if len(ranked) < 2 or ranked[0][1] < min_answer:
                return None
            if not _margin_ok(ranked[0][1], ranked[1][1], min_margin):
                return None
            return ranked[0][0]
        if len(ranked) < k + 1 or ranked[k - 1][1] < min_answer:
            return None
        window = ranked[: k + 1]
        for a, b in zip(window, window[1:]):
            if not _margin_ok(a[1], b[1], min_margin):
                return None
        return [e for e, _ in ranked[:k]]
    if kind == "pairwise":
        a = sum(1 for l, e in zip(labels, ents) if l == label and e == entity_a)
        b = sum(1 for l, e in zip(labels, ents) if l == label and e == entity_b)
        hi, lo = max(a, b), min(a, b)
        if lo < min_answer or not _margin_ok(hi, lo, min_margin):
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
        if askable:
            c = Counter({l: n for l, n in c.items() if l in askable})
        ranked = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        return _label_stat(ranked, kind, min_margin, min_answer)
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

def _make_one(kind, meta, cfg, rng, *, labels, askable, drift_target, unit, k,
              ent_counts=None, prior_ent=None, prior_lab=None):
    """Return a question dict for `kind`, or None if this draw is degenerate."""
    mm, ma = cfg.min_rank_margin, cfg.min_answer_count
    label_list = ", ".join(f"'{l}'" for l in labels)
    if kind == "count":
        label = rng.choice(labels)
        gt = verified_gt(meta, kind, label=label)
        # an answer of a handful of records is retrieval, not aggregation
        if gt in ("0", str(meta.height)) or int(gt) < ma:
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
        # pick the label first, then an entity whose count for it is large enough
        # to require counting rather than spotting three records.
        label = rng.choice(labels)
        pool = (
            meta.filter((pl.col("label") == label) & pl.col("entity").is_in(askable))
            .group_by("entity").len()
        )
        valid = []
        for e, c in zip(pool["entity"].to_list(), pool["len"].to_list()):
            total = meta.filter(pl.col("entity") == e).height
            if cfg.min_entity_answer <= c < total:
                valid.append(e)
        if not valid:
            return None
        entity = rng.choice(sorted(valid))
        gt = verified_gt(meta, kind, label=label, entity=entity,
                         min_answer=cfg.min_entity_answer)
        if gt is None:
            return None
        return {"kind": kind, "label": label, "entity": entity, "answer": gt,
                "question": resolve_template(cfg, kind).format(label=label, entity=entity)}

    # --- entity-relational families: always over a NAMED, frequency-matched set.
    # Ranging over every askable entity made these answerable from the corpus
    # prior (biggest brand wins) and left the answer resting on <10 records.
    if kind in ("entity_argmax", "top_k", "pairwise"):
        n_cand = 2 if kind == "pairwise" else max(cfg.entity_candidates, k + 1)
        label = rng.choice(labels)
        cands = pick_entity_candidates(ent_counts or {}, (prior_ent or {}).get(label, {}),
                                       rng, n=n_cand,
                                       min_support=cfg.min_entity_examples,
                                       tol=cfg.entity_band_tol)
        if cands is None:
            return None
        if kind == "pairwise":
            entity_a, entity_b = cands
            gt = verified_gt(meta, kind, label=label, entity_a=entity_a, entity_b=entity_b,
                             min_margin=mm, min_answer=cfg.min_entity_answer)
            if gt is None:
                return None
            return {"kind": kind, "label": label, "entity_a": entity_a,
                    "entity_b": entity_b, "candidates": cands, "answer": gt,
                    "question": resolve_template(cfg, kind).format(
                        label=label, entity_a=entity_a, entity_b=entity_b,
                        soru_a=soru_eki(entity_a), soru_b=soru_eki(entity_b))}
        gt = verified_gt(meta, kind, label=label, k=k, askable=cands,
                         min_margin=mm, min_answer=cfg.min_entity_answer)
        if gt is None:
            return None
        q = {"kind": kind, "label": label, "candidates": cands, "answer": gt,
             "question": resolve_template(cfg, kind).format(
                 label=label, k=k, candidates=fmt_candidates(cands))}
        if kind == "top_k":
            q["k"] = k
            q["answer_display"] = " > ".join(gt)
        return q

    if kind == "shift":
        label = drift_target
        gt = verified_gt(meta, kind, label=label)
        if gt is None:
            return None
        answer = SHIFT_ANSWER[cfg.language][gt]
        return {"kind": kind, "label": label, "answer": answer,
                "question": resolve_template(cfg, kind).format(label=label)}

    if kind in ("most_common", "least_common", "second_most"):
        # The candidate labels are NAMED in the question. Two reasons:
        #  1. Well-posedness -- no model can be expected to produce
        #     'iot_hue_lightoff' without being told the label space exists.
        #  2. On a large label space the full ranking is decided by its tail: at
        #     48 classes the rarest label in a 6,000-record haystack has ~7
        #     records and adjacent ranks differ by 1, so `least_common` over all
        #     labels is a coin flip. Restricting to a few well-supported,
        #     prior-matched labels makes the comparison substantive.
        # With K <= label_candidates the candidate set IS the whole label space,
        # so the 3-class review axis keeps its original semantics.
        if len(labels) <= cfg.label_candidates:
            cands = labels
        else:
            cands = pick_entity_candidates(
                dict(Counter(meta["label"].to_list())), (prior_lab or {}), rng,
                n=cfg.label_candidates, min_support=ma, tol=cfg.label_band_tol)
            if cands is None:
                return None
        gt = verified_gt(meta, kind, askable=cands, min_margin=mm, min_answer=ma)
        if gt is None:
            return None
        return {"kind": kind, "label": None, "candidates": cands, "answer": gt,
                "question": resolve_template(cfg, kind).format(
                    labels=", ".join(f"'{l}'" for l in cands))}

    raise ValueError(kind)


def _dedup_key(q: dict) -> tuple:
    if q["kind"] == "pairwise":
        return ("pairwise", q["label"], frozenset((q["entity_a"], q["entity_b"])))
    if q["kind"] == "entity_count":
        return ("entity_count", q["label"], q["entity"])
    if q["kind"] in ("entity_argmax", "top_k", "most_common", "least_common",
                     "second_most"):                # same family, different candidates
        return (q["kind"], q["label"], tuple(q.get("candidates") or ()))
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


def generate_questions(meta, cfg, rng, *, drift_target, unit, k, prior_ent=None,
                       prior_lab=None):
    labels = sorted(meta["label"].unique().to_list())
    askable = sorted(
        meta.group_by("entity").len()
        .filter((pl.col("len") >= cfg.min_entity_examples) & (pl.col("entity") != "__none__"))
        ["entity"].to_list()
    )   # min_entity_examples counts records IN THIS HAYSTACK, not in the pool
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
    ent_counts = entity_haystack_counts(meta) if entity_relational else {}
    if entity_relational:
        families += ["entity_count", "entity_argmax"]
        # an entity family ships only if a frequency-MATCHED candidate set of the
        # required size actually exists in this haystack (see pick_entity_candidates)
        probe = random.Random(0)
        def _has(n):
            return any(pick_entity_candidates(ent_counts, (prior_ent or {}).get(l, {}),
                                              probe, n=n,
                                              min_support=cfg.min_entity_examples,
                                              tol=cfg.entity_band_tol) is not None
                       for l in labels)
        if _has(2):
            families.append("pairwise")
        if _has(max(cfg.entity_candidates, k + 1)):
            families.append("top_k")

    families = [f for f in families if f not in set(cfg.families_disabled)]
    quota = allocate_quota(families, cfg.questions_per_haystack)
    seen: set[tuple] = set()
    out: list[dict] = []

    def fill(kind: str, n: int, attempt_budget: int) -> int:
        got = 0
        attempts = 0
        while got < n and attempts < attempt_budget:
            attempts += 1
            q = _make_one(kind, meta, cfg, rng, labels=labels, askable=askable,
                          drift_target=drift_target, unit=unit, k=k,
                          ent_counts=ent_counts, prior_ent=prior_ent,
                          prior_lab=prior_lab)
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
    realized: dict[str, int] = {}
    for kind, n in quota.items():
        realized[kind] = fill(kind, n, attempt_budget=40 * max(1, n))
    # A family can be rejected out of existence by the difficulty floors -- which
    # is correct behaviour, but MUST be loud. A silent starvation is how a new
    # source ships with three families missing: on an 18-class axis the 3-class
    # default of min_rank_margin=0.10 rejects every ranking draw, and the quota
    # spills into count/proportion with no indication anything was lost.
    for kind, want in quota.items():
        got = realized.get(kind, 0)
        if want and got == 0:
            print(f"[starved] {cfg.out_dir}: family '{kind}' produced 0/{want} questions. "
                  f"The difficulty floors reject every draw for this source. Run "
                  f"--audit for recommended thresholds, or disable the family "
                  f"explicitly via \"families_disabled\".", file=sys.stderr)
        elif want and got < want:
            print(f"[short]   {cfg.out_dir}: family '{kind}' produced {got}/{want}.",
                  file=sys.stderr)
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
    clean_stats: dict = {}
    df = clean(load_source(cfg), cfg, clean_stats)
    n_label_space = df.select(pl.col("label").n_unique()).item()
    unit = resolve_proportion_unit(cfg, n_label_space)
    k = cfg.top_k_k
    source_hash = hashlib.sha256(
        "\n".join(df.sort("row_id")["text"].head(1000).to_list()).encode()
    ).hexdigest()[:16]

    out = Path(cfg.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # a tier removed from the config used to leave its meta_*.parquet behind and
    # ship with the release; clear generated artifacts before every build
    for stale in list(out.glob("meta_*.parquet")) + list(out.glob("*.jsonl")):
        stale.unlink()
    sample = df.sample(min(df.height, 500), seed=0)["text"]
    mean_tok = sum(count_tokens(t) for t in sample) / len(sample)
    sep_tok = count_tokens(cfg.separator)

    # pool-level (label -> entity -> count): what a context-free oracle knows.
    # Candidate sets are matched against this so the oracle cannot rank them.
    prior_ent: dict[str, dict[str, int]] = {}
    if cfg.entity_col:
        pe = df.group_by(["label", "entity"]).len()
        for lab, ent_, c in zip(pe["label"].to_list(), pe["entity"].to_list(),
                                pe["len"].to_list()):
            prior_ent.setdefault(lab, {})[ent_] = c

    prior_lab = dict(Counter(df["label"].to_list()))

    ceiling, ceiling_info = ranking_length_ceiling(df, mean_tok + sep_tok)
    check_length_feasibility(cfg, ceiling)
    ceiling_info["ranking_length_ceiling_tokens"] = ceiling

    hay_path = out / "haystacks.jsonl"
    q_path = out / "questions.jsonl"
    kind_counts: Counter = Counter()
    hs_summary: list[dict] = []
    n_q = 0

    with hay_path.open("w", encoding="utf-8") as hf, q_path.open("w", encoding="utf-8") as qf:
        record_mode = bool(cfg.haystack_target_records)
        targets = cfg.haystack_target_records if record_mode else cfg.haystack_target_tokens
        for target in targets:
            for ki in range(cfg.haystacks_per_length):
                # pair_seed: a parallel corpus (MASSIVE tr/en) is row-aligned after
                # clean(), so dropping `language` from the seed makes both locales
                # sample the SAME records -> identical gold answers -> paired tests.
                seed_lang = "pair" if cfg.pair_seed else cfg.language
                rng = random.Random(f"{cfg.seed}-{seed_lang}-{target}-{ki}")
                # record mode takes exactly `target` rows; token mode estimates
                # how many rows fit the budget and then trims to fit
                need = target if record_mode else round(target / (mean_tok + sep_tok) * 1.05)
                weights = (draw_label_weights(df["label"].to_list(), cfg.dirichlet_alpha, rng)
                           if cfg.dirichlet_alpha > 0 else None)
                ent_jitter = (draw_entity_jitter(df["entity"].to_list(),
                                                 cfg.entity_jitter_sigma, rng)
                              if cfg.entity_col and cfg.entity_jitter_sigma > 0 else None)
                order = rank_candidate_rows(df, rng, weights, ent_jitter)
                if record_mode:
                    kept = df[order[: min(need, df.height)]]
                else:
                    kept = select_rows_to_fit(df[order[:need]], target,
                                              count_tokens, cfg.separator)
                    # `need` is estimated from the POOL's mean record length. On a
                    # heavy-tailed length distribution the sampled subset runs
                    # shorter than the mean, so every candidate fits and the
                    # haystack lands far under budget: tr_oolong shipped a "100K"
                    # haystack of 53K tokens and a "500K" one of 381K.
                    # rank_candidate_rows returns the FULL ranking, so deepening
                    # the slice extends the same weighted selection -- a haystack
                    # that already fit is untouched.
                    grow = 0
                    while kept.height == min(need, df.height) < df.height and grow < 12:
                        grow += 1
                        need = min(df.height, int(need * 1.6) + 64)
                        kept = select_rows_to_fit(df[order[:need]], target,
                                                  count_tokens, cfg.separator)
                    got = sum(count_tokens(t) for t in kept["text"]) + \
                        count_tokens(cfg.separator) * max(0, kept.height - 1)
                    if got < 0.95 * target:
                        print(f"[short-haystack] {cfg.language}-{target}-{ki}: {got:,} of "
                              f"{target:,} tokens ({got/target:.2f}x) -- the pool cannot "
                              f"fill this tier; lower the tier or enlarge the source.",
                              file=sys.stderr)

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
                    meta, cfg, rng, drift_target=drift_target, unit=unit, k=k,
                    prior_ent=prior_ent, prior_lab=prior_lab)

                hs_id = f"{cfg.language}-{'r' if record_mode else ''}{target}-{ki}"
                meta.write_parquet(out / f"meta_{hs_id}.parquet")
                hf.write(json.dumps({
                    "haystack_id": hs_id, "language": cfg.language,
                    "target_tokens": target if not record_mode else count_tokens(hay),
                    "target_records": target if record_mode else None,
                    "n_tokens": count_tokens(hay),
                    "n_examples": meta.height,
                    "drift_target": drift_target, "drift_ok": drift_ok,
                    "haystack": hay,
                }, ensure_ascii=False) + "\n")

                for qi, q in enumerate(questions):
                    kind_counts[q["kind"]] += 1
                    qf.write(json.dumps({
                        "id": f"{hs_id}-q{qi}", "haystack_id": hs_id,
                        "language": cfg.language,
                        "target_tokens": target if not record_mode else None,
                        "target_records": target if record_mode else None,
                        **q,
                    }, ensure_ascii=False) + "\n")
                    n_q += 1

                hs_summary.append({"haystack_id": hs_id, "n_examples": meta.height,
                                   "n_tokens": count_tokens(hay),
                                   # every length in this benchmark is measured with ONE
                                   # tokenizer; n_chars lets a reader re-derive lengths
                                   # for a model whose tokenizer differs (for Turkish the
                                   # difference is large -- see README limitations)
                                   "n_chars": len(hay),
                                   "row_ids": sorted(meta["row_id"].to_list()),
                                   "_tier": target,
                                   "drift_target": drift_target, "drift_ok": drift_ok,
                                   "n_questions": len(questions)})
                print(f"built {hs_id}: {meta.height} examples, {len(questions)} questions"
                      + (f" (drift={drift_target})" if drift_target else " (no drift)"))

    # Overlap between the haystacks of one tier. They are drawn independently
    # from the same pool, so at the longest tiers they necessarily share records
    # and are NOT independent samples: per-tier variance is understated. Ground
    # truth is unaffected (it is computed from the actual haystack), but the
    # figure belongs in the manifest so a reader can weight the evidence.
    tier_overlap: dict[str, dict] = {}
    by_tier: dict[int, list[set]] = {}
    for h in hs_summary:
        by_tier.setdefault(h["_tier"], []).append(set(h["row_ids"]))
    for tier, groups in sorted(by_tier.items()):
        pairs = [(a, b) for i, a in enumerate(groups) for b in groups[i + 1:]]
        if not pairs:
            continue
        jac = [len(a & b) / max(1, len(a | b)) for a, b in pairs]
        tier_overlap[str(tier)] = {
            "n_haystacks": len(groups),
            "mean_jaccard": round(sum(jac) / len(jac), 4),
            "max_jaccard": round(max(jac), 4),
            "pool_fraction_per_haystack": round(
                sum(len(g) for g in groups) / len(groups) / df.height, 4),
        }
    for h in hs_summary:
        h.pop("row_ids", None)
        h.pop("_tier", None)

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
        "cleaning": clean_stats,
        "ranking_feasibility": ceiling_info,
        "tier_overlap": tier_overlap,
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