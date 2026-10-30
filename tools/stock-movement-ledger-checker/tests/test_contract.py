import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import movements as app
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
        for key in ['stocks_sha256', 'movements_sha256']:self.assertIsNone(out[key])
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
        for path in [['stocks'], ['movements']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['stocks_sha256', 'movements_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['stocks'], ['movements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['stocks'], ['movements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['stocks'], ['movements']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['stocks'], ['movements']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['stocks'], ['movements']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['stocks'], ['movements']][0]).clear();self.withheld(value)

    def test_known_opening_receipt_issue_and_closing(self):
        row=self.run_value()['assessment']['stocks'][0];self.assertEqual(row['closing_quantity'],10);self.assertEqual([v['delta'] for v in row['history']],[4,-6]);self.assertEqual([v['balance_after'] for v in row['history']],[16,10])
    def test_signed_adjustment_and_zero_refusal(self):
        self.value['movements'][1].update(kind='adjustment',quantity=-6);self.assertEqual(self.run_value()['assessment']['stocks'][0]['closing_quantity'],10)
        self.value['movements'][1]['quantity']=0;self.withheld()
    def test_negative_intermediate_balance_is_not_erased_by_later_receipt(self):
        first=self.value['movements'][0];first.update(kind='issue',quantity=20);self.value['movements'][1].update(kind='receipt',quantity=30);row=self.review()['assessment']['stocks'][0];self.assertEqual(row['closing_quantity'],22);self.assertEqual(row['history'][0]['balance_after'],-8)
    def test_future_movement_is_visible_and_not_applied(self):
        self.value['as_of']=5;row=self.review()['assessment']['stocks'][0];self.assertEqual(row['closing_quantity'],16);self.assertFalse(row['history'][1]['applied']);self.assertIsNone(row['history'][1]['balance_after'])
    def test_future_opening_never_becomes_zero_or_current_stock(self):
        self.value['as_of']=0;self.value['stocks'][0]['at']=1
        for row in self.value['movements']:row['stock_sha256']=pin(self.value['stocks'][0])
        row=self.review()['assessment']['stocks'][0];self.assertIsNone(row['closing_quantity']);self.assertTrue(all(not v['applied'] for v in row['history']))
    def test_order_ties_use_ordinal_but_gaps_and_time_reversal_withhold(self):
        self.value['movements'][1]['at']=5;self.assertEqual(self.run_value()['status'],'PASS')
        for change in ({'ordinal':3},{'at':4}):
            value=copy.deepcopy(self.value);value['movements'][1].update(change);self.withheld(value)
    def test_movement_before_opening_or_ambiguous_slot_withholds(self):
        self.value['stocks'][0]['at']=6
        for row in self.value['movements']:row['stock_sha256']=pin(self.value['stocks'][0])
        self.withheld();self.value['stocks'][0]['at']=0
        for row in self.value['movements']:row['stock_sha256']=pin(self.value['stocks'][0])
        self.value['movements'].append(dict(self.value['movements'][0],id='alias'));self.withheld()
    def test_unknown_or_stale_stock_binding_withholds(self):
        for change in ({'stock':'other'},{'stock_revision':2},{'stock_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['movements'][0].update(change);self.withheld(value)
    def test_idle_ledger_preserves_opening_quantity(self):
        self.value['movements']=[];self.assertEqual(self.run_value()['assessment']['stocks'][0]['closing_quantity'],12)
    def test_quantity_types_and_asof_are_strict(self):
        for change in ({'quantity':True},{'quantity':-1},{'kind':'transfer'}):
            value=copy.deepcopy(self.value);value['movements'][0].update(change);self.withheld(value)
        self.value['as_of']=True
        with self.assertRaises(t.Rejected):self.run_value()
