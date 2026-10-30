import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import scenarios as app
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
        for key in ['baseline_sha256', 'candidate_sha256', 'baseline_requests_sha256', 'candidate_requests_sha256']:self.assertIsNone(out[key])
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
        for path in [['baseline', 'roles'], ['baseline', 'actions'], ['baseline', 'resources'], ['baseline', 'assignments'], ['baseline', 'rules'], ['candidate', 'roles'], ['candidate', 'actions'], ['candidate', 'resources'], ['candidate', 'assignments'], ['candidate', 'rules'], ['baseline_requests'], ['candidate_requests']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['baseline_sha256', 'candidate_sha256', 'baseline_requests_sha256', 'candidate_requests_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['baseline', 'roles'], ['baseline', 'actions'], ['baseline', 'resources'], ['baseline', 'assignments'], ['baseline', 'rules'], ['candidate', 'roles'], ['candidate', 'actions'], ['candidate', 'resources'], ['candidate', 'assignments'], ['candidate', 'rules'], ['baseline_requests'], ['candidate_requests']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['baseline', 'roles'], ['baseline', 'actions'], ['baseline', 'resources'], ['baseline', 'assignments'], ['baseline', 'rules'], ['candidate', 'roles'], ['candidate', 'actions'], ['candidate', 'resources'], ['candidate', 'assignments'], ['candidate', 'rules'], ['baseline_requests'], ['candidate_requests']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next((k for k in row if k!='id'),None)
            if field is None:continue  # ID-only declarations have no valid conflicting payload.
            if type(row[field]) is list:row[field]=['other-declared-id']+row[field][1:]
            else:row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['baseline', 'roles'], ['baseline', 'actions'], ['baseline', 'resources'], ['baseline', 'assignments'], ['baseline', 'rules'], ['candidate', 'roles'], ['candidate', 'actions'], ['candidate', 'resources'], ['candidate', 'assignments'], ['candidate', 'rules'], ['baseline_requests'], ['candidate_requests']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['baseline', 'roles'], ['baseline', 'actions'], ['baseline', 'resources'], ['baseline', 'assignments'], ['baseline', 'rules'], ['candidate', 'roles'], ['candidate', 'actions'], ['candidate', 'resources'], ['candidate', 'assignments'], ['candidate', 'rules'], ['baseline_requests'], ['candidate_requests']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['baseline', 'roles'], ['baseline', 'actions'], ['baseline', 'resources'], ['baseline', 'assignments'], ['baseline', 'rules'], ['candidate', 'roles'], ['candidate', 'actions'], ['candidate', 'resources'], ['candidate', 'assignments'], ['candidate', 'rules'], ['baseline_requests'], ['candidate_requests']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['baseline', 'roles'], ['baseline', 'actions'], ['baseline', 'resources'], ['baseline', 'assignments'], ['baseline', 'rules'], ['candidate', 'roles'], ['candidate', 'actions'], ['candidate', 'resources'], ['candidate', 'assignments'], ['candidate', 'rules'], ['baseline_requests'], ['candidate_requests']][0]).clear();self.withheld(value)

    def test_known_header_only_change_with_equal_scenarios(self):
        out=self.run_value();self.assertTrue(out['assessment']['all_declared_scenarios_equal']);self.assertTrue(all(v['state']=='unchanged' for v in out['assessment']['requests']));self.assertFalse(out['assessment']['security_improvement_inferred'])
    def test_changed_allow_to_deny_is_review_without_security_inference(self):
        self.value['candidate']['rules'][0]['effect']='deny';row=self.review()['assessment']['requests'][0];self.assertEqual(row['state'],'decision_changed');self.assertEqual((row['baseline']['decision'],row['candidate']['decision']),('allow','deny'))
    def test_missing_candidate_requests_do_not_improve_results(self):
        self.value['candidate_requests']=[];out=self.review();self.assertEqual({v['state'] for v in out['assessment']['requests']},{'candidate_missing'});self.assertTrue(all(v['candidate'] is None for v in out['assessment']['requests']))
    def test_added_candidate_request_and_changed_revision_remain_incomparable(self):
        value=copy.deepcopy(self.value);value['candidate_requests'].append(dict(value['candidate_requests'][0],id='extra-request'));out=self.review(value);self.assertEqual(out['assessment']['requests'][0]['state'],'candidate_only')
        self.value['candidate_requests'][0]['revision']=2;row=self.review()['assessment']['requests'][0];self.assertEqual(row['state'],'request_scope_changed');self.assertIsNone(row['baseline']);self.assertIsNone(row['candidate'])
    def test_changed_actor_action_resource_or_expectation_is_not_paired(self):
        for change in ({'actor':'actor-alpha'},{'action':'view'},{'expected':None}):
            value=copy.deepcopy(self.value);value['candidate_requests'][0].update(change);self.assertEqual(self.review(value)['assessment']['requests'][0]['state'],'request_scope_changed')
    def test_equal_denial_with_failed_expectations_still_requires_review(self):
        for field in ('baseline_requests','candidate_requests'):self.value[field][0]['actor']='actor-alpha'
        row=self.review()['assessment']['requests'][0];self.assertEqual(row['state'],'unchanged');self.assertFalse(row['baseline']['expectation_met']);self.assertFalse(row['candidate']['expectation_met'])
    def test_same_policy_identity_with_changed_definition_withholds(self):
        self.value['candidate']['revision']=1;self.value['candidate']['rules'][0]['effect']='deny';self.withheld()
    def test_identical_policy_identity_and_definition_are_supported(self):
        self.value['candidate']=copy.deepcopy(self.value['baseline']);out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual(out['baseline_sha256'],out['candidate_sha256'])
    def test_unknown_candidate_action_withholds_full_comparison(self):
        self.value['candidate_requests'][0]['action']='other';self.withheld()
    def test_empty_baseline_cohort_is_not_a_comparison(self):
        self.value['baseline_requests']=[];self.withheld()
    def test_both_changed_and_unchanged_rows_are_retained(self):
        self.value['candidate']['rules'][0]['effect']='deny';out=self.review();self.assertEqual(len(out['assessment']['requests']),3);self.assertEqual([v['state'] for v in out['assessment']['requests']],['decision_changed','unchanged','unchanged'])
    def test_opposite_direction_change_is_also_review_not_ranking(self):
        self.value['baseline']['rules'][0]['effect']='deny';row=self.review()['assessment']['requests'][0];self.assertEqual((row['baseline']['decision'],row['candidate']['decision']),('deny','allow'));self.assertFalse(self.review()['assessment']['security_improvement_inferred'])
