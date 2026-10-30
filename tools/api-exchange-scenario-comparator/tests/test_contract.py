import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import scenarios as app
import api_core as r

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
        for key in ['baseline_operations_sha256', 'candidate_operations_sha256', 'baseline_requests_sha256', 'candidate_requests_sha256', 'baseline_responses_sha256', 'candidate_responses_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('network_requests_performed','servers_started','authentication_performed','credentials_verified','service_behavior_verified','wire_protocol_verified','records_changed','raw_values_emitted','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['baseline_operations'], ['candidate_operations'], ['baseline_requests'], ['candidate_requests'], ['baseline_responses'], ['candidate_responses']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['baseline_operations_sha256', 'candidate_operations_sha256', 'baseline_requests_sha256', 'candidate_requests_sha256', 'baseline_responses_sha256', 'candidate_responses_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['baseline_operations'], ['candidate_operations'], ['baseline_requests'], ['candidate_requests'], ['baseline_responses'], ['candidate_responses']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['baseline_operations'], ['candidate_operations'], ['baseline_requests'], ['candidate_requests'], ['baseline_responses'], ['candidate_responses']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['baseline_operations'], ['candidate_operations'], ['baseline_requests'], ['candidate_requests'], ['baseline_responses'], ['candidate_responses']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['baseline_operations'], ['candidate_operations'], ['baseline_requests'], ['candidate_requests'], ['baseline_responses'], ['candidate_responses']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['baseline_operations'], ['candidate_operations'], ['baseline_requests'], ['candidate_requests'], ['baseline_responses'], ['candidate_responses']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['baseline_operations'], ['candidate_operations'], ['baseline_requests'], ['candidate_requests'], ['baseline_responses'], ['candidate_responses']][0]).clear();self.withheld(value)

    def repin(self):
        for side in ('baseline','candidate'):
            operation=self.value[side+'_operations'][0]
            for row in self.value[side+'_requests']:row.update(operation_revision=operation['revision'],operation_sha256=pin(operation))
            for row in self.value[side+'_responses']:row['request_sha256']=pin(next(v for v in self.value[side+'_requests'] if v['id']==row['request']))
    def test_known_header_revision_change_with_equal_observation_results(self):
        out=self.run_value();row=out['assessment']['scenarios'][0];self.assertEqual(row['state'],'unchanged');self.assertTrue(row['baseline']['request_valid']);self.assertTrue(row['candidate']['response_valid']);self.assertFalse(out['assessment']['whole_api_compatibility_verified'])
    def test_contract_change_retains_request_and_response_regression(self):
        self.value['candidate_operations'][0]['request_fields'][3]['maximum']=1;self.repin();row=self.review()['assessment']['scenarios'][0];self.assertEqual(row['state'],'validation_changed');self.assertFalse(row['candidate']['request_valid']);self.assertFalse(row['candidate']['response_valid'])
    def test_missing_candidate_requests_never_improve_coverage(self):
        self.value['candidate_requests']=[];self.value['candidate_responses']=[];row=self.review()['assessment']['scenarios'][0];self.assertEqual(row['state'],'candidate_missing');self.assertIsNone(row['candidate'])
    def test_missing_response_on_either_side_remains_incomparable(self):
        for side in ('baseline','candidate'):
            value=copy.deepcopy(self.value);value[side+'_responses']=[];row=self.review(value)['assessment']['scenarios'][0];self.assertEqual(row['state'],'response_coverage_missing');self.assertIsNone(row['baseline'])
    def test_changed_request_payload_or_expectation_is_not_paired(self):
        for change in ({'expected_valid':None},{'method':'PUT'},{'revision':2}):
            value=copy.deepcopy(self.value);value['candidate_requests'][0].update(change);value['candidate_responses'][0].update(request_revision=value['candidate_requests'][0]['revision'],request_sha256=pin(value['candidate_requests'][0]));self.assertEqual(self.review(value)['assessment']['scenarios'][0]['state'],'request_scope_changed')
    def test_changed_response_payload_or_identity_is_not_a_regression_comparison(self):
        for change in ({'id':'different-observation'},{'status':400},{'body':{'accepted':False,'proposal':'proposal-alpha'}}):
            value=copy.deepcopy(self.value);value['candidate_responses'][0].update(change);row=self.review(value)['assessment']['scenarios'][0];self.assertEqual(row['state'],'response_scope_changed');self.assertIsNone(row['candidate'])
    def test_same_operation_identity_cannot_hide_changed_definition(self):
        self.value['candidate_operations'][0]['revision']=1;self.value['candidate_operations'][0]['request_fields'][3]['maximum']=1;self.repin();self.withheld()
    def test_identical_operation_identity_and_definition_are_supported(self):
        self.value['candidate_operations']=copy.deepcopy(self.value['baseline_operations']);self.repin();self.assertEqual(self.run_value()['status'],'PASS')
    def test_expected_invalid_cases_can_match_without_claiming_valid_api_traffic(self):
        for side in ('baseline','candidate'):
            self.value[side+'_requests'][0]['body']['priority']=6;self.value[side+'_requests'][0]['expected_valid']=False;self.value[side+'_responses'][0]['expected_valid']=False
        self.repin();out=self.run_value();row=out['assessment']['scenarios'][0];self.assertEqual(out['status'],'PASS');self.assertFalse(row['baseline']['request_valid']);self.assertFalse(row['candidate']['response_valid']);self.assertTrue(row['candidate']['response_expectation_met'])
    def test_equal_invalidity_with_wrong_expectations_still_requires_review(self):
        for side in ('baseline','candidate'):self.value[side+'_requests'][0]['body']['priority']=6
        self.repin();row=self.review()['assessment']['scenarios'][0];self.assertEqual(row['state'],'unchanged');self.assertFalse(row['candidate']['request_expectation_met'])
    def test_added_candidate_requests_and_empty_baseline_have_explicit_outcomes(self):
        value=copy.deepcopy(self.value);request=dict(value['candidate_requests'][0],id='added-request');value['candidate_requests'].append(request);value['candidate_responses'].append(dict(value['candidate_responses'][0],id='added-response',request=request['id'],request_sha256=pin(request)));out=self.review(value);self.assertEqual(out['assessment']['scenarios'][0]['state'],'candidate_only')
        self.value['baseline_requests']=[];self.value['baseline_responses']=[];self.withheld()
    def test_unknown_operation_or_stale_response_pin_withholds_full_comparison(self):
        value=copy.deepcopy(self.value);value['candidate_requests'][0]['operation']='other';self.withheld(value);self.value['candidate_responses'][0]['request_sha256']='0'*64;self.withheld()
