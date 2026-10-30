import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import overlays as app
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
        for key in ['contract_sha256', 'layers_sha256', 'changes_sha256']:self.assertIsNone(out[key])
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
        for path in [['contract', 'fields'], ['layers'], ['changes']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['contract_sha256', 'layers_sha256', 'changes_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['contract', 'fields'], ['layers'], ['changes']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['contract', 'fields'], ['layers'], ['changes']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            
            if path[-1]=='fields':row=copy.deepcopy(rows[0]);row['required']=not row['required']
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['contract', 'fields'], ['layers'], ['changes']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['contract', 'fields'], ['layers'], ['changes']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['contract', 'fields'], ['layers'], ['changes']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])

    def repin(self):
        for row in self.value['layers']:row['contract_sha256']=pin(self.value['contract'])
        for row in self.value['changes']:row['layer_sha256']=pin(next(v for v in self.value['layers'] if v['id']==row['layer']))
    def test_known_explicit_override_and_effective_pin(self):
        out=self.run_value();self.assertEqual([v['key'] for v in out['assessment']['effective_fields']],['demo_enabled','display_mode','queue_limit'])
        final=[dict(key='demo_enabled',value_type='boolean',value_sha256=pin(True)),dict(key='display_mode',value_type='string',value_sha256=pin('quiet')),dict(key='queue_limit',value_type='integer',value_sha256=pin(8))]
        self.assertEqual(out['effective_configuration_sha256'],pin(dict(contract_sha256=pin(self.value['contract']),present=final)));self.assertFalse(out['assessment']['defaults_inserted'])
    def test_denied_override_never_emits_effective_configuration(self):
        self.value['changes'][-1]['allow_override']=False;out=self.review();self.assertIsNone(out['assessment']['effective_fields']);self.assertIsNone(out['effective_configuration_sha256']);self.assertTrue(any(v['failed_criterion']=='OVERRIDE_DENIED' and not v['applied'] for v in out['assessment']['changes']))
    def test_declared_defaults_never_fill_required_missing_keys(self):
        self.value['changes']=[v for v in self.value['changes'] if v['key']!='queue_limit'];out=self.review();self.assertEqual(out['assessment']['missing_required_keys'],['queue_limit']);self.assertIsNone(out['effective_configuration_sha256'])
    def test_delete_required_key_and_delete_absent_key_are_visible(self):
        self.value['changes'][-1].update(action='delete',value_type=None,value_sha256=None,allow_override=False);out=self.review();self.assertEqual(out['assessment']['missing_required_keys'],['queue_limit'])
        self.value['changes']=[self.value['changes'][-1]];out=self.review();self.assertTrue(any(v['code']=='DELETE_ABSENT_KEY' for v in out['issues']))
    def test_delete_then_reset_is_explicit_final_state(self):
        delete=dict(self.value['changes'][-1],action='delete',value_type=None,value_sha256=None,allow_override=False);self.value['changes'][-1]=delete
        layer=dict(self.value['layers'][-1],id='third-layer',ordinal=3);self.value['layers'].append(layer);self.value['changes'].append(dict(delete,id='restore-value',layer=layer['id'],layer_sha256=pin(layer),action='set',value_type='integer',value_sha256=pin(6)))
        self.assertEqual(self.run_value()['status'],'PASS')
    def test_layer_gaps_and_ambiguous_key_slots_withhold(self):
        value=copy.deepcopy(self.value);value['layers'][1]['ordinal']=3;self.withheld(value)
        self.value['changes'].append(dict(self.value['changes'][0],id='alias'));self.withheld()
    def test_unknown_stale_layer_and_contract_pins_withhold(self):
        for change in ({'layer':'other'},{'layer_revision':2},{'layer_sha256':'0'*64},{'key':'other'},{'value_type':'string'}):
            value=copy.deepcopy(self.value);value['changes'][0].update(change);self.withheld(value)
        self.value['layers'][0]['contract_sha256']='0'*64;self.withheld()
    def test_empty_layers_never_pass_even_for_empty_contract(self):
        self.value['layers']=[];self.value['changes']=[];self.withheld()
    def test_empty_optional_and_empty_contract_scopes_are_explicit(self):
        self.value['changes']=[]
        for field in self.value['contract']['fields']:field['required']=False
        self.repin();self.assertEqual(self.run_value()['assessment']['effective_fields'],[])
        self.value['contract']['fields']=[];self.repin();self.assertEqual(self.run_value()['status'],'PASS')
    def test_no_value_digests_or_default_values_in_effective_field_rows(self):
        for row in self.run_value()['assessment']['effective_fields']:self.assertEqual(set(row),{'key','value_type','source_layer','source_change'})
        for change in ({'allow_override':1},{'value_sha256':'A'*64},{'value_type':'number'},{'action':'execute'}):
            value=copy.deepcopy(self.value);value['changes'][0].update(change);self.withheld(value)
