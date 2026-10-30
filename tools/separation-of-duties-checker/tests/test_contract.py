import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import duties as app
import access_core as r

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
        for key in ['policy_sha256', 'role_constraints_sha256', 'workflow_constraints_sha256', 'events_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('identity_authenticated','authorization_verified','access_enforced','permissions_changed','accounts_changed','network_accessed','actions_executed','records_changed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['role_constraints'], ['workflow_constraints'], ['events']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['policy_sha256', 'role_constraints_sha256', 'workflow_constraints_sha256', 'events_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['role_constraints'], ['workflow_constraints'], ['events']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['role_constraints'], ['workflow_constraints'], ['events']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next((k for k in row if k!='id'),None)
            if field is None:continue  # ID-only declarations have no valid conflicting payload.
            if type(row[field]) is list:row[field]=['other-declared-id']+row[field][1:]
            else:row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['role_constraints'], ['workflow_constraints'], ['events']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['role_constraints'], ['workflow_constraints'], ['events']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['role_constraints'], ['workflow_constraints'], ['events']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['role_constraints'], ['workflow_constraints'], ['events']][0]).clear();self.withheld(value)

    def repin(self):
        policy=copy.deepcopy(self.value['policy'])
        for field in ('roles','actions','resources','assignments','rules'):policy[field].sort(key=lambda row:row['id'])
        for row in policy['roles']:row['inherits'].sort()
        for row in policy['assignments']:row['roles'].sort()
        for row in self.value['events']:row['policy_sha256']=pin(policy)
    def test_known_separate_actors_have_no_role_or_workflow_conflict(self):
        out=self.run_value();self.assertEqual(out['assessment']['role_conflicts'],[]);self.assertEqual(out['assessment']['workflow_conflicts'],[]);self.assertFalse(out['assessment']['event_permissions_checked']);self.assertFalse(out['assessment']['workflow_history_complete'])
    def test_prohibited_roles_include_inherited_membership(self):
        self.value['policy']['roles'][1]['inherits']=['observer','technician'];self.repin();out=self.review();self.assertEqual(out['assessment']['role_conflicts'][0]['actor'],'actor-beta')
    def test_same_actor_same_resource_incompatible_action_claims_are_visible(self):
        self.value['events'][1]['actor']='actor-alpha';out=self.review();row=out['assessment']['workflow_conflicts'][0];self.assertEqual(row['actor'],'actor-alpha');self.assertEqual(row['left_event_ids'],['event-approve']);self.assertEqual(row['right_event_ids'],['event-submit'])
    def test_different_resources_do_not_merge_workflow_histories(self):
        self.value['policy']['resources'].append(dict(id='hvac-other-proposal'));self.repin();self.value['events'][1].update(actor='actor-alpha',resource='hvac-other-proposal');self.assertEqual(self.run_value()['status'],'PASS')
    def test_events_are_not_filtered_by_declared_permissions(self):
        self.value['events'][1]['actor']='actor-unassigned';self.value['events'][0]['actor']='actor-unassigned';self.assertEqual(self.review()['assessment']['workflow_conflicts'][0]['actor'],'actor-unassigned')
    def test_swapped_constraint_normalization_and_aliases(self):
        before=self.run_value();self.value['role_constraints'][0]['roles'].reverse();flow=self.value['workflow_constraints'][0];flow['left_action'],flow['right_action']=flow['right_action'],flow['left_action'];after=self.run_value();self.assertEqual(before['qualified_scope_sha256'],after['qualified_scope_sha256']);self.value['workflow_constraints'].append(dict(flow,id='alias'));self.withheld()
    def test_missing_assignments_or_events_are_review_not_clearance(self):
        value=copy.deepcopy(self.value);value['events']=[];self.assertEqual(self.review(value)['assessment']['declared_event_count'],0);self.value['policy']['assignments']=[];self.repin();self.assertEqual(self.review()['assessment']['declared_actor_count'],0)
    def test_no_constraints_never_passes_vacuously(self):
        self.value['role_constraints']=[];self.value['workflow_constraints']=[];self.withheld()
    def test_role_only_and_workflow_only_scopes_are_explicit(self):
        value=copy.deepcopy(self.value);value['role_constraints']=[];self.assertEqual(self.run_value(value)['status'],'PASS');self.value['workflow_constraints']=[];self.value['events']=[];self.assertEqual(self.run_value()['status'],'PASS')
    def test_stale_policy_unknown_constraints_and_bad_event_references_withhold(self):
        value=copy.deepcopy(self.value);value['events'][0]['policy_sha256']='0'*64;self.withheld(value)
        value=copy.deepcopy(self.value);value['role_constraints'][0]['roles'][0]='other';self.withheld(value)
        self.value['workflow_constraints'][0]['left_action']='other';self.withheld()
    def test_duty_scope_product_limit_is_explicit(self):
        self.value['workflow_constraints']=[dict(self.value['workflow_constraints'][0],id='constraint-'+str(i)) for i in range(21)];self.value['events']=[dict(self.value['events'][0],id='event-'+str(i)) for i in range(1000)]
        with self.assertRaisesRegex(t.Rejected,'DUTY_SCOPE_LIMIT'):self.run_value()
    def test_repeated_declared_events_are_complete_evidence_not_hidden(self):
        self.value['events'][1]['actor']='actor-alpha';self.value['events'].append(dict(self.value['events'][0],id='event-submit-two'));row=self.review()['assessment']['workflow_conflicts'][0];self.assertEqual(row['right_event_ids'],['event-submit','event-submit-two'])
