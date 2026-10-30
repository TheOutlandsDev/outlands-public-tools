import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import handoff as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['images_sha256', 'annotations_sha256', 'taxonomy_sha256', 'categories_sha256', 'handoff_sha256', 'selected_annotations_sha256']:self.assertIsNone(r[key])
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
        for key in ['images', 'annotations', 'categories', 'approvals']:self.value[key].reverse()
        actual=self.run_value()
        for key in ['images_sha256', 'annotations_sha256', 'taxonomy_sha256', 'categories_sha256', 'handoff_sha256', 'selected_annotations_sha256']:self.assertEqual(actual[key],expected[key])
    def test_identical_identity_snapshots_never_inflate_counts(self):
        for key in ['images', 'annotations', 'categories', 'approvals']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));r=self.run_value(v)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')),counts['input_rows'])
    def test_rejected_rows_withhold_and_omit_values(self):
        for key in ['images', 'annotations', 'categories', 'approvals']:
            v=copy.deepcopy(self.value);v[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(v)
            self.assertEqual(r['counts'][key]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_row_limit_and_nonlist_refused(self):
        for key in ['images', 'annotations', 'categories', 'approvals']:
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

    def pin_plan(self):
        h=self.value['handoff'];taxonomy=copy.deepcopy(self.value['taxonomy']);taxonomy['labels'].sort()
        for key in ('images','annotations','categories'):h[key+'_sha256']=pin(sorted(self.value[key],key=lambda r:r['id']))
        h['taxonomy_sha256']=pin(taxonomy)
    def test_exact_selected_counts_mapping_and_pin(self):
        r=self.run_value();a=r['assessment'];self.assertTrue(a['eligible_for_manual_export_review']);self.assertEqual((a['images'],a['annotations']),(2,2))
        self.assertEqual(a['label_to_index'],{'fan-panel':0,'filter-panel':1});self.assertEqual(r['selected_annotations_sha256'],pin(self.value['annotations']));self.assertFalse(r['geometry_verified'])
    def test_subset_counts_refer_to_selected_images_and_annotations(self):
        self.value['handoff'].update(selected_annotations=['annotation-alpha'],expected_images=1,expected_annotations=1,expected_label_counts={'fan-panel':0,'filter-panel':1})
        a=self.run_value()['assessment'];self.assertTrue(a['eligible_for_manual_export_review']);self.assertEqual(a['selected_images'],['panel-alpha'])
    def test_missing_and_rejected_approvals_retain_diagnostics_without_selected_pin(self):
        self.value['approvals'].pop();self.value['approvals'][0]['decision']='reject';r=self.review()
        self.assertEqual(r['assessment']['missing_approvals'],['annotation-bravo']);self.assertEqual(r['assessment']['rejected_approvals'],['annotation-alpha']);self.assertIsNone(r['selected_annotations_sha256'])
    def test_all_count_mismatches_are_visible(self):
        self.value['handoff'].update(expected_images=1,expected_annotations=3,expected_label_counts={'fan-panel':2,'filter-panel':1});a=self.review()['assessment']
        self.assertEqual(a['failed_criteria'],['IMAGE_COUNT_MISMATCH','ANNOTATION_COUNT_MISMATCH','LABEL_COUNTS_MISMATCH'])
    def test_distinct_approval_ids_for_one_annotation_are_ambiguous(self):
        self.value['approvals'].append(dict(self.value['approvals'][0],id='approval-extra'));self.withheld()
    def test_stale_annotation_revision_hash_or_unknown_approval_withholds(self):
        for change in ({'annotation':'missing'},{'annotation_revision':2},{'annotation_sha256':'0'*64}):
            v=copy.deepcopy(self.value);v['approvals'][0].update(change);self.withheld(v)
    def test_geometry_or_label_change_invalidates_full_snapshot_approval(self):
        self.value['annotations'][0]['geometry'][0]=[11,10];self.pin_plan();self.withheld()
        self.value['annotations'][0]['label']='fan-panel';self.pin_plan();self.withheld()
    def test_every_source_scope_pin_is_checked(self):
        for key in ('images_sha256','annotations_sha256','taxonomy_sha256','categories_sha256'):
            v=copy.deepcopy(self.value);v['handoff'][key]='0'*64;self.withheld(v)
    def test_unknown_selection_is_not_dropped(self):
        self.value['handoff']['selected_annotations'].append('missing');self.withheld()
    def test_duplicate_selection_or_empty_selection_is_fixed_refusal(self):
        for selected in ([],['annotation-alpha','annotation-alpha']):
            self.value['handoff']['selected_annotations']=selected
            with self.assertRaises(t.Rejected):self.run_value()
    def test_category_label_or_index_collisions_withhold(self):
        for change in ({'index':0},{'label':'fan-panel'},{'label':'other'}):
            v=copy.deepcopy(self.value);v['categories'][1].update(change);self.withheld(v)
    def test_category_coverage_requires_unselected_labels_too(self):
        self.value['categories'].pop();self.pin_plan();self.withheld()
    def test_sparse_category_indexes_are_explicit_and_allowed(self):
        self.value['categories'][1]['index']=7;self.pin_plan();self.assertEqual(self.run_value()['assessment']['label_to_index']['filter-panel'],7)
    def test_unused_approval_is_still_validated_for_staleness(self):
        self.value['handoff'].update(selected_annotations=['annotation-alpha'],expected_images=1,expected_annotations=1,expected_label_counts={'fan-panel':0,'filter-panel':1})
        self.value['approvals'][1]['annotation_revision']=2;self.withheld()
    def test_geometry_alignment_is_not_granted_by_pinned_approval(self):
        self.value['annotations'][0]['geometry']=[[0,0],[40,40],[40,0],[0,40]]
        self.value['approvals'][0]['annotation_sha256']=pin(self.value['annotations'][0]);self.pin_plan()
        r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertFalse(r['geometry_verified']);self.assertFalse(r['content_geometry_alignment_verified'])
    def test_handoff_revision_counts_and_label_map_types_are_fixed_refusals(self):
        for change in ({'revision':True},{'expected_images':True},{'expected_annotations':0},{'expected_label_counts':{'fan-panel':1}},{'expected_label_counts':{'fan-panel':True,'filter-panel':1}},{'extra':0}):
            v=copy.deepcopy(self.value);v['handoff'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)
    def test_category_index_boolean_negative_and_out_of_bounds_reject_rows(self):
        for index in (True,-1,256,'0'):
            v=copy.deepcopy(self.value);v['categories'][0]['index']=index;self.withheld(v)
    def test_unknown_stale_annotation_and_empty_scope_withhold(self):
        v=copy.deepcopy(self.value);v['annotations'][0]['image']='missing';self.withheld(v)
        self.value['annotations']=[];self.withheld()
