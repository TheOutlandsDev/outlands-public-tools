import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import views as app
import view_core as r
def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(v):return hashlib.sha256(encode(v)).hexdigest()
class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,v=None):return app.check(encode(self.value if v is None else v))
    def review(self,v=None):
        out=self.run_value(v);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256']);return out
    def withheld(self,v=None):
        out=self.review(v);self.assertIsNone(out['assessment']);self.assertIsNone(out['cohort_sha256']);return out
    def repin(self):
        v=self.value;parsers={'views':r.view,'baseline_views':r.view,'candidate_views':r.view,'snapshots':r.snapshot,'projections':r.projection,'plans':r.plan}
        def select(cohort,id):return parsers[cohort](next(row for row in v[cohort] if row['id']==id))[1]
        for rows,refs in [('projections',[('view','views'),('snapshot','snapshots')]),('plans',[('projection','projections')]),('pages',[('plan','plans')]),('cases',[('baseline_view','baseline_views'),('candidate_view','candidate_views'),('snapshot','snapshots')])]:
            for row in v.get(rows,[]):
                for name,cohort in refs:
                    selected=select(cohort,row[name]);row.update({name+'_revision':selected['revision'],name+'_sha256':pin(selected)})
    def test_declarations_do_not_claim_sql_browser_execution_or_raw_values(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('execution_authorized','target_changes_performed','browser_started','dom_inspected','sql_executed','network_requests_performed','records_changed','raw_scalar_values_emitted','whole_view_compatibility_verified','content_privacy_verified'):self.assertIs(out[key],False)
    def test_outer_schema_format_float_nan_and_duplicate_keys_refuse(self):
        for value in ({},True,dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        for raw in (b'{"format":0,"format":1}',b'{"x":1.2}',b'{"x":NaN}'):
            with self.assertRaises(t.Rejected):app.check(raw)
    def test_raw_input_hash_determinism_and_semantic_pins(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out,app.check(raw));self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());other=app.check(json.dumps(self.value,indent=2).encode('ascii'));self.assertNotEqual(out['input_sha256'],other['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],other['qualified_scope_sha256'])
    def test_cohort_order_is_normalized(self):
        before=self.run_value()
        for key in ['views']:self.value[key].reverse()
        self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_identical_top_level_rows_preserve_duplicate_accounting(self):
        for key in ['views']:
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));out=self.run_value(v);self.assertEqual(out['status'],'PASS');counts=out['counts'][key];self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[n] for n in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_withhold_every_member(self):
        for key in ['views']:
            v=copy.deepcopy(self.value);row=copy.deepcopy(v[key][0]);row['revision']+=1;v[key].extend([row,copy.deepcopy(v[key][0])]);out=self.withheld(v);self.assertEqual(out['counts'][key]['conflict_rows'],3)
    def test_unknown_fields_and_bad_rows_omit_untrusted_values(self):
        for key in ['views']:
            for row in (None,dict(id='SYNTHETIC_SENTINEL'),dict(self.value[key][0],extra='SYNTHETIC_SENTINEL')):
                v=copy.deepcopy(self.value);v[key].append(row);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld(v)))
    def test_nonlist_and_raw_caps_are_fixed_refusals(self):
        for key in ['views']:
            for bad in (None,{},[{}]*513):
                v=copy.deepcopy(self.value);v[key]=bad
                with self.assertRaises(t.Rejected):self.run_value(v)
    def test_scalar_types_are_exact_and_nullability_explicit(self):
        for col,values in [(dict(type='integer',nullable=True),[True,'1',10**12+1]),(dict(type='boolean',nullable=False),[0,'true',None]),(dict(type='string',nullable=False),[True,1,'x'*257])]:
            for value in values:
                with self.assertRaises(t.Rejected):r.scalar(value,col)
        r.scalar(None,dict(type='integer',nullable=True));r.scalar(-10**12,dict(type='integer',nullable=False))
    def test_exact_revision_id_and_nullable_flags_are_required(self):
        base=dict(id='fictional',type='integer',nullable=False)
        for key,value in [('nullable',1),('type','float'),('id','')]:
            v=dict(base);v[key]=value
            with self.assertRaises(t.Rejected):r.column(v)
        for revision in (0,True,1000001):
            v=copy.deepcopy(self.value);v['views'][0]['revision']=revision;self.withheld(v)
    def test_sequence_coverage_retains_duplicates_missing_unexpected_and_order(self):
        out=r.sequence_check(['a','a','unknown'],['a','b']);self.assertEqual(out,dict(valid=False,missing_count=1,unexpected_count=1,duplicate_count=1,order_matches=False));self.assertFalse(r.sequence_check(['b','a'],['a','b'])['order_matches'])
    def test_empty_required_view_cohort_never_passes_vacuously(self):self.value['views']=[];self.withheld()

    def view(self):return self.value['views'][0]
    def test_known_columns_predicate_and_explicit_tie_breaker(self):
        out=self.run_value()['assessment']['views'][0];self.assertEqual((out['column_count'],out['predicate_count'],out['sort_fields'],out['id_order']),(3,1,['stock'],'asc'))
    def test_column_and_predicate_order_normalize_but_sort_priority_does_not(self):
        view=self.view();view['predicates'].append(dict(id='nonnegative',field='stock',op='ge',value=0));before=self.run_value();view['columns'].reverse();view['predicates'].reverse();self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256']);view['sort'].append(dict(field='name',direction='asc',nulls='first'));before=self.run_value();view['sort'].reverse();self.assertNotEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_sort_fields_are_unique_known_and_bounded(self):
        for rules in ([dict(field='missing',direction='asc',nulls='last')],self.view()['sort']*2,self.view()['sort']*9):
            v=copy.deepcopy(self.value);v['views'][0]['sort']=rules;self.withheld(v)
    def test_null_placement_direction_and_id_order_have_no_defaults(self):
        for key,value in [('nulls','automatic'),('direction','automatic')]:
            v=copy.deepcopy(self.value);v['views'][0]['sort'][0][key]=value;self.withheld(v)
        for value in (None,'automatic',True):self.view()['id_order']=value;self.withheld()
    def test_unknown_predicate_field_operator_and_boolean_order_refuse(self):
        for pred in (dict(id='p',field='missing',op='eq',value=True),dict(id='p',field='active',op='contains',value=True),dict(id='p',field='active',op='lt',value=True)):
            self.view()['predicates']=[pred];self.withheld()
    def test_null_predicates_require_null_operand_and_comparisons_require_nonnull(self):
        for pred in (dict(id='p',field='stock',op='eq',value=None),dict(id='p',field='stock',op='is_null',value=0)):
            v=copy.deepcopy(self.value);v['views'][0]['predicates']=[pred];self.withheld(v)
        self.view()['predicates']=[dict(id='p',field='stock',op='is_null',value=None)];self.assertEqual(self.run_value()['status'],'PASS')
    def test_predicate_operand_type_has_no_numeric_or_boolean_coercion(self):
        for value in (1,'true',[],{}):
            v=copy.deepcopy(self.value);v['views'][0]['predicates'][0]['value']=value;self.withheld(v)
    def test_duplicate_columns_and_predicate_ids_always_refuse(self):
        v=copy.deepcopy(self.value);v['views'][0]['columns']*=2;self.withheld(v);self.view()['predicates']*=2;self.withheld()
    def test_empty_predicates_and_sort_use_only_explicit_id_order(self):self.view()['predicates']=[];self.view()['sort']=[];self.assertEqual(self.run_value()['status'],'PASS')
    def test_column_and_predicate_raw_caps_refuse_without_truncation(self):
        for key,bad in [('columns',[]),('columns',self.view()['columns']*11),('predicates',self.view()['predicates']*17)]:
            v=copy.deepcopy(self.value);v['views'][0][key]=bad;self.withheld(v)
    def test_nonnullable_columns_can_use_explicit_null_tests(self):self.view()['predicates']=[dict(id='p',field='active',op='is_not_null',value=None)];self.assertEqual(self.run_value()['status'],'PASS')
    def test_predicate_values_are_not_echoed_in_success_or_failures(self):
        self.view()['predicates']=[dict(id='p',field='name',op='eq',value='SYNTHETIC_SENTINEL')];self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.run_value()));self.view()['predicates'][0]['field']='missing';self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld()))
