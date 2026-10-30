"""Actual independent CLI and connected fictional HVAC dataset acceptance."""
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
TOOLS={'dataset-partition-checker':'partitions.py','annotation-agreement-reporter':'agreement.py',
       'training-selection-checker':'selection.py','evaluation-slice-checker':'slices.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-hvac-datasets-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_retain_complete_qualified_findings(self):
        for name,key in zip(TOOLS,['assessment','assessment','assessment','coverage']):
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNotNone(result[key])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_dataset_review_and_existing_gate(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        partition_input=example('dataset-partition-checker');partition=self.run_value('dataset-partition-checker',partition_input)
        agreement_input=example('annotation-agreement-reporter');agreement=self.run_value('annotation-agreement-reporter',agreement_input)
        self.assertEqual(agreement['assessment']['complete_items'],4);self.assertEqual(agreement['assessment']['disagreement_items'],0)
        self.assertEqual(partition['taxonomy_sha256'],agreement['taxonomy_sha256'])
        # This fictional operator adapter creates declarations; the tools never grant approvals.
        selection_input=example('training-selection-checker');selection_input['records']=partition_input['records']
        selection=self.run_value('training-selection-checker',selection_input)
        self.assertEqual(selection['records_sha256'],partition['records_sha256']);self.assertEqual(selection['assessment']['eligible_records'],2)
        self.assertEqual(selection['selected_records_sha256'],sha(encode(sorted([r for r in partition_input['records'] if r['partition']=='train'],key=lambda r:r['id']))))
        slice_input=example('evaluation-slice-checker')
        slice_input['cohort']=[dict(id=r['id'],expected_label=r['label']) for r in partition_input['records'] if r['partition']=='test']
        coverage=self.run_value('evaluation-slice-checker',slice_input);self.assertEqual(coverage['coverage']['covered_cases'],2)
        self.assertEqual(coverage['taxonomy_sha256'],partition['taxonomy_sha256'])
        # Explicitly adapt the declared held-out cohort to the already public candidate gate.
        scope=dict(id='hvac-demo',revision=1,prompt_sha256=sha(encode({'fictional_hvac':'prompt'})),decision_policy_sha256=sha(encode({'fictional_hvac':'rule'})),
                   cohort_sha256=coverage['cohort_sha256'],taxonomy_sha256=coverage['taxonomy_sha256'],
                   predictions=[dict(id=r['id'],label='filter') for r in slice_input['cohort']])
        candidate=dict(scope,revision=2,predictions=[dict(id=r['id'],label=r['expected_label']) for r in slice_input['cohort']])
        gate_input=dict(format='outlands-candidate-evaluation-gate-v1',labels=slice_input['taxonomy'],cohort=slice_input['cohort'],baseline=scope,candidate=candidate,
            policy=dict(minimum_accuracy='0.5',maximum_regression='0',maximum_abstention_increase='0',required_prompt_sha256=candidate['prompt_sha256'],required_decision_policy_sha256=candidate['decision_policy_sha256']))
        file=self.root/'fictional-gate.json';file.write_bytes(encode(gate_input))
        code,gate=self.invoke(ROOT/'tools/candidate-evaluation-gate-planner/gates.py',['--input',file])
        self.assertEqual(code,0);self.assertEqual(gate['metrics']['baseline']['accuracy']['exact_fraction'],'1/2');self.assertEqual(gate['metrics']['candidate']['accuracy']['exact_fraction'],'1/1')
        self.assertTrue(gate['assessment']['eligible_for_manual_review']);self.assertFalse(gate['holdout_independence_verified']);self.assertFalse(gate['deploy_authorized'])
        for result in (partition,agreement,selection,coverage):
            for key in ('artifact_bytes_verified','label_truth_verified','training_performed','dataset_export_performed','target_changes_performed'):self.assertFalse(result[key])

    def test_training_approval_does_not_establish_partition_independence(self):
        selection=json.loads((ROOT/'tools/training-selection-checker/examples/input.json').read_text(encoding='utf-8'))
        selection['records'][2]['group']=selection['records'][0]['group']
        approved=self.run_value('training-selection-checker',selection);self.assertTrue(approved['assessment']['eligible_for_manual_export_review'])
        partition=self.run_value('dataset-partition-checker',dict(format='outlands-dataset-partition-v1',taxonomy=selection['taxonomy'],records=selection['records']),1)
        self.assertTrue(partition['assessment']['group_overlaps']);self.assertFalse(approved['holdout_independence_verified'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])
