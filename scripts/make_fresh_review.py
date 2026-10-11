"""A fresh blind sheet that checks the frozen label groupings (v0.11).

The intent grouping (MASSIVE's 18 scenarios, general_quirky removed) and the
complaint grouping (12 groups, two catch-alls removed) were chosen after
seeing part of the first review. This sheet draws records that were NOT in
that review, labelled directly with the groups, so the agreement it measures
was not used to choose them.

    .venv/bin/python scripts/make_fresh_review.py
    .venv/bin/python scripts/label_tool.py --root scratch/prefreeze/human_review_fresh

It refuses to overwrite an existing sheet. The source key stays in
private_key.json, which the reviewer does not open.
"""
import csv
import hashlib
import json
import random
from pathlib import Path

import polars as pl

ROOT = Path("scratch/prefreeze")
OUT = ROOT / "human_review_fresh"
PER_INTENT_GROUP, PER_COMPLAINT_GROUP = 2, 3

COMPLAINT_GROUPS = {
    "elektronik ve ev aletleri": ["elektronik", "bilgisayar", "beyaz eşya", "küçük ev aletleri"],
    "ev, yapı ve temizlik": ["mobilya ve ev tekstili", "emlak ve inşaat", "mutfak araç gereç", "temizlik"],
    "eğlence, spor ve etkinlik": ["mekan ve eğlence", "etkinlik ve organizasyon", "spor"],
    "enerji ve kamu hizmetleri": ["enerji", "kamu hizmetleri"],
    "internet ve medya": ["internet", "medya"],
    "ulaşım ve turizm": ["ulaşım", "turizm"],
    "finans ve sigorta": ["finans", "sigortacılık"],
    "gıda ve içecek": ["gıda", "içecek"],
    "giyim ve aksesuar": ["giyim", "mücevher saat gözlük"],
    "sağlık ve kişisel bakım": ["sağlık", "kişisel bakım ve kozmetik"],
    "otomotiv": ["otomotiv"],
    "eğitim": ["eğitim"],
}
COMPLAINT_MAP = {old: new for new, olds in COMPLAINT_GROUPS.items() for old in olds}
INTENT_DROP = {"general_quirky"}
SCENARIO_GLOSS = {
    "alarm": "alarm kurma, sorma, silme", "audio": "ses düzeyi, sessize alma",
    "calendar": "takvim, hatırlatıcı, etkinlik kaydı", "cooking": "yemek tarifi",
    "datetime": "saat, tarih, saat dilimi", "email": "e-posta okuma, gönderme, kişiler",
    "general": "fıkra, şaka", "iot": "akıllı ev: ışıklar, kahve makinesi, süpürge",
    "lists": "liste oluşturma, sorma, silme", "music": "müzik beğenisi, çalan şarkı bilgisi",
    "news": "haberler", "play": "müzik, radyo, podcast, sesli kitap, oyun açma",
    "qa": "bilgi soruları, tanım, matematik, döviz, borsa",
    "recommendation": "etkinlik, mekan, film önerisi", "social": "sosyal medya paylaşımı veya sorgusu",
    "takeaway": "yemek siparişi", "transport": "ulaşım, taksi, bilet, trafik", "weather": "hava durumu",
}


def records(subset):
    seen = {}
    for m in sorted((ROOT / "test" / f"{subset}_out").glob("meta_*.parquet")):
        for t, l in pl.read_parquet(m, columns=["text", "label"]).iter_rows():
            seen.setdefault(t, l)
    return seen


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; refusing to overwrite human work.")
    reviewed = set()
    for f in (ROOT / "human_review").glob("review_*.csv"):
        reviewed |= {r["text"] for r in csv.DictReader(f.open(encoding="utf-8-sig"))}
    for f in (ROOT / "human_review" / "removed_neutral").glob("review_*.csv"):
        reviewed |= {r["text"] for r in csv.DictReader(f.open(encoding="utf-8-sig"))}

    rows, key = [], {}
    plans = [
        ("tr_intent_paired", lambda l: None if l in INTENT_DROP else l.split("_")[0], PER_INTENT_GROUP),
        ("sikayet_tr", lambda l: COMPLAINT_MAP.get(l), PER_COMPLAINT_GROUP),
    ]
    for subset, group_of, per_group in plans:
        by_group = {}
        for text, label in records(subset).items():
            g = group_of(label)
            if g and text not in reviewed:
                by_group.setdefault(g, []).append((text, label))
        rng = random.Random("fresh-review-v1:" + subset)
        labels = sorted(by_group)
        for g in labels:
            for text, label in rng.sample(sorted(by_group[g]), per_group):
                rid = hashlib.sha256((subset + ":" + text).encode()).hexdigest()[:16]
                rows.append({"review_id": rid, "dataset": subset, "text": text,
                             "available_labels": " | ".join(labels + ["uncertain"]),
                             "human_label": "", "notes": ""})
                key[rid] = {"dataset": subset, "source_label": g, "original_label": label}
    random.Random("fresh-review-v1:order").shuffle(rows)

    OUT.mkdir(parents=True)
    with (OUT / "review_tr.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (OUT / "private_key.json").write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    gloss = "; ".join(f"{k} = {v}" for k, v in SCENARIO_GLOSS.items())
    tasks = {
        "tr_intent_paired": "Sesli asistan isteğinin konusunu (senaryosunu) seç. " + gloss + ".",
        "sikayet_tr": ("Şikâyetin ilgili olduğu ürün veya hizmet grubunu seç. Şirket ve markalar "
                       "hakkındaki genel bilgini kullanabilirsin (ör. Köfteci Yusuf bir yemek zinciridir)."),
    }
    (OUT / "task_definitions.json").write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(rows)} records -> {OUT}/review_tr.csv")


if __name__ == "__main__":
    main()
