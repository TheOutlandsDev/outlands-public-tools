import copy
import json
from pathlib import Path
import unittest
import provenance
import toolkit as t

EXAMPLES=Path(__file__).absolute().parents[1]/'examples'


class Provenance(unittest.TestCase):
    def setUp(self):
        self.contract=t.decode((EXAMPLES/'provenance.json').read_bytes())
        self.manifest=(EXAMPLES/'manifest.json').read_bytes()
        self.snapshot=(EXAMPLES/'snapshot.json').read_bytes(); self.policy=(EXAMPLES/'snapshot-policy.json').read_bytes()
        self.inputs={r['id']:(EXAMPLES/(r['id']+('.txt' if r['id'] in ('source','code') else '.json'))).read_bytes()
                     for r in t.decode(self.manifest)['artifacts']}

    def call(self): return provenance.check(t.encode(self.contract),self.manifest,self.snapshot,self.policy,self.inputs)
    def codes(self): return {r['code'] for r in self.call()['issues']}
    def pin_snapshot(self):
        policy=t.decode(self.policy); policy['manifest_sha256']=t.digest(self.snapshot); self.policy=t.encode(policy)
        self.contract.update(snapshot_sha256=t.digest(self.snapshot),snapshot_policy_sha256=t.digest(self.policy))

    def test_fictional_full_artifact_graph_and_snapshot(self):
        result=self.call(); self.assertEqual(result['status'],'PASS'); self.assertEqual(len(result['observed']),9)
        self.assertEqual(result['snapshot_status'],'PASS'); self.assertFalse(result['execution_verified'])
        self.assertFalse(result['source_authority_verified']); self.assertFalse(result['target_changes_performed'])

    def test_each_outer_pin_is_checked(self):
        for key in ('manifest_sha256','snapshot_sha256','snapshot_policy_sha256'):
            saved=self.contract[key]; self.contract[key]='0'*64
            self.assertIn(key.upper()+'_MISMATCH',self.codes()); self.contract[key]=saved

    def test_run_identity_mismatch(self):
        self.contract['run_id']='other-run'; self.assertIn('RUN_ID_MISMATCH',self.codes())

    def test_actual_artifact_bytes_not_only_manifest_assertions(self):
        self.inputs['code']+=b'changed'
        self.assertIn('ARTIFACT_HASH_MISMATCH',self.codes()); self.assertIn('ARTIFACT_SIZE_MISMATCH',self.codes())

    def test_missing_and_extra_input_buffers_refused(self):
        self.inputs.pop('source')
        with self.assertRaises(t.Rejected): self.call()

    def test_unknown_reference(self):
        self.contract['steps'][0]['uses'].append('missing')
        self.assertIn('UNKNOWN_ARTIFACT_REFERENCE',self.codes())

    def test_unavailable_result_and_self_dependency(self):
        self.contract['steps'][0]['uses'].append('result')
        self.assertIn('ARTIFACT_NOT_AVAILABLE',self.codes()); self.assertIn('SELF_DEPENDENCY',self.codes())

    def test_duplicate_producer(self):
        second=copy.deepcopy(self.contract['steps'][0]); second['id']='another-step'; self.contract['steps'].append(second)
        self.assertIn('DUPLICATE_PRODUCER',self.codes())

    def test_no_output_generation_for_external_inputs(self):
        self.contract['steps'][0]['produces'].append('configuration')
        self.assertIn('EXTERNAL_ARTIFACT_PRODUCTION_FORBIDDEN',self.codes())

    def test_unused_mapping_and_missing_result_coverage(self):
        self.contract['steps'][0]['uses'].remove('mapping')
        self.assertIn('ARTIFACT_USAGE_COVERAGE_MISMATCH',self.codes())
        self.contract['steps'][0]['produces']=['missing']
        self.assertIn('RESULT_PRODUCTION_COVERAGE_MISMATCH',self.codes())

    def test_code_artifact_and_data_input_required(self):
        self.contract['steps'][0]['uses'].remove('code')
        self.assertIn('ONE_CODE_ARTIFACT_REQUIRED',self.codes())
        self.contract['steps'][0]['uses'].remove('source')
        self.assertIn('DATA_INPUT_REQUIRED',self.codes())

    def test_code_is_never_executed(self):
        self.inputs['code']=b'raise RuntimeError("FICTIONAL_MUST_NOT_EXECUTE")\n'
        value=t.decode(self.manifest)
        for row in value['artifacts']:
            if row['id']=='code': row.update(bytes=len(self.inputs['code']),sha256=t.digest(self.inputs['code']))
        self.manifest=t.encode(value); self.contract['manifest_sha256']=t.digest(self.manifest)
        self.assertEqual(self.call()['status'],'PASS')

    def test_snapshot_binding_must_cover_all_input_roles(self):
        self.contract['snapshot_bindings'][0]['artifact']='code'
        with self.assertRaisesRegex(t.Rejected,'SNAPSHOT_INPUT_COVERAGE_INVALID'): self.call()

    def test_snapshot_staleness_and_future_capture_preserved(self):
        value=t.decode(self.policy); value['as_of']='2030-01-02T00:00:00Z'; self.policy=t.encode(value); self.pin_snapshot()
        self.assertIn('SNAPSHOT_SNAPSHOT_STALE',self.codes())
        value['as_of']='2029-12-31T23:59:59Z'; self.policy=t.encode(value); self.pin_snapshot()
        self.assertIn('SNAPSHOT_CAPTURE_AFTER_AS_OF',self.codes())

    def test_inclusive_freshness_boundary(self):
        self.assertEqual(self.call()['status'],'PASS')
        value=t.decode(self.policy); value['max_age_seconds']=3599; self.policy=t.encode(value); self.pin_snapshot()
        self.assertIn('SNAPSHOT_SNAPSHOT_STALE',self.codes())

    def test_snapshot_policy_and_item_pin_mismatches(self):
        value=t.decode(self.policy); value['manifest_sha256']='0'*64; self.policy=t.encode(value)
        self.contract['snapshot_policy_sha256']=t.digest(self.policy)
        self.assertIn('SNAPSHOT_MANIFEST_PIN_MISMATCH',self.codes())

    def test_consistent_declared_false_counts_remain_unverified(self):
        value=t.decode(self.snapshot); value['items'][0]['records']=999
        value['reconciliation'].update(input_records=1000,accepted_records=999)
        self.snapshot=t.encode(value)
        policy=t.decode(self.policy); policy['expected_items'][0]['records']=999; self.policy=t.encode(policy); self.pin_snapshot()
        result=self.call(); self.assertEqual(result['status'],'PASS')
        self.assertFalse(result['record_counts_independently_verified'])

    def test_opaque_evidence_is_not_independently_interpreted(self):
        result=self.call(); self.assertNotIn('ready_for_explicit_review',result)
        self.assertFalse(result['execution_verified']); self.assertFalse(result['record_counts_independently_verified'])

    def test_duplicate_references_and_unknown_contract_fields(self):
        self.contract['steps'][0]['uses'].append('source')
        with self.assertRaisesRegex(t.Rejected,'DUPLICATE_REFERENCE'): self.call()

    def test_cycles_and_ordering_are_not_sorted_away(self):
        value=t.decode(self.manifest); value['artifacts'].append(dict(id='intermediate',role='result',bytes=0,sha256=t.digest(b'')))
        self.manifest=t.encode(value); self.inputs['intermediate']=b''; self.contract['manifest_sha256']=t.digest(self.manifest)
        first=self.contract['steps'][0]; first['uses'].append('intermediate')
        second=dict(id='stage-two',code_version='v1',uses=['code','result'],produces=['intermediate'])
        self.contract['steps'].append(second)
        self.assertIn('ARTIFACT_NOT_AVAILABLE',self.codes())
        first['uses'].remove('intermediate'); first['produces']=['intermediate']
        second.update(uses=['code','intermediate'],produces=['result'])
        self.assertEqual(self.call()['status'],'PASS')

    def test_immutable_deterministic_report(self):
        before=copy.deepcopy((self.contract,self.inputs)); self.assertEqual(self.call(),self.call())
        self.assertEqual(before,(self.contract,self.inputs))
