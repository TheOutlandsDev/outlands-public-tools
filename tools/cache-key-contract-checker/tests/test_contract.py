import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import keys as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['contract_sha256', 'entries_sha256', 'qualified_entries_sha256']:self.assertIsNone(r[key])
        return r
    def test_positive_and_authority_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('artifact_bytes_verified','record_authenticity_verified','actual_cache_state_verified','cache_mutated','execution_performed','exactly_once_verified','retry_authorized','provider_contacted','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_preserves_full_scope_pins(self):
        before=self.run_value()
        for key in ['entries']:self.value[key].reverse()
        after=self.run_value()
        for key in ['contract_sha256', 'entries_sha256', 'qualified_entries_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_identity_snapshots_count_once(self):
        for key in ['entries']:
            if not self.value[key]:continue
            value=copy.deepcopy(self.value);value[key].append(copy.deepcopy(value[key][0]));r=self.run_value(value)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_bad_rows_withhold_and_omit_supplied_values(self):
        for key in ['entries']:
            value=copy.deepcopy(self.value);value[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_are_fixed_refusals(self):
        for key in ['entries']:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);value[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def rekey(self,row=None):
        row=row or self.value['entries'][0];rule=copy.deepcopy(self.value['contract']);rule['dependencies'].sort();row['contract_sha256']=pin(rule)
        row['inputs'].sort(key=lambda r:r['id']);row['key_sha256']=pin(dict(contract_sha256=row['contract_sha256'],inputs=row['inputs']))
    def test_expected_key_uses_complete_contract_and_sorted_inputs(self):
        r=self.run_value();row=self.value['entries'][0];self.assertEqual(r['assessment']['entries'][0]['expected_key_sha256'],pin(dict(contract_sha256=pin(self.value['contract']),inputs=row['inputs'])));self.assertEqual(r['qualified_entries_sha256'],pin(self.value['entries']))
    def test_input_order_and_contract_dependency_order_normalize(self):
        before=self.run_value();self.value['contract']['dependencies'].reverse();self.value['entries'][0]['inputs'].reverse();self.assertEqual(self.run_value()['qualified_entries_sha256'],before['qualified_entries_sha256'])
    def test_input_revision_change_requires_a_different_key(self):
        self.value['entries'][0]['inputs'][0]['revision']=2;r=self.review();self.assertIn('KEY_DERIVATION_MISMATCH',r['assessment']['entries'][0]['failed_criteria']);self.assertIsNone(r['qualified_entries_sha256']);self.assertIsNotNone(r['entries_sha256'])
    def test_missing_dependency_never_gets_a_partial_expected_key(self):
        self.value['entries'][0]['inputs'].pop();r=self.review();self.assertEqual(r['assessment']['entries'][0]['missing_dependencies'],['ruleset']);self.assertIsNone(r['assessment']['entries'][0]['expected_key_sha256'])
    def test_unknown_or_duplicate_dependency_is_a_rejected_row(self):
        for row in (dict(id='other',revision=1,sha256='1'*64),copy.deepcopy(self.value['entries'][0]['inputs'][0])):
            value=copy.deepcopy(self.value);value['entries'][0]['inputs'].append(row);self.withheld(value)
    def test_same_key_same_material_same_content_aliases_are_visible(self):
        self.value['entries'].append(dict(self.value['entries'][0],id='entry-alias'));r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(r['assessment']['unique_keys'],1);self.assertEqual(len(r['assessment']['key_groups'][0]['entry_ids']),2)
    def test_same_declared_key_different_inputs_is_a_group_conflict(self):
        other=copy.deepcopy(self.value['entries'][0]);other['id']='entry-other';other['inputs'][0]['revision']=2;self.value['entries'].append(other);r=self.review()
        self.assertFalse(r['assessment']['key_groups'][0]['consistent']);self.assertTrue(all('KEY_INPUT_BINDING_CONFLICT' in row['failed_criteria'] for row in r['assessment']['entries']))
    def test_same_key_different_content_is_not_latest_value_selection(self):
        self.value['entries'].append(dict(self.value['entries'][0],id='entry-other',content_sha256='1'*64));r=self.review();self.assertEqual(r['assessment']['key_groups'][0]['content_bindings'],2);self.assertIsNone(r['qualified_entries_sha256'])
    def test_stale_contract_pin_withholds_all_keys(self):
        self.value['contract']['key_version']=2;self.withheld()
    def test_namespace_and_key_version_bind_derivation(self):
        original=self.value['entries'][0]['key_sha256'];self.value['contract'].update(namespace='hvac-other',key_version=2);self.rekey();self.assertEqual(self.run_value()['status'],'PASS');self.assertNotEqual(self.value['entries'][0]['key_sha256'],original)
    def test_conflicting_entry_identity_withholds_every_member(self):
        self.value['entries'].append(dict(self.value['entries'][0],content_sha256='1'*64));r=self.withheld();self.assertEqual(r['counts']['entries']['conflict_rows'],2)
    def test_empty_entries_and_bad_input_fingerprints_withhold(self):
        value=copy.deepcopy(self.value);value['entries']=[];self.withheld(value)
        for change in ({'revision':True},{'sha256':'bad'},{'extra':0}):
            value=copy.deepcopy(self.value);value['entries'][0]['inputs'][0].update(change);self.withheld(value)
    def test_contract_schema_and_dependency_bounds_refuse(self):
        for change in ({'key_version':True},{'dependencies':[]},{'dependencies':['a','a']},{'extra':0}):
            value=copy.deepcopy(self.value);value['contract'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(value)
    def test_invalid_key_hash_is_rejected_but_wrong_valid_hash_is_review(self):
        value=copy.deepcopy(self.value);value['entries'][0]['key_sha256']='not-a-hash';self.withheld(value)
        self.value['entries'][0]['key_sha256']='0'*64;self.assertIsNotNone(self.review()['assessment'])
    def test_fictional_game_cache_contract(self):
        value=json.loads((Path(__file__).resolve().parents[1]/'examples/game-cache.json').read_text(encoding='utf-8'));self.assertTrue(self.run_value(value)['assessment']['all_bindings_valid'])
