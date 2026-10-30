import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import retries as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['policy_sha256', 'operations_sha256', 'attempts_sha256', 'budget_review_sha256']:self.assertIsNone(r[key])
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
        for key in ['operations', 'attempts']:self.value[key].reverse()
        after=self.run_value()
        for key in ['policy_sha256', 'operations_sha256', 'attempts_sha256', 'budget_review_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_identity_snapshots_count_once(self):
        for key in ['operations', 'attempts']:
            if not self.value[key]:continue
            value=copy.deepcopy(self.value);value[key].append(copy.deepcopy(value[key][0]));r=self.run_value(value)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_bad_rows_withhold_and_omit_supplied_values(self):
        for key in ['operations', 'attempts']:
            value=copy.deepcopy(self.value);value[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_are_fixed_refusals(self):
        for key in ['operations', 'attempts']:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);value[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def rebind(self):
        policy=copy.deepcopy(self.value['policy']);policy['retryable_failures'].sort();ops={r['id']:r for r in self.value['operations']}
        for row in self.value['attempts']:
            row['policy_sha256']=pin(policy)
            if row['operation'] in ops:row.update(operation_revision=ops[row['operation']]['revision'],operation_sha256=pin(ops[row['operation']]))
    def history(self,times):
        a=self.value['attempts'][0];self.value['attempts']=[dict(a,id='attempt-'+str(i+1),ordinal=i+1,at=at) for i,at in enumerate(times)]
    def test_known_due_boundary_and_manual_review_not_authorization(self):
        r=self.run_value();a=r['assessment']['operations'][0];self.assertEqual((a['attempts'],a['remaining_attempts'],a['earliest_next_at']),(1,2,15));self.assertTrue(a['eligible_for_manual_attempt_review']);self.assertFalse(r['retry_authorized'])
        self.value['as_of']=14;self.assertEqual(self.run_value()['assessment']['operations'][0]['state'],'waiting')
        self.value['as_of']=15;self.assertEqual(self.run_value()['assessment']['operations'][0]['state'],'ready_for_manual_review')
    def test_capped_exponential_delay_is_exact(self):
        self.value['policy'].update(maximum_attempts=5,maximum_delay=7);self.history([10,15,22]);self.rebind();self.value['as_of']=28;a=self.run_value()['assessment']['operations'][0]
        self.assertEqual(a['earliest_next_at'],29);self.assertEqual(a['state'],'waiting');self.value['as_of']=29;self.assertTrue(self.run_value()['assessment']['operations'][0]['eligible_for_manual_attempt_review'])
    def test_zero_delay_is_explicit_and_equal_time_is_allowed(self):
        self.value['policy'].update(base_delay=0,maximum_delay=0);self.history([10,10]);self.value['as_of']=10;self.rebind();self.assertEqual(self.run_value()['status'],'PASS')
    def test_exhausted_budget_can_pass_consistency_without_retry_eligibility(self):
        self.history([10,15,25]);self.value['as_of']=25;a=self.run_value()['assessment']['operations'][0];self.assertEqual(a['state'],'exhausted');self.assertEqual(a['remaining_attempts'],0);self.assertFalse(a['eligible_for_manual_attempt_review'])
    def test_over_cap_history_is_retained_without_truncation(self):
        self.history([10,15,25,45]);self.value['as_of']=45;r=self.review();a=r['assessment']['operations'][0];self.assertEqual(a['attempts'],4);self.assertIn('ATTEMPT_CAP_EXCEEDED',a['failed_criteria']);self.assertIsNone(r['budget_review_sha256'])
    def test_early_retry_is_a_visible_policy_finding_and_disables_manual_eligibility(self):
        self.history([10,14]);self.value['as_of']=25;a=self.review()['assessment']['operations'][0];self.assertEqual(a['early_attempt_ids'],['attempt-2']);self.assertFalse(a['eligible_for_manual_attempt_review']);self.assertEqual(a['state'],'policy_review_required')
    def test_unknown_outcome_and_missing_history_never_become_retry_ready(self):
        self.value['attempts'][0].update(status='unknown',failure_class=None,result_sha256=None);a=self.review()['assessment']['operations'][0];self.assertEqual(a['state'],'unknown');self.assertIsNone(a['earliest_next_at'])
        self.value['attempts']=[];a=self.review()['assessment']['operations'][0];self.assertEqual(a['state'],'no_receipts');self.assertFalse(a['eligible_for_manual_attempt_review'])
    def test_success_and_nonretryable_failure_are_terminal_consistent_states(self):
        self.value['attempts'][0].update(status='succeeded',failure_class=None);self.assertEqual(self.run_value()['assessment']['operations'][0]['state'],'succeeded')
        self.value['attempts'][0].update(status='failed',failure_class='transient');self.assertEqual(self.run_value()['assessment']['operations'][0]['state'],'terminal_failed')
    def test_attempt_after_success_unknown_or_nonretryable_failure_withholds(self):
        for change in ({'status':'succeeded','failure_class':None},{'status':'unknown','failure_class':None,'result_sha256':None},{'failure_class':'transient'}):
            original=copy.deepcopy(self.value);self.history([10,15]);self.value['attempts'][0].update(change);self.withheld();self.value=original
    def test_future_receipts_nonmonotonic_time_and_ordinal_gaps_withhold(self):
        value=copy.deepcopy(self.value);value['attempts'][0]['at']=21;self.withheld(value)
        value=copy.deepcopy(self.value);value['attempts'][0]['ordinal']=2;self.withheld(value)
        self.history([10,9]);self.withheld()
    def test_distinct_ids_at_one_operation_ordinal_are_ambiguous(self):
        self.value['attempts'].append(dict(self.value['attempts'][0],id='attempt-other'));self.withheld()
    def test_key_aliases_cannot_split_an_attempt_budget(self):
        self.value['operations'].append(dict(self.value['operations'][0],id='operation-alias'));self.withheld()
    def test_exact_operation_and_policy_pins_are_required(self):
        for change in ({'operation':'missing'},{'operation_revision':2},{'operation_sha256':'0'*64},{'policy_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['attempts'][0].update(change);self.withheld(value)
    def test_policy_revision_change_cannot_reuse_old_receipt_pin(self):
        self.value['policy']['revision']=2;self.withheld()
    def test_conditional_receipt_shapes_and_boolean_ordinals_reject_rows(self):
        for change in ({'ordinal':True},{'at':True},{'failure_class':None},{'result_sha256':None},{'status':'pending'},{'status':'unknown'}):
            value=copy.deepcopy(self.value);value['attempts'][0].update(change);self.withheld(value)
    def test_policy_bounds_unknown_classes_and_invalid_delays_refuse(self):
        for change in ({'maximum_attempts':0},{'maximum_attempts':33},{'base_delay':21},{'retryable_failures':['other']},{'maximum_delay':True}):
            value=copy.deepcopy(self.value);value['policy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(value)
    def test_maximum_supported_ordinal_has_bounded_future_deadline(self):
        self.value['attempts'][0]['at']=1000000000000;self.value['as_of']=1000000000000;a=self.run_value()['assessment']['operations'][0];self.assertEqual(a['earliest_next_at'],1000000000005);self.assertEqual(a['state'],'waiting')
    def test_empty_operations_withhold(self):
        self.value['operations']=[];self.withheld()
