import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import position as app
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
        for key in ['stocks_sha256', 'inbound_sha256', 'reservations_sha256']:self.assertIsNone(out[key])
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
        for path in [['stocks'], ['inbound'], ['reservations']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['stocks_sha256', 'inbound_sha256', 'reservations_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['stocks'], ['inbound'], ['reservations']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['stocks'], ['inbound'], ['reservations']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['stocks'], ['inbound'], ['reservations']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['stocks'], ['inbound'], ['reservations']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['stocks'], ['inbound'], ['reservations']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['stocks'], ['inbound'], ['reservations']][0]).clear();self.withheld(value)

    def test_known_on_hand_plus_inbound_minus_reserved(self):
        row=self.run_value()['assessment']['stocks'][0];self.assertEqual((row['on_hand'],row['eligible_inbound'],row['reserved_demand'],row['inventory_position']),(10,2,4,8))
    def test_explicit_horizon_boundaries_and_exclusions(self):
        for at in (20,30):
            value=copy.deepcopy(self.value);value['inbound'][0]['due_at']=at;self.assertEqual(self.run_value(value)['assessment']['stocks'][0]['inventory_position'],8)
        self.value['inbound'][0]['due_at']=31;out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual(out['assessment']['stocks'][0]['inventory_position'],6);self.assertEqual(out['assessment']['inbound'][0]['reason'],'beyond_horizon')
    def test_pending_cancelled_and_released_claims_are_visible_exclusions(self):
        for state in ('pending','cancelled'):
            value=copy.deepcopy(self.value);value['inbound'][0]['state']=state;out=self.run_value(value);self.assertEqual(out['status'],'PASS');self.assertFalse(out['assessment']['inbound'][0]['included'])
        self.value['reservations'][0]['state']='released';self.assertEqual(self.run_value()['assessment']['stocks'][0]['inventory_position'],12)
    def test_overdue_inbound_is_not_silently_counted(self):
        self.value['inbound'][0]['due_at']=19;out=self.review();self.assertFalse(out['assessment']['inbound'][0]['included']);self.assertEqual(out['assessment']['stocks'][0]['inventory_position'],6)
    def test_stale_or_future_stock_snapshot_has_unknown_position(self):
        for at in (19,21):
            value=copy.deepcopy(self.value);value['stocks'][0]['at']=at
            for side in ('inbound','reservations'):value[side][0]['stock_sha256']=pin(value['stocks'][0])
            self.assertIsNone(self.review(value)['assessment']['stocks'][0]['inventory_position'])
    def test_negative_position_is_visible_and_requires_review(self):
        self.value['reservations'][0]['quantity']=20;self.assertEqual(self.review()['assessment']['stocks'][0]['inventory_position'],-8)
    def test_alias_source_claims_cannot_double_count(self):
        for side in ('inbound','reservations'):
            value=copy.deepcopy(self.value);value[side].append(dict(value[side][0],id='alias'));self.withheld(value)
    def test_exact_item_unit_and_stock_pins_are_required(self):
        for side in ('inbound','reservations'):
            for change in ({'item':'other'},{'unit':'other'},{'stock':'other'},{'stock_sha256':'0'*64}):
                value=copy.deepcopy(self.value);value[side][0].update(change);self.withheld(value)
    def test_empty_claims_are_an_explicit_position_snapshot(self):
        self.value['inbound']=[];self.value['reservations']=[];self.assertEqual(self.run_value()['assessment']['stocks'][0]['inventory_position'],10)
    def test_horizon_and_quantity_types_refuse(self):
        value=copy.deepcopy(self.value);value['horizon']=19
        with self.assertRaises(t.Rejected):self.run_value(value)
        self.value['inbound'][0]['quantity']=True;self.withheld()
