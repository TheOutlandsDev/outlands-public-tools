"""Actual independent CLI and connected fictional resource/flow acceptance."""
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
TOOLS={'resource-reservation-checker':'reservations.py','assignment-eligibility-checker':'assignments.py',
       'process-event-duration-analyzer':'durations.py','flow-balance-reconciler':'flows.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-resource-flow-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_retain_findings_or_withhold_invalid_history(self):
        for name,key in zip(TOOLS,['summary','assessments','durations','balances']):
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1); self.assertEqual(result['status'],'REVIEW_REQUIRED')
            if name=='process-event-duration-analyzer': self.assertIsNone(result[key])
            else: self.assertIsNotNone(result[key]); self.assertTrue(result['issues'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_cohort(self):
        selected=json.loads((ROOT/'tools/assignment-eligibility-checker/examples/input.json').read_text(encoding='utf-8'))
        eligibility=self.run_value('assignment-eligibility-checker',selected)
        self.assertTrue(all(row['eligible_under_declarations'] for row in eligibility['assessments']))
        task_by_id={row['id']:row for row in selected['tasks']}
        reservations=[]
        for proposal in eligibility['assessments']:
            task=task_by_id[proposal['task_id']]
            reservations.append(dict(id=proposal['id'],resource_id=proposal['resource_id'],start=task['start'],end=task['end'],units=task['units']))
        capacity=self.run_value('resource-reservation-checker',dict(format='outlands-resource-reservations-v1',resources=selected['resources'],reservations=reservations))
        self.assertEqual(capacity['resource_contract_sha256'],eligibility['resource_contract_sha256']); self.assertEqual(capacity['summary'][0]['peak_units'],2)
        runs=[dict(id='run-'+str(i),start=task['start'],end=task['end']) for i,task in enumerate(selected['tasks'],1)]
        events=[]
        for run in runs:
            events.extend([dict(id='start-'+run['id'],run_id=run['id'],at=run['start'],kind='start'),dict(id='finish-'+run['id'],run_id=run['id'],at=run['end'],kind='finish')])
        events.extend([dict(id='hold-a',run_id='run-1',at=2,kind='hold'),dict(id='resume-a',run_id='run-1',at=4,kind='resume')])
        durations=self.run_value('process-event-duration-analyzer',dict(format='outlands-process-event-durations-v1',runs=runs,events=events))
        self.assertEqual(durations['totals'],dict(elapsed_ticks=12,active_ticks=10,hold_ticks=2,hold_count=1))
        # Fictional exercise explicitly declares one whole unit per completed run.
        completed=len(durations['durations']); self.assertEqual(completed,2)
        flow=self.run_value('flow-balance-reconciler',dict(format='outlands-flow-balance-v1',unit='pieces',
            balances=[dict(id='bucket-a',opening=10,closing=10-completed),dict(id='bucket-b',opening=0,closing=completed)],
            movements=[dict(id='transfer-completed',from_bucket='bucket-a',to_bucket='bucket-b',quantity=completed)],adjustments=[]))
        self.assertEqual([row['computed_closing'] for row in flow['balances']],[8,2]); self.assertEqual(flow['totals']['computed_closing'],10)
        self.assertFalse(flow['actual_quantities_verified'])

    def test_individually_eligible_proposals_can_still_conflict(self):
        value=json.loads((ROOT/'tools/assignment-eligibility-checker/examples/input.json').read_text(encoding='utf-8'))
        for row in value['tasks']: row.update(start=0,end=6,units=2)
        eligibility=self.run_value('assignment-eligibility-checker',value); self.assertEqual(eligibility['status'],'PASS')
        reservations=[dict(id=row['id'],resource_id=row['resource_id'],start=0,end=6,units=2) for row in value['assignments']]
        conflict=self.run_value('resource-reservation-checker',dict(format='outlands-resource-reservations-v1',resources=value['resources'],reservations=reservations),1)
        self.assertEqual(conflict['summary'][0]['over_capacity_spans'],[dict(start=0,end=6,units=4)])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])
