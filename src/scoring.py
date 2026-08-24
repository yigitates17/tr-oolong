"""Frozen scoring for TR-OOLONG.

FREEZE POLICY: do not change this file after the first model run; any change
invalidates all previous scores. Nothing has been frozen yet -- v0.4.0 is the
last chance to add a metric.

Three numbers per question:

  exact     1.0 if the normalized prediction equals the gold answer, else 0.0.

  partial   OOLONG parity. Exact for categorical families; 0.75 ** |y - yhat|
            for numeric ones. Kept UNCHANGED so results are directly comparable
            with Bertsch et al. (2025), who use the same formula.

  relative  Scale-free numeric credit: max(0, 1 - |y - yhat| / max(y, 1)).
            Added in v0.4.0 because `partial` is degenerate at this benchmark's
            magnitudes. OOLONG runs at 8K-128K tokens where counts are small;
            TR-OOLONG `count` answers have a median of ~1,000 and reach 12,225,
            and 0.75**50 is 6e-7 -- so `partial` collapses to `exact` and a
            model off by 2% scores the same as one off by 100%. Both are
            reported; `partial` is the comparability metric, `relative` is the
            informative one.

Categorical matching also accepts an ASCII-folded form, so a model that answers
'nötr' where the gold label is the corpus's 'notr' (or 'artti' for 'arttı') is
not penalised for an orthographic artifact of the source data.
"""

import re
import unicodedata

from build_tr_oolong import tr_casefold

NUMERIC_KINDS = ("count", "proportion", "entity_count")


def normalize(s: str, language: str) -> str:
    s = unicodedata.normalize("NFC", str(s)).strip()
    s = tr_casefold(s) if language == "tr" else s.casefold()
    return re.sub(r"\s+", " ", s)


def ascii_fold(s: str) -> str:
    """Strip diacritics: 'nötr' -> 'notr', 'arttı' -> 'artti'.

    Used only as a FALLBACK equality test for categorical answers, never to
    build the gold answer. Turkish label spaces here (olumlu/olumsuz/nötr,
    48 ASCII intent names) stay distinct under folding, so this cannot merge
    two different correct answers.
    """
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").replace("ı", "i")


def parse_int(s: str) -> int | None:
    m = re.search(r"-?\d+", str(s))
    return int(m.group()) if m else None


def _cat_eq(gold: str, pred: str, lang: str) -> float:
    g, p = normalize(gold, lang), normalize(pred, lang)
    if g == p:
        return 1.0
    return float(ascii_fold(g) == ascii_fold(p))


def score(question: dict, prediction: str) -> dict:
    lang = question["language"]
    kind = question["kind"]
    gold = question["answer"]
    if kind in NUMERIC_KINDS:
        y = int(gold)
        yhat = parse_int(prediction)
        if yhat is None:
            return {"exact": 0.0, "partial": 0.0, "relative": 0.0}
        err = abs(y - yhat)
        return {"exact": float(yhat == y),
                "partial": 0.75 ** err,
                "relative": max(0.0, 1.0 - err / max(abs(y), 1))}
    if kind == "top_k":
        gold_list = [normalize(g, lang) for g in gold]
        pred_list = [normalize(p, lang) for p in re.split(r"[>,]", str(prediction)) if p.strip()]
        exact = float(pred_list == gold_list)
        return {"exact": exact, "partial": exact, "relative": exact}
    exact = _cat_eq(gold, prediction, lang)
    return {"exact": exact, "partial": exact, "relative": exact}
