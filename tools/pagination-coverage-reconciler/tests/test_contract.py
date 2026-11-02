import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import pages as app
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
        for key in ['views', 'snapshots', 'projections', 'plans', 'pages']:self.value[key].reverse()
        self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_identical_top_level_rows_preserve_duplicate_accounting(self):
        for key in ['views', 'snapshots', 'projections', 'plans', 'pages']:
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));out=self.run_value(v);self.assertEqual(out['status'],'PASS');counts=out['counts'][key];self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[n] for n in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_withhold_every_member(self):
        for key in ['views', 'snapshots', 'projections', 'plans', 'pages']:
            v=copy.deepcopy(self.value);row=copy.deepcopy(v[key][0]);row['revision']+=1;v[key].extend([row,copy.deepcopy(v[key][0])]);out=self.withheld(v);self.assertEqual(out['counts'][key]['conflict_rows'],3)
    def test_unknown_fields_and_bad_rows_omit_untrusted_values(self):
        for key in ['views', 'snapshots', 'projections', 'plans', 'pages']:
            for row in (None,dict(id='SYNTHETIC_SENTINEL'),dict(self.value[key][0],extra='SYNTHETIC_SENTINEL')):
                v=copy.deepcopy(self.value);v[key].append(row);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld(v)))
    def test_nonlist_and_raw_caps_are_fixed_refusals(self):
        for key in ['views', 'snapshots', 'projections', 'plans', 'pages']:
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

    def result(self,out=None):return (out or self.run_value())['assessment']['plans'][0]
    def test_known_two_pages_complete_ordered_coverage(self):
        out=self.result();self.assertTrue(out['complete']);self.assertTrue(out['valid']);self.assertEqual(out['expected_page_count'],2);self.assertEqual(out['pages'][1]['expected_row_ids'],['motor','sensor'])
    def test_missing_page_retains_gap_and_withholds_global_coverage(self):self.value['pages'].pop();out=self.result(self.review());self.assertFalse(out['complete']);self.assertEqual(out['missing_indices'],[1]);self.assertIsNone(out['coverage'])
    def test_duplicate_page_slots_are_never_resolved_by_latest_or_first(self):self.value['pages'].append(dict(self.value['pages'][0],id='other'));out=self.result(self.review());self.assertEqual(out['duplicate_indices'],[0]);self.assertFalse(out['complete']);self.assertIsNone(out['coverage'])
    def test_unexpected_page_index_and_missing_page_are_separate(self):self.value['pages'][1]['index']=2;out=self.result(self.review());self.assertEqual(out['unexpected_indices'],[2]);self.assertEqual(out['missing_indices'],[1])
    def test_wrong_local_order_does_not_pass_even_with_exact_membership(self):
        self.value['pages'][0]['row_ids'].reverse();out=self.result(self.review());self.assertTrue(out['complete']);self.assertFalse(out['valid']);self.assertFalse(out['coverage']['order_matches'])
        self.setUp();self.value['pages'][0]['row_ids']=['filter-a'];self.value['pages'][1]['row_ids']=['filter-b','motor','sensor'];out=self.result(self.review());self.assertTrue(out['complete']);self.assertTrue(out['coverage']['valid']);self.assertFalse(out['valid'])
    def test_cross_page_duplicates_missing_rows_and_unexpected_ids_are_visible(self):self.value['pages'][1]['row_ids']=['filter-a','unknown'];out=self.result(self.review());self.assertEqual((out['coverage']['duplicate_count'],out['coverage']['missing_count'],out['coverage']['unexpected_count']),(1,2,1))
    def test_invalid_projection_withholds_page_conclusions_even_if_claims_match(self):
        self.value['projections'][0]['row_ids'].reverse();self.repin();out=self.result(self.review());self.assertFalse(out['complete']);self.assertIsNone(out['expected_page_count']);self.assertIsNone(out['pages']);self.assertIsNone(out['coverage'])
    def test_stale_plan_projection_or_page_bindings_withhold_all(self):
        for cohort,key in [('plans','projection_sha256'),('pages','plan_sha256')]:
            v=copy.deepcopy(self.value);v[cohort][0][key]='0'*64;self.withheld(v)
    def test_empty_projection_requires_one_explicit_empty_page(self):
        self.value['snapshots'][0]['rows']=[];self.value['projections'][0]['row_ids']=[];self.value['pages']=self.value['pages'][:1];self.value['pages'][0]['row_ids']=[];self.repin();self.assertTrue(self.result()['valid']);self.assertEqual(self.result()['expected_page_count'],1);self.value['pages']=[];self.assertFalse(self.result(self.review())['complete'])
    def test_page_size_change_requires_new_exact_page_binding(self):self.value['plans'][0]['page_size']=3;self.withheld();self.repin();out=self.result(self.review());self.assertFalse(out['valid']);self.assertEqual(out['pages'][0]['expected_row_ids'],['filter-a','filter-b','motor'])
    def test_page_size_index_and_row_list_bounds_refuse(self):
        for cohort,key,value in [('plans','page_size',0),('plans','page_size',True),('plans','page_size',129),('pages','index',True),('pages','index',512),('pages','row_ids',['filter-a']*129)]:
            v=copy.deepcopy(self.value);v[cohort][0][key]=value;self.withheld(v)
    def test_page_cohort_order_and_identical_duplicate_observation_normalize(self):
        before=self.run_value();self.value['pages'].reverse();self.value['pages'].append(copy.deepcopy(self.value['pages'][0]));self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
