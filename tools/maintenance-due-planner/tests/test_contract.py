from due import check as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t
import service_core as c

def sample():return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value):return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_hvac_example_passes(self):self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_wrong_format_and_unknown_fields(self):
        for change in ({'format':'unsupported'},{'extra':0}):
            with self.assertRaises(t.Rejected):run(dict(sample(),**change))

    def test_strict_json_and_outer_shapes(self):
        for raw in (b'null',b'[]',b'{}',b'NaN',b'1.0',b'"\\ud800"',b'{"format":1,"format":2}'):
            with self.assertRaises(t.Rejected):OP(raw)

    def test_input_pin_no_mutation_or_authorization(self):
        value=sample();before=copy.deepcopy(value);raw=t.encode(value);result=OP(raw)
        self.assertEqual(value,before);self.assertEqual(result['input_sha256'],t.digest(raw));self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_changes_performed'])

    def test_report_round_trip(self):
        result=run(sample());self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_not_due_thresholds_and_distances(self):
        row=run(sample())['assessments'][0]
        self.assertEqual((row['due_state'],row['next_due_at'],row['due_usage'],row['remaining_time'],row['remaining_usage']),('not_due',14,15,6,3))

    def test_equality_means_due_for_each_criterion(self):
        for change in ({'time_interval':6},{'usage_interval':7}):
            value=sample();value['plans'][0].update(change);result=run(value)
            self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertEqual(result['assessments'][0]['due_state'],'due')

    def test_stale_usage_is_unknown_even_if_stored_value_exceeds_threshold(self):
        value=sample();value.update(as_of=10,maximum_meter_age=1);value['plans'][0].update(time_interval=None,usage_interval=1)
        row=run(value)['assessments'][0];self.assertEqual(row['due_state'],'unknown');self.assertIsNone(row['due_by_usage']);self.assertLess(row['remaining_usage'],0)

    def test_time_due_survives_stale_usage_uncertainty(self):
        value=sample();value['as_of']=14;row=run(value)['assessments'][0]
        self.assertEqual(row['due_state'],'due');self.assertTrue(row['due_by_time']);self.assertFalse(row['meter_fresh'])

    def test_time_only_plan_requires_no_meter(self):
        value=sample();value['meters']=[];value['plans'][0].update(usage_interval=None,meter_id=None,meter_unit=None,usage_origin=None,last_service_usage=None)
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertIsNone(result['assessments'][0]['due_by_usage'])

    def test_usage_only_plan_and_zero_freshness_window(self):
        value=sample();value['plans'][0]['time_interval']=None;value['maximum_meter_age']=0
        self.assertEqual(run(value)['status'],'PASS');value['as_of']=9;self.assertEqual(run(value)['assessments'][0]['due_state'],'unknown')

    def test_future_or_pre_service_snapshot_is_not_silently_used(self):
        for change in ({'observed_at':9},{'observed_at':1},{'total_usage':4}):
            value=sample();value['meters'][0].update(change);self.assertIsNone(run(value)['assessments'])
        value=sample();value['plans'][0]['last_service_at']=9;self.assertIsNone(run(value)['assessments'])

    def test_unit_origin_and_missing_meter_withhold_all(self):
        for change in ({'meter_unit':'other'},{'usage_origin':'other'},{'meter_id':'missing'}):
            value=sample();value['plans'][0].update(change);self.assertIsNone(run(value)['assessments'])

    def test_invalid_interval_unused_fields_and_empty_cohort(self):
        for change in ({'time_interval':0},{'usage_interval':True},{'time_interval':None,'usage_interval':None},{'usage_interval':None}):
            value=sample();value['plans'][0].update(change);self.assertIsNone(run(value)['assessments'])
        value=sample();value['plans']=[];self.assertIsNone(run(value)['assessments'])

    def test_duplicates_and_conflicts_do_not_choose_latest(self):
        value=sample();before=run(value)
        for key in ('meters','plans'):value[key]*=2
        self.assertEqual(run(value)['assessments'],before['assessments'])
        value['plans'].append(dict(value['plans'][0],usage_interval=11));self.assertIsNone(run(value)['assessments'])

    def test_declared_source_pin_is_not_byte_verification(self):
        value=sample();value['meters'][0]['source_sha256']='0'*64;result=run(value)
        self.assertEqual(result['status'],'PASS');self.assertFalse(result['meter_sources_verified']);self.assertFalse(result['schedule_created']);self.assertFalse(result['live_clock_used'])
