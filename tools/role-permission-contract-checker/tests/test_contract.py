import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import roles as app
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
        for key in ['policy_sha256']:self.assertIsNone(out[key])
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
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['policy_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next((k for k in row if k!='id'),None)
            if field is None:continue  # ID-only declarations have no valid conflicting payload.
            if type(row[field]) is list:row[field]=['other-declared-id']+row[field][1:]
            else:row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['policy', 'roles'], ['policy', 'actions'], ['policy', 'resources'], ['policy', 'assignments'], ['policy', 'rules']][0]).clear();self.withheld(value)

    def test_known_inherited_roles_and_literal_permission_contract(self):
        out=self.run_value();self.assertEqual(out['assessment']['roles'][2]['inherited_role_ids'],['observer']);self.assertEqual(out['assessment']['actors'][0]['effective_role_ids'],['observer','technician']);self.assertTrue(out['assessment']['inheritance_acyclic'])
    def test_unknown_role_action_and_resource_references_withhold(self):
        for change in ({'role':'other'},{'action':'other'},{'resource':'other'}):
            value=copy.deepcopy(self.value);value['policy']['rules'][0].update(change);self.withheld(value)
        self.value['policy']['roles'][0]['inherits']=['other'];self.withheld()
    def test_self_cycle_and_multinode_cycle_do_not_produce_partial_closure(self):
        value=copy.deepcopy(self.value);value['policy']['roles'][0]['inherits']=['observer'];self.withheld(value)
        self.value['policy']['roles'][0]['inherits']=['technician'];out=self.withheld();self.assertTrue(any(v['code']=='ROLE_CYCLE' for v in out['issues']))
    def test_assignment_and_rule_alias_slots_are_ambiguous(self):
        for field in ('assignments','rules'):
            value=copy.deepcopy(self.value);value['policy'][field].append(dict(value['policy'][field][0],id='alias'));self.withheld(value)
    def test_empty_assignments_and_rules_are_explicit_deny_all_metadata(self):
        self.value['policy']['assignments']=[];self.value['policy']['rules']=[];out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual(out['assessment']['actors'],[])
    def test_all_three_declaration_cohorts_are_required(self):
        for field in ('roles','actions','resources'):
            value=copy.deepcopy(self.value);value['policy'][field]=[];self.withheld(value)
    def test_set_normalization_preserves_policy_pin(self):
        self.value['policy']['assignments'][0]['roles']=['reviewer','technician'];before=self.run_value();self.value['policy']['assignments'][0]['roles'].reverse();self.assertEqual(before['policy_sha256'],self.run_value()['policy_sha256'])
    def test_no_implicit_wildcard_or_pattern_rule(self):
        for change in ({'resource':'*'},{'effect':True},{'role':'review*'}):
            value=copy.deepcopy(self.value);value['policy']['rules'][0].update(change);self.withheld(value)
    def test_deep_roles_use_bounded_iterative_expansion(self):
        self.value['policy'].update(roles=[dict(id='role-'+str(i),inherits=[] if i==0 else ['role-'+str(i-1)]) for i in range(40)],assignments=[],rules=[]);self.assertEqual(self.run_value()['status'],'PASS');self.value['policy']['roles']=[dict(id='role-'+str(i),inherits=[] if i==0 else ['role-'+str(i-1)]) for i in range(182)]
        with self.assertRaisesRegex(t.Rejected,'ROLE_EXPANSION_LIMIT'):self.run_value()
    def test_actor_expansion_is_bounded_separately(self):
        policy=self.value['policy'];policy['roles']=[dict(id='role-'+str(i),inherits=[] if i==0 else ['role-'+str(i-1)]) for i in range(40)];policy['rules']=[];policy['assignments']=[dict(id='assignment-'+str(i),actor='actor-'+str(i),roles=['role-39']) for i in range(410)]
        with self.assertRaisesRegex(t.Rejected,'ACTOR_EXPANSION_LIMIT'):self.run_value()
    def test_id_only_rows_have_duplicate_or_rejected_accounting(self):
        self.value['policy']['actions'].append(copy.deepcopy(self.value['policy']['actions'][0]));self.assertEqual(self.run_value()['counts']['policy_actions']['duplicate_rows'],1);self.value['policy']['actions'].append(dict(self.value['policy']['actions'][0],extra=True));self.assertEqual(self.withheld()['counts']['policy_actions']['rejected_rows'],1)
    def test_policy_header_shape_revision_and_tags_are_strict(self):
        for change in ({'revision':True},{'extra':0}):
            value=copy.deepcopy(self.value);value['policy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(value)
        self.value['policy']['roles'][0]['inherits']=['same','same'];self.withheld()
