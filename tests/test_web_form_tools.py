"""Actual independent CLI and connected fictional HVAC web form acceptance."""
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
TOOLS={'form-definition-contract-checker':'forms.py','form-submission-contract-checker':'submissions.py',
       'ui-transition-history-checker':'histories.py','ui-interaction-scenario-comparator':'scenarios.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-web-form-'); self.addCleanup(self.temp.cleanup)
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
            code,out=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json');self.assertEqual(code,1);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256'])
            if name=='form-definition-contract-checker':self.assertIsNone(out['assessment']);self.assertIsNone(out['forms_sha256'])
            else:self.assertIsNotNone(out['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_service_request_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        forms=self.run_value('form-definition-contract-checker',example('form-definition-contract-checker'));submissions=self.run_value('form-submission-contract-checker',example('form-submission-contract-checker'));histories=self.run_value('ui-transition-history-checker',example('ui-transition-history-checker'));scenarios=self.run_value('ui-interaction-scenario-comparator',example('ui-interaction-scenario-comparator'))
        self.assertEqual({v['forms_sha256'] for v in (forms,submissions,histories)},{forms['forms_sha256']});self.assertEqual(submissions['submissions_sha256'],histories['submissions_sha256']);self.assertEqual(scenarios['baseline_forms_sha256'],forms['forms_sha256']);self.assertEqual(scenarios['baseline_histories_sha256'],histories['histories_sha256']);self.assertTrue(scenarios['assessment']['all_declared_outcomes_equal'])
        for report in (forms,submissions,histories,scenarios):
            for key in ('browser_started','dom_inspected','scripts_executed','network_requests_performed','authentication_performed','records_changed','raw_values_emitted','accessibility_verified','whole_ui_compatibility_verified','target_changes_performed'):self.assertFalse(report[key])

    def test_missing_or_changed_scenarios_never_become_a_clean_comparison(self):
        name='ui-interaction-scenario-comparator';value=json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'));value['candidate_histories']=[];out=self.run_value(name,value,1);self.assertEqual(out['assessment']['histories'][0]['state'],'candidate_missing');self.assertIsNone(out['qualified_scope_sha256'])
        value=json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'));value['candidate_histories'][0]['events'][1]['action']='revise';out=self.run_value(name,value,1);self.assertEqual(out['assessment']['histories'][0]['state'],'interaction_scope_changed');self.assertIsNone(out['assessment']['histories'][0]['candidate'])
        value['status']='PASS';self.assertEqual(self.run_value(name,value,2)['status'],'ERROR')

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_and_ai_software_cli_examples(self):
        for name,file in [('form-definition-contract-checker','game-form.json'),('form-submission-contract-checker','ai-software-submission.json')]:
            code,out=self.cli(name,file=ROOT/'tools'/name/'examples'/file);self.assertEqual(code,0);self.assertEqual(out['status'],'PASS');self.assertFalse(out['browser_started']);self.assertFalse(out['scripts_executed'])




    def test_existing_configuration_checker_reviews_explicit_scalar_projection(self):
        name='form-submission-contract-checker';value=json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'));settings={key:value['submissions'][0]['values'][key] for key in ('equipment','priority','urgent')};contract=dict(schema_version=1,fields=[dict(id='equipment',key='equipment',type='string',required=True,min_length=1,max_length=32,choices=['air-handler','heat-pump']),dict(id='priority',key='priority',type='integer',required=True,minimum=1,maximum=5),dict(id='urgent',key='urgent',type='boolean',required=False)],rules=[])
        contract_file=self.root/'fictional-form-projection-contract.json';contract_file.write_bytes(encode(contract));settings_file=self.root/'fictional-form-projection-values.json';settings_file.write_bytes(encode(settings));script=ROOT/'tools/configuration-contract-checker/config_check.py'
        code,out=self.invoke(script,['--contract',contract_file,'--settings',settings_file]);self.assertEqual(code,0);self.assertEqual(out['status'],'NO_DECLARED_VIOLATIONS');self.assertTrue(self.run_value(name,value)['assessment']['submissions'][0]['valid'])
        settings['priority']=6;value['submissions'][0]['values']['priority']=6;settings_file.write_bytes(encode(settings));code,out=self.invoke(script,['--contract',contract_file,'--settings',settings_file]);self.assertEqual(code,1);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertFalse(self.run_value(name,value,1)['assessment']['submissions'][0]['valid'])

    def test_declared_validation_error_branch_is_distinct_from_valid_submission(self):
        value=json.loads((ROOT/'tools/ui-transition-history-checker/examples/input.json').read_text(encoding='utf-8'));submission=value['submissions'][0];submission['values']['priority']=6;submission['expected_valid']=False;value['flows'][0]['transitions'][0]['submission_requirement']='invalid';value['histories'][0]['flow_sha256']=sha(encode(value['flows'][0]));value['histories'][0]['events'][0]['submission_sha256']=sha(encode(submission))
        submission_out=self.run_value('form-submission-contract-checker',dict(format='outlands-form-submissions-v1',forms=value['forms'],submissions=value['submissions']),1);self.assertFalse(submission_out['assessment']['submissions'][0]['valid']);self.assertTrue(submission_out['assessment']['submissions'][0]['expectation_met'])
        history_out=self.run_value('ui-transition-history-checker',value);self.assertFalse(history_out['assessment']['submissions'][0]['valid']);self.assertTrue(history_out['assessment']['histories'][0]['valid']);self.assertFalse(history_out['browser_started'])
