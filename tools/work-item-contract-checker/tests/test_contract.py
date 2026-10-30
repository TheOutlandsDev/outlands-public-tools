import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import items as app
import worker_core as r

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
        for key in ['handlers_sha256', 'items_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('payloads_opened','handler_executed','artifact_bytes_verified','worker_contacted','ownership_enforced','jobs_executed','queue_changed','records_changed','results_committed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['handlers'], ['items']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['handlers_sha256', 'items_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['handlers'], ['items']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['handlers'], ['items']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['handlers'], ['items']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['handlers'], ['items']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['handlers'], ['items']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['handlers'], ['items']][0]).clear();self.withheld(value)

    def test_known_exact_handler_and_required_metadata(self):
        out=self.run_value();self.assertEqual(out['assessment']['items'],[dict(id='hvac-summary-job',handler_id='hvac-summary-handler',missing_metadata=[],declared_metadata_complete=True)]);self.assertFalse(out['assessment']['payload_values_validated']);self.assertFalse(out['assessment']['metadata_values_validated'])
    def test_missing_metadata_is_visible_not_invented(self):
        self.value['items'][0]['metadata']=['review-scope'];out=self.review();self.assertEqual(out['assessment']['items'][0]['missing_metadata'],['equipment-group']);self.assertIsNotNone(out['items_sha256'])
    def test_extra_declared_metadata_is_allowed_without_value_validation(self):
        self.value['items'][0]['metadata'].append('fictional-extra');self.assertEqual(self.run_value()['status'],'PASS')
    def test_handler_reference_and_all_contract_fields_are_exact(self):
        for change in ({'handler':'other'},{'handler_revision':2},{'handler_sha256':'0'*64},{'kind':'other'},{'input_contract_sha256':'0'*64},{'result_contract_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['items'][0].update(change);self.withheld(value)
    def test_selected_handler_changes_require_explicit_item_rebinding(self):
        handler=self.value['handlers'][0];handler['revision']=2;self.withheld();item=self.value['items'][0];item.update(handler_revision=2,handler_sha256=pin(handler));self.assertEqual(self.run_value()['status'],'PASS')
    def test_set_like_metadata_order_does_not_change_scope(self):
        before=self.run_value();self.value['handlers'][0]['required_metadata'].reverse();self.value['items'][0]['metadata'].reverse();out=self.run_value();self.assertEqual(before['qualified_scope_sha256'],out['qualified_scope_sha256'])
    def test_duplicate_tags_and_non_list_tags_reject_records(self):
        for side,field in [('handlers','required_metadata'),('items','metadata')]:
            for bad in (['same','same'],None,['INVALID_SENTINEL'],['tag-'+str(i) for i in range(33)]):
                value=copy.deepcopy(self.value);value[side][0][field]=bad;self.withheld(value)
    def test_empty_required_metadata_is_an_explicit_supported_contract(self):
        handler=self.value['handlers'][0];handler['required_metadata']=[];self.value['items'][0].update(metadata=[],handler_sha256=pin(handler));self.assertEqual(self.run_value()['status'],'PASS')
    def test_multiple_explicit_handlers_of_same_kind_are_not_auto_selected(self):
        self.value['handlers'].append(dict(self.value['handlers'][0],id='alternate-handler'));self.assertEqual(self.run_value()['assessment']['items'][0]['handler_id'],'hvac-summary-handler')
    def test_payload_fingerprints_are_opaque_not_content_proof(self):
        self.value['items'][0]['input_sha256']='0'*64;out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['payloads_opened']);self.assertFalse(out['artifact_bytes_verified'])
    def test_multiple_jobs_are_independent_and_complete(self):
        self.value['items'].append(dict(self.value['items'][0],id='hvac-second-job'));self.assertEqual(len(self.run_value()['assessment']['items']),2)
    def test_no_handlers_or_items_never_passes_vacuously(self):
        for side in ('handlers','items'):
            value=copy.deepcopy(self.value);value[side]=[];self.withheld(value)
