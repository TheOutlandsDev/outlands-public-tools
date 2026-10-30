import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import maps as app

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
        for path in [['before', 'points'], ['after', 'points']]:
            rows=self.value
            for key in path:rows=rows[key]
            rows.reverse()
        after=self.run_value()
        for key in ['before_sha256', 'after_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_snapshots_count_once_with_complete_accounting(self):
        for path in [['before', 'points'], ['after', 'points']]:
            value=copy.deepcopy(self.value);rows=value
            for key in path:rows=rows[key]
            rows.append(copy.deepcopy(rows[0]));r=self.run_value(value);self.assertEqual(r['status'],'PASS')
            side=path[-1] if len(path)==1 else path[0]+'_points';counts=r['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_rejected_rows_withhold_qualified_result_and_omit_values(self):
        for path in [['before', 'points'], ['after', 'points']]:
            value=copy.deepcopy(self.value);rows=value
            for key in path:rows=rows[key]
            rows.append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_refuse(self):
        for path in [['before', 'points'], ['after', 'points']]:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);selected=value
                for key in path[:-1]:selected=selected[key]
                selected[path[-1]]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_unchanged_map_has_equal_pins_and_no_application(self):
        r=self.run_value();self.assertFalse(r['assessment']['changed']);self.assertEqual(r['before_sha256'],r['after_sha256']);self.assertFalse(r['mapping_applied'])
    def test_valid_change_requires_manual_review_and_retains_pins(self):
        self.value['after']['revision']=2;self.value['after']['points'][1]['output_probability']='0.6';r=self.review()
        self.assertTrue(r['assessment']['changed']);self.assertEqual(r['assessment']['points_changed'],['point-middle']);self.assertNotEqual(r['before_sha256'],r['after_sha256'])
    def test_content_change_without_revision_withholds_comparison(self):
        self.value['after']['points'][1]['output_probability']='0.6';r=self.withheld();self.assertIsNone(r['before_sha256']);self.assertTrue(r['map_assessments']['after']['nondecreasing'])
    def test_version_only_increase_passes_without_calibration_claim(self):
        self.value['after']['revision']=2;r=self.run_value();self.assertTrue(r['assessment']['version_only']);self.assertFalse(r['calibration_established'])
    def test_map_or_model_revision_regression_withholds(self):
        value=copy.deepcopy(self.value);value['before']['revision']=2;self.withheld(value)
        self.value['before']['model_revision']=2;self.value['after']['revision']=3;self.withheld()
    def test_model_revision_change_requires_mapping_revision_too(self):
        self.value['after']['model_revision']=2;self.withheld();self.value['after']['revision']=2;r=self.review();self.assertTrue(r['assessment']['model_revision_changed'])
    def test_identity_or_label_direction_changes_are_not_implicit_rebindings(self):
        for change in ({'id':'other-map'},{'model':'other-model'},{'positive_label':'no-service','negative_label':'service-needed'}):
            value=copy.deepcopy(self.value);value['after'].update(change);value['after']['revision']=2;self.withheld(value)
    def test_input_domain_must_include_zero_and_one(self):
        for index,x in ((0,'0.1'),(2,'0.9')):
            value=copy.deepcopy(self.value);value['after']['points'][index]['input_probability']=x;r=self.withheld(value);self.assertFalse(r['map_assessments']['after']['domain_complete'])
    def test_decreasing_outputs_are_rejected_as_a_map_contract(self):
        self.value['after']['points'][1]['output_probability']='1';self.value['after']['points'][2]['output_probability']='0.9';r=self.withheld();self.assertFalse(r['map_assessments']['after']['nondecreasing'])
    def test_flat_outputs_and_nonextreme_endpoint_outputs_are_allowed(self):
        for mapping in (self.value['before'],self.value['after']):
            for point in mapping['points']:point['output_probability']='0.5'
        self.assertEqual(self.run_value()['status'],'PASS')
        for mapping in (self.value['before'],self.value['after']):
            for point,y in zip(mapping['points'],['0.1','0.5','0.9']):point['output_probability']=y
        self.assertEqual(self.run_value()['status'],'PASS')
    def test_distinct_ids_at_one_input_are_ambiguous_even_with_equal_output(self):
        self.value['after']['points'].append(dict(self.value['after']['points'][1],id='point-other'));r=self.withheld();self.assertTrue(any(i['code']=='INPUT_COORDINATE_AMBIGUOUS' for i in r['issues']))
    def test_conflicting_point_identity_withholds_every_copy(self):
        self.value['after']['points'].append(dict(self.value['after']['points'][1],output_probability='0.6'));r=self.withheld();self.assertEqual(r['counts']['after_points']['conflict_rows'],2)
    def test_point_identity_change_is_a_content_change_even_if_curve_same(self):
        self.value['after']['points'][1]['id']='point-renamed';self.value['after']['revision']=2;a=self.review()['assessment'];self.assertEqual(a['points_added'],['point-renamed']);self.assertEqual(a['points_removed'],['point-middle'])
    def test_insufficient_points_and_bad_decimal_types_withhold(self):
        value=copy.deepcopy(self.value);value['after']['points']=value['after']['points'][:1];self.withheld(value)
        for y in (True,'1.1','0.0000001'):
            value=copy.deepcopy(self.value);value['after']['points'][0]['output_probability']=y;self.withheld(value)
    def test_normalized_point_order_and_decimal_spelling_preserve_pin(self):
        before=self.run_value()['after_sha256'];self.value['after']['points'][0]['input_probability']='-0.0';self.value['after']['points'][1]['output_probability']='0.500000';self.value['after']['points'].reverse();self.assertEqual(self.run_value()['after_sha256'],before)
    def test_full_64_point_bound_is_supported(self):
        points=[dict(id='point-'+str(i).zfill(2),input_probability='0.'+str(i).zfill(2),output_probability='0.'+str(i).zfill(2)) for i in range(63)]+[dict(id='point-end',input_probability='1',output_probability='1')]
        for side in ('before','after'):self.value[side]['points']=copy.deepcopy(points)
        self.assertEqual(self.run_value()['status'],'PASS');self.assertEqual(self.run_value()['map_assessments']['after']['points_count'],64)
    def test_header_schema_types_and_point_limit_are_fixed_refusals(self):
        for change in ({'revision':True},{'model_revision':0},{'positive_label':'no-service'},{'extra':0}):
            value=copy.deepcopy(self.value);value['after'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(value)
        self.value['after']['points']=[{}]*65
        with self.assertRaises(t.Rejected):self.run_value()
