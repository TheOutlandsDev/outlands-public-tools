import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import contracts as app
import config_core as r

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
        for key in ['baseline_sha256', 'candidate_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('raw_setting_values_emitted','settings_values_validated','runtime_compatibility_verified','adapter_bytes_verified','migration_executed','configuration_changed','installation_performed','execution_performed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['baseline', 'fields'], ['candidate', 'fields']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['baseline_sha256', 'candidate_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['baseline', 'fields'], ['candidate', 'fields']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['baseline', 'fields'], ['candidate', 'fields']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            
            if path[-1]=='fields':row=copy.deepcopy(rows[0]);row['required']=not row['required']
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['baseline', 'fields'], ['candidate', 'fields']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['baseline', 'fields'], ['candidate', 'fields']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['baseline', 'fields'], ['candidate', 'fields']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])

    def test_header_only_change_is_not_runtime_compatibility_proof(self):
        out=self.run_value();self.assertTrue(out['assessment']['header_changed']);self.assertTrue(out['assessment']['all_field_metadata_equal']);self.assertFalse(out['assessment']['breaking_change_inferred']);self.assertFalse(out['runtime_compatibility_verified'])
    def test_added_removed_and_changed_fields_are_exact_findings(self):
        self.value['candidate']['fields'].pop(0);self.value['candidate']['fields'].append(dict(self.value['baseline']['fields'][0],id='extra-key'));self.value['candidate']['fields'][-2]['required']=False
        rows={v['id']:v for v in self.review()['assessment']['fields']};self.assertEqual(rows['demo_enabled']['state'],'removed');self.assertEqual(rows['extra-key']['state'],'added');self.assertEqual(rows['queue_limit']['changed_attributes'],['required'])
    def test_all_attribute_differences_remain_metadata_only(self):
        self.value['candidate']['fields'][0].update(type='integer',required=False,default_sha256=pin(2),constraint_sha256=pin({'maximum':3}));row=self.review()['assessment']['fields'][0];self.assertEqual(row['changed_attributes'],['type','required','default_sha256','constraint_sha256']);self.assertNotIn('default_sha256',row)
    def test_same_identity_different_definition_is_not_a_diff_scope(self):
        self.value['candidate']=copy.deepcopy(self.value['baseline']);self.value['candidate']['fields'][0]['required']=False;self.withheld()
    def test_exact_same_contract_is_valid(self):
        self.value['candidate']=copy.deepcopy(self.value['baseline']);out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['assessment']['header_changed']);self.assertEqual(out['baseline_sha256'],out['candidate_sha256'])
    def test_explicit_empty_contracts_are_supported(self):
        for side in ('baseline','candidate'):self.value[side]['fields']=[]
        self.assertEqual(self.run_value()['assessment']['fields'],[])
        self.value['candidate']['fields']=[dict(id='new-key',type='boolean',required=True,default_sha256=None,constraint_sha256=pin({}))];self.assertEqual(self.review()['assessment']['fields'][0]['state'],'added')
    def test_nested_metadata_field_types_are_strict(self):
        for change in ({'required':1},{'type':'object'},{'default_sha256':'A'*64},{'constraint_sha256':None},{'id':'PRIVATE_SENTINEL'}):
            value=copy.deepcopy(self.value);value['candidate']['fields'][0].update(change);self.withheld(value)
    def test_contract_header_revision_and_unknown_fields_are_fixed_refusals(self):
        for change in ({'revision':True},{'id':'INVALID_SENTINEL'},{'extra':0}):
            value=copy.deepcopy(self.value);value['baseline'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(value)
    def test_field_limit_is_128_per_definition(self):
        for side in ('baseline','candidate'):self.value[side]['fields']=[dict(self.value[side]['fields'][0],id='field-'+str(i)) for i in range(128)]
        self.assertEqual(self.run_value()['status'],'PASS');self.value['candidate']['fields'].append(dict(self.value['candidate']['fields'][0],id='field-extra'))
        with self.assertRaises(t.Rejected):self.run_value()
    def test_constraint_and_default_fingerprints_never_infer_semantics(self):
        self.value['candidate']['fields'][0]['constraint_sha256']=pin({'minimum':0});out=self.review();self.assertEqual(out['assessment']['fields'][0]['changed_attributes'],['constraint_sha256']);self.assertFalse(out['assessment']['breaking_change_inferred'])
