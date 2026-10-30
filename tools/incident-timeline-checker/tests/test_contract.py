import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import incidents as app
import health_core as r

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
        for key in ['components_sha256', 'incidents_sha256', 'events_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('observations_independently_verified','artifact_bytes_verified','actual_health_verified','notifications_sent','alerts_suppressed','recovery_authorized','recovery_performed','records_changed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['components'], ['incidents'], ['events']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['components_sha256', 'incidents_sha256', 'events_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['components'], ['incidents'], ['events']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['components'], ['incidents'], ['events']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['components'], ['incidents'], ['events']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['components'], ['incidents'], ['events']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['components'], ['incidents'], ['events']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['components'], ['incidents'], ['events']][0]).clear();self.withheld(value)

    def event(self,n,action,at):
        return dict(self.value['events'][0],id='event-'+str(n),ordinal=n,action=action,at=at)
    def test_known_resolution_and_asof_replay(self):
        row=self.run_value()['assessment']['incidents'][0];self.assertEqual(row['state_as_of'],'resolved');self.assertTrue(row['resolved_as_of']);self.assertEqual(row['effective_event_ids'],['event-1','event-2','event-3'])
        self.value['as_of']=15;row=self.run_value()['assessment']['incidents'][0];self.assertEqual(row['state_as_of'],'acknowledged');self.assertFalse(row['resolved_as_of']);self.assertEqual(row['future_event_ids'],['event-3'])
    def test_reopen_requires_a_new_resolution_claim(self):
        self.value['events'].append(self.event(4,'reopen',25));row=self.run_value()['assessment']['incidents'][0];self.assertEqual(row['state_as_of'],'open');self.assertFalse(row['resolved_as_of'])
    def test_input_order_is_not_event_order(self):
        before=self.run_value();self.value['events'].reverse();self.assertEqual(self.run_value()['assessment'],before['assessment'])
    def test_equal_at_uses_explicit_ordinal(self):
        for row in self.value['events']:row['at']=10
        self.value['as_of']=10;self.assertEqual(self.run_value()['assessment']['incidents'][0]['state_as_of'],'resolved')
    def test_missing_history_and_future_only_history_never_pass_vacuously(self):
        value=copy.deepcopy(self.value);value['events']=[];self.assertEqual(self.review(value)['assessment']['incidents'][0]['state_as_of'],'not_opened')
        self.value['as_of']=9;self.assertEqual(self.review()['assessment']['incidents'][0]['future_event_ids'],['event-1','event-2','event-3'])
    def test_ordinal_gaps_time_reversal_and_duplicate_slots_withhold(self):
        for change in ({'ordinal':4},{'at':5}):
            value=copy.deepcopy(self.value);value['events'][1].update(change);self.withheld(value)
        self.value['events'].append(dict(self.value['events'][0],id='alias'));self.withheld()
    def test_illegal_transitions_never_produce_partial_timeline(self):
        for action in ('resolve','acknowledge','reopen'):
            value=copy.deepcopy(self.value);value['events'][0]['action']=action;self.withheld(value)
        self.value['events'].append(self.event(4,'acknowledge',25));self.withheld()
    def test_future_protocol_errors_are_not_filtered_away(self):
        self.value['events'].append(self.event(4,'open',100));self.withheld()
    def test_resolution_without_acknowledgement_is_an_explicit_valid_transition(self):
        self.value['events'].pop(1);self.value['events'][1]['ordinal']=2;self.assertTrue(self.run_value()['assessment']['incidents'][0]['resolved_as_of'])
    def test_incident_component_and_event_snapshot_pins_are_exact(self):
        for side,field in [('incidents','component_sha256'),('events','incident_sha256')]:
            value=copy.deepcopy(self.value);value[side][0][field]='0'*64;self.withheld(value)
    def test_empty_incident_cohort_and_bad_action_withhold(self):
        value=copy.deepcopy(self.value);value['incidents']=[];self.withheld(value);self.value['events'][0]['action']='restart';self.withheld()
