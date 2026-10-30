import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import submissions as app
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
        for key in ['forms_sha256', 'submissions_sha256']:self.assertIsNone(out[key])
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
        for path in [['forms'], ['submissions']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['forms_sha256', 'submissions_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['forms'], ['submissions']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['forms'], ['submissions']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['forms'], ['submissions']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['forms'], ['submissions']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['forms'], ['submissions']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['forms'], ['submissions']][0]).clear();self.withheld(value)


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

    def decisions(self,out=None):return {v['id']:v for v in (out or self.run_value())['assessment']['submissions'][0]['fields']}
    def test_known_visibility_requiredness_and_optional_absence(self):
        rows=self.decisions();self.assertEqual(rows['filter-grade'],dict(id='filter-grade',visible=True,required=True,state='valid'));self.assertEqual(rows['review-note']['state'],'optional_absent')
    def test_hidden_value_is_refused_instead_of_dropped(self):
        self.value['submissions'][0]['values']['equipment']='heat-pump';self.assertEqual(self.decisions(self.review())['filter-grade']['state'],'hidden_value_refused')
    def test_hidden_absence_does_not_demand_a_base_required_field(self):
        values=self.value['submissions'][0]['values'];values['equipment']='heat-pump';values.pop('filter-grade');self.assertEqual(self.decisions()['filter-grade'],dict(id='filter-grade',visible=False,required=False,state='hidden_absent'))
    def test_conditional_requirement_uses_boolean_without_coercion(self):
        self.value['submissions'][0]['values']['urgent']=True;self.assertEqual(self.decisions(self.review())['review-note']['state'],'missing_required');self.value['submissions'][0]['values']['review-note']='fictional review';self.assertEqual(self.run_value()['status'],'PASS')
    def test_invalid_parent_cannot_activate_child_rule(self):
        self.value['submissions'][0]['values']['urgent']=1;rows=self.decisions(self.review());self.assertEqual(rows['urgent']['state'],'type_invalid');self.assertFalse(rows['review-note']['required'])
    def test_unknown_and_missing_fields_are_accounted_without_value_or_name_echo(self):
        values=self.value['submissions'][0]['values'];values.pop('priority');values['unknown-private-key']='SYNTHETIC_VALUE_SENTINEL';out=self.review();self.assertEqual(out['assessment']['submissions'][0]['unknown_field_count'],1);self.assertEqual(self.decisions(out)['priority']['state'],'missing_required');self.assertNotIn('SYNTHETIC_VALUE_SENTINEL',json.dumps(out));self.assertNotIn('unknown-private-key',json.dumps(out))
    def test_exact_scalar_types_and_bounds_are_not_coerced(self):
        for value,state in [(True,'type_invalid'),('2','type_invalid'),(6,'out_of_range')]:
            item=copy.deepcopy(self.value);item['submissions'][0]['values']['priority']=value;self.assertEqual(self.decisions(self.review(item))['priority']['state'],state)
    def test_nested_null_float_and_array_values_are_unsupported(self):
        for value in (None,{},[],1.2):
            item=copy.deepcopy(self.value);item['submissions'][0]['values']['priority']=value
            if type(value) is float:
                with self.assertRaises(t.Rejected):self.run_value(item)
            else:self.withheld(item)
    def test_exact_form_selection_revision_and_snapshot_required(self):
        for change in ({'form':'other'},{'form_revision':2},{'form_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['submissions'][0].update(change);self.withheld(value)
    def test_optional_missing_parent_never_matches_a_condition(self):
        self.value['submissions'][0]['values'].pop('urgent');self.assertFalse(self.decisions()['review-note']['required'])
    def test_normalization_is_required_before_binding_snapshot(self):
        self.value['forms'][0]['fields'].reverse();self.repin();self.assertEqual(self.run_value()['status'],'PASS');self.value['submissions'][0]['form_sha256']=pin(self.value['forms'][0]);self.withheld()
    def test_expected_negative_does_not_clear_an_invalid_submission(self):
        self.value['submissions'][0]['values']['priority']=6;self.value['submissions'][0]['expected_valid']=False;row=self.review()['assessment']['submissions'][0];self.assertFalse(row['valid']);self.assertTrue(row['expectation_met'])
    def test_expectation_mismatch_requires_review_for_a_valid_submission(self):
        self.value['submissions'][0]['expected_valid']=False;row=self.review()['assessment']['submissions'][0];self.assertTrue(row['valid']);self.assertFalse(row['expectation_met'])
    def test_assessment_budget_is_bounded_before_evaluating_rows(self):
        self.value['forms'][0]['fields']=[dict(self.value['forms'][0]['fields'][2],id='field-'+str(i)) for i in range(32)];self.value['submissions']=[dict(self.value['submissions'][0],id='submission-'+str(i)) for i in range(257)];self.repin()
        with self.assertRaisesRegex(t.Rejected,'FIELD_ASSESSMENT_LIMIT'):self.run_value()
    def test_hidden_ancestor_cannot_activate_a_descendant(self):
        fields=self.value['forms'][0]['fields'];fields[3]['visible_when']=[dict(field='filter-grade',equals='standard')];values=self.value['submissions'][0]['values'];values['equipment']='heat-pump';values.pop('filter-grade');self.repin();self.assertEqual(self.decisions()['review-note']['state'],'hidden_absent')
    def test_no_defaults_are_inserted_and_inputs_are_unchanged(self):
        before=copy.deepcopy(self.value);self.run_value();self.assertEqual(self.value,before);self.assertNotIn('review-note',self.value['submissions'][0]['values'])
