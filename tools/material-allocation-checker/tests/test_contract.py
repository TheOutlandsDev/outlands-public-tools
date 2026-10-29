from allocations import check as OP

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

    def test_known_hvac_demand_and_remaining_inventory(self):
        result=run(sample());self.assertEqual([r['allocated'] for r in result['demands']],[4,2])
        self.assertEqual([r['unreserved'] for r in result['lots']],[4,2]);self.assertFalse(result['allocation_policy_selected'])

    def test_alias_and_canonical_reservations_share_one_supply(self):
        value=sample();value['demands'][0]['quantity']=5;value['allocations'][0]['quantity']=3
        value['allocations'].append(dict(id='second-motor-reservation',demand_id='motor-demand',lot_id='motor-lot-a',quantity=2))
        result=run(value);self.assertEqual(result['status'],'REVIEW_REQUIRED')
        motor=next(r for r in result['lots'] if r['id']=='motor-lot-a');self.assertEqual((motor['reserved'],motor['excess'],motor['unreserved']),(5,1,-1))
        self.assertEqual(next(r for r in result['demands'] if r['id']=='motor-demand')['shortage'],0)

    def test_shortage_and_excess_are_retained_diagnostics(self):
        for quantity,code in [(1,'DEMAND_SHORTAGE'),(3,'DEMAND_OVERALLOCATED')]:
            value=sample();value['allocations'][0]['quantity']=quantity;result=run(value)
            self.assertIsNotNone(result['demands']);self.assertIn(code,[i['code'] for i in result['issues']])

    def test_zero_allocations_reports_all_shortages(self):
        value=sample();value['allocations']=[];result=run(value)
        self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertEqual(sum(r['shortage'] for r in result['demands']),6)

    def test_split_demand_across_multiple_lots(self):
        value=sample();value['lots'].append(dict(value['lots'][0],id='motor-lot-b',quantity=1))
        value['allocations'][0]['quantity']=1;value['allocations'].append(dict(id='reserve-extra',lot_id='motor-lot-b',demand_id='motor-demand',quantity=1))
        self.assertEqual(run(value)['status'],'PASS')

    def test_multiple_demands_share_capacity_without_reallocation(self):
        value=sample();value['demands'].append(dict(value['demands'][0],id='second-service-job'))
        value['allocations'].append(dict(value['allocations'][0],id='second',demand_id='second-service-job'))
        self.assertEqual(run(value)['status'],'PASS')

    def test_item_unit_missing_demand_and_lot_are_structural_errors(self):
        for update in ({'lot_id':'missing'},{'demand_id':'missing'},{'lot_id':'filter-lot-a'}):
            value=sample();value['allocations'][0].update(update);self.assertIsNone(run(value)['demands'])
        value=sample();value['demands'][0]['unit']='boxes';self.assertIsNone(run(value)['lots'])

    def test_duplicate_snapshots_count_once_conflicts_withhold(self):
        value=sample();before=run(value)
        for key in ('lots','aliases','demands','allocations'):value[key]*=2
        self.assertEqual(run(value)['lots'],before['lots'])
        value['allocations'].append(dict(value['allocations'][0],quantity=1));self.assertIsNone(run(value)['lots'])

    def test_missing_demand_cohort_and_invalid_inventory(self):
        value=sample();value.update(demands=[],allocations=[]);self.assertIsNone(run(value)['demands'])
        value=sample();value['aliases'][0]['target_id']='service-motor-label';self.assertIsNone(run(value)['demands'])

    def test_distinct_allocation_ids_are_additive_claims(self):
        value=sample();value['allocations'].append(dict(value['allocations'][0],id='separate-claim'))
        result=run(value);self.assertIn('DEMAND_OVERALLOCATED',[i['code'] for i in result['issues']])

    def test_large_integer_quantities_remain_exact(self):
        value=sample();value['lots'][0]['quantity']=10**12;value['demands'][0]['quantity']=10**12;value['allocations'][0]['quantity']=10**12
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertEqual(next(r for r in result['lots'] if r['id']=='motor-lot-a')['unreserved'],0)

    def test_order_invariant_results_and_inventory_pin(self):
        value=sample();before=run(value)
        for key in ('lots','aliases','demands','allocations'):value[key].reverse()
        after=run(value)
        for key in ('lots','demands','lot_contract_sha256'):self.assertEqual(before[key],after[key])
