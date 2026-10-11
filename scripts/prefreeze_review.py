"""Create blind review sheets and apply human judgments to question margins.

Never overwrites an existing sheet. A sample is a label-quality screen, not
certification of every winner. Observed corrected margins are reported with
explicit unreviewed-record bounds; pending review never counts as a pass.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random
import sys
import polars as pl
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"), str(ROOT/"scripts")]
from prepare_prefreeze import fingerprint
from task_contract import task_description

SETS=["tr_intent_paired","sikayet_tr","interpress_tr","sinema_tr","musteri_tr","vitamins_tr",
      "en_intent_paired","marc_en","amazon_hpc_en"]
FIELDS=["review_id","dataset","text","available_labels","human_label","notes"]


def prepare(root, per_set):
    out=root/"human_review"
    if out.exists():raise SystemExit("Review folder exists; refusing to overwrite human work.")
    out.mkdir()
    sheets={"tr":[],"en":[]}; key={}; definitions={}
    for name in SETS:
        d=root/"test"/f"{name}_out"
        man=json.loads((d/"manifest.json").read_text());lang=man['config']['language']
        qs=[json.loads(l) for l in (d/"questions.jsonl").read_text().splitlines()]
        core=[q for q in qs if q['role']=='core']
        compared={q[k] for q in core for k in ('label_a','label_b')}
        pool={}
        for hid in sorted({q['haystack_id'] for q in core}):
            meta=pl.read_parquet(d/f"meta_{hid}.parquet")
            for t,l in zip(meta['text'],meta['label']):pool[fingerprint(t,lang)]=(t,l)
        strata={"compared":[h for h,(_,l) in pool.items() if l in compared],
                "background":[h for h,(_,l) in pool.items() if l not in compared]}
        rng=random.Random('human-review-v1:'+name)
        for stratum, hashes in strata.items():
            quota=per_set if not strata['background'] else per_set//2
            selected=rng.sample(sorted(hashes),min(quota,len(hashes)))
            for h in selected:
                t,l=pool[h]; rid=hashlib.sha256((name+':'+h).encode()).hexdigest()[:16]
                sheets[lang].append(dict(zip(FIELDS,[rid,name,t,' | '.join(man['label_names'])+' | uncertain','',''])))
                key[rid]={'dataset':name,'language':lang,'fingerprint':h,'source_label':l,'stratum':stratum,
                          'population':len(hashes),'sample_size':len(selected)}
        definitions[name]=task_description(name,lang)
    for lang,rows in sheets.items():
        random.Random('blind-order:'+lang).shuffle(rows)
        with (out/f"review_{lang}.csv").open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    (out/'private_key.json').write_text(json.dumps(key,indent=2,ensure_ascii=False)+'\n')
    (out/'task_definitions.json').write_text(json.dumps(definitions,indent=2,ensure_ascii=False)+'\n')
    (out/'README.md').write_text('''Review the CSVs without opening private_key.json. Read task_definitions.json first.

For each row, enter exactly one of available_labels in human_label. Use
`uncertain` when the text does not determine a single label. Notes are optional.
Do not infer an unseen rating or product category. Keep row IDs and text intact.
The English sheet is a separate task; do not use a translated counterpart to
decide its label. A second independent reviewer can fill a separate copy.

This first batch screens label quality, including background labels that can
be mistaken for the compared labels. It is not exhaustive winner certification.
Further adjudication depends on what this batch reveals. Previous annotation
files have been preserved, but are not copied into this blind sheet.

After saving, run:

    .venv/bin/python scripts/prefreeze_review.py --stats

This reports completion, disagreements, uncertainty and observed effects on
question winners. It cannot declare unreviewed records correct.
''',encoding='utf-8')
    print('Prepared blind sheets:',{l:len(r) for l,r in sheets.items()},flush=True)


def analyze(root):
    out=root/'human_review';key=json.loads((out/'private_key.json').read_text()); judgments={}; summary=defaultdict(Counter)
    invalid=[];seen=set()
    for p in sorted(out.glob('review_*.csv')):
        for row in csv.DictReader(p.open(encoding='utf-8-sig')):
            rid=row['review_id']
            if rid not in key or rid in seen:invalid.append(rid);continue
            seen.add(rid); item=key[rid];name=item['dataset'];lab=row['human_label'].strip()
            summary[name]['total']+=1
            if not lab:summary[name]['pending']+=1;continue
            if lab not in row['available_labels'].split(' | '):invalid.append(rid);continue
            if fingerprint(row['text'],item['language'])!=item['fingerprint']:invalid.append(rid);continue
            summary[name]['completed']+=1
            summary[name]['uncertain' if lab=='uncertain' else 'agrees' if lab==item['source_label'] else 'disagrees']+=1
            # Verdicts given after label_tool reveals the source label; the blind label above is the measurement.
            if row.get('after_reveal'):summary[name]['after_reveal:'+row['after_reveal']]+=1
            if row.get('revised_after_reveal'):summary[name]['revised_after_reveal']+=1
            # Same source text may appear in both intent subsets.
            judgments[(item['language'],item['fingerprint'])]=lab
    missing=set(key)-seen
    invalid.extend(sorted(missing))
    impacts=[]
    for d in sorted((root/'test').glob('*_out')):
        qs=[json.loads(l) for l in (d/'questions.jsonl').read_text().splitlines()]
        by_h=defaultdict(list)
        for q in qs:
            if q['role']=='core':by_h[q['haystack_id']].append(q)
        for hid,group in by_h.items():
            m=pl.read_parquet(d/f'meta_{hid}.parquet');lang=group[0]['language']
            records=[(l,judgments.get((lang,fingerprint(t,lang)))) for t,l in zip(m['text'],m['label'])]
            for q in group:
                a,b=q['label_a'],q['label_b']
                contribution=lambda l:int(l==a)-int(l==b)
                gold=sum(contribution(l) for l,_ in records)
                corrected=sum(contribution(j if j and j!='uncertain' else l) for l,j in records)
                known=sum(contribution(j) for _,j in records if j and j!='uncertain')
                unknown=sum(j is None or j=='uncertain' for _,j in records)
                impacts.append({'uid':q['uid'],'gold_margin':gold,'observed_corrected_margin':corrected,
                                'observed_winner_changed_or_tied':gold*corrected<=0,
                                'unreviewed_or_uncertain':unknown,'possible_margin_interval':[known-unknown,known+unknown],
                                'winner_certified':(known-unknown>0 if gold>0 else known+unknown<0)})
    completed=sum(s['completed'] for s in summary.values());total=len(key)
    report={'annotation_status':'complete' if completed==total and not invalid else 'pending',
            'completed':completed,'total':total,'invalid_or_missing_ids':invalid,
            'by_dataset':dict(summary),'question_impacts':impacts,
            'note':'Counts describe this stratified screening sample; do not pool into a population error rate. Unreviewed labels are not certified.'}
    (root/'reports/human_review.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='question_impacts'},indent=2,ensure_ascii=False))
    if invalid:raise SystemExit('Invalid annotations: see report')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('scratch/prefreeze'))
    ap.add_argument('--per-set',type=int,default=40);ap.add_argument('--stats',action='store_true')
    args=ap.parse_args()
    analyze(args.root) if args.stats else prepare(args.root,args.per_set)
