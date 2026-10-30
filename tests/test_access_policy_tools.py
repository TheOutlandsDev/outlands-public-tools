"""Actual independent CLI and connected fictional HVAC access policy acceptance."""
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
TOOLS={'role-permission-contract-checker':'roles.py','access-decision-evaluator':'decisions.py',
       'separation-of-duties-checker':'duties.py','access-policy-scenario-comparator':'scenarios.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-access-policy-'); self.addCleanup(self.temp.cleanup)
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
            if name=='role-permission-contract-checker':self.assertIsNone(out['assessment']);self.assertIsNone(out['policy_sha256'])
            else:self.assertIsNotNone(out['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_service_policy_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        roles=self.run_value('role-permission-contract-checker',example('role-permission-contract-checker'));decisions=self.run_value('access-decision-evaluator',example('access-decision-evaluator'));duties=self.run_value('separation-of-duties-checker',example('separation-of-duties-checker'));comparison=self.run_value('access-policy-scenario-comparator',example('access-policy-scenario-comparator'))
        self.assertEqual({r['policy_sha256'] for r in (roles,decisions,duties)},{roles['policy_sha256']});self.assertEqual(comparison['baseline_sha256'],roles['policy_sha256']);self.assertEqual(comparison['baseline_requests_sha256'],decisions['requests_sha256']);self.assertEqual(comparison['candidate_requests_sha256'],decisions['requests_sha256'])
        actual={row['id']:row['decision'] for row in decisions['assessment']['requests']};self.assertEqual(actual,{'request-approve':'allow','request-submit':'allow','request-unassigned':'deny'});self.assertEqual(duties['assessment']['workflow_conflicts'],[]);self.assertTrue(comparison['assessment']['all_declared_scenarios_equal'])
        for report in (roles,decisions,duties,comparison):
            for key in ('identity_authenticated','authorization_verified','access_enforced','permissions_changed','accounts_changed','network_accessed','actions_executed','records_changed','target_changes_performed'):self.assertFalse(report[key])

    def test_missing_candidate_scenarios_never_become_a_clean_comparison(self):
        name='access-policy-scenario-comparator';value=json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'));value['candidate_requests']=[];out=self.run_value(name,value,1);self.assertEqual(len(out['assessment']['requests']),3);self.assertTrue(all(row['state']=='candidate_missing' and row['candidate'] is None for row in out['assessment']['requests']));self.assertIsNone(out['qualified_scope_sha256']);self.assertFalse(out['assessment']['security_improvement_inferred'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_and_ai_software_cli_examples(self):
        for name,file in [('role-permission-contract-checker','game-policy.json'),('access-decision-evaluator','ai-software-policy.json')]:
            code,out=self.cli(name,file=ROOT/'tools'/name/'examples'/file);self.assertEqual(code,0);self.assertEqual(out['status'],'PASS');self.assertFalse(out['identity_authenticated']);self.assertFalse(out['network_accessed'])




    def test_existing_approval_coverage_does_not_establish_separation_of_duties(self):
        # Explicit fictional adapter: review grants are declarations independent of access rules.
        item=dict(id='hvac-service-proposal',revision=1,artifact_sha256=sha(encode({'fictional':'proposal-content'})));policy=dict(id='fictional-review-coverage',revision=1,required_roles=['reviewer','technician']);events=[]
        for role in policy['required_roles']:events.append(dict(id='grant-'+role,item=item['id'],item_revision=1,item_sha256=sha(encode(item)),policy_sha256=sha(encode(policy)),reviewer='actor-alpha',role=role,at=10,action='approve',grant=None))
        value=dict(format='outlands-approval-scope-v1',policy=policy,items=[item],events=events,as_of=20);file=self.root/'fictional-approval-coverage.json';file.write_bytes(encode(value));code,out=self.invoke(ROOT/'tools/approval-scope-checker/approvals.py',['--input',file]);self.assertEqual(code,0);self.assertIsNotNone(out['review_scope_sha256']);self.assertFalse(out['execution_authorized'])
        duties=json.loads((ROOT/'tools/separation-of-duties-checker/examples/input.json').read_text(encoding='utf-8'));duties['policy']['assignments'][0]['roles']=['reviewer','technician'];role_report=self.run_value('role-permission-contract-checker',dict(format='outlands-role-permission-contract-v1',policy=duties['policy']))
        for row in duties['events']:row.update(actor='actor-alpha',policy_sha256=role_report['policy_sha256'])
        result=self.run_value('separation-of-duties-checker',duties,1);self.assertTrue(result['assessment']['role_conflicts']);self.assertTrue(result['assessment']['workflow_conflicts']);self.assertIsNone(result['qualified_scope_sha256'])

    def test_deny_precedence_is_explicit_even_when_allow_also_matches(self):
        name='access-decision-evaluator';value=json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'));value['policy']['rules'].append(dict(id='deny-inherited',role='observer',action='approve',resource='hvac-service-proposal',effect='deny'));out=self.run_value(name,value,1);row=out['assessment']['requests'][0];self.assertEqual(row['decision'],'deny');self.assertEqual(row['matching_allow_rule_ids'],['allow-approve']);self.assertEqual(row['matching_deny_rule_ids'],['deny-inherited']);self.assertIsNone(out['qualified_scope_sha256'])
