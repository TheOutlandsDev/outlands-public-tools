from reservations import check as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t
from test_resource_core import resource,task

def sample(): return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value): return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_example_passes(self): self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_wrong_format_and_unknown_fields(self):
        for change in ({'format':'unsupported'},{'extra':0}):
            with self.assertRaises(t.Rejected): run(dict(sample(),**change))

    def test_invalid_json_and_outer_shapes(self):
        for raw in (b'{"format":1,"format":2}',b'NaN',b'1.0',b'"\\ud800"',b'null',b'[]',b'{}'):
            with self.assertRaises(t.Rejected): OP(raw)

    def test_input_pin_no_mutation_or_authorization(self):
        value=sample(); before=copy.deepcopy(value); raw=t.encode(value); result=OP(raw)
        self.assertEqual(value,before); self.assertEqual(result['input_sha256'],t.digest(raw))
        self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_json_round_trip(self):
        result=run(sample()); self.assertEqual(t.decode(t.encode(result)),result)

    def test_adjacent_bookings_do_not_overlap(self):
        row=run(sample())['summary'][0]; self.assertEqual(row['peak_units'],2); self.assertEqual(row['over_capacity_spans'],[])

    def test_exact_over_capacity_span(self):
        value=sample(); value['reservations'][1]['start']=3; result=run(value)
        self.assertEqual(result['summary'][0]['over_capacity_spans'],[dict(start=3,end=6,units=3)])
        self.assertIn('CAPACITY_EXCEEDED',[i['code'] for i in result['issues']])

    def test_simultaneous_ends_and_starts_use_net_change(self):
        value=sample(); value['reservations'][0]['units']=2
        self.assertEqual(run(value)['status'],'PASS')

    def test_sweep_against_discrete_independent_oracle(self):
        spans=[(0,2,1),(1,3,2),(2,4,1),(3,5,2)]
        for a in spans:
            for b in spans:
                value=sample(); value['reservations']=[dict(id='a',resource_id='resource-a',start=a[0],end=a[1],units=a[2]),dict(id='b',resource_id='resource-a',start=b[0],end=b[1],units=b[2])]
                result=run(value); expected=[sum(q for start,end,q in (a,b) if start<=tick<end) for tick in range(6)]
                row=result['summary'][0]; actual={tick for span in row['over_capacity_spans'] for tick in range(span['start'],span['end'])}
                self.assertEqual(row['peak_units'],max(expected)); self.assertEqual(actual,{i for i,used in enumerate(expected) if used>2})

    def test_one_booking_over_capacity(self):
        value=sample(); value['reservations']=value['reservations'][:1]; value['reservations'][0]['units']=3
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_duplicate_bookings_do_not_add_demand(self):
        value=sample(); before=run(value); value['reservations']*=2; after=run(value)
        self.assertEqual(after['summary'],before['summary']); self.assertEqual(after['counts']['reservations']['duplicate_rows'],2)

    def test_conflicts_and_bad_rows_withhold_summary(self):
        for bad in (None,dict(sample()['reservations'][0],units=2)):
            value=sample(); value['reservations'].append(bad); self.assertIsNone(run(value)['summary'])

    def test_missing_resource_and_availability_gap_withhold(self):
        value=sample(); value['reservations'][0]['resource_id']='missing'; self.assertIsNone(run(value)['summary'])
        value=sample(); value['resources'][0]['availability']=[dict(start=0,end=4),dict(start=5,end=20)]
        self.assertIsNone(run(value)['summary'])

    def test_idle_resources_and_empty_resource_cohort(self):
        value=sample(); value['reservations']=[]; self.assertEqual(run(value)['summary'][0]['peak_units'],0)
        value['resources']=[]; self.assertIsNone(run(value)['summary'])

    def test_order_invariance_and_no_schedule_actions(self):
        value=sample(); before=run(value); value['reservations'].reverse(); after=run(value)
        self.assertEqual(after['summary'],before['summary']); self.assertFalse(after['reservations_changed']); self.assertFalse(after['schedule_optimized'])
