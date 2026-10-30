import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import boxes as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['images_sha256', 'boxes_sha256']:self.assertIsNone(r[key])
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
        for key in ['images', 'boxes']:self.value[key].reverse()
        actual=self.run_value()
        for key in ['images_sha256', 'boxes_sha256']:self.assertEqual(actual[key],expected[key])
    def test_identical_identity_snapshots_never_inflate_counts(self):
        for key in ['images', 'boxes']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));r=self.run_value(v)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')),counts['input_rows'])
    def test_rejected_rows_withhold_and_omit_values(self):
        for key in ['images', 'boxes']:
            v=copy.deepcopy(self.value);v[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(v)
            self.assertEqual(r['counts'][key]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_row_limit_and_nonlist_refused(self):
        for key in ['images', 'boxes']:
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

    def box(self,source,target='pixel-xyxy',review=False):
        self.value['boxes'][0].update(source=source,target=target);r=self.review() if review else self.run_value()
        if not review:self.assertEqual(r['status'],'PASS')
        return r['assessment']['boxes'][0]
    def test_known_normalized_center_fractions(self):
        a=self.run_value()['assessment']['boxes'][0];self.assertEqual(a['converted_values'],['1/4','1/4','1/3','1/4']);self.assertEqual(a['pixel_edges'],['10/1','10/1','50/1','30/1'])
    def test_xyxy_to_xywh_and_back_are_exact(self):
        a=self.box(dict(format='pixel-xyxy',values=[10,10,50,30]),'pixel-xywh');self.assertEqual(a['converted_values'],[10,10,40,20])
        b=self.box(dict(format='pixel-xywh',values=a['converted_values']));self.assertEqual(b['converted_values'],[10,10,50,30])
    def test_normalized_fraction_round_trip_recovers_integer_edges(self):
        a=self.box(dict(format='unit-cxcywh',values=['1/4','1/4','1/3','1/4']));self.assertEqual(a['converted_values'],[10,10,50,30])
    def test_full_frame_has_center_half_and_unit_extents(self):
        a=self.box(dict(format='pixel-xyxy',values=[0,0,120,80]),'unit-cxcywh');self.assertEqual(a['converted_values'],['1/2','1/2','1/1','1/1'])
    def test_one_pixel_box_does_not_use_inclusive_endpoint_adjustment(self):
        a=self.box(dict(format='pixel-xyxy',values=[0,0,1,1]),'pixel-xywh');self.assertEqual(a['converted_values'],[0,0,1,1])
    def test_nonintegral_edges_withhold_only_conversion_and_never_round(self):
        a=self.box(dict(format='unit-cxcywh',values=['1/2','1/2','1/7','1/4']),review=True)
        self.assertIn('NONINTEGRAL_PIXEL_EDGES',a['failed_criteria']);self.assertIsNone(a['converted_values']);self.assertFalse(self.run_value()['coordinates_rounded'])
    def test_normalized_center_inside_frame_can_still_have_outside_edges(self):
        a=self.box(dict(format='unit-cxcywh',values=['0/1','1/2','1/2','1/2']),review=True);self.assertIn('BOX_OUTSIDE_FRAME',a['failed_criteria'])
    def test_zero_area_negative_extent_and_outside_are_retained_findings(self):
        for source in [dict(format='pixel-xyxy',values=[10,10,10,30]),dict(format='pixel-xywh',values=[10,10,-5,20]),dict(format='pixel-xyxy',values=[0,0,121,80])]:
            a=self.box(source,review=True);self.assertIsNone(a['converted_values']);self.assertIsNotNone(self.run_value()['boxes_sha256'])
    def test_all_outside_edges_are_reported_even_for_reversed_box(self):
        a=self.box(dict(format='pixel-xyxy',values=[121,0,-1,20]),review=True);self.assertEqual(a['failed_criteria'],['BOX_AREA_NONPOSITIVE','BOX_OUTSIDE_FRAME'])
    def test_fraction_normalization_deduplicates_equivalent_snapshots(self):
        self.value['boxes'][0]['source']=dict(format='unit-cxcywh',values=['2/8','1/4','2/6','1/4'])
        a=copy.deepcopy(self.value['boxes'][0]);a['source']['values']=['1/4','2/8','1/3','2/8'];self.value['boxes'].append(a)
        r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(r['counts']['boxes']['duplicate_rows'],1)
    def test_invalid_fraction_syntax_denominators_ranges_and_coercion_reject_rows(self):
        for bad in ('0.5','1e-1','-1/4','01/4','1/0','2/1','1000000001/1000000001',True,None,{}):
            v=copy.deepcopy(self.value);v['boxes'][0]['source']=dict(format='unit-cxcywh',values=[bad,'1/4','1/3','1/4']);self.withheld(v)
    def test_pixel_integer_and_format_schemas_reject_ambiguity(self):
        for change in ({'source':{'format':'xyxy','values':[0,0,1,1]}},{'source':{'format':'pixel-xyxy','values':[0,0,True,1]}},{'source':{'format':'pixel-xyxy','values':[0,0,1]}},{'target':'auto'},{'target':[]}):
            v=copy.deepcopy(self.value);v['boxes'][0].update(change);self.withheld(v)
    def test_one_bad_geometry_does_not_hide_other_conversion_diagnostics(self):
        a=self.value['boxes'][0];self.value['boxes'].append(dict(a,id='box-bad',source=dict(format='pixel-xyxy',values=[0,0,0,1])))
        r=self.review();self.assertEqual(r['assessment']['converted_boxes'],1);self.assertTrue(r['assessment']['boxes'][0]['valid']);self.assertFalse(r['assessment']['boxes'][1]['valid'])
    def test_conflicting_box_identity_withholds_all_conversions(self):
        self.value['boxes'].append(dict(self.value['boxes'][0],target='pixel-xyxy'));self.withheld()
    def test_empty_boxes_and_unknown_image_withhold(self):
        v=copy.deepcopy(self.value);v['boxes'][0]['image']='missing';self.withheld(v)
        self.value['boxes']=[];self.withheld()
    def test_exact_game_geometry_example(self):
        value=json.loads((Path(__file__).resolve().parents[1]/'examples/game-boxes.json').read_text(encoding='utf-8'))
        self.assertEqual(self.run_value(value)['assessment']['boxes'][0]['converted_values'],['1/4','1/4','1/2','1/2'])
