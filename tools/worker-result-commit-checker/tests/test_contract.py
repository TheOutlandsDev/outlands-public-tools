import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import commits as app
import worker_core as r

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()
def at(value,path):
    for key in path:value=value[key]
    return value

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        out=self.run_value(value);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256']);return out
    def withheld(self,value=None):
        out=self.review(value);self.assertIsNone(out['assessment'])
        for key in ['items_sha256', 'lease_events_sha256', 'deliveries_sha256', 'results_sha256', 'commits_sha256', 'as_of_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('payloads_opened','handler_executed','artifact_bytes_verified','worker_contacted','ownership_enforced','jobs_executed','queue_changed','records_changed','results_committed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['items'], ['lease_events'], ['deliveries'], ['results'], ['commits']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['items_sha256', 'lease_events_sha256', 'deliveries_sha256', 'results_sha256', 'commits_sha256', 'as_of_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['results'], ['commits']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['results'], ['commits']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['results'], ['commits']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['results'], ['commits']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['results'], ['commits']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['items'], ['lease_events'], ['deliveries'], ['results'], ['commits']][0]).clear();self.withheld(value)

    def repin_result(self):self.value['commits'][0]['result_sha256']=pin(self.value['results'][0])
    def repin_delivery(self):self.value['results'][0]['delivery_sha256']=pin(self.value['deliveries'][0]);self.repin_result()
    def test_known_commit_binds_exact_result_and_current_owner(self):
        out=self.run_value();self.assertEqual(out['assessment']['items'][0]['consistent_commit_id'],'commit-current');self.assertTrue(out['assessment']['commits'][0]['consistent']);self.assertFalse(out['assessment']['commit_verified']);self.assertFalse(out['artifact_bytes_verified'])
    def test_missing_commit_and_empty_results_are_not_success(self):
        self.value['commits']=[];out=self.review();self.assertIsNone(out['assessment']['items'][0]['consistent_commit_id']);self.value['results']=[];self.assertEqual(self.review()['assessment']['results'],[])
    def test_alias_commits_are_ambiguous_not_latest_or_equal_payload_selection(self):
        self.value['commits'].append(dict(self.value['commits'][0],id='alias'));out=self.review();self.assertIsNone(out['assessment']['items'][0]['consistent_commit_id']);self.assertTrue(all('COMMIT_SLOT_AMBIGUOUS' in v['failed_criteria'] for v in out['assessment']['commits']))
    def test_expired_owner_cannot_commit_even_when_result_was_timely(self):
        self.value['commits'][0]['at']=50;self.value['as_of']=50;out=self.review();self.assertTrue(out['assessment']['results'][0]['consistent']);self.assertIn('COMMIT_OWNER_NOT_ACTIVE',out['assessment']['commits'][0]['failed_criteria'])
    def test_late_old_result_is_retained_and_cannot_be_committed(self):
        self.value['deliveries'][0].update(at=12,worker='worker-alpha',token=1);self.repin_delivery();self.value['results'][0].update(at=25,worker='worker-alpha',token=1);self.repin_result();self.value['commits'][0].update(worker='worker-alpha',token=1);out=self.review();self.assertIn('RESULT_OWNER_NOT_ACTIVE',out['assessment']['results'][0]['failed_criteria']);self.assertIn('COMMIT_RESULT_INVALID',out['assessment']['commits'][0]['failed_criteria'])
    def test_result_and_commit_owner_must_match_their_exact_source_record(self):
        value=copy.deepcopy(self.value);value['commits'][0]['worker']='worker-other';self.assertIn('COMMIT_RESULT_OWNER_MISMATCH',self.review(value)['assessment']['commits'][0]['failed_criteria'])
        self.value['results'][0]['worker']='worker-other';self.repin_result();self.assertIn('RESULT_DELIVERY_OWNER_MISMATCH',self.review()['assessment']['results'][0]['failed_criteria'])
    def test_exact_input_handler_result_contract_and_source_pins_withhold(self):
        for change in ({'input_sha256':'0'*64},{'handler_sha256':'0'*64},{'result_contract_sha256':'0'*64},{'delivery_sha256':'0'*64},{'item_revision':2}):
            value=copy.deepcopy(self.value);value['results'][0].update(change);self.withheld(value)
        self.value['commits'][0]['result_sha256']='0'*64;self.withheld()
    def test_result_before_delivery_and_commit_before_result_withhold(self):
        value=copy.deepcopy(self.value);value['results'][0]['at']=21;self.withheld(value);self.value['commits'][0]['at']=33;self.withheld()
    def test_future_result_or_commit_is_visible_but_not_consistent(self):
        self.value['results'][0]['at']=41;self.repin_result();self.value['commits'][0]['at']=42;out=self.review();self.assertIn('RESULT_AFTER_AS_OF',out['assessment']['results'][0]['failed_criteria']);self.assertIn('COMMIT_AFTER_AS_OF',out['assessment']['commits'][0]['failed_criteria'])
    def test_result_alias_for_same_delivery_is_a_structural_ambiguity(self):
        self.value['results'].append(dict(self.value['results'][0],id='alias'));self.withheld()
    def test_invalid_lease_history_withholds_complete_result_assessment(self):
        self.value['lease_events'][1]['at']=19;self.withheld()
    def test_unopened_artifact_fingerprint_is_an_opaque_claim(self):
        self.value['results'][0]['artifact_sha256']='0'*64;self.repin_result();out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['artifact_bytes_verified']);self.assertFalse(out['results_committed'])
