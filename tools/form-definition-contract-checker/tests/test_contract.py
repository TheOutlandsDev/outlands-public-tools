import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import forms as app
import form_core as r

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
        for key in ['forms_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('browser_started','dom_inspected','scripts_executed','network_requests_performed','authentication_performed','records_changed','raw_values_emitted','content_privacy_verified','execution_authorized','target_changes_performed','accessibility_verified','whole_ui_compatibility_verified'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['forms']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['forms_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['forms']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['forms']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['forms']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['forms']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['forms']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['forms']][0]).clear();self.withheld(value)


    def repin(self,value=None,prefix=''):
        value=self.value if value is None else value
        def name(key):return prefix+'_'+key if prefix else key
        forms={v['id']:r.form(v)[1] for v in value[name('forms')]};flows={v['id']:v for v in value.get(name('flows'),[])};subs={v['id']:v for v in value.get(name('submissions'),[])}
        for row in [*flows.values(),*subs.values()]:
            if row['form'] in forms:row.update(form_revision=forms[row['form']]['revision'],form_sha256=pin(forms[row['form']]))
        for row in value.get(name('histories'),[]):
            if row['flow'] in flows:row.update(flow_revision=flows[row['flow']]['revision'],flow_sha256=pin(r.flow(flows[row['flow']])[1]))
            for item in row['events']:
                if item['submission'] in subs:item.update(submission_revision=subs[item['submission']]['revision'],submission_sha256=pin(subs[item['submission']]))

    def test_known_hvac_dependency_order(self):
        row=self.run_value()['assessment']['forms'][0];self.assertEqual(row['field_count'],5);self.assertEqual(row['evaluation_order'],['equipment','priority','urgent','filter-grade','review-note'])
    def test_self_dependency_is_not_a_visible_default(self):
        self.value['forms'][0]['fields'][0]['visible_when']=[dict(field='equipment',equals='air-handler')];self.withheld()
    def test_cycle_through_required_and_visibility_rules_is_refused(self):
        self.value['forms'][0]['fields'][0]['required_when']=[dict(field='filter-grade',equals='standard')];self.withheld()
    def test_unknown_condition_reference_and_duplicate_predicates_refuse_whole_form(self):
        for rules in ([dict(field='missing',equals=True)],[dict(field='equipment',equals='air-handler')]*2):
            value=copy.deepcopy(self.value);value['forms'][0]['fields'][1]['visible_when']=rules;self.withheld(value)
    def test_condition_literal_is_checked_against_exact_parent_type_and_rules(self):
        for literal in (1,'true',None):
            value=copy.deepcopy(self.value);value['forms'][0]['fields'][3]['required_when'][0]['equals']=literal;self.withheld(value)
        self.value['forms'][0]['fields'][1]['visible_when'][0]['equals']='other-equipment';self.withheld()
    def test_nested_duplicate_id_even_identical_is_not_collapsed(self):
        fields=self.value['forms'][0]['fields'];fields.append(copy.deepcopy(fields[0]));self.withheld()
    def test_missing_or_unknown_field_rule_is_not_inferred(self):
        for change in ('missing','extra'):
            value=copy.deepcopy(self.value);field=value['forms'][0]['fields'][0]
            if change=='missing':field.pop('required')
            else:field['default']='air-handler'
            self.withheld(value)
    def test_boolean_is_not_integer_limit_or_required_flag(self):
        value=copy.deepcopy(self.value);value['forms'][0]['fields'][2]['maximum']=True;self.withheld(value);self.value['forms'][0]['fields'][0]['required']=1;self.withheld()
    def test_reversed_limits_and_incompatible_rule_types_refuse(self):
        value=copy.deepcopy(self.value);value['forms'][0]['fields'][2].update(minimum=8,maximum=5);self.withheld(value);self.value['forms'][0]['fields'][4]['minimum']=0;self.withheld()
    def test_choices_are_unique_typed_and_within_length_rules(self):
        for choices in (['air-handler','air-handler'],[True],['air-handler']):
            value=copy.deepcopy(self.value);value['forms'][0]['fields'][0].update(choices=choices,max_length=3);self.withheld(value)
    def test_normalized_field_and_choice_order_produce_same_pin(self):
        before=self.run_value();self.value['forms'][0]['fields'].reverse()
        for field in self.value['forms'][0]['fields']:field['choices'].reverse()
        self.assertEqual(before['forms_sha256'],self.run_value()['forms_sha256'])
    def test_empty_or_oversized_nested_fields_refuse_whole_form(self):
        for fields in ([],[self.value['forms'][0]['fields'][0]]*33):
            value=copy.deepcopy(self.value);value['forms'][0]['fields']=fields;self.withheld(value)
    def test_raw_form_and_condition_caps_are_not_truncated(self):
        value=copy.deepcopy(self.value);value['forms']=[dict(value['forms'][0],id='form-'+str(i)) for i in range(65)]
        with self.assertRaisesRegex(t.Rejected,'COHORT_LIMIT'):self.run_value(value)
        self.value['forms'][0]['fields'][0]['visible_when']=[dict(field='urgent',equals=True)]*9;self.withheld()
    def test_optional_hidden_required_fields_are_explicit_declarations(self):
        self.value['forms'][0]['fields'][1]['required']=False;self.assertEqual(self.run_value()['status'],'PASS')
    def test_revision_is_positive_bounded_integer(self):
        for revision in (0,True,1000001):
            value=copy.deepcopy(self.value);value['forms'][0]['revision']=revision;self.withheld(value)
    def test_reports_do_not_emit_choice_or_condition_payload_values(self):
        out=json.dumps(self.run_value());self.assertNotIn('air-handler',out);self.assertNotIn('standard',out)
