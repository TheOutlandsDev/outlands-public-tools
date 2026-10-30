"""Actual independent CLI and connected fictional AI contract acceptance."""
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
TOOLS={'prompt-contract-diff':'prompts.py','label-mapping-contract-checker':'labels.py',
       'score-abstention-policy-checker':'scores.py','candidate-evaluation-gate-planner':'gates.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-ai-contracts-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_retain_qualified_change_and_policy_diagnostics(self):
        for name,key in zip(TOOLS,['changes','assessment','decisions','assessment']):
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNotNone(result[key])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_classifier_review(self):
        def example(name,file='input.json'):return json.loads((ROOT/'tools'/name/'examples'/file).read_text(encoding='utf-8'))
        changed=example('prompt-contract-diff','needs-review.json');prompt=self.run_value('prompt-contract-diff',changed,1)
        mapping_input=example('label-mapping-contract-checker');mapping_input['before']=changed['before']['output_contract']['taxonomy'];mapping_input['after']=changed['after']['output_contract']['taxonomy']
        mapping=self.run_value('label-mapping-contract-checker',mapping_input)
        self.assertEqual(mapping['before_sha256'],prompt['before_taxonomy_sha256']);self.assertEqual(mapping['after_sha256'],prompt['after_taxonomy_sha256'])
        self.assertFalse(mapping['assessment']['record_level_rule_required']);self.assertFalse(mapping['records_relabelled'])
        scored_input=example('score-abstention-policy-checker');scored_input['policy']['labels']=mapping_input['after']['labels']
        scored=self.run_value('score-abstention-policy-checker',scored_input);self.assertEqual(scored['summary']['abstentions'],1)
        gate_input=example('candidate-evaluation-gate-planner');gate_input['labels']=mapping_input['after']
        # The exercise explicitly translates fictional baseline records through reviewed one-to-one mappings.
        destinations={row['source']:row['targets'][0] for row in mapping['assessment']['mappings']}
        old_baseline=[dict(id='case-filter',label='filter-service'),dict(id='case-noise',label='needs-review'),dict(id='case-uncertain',label=None)]
        gate_input['baseline']['predictions']=[dict(id=r['id'],label=destinations[r['label']] if r['label'] is not None else None) for r in old_baseline]
        gate_input['candidate']['predictions']=[dict(id=r['id'],label=r['computed_label']) for r in scored['decisions']]
        for side in ('baseline','candidate'):gate_input[side]['taxonomy_sha256']=mapping['after_sha256']
        gate_input['baseline']['prompt_sha256']=prompt['before_sha256']
        gate_input['candidate']['prompt_sha256']=prompt['after_sha256'];gate_input['candidate']['decision_policy_sha256']=scored['policy_sha256']
        gate_input['policy'].update(required_prompt_sha256=prompt['after_sha256'],required_decision_policy_sha256=scored['policy_sha256'])
        gate=self.run_value('candidate-evaluation-gate-planner',gate_input)
        self.assertTrue(gate['assessment']['eligible_for_manual_review']);self.assertEqual(gate['metrics']['candidate']['accuracy']['exact_fraction'],'2/3')
        self.assertEqual(gate['assessment']['accuracy_delta']['exact_fraction'],'1/3');self.assertEqual(gate['assessment']['abstention_delta']['exact_fraction'],'0/1')
        for key in ('deploy_authorized','release_performed','training_performed','holdout_independence_verified','artifact_bytes_verified'):self.assertFalse(gate[key])

    def test_policy_consistency_does_not_satisfy_a_stricter_evaluation_gate(self):
        code,scores=self.cli('score-abstention-policy-checker');self.assertEqual(code,0);self.assertEqual(scores['summary']['declaration_mismatches'],0)
        value=json.loads((ROOT/'tools/candidate-evaluation-gate-planner/examples/input.json').read_text(encoding='utf-8'));value['policy']['minimum_accuracy']='0.9'
        gate=self.run_value('candidate-evaluation-gate-planner',value,1)
        self.assertFalse(gate['assessment']['eligible_for_manual_review']);self.assertIn('MINIMUM_ACCURACY_NOT_MET',gate['assessment']['failed_criteria']);self.assertFalse(gate['deploy_authorized'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_event_cli(self):
        name='score-abstention-policy-checker';code,result=self.cli(name,file=ROOT/'tools'/name/'examples/game-events.json')
        self.assertEqual(code,0);self.assertEqual([r['computed_label'] for r in result['decisions']],['quest',None]);self.assertFalse(result['inference_performed'])
