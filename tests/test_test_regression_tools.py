"""Actual independent CLI and connected fictional HVAC test/regression acceptance."""
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
TOOLS={'test-case-manifest-checker':'cases.py','test-run-coverage-checker':'runs.py',
       'regression-comparison-reporter':'regressions.py','evidence-completeness-checker':'evidence.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-test-regression-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_retain_findings_without_qualified_scope(self):
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json');self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNone(result['qualified_scope_sha256']);self.assertIsNotNone(result['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_result_and_failure_evidence_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        manifest_input=example('test-case-manifest-checker');manifest=self.run_value('test-case-manifest-checker',manifest_input)
        self.assertTrue(manifest['assessment']['all_expectation_contracts_present'])
        run_input=example('test-run-coverage-checker');self.assertEqual(run_input['cases'],manifest_input['cases']);self.assertEqual(run_input['expectations'],manifest_input['expectations'])
        baseline=self.run_value('test-run-coverage-checker',run_input);self.assertEqual(baseline['cases_sha256'],manifest['cases_sha256']);self.assertEqual(baseline['assessment']['matched_cases'],1)
        comparison_input=example('regression-comparison-reporter');comparison_input['candidate']['results'][0]['observed_exit']=1
        comparison=self.run_value('regression-comparison-reporter',comparison_input,1);self.assertEqual(comparison['assessment']['cases'][0]['state'],'regression')
        candidate=comparison_input['candidate'];candidate_coverage=self.run_value('test-run-coverage-checker',dict(format='outlands-test-run-coverage-v1',**candidate),1);self.assertFalse(candidate_coverage['assessment']['cases'][0]['matched'])
        # Explicit fictional operator adapter: evidence describes the candidate's failure.
        evidence_input=example('evidence-completeness-checker');evidence_input.update(candidate)
        for artifact in evidence_input['artifacts']:artifact.update(run=candidate['run']['id'],run_revision=candidate['run']['revision'],run_sha256=sha(encode(candidate['run'])),result=candidate['results'][0]['id'],result_sha256=sha(encode(candidate['results'][0])))
        evidence=self.run_value('evidence-completeness-checker',evidence_input);self.assertTrue(evidence['assessment']['all_evidence_contracts_complete']);self.assertFalse(evidence['assessment']['cases'][0]['observation']['matched']);self.assertFalse(evidence['assessment']['test_outcomes_upgraded'])
        self.assertEqual(evidence['results_sha256'],candidate_coverage['results_sha256'])
        for result in (manifest,baseline,comparison,candidate_coverage,evidence):
            for key in ('tests_executed','test_execution_verified','artifact_bytes_verified','evidence_authenticity_verified','approval_authority_verified','target_changes_performed'):self.assertFalse(result[key])

    def test_cancelled_observation_is_incomplete_across_run_comparison_and_evidence(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        run_input=example('test-run-coverage-checker');run_input['results'][0].update(state='cancelled',observed_exit=None,stdout_sha256=None,stderr_sha256=None,output_complete=False)
        run=self.run_value('test-run-coverage-checker',run_input,1);self.assertIsNone(run['assessment']['cases'][0]['matched'])
        comparison_input=example('regression-comparison-reporter');row=comparison_input['candidate']['results'][0];row.update(state='cancelled',observed_exit=None,stdout_sha256=None,stderr_sha256=None,output_complete=False)
        comparison=self.run_value('regression-comparison-reporter',comparison_input,1);self.assertEqual(comparison['assessment']['cases'][0]['state'],'incomplete_comparison')
        evidence_input=example('evidence-completeness-checker');evidence_input['results']=run_input['results']
        for artifact in evidence_input['artifacts']:artifact['result_sha256']=sha(encode(run_input['results'][0]))
        evidence=self.run_value('evidence-completeness-checker',evidence_input,1);self.assertFalse(evidence['assessment']['cases'][0]['ready_for_manual_evidence_review']);self.assertIsNone(evidence['qualified_scope_sha256'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_case_cli(self):
        name='test-case-manifest-checker';code,out=self.cli(name,file=ROOT/'tools'/name/'examples/game-cases.json');self.assertEqual(code,0);self.assertTrue(out['assessment']['all_expectation_contracts_present']);self.assertFalse(out['tests_executed'])
