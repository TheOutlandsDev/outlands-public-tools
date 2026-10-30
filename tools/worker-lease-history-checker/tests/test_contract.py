import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import leases as app
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
        for key in ['items_sha256', 'lease_events_sha256', 'as_of_sha256']:self.assertIsNone(out[key])
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
        for path in [['items'], ['lease_events']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['items_sha256', 'lease_events_sha256', 'as_of_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['items'], ['lease_events']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['items'], ['lease_events']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['items'], ['lease_events']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['items'], ['lease_events']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['items'], ['lease_events']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['items'], ['lease_events']][0]).clear();self.withheld(value)

    def event(self,id,ordinal,at,action='acquire',worker='worker-beta',token=2,until=50):
        return dict(self.value['lease_events'][0],id=id,ordinal=ordinal,at=at,action=action,worker=worker,token=token,until=until)
    def test_known_expiry_takeover_and_renewal_windows(self):
        out=self.run_value();windows=out['assessment']['ownership_windows'];self.assertEqual([(v['worker'],v['token'],v['start'],v['end']) for v in windows],[('worker-alpha',1,10,20),('worker-beta',2,20,50)]);self.assertEqual(out['assessment']['items'][0]['current_owner']['token'],2)
    def test_expiry_is_exclusive_and_no_active_owner_is_not_a_failure(self):
        self.value['as_of']=50;out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNone(out['assessment']['items'][0]['current_owner']);self.assertFalse(r.owns(out['assessment']['ownership_windows'],'hvac-summary-job','worker-beta',2,50))
    def test_overlapping_acquisition_is_not_applied(self):
        self.value['lease_events'][1]['at']=19;out=self.review();row=out['assessment']['items'][0]['history'][1];self.assertFalse(row['applied']);self.assertIn('LEASE_OVERLAP',row['failed_criteria']);self.assertEqual(len(out['assessment']['ownership_windows']),1)
    def test_expired_token_cannot_be_reused_or_decreased(self):
        for token in (1,):
            value=copy.deepcopy(self.value);value['lease_events'][1]['token']=token;self.assertIn('TOKEN_NOT_INCREASING',self.review(value)['assessment']['items'][0]['history'][1]['failed_criteria'])
    def test_rejected_acquisition_still_records_highest_declared_issued_token(self):
        self.value['lease_events']=[self.value['lease_events'][0],self.event('overlap',2,15,token=5,until=30),self.event('later',3,20,token=4,until=40)];out=self.review();self.assertEqual(out['assessment']['items'][0]['highest_declared_acquire_token'],5);self.assertIn('TOKEN_NOT_INCREASING',out['assessment']['items'][0]['history'][2]['failed_criteria'])
    def test_renewal_requires_live_exact_owner_and_actual_extension(self):
        for change in ({'worker':'worker-alpha'},{'token':3},{'until':40},{'at':40,'until':50}):
            value=copy.deepcopy(self.value);value['lease_events'][2].update(change);self.assertFalse(self.review(value)['assessment']['items'][0]['history'][2]['applied'])
    def test_release_truncates_window_and_allows_explicit_new_owner(self):
        self.value['lease_events']=[self.value['lease_events'][0],self.event('release',2,15,'release','worker-alpha',1,None),self.event('next',3,15,token=2,until=30)];out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual([v['end'] for v in out['assessment']['ownership_windows']],[15,30]);self.assertIsNone(out['assessment']['items'][0]['current_owner'])
    def test_future_lease_event_is_visible_and_does_not_change_ownership(self):
        self.value['as_of']=25;out=self.review();self.assertEqual(out['assessment']['items'][0]['current_owner']['until'],40);self.assertFalse(out['assessment']['items'][0]['history'][2]['applied'])
    def test_missing_history_is_unknown_not_free_or_owned(self):
        self.value['lease_events']=[];out=self.review();self.assertIsNone(out['assessment']['items'][0]['current_owner']);self.assertEqual(out['assessment']['ownership_windows'],[])
    def test_gaps_reversed_times_and_different_ids_claiming_same_slot_withhold(self):
        for change in ({'ordinal':4},{'at':9}):
            value=copy.deepcopy(self.value);value['lease_events'][1].update(change);self.withheld(value)
        self.value['lease_events'].append(dict(self.value['lease_events'][0],id='alias'));self.withheld()
    def test_exact_item_binding_and_event_shapes_are_required(self):
        for change in ({'item':'other'},{'item_revision':2},{'item_sha256':'0'*64},{'token':True},{'until':10},{'action':'execute'}):
            value=copy.deepcopy(self.value);value['lease_events'][0].update(change);self.withheld(value)
    def test_boolean_asof_and_empty_items_are_refused_conservatively(self):
        value=copy.deepcopy(self.value);value['items']=[];self.withheld(value);self.value['as_of']=True
        with self.assertRaises(t.Rejected):self.run_value()
