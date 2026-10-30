import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import shipments as app
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
        for key in ['orders_sha256', 'shipments_sha256', 'lines_sha256', 'receipts_sha256']:self.assertIsNone(out[key])
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
        for path in [['orders'], ['shipments'], ['lines'], ['receipts']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['orders_sha256', 'shipments_sha256', 'lines_sha256', 'receipts_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['orders'], ['shipments'], ['lines'], ['receipts']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['orders'], ['shipments'], ['lines'], ['receipts']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['orders'], ['shipments'], ['lines'], ['receipts']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['orders'], ['shipments'], ['lines'], ['receipts']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['orders'], ['shipments'], ['lines'], ['receipts']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['orders'], ['shipments'], ['lines'], ['receipts']][0]).clear();self.withheld(value)

    def repin_receipt(self):self.value['receipts'][0]['line_sha256']=pin(self.value['lines'][0])
    def test_known_full_dispatch_and_declared_receipt_coverage(self):
        row=self.run_value()['assessment']['orders'][0];self.assertEqual((row['required_quantity'],row['dispatched_quantity'],row['declared_received_quantity'],row['unshipped'],row['receipt_shortage']),(4,4,4,0,0))
    def test_partial_receipt_and_excess_remain_distinct(self):
        self.value['receipts'][0]['quantity']=3;out=self.review();self.assertEqual(out['assessment']['lines'][0]['failed_criteria'],['RECEIPT_SHORTFALL']);self.assertEqual(out['assessment']['orders'][0]['receipt_shortage'],1)
        self.value['receipts'][0]['quantity']=5;out=self.review();self.assertEqual(out['assessment']['lines'][0]['declared_unreceived'],-1);self.assertEqual(out['assessment']['orders'][0]['receipt_excess'],1)
    def test_missing_receipt_never_proves_non_delivery_or_zero_actual_receipt(self):
        self.value['receipts']=[];row=self.review()['assessment']['lines'][0];self.assertIsNone(row['receipt_id']);self.assertEqual(row['failed_criteria'],['RECEIPT_MISSING'])
    def test_empty_shipment_and_claim_cohorts_leave_order_unfulfilled(self):
        self.value['shipments']=[];self.value['lines']=[];self.value['receipts']=[];row=self.review()['assessment']['orders'][0];self.assertEqual(row['unshipped'],4);self.assertEqual(row['receipt_shortage'],4)
    def test_empty_declared_shipment_requires_content(self):
        self.value['lines']=[];self.value['receipts']=[];out=self.review();self.assertTrue(any(row['code']=='SHIPMENT_CONTENT_MISSING' for row in out['issues']))
    def test_split_order_across_two_shipments_is_additive(self):
        self.value['lines'][0]['quantity']=2;self.value['receipts'][0]['quantity']=2;self.repin_receipt();ship=dict(self.value['shipments'][0],id='second-shipment');self.value['shipments'].append(ship)
        line=dict(self.value['lines'][0],id='second-line',shipment=ship['id'],shipment_sha256=pin(ship));self.value['lines'].append(line);self.value['receipts'].append(dict(id='second-receipt',line=line['id'],line_sha256=pin(line),quantity=2));self.assertEqual(self.run_value()['status'],'PASS')
    def test_same_shipment_order_slot_and_receipt_aliases_are_ambiguous(self):
        for side in ('lines','receipts'):
            value=copy.deepcopy(self.value);value[side].append(dict(value[side][0],id='alias'));self.withheld(value)
    def test_overshipment_does_not_become_satisfied_order_by_clamping(self):
        self.value['lines'][0]['quantity']=5;self.value['receipts'][0]['quantity']=5;self.repin_receipt();row=self.review()['assessment']['orders'][0];self.assertEqual(row['over_shipped'],1);self.assertEqual(row['receipt_excess'],1)
    def test_full_order_shipment_line_and_item_unit_bindings_are_exact(self):
        for change in ({'order':'other'},{'order_revision':2},{'order_sha256':'0'*64},{'shipment':'other'},{'shipment_revision':2},{'shipment_sha256':'0'*64},{'item':'other'},{'unit':'other'}):
            value=copy.deepcopy(self.value);value['lines'][0].update(change);self.withheld(value)
        self.value['receipts'][0]['line_sha256']='0'*64;self.withheld()
    def test_orphan_receipt_and_bad_quantity_are_rejected(self):
        value=copy.deepcopy(self.value);value['receipts'][0]['line']='unknown';self.withheld(value)
        for side in ('orders','lines','receipts'):
            value=copy.deepcopy(self.value);value[side][0]['quantity']=True;self.withheld(value)
