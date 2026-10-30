import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import approvals as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['review_scope_sha256', 'items_sha256', 'events_sha256', 'policy_sha256']:self.assertIsNone(r[key])
        return r
    def test_positive_and_authority_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('artifact_bytes_verified','reviewer_identity_verified','approval_authority_verified','records_changed','execution_performed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_preserves_full_scope_pins(self):
        before=self.run_value()
        for key in ['items', 'events']:self.value[key].reverse()
        after=self.run_value()
        for key in ['review_scope_sha256', 'items_sha256', 'events_sha256', 'policy_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_identity_snapshots_count_once(self):
        for key in ['items', 'events']:
            if not self.value[key]:continue
            value=copy.deepcopy(self.value);value[key].append(copy.deepcopy(value[key][0]));r=self.run_value(value)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_bad_rows_withhold_and_omit_supplied_values(self):
        for key in ['items', 'events']:
            value=copy.deepcopy(self.value);value[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_are_fixed_refusals(self):
        for key in ['items', 'events']:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);value[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_conflicting_identity_groups_exclude_every_member(self):
        for side in ['items', 'events']:
            if not self.value[side]:continue
            value=copy.deepcopy(self.value);row=copy.deepcopy(value[side][0])
            field=next(k for k in row if k!='id' and isinstance(row[k],(str,int)) and row[k] is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            value[side].extend([row,copy.deepcopy(value[side][0])]);r=self.withheld(value)
            self.assertEqual(r['counts'][side]['conflict_rows'],3)
    def test_input_pin_is_raw_and_reports_are_deterministic(self):
        raw=encode(self.value);r=app.check(raw);self.assertEqual(r['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(r,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(r['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(r['review_scope_sha256'],app.check(spaced)['review_scope_sha256'])
    def test_required_cohort_is_not_vacuously_valid(self):
        self.value[['items', 'events'][0]]=[];self.withheld()
    def test_unknown_fields_and_nonobjects_are_rejected_rows(self):
        for side in ['items', 'events']:
            value=copy.deepcopy(self.value);value[side].append(None);self.withheld(value)
            if value[side][:-1]:
                value=copy.deepcopy(self.value);value[side][0]['extra']=0;self.withheld(value)

    def revoke(self,at=20):
        return dict(self.value['events'][0],id='revocation',at=at,action='revoke',grant=self.value['events'][0]['id'])
    def test_known_coverage_and_exact_boundary_revocation(self):
        r=self.run_value();self.assertEqual(r['assessment']['items'][0]['active_grant_ids'],['grant-quality','grant-service'])
        self.value['events'].append(self.revoke());r=self.review();self.assertEqual(r['assessment']['items'][0]['missing_roles'],['quality']);self.assertEqual(r['assessment']['items'][0]['revoked_grant_ids'],['grant-quality'])
    def test_future_revocation_and_grant_are_visible_but_not_active(self):
        self.value['events'].append(self.revoke(21));r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(r['assessment']['future_event_ids'],['revocation'])
        self.value['as_of']=9;r=self.review();self.assertEqual(r['assessment']['items'][0]['active_grant_ids'],[])
    def test_same_ordinal_or_earlier_revocation_is_invalid(self):
        for at in (9,10):
            value=copy.deepcopy(self.value);value['events'].append(self.revoke(at));self.withheld(value)
    def test_unknown_grant_or_revoking_revocation_withholds(self):
        revoke=self.revoke();revoke['grant']='missing';self.value['events'].append(revoke);self.withheld()
    def test_reviewer_or_role_mismatch_cannot_revoke(self):
        for change in ({'reviewer':'other'},{'role':'service'}):
            value=copy.deepcopy(self.value);value['events'].append(dict(self.revoke(),**change));self.withheld(value)
    def test_new_revision_does_not_inherit_old_approval(self):
        self.value['items'][0]['revision']=3;self.withheld()
    def test_policy_and_asof_change_scope_pin(self):
        before=self.run_value()['review_scope_sha256'];self.value['as_of']=21;self.assertNotEqual(self.run_value()['review_scope_sha256'],before)
        self.value['policy']['revision']=2;self.withheld()
        for row in self.value['events']:row['policy_sha256']=pin(self.value['policy'])
        self.assertNotEqual(self.run_value()['review_scope_sha256'],before)
    def test_missing_events_is_missing_coverage_not_authentication(self):
        self.value['events']=[];r=self.review();self.assertFalse(r['assessment']['all_declared_scopes_covered']);self.assertFalse(r['reviewer_identity_verified'])
    def test_scope_slot_ambiguity_withholds(self):
        self.value['events'].append(dict(self.value['events'][0],id='alias'));self.withheld()
    def test_reapproval_does_not_erase_revocation_history(self):
        self.value['events'].append(self.revoke());self.value['events'].append(dict(self.value['events'][0],id='new-grant',at=21));self.value['as_of']=21
        r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(r['assessment']['items'][0]['revoked_grant_ids'],['grant-quality']);self.assertEqual(r['assessment']['items'][0]['active_grant_ids'],['grant-service','new-grant'])
    def test_out_of_order_input_is_ordered_by_explicit_at_not_list(self):
        self.value['events'].insert(0,self.revoke());r=self.review();self.assertEqual(r['assessment']['items'][0]['missing_roles'],['quality'])
    def test_boolean_asof_and_invalid_event_action_refuse(self):
        value=copy.deepcopy(self.value);value['as_of']=True
        with self.assertRaises(t.Rejected):self.run_value(value)
        self.value['events'][0]['action']='execute';self.withheld()
    def test_grant_shape_is_exact_and_role_is_declared(self):
        for change in ({'grant':'other'},{'role':'other'},{'at':True}):
            value=copy.deepcopy(self.value);value['events'][0].update(change);self.withheld(value)
    def test_future_events_still_require_valid_scope(self):
        self.value['events'][0].update(at=100,item_sha256='0'*64);self.withheld()
    def test_a_revocation_cannot_target_another_revocation(self):
        first=self.revoke();second=dict(first,id='second-revocation',at=21,grant=first['id']);self.value['events'].extend([first,second]);self.withheld()
    def test_policy_role_order_normalizes_without_rebinding_events(self):
        before=self.run_value()['review_scope_sha256'];self.value['policy']['required_roles'].reverse();self.assertEqual(self.run_value()['review_scope_sha256'],before)
