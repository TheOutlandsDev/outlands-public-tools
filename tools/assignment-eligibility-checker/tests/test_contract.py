from assignments import check as OP

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

    def test_known_eligible_proposals(self):
        result=run(sample()); self.assertTrue(all(r['eligible_under_declarations'] for r in result['assessments']))
        self.assertFalse(result['qualifications_certified']); self.assertFalse(result['work_assigned'])

    def test_multiple_ineligibility_reasons_remain_visible(self):
        value=sample(); value['tasks'][0].update(units=3,end=21,required_capabilities=['missing'])
        result=run(value); row=result['assessments'][0]
        self.assertEqual(row['reasons'],['MISSING_CAPABILITY','UNITS_EXCEED_CAPACITY','OUTSIDE_AVAILABILITY'])
        self.assertEqual(row['missing_capabilities_count'],1); self.assertFalse(row['execution_authorized'])

    def test_individual_eligibility_does_not_check_combined_capacity(self):
        value=sample()
        for row in value['tasks']: row.update(start=0,end=6,units=2)
        result=run(value); self.assertEqual(result['status'],'PASS'); self.assertFalse(result['combined_reservation_capacity_checked'])

    def test_missing_assignment_withholds_assessments(self):
        value=sample(); value['assignments'].pop(); self.assertIsNone(run(value)['assessments'])

    def test_unknown_task_or_resource(self):
        for key in ('task_id','resource_id'):
            value=sample(); value['assignments'][0][key]='missing'; self.assertIsNone(run(value)['assessments'])

    def test_multiple_proposals_for_one_task_are_not_selected(self):
        value=sample(); value['assignments'].append(dict(value['assignments'][0],id='another'))
        self.assertIn('MULTIPLE_PROPOSALS_FOR_TASK',[i['code'] for i in run(value)['issues']]); self.assertIsNone(run(value)['assessments'])

    def test_duplicate_snapshots_count_once(self):
        value=sample(); before=run(value)
        for key in ('resources','tasks','assignments'): value[key]*=2
        self.assertEqual(run(value)['assessments'],before['assessments'])

    def test_conflicting_task_or_resource_withholds_all(self):
        for key,changed in [('tasks',dict(task(),units=2)),('resources',dict(resource(),capacity=3))]:
            value=sample(); value[key].append(changed); self.assertIsNone(run(value)['assessments'])

    def test_adjacent_availability_is_contiguous(self):
        value=sample(); value['resources'][0]['availability']=[dict(start=0,end=5),dict(start=5,end=20)]
        self.assertEqual(run(value)['status'],'PASS')

    def test_empty_availability_is_ineligible(self):
        value=sample(); value['resources'][0]['availability']=[]; result=run(value)
        self.assertTrue(all('OUTSIDE_AVAILABILITY' in r['reasons'] for r in result['assessments']))

    def test_empty_tasks_and_order_invariance(self):
        value=sample(); before=run(value); value['tasks'].reverse(); value['assignments'].reverse()
        self.assertEqual(run(value)['assessments'],before['assessments'])
        value.update(tasks=[],assignments=[]); self.assertIsNone(run(value)['assessments'])
