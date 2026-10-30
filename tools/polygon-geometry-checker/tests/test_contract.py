import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import polygons as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['images_sha256', 'polygons_sha256']:self.assertIsNone(r[key])
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
        for key in ['images', 'polygons']:self.value[key].reverse()
        actual=self.run_value()
        for key in ['images_sha256', 'polygons_sha256']:self.assertEqual(actual[key],expected[key])
    def test_identical_identity_snapshots_never_inflate_counts(self):
        for key in ['images', 'polygons']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));r=self.run_value(v)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')),counts['input_rows'])
    def test_rejected_rows_withhold_and_omit_values(self):
        for key in ['images', 'polygons']:
            v=copy.deepcopy(self.value);v[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(v)
            self.assertEqual(r['counts'][key]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_row_limit_and_nonlist_refused(self):
        for key in ['images', 'polygons']:
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

    def geometry(self,points,review=False):
        self.value['polygons'][0]['vertices']=points;r=self.review() if review else self.run_value()
        if not review:self.assertEqual(r['status'],'PASS')
        return r['assessment']['polygons'][0]
    def test_rectangle_area_orientation_and_envelope_known_answer(self):
        a=self.run_value()['assessment']['polygons'][0];self.assertEqual(a['area'],dict(numerator=1600,denominator=2,exact_fraction='800/1'))
        self.assertEqual(a['orientation'],'clockwise');self.assertEqual(a['envelope'],dict(left=10,top=10,right=50,bottom=30));self.assertEqual(a['edge_contact_count'],0)
    def test_triangle_half_unit_area_is_exact(self):
        a=self.geometry([[0,0],[1,0],[0,1]]);self.assertEqual(a['area']['exact_fraction'],'1/2')
    def test_reversing_winding_preserves_area_and_flips_orientation(self):
        points=self.value['polygons'][0]['vertices'];a=self.geometry(list(reversed(points)));self.assertEqual(a['orientation'],'counterclockwise');self.assertEqual(a['area']['exact_fraction'],'800/1')
    def test_cyclic_vertex_rotation_preserves_geometry_but_not_literal_pin(self):
        before=self.run_value();points=self.value['polygons'][0]['vertices'];self.value['polygons'][0]['vertices']=points[1:]+points[:1];after=self.run_value()
        self.assertEqual(before['assessment']['polygons'][0]['area'],after['assessment']['polygons'][0]['area']);self.assertNotEqual(before['polygons_sha256'],after['polygons_sha256'])
    def test_concave_simple_polygon_is_valid(self):
        a=self.geometry([[0,0],[40,0],[40,40],[20,20],[0,40]]);self.assertEqual(a['area']['exact_fraction'],'1200/1')
    def test_collinear_redundant_vertex_without_backtracking_is_valid(self):
        self.geometry([[0,0],[20,0],[40,0],[40,40],[0,40]])
    def test_frame_edge_vertices_are_allowed(self):
        self.geometry([[0,0],[120,0],[120,80],[0,80]])
    def test_bowtie_intersection_and_zero_area_are_both_reported(self):
        a=self.geometry([[10,10],[50,30],[50,10],[10,30]],True);self.assertIn('EDGE_CONTACT',a['failed_criteria']);self.assertIn('AREA_ZERO',a['failed_criteria'])
    def test_nonadjacent_vertex_touch_is_not_simple(self):
        a=self.geometry([[0,0],[40,0],[40,40],[20,0],[0,40]],True);self.assertGreater(a['edge_contact_count'],0)
    def test_adjacent_backtracking_overlap_is_detected(self):
        a=self.geometry([[0,0],[40,0],[20,0],[40,40],[0,40]],True);self.assertTrue(any(x['kind']=='adjacent_overlap' for x in a['edge_contacts']))
    def test_nonadjacent_collinear_overlap_is_detected(self):
        a=self.geometry([[0,0],[40,0],[40,30],[10,30],[10,0],[30,0],[30,40],[0,40]],True);self.assertIn('EDGE_CONTACT',a['failed_criteria'])
    def test_explicit_closing_vertex_is_not_silently_removed(self):
        points=self.value['polygons'][0]['vertices'];a=self.geometry(points+[points[0]],True);self.assertEqual(a['vertex_count'],5);self.assertIn('VERTEX_REPEATED',a['failed_criteria']);self.assertIn('EDGE_ZERO_LENGTH',a['failed_criteria'])
    def test_outside_frame_geometry_retains_scope_with_review(self):
        a=self.geometry([[-1,0],[40,0],[40,40]],True);self.assertIn('VERTEX_OUTSIDE_FRAME',a['failed_criteria']);self.assertIsNotNone(self.run_value()['polygons_sha256'])
    def test_contact_list_is_capped_without_losing_total_count(self):
        a=self.geometry([[10,10]]*128,True);self.assertEqual(a['edge_contact_count'],8000);self.assertEqual(len(a['edge_contacts']),16);self.assertTrue(a['edge_contacts_truncated'])
    def test_maximum_simple_vertex_count_and_large_integer_area(self):
        points=[[i,0] for i in range(32)]+[[32,i] for i in range(32)]+[[32-i,32] for i in range(32)]+[[0,32-i] for i in range(32)]
        self.assertEqual(self.geometry(points)['area']['exact_fraction'],'1024/1')
        image=self.value['images'][0];image.update(width=1000000,height=1000000);self.value['polygons'][0]['image_snapshot_sha256']=pin(image)
        self.assertEqual(self.geometry([[0,0],[1000000,0],[1000000,1000000],[0,1000000]])['area']['exact_fraction'],'1000000000000/1')
    def test_malformed_vertex_counts_coordinates_and_nested_rings_reject_rows(self):
        for points in ([],[[0,0],[1,1]],[[0,0]]*129,[[0,0],[1,1],[True,2]],[[0,0],[1,1],[2000001,2]],[[[0,0],[1,1],[2,2]]]):
            v=copy.deepcopy(self.value);v['polygons'][0]['vertices']=points;self.withheld(v)
    def test_empty_polygons_unknown_reference_and_revision_conflict_withhold(self):
        for change in ({'image':'missing'},{'image_revision':2},{'image_snapshot_sha256':'0'*64}):
            v=copy.deepcopy(self.value);v['polygons'][0].update(change);self.withheld(v)
        self.value['polygons']=[];self.withheld()
    def test_total_vertex_budget_refuses_before_pairwise_analysis(self):
        a=self.value['polygons'][0];self.value['polygons']=[dict(a,id='polygon-'+str(i),vertices=[[j,0] for j in range(64)]) for i in range(65)]
        with self.assertRaisesRegex(t.Rejected,'TOTAL_VERTEX_LIMIT'):self.run_value()
    def test_segment_contacts_are_orientation_invariant_and_disjoint_is_false(self):
        import visual_core as v
        for a,b,p,q,want in [([0,0],[4,4],[0,4],[4,0],True),([0,0],[4,0],[4,0],[8,0],True),([0,0],[4,0],[5,0],[8,0],False),([0,0],[4,0],[1,0],[3,0],True)]:
            for x,y in ((a,b),(b,a)):
                for u,w in ((p,q),(q,p)):self.assertEqual(v.intersects(x,y,u,w),want)
