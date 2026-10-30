import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import freshness as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['policy_sha256', 'entries_sha256', 'invalidations_sha256']:self.assertIsNone(r[key])
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
        for key in ['entries', 'invalidations']:self.value[key].reverse()
        after=self.run_value()
        for key in ['policy_sha256', 'entries_sha256', 'invalidations_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_identity_snapshots_count_once(self):
        for key in ['entries', 'invalidations']:
            if not self.value[key]:continue
            value=copy.deepcopy(self.value);value[key].append(copy.deepcopy(value[key][0]));r=self.run_value(value)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_bad_rows_withhold_and_omit_supplied_values(self):
        for key in ['entries', 'invalidations']:
            value=copy.deepcopy(self.value);value[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_are_fixed_refusals(self):
        for key in ['entries', 'invalidations']:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);value[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_known_age_expiry_and_future_invalidation(self):
        a=self.run_value()['assessment']['entries'][0];self.assertEqual((a['state'],a['age'],a['expires_at']),('fresh',10,30));self.assertEqual(a['invalidation_ids'],[])
    def test_expiry_boundary_is_exclusive_of_freshness(self):
        self.value['as_of']=29;self.assertEqual(self.run_value()['status'],'PASS')
        self.value['as_of']=30;a=self.review()['assessment']['entries'][0];self.assertEqual(a['state'],'expired');self.assertTrue(a['expired'])
    def test_creation_boundary_and_zero_lifetime(self):
        self.value['as_of']=10;self.assertEqual(self.run_value()['assessment']['entries'][0]['age'],0)
        self.value['policy']['lifetime']=0;self.assertEqual(self.review()['assessment']['entries'][0]['state'],'expired')
    def test_invalidation_and_expiry_both_remain_visible(self):
        self.value['as_of']=40;a=self.review()['assessment']['entries'][0];self.assertEqual(a['state'],'invalidated');self.assertEqual(a['failed_criteria'],['DEPENDENCY_INVALIDATED','LIFETIME_EXPIRED']);self.assertEqual(a['invalidation_ids'],['invalidate-job'])
    def test_future_creation_has_no_age_and_is_not_usable(self):
        self.value['as_of']=9;a=self.review()['assessment']['entries'][0];self.assertEqual(a['state'],'future_creation');self.assertIsNone(a['age']);self.assertFalse(a['eligible_for_manual_read_review'])
    def test_exact_snapshot_invalidation_does_not_invalidate_a_new_revision(self):
        self.value['invalidations'][0]['at']=15
        other=copy.deepcopy(self.value['entries'][0]);other.update(id='cache-bravo',key_sha256='1'*64);other['inputs'][0]['revision']=2;self.value['entries'].append(other)
        r=self.review();self.assertEqual([row['state'] for row in r['assessment']['entries']],['invalidated','fresh'])
    def test_creation_after_invalidation_cannot_resurrect_same_dependency_snapshot(self):
        self.value['invalidations'][0]['at']=15;self.value['entries'][0]['created_at']=18;a=self.review()['assessment']['entries'][0];self.assertEqual(a['state'],'invalidated')
    def test_all_applicable_invalidation_declarations_are_retained(self):
        self.value['invalidations'].append(dict(self.value['invalidations'][0],id='invalidate-earlier',at=15));self.value['as_of']=40
        self.assertEqual(self.review()['assessment']['entries'][0]['invalidation_ids'],['invalidate-earlier','invalidate-job'])
    def test_unknown_invalidation_snapshot_is_not_ignored_even_if_future(self):
        for change in ({'dependency':'missing'},{'dependency_revision':2},{'dependency_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['invalidations'][0].update(change);self.withheld(value)
    def test_distinct_entry_ids_for_same_key_are_ambiguous(self):
        self.value['entries'].append(dict(self.value['entries'][0],id='cache-alias'));self.withheld()
    def test_conflicting_invalidation_identity_withholds_group(self):
        self.value['invalidations'].append(dict(self.value['invalidations'][0],at=15));r=self.withheld();self.assertEqual(r['counts']['invalidations']['conflict_rows'],2)
    def test_policy_and_as_of_types_are_fixed_refusals(self):
        for value in (True,-1,1000000000001):
            v=copy.deepcopy(self.value);v['as_of']=value
            with self.assertRaises(t.Rejected):self.run_value(v)
        for value in (True,-1,1000000001):
            v=copy.deepcopy(self.value);v['policy']['lifetime']=value
            with self.assertRaises(t.Rejected):self.run_value(v)
    def test_bad_entry_inputs_and_invalidation_ordinals_reject_rows(self):
        for inputs in (None,[],[dict(id='a',revision=True,sha256='0'*64)]):
            v=copy.deepcopy(self.value);v['entries'][0]['inputs']=inputs;self.withheld(v)
        v=copy.deepcopy(self.value);v['invalidations'][0]['at']=True;self.withheld(v)
    def test_empty_entries_withhold_but_no_invalidations_is_valid(self):
        value=copy.deepcopy(self.value);value['entries']=[];self.withheld(value)
        self.value['invalidations']=[];self.assertEqual(self.run_value()['status'],'PASS')
