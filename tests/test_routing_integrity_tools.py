"""Actual independent CLI and connected fictional HVAC routing acceptance."""
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
TOOLS={'model-capability-checker':'models.py','request-routing-checker':'routes.py',
       'fallback-chain-checker':'fallbacks.py','inference-receipt-reconciler':'receipts.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-routing-contracts-'); self.addCleanup(self.temp.cleanup)
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
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNotNone(result['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_route_fallback_and_receipts(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        capabilities_input=example('model-capability-checker');capabilities=self.run_value('model-capability-checker',capabilities_input)
        models={r['id']:r for r in capabilities['assessment']['models']}
        route_input=example('request-routing-checker');route_input['models']=capabilities_input['models']
        for p in route_input['proposals']:p['model_sha256']=models[p['model']]['model_sha256']
        route=self.run_value('request-routing-checker',route_input);self.assertTrue(route['assessment']['eligible_for_manual_routing_review'])
        self.assertEqual(route['models_sha256'],capabilities['models_sha256'])
        fallback_input=example('fallback-chain-checker');fallback_input.update(models=capabilities_input['models'],request=route_input['requests'][0],policy=route_input['policy'])
        fallback_input['chain'].update(request_sha256=sha(encode(fallback_input['request'])),policy_sha256=route['policy_sha256'])
        for s in fallback_input['chain']['steps']:s['model_sha256']=models[s['model']]['model_sha256']
        fallback=self.run_value('fallback-chain-checker',fallback_input)
        self.assertEqual([s['model'] for s in fallback['assessment']['ordered_steps']],['hvac-primary','hvac-reserve']);self.assertIsNotNone(fallback['plan_sha256'])
        receipts_input=example('inference-receipt-reconciler')
        for key in ('models','request','policy','chain'):receipts_input[key]=fallback_input[key]
        # These invented receipts are supplied declarations, not results of invoking models.
        for a in receipts_input['attempts']:a.update(model_sha256=models[a['model']]['model_sha256'],request_sha256=fallback['request_sha256'],plan_sha256=fallback['plan_sha256'])
        receipts=self.run_value('inference-receipt-reconciler',receipts_input)
        self.assertEqual(receipts['plan_sha256'],fallback['plan_sha256']);self.assertEqual(receipts['assessment']['observed_terminal_status'],'succeeded')
        self.assertEqual(receipts['assessment']['ordered_attempt_ids'],['attempt-one','attempt-two']);self.assertEqual(receipts['assessment']['attempts'],2)
        for result in (capabilities,route,fallback,receipts):
            self.assertEqual(result['models_sha256'],capabilities['models_sha256'])
            for key in ('provider_contacted','inference_performed','inference_occurrence_verified','artifact_bytes_verified','dispatch_authorized','output_content_verified','target_changes_performed'):self.assertFalse(result[key])

    def test_consistent_capabilities_do_not_make_an_oversized_request_eligible(self):
        capabilities=self.cli('model-capability-checker')[1];self.assertEqual(capabilities['assessment']['consistent_models'],2)
        value=json.loads((ROOT/'tools/request-routing-checker/examples/needs-review.json').read_text(encoding='utf-8'))
        route=self.run_value('request-routing-checker',value,1);self.assertFalse(route['assessment']['eligible_for_manual_routing_review']);self.assertIsNone(route['route_plan_sha256'])
        self.assertIn('MODEL_INPUT_BUDGET_EXCEEDED',route['assessment']['proposals'][0]['failed_criteria'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_routing_cli(self):
        name='request-routing-checker';code,r=self.cli(name,file=ROOT/'tools'/name/'examples/game-routing.json')
        self.assertEqual(code,0);self.assertEqual(r['assessment']['proposals'][0]['model'],'game-dialogue');self.assertFalse(r['provider_contacted'])
