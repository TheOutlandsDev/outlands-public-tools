"""Actual independent CLI and connected fictional HVAC cache/retry acceptance."""
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
TOOLS={'cache-key-contract-checker':'keys.py','cache-freshness-planner':'freshness.py',
       'retry-budget-checker':'retries.py','idempotency-ledger-reconciler':'ledger.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-cache-retry-'); self.addCleanup(self.temp.cleanup)
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

    def test_connected_four_tool_hvac_cache_refresh_review(self):
        def example(name,file='input.json'):return json.loads((ROOT/'tools'/name/'examples'/file).read_text(encoding='utf-8'))
        key_input=example('cache-key-contract-checker');keys=self.run_value('cache-key-contract-checker',key_input);source=key_input['entries'][0]
        self.assertEqual(keys['assessment']['entries'][0]['expected_key_sha256'],source['key_sha256']);self.assertTrue(keys['assessment']['all_bindings_valid'])
        fresh_input=example('cache-freshness-planner');entry=fresh_input['entries'][0]
        for field in ('key_sha256','content_sha256','inputs'):entry[field]=source[field]
        fresh_input['as_of']=40;freshness=self.run_value('cache-freshness-planner',fresh_input,1)
        self.assertEqual(freshness['assessment']['entries'][0]['state'],'invalidated');self.assertTrue(freshness['assessment']['entries'][0]['expired'])
        retry_input=example('retry-budget-checker');operation=retry_input['operations'][0]
        # Explicit fictional operator adapter: the operation key has its own declared namespace.
        operation['key_sha256']=sha(encode(dict(namespace='fictional-hvac-refresh',cache_key_sha256=source['key_sha256'])))
        operation['payload_sha256']=source['content_sha256']
        for attempt in retry_input['attempts']:attempt['operation_sha256']=sha(encode(operation))
        retry_input['as_of']=fresh_input['as_of'];retry=self.run_value('retry-budget-checker',retry_input)
        self.assertEqual(retry['assessment']['operations'][0]['state'],'ready_for_manual_review');self.assertEqual(retry['assessment']['operations'][0]['earliest_next_at'],15)
        ledger_input=example('idempotency-ledger-reconciler');ledger_input['operations']=retry_input['operations'];claim=ledger_input['records'][0]
        claim.update(operation_sha256=sha(encode(operation)),key_sha256=operation['key_sha256'],payload_sha256=operation['payload_sha256'],state=retry_input['attempts'][0]['status'],result_sha256=retry_input['attempts'][0]['result_sha256'])
        ledger=self.run_value('idempotency-ledger-reconciler',ledger_input);self.assertEqual(ledger['operations_sha256'],retry['operations_sha256'])
        self.assertEqual(ledger['assessment']['key_groups'][0]['declared_state'],'failed');self.assertTrue(ledger['assessment']['all_terminal_claims_unambiguous'])
        for result in (keys,freshness,retry,ledger):
            for key in ('cache_mutated','execution_performed','exactly_once_verified','retry_authorized','provider_contacted','artifact_bytes_verified','record_authenticity_verified','target_changes_performed'):self.assertFalse(result[key])

    def test_unknown_outcomes_do_not_make_a_retry_ready_or_a_ledger_resolved(self):
        retry_input=json.loads((ROOT/'tools/retry-budget-checker/examples/needs-review.json').read_text(encoding='utf-8'))
        retry=self.run_value('retry-budget-checker',retry_input,1);self.assertEqual(retry['assessment']['operations'][0]['state'],'unknown');self.assertFalse(retry['assessment']['operations'][0]['eligible_for_manual_attempt_review']);self.assertIsNone(retry['budget_review_sha256'])
        ledger_input=json.loads((ROOT/'tools/idempotency-ledger-reconciler/examples/needs-review.json').read_text(encoding='utf-8'))
        ledger=self.run_value('idempotency-ledger-reconciler',ledger_input,1);self.assertEqual(ledger['assessment']['key_groups'][0]['declared_state'],'unresolved');self.assertIsNone(ledger['ledger_reconciliation_sha256']);self.assertFalse(ledger['exactly_once_verified'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_cache_key_cli(self):
        name='cache-key-contract-checker';code,r=self.cli(name,file=ROOT/'tools'/name/'examples/game-cache.json')
        self.assertEqual(code,0);self.assertTrue(r['assessment']['all_bindings_valid']);self.assertFalse(r['actual_cache_state_verified'])
