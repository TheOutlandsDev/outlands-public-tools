import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import manifest as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['images_sha256', 'annotations_sha256', 'taxonomy_sha256']:self.assertIsNone(r[key])
        return r
    def test_fictional_positive_and_authority_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('artifact_bytes_verified','label_truth_verified','content_geometry_alignment_verified','approval_authenticity_verified','dataset_export_performed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_format_unknown_fields_and_duplicate_keys_refused(self):
        for v in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(v)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_does_not_change_scope_pins(self):
        expected=self.run_value()
        for key in ['images', 'annotations']:self.value[key].reverse()
        actual=self.run_value()
        for key in ['images_sha256', 'annotations_sha256', 'taxonomy_sha256']:self.assertEqual(actual[key],expected[key])
    def test_identical_identity_snapshots_never_inflate_counts(self):
        for key in ['images', 'annotations']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));r=self.run_value(v)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')),counts['input_rows'])
    def test_rejected_rows_withhold_and_omit_values(self):
        for key in ['images', 'annotations']:
            v=copy.deepcopy(self.value);v[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(v)
            self.assertEqual(r['counts'][key]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_row_limit_and_nonlist_refused(self):
        for key in ['images', 'annotations']:
            for value in (None,{},[{}]*1001):
                v=copy.deepcopy(self.value);v[key]=value
                with self.assertRaises(t.Rejected):self.run_value(v)
    def test_bad_image_dimensions_hash_and_revision_reject_rows(self):
        for change in ({'width':0},{'width':True},{'height':1000001},{'content_sha256':'A'*64},{'revision':0},{'extra':0}):
            v=copy.deepcopy(self.value);v['images'][0].update(change);self.withheld(v)
    def test_changed_image_dimensions_or_revision_invalidates_existing_reference(self):
        for change in ({'width':119},{'height':79},{'revision':2},{'content_sha256':'0'*64}):
            v=copy.deepcopy(self.value);v['images'][0].update(change);self.withheld(v)
    def test_conflicting_image_id_never_selects_latest(self):
        self.value['images'].append(dict(self.value['images'][0],revision=2));r=self.withheld();self.assertEqual(r['counts']['images']['conflict_rows'],2)
    def test_empty_images_withholds(self):
        self.value['images']=[];self.withheld()

    def test_complete_counts_and_independent_pin_oracles(self):
        r=self.run_value();self.assertEqual((r['assessment']['images'],r['assessment']['annotations']),(2,2))
        self.assertEqual(r['images_sha256'],pin(self.value['images']));self.assertEqual(r['annotations_sha256'],pin(self.value['annotations']))
        self.assertEqual(r['assessment']['label_counts'],{'fan-panel':1,'filter-panel':1});self.assertFalse(r['geometry_verified'])
    def test_unannotated_images_retain_scope_but_require_review(self):
        self.value['annotations'].pop();r=self.review();self.assertEqual(r['assessment']['unannotated_images'],['panel-bravo']);self.assertIsNotNone(r['images_sha256'])
    def test_empty_annotations_do_not_issue_partial_scope_pins(self):
        self.value['annotations']=[];self.withheld()
    def test_unknown_stale_image_taxonomy_and_label_references_withhold(self):
        for change in ({'image':'missing'},{'image_revision':2},{'image_snapshot_sha256':'0'*64},{'taxonomy_sha256':'0'*64},{'label':'other'}):
            v=copy.deepcopy(self.value);v['annotations'][0].update(change);self.withheld(v)
    def test_conflicting_annotation_revision_withholds_group(self):
        self.value['annotations'].append(dict(self.value['annotations'][0],revision=2));r=self.withheld();self.assertEqual(r['counts']['annotations']['conflict_rows'],2)
    def test_taxonomy_revision_change_requires_new_annotation_pin(self):
        self.value['taxonomy']['revision']=2;self.withheld()
    def test_shape_syntax_checks_but_geometry_is_not_claimed(self):
        self.value['annotations'][0]['geometry']=[[10,10],[50,30],[50,10],[10,30]]
        self.assertEqual(self.run_value()['status'],'PASS');self.assertFalse(self.run_value()['geometry_verified'])
    def test_malformed_geometry_and_unknown_kind_reject_rows(self):
        for change in ({'geometry':[[0,0],[1,1]]},{'geometry':[[0,False],[1,1],[2,2]]},{'geometry':{}},{'kind':'mask'},{'kind':[]},{'image_revision':True}):
            v=copy.deepcopy(self.value);v['annotations'][0].update(change);self.withheld(v)
    def test_box_requires_exact_fields_and_bounded_integer_edges(self):
        for geometry in ({'left':0,'top':0,'right':1},{'left':0,'top':0,'right':True,'bottom':1},{'left':0,'top':0,'right':2000001,'bottom':1}):
            v=copy.deepcopy(self.value);v['annotations'][1]['geometry']=geometry;self.withheld(v)
    def test_total_polygon_vertex_budget_is_a_fixed_refusal(self):
        a=self.value['annotations'][0];self.value['annotations']=[dict(a,id='polygon-'+str(i),geometry=[[j,0] for j in range(64)]) for i in range(65)]
        with self.assertRaisesRegex(t.Rejected,'TOTAL_VERTEX_LIMIT'):self.run_value()
    def test_taxonomy_schema_is_fixed_refusal(self):
        for change in ({'revision':True},{'labels':[]},{'labels':['fan-panel','fan-panel']}):
            v=copy.deepcopy(self.value);v['taxonomy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)
