import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import ledger as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['operations_sha256', 'records_sha256', 'ledger_reconciliation_sha256']:self.assertIsNone(r[key])
        return r
    def test_positive_and_authority_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('artifact_bytes_verified','record_authenticity_verified','actual_cache_state_verified','cache_mutated','execution_performed','exactly_once_verified','retry_authorized','provider_contacted','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_preserves_full_scope_pins(self):
        before=self.run_value()
        for key in ['operations', 'records']:self.value[key].reverse()
        after=self.run_value()
        for key in ['operations_sha256', 'records_sha256', 'ledger_reconciliation_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_identity_snapshots_count_once(self):
        for key in ['operations', 'records']:
            if not self.value[key]:continue
            value=copy.deepcopy(self.value);value[key].append(copy.deepcopy(value[key][0]));r=self.run_value(value)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_bad_rows_withhold_and_omit_supplied_values(self):
        for key in ['operations', 'records']:
            value=copy.deepcopy(self.value);value[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_are_fixed_refusals(self):
        for key in ['operations', 'records']:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);value[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_consistent_failed_claim_is_not_a_success_or_execution_proof(self):
        r=self.run_value();a=r['assessment']['key_groups'][0];self.assertTrue(a['unambiguous_terminal_claim']);self.assertEqual(a['declared_state'],'failed');self.assertEqual(a['declared_result_sha256'],self.value['records'][0]['result_sha256']);self.assertFalse(r['exactly_once_verified'])
    def test_consistent_success_is_a_declaration_only(self):
        self.value['records'][0]['state']='succeeded';r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertFalse(r['execution_performed']);self.assertFalse(r['record_authenticity_verified'])
    def test_redundant_equal_claims_do_not_become_execution_counts(self):
        self.value['records'].append(dict(self.value['records'][0],id='claim-copy'));a=self.run_value()['assessment']['key_groups'][0]
        self.assertEqual((a['claim_records'],a['distinct_claims'],a['redundant_claim_records']),(2,1,1));self.assertTrue(a['unambiguous_terminal_claim'])
    def test_state_conflict_does_not_choose_terminal_or_latest(self):
        self.value['records'].append(dict(self.value['records'][0],id='claim-pending',state='pending',result_sha256=None));r=self.review();a=r['assessment']['key_groups'][0];self.assertEqual(a['declared_state'],'unresolved');self.assertIsNone(a['declared_result_sha256']);self.assertIn('CLAIM_STATE_CONFLICT',a['failed_criteria'])
    def test_different_terminal_results_are_not_merged(self):
        self.value['records'].append(dict(self.value['records'][0],id='claim-other',result_sha256='1'*64));a=self.review()['assessment']['key_groups'][0];self.assertIn('CLAIM_RESULT_CONFLICT',a['failed_criteria']);self.assertFalse(a['unambiguous_terminal_claim'])
    def test_pending_and_unknown_each_require_review(self):
        for state,code in [('pending','PENDING_OUTCOME'),('unknown','UNKNOWN_OUTCOME')]:
            self.value['records'][0].update(state=state,result_sha256=None);r=self.review();self.assertIn(code,r['assessment']['key_groups'][0]['failed_criteria']);self.assertIsNone(r['ledger_reconciliation_sha256'])
    def test_missing_records_are_unresolved_not_zero_executions(self):
        self.value['records']=[];a=self.review()['assessment']['key_groups'][0];self.assertEqual(a['declared_state'],'unresolved');self.assertIn('OPERATION_RECEIPTS_MISSING',a['failed_criteria'])
    def test_operation_key_aliases_and_conflicting_payloads_are_visible(self):
        other=dict(self.value['operations'][0],id='operation-other',payload_sha256='1'*64);self.value['operations'].append(other)
        claim=dict(self.value['records'][0],id='claim-other',operation=other['id'],operation_sha256=pin(other),payload_sha256=other['payload_sha256']);self.value['records'].append(claim)
        a=self.review()['assessment']['key_groups'][0];self.assertIn('KEY_PAYLOAD_CONFLICT',a['failed_criteria']);self.assertIn('OPERATION_KEY_ALIASES',a['failed_criteria']);self.assertEqual(len(a['operation_ids']),2)
    def test_equal_payload_aliases_still_need_explicit_operation_resolution(self):
        other=dict(self.value['operations'][0],id='operation-other');self.value['operations'].append(other);self.value['records'].append(dict(self.value['records'][0],id='claim-other',operation=other['id'],operation_sha256=pin(other)))
        a=self.review()['assessment']['key_groups'][0];self.assertEqual(a['failed_criteria'],['OPERATION_KEY_ALIASES'])
    def test_unknown_stale_or_wrong_key_payload_binding_withholds(self):
        for change in ({'operation':'missing'},{'operation_revision':2},{'operation_sha256':'0'*64},{'key_sha256':'0'*64},{'payload_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['records'][0].update(change);self.withheld(value)
    def test_conflicting_record_identity_withholds_every_member(self):
        self.value['records'].append(dict(self.value['records'][0],state='succeeded'));r=self.withheld();self.assertEqual(r['counts']['records']['conflict_rows'],2)
    def test_invalid_record_shapes_and_unresolved_results_reject_rows(self):
        for change in ({'state':'other'},{'state':True},{'result_sha256':None},{'state':'unknown'},{'operation_revision':True}):
            value=copy.deepcopy(self.value);value['records'][0].update(change);self.withheld(value)
    def test_changed_operation_revision_cannot_reuse_old_claim(self):
        self.value['operations'][0]['revision']=2;self.withheld()
    def test_empty_operation_scope_and_bad_operation_hash_withhold(self):
        value=copy.deepcopy(self.value);value['operations']=[];self.withheld(value)
        self.value['operations'][0]['payload_sha256']='bad';self.withheld()
    def test_reconciliation_pin_binds_actual_selected_snapshots(self):
        r=self.run_value();self.assertEqual(r['operations_sha256'],pin(self.value['operations']));self.assertEqual(r['ledger_reconciliation_sha256'],pin({k:r[k] for k in ('operations_sha256','records_sha256')}))
