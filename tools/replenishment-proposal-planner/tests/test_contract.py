import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import replenish as app
import stock_core as r

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()
def at(value,path):
    for key in path:value=value[key]
    return value

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        out=self.run_value(value);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256']);return out
    def withheld(self,value=None):
        out=self.review(value);self.assertIsNone(out['assessment'])
        for key in ['positions_sha256', 'policies_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('physical_stock_verified','inbound_eligibility_verified','delivery_verified','records_changed','stock_updated','purchase_order_created','reservations_changed','shipment_executed','procurement_authorized','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['positions'], ['policies']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['positions_sha256', 'policies_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['positions'], ['policies']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['positions'], ['policies']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['positions'], ['policies']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['positions'], ['policies']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['positions'], ['policies']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['positions'], ['policies']][0]).clear();self.withheld(value)

    def repin(self):self.value['policies'][0]['position_sha256']=pin(self.value['positions'][0])
    def test_known_target_difference_rounding_and_cap(self):
        row=self.run_value()['assessment']['positions'][0];self.assertEqual((row['triggered'],row['required_unrounded'],row['required_order_quantity'],row['proposed_quantity']),(True,12,12,12))
    def test_trigger_is_strictly_below_minimum(self):
        for position in (10,20):
            self.value['positions'][0]['inventory_position']=position;self.repin();row=self.run_value()['assessment']['positions'][0];self.assertFalse(row['triggered']);self.assertEqual(row['proposed_quantity'],0)
    def test_rounding_is_upward_to_multiple_and_never_clamped(self):
        self.value['positions'][0]['inventory_position']=9;self.repin();row=self.run_value()['assessment']['positions'][0];self.assertEqual((row['required_unrounded'],row['required_order_quantity']),(11,12))
        self.value['policies'][0]['maximum_proposal']=11;row=self.review()['assessment']['positions'][0];self.assertEqual(row['required_order_quantity'],12);self.assertIsNone(row['proposed_quantity'])
    def test_missing_policy_or_stale_asof_does_not_invent_zero_order(self):
        value=copy.deepcopy(self.value);value['policies']=[];self.assertIsNone(self.review(value)['assessment']['positions'][0]['proposed_quantity'])
        self.value['as_of']=21;row=self.review()['assessment']['positions'][0];self.assertIsNone(row['required_unrounded']);self.assertIsNone(row['proposed_quantity'])
    def test_negative_position_is_declared_deficit_not_physical_stock_proof(self):
        self.value['positions'][0]['inventory_position']=-2;self.repin();row=self.run_value()['assessment']['positions'][0];self.assertEqual(row['proposed_quantity'],24)
    def test_zero_cap_explicitly_blocks_triggered_proposal(self):
        self.value['policies'][0]['maximum_proposal']=0;self.assertIsNone(self.review()['assessment']['positions'][0]['proposed_quantity'])
    def test_duplicate_position_policy_slots_are_ambiguous(self):
        self.value['policies'].append(dict(self.value['policies'][0],id='alias'));self.withheld()
    def test_unknown_and_stale_position_bindings_withhold(self):
        for change in ({'position':'other'},{'position_revision':2},{'position_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['policies'][0].update(change);self.withheld(value)
    def test_policy_and_quantity_shapes_are_strict(self):
        for change in ({'minimum':21},{'order_multiple':0},{'target':True},{'maximum_proposal':-1}):
            value=copy.deepcopy(self.value);value['policies'][0].update(change);self.withheld(value)
    def test_extreme_integer_deficit_is_bounded_and_not_float_rounded(self):
        self.value['positions'][0]['inventory_position']=-10**15;self.repin();self.value['policies'][0].update(minimum=10**12,target=10**12,order_multiple=999999999999,maximum_proposal=10**12)
        row=self.review()['assessment']['positions'][0];self.assertGreaterEqual(row['required_order_quantity'],10**15+10**12);self.assertEqual(row['required_order_quantity']%999999999999,0);self.assertIsNone(row['proposed_quantity']);self.assertLess(len(t.encode(self.run_value())),8*1024*1024)
