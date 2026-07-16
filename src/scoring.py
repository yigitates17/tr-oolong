"""Frozen scoring for TR-OOLONG. FREEZE POLICY: do not change this file after
the first model run; any change invalidates all previous scores.

Two metrics per question:
  exact   -- 1.0 if the normalized prediction equals the gold answer, else 0.0
  partial -- exact for categorical families; 0.75 ** |y - yhat| for numeric
             families (count, proportion, entity_count), so near-miss counts
             earn partial credit that decays geometrically with error.
"""

import re
import unicodedata

from build_tr_oolong import tr_casefold

NUMERIC_KINDS = ("count", "proportion", "entity_count")


def normalize(s: str, language: str) -> str:
    s = unicodedata.normalize("NFC", str(s)).strip()
    s = tr_casefold(s) if language == "tr" else s.casefold()
    return re.sub(r"\s+", " ", s)


def parse_int(s: str) -> int | None:
    m = re.search(r"-?\d+", str(s))
    return int(m.group()) if m else None


def score(question: dict, prediction: str) -> dict:
    lang = question["language"]
    kind = question["kind"]
    gold = question["answer"]
    if kind in NUMERIC_KINDS:
        y = int(gold)
        yhat = parse_int(prediction)
        if yhat is None:
            return {"exact": 0.0, "partial": 0.0}
        return {"exact": float(yhat == y), "partial": 0.75 ** abs(y - yhat)}
    if kind == "top_k":
        gold_list = [normalize(g, lang) for g in gold]
        pred_list = [normalize(p, lang) for p in re.split(r"[>,]", str(prediction)) if p.strip()]
        exact = float(pred_list == gold_list)
        return {"exact": exact, "partial": exact}
    exact = float(normalize(prediction, lang) == normalize(gold, lang))
    return {"exact": exact, "partial": exact}