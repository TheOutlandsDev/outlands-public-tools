import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import cases as app
import test_core as r

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
        for key in ['cases_sha256', 'expectations_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('artifact_bytes_verified','test_execution_verified','tests_executed','evidence_authenticity_verified','approval_authority_verified','records_changed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['cases'], ['expectations']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['cases_sha256', 'expectations_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['cases'], ['expectations']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['cases'], ['expectations']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['cases'], ['expectations']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['cases'], ['expectations']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['cases'], ['expectations']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['cases'], ['expectations']][0]).clear();self.withheld(value)

    def test_known_normalized_expectation_material(self):
        case=self.value['cases'][0];exp=self.value['expectations'][0];self.assertEqual(case['expectation_sha256'],pin(dict(exit_code=0,stdout_sha256=exp['stdout_sha256'],stderr_sha256=exp['stderr_sha256'])))
        out=self.run_value();self.assertEqual(out['assessment']['cases'],[dict(id='hvac-air-handler-flow',expectation_id='expect-flow',expectation_contract_present=True)]);self.assertEqual(out['cases_sha256'],pin(self.value['cases']))
    def test_missing_expectation_retains_exact_missing_case(self):
        self.value['expectations']=[];out=self.review();self.assertFalse(out['assessment']['cases'][0]['expectation_contract_present']);self.assertIsNotNone(out['cases_sha256'])
    def test_changed_expected_exit_hash_never_silently_rebinds(self):
        self.value['expectations'][0]['expected_exit']=1;self.withheld()
    def test_stale_or_unknown_case_reference_withholds(self):
        for change in ({'case':'other'},{'case_revision':2},{'case_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['expectations'][0].update(change);self.withheld(value)
    def test_two_expectation_ids_for_one_case_are_ambiguous(self):
        self.value['expectations'].append(dict(self.value['expectations'][0],id='other'));self.withheld()
    def test_expected_nonzero_exit_is_explicit_valid_contract(self):
        exp=self.value['expectations'][0];case=self.value['cases'][0];exp['expected_exit']=7;case['expectation_sha256']=r.expectation_pin(exp);exp['case_sha256']=pin(case);self.assertEqual(self.run_value()['status'],'PASS')
    def test_bad_exit_revision_and_hash_shapes_are_rejected(self):
        for field,bad in [('expected_exit',True),('expected_exit',-1),('expected_exit',256),('case_revision',True),('stdout_sha256','A'*64)]:
            value=copy.deepcopy(self.value);value['expectations'][0][field]=bad;self.withheld(value)
    def test_declared_case_aliases_remain_distinct_cases(self):
        case=dict(self.value['cases'][0],id='hvac-second');self.value['cases'].append(case);self.value['expectations'].append(dict(self.value['expectations'][0],id='second-expectation',case=case['id'],case_sha256=pin(case)))
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual(len(out['assessment']['cases']),2)
