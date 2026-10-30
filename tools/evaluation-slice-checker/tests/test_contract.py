import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import slices as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None,key='coverage'):
        result=self.run_value(value);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);return result
    def withheld(self,value=None):
        result=self.review(value);self.assertIsNone(result['coverage']);return result
    def test_fictional_positive_and_authority_boundaries(self):
        result=self.run_value();self.assertEqual(result['status'],'PASS')
        for key in ('artifact_bytes_verified','label_truth_verified','holdout_independence_verified','training_performed','dataset_export_performed','content_privacy_verified','execution_authorized','target_changes_performed'):
            self.assertIs(result[key],False)
    def test_outer_contract_format_unknown_fields_and_duplicate_keys(self):
        for v in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(v)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_order_changes_do_not_change_qualified_pins(self):
        expected=self.run_value()
        for key in ['cohort', 'slices', 'memberships']:self.value[key].reverse()
        actual=self.run_value()
        for key in ['cohort_sha256', 'taxonomy_sha256', 'policy_sha256']:self.assertEqual(actual[key],expected[key])
    def test_identical_snapshots_count_once(self):
        for key in ['cohort', 'slices', 'memberships']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));result=self.run_value(v)
            self.assertEqual(result['status'],'PASS');counts=result['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')),counts['input_rows'])
    def test_rejected_rows_withhold_assessment_and_omit_values(self):
        for key in ['cohort', 'slices', 'memberships']:
            v=copy.deepcopy(self.value);v[key].append({'id':'SYNTHETIC_SENTINEL'});result=self.withheld(v)
            self.assertEqual(result['counts'][key]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))
    def test_list_bounds_are_fixed_refusals(self):
        for key in ['cohort', 'slices', 'memberships']:
            for rows in (None,{},[{}]*1001):
                v=copy.deepcopy(self.value);v[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(v)
    def test_taxonomy_rejects_duplicate_unknown_and_boolean_revision(self):
        for change in ({'labels':['filter','filter']},{'labels':[]},{'revision':True},{'revision':0},{'extra':0}):
            v=copy.deepcopy(self.value);v['taxonomy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)

    def test_complete_coverage_has_explicit_denominators_and_pin(self):
        r=self.run_value();a=r['coverage'];self.assertEqual(a['covered_fraction'],dict(numerator=2,denominator=2,exact_fraction='1/1'))
        self.assertEqual(r['cohort_sha256'],pin(self.value['cohort']));self.assertTrue(a['eligible_for_manual_comparison_review'])
    def test_missing_cases_and_slice_minimum_fail_but_retain_counts(self):
        self.value['memberships'].pop();a=self.review()['coverage'];self.assertEqual(a['covered_fraction']['exact_fraction'],'1/2')
        self.assertEqual(a['unassigned_cases'],['case-delta']);self.assertEqual(a['failed_criteria'],['CASES_UNASSIGNED','MINIMUM_COVERAGE_NOT_MET','SLICE_MINIMUM_NOT_MET'])
    def test_equal_fraction_threshold_passes_exactly(self):
        self.value['memberships'].pop();self.value['slices'][1]['minimum_cases']=0
        self.value['policy'].update(require_all_cases_assigned=False,minimum_covered_fraction='0.5');self.assertEqual(self.run_value()['status'],'PASS')
        self.value['policy']['minimum_covered_fraction']='0.500001';self.assertIn('MINIMUM_COVERAGE_NOT_MET',self.review()['coverage']['failed_criteria'])
    def test_no_memberships_has_zero_coverage_not_zero_denominator(self):
        self.value['memberships']=[];a=self.review()['coverage'];self.assertEqual(a['covered_fraction']['exact_fraction'],'0/1');self.assertEqual(a['cohort_cases'],2)
    def test_explicit_zero_minima_allow_empty_slices_without_implying_quality(self):
        self.value['memberships']=[];self.value['policy'].update(minimum_covered_fraction='0',require_all_cases_assigned=False)
        for r in self.value['slices']:r['minimum_cases']=0
        self.assertEqual(self.run_value()['status'],'PASS')
    def test_overlap_refused_for_exclusive_membership_but_allowed_when_declared(self):
        self.value['memberships'].append(dict(id='member-cross',case='case-charlie',slice='noise-jobs'))
        self.assertIn('EXCLUSIVE_MEMBERSHIP_OVERLAP',self.review()['coverage']['failed_criteria'])
        self.value['policy']['membership_mode']='overlap';a=self.run_value()['coverage'];self.assertTrue(a['eligible_for_manual_comparison_review']);self.assertEqual(a['unique_memberships'],3);self.assertEqual(a['covered_cases'],2)
    def test_semantic_duplicate_membership_does_not_inflate_counts(self):
        self.value['memberships'].append(dict(self.value['memberships'][0],id='extra-member'));a=self.review()['coverage']
        self.assertEqual(a['unique_memberships'],2);self.assertEqual(a['slices'][0]['cases'],1);self.assertEqual(len(a['repeated_memberships']),1)
    def test_duplicate_identity_and_semantic_duplicate_are_distinct(self):
        self.value['memberships'].append(copy.deepcopy(self.value['memberships'][0]));r=self.run_value()
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['counts']['memberships']['duplicate_rows'],1);self.assertEqual(r['coverage']['repeated_memberships'],[])
    def test_per_label_counts_include_zero_labels(self):
        a=self.run_value()['coverage'];self.assertEqual(a['slices'][0]['label_counts'],dict(filter=1,noise=0))
    def test_unknown_case_or_slice_withholds_all_qualified_pins(self):
        for change in ({'case':'missing'},{'slice':'missing'}):
            v=copy.deepcopy(self.value);v['memberships'][0].update(change);r=self.withheld(v)
            for key in ('cohort_sha256','taxonomy_sha256','policy_sha256'):self.assertIsNone(r[key])
    def test_empty_cohort_or_slice_list_withholds(self):
        for key in ('cohort','slices'):
            v=copy.deepcopy(self.value);v[key]=[];self.withheld(v)
    def test_conflicting_cohort_label_never_produces_a_partial_pin(self):
        self.value['cohort'].append(dict(self.value['cohort'][0],expected_label='noise'));r=self.withheld();self.assertIsNone(r['cohort_sha256'])
    def test_policy_normalizes_decimal_string_pins(self):
        expected=self.run_value()['policy_sha256'];self.value['policy']['minimum_covered_fraction']='1.000000';self.assertEqual(self.run_value()['policy_sha256'],expected)
    def test_policy_types_and_unit_interval_are_refused(self):
        for change in ({'membership_mode':[]},{'membership_mode':'auto'},{'require_all_cases_assigned':1},{'minimum_covered_fraction':'1.1'},{'minimum_covered_fraction':'0.0000001'},{'extra':0}):
            v=copy.deepcopy(self.value);v['policy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)
    def test_slice_minimum_rejects_bool_negative_and_overbound(self):
        for minimum in (True,-1,1001,'1'):
            v=copy.deepcopy(self.value);v['slices'][0]['minimum_cases']=minimum;self.withheld(v)
