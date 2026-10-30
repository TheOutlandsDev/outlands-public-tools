import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import responses as app
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
        for key in ['operations_sha256', 'requests_sha256', 'responses_sha256']:self.assertIsNone(out[key])
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
        for path in [['operations'], ['requests'], ['responses']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['operations_sha256', 'requests_sha256', 'responses_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['operations'], ['requests'], ['responses']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['operations'], ['requests'], ['responses']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['operations'], ['requests'], ['responses']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['operations'], ['requests'], ['responses']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['operations'], ['requests'], ['responses']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['operations'], ['requests'], ['responses']][0]).clear();self.withheld(value)

    def repin(self):self.value['responses'][0]['request_sha256']=pin(self.value['requests'][0])
    def test_known_response_is_bound_to_exact_request_and_operation(self):
        out=self.run_value();self.assertTrue(out['assessment']['responses'][0]['valid']);self.assertEqual(out['assessment']['responses'][0]['variant_id'],'response-success');self.assertEqual(out['assessment']['coverage'],[dict(request='request-preview',response_id='observed-preview')])
    def test_explicit_error_variant_can_validate_an_invalid_request(self):
        request=self.value['requests'][0];request['body']['priority']=6;request['expected_valid']=False;self.repin();self.value['responses'][0].update(status=400,headers={},body={'error':'invalid-proposal'});out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertFalse(out['assessment']['requests'][0]['valid']);self.assertTrue(out['assessment']['responses'][0]['valid'])
    def test_invalid_request_cannot_use_success_variant_and_false_expectation_cannot_clear_response(self):
        self.value['requests'][0]['body']['priority']=6;self.value['requests'][0]['expected_valid']=False;self.repin();self.value['responses'][0]['expected_valid']=False;row=self.review()['assessment']['responses'][0];self.assertIn('REQUEST_VALIDITY_VARIANT_MISMATCH',row['failed_criteria']);self.assertTrue(row['expectation_met'])
    def test_missing_response_coverage_is_not_a_success_or_invented_body(self):
        self.value['responses']=[];out=self.review();self.assertIsNone(out['assessment']['coverage'][0]['response_id']);self.assertEqual(out['assessment']['responses'],[])
    def test_alias_response_id_for_same_request_is_structural_ambiguity(self):
        self.value['responses'].append(dict(self.value['responses'][0],id='alias'));self.withheld()
    def test_unknown_status_and_wrong_media_remain_findings(self):
        value=copy.deepcopy(self.value);value['responses'][0]['status']=201;self.assertEqual(self.review(value)['assessment']['responses'][0]['failed_criteria'],['STATUS_UNDECLARED']);self.value['responses'][0]['media_type']=None;self.assertIn('MEDIA_TYPE_MISMATCH',self.review()['assessment']['responses'][0]['failed_criteria'])
    def test_body_type_missing_required_and_unknown_fields_do_not_echo_data(self):
        self.value['responses'][0]['body'].update(accepted='SYNTHETIC_VALUE_SENTINEL',extra='SYNTHETIC_VALUE_SENTINEL');out=self.review();self.assertEqual(out['assessment']['responses'][0]['unknown_field_counts']['body'],1);self.assertNotIn('SYNTHETIC_VALUE_SENTINEL',json.dumps(out))
    def test_exact_request_revision_and_hash_withhold_entire_scope(self):
        for change in ({'request':'other'},{'request_revision':2},{'request_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['responses'][0].update(change);self.withheld(value)
    def test_request_and_response_expected_mismatches_are_separate(self):
        value=copy.deepcopy(self.value);value['requests'][0]['expected_valid']=False;value['responses'][0]['request_sha256']=pin(value['requests'][0]);self.assertTrue(any(v['side']=='requests' for v in self.review(value)['issues']));self.value['responses'][0]['expected_valid']=False;self.assertTrue(any(v['side']=='responses' for v in self.review()['issues']))
    def test_head_and_bodyless_status_never_allow_content(self):
        operation=self.value['operations'][0];operation.update(method='HEAD',request_media_type=None,request_fields=[v for v in operation['request_fields'] if v['location']!='body'],responses=[dict(id='head-ok',status=200,media_type=None,request_valid=True,fields=[])]);request=self.value['requests'][0];request.update(method='HEAD',media_type=None,body=None,operation_sha256=pin(operation));self.repin();self.value['responses'][0].update(media_type=None,headers={},body=None);self.assertEqual(self.run_value()['status'],'PASS');self.value['responses'][0]['body']={};self.assertIn('BODY_NOT_ALLOWED',self.review()['assessment']['responses'][0]['failed_criteria'])
    def test_field_assessment_scope_is_bounded_before_rendering(self):
        operation=self.value['operations'][0];template=operation['request_fields'][1];fields=[dict(template,id='field-'+str(i),name='name-'+str(i),required=False,choices=[]) for i in range(32)];operation.update(route=['preview'],request_fields=fields,responses=[dict(id='ok',status=200,media_type='application/json',request_valid=True,fields=copy.deepcopy(fields))]);requests=[];responses=[]
        for i in range(520):
            request=dict(self.value['requests'][0],id='request-'+str(i),path=['preview'],query={},headers={},body={},operation_sha256=pin(operation));requests.append(request);responses.append(dict(self.value['responses'][0],id='response-'+str(i),request=request['id'],request_sha256=pin(request),headers={},body={}))
        self.value.update(requests=requests,responses=responses)
        with self.assertRaisesRegex(t.Rejected,'FIELD_ASSESSMENT_LIMIT'):self.run_value()
    def test_no_actual_response_or_authentication_claim_is_made(self):
        out=self.run_value();self.assertFalse(out['service_behavior_verified']);self.assertFalse(out['authentication_performed']);self.assertFalse(out['wire_protocol_verified']);self.assertFalse(out['raw_values_emitted'])
