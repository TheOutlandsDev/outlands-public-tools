"""Actual independent CLI and connected fictional HVAC worker/queue acceptance."""
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
TOOLS={'work-item-contract-checker':'items.py','worker-lease-history-checker':'leases.py',
       'queue-acknowledgement-reconciler':'acks.py','worker-result-commit-checker':'commits.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-worker-queue-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_retain_diagnostics_without_qualified_scope(self):
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json');self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNone(result['qualified_scope_sha256']);self.assertIsNotNone(result['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_worker_takeover_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        item=self.run_value('work-item-contract-checker',example('work-item-contract-checker'));lease=self.run_value('worker-lease-history-checker',example('worker-lease-history-checker'));ack=self.run_value('queue-acknowledgement-reconciler',example('queue-acknowledgement-reconciler'));commit=self.run_value('worker-result-commit-checker',example('worker-result-commit-checker'))
        self.assertEqual({r['items_sha256'] for r in (item,lease,ack,commit)},{item['items_sha256']});self.assertEqual({r['lease_events_sha256'] for r in (lease,ack,commit)},{lease['lease_events_sha256']});self.assertEqual(ack['deliveries_sha256'],commit['deliveries_sha256'])
        self.assertEqual(lease['assessment']['items'][0]['current_owner']['worker'],'worker-beta');self.assertEqual(ack['assessment']['items'][0]['single_consistent_acknowledged_delivery'],'delivery-current');self.assertEqual(commit['assessment']['items'][0]['consistent_commit_id'],'commit-current')
        for report in (item,lease,ack,commit):
            for key in ('payloads_opened','handler_executed','artifact_bytes_verified','worker_contacted','ownership_enforced','jobs_executed','queue_changed','records_changed','results_committed','target_changes_performed'):self.assertFalse(report[key])

    def test_late_old_owner_records_remain_visible_without_erasing_current_claims(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        ack_input=example('queue-acknowledgement-reconciler');current=ack_input['deliveries'][0];current['ordinal']=2;ack_input['acknowledgements'][0]['delivery_sha256']=sha(encode(current));old=dict(current,id='delivery-old',ordinal=1,at=12,worker='worker-alpha',token=1);ack_input['deliveries'].append(old);ack_input['acknowledgements'].append(dict(id='ack-old',delivery=old['id'],delivery_sha256=sha(encode(old)),at=25,worker='worker-alpha',token=1,state='acknowledged'))
        ack=self.run_value('queue-acknowledgement-reconciler',ack_input,1);self.assertEqual(ack['assessment']['items'][0]['single_consistent_acknowledged_delivery'],'delivery-current');self.assertFalse(ack['assessment']['items'][0]['all_deliveries_accounted']);self.assertIn('ACK_OWNER_NOT_ACTIVE',ack['assessment']['deliveries'][0]['failed_criteria'])
        commit_input=example('worker-result-commit-checker');commit_input['deliveries']=ack_input['deliveries'];result=commit_input['results'][0];result['delivery_sha256']=sha(encode(current));commit_input['commits'][0]['result_sha256']=sha(encode(result));commit_input['results'].append(dict(result,id='result-old',delivery=old['id'],delivery_sha256=sha(encode(old)),at=25,worker='worker-alpha',token=1))
        commit=self.run_value('worker-result-commit-checker',commit_input,1);self.assertEqual(commit['assessment']['items'][0]['consistent_commit_id'],'commit-current');self.assertIn('RESULT_OWNER_NOT_ACTIVE',commit['assessment']['results'][1]['failed_criteria'])
        for report in (ack,commit):self.assertIsNone(report['qualified_scope_sha256']);self.assertFalse(report['target_changes_performed'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_job_cli(self):
        name='work-item-contract-checker';code,out=self.cli(name,file=ROOT/'tools'/name/'examples/game-job.json');self.assertEqual(code,0);self.assertTrue(out['assessment']['items'][0]['declared_metadata_complete']);self.assertFalse(out['handler_executed'])


    def operation_adapter(self):
        # This is a new explicit fictional operation, not an inference that a worker ran.
        item=json.loads((ROOT/'tools/work-item-contract-checker/examples/input.json').read_text(encoding='utf-8'))['items'][0]
        return dict(id=item['id'],revision=item['revision'],key_sha256=sha(encode(dict(item=item['id'],revision=item['revision']))),payload_sha256=item['input_sha256'])

    def test_existing_retry_budget_checks_explicit_fictional_attempts_separately(self):
        operation=self.operation_adapter();policy=dict(id='fictional-retry-policy',revision=1,maximum_attempts=3,base_delay=5,maximum_delay=20,retryable_failures=['timeout']);first=dict(id='attempt-one',operation=operation['id'],operation_revision=1,operation_sha256=sha(encode(operation)),policy_sha256=sha(encode(policy)),ordinal=1,at=22,status='failed',failure_class='timeout',result_sha256=sha(encode({'fictional':'timeout-claim'})))
        value=dict(format='outlands-retry-budget-v1',policy=policy,operations=[operation],attempts=[first],as_of=30);file=self.root/'fictional-retry.json';file.write_bytes(encode(value));script=ROOT/'tools/retry-budget-checker/retries.py'
        code,out=self.invoke(script,['--input',file]);self.assertEqual(code,0);self.assertEqual(out['assessment']['operations'][0]['earliest_next_at'],27);self.assertTrue(out['assessment']['operations'][0]['eligible_for_manual_attempt_review'])
        value['attempts'].append(dict(first,id='attempt-too-early',ordinal=2,at=24));file.write_bytes(encode(value));code,out=self.invoke(script,['--input',file]);self.assertEqual(code,1);self.assertIn('RETRY_BEFORE_REQUIRED_DELAY',out['assessment']['operations'][0]['failed_criteria']);self.assertFalse(out['execution_performed'])

    def test_existing_idempotency_checker_reconciles_explicit_commit_claims_separately(self):
        operation=self.operation_adapter();selected=json.loads((ROOT/'tools/worker-result-commit-checker/examples/input.json').read_text(encoding='utf-8'))['results'][0]
        claim=dict(id='fictional-terminal-claim',operation=operation['id'],operation_revision=1,operation_sha256=sha(encode(operation)),key_sha256=operation['key_sha256'],payload_sha256=operation['payload_sha256'],state='succeeded',result_sha256=selected['artifact_sha256']);value=dict(format='outlands-idempotency-ledger-v1',operations=[operation],records=[claim]);file=self.root/'fictional-ledger.json';file.write_bytes(encode(value));script=ROOT/'tools/idempotency-ledger-reconciler/ledger.py'
        code,out=self.invoke(script,['--input',file]);self.assertEqual(code,0);self.assertTrue(out['assessment']['all_terminal_claims_unambiguous'])
        value['records'].append(dict(claim,id='conflicting-terminal-claim',result_sha256='0'*64));file.write_bytes(encode(value));code,out=self.invoke(script,['--input',file]);self.assertEqual(code,1);self.assertIn('CLAIM_RESULT_CONFLICT',out['assessment']['key_groups'][0]['failed_criteria']);self.assertFalse(out['execution_performed'])
