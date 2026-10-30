import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import decisions as app
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
        for key in ['policy_sha256', 'requests_sha256']:self.assertIsNone(out[key])
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
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['requests']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['policy_sha256', 'requests_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['requests']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['requests']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next((k for k in row if k!='id'),None)
            if field is None:continue  # ID-only declarations have no valid conflicting payload.
            if type(row[field]) is list:row[field]=['other-declared-id']+row[field][1:]
            else:row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['requests']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['requests']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['requests']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules'], ['requests']][0]).clear();self.withheld(value)

    def test_known_allow_and_closed_world_default_deny(self):
        out=self.run_value();rows={v['id']:v for v in out['assessment']['requests']};self.assertEqual(rows['request-approve']['decision'],'allow');self.assertEqual(rows['request-unassigned']['decision'],'deny');self.assertEqual(rows['request-unassigned']['reason'],'default_deny');self.assertFalse(rows['request-unassigned']['assignment_present'])
    def test_explicit_deny_overrides_allow_through_inherited_role(self):
        self.value['policy']['rules'].append(dict(id='deny-inherited',role='observer',action='approve',resource='hvac-service-proposal',effect='deny'));row=self.review()['assessment']['requests'][0];self.assertEqual(row['decision'],'deny');self.assertEqual(row['reason'],'explicit_deny');self.assertEqual(row['matching_allow_rule_ids'],['allow-approve']);self.assertEqual(row['matching_deny_rule_ids'],['deny-inherited'])
    def test_no_matching_rule_or_no_declared_roles_is_deny(self):
        self.value['requests']=[dict(self.value['requests'][0],actor='actor-alpha',expected='deny')];self.assertEqual(self.run_value()['assessment']['requests'][0]['reason'],'default_deny');self.value['policy']['assignments']=[];self.assertEqual(self.run_value()['status'],'PASS')
    def test_expectation_mismatch_retains_diagnostic_not_qualified_scope(self):
        self.value['requests'][0]['expected']='deny';out=self.review();self.assertFalse(out['assessment']['requests'][0]['expectation_met']);self.assertIsNotNone(out['policy_sha256'])
    def test_null_expectation_is_not_an_approval(self):
        for row in self.value['requests']:row['expected']=None
        out=self.run_value();self.assertTrue(all(v['expectation_met'] is None for v in out['assessment']['requests']));self.assertFalse(out['authorization_verified'])
    def test_unknown_action_or_resource_withholds_instead_of_assuming_safe_denial(self):
        for change in ({'action':'other'},{'resource':'other'}):
            value=copy.deepcopy(self.value);value['requests'][0].update(change);self.withheld(value)
    def test_empty_request_scope_never_passes_vacuously(self):
        self.value['requests']=[];self.withheld()
    def test_actor_identity_is_symbolic_without_lookup(self):
        self.value['requests']=[dict(self.value['requests'][0],actor='invented-unassigned-actor',expected='deny')];out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['identity_authenticated']);self.assertFalse(out['network_accessed'])
    def test_cyclic_or_ambiguous_policy_withholds_all_decisions(self):
        self.value['policy']['roles'][0]['inherits']=['technician'];self.withheld()
    def test_decision_scope_product_limit_is_explicit(self):
        self.value['requests']=[dict(self.value['requests'][0],id='request-'+str(i)) for i in range(1000)];self.value['policy']['rules']=[dict(self.value['policy']['rules'][0],id='rule-'+str(i)) for i in range(51)]
        with self.assertRaisesRegex(t.Rejected,'DECISION_SCOPE_LIMIT'):self.run_value()
    def test_unknown_fields_boolean_revision_and_invalid_expected_are_rejected(self):
        for change in ({'revision':True},{'expected':True},{'actor':'INVALID_SENTINEL'},{'extra':0}):
            value=copy.deepcopy(self.value);value['requests'][0].update(change);self.withheld(value)
    def test_permission_lists_are_order_independent_and_all_reasons_retained(self):
        policy=self.value['policy'];policy['rules'].append(dict(id='also-allow',role='observer',action='approve',resource='hvac-service-proposal',effect='allow'));before=self.run_value();policy['rules'].reverse();after=self.run_value();self.assertEqual(before['assessment'],after['assessment']);self.assertEqual(after['assessment']['requests'][0]['matching_allow_rule_ids'],['allow-approve','also-allow'])
