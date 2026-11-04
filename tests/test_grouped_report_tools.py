"""Fictional grouped-report CLI acceptance and conservative failure cases."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/'tools'
TOOLS={
 'grouped-report-contract-checker':'contracts.py',
 'group-membership-coverage-checker':'membership.py',
 'grouped-aggregate-reconciler':'aggregates.py',
 'grouped-report-scenario-comparator':'scenarios.py',
}
def invoke(name,value=None):
    folder=ROOT/name
    if value is None:path=folder/'examples/input.json';return run(name,path)
    with tempfile.TemporaryDirectory(prefix='fictional-group-report-') as temp:
        path=Path(temp)/'input.json'
        path.write_text(json.dumps(value,ensure_ascii=True)+'\n',encoding='utf-8')
        return run(name,path)
def run(name,path):
    q=subprocess.run([sys.executable,'-B',str(ROOT/name/TOOLS[name]),'--input',str(path)],capture_output=True,text=True)
    if q.stderr:raise AssertionError(q.stderr)
    return q.returncode,json.loads(q.stdout)
def example(name):return json.loads((ROOT/name/'examples/input.json').read_text(encoding='utf-8'))

class GroupedReports(unittest.TestCase):
    def test_all_four_examples_and_source_pins(self):
        for name in TOOLS:
            code,result=invoke(name)
            self.assertEqual(code,1 if name.endswith('scenario-comparator') else 0)
            self.assertEqual(result['status'],'REVIEW_REQUIRED' if code else 'PASS')
            q=subprocess.run([sys.executable,'-B',str(ROOT/name/'source_check.py')],capture_output=True,text=True)
            self.assertEqual(q.returncode,0,q.stderr+q.stdout)
            self.assertEqual(json.loads(q.stdout)['status'],'SOURCE_MATCH')

    def test_duplicate_or_missing_contributors_withhold_scope(self):
        for name in ('group-membership-coverage-checker','grouped-aggregate-reconciler'):
            for ids in (['job_a','job_a'],['job_a']):
                value=example(name);value['claims'][0]['groups'][0]['row_ids']=ids
                code,result=invoke(name,value)
                self.assertEqual(code,1);self.assertIsNone(result['qualified_scope_sha256'])
                self.assertTrue(any(i['code'] in ('DUPLICATE_CONTRIBUTOR','MEMBERSHIP_MISMATCH') for i in result['issues']))

    def test_changed_aggregate_withholds_scope(self):
        name='grouped-aggregate-reconciler';value=example(name)
        value['claims'][0]['groups'][0]['values']['hours_sum']='3.00'
        code,result=invoke(name,value)
        self.assertEqual(code,1);self.assertIsNone(result['qualified_scope_sha256'])
        self.assertIn('AGGREGATE_MISMATCH',[i['code'] for i in result['issues']])

    def test_false_definition_pin_withholds_assessment(self):
        name='group-membership-coverage-checker';value=example(name)
        value['claims'][0]['definition_sha256']='0'*64
        code,result=invoke(name,value)
        self.assertEqual(code,1);self.assertIsNone(result['assessment'])
        self.assertIn('SNAPSHOT_MISMATCH',[i['code'] for i in result['issues']])

    def test_all_null_measure_and_null_group(self):
        name='grouped-aggregate-reconciler';value=example(name)
        definition=value['definitions'][0];snapshot=value['snapshots'][0]
        snapshot['rows']=[{'id':'job_a','values':{'area':'north','hours':None}}]
        import hashlib
        raw=(json.dumps(snapshot,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode()
        claim=value['claims'][0];claim['snapshot_sha256']=hashlib.sha256(raw).hexdigest()
        claim['groups']=[{'id':'north','key':['north'],'row_ids':['job_a'],'values':{'hours_sum':None,'jobs':1,'known':0}}]
        code,result=invoke(name,value)
        self.assertEqual(code,0,result)
        self.assertEqual(result['assessment'][0]['expected'][0]['values']['hours_sum'],None)

    def test_duplicate_keys_refused(self):
        name='grouped-report-contract-checker'
        with tempfile.TemporaryDirectory(prefix='fictional-group-report-') as temp:
            path=Path(temp)/'duplicate.json';path.write_text('{"format":"x","format":"y"}',encoding='utf-8')
            code,result=run(name,path)
        self.assertEqual(code,2);self.assertEqual(result['code'],'JSON_DUPLICATE_KEY')

if __name__=='__main__':unittest.main()
