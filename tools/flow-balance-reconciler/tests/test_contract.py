from flows import reconcile as OP

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

    def test_known_bucket_and_global_conservation(self):
        result=run(sample()); a,b=result['balances']
        self.assertEqual((a['computed_closing'],b['computed_closing']),(12,3))
        self.assertEqual(result['totals'],dict(opening=12,external_incoming=5,external_outgoing=1,internal_transferred_units=3,adjustment=-1,computed_closing=15,declared_closing=15))

    def test_matching_global_totals_do_not_hide_bucket_mismatches(self):
        value=sample(); value['balances'][0]['closing']=11; value['balances'][1]['closing']=4
        result=run(value); self.assertEqual(result['totals']['declared_closing'],result['totals']['computed_closing'])
        self.assertEqual(len([i for i in result['issues'] if i['code']=='FLOW_BALANCE_MISMATCH']),2)

    def test_duplicate_snapshots_do_not_double_count(self):
        value=sample(); before=run(value)
        for key in ('balances','movements','adjustments'): value[key]*=2
        after=run(value); self.assertEqual(after['totals'],before['totals']); self.assertEqual(after['balances'],before['balances'])

    def test_conflicting_or_rejected_record_withholds_balances(self):
        for bad in (None,dict(sample()['movements'][0],quantity=4)):
            value=sample(); value['movements'].append(bad); self.assertIsNone(run(value)['balances'])

    def test_unknown_bucket_and_cross_kind_event_id_alias(self):
        value=sample(); value['movements'][0]['to_bucket']='missing'; self.assertIsNone(run(value)['totals'])
        value=sample(); value['adjustments'][0]['id']=value['movements'][0]['id']; result=run(value)
        self.assertIsNone(result['balances']); self.assertIn('EVENT_ID_ALIAS',[i['code'] for i in result['issues']])

    def test_invalid_endpoints_units_and_boolean_quantities(self):
        for change in ({'from_bucket':None,'to_bucket':None},{'to_bucket':'bucket-a'},{'quantity':0},{'quantity':True}):
            value=sample(); value['movements'][0].update(change); self.assertIsNone(run(value)['totals'])
        value=sample(); value['unit']='UPPER'
        with self.assertRaises(t.Rejected): run(value)

    def test_negative_computed_closing_is_visible(self):
        value=sample(); value['adjustments'][0]['delta']=-100
        result=run(value); self.assertIsNotNone(result['balances']); self.assertIn('NEGATIVE_COMPUTED_CLOSING',[i['code'] for i in result['issues']])

    def test_no_event_balanced_window_is_valid(self):
        value=sample(); value.update(movements=[],adjustments=[])
        for row in value['balances']: row['closing']=row['opening']
        self.assertEqual(run(value)['status'],'PASS')

    def test_large_exact_aggregate_and_zero_adjustment_refusal(self):
        value=sample(); value.update(movements=[],adjustments=[])
        for row in value['balances']: row.update(opening=10**12,closing=10**12)
        self.assertEqual(run(value)['totals']['computed_closing'],2*10**12)
        value['adjustments']=[dict(id='zero',bucket='bucket-a',delta=0)]; self.assertIsNone(run(value)['totals'])

    def test_net_balance_does_not_prove_intermediate_stock(self):
        value=sample(); value.update(balances=[dict(id='bucket-a',opening=0,closing=0)],adjustments=[],movements=[
            dict(id='out',from_bucket='bucket-a',to_bucket=None,quantity=1),dict(id='in',from_bucket=None,to_bucket='bucket-a',quantity=1)])
        result=run(value); self.assertEqual(result['status'],'PASS'); self.assertFalse(result['intermediate_balances_checked'])

    def test_order_invariance_and_empty_cohort(self):
        value=sample(); before=run(value)
        for key in ('balances','movements','adjustments'): value[key].reverse()
        self.assertEqual(run(value)['balances'],before['balances'])
        value.update(balances=[],movements=[],adjustments=[]); self.assertIsNone(run(value)['balances'])
