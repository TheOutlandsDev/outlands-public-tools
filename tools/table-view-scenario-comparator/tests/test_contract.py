import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import scenarios as app
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
        for key in ['baseline_views', 'candidate_views', 'snapshots', 'cases']:self.value[key].reverse()
        self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_identical_top_level_rows_preserve_duplicate_accounting(self):
        for key in ['baseline_views', 'candidate_views', 'snapshots', 'cases']:
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));out=self.run_value(v);self.assertEqual(out['status'],'PASS');counts=out['counts'][key];self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[n] for n in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_withhold_every_member(self):
        for key in ['baseline_views', 'candidate_views', 'snapshots', 'cases']:
            v=copy.deepcopy(self.value);row=copy.deepcopy(v[key][0]);row['revision']+=1;v[key].extend([row,copy.deepcopy(v[key][0])]);out=self.withheld(v);self.assertEqual(out['counts'][key]['conflict_rows'],3)
    def test_unknown_fields_and_bad_rows_omit_untrusted_values(self):
        for key in ['baseline_views', 'candidate_views', 'snapshots', 'cases']:
            for row in (None,dict(id='SYNTHETIC_SENTINEL'),dict(self.value[key][0],extra='SYNTHETIC_SENTINEL')):
                v=copy.deepcopy(self.value);v[key].append(row);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld(v)))
    def test_nonlist_and_raw_caps_are_fixed_refusals(self):
        for key in ['baseline_views', 'candidate_views', 'snapshots', 'cases']:
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
            v=copy.deepcopy(self.value);v['baseline_views'][0]['revision']=revision;self.withheld(v)
    def test_sequence_coverage_retains_duplicates_missing_unexpected_and_order(self):
        out=r.sequence_check(['a','a','unknown'],['a','b']);self.assertEqual(out,dict(valid=False,missing_count=1,unexpected_count=1,duplicate_count=1,order_matches=False));self.assertFalse(r.sequence_check(['b','a'],['a','b'])['order_matches'])
    def test_empty_required_view_cohort_never_passes_vacuously(self):self.value['baseline_views']=[];self.withheld()

    def first(self,out=None):return (out or self.run_value())['assessment']['cases'][0]
    def test_equal_selected_order_and_page_windows_under_new_revision(self):out=self.first();self.assertTrue(out['equal']);self.assertEqual(out['baseline_pages'],[['filter-a','filter-b'],['motor','sensor']])
    def test_changed_sort_order_is_visible_with_same_membership(self):self.value['candidate_views'][0]['sort'][0]['direction']='asc';self.repin();out=self.first(self.review());self.assertEqual(set(out['baseline_row_ids']),set(out['candidate_row_ids']));self.assertNotEqual(out['baseline_pages'],out['candidate_pages'])
    def test_changed_filter_membership_is_visible(self):self.value['candidate_views'][0]['predicates']=[];self.repin();out=self.first(self.review());self.assertNotIn('old-kit',out['baseline_row_ids']);self.assertIn('old-kit',out['candidate_row_ids'])
    def test_same_view_id_revision_changed_definition_withholds(self):self.value['candidate_views'][0].update(revision=1,id_order='desc');self.repin();self.withheld()
    def test_changed_null_order_or_id_tie_breaker_cannot_hide(self):
        for change in ('nulls','tie'):
            self.setUp()
            if change=='nulls':self.value['candidate_views'][0]['sort'][0]['nulls']='first'
            else:self.value['candidate_views'][0]['id_order']='desc'
            self.repin();self.assertFalse(self.first(self.review())['equal'])
    def test_stale_case_view_or_snapshot_reference_withholds(self):
        for key in ('baseline_view_sha256','candidate_view_sha256','snapshot_sha256'):
            v=copy.deepcopy(self.value);v['cases'][0][key]='0'*64;self.withheld(v)
    def test_column_contract_change_is_not_a_comparable_reinterpretation(self):self.value['candidate_views'][0]['columns'][1]['nullable']=True;self.repin();self.withheld()
    def test_empty_record_snapshot_can_match_but_case_cohort_cannot_be_empty(self):self.value['snapshots'][0]['rows']=[];self.repin();out=self.first();self.assertEqual(out['baseline_pages'],[[]]);self.assertTrue(out['equal']);self.value['cases']=[];self.withheld()
    def test_unobserved_definition_change_only_establishes_selected_outcomes(self):self.value['candidate_views'][0]['predicates'].append(dict(id='present-name',field='name',op='is_not_null',value=None));self.repin();out=self.run_value();self.assertTrue(out['assessment']['all_selected_outcomes_equal']);self.assertFalse(out['whole_view_compatibility_verified'])
    def test_shared_page_size_is_pinned_and_derives_both_boundaries(self):self.value['cases'][0]['page_size']=3;out=self.first();self.assertEqual(out['baseline_pages'],[['filter-a','filter-b','motor'],['sensor']]);self.assertEqual(out['baseline_pages'],out['candidate_pages'])
    def test_snapshot_rows_and_columns_normalize_without_changing_scope(self):before=self.run_value();self.value['snapshots'][0]['rows'].reverse();self.value['snapshots'][0]['columns'].reverse();self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_invalid_typed_snapshot_never_becomes_equal_negative_outcomes(self):self.value['snapshots'][0]['rows'][0]['values']['stock']=True;self.withheld()
