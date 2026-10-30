import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import runs as app
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
        for key in ['cases_sha256', 'expectations_sha256', 'results_sha256', 'run_sha256']:self.assertIsNone(out[key])
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
        for path in [['cases'], ['expectations'], ['results']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['cases_sha256', 'expectations_sha256', 'results_sha256', 'run_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['cases'], ['expectations'], ['results']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['cases'], ['expectations'], ['results']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['cases'], ['expectations'], ['results']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['cases'], ['expectations'], ['results']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['cases'], ['expectations'], ['results']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['cases'], ['expectations'], ['results']][0]).clear();self.withheld(value)

    def rebind(self,value=None):
        value=self.value if value is None else value;header=value['run'];header['cases_sha256']=pin(sorted(value['cases'],key=lambda row:row['id']));header['expectations_sha256']=pin(sorted(value['expectations'],key=lambda row:row['id']))
        for row in value['results']:row['run_sha256']=pin(header)
    def test_known_complete_matching_coverage(self):
        out=self.run_value();self.assertEqual((out['assessment']['planned_cases'],out['assessment']['completed_cases'],out['assessment']['matched_cases']),(1,1,1));self.assertTrue(out['assessment']['all_cases_complete_and_matched'])
    def test_no_result_is_missing_not_passed(self):
        self.value['results']=[];out=self.review();self.assertIsNone(out['assessment']['cases'][0]['matched']);self.assertEqual(out['assessment']['cases'][0]['state'],'missing')
    def test_all_noncompleted_states_never_match(self):
        for state in ('timeout','cancelled','refused','not-run','output-limited','unknown'):
            value=copy.deepcopy(self.value);value['results'][0].update(state=state,observed_exit=None,stdout_sha256=None,stderr_sha256=None,output_complete=False);out=self.review(value);self.assertIsNone(out['assessment']['cases'][0]['matched'])
    def test_completed_but_truncated_is_incomplete(self):
        self.value['results'][0]['output_complete']=False;out=self.review();self.assertEqual(out['assessment']['cases'][0]['failed_criteria'],['OUTPUT_INCOMPLETE']);self.assertIsNone(out['assessment']['cases'][0]['matched'])
    def test_each_observed_field_must_match(self):
        for field,new in [('observed_exit',1),('stdout_sha256','0'*64),('stderr_sha256','0'*64)]:
            value=copy.deepcopy(self.value);value['results'][0][field]=new;self.assertIs(self.review(value)['assessment']['cases'][0]['matched'],False)
    def test_expected_nonzero_result_can_match(self):
        exp=self.value['expectations'][0];case=self.value['cases'][0];exp['expected_exit']=7;case['expectation_sha256']=r.expectation_pin(exp);exp['case_sha256']=pin(case);self.value['results'][0].update(observed_exit=7,case_sha256=pin(case));self.rebind();self.assertEqual(self.run_value()['status'],'PASS')
    def test_multiple_result_ids_per_case_do_not_select_latest(self):
        self.value['results'].append(dict(self.value['results'][0],id='other-result'));self.withheld()
    def test_run_subject_and_cohort_changes_require_exact_rebinding(self):
        self.value['run']['subject_sha256']='1'*64;self.withheld();self.rebind();self.assertEqual(self.run_value()['status'],'PASS')
    def test_stale_run_case_and_unknown_references_withhold(self):
        for change in ({'run':'other'},{'run_revision':2},{'run_sha256':'0'*64},{'case':'other'},{'case_revision':2},{'case_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['results'][0].update(change);self.withheld(value)
    def test_wrong_header_cohort_never_qualifies(self):
        self.value['run']['cases_sha256']='0'*64;self.withheld()
    def test_missing_expectation_requires_review_even_with_matching_observation(self):
        self.value['expectations']=[];self.rebind();self.assertIn('EXPECTATION_MISSING',self.review()['assessment']['cases'][0]['failed_criteria'])
    def test_impossible_noncompleted_payload_and_boolean_exit_refuse(self):
        for change in ({'state':'timeout'},{'observed_exit':True},{'output_complete':1},{'state':'passed'}):
            value=copy.deepcopy(self.value);value['results'][0].update(change);self.withheld(value)
