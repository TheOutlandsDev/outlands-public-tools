from bom import check as OP

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

    def test_unknown_fields_and_format(self):
        for update in ({'extra':0},{'format':'unsupported'}):
            with self.assertRaises(t.Rejected):run(dict(sample(),**update))

    def test_strict_json_and_outer_shapes(self):
        for raw in (b'null',b'[]',b'{}',b'NaN',b'1.0',b'"\\ud800"',b'{"format":1,"format":2}'):
            with self.assertRaises(t.Rejected):OP(raw)

    def test_raw_input_pin_no_mutation_or_authorization(self):
        value=sample();before=copy.deepcopy(value);raw=t.encode(value);result=OP(raw)
        self.assertEqual(value,before);self.assertEqual(result['input_sha256'],t.digest(raw))
        self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_changes_performed']);self.assertFalse(result['declarations_independently_verified'])

    def test_report_round_trip(self):
        result=run(sample());self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_multilevel_hvac_requirements(self):
        result=run(sample());q={r['component_id']:r['quantity'] for r in result['requirements']}
        self.assertEqual(q,{'air-handler-kit':2,'blower-module':2,'blower-motor':2,'panel-filter':4})
        self.assertEqual({r['component_id'] for r in result['requirements'] if r['is_leaf']},{'blower-motor','panel-filter'})

    def test_shared_child_paths_accumulate_once_per_edge(self):
        value=dict(format=sample()['format'],components=[dict(id=i,unit='pieces') for i in ('a','b','c','d')],
            links=[dict(id='ab',parent_id='a',component_id='b',quantity=2),dict(id='ac',parent_id='a',component_id='c',quantity=3),dict(id='bd',parent_id='b',component_id='d',quantity=5),dict(id='cd',parent_id='c',component_id='d',quantity=7)],orders=[dict(id='order',component_id='a',quantity=4)])
        self.assertEqual({r['component_id']:r['quantity'] for r in run(value)['requirements']}['d'],124)
        value['orders'].append(dict(id='extra-motor-order',component_id='d',quantity=2))
        self.assertEqual({r['component_id']:r['quantity'] for r in run(value)['requirements']}['d'],126)

    def test_direct_leaf_order_and_unused_component(self):
        value=sample();value['orders']=[dict(id='replacement',component_id='panel-filter',quantity=3)]
        self.assertEqual(run(value)['requirements'],[dict(component_id='panel-filter',quantity=3,unit='pieces',is_leaf=True)])

    def test_unreachable_cycle_is_still_invalid(self):
        value=sample();value['components'].append(dict(id='unused',unit='pieces'));value['links'].append(dict(id='self',parent_id='unused',component_id='unused',quantity=1))
        result=run(value);self.assertIsNone(result['requirements']);self.assertIn('COMPONENT_CYCLE',[i['code'] for i in result['issues']])

    def test_parallel_distinct_edges_are_not_summed(self):
        value=sample();value['links'].append(dict(value['links'][0],id='different'))
        self.assertIsNone(run(value)['requirements'])

    def test_duplicate_snapshots_never_inflate_requirements(self):
        value=sample();before=run(value)['requirements']
        for key in ('components','links','orders'):value[key]*=2
        self.assertEqual(run(value)['requirements'],before)

    def test_conflicts_or_missing_references_withhold_all(self):
        for update in ({'component_id':'missing'},{'quantity':True}):
            value=sample();value['links'][0].update(update);self.assertIsNone(run(value)['requirements'])
        value=sample();value['orders'].append(dict(value['orders'][0],quantity=3));self.assertIsNone(run(value)['requirements'])

    def test_empty_required_cohorts(self):
        for key in ('components','orders'):
            value=sample();value[key]=[];self.assertIsNone(run(value)['requirements'])

    def test_derived_quantity_limit_refuses_without_partial_results(self):
        value=sample();value['orders'][0]['quantity']=10**9
        for row in value['links']:row['quantity']=10**6
        with self.assertRaisesRegex(t.Rejected,'REQUIREMENT_LIMIT'):run(value)

    def test_independent_tree_requirement_oracle(self):
        for root_quantity in (1,3,9):
            for motor_count in (1,2,7):
                value=sample();value['orders'][0]['quantity']=root_quantity;value['links'][1]['quantity']=motor_count
                q={r['component_id']:r['quantity'] for r in run(value)['requirements']}
                self.assertEqual(q['blower-motor'],sum(motor_count for _ in range(root_quantity)))
                self.assertEqual(q['panel-filter'],sum(2 for _ in range(root_quantity)))

    def test_input_order_does_not_change_requirements(self):
        value=sample();before=run(value)
        for key in ('components','links','orders'):value[key].reverse()
        after=run(value);self.assertEqual(before['requirements'],after['requirements']);self.assertEqual(before['topological_order'],after['topological_order'])
