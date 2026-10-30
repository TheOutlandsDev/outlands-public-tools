import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import requests as app
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
        for key in ['operations_sha256', 'requests_sha256']:self.assertIsNone(out[key])
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
        for path in [['operations'], ['requests']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['operations_sha256', 'requests_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['operations'], ['requests']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['operations'], ['requests']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['operations'], ['requests']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['operations'], ['requests']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['operations'], ['requests']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['operations'], ['requests']][0]).clear();self.withheld(value)

    def test_known_valid_request_and_optional_field_absence(self):
        out=self.run_value();self.assertTrue(out['assessment']['requests'][0]['valid']);self.assertTrue(out['assessment']['requests'][0]['expectation_met']);self.value['requests'][0]['headers']={};self.value['requests'][0]['body'].pop('urgent');row=self.run_value()['assessment']['requests'][0];self.assertEqual(sum(v['state']=='optional_absent' for v in row['fields']),2)
    def test_wrong_method_and_route_never_trigger_routing_precedence(self):
        for change in ({'method':'PUT'},{'path':['other','proposal-alpha']}):
            value=copy.deepcopy(self.value);value['requests'][0].update(change);self.assertFalse(self.review(value)['assessment']['requests'][0]['valid'])
    def test_missing_fields_and_unknown_names_are_visible_without_values(self):
        self.value['requests'][0]['body'].pop('equipment');self.value['requests'][0]['body']['unknown-key']='SYNTHETIC_VALUE_SENTINEL';out=self.review();row=out['assessment']['requests'][0];self.assertEqual(row['unknown_field_counts']['body'],1);self.assertTrue(any(v['state']=='missing_required' for v in row['fields']));self.assertNotIn('SYNTHETIC_VALUE_SENTINEL',json.dumps(out));self.assertNotIn('unknown-key',json.dumps(out))
    def test_integer_boolean_and_string_fields_are_not_coerced(self):
        for change in ({'priority':True},{'priority':'2'},{'urgent':1},{'equipment':2}):
            value=copy.deepcopy(self.value);value['requests'][0]['body'].update(change);self.assertIn('FIELD_RULE_VIOLATION',self.review(value)['assessment']['requests'][0]['failed_criteria'])
    def test_choice_and_range_failures_are_exact(self):
        for change in ({'priority':0},{'priority':6},{'equipment':'SYNTHETIC_VALUE_SENTINEL'}):
            value=copy.deepcopy(self.value);value['requests'][0]['body'].update(change);out=self.review(value);self.assertFalse(out['assessment']['requests'][0]['valid']);self.assertNotIn('SYNTHETIC_VALUE_SENTINEL',json.dumps(out))
    def test_media_and_body_presence_are_independent_findings(self):
        self.value['requests'][0].update(media_type=None,body=None);row=self.review()['assessment']['requests'][0];self.assertIn('MEDIA_TYPE_MISMATCH',row['failed_criteria']);self.assertIn('JSON_BODY_REQUIRED',row['failed_criteria'])
    def test_null_expectation_is_not_a_validation_override(self):
        self.value['requests'][0].update(expected_valid=None);self.assertIsNone(self.run_value()['assessment']['requests'][0]['expectation_met']);self.value['requests'][0]['body']['priority']=6;self.assertFalse(self.review()['assessment']['requests'][0]['valid']);self.value['requests'][0]['expected_valid']=False;self.assertTrue(self.review()['assessment']['requests'][0]['expectation_met'])
    def test_exact_operation_revision_hash_and_known_selection_withhold(self):
        for change in ({'operation':'other'},{'operation_revision':2},{'operation_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['requests'][0].update(change);self.withheld(value)
    def test_query_values_are_decoded_strings_without_coercion(self):
        self.value['requests'][0]['query']['mode']=1;self.withheld()
    def test_custom_headers_reject_controls_noncustom_names_and_uppercase(self):
        for headers in ({'x-demo-client':'bad\r\nvalue'},{'content-type':'application/json'},{'X-Demo-Client':'workbench'}):
            value=copy.deepcopy(self.value);value['requests'][0]['headers']=headers;self.withheld(value)
    def test_nested_or_null_scalar_body_values_are_outside_supported_subset(self):
        for bad in ({'nested':1},[],None):
            value=copy.deepcopy(self.value);value['requests'][0]['body']['equipment']=bad;self.withheld(value)
    def test_empty_request_scope_and_unknown_fields_are_not_vacuous_passes(self):
        value=copy.deepcopy(self.value);value['requests']=[];self.withheld(value);self.value['requests'][0]['expected_valid']=1;self.withheld()
