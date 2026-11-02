import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import projections as app
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
        for key in ['views', 'snapshots', 'projections']:self.value[key].reverse()
        self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_identical_top_level_rows_preserve_duplicate_accounting(self):
        for key in ['views', 'snapshots', 'projections']:
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));out=self.run_value(v);self.assertEqual(out['status'],'PASS');counts=out['counts'][key];self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[n] for n in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_withhold_every_member(self):
        for key in ['views', 'snapshots', 'projections']:
            v=copy.deepcopy(self.value);row=copy.deepcopy(v[key][0]);row['revision']+=1;v[key].extend([row,copy.deepcopy(v[key][0])]);out=self.withheld(v);self.assertEqual(out['counts'][key]['conflict_rows'],3)
    def test_unknown_fields_and_bad_rows_omit_untrusted_values(self):
        for key in ['views', 'snapshots', 'projections']:
            for row in (None,dict(id='SYNTHETIC_SENTINEL'),dict(self.value[key][0],extra='SYNTHETIC_SENTINEL')):
                v=copy.deepcopy(self.value);v[key].append(row);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld(v)))
    def test_nonlist_and_raw_caps_are_fixed_refusals(self):
        for key in ['views', 'snapshots', 'projections']:
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

    def result(self,out=None):return (out or self.run_value())['assessment']['projections'][0]
    def expected(self):return r.evaluate(r.view(self.value['views'][0])[1],r.snapshot(self.value['snapshots'][0])[1])
    def test_hvac_filter_descending_nulls_last_and_id_tie_break(self):self.assertEqual(self.result()['expected_row_ids'],['filter-a','filter-b','motor','sensor'])
    def test_wrong_order_preserves_coverage_but_never_passes(self):
        self.value['projections'][0]['row_ids'].reverse();out=self.result(self.review());self.assertEqual((out['missing_count'],out['unexpected_count'],out['duplicate_count']),(0,0,0));self.assertFalse(out['order_matches'])
    def test_duplicate_missing_and_unexpected_row_ids_are_all_accounted(self):
        self.value['projections'][0]['row_ids']=['filter-a','filter-a','untrusted'];out=self.result(self.review());self.assertEqual((out['missing_count'],out['unexpected_count'],out['duplicate_count']),(3,1,1));self.assertNotIn('untrusted',json.dumps(out))
    def test_descending_sort_does_not_reverse_explicit_null_placement(self):
        v=self.value['views'][0];v['sort'][0]['nulls']='first';self.assertEqual(self.expected(),['sensor','filter-a','filter-b','motor']);v['sort'][0]['direction']='asc';self.assertEqual(self.expected(),['sensor','motor','filter-a','filter-b'])
    def test_id_tie_breaker_is_explicit_and_independent_of_source_order(self):
        before=self.expected();self.value['snapshots'][0]['rows'].reverse();self.assertEqual(before,self.expected());self.value['views'][0]['id_order']='desc';self.assertEqual(self.expected(),['filter-b','filter-a','motor','sensor'])
    def test_null_ne_comparison_is_false_and_requires_explicit_null_operator(self):
        v=self.value['views'][0];v['predicates']=[dict(id='p',field='stock',op='ne',value=8)];self.assertEqual(self.expected(),['old-kit','motor']);v['predicates']=[dict(id='p',field='stock',op='is_null',value=None)];self.assertEqual(self.expected(),['sensor'])
    def test_bool_sort_and_all_six_integer_comparisons_have_known_answers(self):
        for op,want in [('eq',['filter-a','filter-b']),('ne',['old-kit','motor']),('lt',['motor']),('le',['filter-a','filter-b','motor']),('gt',['old-kit']),('ge',['old-kit','filter-a','filter-b'])]:
            self.value['views'][0]['predicates']=[dict(id='p',field='stock',op=op,value=8)];self.assertEqual(self.expected(),want)
        v=self.value['views'][0];v['predicates']=[];v['sort']=[dict(field='active',direction='asc',nulls='last')];self.assertEqual(self.expected()[0],'old-kit')
    def test_snapshot_schema_values_and_nested_ids_are_strict(self):
        for change in ('missing','extra','bool','duplicate'):
            v=copy.deepcopy(self.value);s=v['snapshots'][0]
            if change=='missing':s['rows'][0]['values'].pop('stock')
            elif change=='extra':s['rows'][0]['values']['unknown']=0
            elif change=='bool':s['rows'][0]['values']['stock']=True
            else:s['rows'].append(copy.deepcopy(s['rows'][0]))
            self.withheld(v)
    def test_stale_pins_and_column_contract_mismatch_withhold_scope(self):
        for key in ('view_sha256','snapshot_sha256'):
            v=copy.deepcopy(self.value);v['projections'][0][key]='0'*64;self.withheld(v)
        self.value['views'][0]['columns'][1]['nullable']=True;self.repin();self.withheld()
    def test_empty_snapshot_and_empty_projection_are_explicit_valid_cases(self):self.value['snapshots'][0]['rows']=[];self.value['projections'][0]['row_ids']=[];self.repin();self.assertTrue(self.result()['valid'])
    def test_snapshot_order_normalizes_and_raw_values_never_enter_report(self):
        before=self.run_value();self.value['snapshots'][0]['rows'].reverse();self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256']);self.assertNotIn('Standard filter',json.dumps(before))
    def test_text_comparison_is_case_sensitive_codepoint_order_without_numeric_inference(self):
        v=self.value['views'][0];v['predicates']=[];v['sort']=[dict(field='name',direction='asc',nulls='last')];s=self.value['snapshots'][0];s['rows']=s['rows'][:3]
        for row,name in zip(s['rows'],['2','10','A']):row['values']['name']=name
        self.assertEqual(self.expected(),['filter-b','filter-a','motor'])
