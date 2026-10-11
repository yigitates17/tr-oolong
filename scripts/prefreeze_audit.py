"""Independent contracts, paired alignment, and local shortcut diagnostics.

No LLM calls. A development-trained bag-of-words classifier scans all text;
top-k diagnostics then reveal gold labels only for selected rows. Scores are
diagnostics, not universal limits on retrieval or proof of full reading.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from verify_release import verify, verify_global_uids
from build_tr_oolong import normalize_for_dedup
from scoring import score


def words(t):
    return re.findall(r"\w+", t.replace("İ", "i").replace("I", "ı").casefold())


def fit_nb(frame):
    labs = sorted(set(frame["label"].to_list()))
    index = {l: i for i, l in enumerate(labs)}
    counts = [Counter() for _ in labs]
    prior = np.ones(len(labs))
    for t, l in zip(frame["text"], frame["label"]):
        counts[index[l]].update(words(t)); prior[index[l]] += 1
    total = Counter()
    for c in counts:
        total.update(c)
    vocabulary = [w for w, n in total.most_common(30000) if n >= 2]
    vocab = {w: i for i, w in enumerate(vocabulary)}
    mat = np.ones((len(labs), len(vocab)))
    for i, counts_i in enumerate(counts):
        for w, n in counts_i.items():
            if w in vocab: mat[i, vocab[w]] += n
    logp = np.log(mat) - np.log(mat.sum(axis=1, keepdims=True))
    prior = np.log(prior / prior.sum())
    def predict(t):
        ids = [vocab[w] for w in words(t) if w in vocab]
        lp = prior + logp[:, ids].sum(axis=1)
        return lp - np.logaddexp.reduce(lp)
    return labs, predict


def audit(root, split, classifiers=True):
    dirs = sorted((root / split).glob("*_out"))
    failures = verify_global_uids([str(d) for d in dirs])
    rows, questions_by_set = [], {}
    for d in dirs:
        s = d.name.removesuffix("_out")
        result = verify(str(d))
        failures.extend(x for x in result if "__checked__" not in x)
        qs = [json.loads(l) for l in (d / "questions.jsonl").read_text().splitlines()]
        questions_by_set[s] = qs
        source = pl.read_parquet(root / "sources" / f"{s}_{split}.parquet")
        source_labels = dict(zip(source["text"], source["label"]))
        dev = pl.read_parquet(root / "sources" / f"{s}_dev.parquet")
        prior = Counter(dev["label"])
        if classifiers and any(q["role"] == "core" for q in qs):
            labs, predict = fit_nb(dev)
            li = {l: i for i, l in enumerate(labs)}
        else:
            predict = None
        cache = {}
        core_i = 0
        for path in sorted(d.glob("meta_*.parquet")):
            hid = path.name[5:-8]
            meta = pl.read_parquet(path)
            labels = meta["label"].to_list(); texts = meta["text"].to_list()
            counts = Counter(labels); n = len(labels)
            if any(source_labels.get(t) != l for t, l in zip(texts, labels)):
                failures.append(f"{s}/{hid}: label not in prepared source")
            if len({normalize_for_dedup(t, qs[0]["language"]) for t in texts}) != n:
                failures.append(f"{s}/{hid}: repeated normalized text")
            for q in (q for q in qs if q["haystack_id"] == hid):
                kind = q["kind"]
                if score(q, q["answer"])["exact"] != 1:
                    failures.append(f"{q['uid']}: gold fails scorer")
                if kind in ("most_common", "least_common", "second_most") and not any(w in q["question"] for w in ("Yalnızca", "Among only")):
                    failures.append(f"{q['uid']}: missing candidate scope")
                if kind == "proportion" and "→ 3" not in q["question"]:
                    failures.append(f"{q['uid']}: missing half rounding")
                if kind == "label_vs_label" and q["answer_key"] == "same" and counts[q["label_a"]] != counts[q["label_b"]]:
                    failures.append(f"{q['uid']}: unequal counts called equal")
                if q["role"] != "core": continue
                a, b = q["label_a"], q["label_b"]
                ca, cb = counts[a], counts[b]
                gold_a = q["answer"] == a
                def right(x, y):
                    return .5 if x == y else float((x > y) == gold_a)
                rng = np.random.default_rng(int(hashlib.sha256(q["uid"].encode()).hexdigest()[:16], 16))
                measures = {"first_option": float(gold_a), "alphabetical": float(q["answer"] == min(a,b)),
                            "development_prior": right(prior[a], prior[b]),
                            "qid_parity": float(q["answer"] == (a if int(q["id"].rsplit('-q',1)[1]) % 2 == 0 else b))}
                # A release-order attack is calculated below in actual file order.
                for f in (.05, .25, .5, .95):
                    k = max(1, round(n*f))
                    draws = rng.multivariate_hypergeometric([ca, cb, n-ca-cb], k, size=100)
                    measures[f"random_oracle_{f:g}"] = float(np.mean([right(x[0],x[1]) for x in draws]))
                for strategy, ids in (("prefix", range(max(1, n//20))),
                                      ("stride", range(0, n, 20))):
                    c = Counter(labels[i] for i in ids)
                    measures[strategy+"_oracle_0.05"] = right(c[a],c[b])
                # Confidence-based early stopping, capped at 50% of records.
                order = rng.permutation(n); read = max(2,n//20)
                while True:
                    sample = [labels[i] for i in order[:read]]
                    x,y=sample.count(a),sample.count(b)
                    if abs(x-y) > 1.96*math.sqrt(max(x+y,1)) or read >= n//2: break
                    read=min(n//2,read+max(1,n//20))
                measures["adaptive_oracle"] = right(x,y)
                measures["adaptive_fraction"] = read/n
                measures["literal_keyword"] = right(sum(a.replace('_',' ') in t.casefold() for t in texts),
                                                       sum(b.replace('_',' ') in t.casefold() for t in texts))
                if predict and a in li and b in li:
                    for t in texts:
                        if t not in cache: cache[t]=predict(t)
                    post=np.array([cache[t] for t in texts])
                    pred=[labs[i] for i in post.argmax(axis=1)]
                    measures["full_development_nb"] = right(pred.count(a),pred.count(b))
                    rank=np.argsort(-np.maximum(post[:,li[a]],post[:,li[b]]))[:max(1,round(.1*n))]
                    c=Counter(labels[i] for i in rank)
                    measures["topic_oracle_0.1"] = right(c[a],c[b])
                gap=abs(ca-cb)
                rows.append({"uid":q["uid"],"dataset":s,"document":q["haystack_uid"],
                             "origin":"core_document" if q.get("core_document") else "ordinary",
                             "gap":gap,"min_direct_flips_to_reverse":gap//2+1,
                             "min_direct_flips_to_tie_or_reverse":(gap+1)//2,
                             "human_stability":"unverified", "measures":measures})
        core=[q for q in qs if q.get("core_document")]
        lookup={r["uid"]:r for r in rows if r["dataset"]==s}
        for i,q in enumerate(core):
            lookup[q["uid"]]["measures"]["release_alternation"] = float(q["answer"]==q["label_a" if i%2==0 else "label_b"])
        print(split, s, len(qs), "questions; checks", "PASS" if not failures else "FAIL", flush=True)
    # Both question semantics and the complete label sequence must align.
    a,b="tr_intent_paired","en_intent_paired"
    if a in questions_by_set and b in questions_by_set:
        aa,bb=questions_by_set[a],questions_by_set[b]
        key=lambda q:(q['id'][3:],q['kind'],q.get('label'),q.get('label_a'),q.get('label_b'),q.get('answer_key',q['answer']))
        if [key(q) for q in aa] != [key(q) for q in bb]: failures.append("paired-intent questions differ")
        for p in (root/split/f"{a}_out").glob("meta_*.parquet"):
            peer=root/split/f"{b}_out"/p.name.replace("meta_tr-","meta_en-",1)
            if not peer.exists() or pl.read_parquet(p)["label"].to_list()!=pl.read_parquet(peer)["label"].to_list():
                failures.append(f"paired labels differ: {p.name}")
    preparation=json.loads((root/"preparation.json").read_text())
    for p,digest in preparation["published_sha256"].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=digest: failures.append("published release modified: "+p)
    summary={}
    for origin in ("core_document","ordinary"):
        group=[r for r in rows if r['origin']==origin]
        metrics=defaultdict(list)
        for r in group:
            for k,v in r['measures'].items():metrics[k].append(v)
        summary[origin]={"n":len(group),"documents":len({r['document'] for r in group}),
                         "means":{k:float(np.mean(v)) for k,v in metrics.items()},
                         "n_per_measure":{k:len(v) for k,v in metrics.items()}}
    payload={"status":"PASS" if not failures else "FAIL", "failures":failures,
             "scope":"Structural and contract checks on every question; shortcuts on core questions. NB trained only on development text. Human label validity is pending.",
             "summary":summary,"questions":rows}
    (root/"reports"/f"audit_{split}.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(summary,indent=2),flush=True)
    if failures: raise SystemExit("\n".join(failures))


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=Path("scratch/prefreeze"))
    ap.add_argument("--split",choices=("dev","test"),default="test")
    ap.add_argument("--no-classifiers",action="store_true")
    args=ap.parse_args();audit(args.root,args.split,not args.no_classifiers)
