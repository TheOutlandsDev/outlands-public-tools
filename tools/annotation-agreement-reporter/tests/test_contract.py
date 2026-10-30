import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import agreement as app

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
        for key in ['items', 'reviews']:self.value[key].reverse()
        actual=self.run_value()
        for key in ['items_sha256', 'taxonomy_sha256']:self.assertEqual(actual[key],expected[key])
    def test_identical_snapshots_count_once(self):
        for key in ['items', 'reviews']:
            if not self.value[key]:continue
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));result=self.run_value(v)
            self.assertEqual(result['status'],'PASS');counts=result['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')),counts['input_rows'])
    def test_rejected_rows_withhold_assessment_and_omit_values(self):
        for key in ['items', 'reviews']:
            v=copy.deepcopy(self.value);v[key].append({'id':'SYNTHETIC_SENTINEL'});result=self.withheld(v)
            self.assertEqual(result['counts'][key]['rejected_rows'],1);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))
    def test_list_bounds_are_fixed_refusals(self):
        for key in ['items', 'reviews']:
            for rows in (None,{},[{}]*1001):
                v=copy.deepcopy(self.value);v[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(v)
    def test_taxonomy_rejects_duplicate_unknown_and_boolean_revision(self):
        for change in ({'labels':['filter','filter']},{'labels':[]},{'revision':True},{'revision':0},{'extra':0}):
            v=copy.deepcopy(self.value);v['taxonomy'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(v)

    def test_exact_denominators_and_complete_unanimity(self):
        a=self.run_value()['assessment'];self.assertEqual((a['reviewed_slots'],a['expected_slots'],a['missing_slots'],a['complete_items']),(8,8,0,4))
        self.assertEqual(a['pair_weighted_agreement'],dict(numerator=4,denominator=4,exact_fraction='1/1'))
    def test_disagreement_has_known_pairwise_fraction(self):
        self.value['reviews'][0]['label']='noise';a=self.review()['assessment']
        self.assertEqual(a['disagreement_items'],1);self.assertEqual(a['pair_weighted_agreement']['exact_fraction'],'3/4')
    def test_missing_review_is_not_a_vote_or_disagreement(self):
        self.value['reviews'].pop();a=self.review()['assessment'];self.assertEqual(a['missing_slots'],1)
        self.assertEqual(a['disagreement_items'],0);self.assertEqual(a['pairs'][0]['matched_items'],3)
    def test_no_reviews_has_no_zero_denominator_agreement(self):
        self.value['reviews']=[];a=self.review()['assessment'];self.assertEqual(a['missing_slots'],8)
        self.assertIsNone(a['pair_weighted_agreement']);self.assertIsNone(a['pairs'][0]['agreement']);self.assertTrue(all(x['unanimous'] is None for x in a['items']))
    def test_one_review_is_not_unanimity(self):
        self.value['reviews']=self.value['reviews'][:1];a=self.review()['assessment'];self.assertIsNone(a['items'][0]['unanimous'])
    def test_three_reviewers_use_pair_weighted_denominator(self):
        self.value['reviewers'].append('reviewer-three');r=copy.deepcopy(self.value['reviews'][0]);r.update(id='review-third',reviewer='reviewer-three',label='noise');self.value['reviews'].append(r)
        a=self.review()['assessment'];self.assertEqual((a['matched_pairs'],a['agreeing_pairs']),(6,4));self.assertEqual(a['pair_weighted_agreement']['exact_fraction'],'2/3')
    def test_distinct_ids_for_one_slot_are_ambiguous_even_if_labels_match(self):
        self.value['reviews'].append(dict(self.value['reviews'][0],id='extra-review'));r=self.withheld()
        self.assertTrue(any(x['code']=='SLOT_AMBIGUOUS' for x in r['issues']))
    def test_conflicting_review_id_withholds_group(self):
        self.value['reviews'].append(dict(self.value['reviews'][0],label='noise'));r=self.withheld();self.assertEqual(r['counts']['reviews']['conflict_rows'],2)
    def test_unknown_and_stale_review_references_withhold(self):
        for change in ({'item':'missing'},{'item_revision':2},{'reviewer':'not-declared'},{'label':'other'},{'label':None}):
            v=copy.deepcopy(self.value);v['reviews'][0].update(change);self.withheld(v)
    def test_item_revision_conflict_never_selects_latest(self):
        self.value['items'].append(dict(self.value['items'][0],revision=2));r=self.withheld();self.assertIsNone(r['items_sha256'])
    def test_empty_item_set_withholds(self):
        self.value['items']=[];self.withheld()
    def test_reviewer_bounds_and_duplicate_reviewer_declarations(self):
        for reviewers in ([],['only'],['a','a'],['r-'+str(i) for i in range(33)]):
            v=copy.deepcopy(self.value);v['reviewers']=reviewers
            with self.assertRaises(t.Rejected):self.run_value(v)
