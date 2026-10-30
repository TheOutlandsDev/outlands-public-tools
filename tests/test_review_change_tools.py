"""Actual independent CLI and connected fictional HVAC review/change acceptance."""
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
TOOLS={'review-queue-contract-checker':'queues.py','correction-lineage-checker':'corrections.py',
       'approval-scope-checker':'approvals.py','change-impact-planner':'impacts.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-review-change-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_do_not_qualify_incomplete_or_stale_scope(self):
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json');self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNone(result['review_scope_sha256'])
            self.assertEqual(result['assessment'] is None,name=='change-impact-planner')

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_service_revision_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        lineage_input=example('correction-lineage-checker');lineage=self.run_value('correction-lineage-checker',lineage_input)
        self.assertTrue(lineage['assessment']['all_histories_complete']);after=lineage_input['snapshots'][1]
        # Explicit fictional operator adapter: lineage IDs and selected item IDs differ.
        selected=dict(id=after['record'],revision=after['revision'],artifact_sha256=after['artifact_sha256'])
        approval_input=example('approval-scope-checker');approval_input['items']=[selected]
        for event in approval_input['events']:event.update(item=selected['id'],item_revision=selected['revision'],item_sha256=sha(encode(selected)))
        approval=self.run_value('approval-scope-checker',approval_input);self.assertTrue(approval['assessment']['all_declared_scopes_covered'])
        active_ids=approval['assessment']['items'][0]['active_grant_ids'];roles=sorted({event['role'] for event in approval_input['events'] if event['id'] in active_ids})
        queue_input=example('review-queue-contract-checker');queue_input['items']=[selected];queue_input['entries'][0].update(item=selected['id'],item_revision=selected['revision'],item_sha256=sha(encode(selected)),covered_roles=roles)
        queues=self.run_value('review-queue-contract-checker',queue_input);self.assertTrue(queues['assessment']['all_covered_and_unblocked']);self.assertEqual(queues['items_sha256'],approval['items_sha256'])
        impact_input=example('change-impact-planner');self.assertEqual(impact_input['nodes'][0],selected)
        impacts=self.run_value('change-impact-planner',impact_input);self.assertEqual(len(impacts['assessment']['recheck_nodes']),3);self.assertEqual(impacts['assessment']['unaffected_node_ids'],['hvac-unrelated-demo'])
        for result in (lineage,approval,queues,impacts):
            for key in ('artifact_bytes_verified','reviewer_identity_verified','approval_authority_verified','records_changed','execution_performed','target_changes_performed'):self.assertFalse(result[key])

    def test_revocation_requires_explicit_queue_recheck_and_stale_graph_blocks_plan(self):
        approval_input=json.loads((ROOT/'tools/approval-scope-checker/examples/needs-review.json').read_text(encoding='utf-8'))
        approval=self.run_value('approval-scope-checker',approval_input,1);self.assertEqual(approval['assessment']['items'][0]['missing_roles'],['quality']);self.assertIsNone(approval['review_scope_sha256'])
        queue_input=json.loads((ROOT/'tools/review-queue-contract-checker/examples/input.json').read_text(encoding='utf-8'))
        active_ids=approval['assessment']['items'][0]['active_grant_ids'];queue_input['entries'][0]['covered_roles']=sorted({row['role'] for row in approval_input['events'] if row['id'] in active_ids})
        queues=self.run_value('review-queue-contract-checker',queue_input,1);self.assertFalse(queues['assessment']['items'][0]['ready_for_manual_review'])
        impacts=self.run_value('change-impact-planner',json.loads((ROOT/'tools/change-impact-planner/examples/needs-review.json').read_text(encoding='utf-8')),1);self.assertIsNone(impacts['assessment']);self.assertIsNone(impacts['review_scope_sha256'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_review_cli(self):
        name='review-queue-contract-checker';code,r=self.cli(name,file=ROOT/'tools'/name/'examples/game-review.json');self.assertEqual(code,0);self.assertTrue(r['assessment']['all_covered_and_unblocked']);self.assertFalse(r['reviewer_identity_verified'])
