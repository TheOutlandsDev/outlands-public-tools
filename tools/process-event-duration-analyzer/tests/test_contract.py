from durations import analyze as OP

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

    def test_known_active_hold_and_elapsed(self):
        result=run(sample()); self.assertEqual(result['durations'],[dict(id='run-a',elapsed_ticks=10,active_ticks=7,hold_ticks=3,hold_count=1)])
        self.assertEqual(result['totals']['active_ticks']+result['totals']['hold_ticks'],result['totals']['elapsed_ticks'])

    def test_finish_while_held_is_explicitly_supported(self):
        value=sample(); value['events'].pop(2); result=run(value)
        self.assertEqual(result['status'],'PASS'); self.assertEqual(result['durations'][0]['hold_ticks'],8)

    def test_missing_finish_or_start_withholds_all(self):
        for index in (0,-1):
            value=sample(); value['events'].pop(index); self.assertIsNone(run(value)['durations'])

    def test_nested_hold_and_resume_while_active_are_invalid(self):
        for change in ({'kind':'hold','at':5},{'kind':'resume','at':2}):
            value=sample(); value['events'][1].update(change); self.assertIsNone(run(value)['durations'])

    def test_distinct_event_ids_at_same_time_are_ambiguous(self):
        value=sample(); value['events'].append(dict(value['events'][1],id='another-hold'))
        result=run(value); self.assertIsNone(result['durations']); self.assertIn('EVENT_TIME_TIE',[i['code'] for i in result['issues']])

    def test_duplicate_event_snapshots_do_not_add_duration(self):
        value=sample(); before=run(value); value['events']*=2
        result=run(value); self.assertEqual(result['durations'],before['durations']); self.assertEqual(result['counts']['events']['duplicate_rows'],4)

    def test_conflicting_or_malformed_event_withholds_all(self):
        for bad in (None,dict(sample()['events'][0],at=1)):
            value=sample(); value['events'].append(bad); self.assertIsNone(run(value)['durations'])

    def test_event_run_binding_and_boundaries(self):
        for change in ({'run_id':'missing'},{'at':11},{'at':1}):
            value=sample(); value['events'][0].update(change); self.assertIsNone(run(value)['durations'])

    def test_chronological_order_is_independent_of_input_order(self):
        value=sample(); before=run(value); value['events'].reverse(); self.assertEqual(run(value)['durations'],before['durations'])

    def test_parallel_run_totals_are_not_makespan(self):
        value=sample(); value['runs'].append(dict(id='run-b',start=0,end=10))
        value['events'] += [dict(id='start-b',run_id='run-b',at=0,kind='start'),dict(id='finish-b',run_id='run-b',at=10,kind='finish')]
        result=run(value); self.assertEqual(result['totals']['elapsed_ticks'],20); self.assertFalse(result['wall_clock_makespan_calculated'])

    def test_empty_cohort_and_unknown_event_kind(self):
        value=sample(); value['events'][0]['kind']='infer'; self.assertIsNone(run(value)['durations'])
        value.update(runs=[],events=[]); self.assertIsNone(run(value)['durations'])
