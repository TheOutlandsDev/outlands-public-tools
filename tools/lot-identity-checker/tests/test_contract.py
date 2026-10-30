from identities import check as OP

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

    def test_chain_resolves_to_canonical_motor_lot(self):
        result=run(sample());mapping={r['id']:r['canonical_lot_id'] for r in result['identities']}
        self.assertEqual(mapping['service-motor-label'],'motor-lot-a');self.assertEqual(mapping['motor-bin-label'],'motor-lot-a')
        self.assertEqual(result['canonical_totals'],[dict(item_id='blower-motor',unit='pieces',quantity=4),dict(item_id='panel-filter',unit='pieces',quantity=8)])

    def test_empty_aliases_and_zero_quantity_are_valid(self):
        value=sample();value['aliases']=[];value['lots'][0]['quantity']=0
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertEqual(len(result['identities']),2)

    def test_aliases_never_create_stock(self):
        value=sample();before=run(value)['canonical_totals']
        value['aliases']+=[dict(id='label-'+str(i),target_id='motor-lot-a') for i in range(100)]
        self.assertEqual(run(value)['canonical_totals'],before)

    def test_missing_targets_collisions_self_and_long_cycles(self):
        for target in ('missing','motor-bin-label','service-motor-label'):
            value=sample();value['aliases'][0]['target_id']=target;self.assertIsNone(run(value)['identities'])
        value=sample();value['aliases'][0]['id']='motor-lot-a';self.assertIsNone(run(value)['identities'])

    def test_conflicting_aliases_and_lots_withhold_every_identity(self):
        for key,update in [('aliases',{'target_id':'filter-lot-a'}),('lots',{'quantity':5})]:
            value=sample();value[key].append(dict(value[key][0],**update));result=run(value)
            self.assertIsNone(result['identities']);self.assertIsNone(result['lot_contract_sha256'])

    def test_exact_duplicate_snapshots_count_once(self):
        value=sample();before=run(value)
        for key in ('lots','aliases'):value[key]*=2
        after=run(value);self.assertEqual(after['identities'],before['identities']);self.assertEqual(after['canonical_totals'],before['canonical_totals'])

    def test_thousand_alias_chain_is_iterative(self):
        value=sample();value['aliases']=[dict(id='alias-'+str(i),target_id='alias-'+str(i+1) if i<999 else 'motor-lot-a') for i in range(1000)]
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertEqual(len(result['identities']),1002)

    def test_units_for_same_item_cannot_silently_mix(self):
        value=sample();value['lots'].append(dict(value['lots'][0],id='extra',unit='boxes'));self.assertIsNone(run(value)['identities'])

    def test_lot_pin_and_results_are_order_invariant(self):
        value=sample();before=run(value)
        for key in ('lots','aliases'):value[key].reverse()
        after=run(value);self.assertEqual(before['lot_contract_sha256'],after['lot_contract_sha256']);self.assertEqual(before['identities'],after['identities'])

    def test_empty_lots_or_rejected_rows_withhold(self):
        value=sample();value['lots']=[];self.assertIsNone(run(value)['identities'])
        value=sample();value['aliases'].append(None);self.assertIsNone(run(value)['identities'])
