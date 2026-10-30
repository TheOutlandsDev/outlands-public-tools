import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import migrations as app
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
        for key in ['contracts_sha256', 'steps_sha256', 'source_sha256', 'target_sha256']:self.assertIsNone(out[key])
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
        for path in [['contracts'], ['steps']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['contracts_sha256', 'steps_sha256', 'source_sha256', 'target_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['contracts'], ['steps']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['contracts'], ['steps']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            
            if path[-1]=='fields':row=copy.deepcopy(rows[0]);row['required']=not row['required']
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['contracts'], ['steps']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['contracts'], ['steps']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['contracts'], ['steps']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])

    def test_known_explicit_path_and_checks_not_executed(self):
        out=self.run_value();self.assertEqual(out['assessment']['contract_ids'],['hvac-service-v1','hvac-service-v2']);self.assertTrue(out['assessment']['target_reached']);self.assertEqual(out['assessment']['required_check_ids'],['fictional-value-contract-check']);self.assertFalse(out['assessment']['checks_executed']);self.assertFalse(out['assessment']['adapters_opened'])
    def test_zero_step_requires_exact_same_source_and_target(self):
        self.value['steps']=[];self.assertFalse(self.review()['assessment']['target_reached']);self.value['target']=copy.deepcopy(self.value['source']);self.assertEqual(self.run_value()['status'],'PASS')
    def test_ordinal_gap_and_alias_ordinal_withhold(self):
        value=copy.deepcopy(self.value);value['steps'][0]['ordinal']=2;self.withheld(value)
        self.value['steps'].append(dict(self.value['steps'][0],id='alias'));self.withheld()
    def test_unknown_stale_selectors_and_step_references_withhold(self):
        for side in ('source','target'):
            for change in ({'id':'other'},{'revision':2},{'sha256':'0'*64}):
                value=copy.deepcopy(self.value);value[side].update(change)
                if side=='target' and change=={'revision':2}:continue
                self.withheld(value)
        for change in ({'from_contract':'other'},{'to_contract_revision':3},{'from_contract_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['steps'][0].update(change);self.withheld(value)
    def test_cycle_is_not_success_even_when_target_matches(self):
        row=dict(self.value['steps'][0],id='return-step',ordinal=2);row.update(from_contract=self.value['target']['id'],from_contract_revision=self.value['target']['revision'],from_contract_sha256=self.value['target']['sha256'],to_contract=self.value['source']['id'],to_contract_revision=self.value['source']['revision'],to_contract_sha256=self.value['source']['sha256']);self.value['steps'].append(row);self.value['target']=copy.deepcopy(self.value['source']);self.withheld()
    def test_two_step_continuity_and_discontinuity(self):
        new=dict(self.value['contracts'][-1],id='hvac-service-v3',revision=3);self.value['contracts'].append(new);row=dict(self.value['steps'][0],id='next-step',ordinal=2,from_contract=self.value['target']['id'],from_contract_revision=2,from_contract_sha256=self.value['target']['sha256'],to_contract=new['id'],to_contract_revision=3,to_contract_sha256=pin(new));self.value['steps'].append(row);self.value['target']=dict(id=new['id'],revision=3,sha256=pin(new));self.assertEqual(self.run_value()['status'],'PASS')
        row.update(from_contract=self.value['source']['id'],from_contract_revision=1,from_contract_sha256=self.value['source']['sha256']);self.withheld()
    def test_one_selected_revision_per_contract_identity(self):
        self.value['contracts'].append(dict(self.value['contracts'][0],revision=2));self.withheld()
    def test_nested_contract_errors_reject_entire_registry_record(self):
        self.value['contracts'][0]['fields'][0]['required']=1;out=self.withheld();self.assertEqual(out['counts']['contracts']['rejected_rows'],1)
    def test_empty_registry_and_bad_adapter_or_check_tags_withhold(self):
        value=copy.deepcopy(self.value);value['contracts']=[];self.withheld(value)
        for change in ({'adapter_sha256':'A'*64},{'required_checks':['check','check']},{'required_checks':['INVALID_SENTINEL']}):
            value=copy.deepcopy(self.value);value['steps'][0].update(change);self.withheld(value)
    def test_selector_shape_errors_are_fixed_refusals(self):
        for change in ({'revision':True},{'sha256':'invalid'},{'extra':'SENTINEL'}):
            value=copy.deepcopy(self.value);value['source'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(value)
    def test_field_and_check_scope_limits_are_bounded(self):
        value=copy.deepcopy(self.value);template=value['contracts'][0];value['contracts']=[dict(template,id='contract-'+str(i),fields=[dict(template['fields'][0],id='field-'+str(j)) for j in range(128)]) for i in range(33)]
        with self.assertRaisesRegex(t.Rejected,'CONTRACT_FIELD_SCOPE_LIMIT'):self.run_value(value)
        value=copy.deepcopy(self.value);value['steps']=[dict(value['steps'][0],id='step-'+str(i),ordinal=i+1,required_checks=['check-'+str(j) for j in range(32)]) for i in range(129)]
        with self.assertRaisesRegex(t.Rejected,'CHECK_REFERENCE_SCOPE_LIMIT'):self.run_value(value)
