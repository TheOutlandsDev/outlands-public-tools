from measurements import check as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t

def sample():return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value):return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_hvac_example_passes(self):self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_wrong_format_and_unknown_fields(self):
        for update in ({'format':'unsupported'},{'extra':0}):
            with self.assertRaises(t.Rejected):run(dict(sample(),**update))

    def test_strict_json_and_outer_shapes(self):
        for raw in (b'null',b'[]',b'{}',b'NaN',b'1.0',b'"\\ud800"',b'{"format":1,"format":2}'):
            with self.assertRaises(t.Rejected):OP(raw)

    def test_raw_input_pin_no_mutation_or_authorization(self):
        value=sample();before=copy.deepcopy(value);raw=t.encode(value);result=OP(raw)
        self.assertEqual(value,before);self.assertEqual(result['input_sha256'],t.digest(raw));self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_changes_performed'])

    def test_report_round_trip(self):
        result=run(sample());self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_readings_retain_exact_normalized_values(self):
        result=run(sample());self.assertTrue(all(r['within_declared_limits'] for r in result['assessments']))
        self.assertEqual(next(r for r in result['assessments'] if r['id']=='air-handler-alpha-flow-check')['value'],'12.5')
        self.assertFalse(result['measurement_accuracy_verified']);self.assertFalse(result['equipment_suitability_verified'])

    def test_each_inclusive_and_exclusive_endpoint(self):
        for boundary,flag,code in [('10','minimum_inclusive','BELOW_MINIMUM'),('20','maximum_inclusive','ABOVE_MAXIMUM')]:
            value=sample();value['measurements'][0]['value']=boundary
            self.assertEqual(run(value)['status'],'PASS');value['rules'][0][flag]=False
            result=run(value);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertIn(code,next(r for r in result['assessments'] if r['id']=='air-handler-alpha-flow-check')['reasons'])

    def test_closed_point_interval(self):
        value=sample();value['rules'][0].update(minimum='12.5',maximum='12.5');value['measurements']=value['measurements'][:1]
        self.assertEqual(run(value)['status'],'PASS');value['measurements'][0]['value']='12.500001';self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_fractional_readings_never_use_binary_float(self):
        value=sample();value['rules'][0].update(minimum='0.1',maximum='0.100002');value['measurements']=value['measurements'][:1];value['measurements'][0]['value']='0.100001'
        self.assertEqual(run(value)['status'],'PASS')

    def test_outside_readings_retain_complete_assessments(self):
        value=sample();value['measurements'][0]['value']='9.999999';result=run(value)
        self.assertEqual(len(result['assessments']),4);self.assertEqual(next(r for r in result['assessments'] if r['id']=='air-handler-alpha-flow-check')['reasons'],['BELOW_MINIMUM'])

    def test_missing_revision_or_unit_withholds_all(self):
        for update in ({'rule_id':'missing'},{'rule_revision':2},{'unit':'other'}):
            value=sample();value['measurements'][0].update(update);self.assertIsNone(run(value)['assessments'])

    def test_multiple_selected_measurements_are_not_latest_selection(self):
        value=sample();value['measurements'].append(dict(value['measurements'][0],id='another-reading'))
        self.assertIsNone(run(value)['assessments'])

    def test_duplicate_normalized_snapshots_count_once(self):
        value=sample();before=run(value);value['measurements'].append(dict(value['measurements'][0],value='12.500000'))
        value['rules'].append(dict(value['rules'][0],minimum='10.0'))
        after=run(value);self.assertEqual(after['assessments'],before['assessments']);self.assertEqual(after['rule_contract_sha256'],before['rule_contract_sha256'])

    def test_conflicting_rule_or_reading_withholds_cohort(self):
        for key,change in [('rules',{'revision':2}),('measurements',{'value':'13'})]:
            value=sample();value[key].append(dict(value[key][0],**change));self.assertIsNone(run(value)['assessments'])

    def test_empty_cohorts_or_rejected_reading_withhold(self):
        for key in ('rules','measurements'):
            value=sample();value[key]=[];self.assertIsNone(run(value)['assessments'])
        value=sample();value['measurements'][0]['value']=12.5
        with self.assertRaises(t.Rejected):run(value)

    def test_input_order_does_not_change_assessments(self):
        value=sample();before=run(value)
        for key in ('rules','measurements'):value[key].reverse()
        after=run(value);self.assertEqual(before['assessments'],after['assessments']);self.assertEqual(before['rule_contract_sha256'],after['rule_contract_sha256'])
