import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import matrix as app
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
        for key in ['components_sha256', 'rules_sha256', 'requirements_sha256']:self.assertIsNone(out[key])
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
        for path in [['components'], ['rules'], ['requirements']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['components_sha256', 'rules_sha256', 'requirements_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['components'], ['rules'], ['requirements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['components'], ['rules'], ['requirements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            
            if path[-1]=='fields':row=copy.deepcopy(rows[0]);row['required']=not row['required']
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['components'], ['rules'], ['requirements']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['components'], ['rules'], ['requirements']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['components'], ['rules'], ['requirements']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])

    def reverse_pair(self,row):
        for suffix in ('','_revision','_sha256'):row['left'+suffix],row['right'+suffix]=row['right'+suffix],row['left'+suffix]
    def test_known_requested_pair_is_declared_supported_only(self):
        out=self.run_value();self.assertEqual(out['assessment']['requirements'][0]['state'],'supported');self.assertTrue(out['assessment']['all_requested_pairs_declared_supported']);self.assertFalse(out['assessment']['unrequested_pairs_checked']);self.assertFalse(out['runtime_compatibility_verified'])
    def test_symmetric_normalization_and_reverse_duplicate(self):
        before=self.run_value();self.reverse_pair(self.value['rules'][0]);self.reverse_pair(self.value['requirements'][0]);after=self.run_value()
        for key in ('rules_sha256','requirements_sha256','qualified_scope_sha256'):self.assertEqual(before[key],after[key])
        self.value['rules'].append(copy.deepcopy(self.value['rules'][0]));self.reverse_pair(self.value['rules'][1]);self.assertEqual(self.run_value()['counts']['rules']['duplicate_rows'],1)
    def test_unknown_is_not_supported_and_false_is_not_missing(self):
        self.value['rules']=[];out=self.review();self.assertEqual(out['assessment']['requirements'][0]['state'],'unlisted');self.assertIsNone(out['assessment']['requirements'][0]['rule_id'])
        self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'));self.value['rules'][0]['allowed']=False;self.assertEqual(self.review()['assessment']['requirements'][0]['state'],'unsupported')
    def test_no_component_or_no_requests_never_passes_vacuously(self):
        for side in ('components','requirements'):
            value=copy.deepcopy(self.value);value[side]=[];self.withheld(value)
    def test_different_rule_or_request_ids_for_same_pair_are_ambiguous(self):
        for side in ('rules','requirements'):
            value=copy.deepcopy(self.value);value[side].append(dict(value[side][0],id='alias'));self.withheld(value)
    def test_stale_or_unknown_endpoint_is_withheld_even_in_unused_rule(self):
        third=dict(self.value['components'][0],id='hvac-third');self.value['components'].append(third)
        unused=dict(self.value['rules'][0],id='unused-rule',right=third['id'],right_sha256=pin(third));self.value['rules'].append(unused);self.assertEqual(self.run_value()['status'],'PASS')
        unused['right_sha256']='0'*64;self.withheld()
    def test_endpoint_versions_and_contract_pins_are_full_snapshot_bound(self):
        for change in ({'version':'another-release'},{'revision':2},{'contract_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['components'][0].update(change);self.withheld(value)
    def test_version_tokens_have_no_range_or_semver_inference(self):
        component=self.value['components'][0];component['version']='unranked-build';component['revision']=3
        for side in ('rules','requirements'):
            row=self.value[side][0];key='left' if row['left']==component['id'] else 'right';row[key+'_revision']=3;row[key+'_sha256']=pin(component)
        self.assertEqual(self.run_value()['status'],'PASS')
    def test_self_pair_and_non_boolean_decision_are_refused_rows(self):
        for side in ('rules','requirements'):
            value=copy.deepcopy(self.value);value[side][0]['right']=value[side][0]['left'];self.withheld(value)
        self.value['rules'][0]['allowed']=1;self.withheld()
    def test_reverse_alias_cannot_silently_override_rule(self):
        alias=dict(self.value['rules'][0],id='opposite-rule',allowed=False);self.reverse_pair(alias);self.value['rules'].append(alias);self.withheld()
