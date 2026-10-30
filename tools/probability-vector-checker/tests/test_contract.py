import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import vectors as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment']);return r
    def test_positive_and_truth_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('probability_interpretation_verified','label_truth_verified','cohort_independence_verified','calibration_established','model_fitted','model_updated','inference_performed','artifact_bytes_verified','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_format_unknown_fields_and_duplicate_keys_refuse(self):
        for v in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(v)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_preserves_normalized_pins(self):
        before=self.run_value()
        for path in [['cases']]:
            rows=self.value
            for key in path:rows=rows[key]
            rows.reverse()
        after=self.run_value()
        for key in ['cases_sha256', 'qualified_cases_sha256', 'taxonomy_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_snapshots_count_once_with_complete_accounting(self):
        for path in [['cases']]:
            value=copy.deepcopy(self.value);rows=value
            for key in path:rows=rows[key]
            rows.append(copy.deepcopy(rows[0]));r=self.run_value(value);self.assertEqual(r['status'],'PASS')
            side=path[-1] if len(path)==1 else path[0]+'_points';counts=r['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_rejected_rows_withhold_qualified_result_and_omit_values(self):
        for path in [['cases']]:
            value=copy.deepcopy(self.value);rows=value
            for key in path:rows=rows[key]
            rows.append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_refuse(self):
        for path in [['cases']]:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);selected=value
                for key in path[:-1]:selected=selected[key]
                selected[path[-1]]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_complete_vectors_and_independent_snapshot_pins(self):
        r=self.run_value();self.assertEqual(r['assessment']['valid_cases'],4);self.assertEqual(r['qualified_cases_sha256'],pin(self.value['cases']))
        self.assertTrue(all(x['probability_sum']['exact_fraction']=='1/1' for x in r['assessment']['cases']))
    def test_bad_sum_retains_exact_total_and_does_not_renormalize(self):
        self.value['cases'][0]['probabilities'][0]['value']='0.7';r=self.review();a=r['assessment']['cases'][0]
        self.assertEqual(a['probability_sum']['exact_fraction'],'19/20');self.assertIsNone(a['vector_sha256']);self.assertIsNone(r['qualified_cases_sha256']);self.assertIsNotNone(r['cases_sha256']);self.assertFalse(r['probabilities_renormalized'])
    def test_explicit_missing_vector_is_not_zero_probability(self):
        self.value['cases'][0]['probabilities']=None;a=self.review()['assessment']['cases'][0]
        self.assertEqual(a['missing_labels'],['no-service','service-needed']);self.assertIsNone(a['probability_sum'])
    def test_absent_label_and_explicit_null_value_are_both_visible(self):
        self.value['cases'][0]['probabilities'].pop();a=self.review()['assessment']['cases'][0];self.assertEqual(a['missing_labels'],['service-needed'])
        self.value['cases'][0]['probabilities'][0]['value']=None;a=self.review()['assessment']['cases'][0];self.assertEqual(len(a['missing_labels']),2)
    def test_empty_vector_retains_missing_class_diagnostics(self):
        self.value['cases'][0]['probabilities']=[];self.assertEqual(len(self.review()['assessment']['cases'][0]['missing_labels']),2)
    def test_unknown_or_repeated_labels_are_ambiguous_rows(self):
        for entry in ({'label':'other','value':'0'},{'label':'no-service','value':'0.75'}):
            value=copy.deepcopy(self.value);value['cases'][0]['probabilities'].append(entry);self.withheld(value)
    def test_sum_has_no_rounding_tolerance(self):
        self.value['taxonomy']['labels']=['explore','quest','rest'];a=self.value['cases'][0];a['probabilities']=[dict(label=k,value='0.333333') for k in self.value['taxonomy']['labels']];self.value['cases']=[a]
        self.assertEqual(self.review()['assessment']['cases'][0]['probability_sum']['exact_fraction'],'999999/1000000')
    def test_trailing_zeros_and_negative_zero_normalize_snapshot_identity(self):
        a=self.value['cases'][0];a['probabilities']=[dict(label='no-service',value='-0.000'),dict(label='service-needed',value='1.000000')]
        b=copy.deepcopy(a);b['probabilities'].reverse()
        for r in b['probabilities']:r['value']='0' if r['label']=='no-service' else '1'
        self.value['cases']=[a,b];r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(r['counts']['cases']['duplicate_rows'],1)
    def test_bad_values_and_case_revisions_are_rejected_rows(self):
        for bad in (True,'NaN','0.0000001','1.000001','-0.1','1/2'):
            value=copy.deepcopy(self.value);value['cases'][0]['probabilities'][0]['value']=bad;self.withheld(value)
        for change in ({'revision':True},{'model_revision':0},{'model':'UPPER'},{'extra':0}):
            value=copy.deepcopy(self.value);value['cases'][0].update(change);self.withheld(value)
    def test_conflicting_case_revisions_never_select_latest(self):
        self.value['cases'].append(dict(self.value['cases'][0],revision=2));r=self.withheld();self.assertEqual(r['counts']['cases']['conflict_rows'],2);self.assertIsNone(r['cases_sha256'])
    def test_empty_case_cohort_withholds(self):
        self.value['cases']=[];self.withheld()
    def test_taxonomy_schema_refuses_duplicate_labels_or_boolean_revision(self):
        for change in ({'labels':[]},{'labels':['same','same']},{'revision':True}):
            value=copy.deepcopy(self.value);value['taxonomy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(value)
    def test_fictional_game_three_class_vector(self):
        value=json.loads((Path(__file__).resolve().parents[1]/'examples/game-vectors.json').read_text(encoding='utf-8'))
        self.assertEqual(self.run_value(value)['assessment']['cases'][0]['probability_sum']['exact_fraction'],'1/1')
