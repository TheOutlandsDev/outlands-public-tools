import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import regressions as app
import test_core as r

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
        for key in ['baseline_cases_sha256', 'baseline_expectations_sha256', 'baseline_results_sha256', 'baseline_run_sha256', 'candidate_cases_sha256', 'candidate_expectations_sha256', 'candidate_results_sha256', 'candidate_run_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('artifact_bytes_verified','test_execution_verified','tests_executed','evidence_authenticity_verified','approval_authority_verified','records_changed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['baseline', 'cases'], ['baseline', 'expectations'], ['baseline', 'results'], ['candidate', 'cases'], ['candidate', 'expectations'], ['candidate', 'results']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['baseline_cases_sha256', 'baseline_expectations_sha256', 'baseline_results_sha256', 'baseline_run_sha256', 'candidate_cases_sha256', 'candidate_expectations_sha256', 'candidate_results_sha256', 'candidate_run_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['baseline', 'cases'], ['baseline', 'expectations'], ['baseline', 'results'], ['candidate', 'cases'], ['candidate', 'expectations'], ['candidate', 'results']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['baseline', 'cases'], ['baseline', 'expectations'], ['baseline', 'results'], ['candidate', 'cases'], ['candidate', 'expectations'], ['candidate', 'results']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['baseline', 'cases'], ['baseline', 'expectations'], ['baseline', 'results'], ['candidate', 'cases'], ['candidate', 'expectations'], ['candidate', 'results']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['baseline', 'cases'], ['baseline', 'expectations'], ['baseline', 'results'], ['candidate', 'cases'], ['candidate', 'expectations'], ['candidate', 'results']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['baseline', 'cases'], ['baseline', 'expectations'], ['baseline', 'results'], ['candidate', 'cases'], ['candidate', 'expectations'], ['candidate', 'results']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['baseline', 'cases'], ['baseline', 'expectations'], ['baseline', 'results'], ['candidate', 'cases'], ['candidate', 'expectations'], ['candidate', 'results']][0]).clear();self.withheld(value)

    def change_contract(self,b):
        case=b['cases'][0];case['revision']=2;exp=b['expectations'][0];exp.update(case_revision=2,case_sha256=pin(case));row=b['results'][0];row.update(case_revision=2,case_sha256=pin(case));self.rebind(b)
    def rebind(self,b):
        b['run']['cases_sha256']=pin(sorted(b['cases'],key=lambda row:row['id']));b['run']['expectations_sha256']=pin(sorted(b['expectations'],key=lambda row:row['id']))
        for row in b['results']:row['run_sha256']=pin(b['run'])
    def state(self,out):return out['assessment']['cases'][0]['state']
    def test_known_unchanged_match_with_different_subject_pins(self):
        self.assertNotEqual(self.value['baseline']['run']['subject_sha256'],self.value['candidate']['run']['subject_sha256']);self.assertEqual(self.state(self.run_value()),'unchanged_match')
    def test_regression_and_improvement_are_directional(self):
        self.value['candidate']['results'][0]['observed_exit']=1;self.assertEqual(self.state(self.review()),'regression')
        self.value['baseline'],self.value['candidate']=self.value['candidate'],self.value['baseline'];out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual(self.state(out),'improvement')
    def test_persisting_mismatch_stays_review_required(self):
        for side in ('baseline','candidate'):self.value[side]['results'][0]['observed_exit']=1
        self.assertEqual(self.state(self.review()),'persisting_mismatch')
    def test_missing_and_incomplete_results_never_become_regressions_or_passes(self):
        self.value['candidate']['results']=[];self.assertEqual(self.state(self.review()),'incomplete_comparison')
    def test_changed_case_revision_is_incomparable(self):
        self.change_contract(self.value['candidate']);self.assertEqual(self.state(self.review()),'incomparable_contract')
    def test_added_and_removed_cases_remain_visible(self):
        b=self.value['candidate'];case=dict(b['cases'][0],id='hvac-extra');b['cases'].append(case);exp=dict(b['expectations'][0],id='extra-expectation',case=case['id'],case_sha256=pin(case));b['expectations'].append(exp);b['results'].append(dict(b['results'][0],id='extra-result',case=case['id'],case_sha256=pin(case)));self.rebind(b)
        out=self.review();self.assertEqual(out['assessment']['classification_counts']['added'],1)
        self.value['baseline'],self.value['candidate']=self.value['candidate'],self.value['baseline'];self.assertEqual(self.review()['assessment']['classification_counts']['removed'],1)
    def test_reused_run_identity_is_not_independent_comparison(self):
        self.value['candidate']['run']['id']=self.value['baseline']['run']['id'];self.value['candidate']['results'][0]['run']=self.value['candidate']['run']['id'];self.rebind(self.value['candidate']);self.withheld()
    def test_stale_result_on_either_side_withholds_every_comparison(self):
        for side in ('baseline','candidate'):
            value=copy.deepcopy(self.value);value[side]['results'][0]['case_sha256']='0'*64;self.withheld(value)
    def test_changed_expectation_contract_is_incomparable_not_improvement(self):
        b=self.value['candidate'];exp=b['expectations'][0];exp['expected_exit']=1;case=b['cases'][0];case['expectation_sha256']=r.expectation_pin(exp);exp['case_sha256']=pin(case);b['results'][0].update(case_sha256=pin(case),observed_exit=1);self.rebind(b);self.assertEqual(self.state(self.review()),'incomparable_contract')
    def test_nonobject_bundle_is_fixed_refusal(self):
        self.value['candidate']=[]
        with self.assertRaises(t.Rejected):self.run_value()
