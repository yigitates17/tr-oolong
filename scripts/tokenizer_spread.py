"""How many tokens does the SAME Turkish/English content cost under different
tokenizers? Reproduces the comparison in PAPER_NOTES.md / README section 4.3,
this time as a saved, seeded script rather than a one-off REPL command --
the previous table's sampling seed was never recorded anywhere in the repo,
which meant nobody could re-draw the same 3,000 rows to add a new tokenizer
to it. This script IS that record from now on.

Draws N pair-aligned rows from datasets/massive_tr.parquet /
datasets/massive_en.parquet (joined on `pair_id`, so it is the same content
in both languages, not a token-budget-matched approximation), then counts
tokens per row with every tokenizer below and reports the TR/EN ratio.

No special tokens are added by any tokenizer here (add_special_tokens=False /
bos=False, eos=False / raw tiktoken.encode) so every row is an apples-to-apples
count of the content alone.

Usage:
    python scripts/tokenizer_spread.py --n 3000 --seed 42
"""
import argparse
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]


def counters():
    """Yields (name, encode_fn). Built lazily so a missing optional dependency
    only disables its own row, not the whole comparison."""
    import tiktoken
    for enc in ("p50k_base", "cl100k_base", "o200k_base"):
        e = tiktoken.get_encoding(enc)
        yield enc, (lambda s, e=e: len(e.encode(s)))

    from transformers import AutoTokenizer
    for hf_id, label in (
        ("Qwen/Qwen3-8B", "Qwen3-8B"),
        ("bert-base-multilingual-cased", "mBERT cased"),
        ("dbmdz/bert-base-turkish-cased", "BERTurk"),
    ):
        tok = AutoTokenizer.from_pretrained(hf_id)
        yield label, (lambda s, tok=tok: len(tok.encode(s, add_special_tokens=False)))

    try:
        from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
        # mistral-large-2411 -> SentencePieceTokenizer (v3, pre-Tekken)
        # mistral-small-2409 -> Tekkenizer (tiktoken-based BPE, the current family)
        for model_id, label in (
            ("mistral-large-2411", "Mistral SentencePiece (large-2411)"),
            ("mistral-small-2409", "Mistral Tekken (small-2409)"),
        ):
            tok = MistralTokenizer.from_model(model_id, strict=True).instruct_tokenizer.tokenizer
            yield label, (lambda s, tok=tok: len(tok.encode(s, bos=False, eos=False)))
    except ImportError:
        print("[skip] mistral-common not installed -- pip install mistral-common[sentencepiece]",
              file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    tr = pl.read_parquet(ROOT / "datasets/massive_tr.parquet")
    en = pl.read_parquet(ROOT / "datasets/massive_en.parquet")
    joined = tr.join(en, on="pair_id", suffix="_en")
    sample = joined.sample(min(args.n, joined.height), seed=args.seed)
    tr_text, en_text = sample["utt"].to_list(), sample["utt_en"].to_list()
    print(f"sampled {sample.height} pair-aligned MASSIVE utterances "
          f"(seed={args.seed}, out of {joined.height} available)\n")

    print(f"{'tokenizer':<38}{'TR tokens':>10}{'EN tokens':>10}{'TR/EN':>9}")
    print("-" * 67)
    for name, enc in counters():
        tr_tok = sum(enc(t) for t in tr_text)
        en_tok = sum(enc(t) for t in en_text)
        print(f"{name:<38}{tr_tok:>10,}{en_tok:>10,}{tr_tok / en_tok:>9.2f}x")


if __name__ == "__main__":
    main()
