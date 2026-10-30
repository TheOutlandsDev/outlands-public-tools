import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import partitions as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None,key='assessment'):
        result=self.run_value(value);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);return result
    def withheld(self,value=None):
        result=self.review(value);self.assertIsNone(result['assessment']);return result
    def test_fictional_positive_and_authority_boundaries(self):
        result=self.run_value();self.assertEqual(result['status'],'PASS')
        for key in ('artifact_bytes_verified','label_truth_verified','holdout_independence_verified','training_performed','dataset_export_performed','content_privacy_verified','execution_authorized','target_changes_performed'):
            self.assertIs(result[key],False)
    def test_outer_contract_format_unknown_fields_and_duplicate_keys(self):
        for v in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(v)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_order_changes_do_not_change_qualified_pins(self):
        expected=self.run_value()
        for key in ['records']:self.value[key].reverse()
        actual=self.run_value()
        for key in ['records_sha256', 'taxonomy_sha256']:self.assertEqual(actual[key],expected[key])
    def test_identical_snapshots_count_once(self):
        for key in ['records']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));result=self.run_value(v)
            self.assertEqual(result['status'],'PASS');counts=result['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')),counts['input_rows'])
    def test_rejected_rows_withhold_assessment_and_omit_values(self):
        for key in ['records']:
            v=copy.deepcopy(self.value);v[key].append({'id':'SYNTHETIC_SENTINEL'});result=self.withheld(v)
            self.assertEqual(result['counts'][key]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))
    def test_list_bounds_are_fixed_refusals(self):
        for key in ['records']:
            for rows in (None,{},[{}]*1001):
                v=copy.deepcopy(self.value);v[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(v)
    def test_taxonomy_rejects_duplicate_unknown_and_boolean_revision(self):
        for change in ({'labels':['filter','filter']},{'labels':[]},{'revision':True},{'revision':0},{'extra':0}):
            v=copy.deepcopy(self.value);v['taxonomy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)

    def test_partition_counts_and_hash_oracles(self):
        r=self.run_value();self.assertEqual(r['assessment']['partition_counts'],dict(train=2,validation=0,test=2))
        self.assertEqual(r['records_sha256'],pin(sorted(self.value['records'],key=lambda r:r['id'])))
        self.assertEqual(r['taxonomy_sha256'],pin(self.value['taxonomy']))
    def test_group_overlap_retains_complete_assessment(self):
        self.value['records'][2]['group']=self.value['records'][0]['group'];r=self.review()
        self.assertEqual(r['assessment']['group_overlaps'],[dict(group='unit-alpha',partitions=['test','train'],record_ids=['case-alpha','case-charlie'])])
        self.assertIsNotNone(r['records_sha256'])
    def test_repeated_content_in_same_partition_is_visible(self):
        self.value['records'][1].update(content_sha256=self.value['records'][0]['content_sha256'],label='filter');r=self.review()
        self.assertEqual(len(r['assessment']['repeated_content']),1);self.assertEqual(r['assessment']['repeated_content'][0]['partitions'],['train']);self.assertFalse(r['assessment']['group_overlaps'])
    def test_content_cross_partition_and_label_conflict(self):
        self.value['records'][3]['content_sha256']=self.value['records'][0]['content_sha256'];r=self.review()
        self.assertEqual(r['assessment']['repeated_content'][0]['partitions'],['test','train']);self.assertEqual(r['assessment']['content_label_conflicts'][0]['labels'],['filter','noise'])
    def test_shared_group_within_one_partition_is_allowed(self):
        self.value['records'][1]['group']=self.value['records'][0]['group'];self.assertEqual(self.run_value()['status'],'PASS')
    def test_identity_conflict_withholds_every_copy_and_all_pins(self):
        a=self.value['records'][0];self.value['records']=[a,copy.deepcopy(a),dict(a,revision=2)];r=self.withheld()
        self.assertEqual(r['counts']['records']['conflict_rows'],3);self.assertIsNone(r['records_sha256']);self.assertIsNone(r['taxonomy_sha256'])
    def test_empty_cohort_does_not_get_a_partial_pin(self):
        self.value['records']=[];r=self.withheld();self.assertIsNone(r['records_sha256'])
    def test_bad_record_fields_types_and_unknown_labels(self):
        for change in ({'revision':True},{'revision':1000001},{'label':'unknown'},{'partition':[]},{'partition':'holdout'},{'content_sha256':'A'*64},{'group':'UPPER'},{'extra':0}):
            v=copy.deepcopy(self.value);v['records'][0].update(change);self.withheld(v)
    def test_no_requirement_for_all_partition_names_to_be_populated(self):
        for row in self.value['records']:row['partition']='validation'
        self.assertEqual(self.run_value()['assessment']['partition_counts']['validation'],4)
