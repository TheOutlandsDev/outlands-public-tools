import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import reachability as app
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
        for key in ['manifests', 'links', 'plans']:self.value[key].reverse()
        self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_identical_top_level_rows_collapse_with_complete_accounting(self):
        for key in ['manifests', 'links', 'plans']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));out=self.run_value(v);self.assertEqual(out['status'],'PASS');counts=out['counts'][key];self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[n] for n in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_excludes_every_member(self):
        for key in ['manifests', 'links', 'plans']:
            v=copy.deepcopy(self.value);row=copy.deepcopy(v[key][0]);row['revision']+=1;v[key].extend([row,copy.deepcopy(v[key][0])]);out=self.withheld(v);self.assertEqual(out['counts'][key]['conflict_rows'],3)
    def test_unknown_fields_bad_rows_and_values_are_fixed_diagnostics(self):
        for key in ['manifests', 'links', 'plans']:
            for bad in (None,dict(id='SYNTHETIC_SENTINEL'),dict(self.value[key][0],extra='SYNTHETIC_SENTINEL')):
                v=copy.deepcopy(self.value);v[key].append(bad);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld(v)))
    def test_raw_cohort_limits_are_not_silently_truncated(self):
        for key in ['manifests', 'links', 'plans']:
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
        v=copy.deepcopy(self.value);v['manifests']=[];self.withheld(v)

    def graph(self,out=None):return (out or self.run_value())['assessment']['plans'][0]['graph']
    def test_hvac_known_reachable_pages_dead_end_and_edge_count(self):
        g=self.graph();self.assertEqual(g['reachable_pages'],['home-page','parts-page','service-page']);self.assertEqual(g['unreachable_pages'],[]);self.assertEqual(g['dead_end_pages'],['service-page']);self.assertEqual(g['unique_edge_count'],2)
    def test_starting_at_alias_resolves_before_reachability(self):
        self.value['plans'][0]['starts']=['old-parts'];g=self.graph(self.review());self.assertEqual(g['start_pages'],['parts-page']);self.assertEqual(g['unreachable_pages'],['home-page'])
    def test_disconnected_declared_page_is_reported(self):
        self.value['manifests'][0]['routes'].append(dict(id='extra',path='/extra',kind='page',page='extra-page',redirect_to=None,anchors=[]));self.repin();self.assertEqual(self.graph(self.review())['unreachable_pages'],['extra-page'])
    def test_broken_targets_withhold_graph_without_fabricating_reachability(self):
        self.value['links'][0]['target_path']='/missing';self.repin();out=self.review();plan=out['assessment']['plans'][0];self.assertFalse(plan['complete']);self.assertIsNone(plan['graph'])
    def test_stale_complete_link_cohort_pin_refuses_added_or_removed_links(self):
        self.value['links'].pop();self.withheld();self.repin();self.assertEqual(self.graph(self.review())['unreachable_pages'],['service-page'])
    def test_zero_edges_single_page_is_complete_and_dead_end_is_not_failure(self):
        self.value['manifests'][0]['routes']=[dict(id='home',path='/',kind='page',page='home-page',redirect_to=None,anchors=[])];self.value['links']=[];self.repin();g=self.graph();self.assertEqual(g['reachable_pages'],['home-page']);self.assertEqual(g['dead_end_pages'],['home-page'])
    def test_ordinary_navigation_cycles_are_reported_without_redirect_cycle_claim(self):
        row=copy.deepcopy(self.value['links'][0]);row.update(id='service-home',source='service',target_path='/',fragment=None);self.value['links'].append(row);self.repin();g=self.graph();self.assertEqual(g['navigation_cycles'],[['home-page','parts-page','service-page']]);self.assertEqual(g['dead_end_pages'],[])
    def test_self_link_and_duplicate_edges_have_deterministic_graph_meaning(self):
        row=copy.deepcopy(self.value['links'][0]);row.update(id='self',source='home',target_path='/',fragment=None);self.value['links'].extend([row,dict(self.value['links'][0],id='parallel')]);self.repin();g=self.graph();self.assertEqual(g['navigation_cycles'],[['home-page']]);self.assertEqual(g['unique_edge_count'],3)
    def test_unknown_empty_duplicate_and_too_many_starts_refuse(self):
        for starts in ([],['missing'],['home','home'],['home']*33):
            v=copy.deepcopy(self.value);v['plans'][0]['starts']=starts;self.withheld(v)
    def test_multiple_starts_union_reachability(self):
        self.value['links']=[];self.value['plans'][0]['starts']=['home','parts','service'];self.repin();self.assertEqual(self.graph()['reachable_pages'],['home-page','parts-page','service-page'])
    def test_links_order_and_top_level_duplicate_do_not_change_plan_binding(self):
        before=self.run_value();self.value['links'].reverse();self.value['links'].append(copy.deepcopy(self.value['links'][0]));self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_each_plan_must_pin_the_whole_selected_manifest_and_link_cohort(self):
        for key in ('manifest_sha256','links_sha256'):
            v=copy.deepcopy(self.value);v['plans'][0][key]='0'*64;self.withheld(v)
