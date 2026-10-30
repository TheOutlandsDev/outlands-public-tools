"""Actual independent CLI and connected fictional HVAC service/maintenance acceptance."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOLS={'meter-history-checker':'meters.py','maintenance-due-planner':'due.py',
       'work-order-lifecycle-checker':'orders.py','service-completion-checker':'completion.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-hvac-service-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def invoke(self,script,args):
        q=subprocess.run([sys.executable,'-B',str(script),*map(str,args)],capture_output=True,
                         env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(q.stderr,b''); return q.returncode,json.loads(q.stdout)

    def cli(self,name,file=None,extra=(),folder=None):
        folder=folder or ROOT/'tools'/name
        return self.invoke(folder/TOOLS[name],['--input',file or folder/'examples/input.json',*extra])

    def run_value(self,name,value,code=0):
        file=self.root/(name+'.json'); file.write_bytes(encode(value)); actual,result=self.cli(name,file=file)
        self.assertEqual(actual,code); return result

    def test_valid_examples(self):
        for name in TOOLS:
            code,result=self.cli(name); self.assertEqual(code,0); self.assertEqual(result['status'],'PASS')

    def test_independent_source_copies(self):
        for name in TOOLS:
            folder=self.root/name; shutil.copytree(ROOT/'tools'/name,folder,ignore=shutil.ignore_patterns('__pycache__'))
            code,result=self.invoke(folder/'source_check.py',[]); self.assertEqual(code,0); self.assertEqual(result['status'],'SOURCE_MATCH')
            self.assertEqual(self.cli(name,folder=folder)[0],0)

    def test_new_reports_and_overwrite_prevention(self):
        for name in TOOLS:
            out=self.root/(name+'.json'); code,result=self.cli(name,extra=('--out',out))
            self.assertEqual(code,0); self.assertEqual(result,dict(status='PASS',report_written=True))
            raw=out.read_bytes(); self.assertEqual(json.loads(raw),self.cli(name)[1])
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertEqual(out.read_bytes(),raw)

    def test_source_tree_output_refusal(self):
        for name in TOOLS:
            out=ROOT/'tools'/name/'fictional-never-created.json'
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertFalse(out.exists())

    def test_fixed_argument_and_path_errors(self):
        for name in TOOLS:
            code,result=self.cli(name,extra=('--SYNTHETIC_SENTINEL',)); self.assertEqual(code,2)
            self.assertEqual(result,dict(status='ERROR',code='ARGUMENTS_INVALID'))
            code,result=self.cli(name,file=self.root/'SYNTHETIC_SENTINEL.json')
            self.assertEqual(code,2); self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))

    def test_review_examples_retain_due_completion_findings_or_withhold_invalid_histories(self):
        for name,key in zip(TOOLS,['snapshots','assessments','orders','assessments']):
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues'])
            if name in ('meter-history-checker','work-order-lifecycle-checker'):self.assertIsNone(result[key])
            else:self.assertIsNotNone(result[key])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_service_cohort(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        metered=self.run_value('meter-history-checker',example('meter-history-checker'))
        snapshot=metered['snapshots'][0];self.assertEqual(snapshot['total_usage'],12);self.assertEqual(snapshot['reset_count'],1)
        planned=example('maintenance-due-planner');planned['meters']=[{key:snapshot[key] for key in ('id','unit','usage_origin','observed_at','total_usage')}]
        planned['meters'][0]['source_sha256']=metered['input_sha256'];planned['plans'][0]['usage_interval']=7
        due=self.run_value('maintenance-due-planner',planned,1)
        self.assertEqual(due['assessments'][0]['due_state'],'due');self.assertTrue(due['assessments'][0]['due_by_usage']);self.assertFalse(due['schedule_created'])
        # This exercise explicitly supplies an operator-chosen order and asserted work history.
        ordered=example('work-order-lifecycle-checker');ordered['orders'][0]['asset_id']=due['assessments'][0]['asset_id']
        history=self.run_value('work-order-lifecycle-checker',ordered);selected=history['orders'][0]
        completed=example('service-completion-checker');completed['orders']=[{key:selected[key] for key in ('id','asset_id','revision','state')}]
        completed['contracts'][0].update(order_revision=selected['revision'],order_sha256=selected['order_sha256'])
        # A fictional evidence pin is a declaration; the checker does not read its bytes.
        completed['evidence'][0]['sha256']=sha(encode(dict(fixture='fictional-filter-check',result='recorded')))
        result=self.run_value('service-completion-checker',completed)
        self.assertTrue(result['assessments'][0]['completed_under_contract']);self.assertEqual(result['assessments'][0]['order_sha256'],selected['order_sha256'])
        self.assertFalse(result['physical_service_verified']);self.assertFalse(result['evidence_bytes_verified']);self.assertFalse(result['stock_or_orders_changed'])

    def test_completed_order_does_not_establish_service_completion(self):
        selected=json.loads((ROOT/'tools/work-order-lifecycle-checker/examples/input.json').read_text(encoding='utf-8'))
        history=self.run_value('work-order-lifecycle-checker',selected)
        self.assertEqual(history['orders'][0]['state'],'completed');self.assertFalse(history['completion_evidence_checked'])
        contract=json.loads((ROOT/'tools/service-completion-checker/examples/input.json').read_text(encoding='utf-8'))
        contract['contracts'][0]['order_sha256']=history['orders'][0]['order_sha256'];contract['tasks'][0]['outcome']='blocked';contract['parts'][0]['returned']=0
        completion=self.run_value('service-completion-checker',contract,1);row=completion['assessments'][0]
        self.assertFalse(row['completed_under_contract']);self.assertTrue(row['unfinished_tasks']);self.assertTrue(row['parts_findings'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])
