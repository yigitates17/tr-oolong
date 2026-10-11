import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_eval


class EvaluationContract(unittest.TestCase):
    def test_failures_count_and_resume_is_versioned(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            man={'config':{'separator':'|||','language':'en','dataset':'fixture','out_dir':str(d)},
                 'label_names':['positive','negative']}
            (d/'manifest.json').write_text(json.dumps(man))
            (d/'haystacks.jsonl').write_text(json.dumps({'haystack_id':'h','haystack':'text'})+'\n')
            qs=[{'uid':f'fixture:{i}','dataset':'fixture','id':str(i),'haystack_id':'h',
                 'language':'en','kind':'close_comparison','role':'core','core_document':True,
                 'question':'Which label?','answer':'positive'} for i in range(2)]
            (d/'questions.jsonl').write_text(''.join(json.dumps(q)+'\n' for q in qs))
            args=argparse.Namespace(model='mock',base_url='http://unused',api_key='',max_tokens=20,
                                    timeout=1,max_questions=0)
            with patch.object(run_eval,'chat',side_effect=[('positive',{}),TimeoutError('fixture')]):
                result=run_eval.run_set(d,args)
            group=result['roles']['core_document']
            self.assertEqual(group['coverage'],.5)
            self.assertEqual(group['primary_all_eligible'],.5)
            self.assertEqual(group['primary_answered'],1)
            with patch.object(run_eval,'chat',return_value=('positive',{})) as mock:
                resumed=run_eval.run_set(d,args)
                self.assertEqual(mock.call_count,1)
            self.assertEqual(resumed['roles']['core_document']['primary_all_eligible'],1)
            args.max_tokens=21
            with patch.object(run_eval,'chat',return_value=('positive',{})) as mock:
                changed=run_eval.run_set(d,args)
                self.assertEqual(mock.call_count,2)
            self.assertNotEqual(changed['predictions'],result['predictions'])


if __name__=='__main__':unittest.main()
