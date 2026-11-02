import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import scenarios as app
import navigation_core as r
def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(v):return hashlib.sha256(encode(v)).hexdigest()
class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,v=None):return app.check(encode(self.value if v is None else v))
    def review(self,v=None):
        out=self.run_value(v);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256']);return out
    def withheld(self,v=None):
        out=self.review(v);self.assertIsNone(out['assessment']);self.assertIsNone(out['cohort_sha256']);return out
    def repin(self,prefix=''):
        v=self.value;manifests={row['id']:r.manifest(row)[1] for row in v[prefix+'manifests']}
        for row in v.get(prefix+'links',[]):
            if row['manifest'] in manifests:row.update(manifest_revision=manifests[row['manifest']]['revision'],manifest_sha256=pin(manifests[row['manifest']]))
        for row in v.get('plans',[]):
            m=manifests[row['manifest']];group={link['id']:(i,link) for i,link in enumerate(v['links']) if link['manifest']==row['manifest']};row.update(manifest_revision=m['revision'],manifest_sha256=pin(m),links_sha256=r.c.cohort_pin(group))
    def test_supplied_declarations_do_not_authorize_execution_or_verify_browser(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('execution_authorized','target_changes_performed','browser_started','dom_inspected','network_requests_performed','records_changed','whole_site_compatibility_verified','accessibility_verified','content_privacy_verified'):self.assertIs(out[key],False)
    def test_outer_shape_format_float_and_duplicate_keys_refuse(self):
        for value in ({},True,dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        for raw in (b'{"format":0,"format":1}',b'{"x":1.2}',b'{"x":NaN}'):
            with self.assertRaises(t.Rejected):app.check(raw)
    def test_raw_hash_determinism_and_semantic_pins(self):
        raw=encode(self.value);before=app.check(raw);self.assertEqual(before,app.check(raw));self.assertEqual(before['input_sha256'],hashlib.sha256(raw).hexdigest());after=app.check(json.dumps(self.value,indent=2).encode('ascii'));self.assertNotEqual(before['input_sha256'],after['input_sha256']);self.assertEqual(before['qualified_scope_sha256'],after['qualified_scope_sha256'])
    def test_top_level_order_does_not_change_cohort_pins(self):
        before=self.run_value()
        for key in ['baseline_manifests', 'candidate_manifests', 'baseline_links', 'candidate_links']:self.value[key].reverse()
        self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_identical_top_level_rows_collapse_with_complete_accounting(self):
        for key in ['baseline_manifests', 'candidate_manifests', 'baseline_links', 'candidate_links']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));out=self.run_value(v);self.assertEqual(out['status'],'PASS');counts=out['counts'][key];self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[n] for n in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_excludes_every_member(self):
        for key in ['baseline_manifests', 'candidate_manifests', 'baseline_links', 'candidate_links']:
            v=copy.deepcopy(self.value);row=copy.deepcopy(v[key][0]);row['revision']+=1;v[key].extend([row,copy.deepcopy(v[key][0])]);out=self.withheld(v);self.assertEqual(out['counts'][key]['conflict_rows'],3)
    def test_unknown_fields_bad_rows_and_values_are_fixed_diagnostics(self):
        for key in ['baseline_manifests', 'candidate_manifests', 'baseline_links', 'candidate_links']:
            for bad in (None,dict(id='SYNTHETIC_SENTINEL'),dict(self.value[key][0],extra='SYNTHETIC_SENTINEL')):
                v=copy.deepcopy(self.value);v[key].append(bad);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld(v)))
    def test_raw_cohort_limits_are_not_silently_truncated(self):
        for key in ['baseline_manifests', 'candidate_manifests', 'baseline_links', 'candidate_links']:
            for bad in (None,{},[{}]*513):
                v=copy.deepcopy(self.value);v[key]=bad
                with self.assertRaises(t.Rejected):self.run_value(v)
    def test_paths_reject_external_encoded_ambiguous_and_relative_forms(self):
        for v in ('','parts','//parts','/parts/','/a//b','/a/../b','/a/./b','/a%2fb','/a?b','/a#b','/a\\b','https://example.invalid/a','/UPPER','/a b','/é',True,None,[],'/'+'/'.join(['a']*9)):
            with self.assertRaises(t.Rejected):r.path(v)
        self.assertEqual(r.path('/'),'/');self.assertEqual(r.path('/a-1/b_2'),'/a-1/b_2')
    def test_bounded_manifest_ids_and_exact_revisions(self):
        m=dict(id='fictional',revision=1,routes=[dict(id='home',path='/',kind='page',page='home-page',redirect_to=None,anchors=[])])
        for revision in (0,True,1000001):
            v=copy.deepcopy(m);v['revision']=revision
            with self.assertRaises(t.Rejected):r.manifest(v)
        for routes in ([],m['routes']*129):
            v=copy.deepcopy(m);v['routes']=routes
            with self.assertRaises(t.Rejected):r.manifest(v)
    def test_fragments_and_starts_require_unique_symbolic_ids(self):
        for value in (['same','same'],[''],[True],['ok']*33):
            with self.assertRaises(t.Rejected):r.ids(value,32)
    def test_missing_required_manifest_never_passes_vacuously(self):
        v=copy.deepcopy(self.value);v['baseline_manifests']=[];self.withheld(v)

    def first(self,out=None):return (out or self.run_value())['assessment']['links'][0]
    def test_new_revision_same_selected_outcomes_matches(self):self.assertTrue(self.first()['equal']);self.assertTrue(self.first()['comparable'])
    def test_changed_terminal_page_is_visible(self):
        row=next(v for v in self.value['candidate_manifests'][0]['routes'] if v['id']=='parts');row['page']='new-parts-page';self.repin('candidate_');out=self.first(self.review());self.assertEqual(out['state'],'outcome_changed');self.assertEqual(out['candidate']['page'],'new-parts-page')
    def test_same_manifest_revision_changed_definition_is_structural_conflict(self):
        m=self.value['candidate_manifests'][0];m['revision']=1;next(v for v in m['routes'] if v['id']=='parts')['page']='other-page';self.repin('candidate_');self.withheld()
    def test_missing_candidate_and_added_observation_never_pass(self):
        v=copy.deepcopy(self.value);v['candidate_links']=[];self.assertEqual(self.review(v)['assessment']['links'][0]['state'],'candidate_missing');self.value['candidate_links'].append(dict(self.value['candidate_links'][0],id='added'));rows=self.review()['assessment']['links'];self.assertEqual(next(v for v in rows if v['id']=='added')['state'],'baseline_missing')
    def test_changed_link_observation_is_incomparable_even_if_target_matches(self):
        self.value['candidate_links'][0]['target_path']='/parts';out=self.first(self.review());self.assertEqual(out['state'],'observation_changed');self.assertFalse(out['comparable']);self.assertIsNone(out['candidate'])
    def test_both_negative_outcomes_do_not_create_a_clean_comparison(self):
        for key in ('baseline_links','candidate_links'):self.value[key][0]['target_path']='/missing'
        out=self.first(self.review());self.assertTrue(out['comparable']);self.assertFalse(out['equal']);self.assertEqual(out['state'],'invalid_target')
    def test_changed_redirect_chain_matters_even_when_terminal_page_matches(self):
        m=self.value['candidate_manifests'][0];m['routes'].append(dict(id='middle',path='/middle',kind='redirect',page=None,redirect_to='parts',anchors=[]));next(v for v in m['routes'] if v['id']=='old-parts')['redirect_to']='middle';self.repin('candidate_');out=self.first(self.review());self.assertEqual(out['state'],'outcome_changed');self.assertEqual(out['baseline']['page'],out['candidate']['page'])
    def test_removed_terminal_fragment_is_invalid_candidate(self):
        next(v for v in self.value['candidate_manifests'][0]['routes'] if v['id']=='parts')['anchors']=[];self.repin('candidate_');self.assertEqual(self.first(self.review())['state'],'invalid_target')
    def test_unused_route_change_does_not_establish_whole_site_equivalence(self):
        self.value['candidate_manifests'][0]['routes'].append(dict(id='extra',path='/extra',kind='page',page='extra-page',redirect_to=None,anchors=[]));self.repin('candidate_');out=self.run_value();self.assertTrue(out['assessment']['all_selected_outcomes_equal']);self.assertFalse(out['whole_site_compatibility_verified'])
    def test_source_page_semantics_are_part_of_outcome(self):
        next(v for v in self.value['candidate_manifests'][0]['routes'] if v['id']=='home')['page']='new-home-page';self.repin('candidate_');self.assertEqual(self.first(self.review())['state'],'outcome_changed')
    def test_stale_candidate_reference_withholds_comparison(self):self.value['candidate_links'][0]['manifest_sha256']='0'*64;self.withheld()
    def test_empty_baseline_and_changed_observation_revision_are_not_equal(self):
        v=copy.deepcopy(self.value);v['baseline_links']=[];self.withheld(v);self.value['candidate_links'][0]['revision']=2;self.assertEqual(self.first(self.review())['state'],'observation_changed')
