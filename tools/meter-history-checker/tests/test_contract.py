from meters import check as OP

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

    def test_known_usage_spans_reset_without_counting_new_baseline(self):
        result=run(sample());self.assertEqual(result['snapshots'],[dict(id='blower-meter',unit='demo-cycles',usage_origin='demo-origin-a',observed_at=8,total_usage=12,display_reading=2,reset_count=1,sample_count=2)])

    def test_explicit_nonzero_reset_baseline_is_not_consumption(self):
        value=sample();value['events'][1]['reading']=100;value['events'][2]['reading']=103
        result=run(value);self.assertEqual(result['snapshots'][0]['total_usage'],13);self.assertEqual(result['snapshots'][0]['display_reading'],103)

    def test_no_events_is_a_baseline_not_fresh_device_evidence(self):
        value=sample();value['events']=[];result=run(value)
        self.assertEqual((result['snapshots'][0]['total_usage'],result['snapshots'][0]['observed_at']),(0,0));self.assertFalse(result['physical_counter_verified'])

    def test_unexplained_decrease_or_invalid_old_reset_reading_withholds_all(self):
        for index,field,new in [(0,'reading',9),(1,'previous_reading',14),(2,'reading',-1)]:
            value=sample();value['events'][index][field]=new;self.assertIsNone(run(value)['snapshots'])

    def test_previous_reading_required_only_for_reset(self):
        for index,new in [(0,10),(1,None),(1,True)]:
            value=sample();value['events'][index]['previous_reading']=new;self.assertIsNone(run(value)['snapshots'])

    def test_ties_and_events_not_after_initial_are_ambiguous(self):
        for at in (0,2):
            value=sample();value['events'][1]['at']=at;self.assertIsNone(run(value)['snapshots'])

    def test_orphan_event_and_empty_meter_cohort_withhold(self):
        value=sample();value['events'][0]['meter_id']='missing';self.assertIsNone(run(value)['snapshots'])
        value=sample();value['meters']=[];self.assertIsNone(run(value)['snapshots'])

    def test_duplicate_snapshots_do_not_add_usage(self):
        value=sample();before=run(value)
        for key in ('meters','events'):value[key]*=2
        self.assertEqual(run(value)['snapshots'],before['snapshots'])

    def test_conflicting_event_or_meter_withholds_complete_cohort(self):
        for key,change in [('events',{'reading':16}),('meters',{'initial_reading':11})]:
            value=sample();value[key].append(dict(value[key][0],**change));self.assertIsNone(run(value)['snapshots'])

    def test_row_order_is_not_event_order(self):
        value=sample();before=run(value);value['events'].reverse();self.assertEqual(run(value)['snapshots'],before['snapshots'])

    def test_exact_large_reset_accumulation(self):
        value=sample();value['meters'][0]['initial_reading']=0;value['events']=[]
        for i in range(20):value['events'].append(dict(id='reset-'+str(i),meter_id='blower-meter',at=i+1,kind='reset',reading=0,previous_reading=10**12))
        self.assertEqual(run(value)['snapshots'][0]['total_usage'],20*10**12)

    def test_independent_segment_sum_oracle(self):
        for old,new,after in [(20,0,2),(22,7,12),(15,100,100)]:
            value=sample();value['events'][1].update(previous_reading=old,reading=new);value['events'][2]['reading']=after
            self.assertEqual(run(value)['snapshots'][0]['total_usage'],sum([15-10,old-15,after-new]))
