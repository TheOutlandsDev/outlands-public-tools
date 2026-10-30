import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import operations as app
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
        for key in ['operations_sha256']:self.assertIsNone(out[key])
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
        for path in [['operations']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['operations_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['operations']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['operations']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['operations']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['operations']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['operations']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['operations']][0]).clear();self.withheld(value)

    def test_known_method_route_and_explicit_response_variants(self):
        row=self.run_value()['assessment']['operations'][0];self.assertEqual((row['method'],row['route_segments'],row['request_fields'],row['response_statuses']),('POST',2,6,[200,400]))
    def test_overlapping_parameter_and_literal_routes_are_ambiguous(self):
        alias=copy.deepcopy(self.value['operations'][0]);alias.update(id='literal-alias',route=['service-proposals','preview']);alias['request_fields']=[v for v in alias['request_fields'] if v['location']!='path'];self.value['operations'].append(alias);self.withheld()
    def test_different_method_or_literal_routes_do_not_overlap(self):
        alias=copy.deepcopy(self.value['operations'][0]);alias.update(id='different',method='PUT');self.value['operations'].append(alias);self.assertEqual(self.run_value()['status'],'PASS');alias.update(method='POST',route=['different-proposals','{proposal}']);self.assertEqual(self.run_value()['status'],'PASS')
    def test_parameter_names_are_unique_and_exactly_declared(self):
        for route in (['service-proposals','{other}'],['{proposal}','{proposal}'],['/private'],['{INVALID}']):
            value=copy.deepcopy(self.value);value['operations'][0]['route']=route;self.withheld(value)
    def test_nested_duplicate_ids_and_field_slots_are_refused_as_whole_operation(self):
        for field in ('request_fields','responses'):
            value=copy.deepcopy(self.value);value['operations'][0][field].append(copy.deepcopy(value['operations'][0][field][0]));out=self.withheld(value);self.assertEqual(out['counts']['operations']['rejected_rows'],1)
        self.value['operations'][0]['request_fields'].append(dict(self.value['operations'][0]['request_fields'][0],id='alias'));self.withheld()
    def test_query_and_header_rules_require_strings_and_custom_header_names(self):
        for change in ({'type':'integer','min_length':None,'max_length':None,'choices':[]},{'name':'content-type'}):
            value=copy.deepcopy(self.value);value['operations'][0]['request_fields'][0].update(change);self.withheld(value)
    def test_status_slots_and_head_body_constraints_are_explicit(self):
        value=copy.deepcopy(self.value);value['operations'][0]['responses'].append(dict(value['operations'][0]['responses'][0],id='status-alias'));self.withheld(value)
        self.value['operations'][0].update(method='HEAD',request_media_type=None,request_fields=[v for v in self.value['operations'][0]['request_fields'] if v['location']!='body']);self.withheld()
    def test_get_head_options_request_body_and_bodyless_statuses_are_bounded(self):
        for method in ('GET','HEAD','OPTIONS'):
            value=copy.deepcopy(self.value);value['operations'][0]['method']=method;self.withheld(value)
        for status in (204,205,304):
            value=copy.deepcopy(self.value);value['operations'][0]['responses'][0]['status']=status;self.withheld(value)
    def test_choices_normalize_and_cannot_exceed_declared_string_limits(self):
        before=self.run_value();self.value['operations'][0]['request_fields'][1]['choices'].reverse();self.assertEqual(before['operations_sha256'],self.run_value()['operations_sha256']);self.value['operations'][0]['request_fields'][1]['max_length']=1;self.withheld()
    def test_invalid_numeric_rules_and_boolean_coercion_are_refused(self):
        for change in ({'maximum':0},{'minimum':True},{'choices':['1']}):
            value=copy.deepcopy(self.value);value['operations'][0]['request_fields'][3].update(change);self.withheld(value)
    def test_fieldless_bodyless_operation_is_an_explicit_supported_contract(self):
        operation=self.value['operations'][0];operation.update(method='GET',route=['health-preview'],request_media_type=None,request_fields=[],responses=[dict(id='no-content',status=204,media_type=None,request_valid=True,fields=[])]);self.assertEqual(self.run_value()['status'],'PASS')
    def test_operation_limit_and_empty_cohort_never_silently_truncate(self):
        value=copy.deepcopy(self.value);value['operations']=[];self.withheld(value);self.value['operations']=[dict(self.value['operations'][0],id='operation-'+str(i)) for i in range(129)]
        with self.assertRaisesRegex(t.Rejected,'OPERATION_LIMIT'):self.run_value()
