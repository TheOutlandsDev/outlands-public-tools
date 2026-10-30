import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import scenarios as app
import form_core as r

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
        for key in ['baseline_forms_sha256', 'baseline_flows_sha256', 'baseline_submissions_sha256', 'baseline_histories_sha256', 'candidate_forms_sha256', 'candidate_flows_sha256', 'candidate_submissions_sha256', 'candidate_histories_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('browser_started','dom_inspected','scripts_executed','network_requests_performed','authentication_performed','records_changed','raw_values_emitted','content_privacy_verified','execution_authorized','target_changes_performed','accessibility_verified','whole_ui_compatibility_verified'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['baseline_forms'], ['baseline_flows'], ['baseline_submissions'], ['baseline_histories'], ['candidate_forms'], ['candidate_flows'], ['candidate_submissions'], ['candidate_histories']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['baseline_forms_sha256', 'baseline_flows_sha256', 'baseline_submissions_sha256', 'baseline_histories_sha256', 'candidate_forms_sha256', 'candidate_flows_sha256', 'candidate_submissions_sha256', 'candidate_histories_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['baseline_forms'], ['baseline_flows'], ['baseline_submissions'], ['baseline_histories'], ['candidate_forms'], ['candidate_flows'], ['candidate_submissions'], ['candidate_histories']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['baseline_forms'], ['baseline_flows'], ['baseline_submissions'], ['baseline_histories'], ['candidate_forms'], ['candidate_flows'], ['candidate_submissions'], ['candidate_histories']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['baseline_forms'], ['baseline_flows'], ['baseline_submissions'], ['baseline_histories'], ['candidate_forms'], ['candidate_flows'], ['candidate_submissions'], ['candidate_histories']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['baseline_forms'], ['baseline_flows'], ['baseline_submissions'], ['baseline_histories'], ['candidate_forms'], ['candidate_flows'], ['candidate_submissions'], ['candidate_histories']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['baseline_forms'], ['baseline_flows'], ['baseline_submissions'], ['baseline_histories'], ['candidate_forms'], ['candidate_flows'], ['candidate_submissions'], ['candidate_histories']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['baseline_forms'], ['baseline_flows'], ['baseline_submissions'], ['baseline_histories'], ['candidate_forms'], ['candidate_flows'], ['candidate_submissions'], ['candidate_histories']][0]).clear();self.withheld(value)


    def repin(self,value=None,prefix=''):
        value=self.value if value is None else value
        def name(key):return prefix+'_'+key if prefix else key
        forms={v['id']:r.form(v)[1] for v in value[name('forms')]};flows={v['id']:v for v in value.get(name('flows'),[])};subs={v['id']:v for v in value.get(name('submissions'),[])}
        for row in [*flows.values(),*subs.values()]:
            if row['form'] in forms:row.update(form_revision=forms[row['form']]['revision'],form_sha256=pin(forms[row['form']]))
        for row in value.get(name('histories'),[]):
            if row['flow'] in flows:row.update(flow_revision=flows[row['flow']]['revision'],flow_sha256=pin(r.flow(flows[row['flow']])[1]))
            for item in row['events']:
                if item['submission'] in subs:item.update(submission_revision=subs[item['submission']]['revision'],submission_sha256=pin(subs[item['submission']]))

    def test_version_specific_pins_allow_unchanged_observations(self):
        out=self.run_value();self.assertTrue(out['assessment']['all_declared_outcomes_equal']);self.assertNotEqual(out['baseline_forms_sha256'],out['candidate_forms_sha256']);self.assertEqual(out['assessment']['histories'][0]['state'],'unchanged')
    def test_changed_priority_rule_changes_observed_outcome(self):
        self.value['candidate_forms'][0]['fields'][2]['maximum']=1;self.repin(prefix='candidate');out=self.review();self.assertEqual(out['assessment']['submissions'][0]['state'],'observed_outcomes_changed');self.assertEqual(out['assessment']['histories'][0]['state'],'observed_outcomes_changed')
    def test_boolean_integer_payload_change_is_not_identical_observation(self):
        self.value['candidate_submissions'][0]['values']['urgent']=0;self.repin(prefix='candidate');row=self.review()['assessment']['histories'][0];self.assertEqual(row['state'],'submission_scope_changed');self.assertIsNone(row['candidate'])
    def test_missing_and_added_histories_are_explicit_incomparable_cases(self):
        value=copy.deepcopy(self.value);value['candidate_histories']=[];row=self.review(value)['assessment']['histories'][0];self.assertEqual(row['state'],'candidate_missing');self.assertIsNone(row['baseline']);self.value['candidate_histories'].append(dict(self.value['candidate_histories'][0],id='added-history'));self.assertEqual(self.review()['assessment']['histories'][0]['state'],'candidate_only')
    def test_changed_ordered_interaction_is_not_a_comparison_case(self):
        self.value['candidate_histories'][0]['events'][1]['action']='revise';row=self.review()['assessment']['histories'][0];self.assertEqual(row['state'],'interaction_scope_changed');self.assertIsNone(row['baseline'])
    def test_same_form_identity_cannot_hide_changed_rules(self):
        self.value['candidate_forms'][0]['revision']=1;self.value['candidate_forms'][0]['fields'][2]['maximum']=1;self.repin(prefix='candidate');self.withheld()
    def test_same_flow_identity_cannot_hide_changed_transition_rules(self):
        self.value['candidate_flows'][0]['revision']=1;self.repin(prefix='candidate');self.withheld()
    def test_identical_definitions_under_identical_identity_are_allowed(self):
        for kind in ('forms','flows','submissions','histories'):self.value['candidate_'+kind]=copy.deepcopy(self.value['baseline_'+kind])
        self.assertEqual(self.run_value()['status'],'PASS')
    def test_equal_expected_negative_histories_can_match_without_validity_claim(self):
        for side in ('baseline','candidate'):
            self.value[side+'_histories'][0]['events']=[];self.value[side+'_histories'][0]['expected_valid']=False
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['assessment']['histories'][0]['baseline']['valid']);self.assertFalse(out['whole_ui_compatibility_verified'])
    def test_equal_wrong_expectations_are_still_review_required(self):
        for side in ('baseline','candidate'):self.value[side+'_histories'][0]['events']=[]
        out=self.review();self.assertEqual(out['assessment']['histories'][0]['state'],'unchanged');self.assertFalse(out['assessment']['histories'][0]['candidate']['expectation_met'])
    def test_stale_candidate_reference_withholds_entire_comparison(self):
        self.value['candidate_submissions'][0]['form_sha256']='0'*64;self.withheld()
    def test_empty_baseline_never_passes_vacuously(self):
        self.value['baseline_histories']=[];self.withheld()
    def test_missing_submission_cannot_leave_history_assessed(self):
        self.value['candidate_submissions']=[];self.withheld()
    def test_changed_unused_observation_is_not_silently_ignored(self):
        for side in ('baseline','candidate'):self.value[side+'_submissions'].append(dict(self.value[side+'_submissions'][0],id='unused-submission'))
        self.value['candidate_submissions'][1]['values']['priority']=3;self.repin(prefix='candidate');out=self.review();self.assertEqual(out['assessment']['histories'][0]['state'],'submission_scope_changed')
    def test_visibility_change_is_observed_even_when_both_submissions_valid(self):
        for side in ('baseline','candidate'):
            self.value[side+'_forms'][0]['fields'][3]['visible_when']=[dict(field='equipment',equals='air-handler' if side=='baseline' else 'heat-pump')];self.repin(prefix=side)
        out=self.review();row=out['assessment']['submissions'][0];self.assertTrue(row['baseline']['valid']);self.assertTrue(row['candidate']['valid']);self.assertEqual(row['state'],'observed_outcomes_changed')
    def test_changed_expectation_is_changed_observation_scope(self):
        self.value['candidate_submissions'][0]['expected_valid']=None;self.repin(prefix='candidate');self.assertEqual(self.review()['assessment']['submissions'][0]['state'],'submission_scope_changed')
