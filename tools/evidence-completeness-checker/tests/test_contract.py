import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import evidence as app
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
        for key in ['cases_sha256', 'expectations_sha256', 'results_sha256', 'run_sha256', 'policy_sha256', 'artifacts_sha256']:self.assertIsNone(out[key])
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
        for path in [['cases'], ['expectations'], ['results'], ['artifacts']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['cases_sha256', 'expectations_sha256', 'results_sha256', 'run_sha256', 'policy_sha256', 'artifacts_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['cases'], ['expectations'], ['results'], ['artifacts']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['cases'], ['expectations'], ['results'], ['artifacts']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['cases'], ['expectations'], ['results'], ['artifacts']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['cases'], ['expectations'], ['results'], ['artifacts']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['cases'], ['expectations'], ['results'], ['artifacts']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['cases'], ['expectations'], ['results'], ['artifacts']][0]).clear();self.withheld(value)

    def repin_artifacts(self):
        for row in self.value['artifacts']:row['result_sha256']=pin(self.value['results'][0])
    def test_known_complete_evidence_bindings(self):
        out=self.run_value();row=out['assessment']['cases'][0];self.assertTrue(row['ready_for_manual_evidence_review']);self.assertEqual(row['missing_roles'],[]);self.assertEqual(len(row['artifact_ids']),2);self.assertFalse(out['assessment']['test_outcomes_upgraded'])
    def test_complete_failure_evidence_does_not_upgrade_outcome(self):
        self.value['results'][0]['observed_exit']=1;self.repin_artifacts();out=self.run_value();self.assertEqual(out['status'],'PASS');row=out['assessment']['cases'][0];self.assertFalse(row['observation']['matched']);self.assertTrue(row['ready_for_manual_evidence_review']);self.assertFalse(out['assessment']['test_outcomes_upgraded'])
    def test_missing_and_incomplete_roles_are_separate(self):
        self.value['artifacts'].pop();self.value['artifacts'][0]['complete']=False;row=self.review()['assessment']['cases'][0];self.assertEqual(row['missing_roles'],['result-summary']);self.assertEqual(row['incomplete_roles'],['case-receipt'])
    def test_empty_artifact_list_is_missing_not_complete(self):
        self.value['artifacts']=[];self.assertEqual(len(self.review()['assessment']['cases'][0]['missing_roles']),2)
    def test_duplicate_case_role_slots_are_ambiguous(self):
        self.value['artifacts'].append(dict(self.value['artifacts'][0],id='other-artifact'));self.withheld()
    def test_stale_result_binding_cannot_follow_changed_result(self):
        self.value['results'][0]['observed_exit']=1;self.withheld()
    def test_cross_run_case_result_policy_and_unknown_bindings_withhold(self):
        for change in ({'run':'other'},{'run_revision':2},{'run_sha256':'0'*64},{'case':'other'},{'case_revision':2},{'case_sha256':'0'*64},{'result':'other'},{'result_sha256':'0'*64},{'policy_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['artifacts'][0].update(change);self.withheld(value)
    def test_policy_role_set_normalization_preserves_pins(self):
        before=self.run_value()['qualified_scope_sha256'];self.value['policy']['required_roles'].reverse();self.assertEqual(self.run_value()['qualified_scope_sha256'],before)
    def test_policy_revision_change_requires_artifact_rebinding(self):
        self.value['policy']['revision']=2;self.withheld()
    def test_truncated_observation_blocks_complete_artifact_claims(self):
        self.value['results'][0]['output_complete']=False;self.repin_artifacts();row=self.review()['assessment']['cases'][0];self.assertFalse(row['ready_for_manual_evidence_review']);self.assertIn('OBSERVATION_INCOMPLETE',[i['code'] for i in self.review()['issues']])
    def test_noncompleted_run_cannot_be_complete_evidence(self):
        self.value['results'][0].update(state='cancelled',observed_exit=None,stdout_sha256=None,stderr_sha256=None,output_complete=False);self.repin_artifacts();self.assertFalse(self.review()['assessment']['all_evidence_contracts_complete'])
    def test_unknown_role_or_boolean_completeness_coercion_refused(self):
        for change in ({'role':'other'},{'complete':1}):
            value=copy.deepcopy(self.value);value['artifacts'][0].update(change);self.withheld(value)
    def test_empty_policy_roles_is_fixed_refusal(self):
        self.value['policy']['required_roles']=[]
        with self.assertRaises(t.Rejected):self.run_value()
