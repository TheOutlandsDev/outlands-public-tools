import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import routes as app
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
        for key in ['manifests']:self.value[key].reverse()
        self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_identical_top_level_rows_collapse_with_complete_accounting(self):
        for key in ['manifests']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));out=self.run_value(v);self.assertEqual(out['status'],'PASS');counts=out['counts'][key];self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[n] for n in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_excludes_every_member(self):
        for key in ['manifests']:
            v=copy.deepcopy(self.value);row=copy.deepcopy(v[key][0]);row['revision']+=1;v[key].extend([row,copy.deepcopy(v[key][0])]);out=self.withheld(v);self.assertEqual(out['counts'][key]['conflict_rows'],3)
    def test_unknown_fields_bad_rows_and_values_are_fixed_diagnostics(self):
        for key in ['manifests']:
            for bad in (None,dict(id='SYNTHETIC_SENTINEL'),dict(self.value[key][0],extra='SYNTHETIC_SENTINEL')):
                v=copy.deepcopy(self.value);v[key].append(bad);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld(v)))
    def test_raw_cohort_limits_are_not_silently_truncated(self):
        for key in ['manifests']:
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

    def manifest(self):return self.value['manifests'][0]
    def test_known_hvac_page_and_alias_counts(self):
        out=self.run_value()['assessment']['manifests'][0];self.assertEqual((out['page_count'],out['redirect_count']),(3,1));self.assertEqual(out['sha256'],pin(r.manifest(self.manifest())[1]))
    def test_route_and_anchor_order_are_normalized(self):
        m=self.manifest();next(v for v in m['routes'] if v['id']=='parts')['anchors']=['filters','motors'];before=self.run_value();m['routes'].reverse()
        for row in m['routes']:row['anchors'].reverse()
        self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_duplicate_paths_even_across_page_and_redirect_are_refused(self):
        m=self.manifest();next(v for v in m['routes'] if v['id']=='old-parts')['path']='/parts';self.withheld()
    def test_duplicate_page_ids_and_nested_route_ids_are_refused(self):
        v=copy.deepcopy(self.value);next(r for r in v['manifests'][0]['routes'] if r['id']=='parts')['page']='home-page';self.withheld(v);self.manifest()['routes'].append(copy.deepcopy(self.manifest()['routes'][0]));self.withheld()
    def test_page_redirect_and_redirect_anchor_payloads_are_distinct(self):
        for field,value in [('page','other'),('anchors',['bad'])]:
            v=copy.deepcopy(self.value);next(r for r in v['manifests'][0]['routes'] if r['kind']=='redirect')[field]=value;self.withheld(v)
        next(v for v in self.manifest()['routes'] if v['kind']=='page')['redirect_to']='home';self.withheld()
    def test_unknown_redirect_and_self_cycle_are_refused(self):
        for target in ('missing','old-parts'):
            v=copy.deepcopy(self.value);next(r for r in v['manifests'][0]['routes'] if r['id']=='old-parts')['redirect_to']=target;self.withheld(v)
    def test_multihop_redirect_and_cycle_have_exact_semantics(self):
        m=self.manifest();m['routes'].append(dict(id='older',path='/older',kind='redirect',page=None,redirect_to='old-parts',anchors=[]));self.assertEqual(self.run_value()['status'],'PASS');self.assertEqual(r.chain(r.manifest(m)[1],'older')[1],['older','old-parts','parts']);next(v for v in m['routes'] if v['id']=='old-parts')['redirect_to']='older';self.withheld()
    def test_all_redirect_manifest_cannot_invent_a_terminal_page(self):
        self.manifest()['routes']=[dict(id='alias',path='/alias',kind='redirect',page=None,redirect_to='alias',anchors=[])];self.withheld()
    def test_duplicate_anchors_unknown_kind_and_extra_keys_refuse(self):
        for field,value in [('anchors',['filters','filters']),('kind','dynamic'),('extra','SYNTHETIC_SENTINEL')]:
            v=copy.deepcopy(self.value);v['manifests'][0]['routes'][0][field]=value;self.withheld(v)
    def test_literal_paths_have_no_implicit_slash_or_case_normalization(self):
        for path in ('/Parts','/parts/','/parts?mode=one','/parts%2fmore'):
            v=copy.deepcopy(self.value);v['manifests'][0]['routes'][0]['path']=path;self.withheld(v)
    def test_long_bounded_alias_chain_terminates_without_recursion(self):
        m=self.manifest();m['routes']=[dict(id='home',path='/',kind='page',page='home-page',redirect_to=None,anchors=[])]+[dict(id='alias-'+str(i),path='/alias-'+str(i),kind='redirect',page=None,redirect_to='home' if i==0 else 'alias-'+str(i-1),anchors=[]) for i in range(127)];self.assertEqual(self.run_value()['status'],'PASS');self.assertEqual(len(r.chain(r.manifest(m)[1],'alias-126')[1]),128)
    def test_untrusted_path_is_not_echoed_in_manifest_failure(self):
        self.manifest()['routes'][0]['path']='SYNTHETIC_SENTINEL';self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld()))
