"""Regression checks for pre-freeze correctness, without remote calls."""
import sys
import unittest
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build_tr_oolong import Config, clean, resolve_template, _label_vs_label
from scoring import parse_int, score


class Contracts(unittest.TestCase):
    def test_conflicts_removed_after_sentiment_mapping(self):
        frame = pl.DataFrame({"text": ["great item", "great item", "same text", "same text"],
                              "label": ["7", "10", "1", "10"], "entity": ["x"] * 4})
        cfg = Config(source_path="", language="en", drop_label_leakage=False,
                     label_translation={"7": "positive", "10": "positive", "1": "negative"})
        stats = {}
        got = clean(frame, cfg, stats)
        self.assertEqual(got["text"].to_list(), ["great item"])
        self.assertEqual(stats["rows_dropped_conflicting_labels"], 2)

    def test_equality_is_exact_by_default(self):
        cfg = Config(source_path="")
        self.assertEqual(cfg.lvl_same_tol, 0)
        self.assertIsNone(_label_vs_label(276, 271, .1, cfg.lvl_same_tol, 10))
        self.assertEqual(_label_vs_label(271, 271, .1, cfg.lvl_same_tol, 10), "same")

    def test_contract_survives_custom_templates(self):
        for lang in ("tr", "en"):
            cfg = Config(source_path="", language=lang, question_templates={"proportion": "{label}"})
            self.assertIn("→ 3", resolve_template(cfg, "proportion", "percent"))
            for kind in ("most_common", "least_common", "second_most"):
                self.assertIn("Yalnızca" if lang == "tr" else "Among only", resolve_template(cfg, kind))

    def test_numeric_parser_never_truncates(self):
        for bad in ("2.5", "2,5", "1,000", "12 or 13", "answer: 12", "12\n13", "NaN", ""):
            self.assertIsNone(parse_int(bad), bad)
        self.assertEqual(parse_int(" 1000\n"), 1000)
        self.assertEqual(parse_int("-2"), -2)

    def test_close_invalid_responses(self):
        q = {"language": "tr", "kind": "close_comparison", "answer": "olumlu"}
        for bad in ("eşit", "olumlu ve olumsuz", "", "olumsuz"):
            self.assertEqual(score(q, bad)["primary"], 0)
        self.assertEqual(score(q, "olumlu")["primary"], 1)


if __name__ == "__main__":
    unittest.main()
