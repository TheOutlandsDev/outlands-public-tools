import copy
from fractions import Fraction
from pathlib import Path
import unittest
import distributions as a
import toolkit as t


def fraction(value): return Fraction(int(value['numerator']),int(value['denominator']))


class Distributions(unittest.TestCase):
    def setUp(self): self.value=t.decode((Path(__file__).absolute().parents[1]/'examples/input.json').read_bytes())
    def call(self): return a.compare(t.encode(self.value))
    def review(self):
        result=self.call(); self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertEqual(result['comparisons'],[]); return result

    def test_hand_calculated_total_variation(self):
        for row in self.call()['comparisons']: self.assertEqual(fraction(row['total_variation_distance']),Fraction(1,2))

    def test_bucket_totals_include_missing_and_outside(self):
        for row in self.call()['comparisons']:
            self.assertEqual(sum(v['reference_count'] for v in row['buckets']),4)
            self.assertEqual(sum(v['current_count'] for v in row['buckets']),4)
        buckets={v['bucket']:v for v in self.call()['comparisons'][0]['buckets']}
        self.assertEqual(buckets['below']['current_count'],1); self.assertEqual(buckets['above']['current_count'],1)
        self.assertEqual(buckets['missing']['reference_count'],1)

    def test_boundary_lower_inclusive_upper_last_inclusive(self):
        buckets={v['bucket']:v for v in self.call()['comparisons'][0]['buckets']}
        self.assertEqual(buckets['bin-1']['reference_count'],1); self.assertEqual(buckets['bin-2']['reference_count'],2)

    def test_unknown_categories_are_counted_without_values(self):
        result=self.call(); rows={v['bucket']:v for v in result['comparisons'][1]['buckets']}
        self.assertEqual(rows['unknown']['current_count'],1); self.assertNotIn('gamma',t.encode(result).decode())

    def test_identical_distributions_zero_distance(self):
        self.value['current']=copy.deepcopy(self.value['reference'])
        self.assertTrue(all(fraction(row['total_variation_distance'])==0 for row in self.call()['comparisons']))

    def test_disjoint_distributions_distance_one(self):
        self.value['reference']=[dict(id='r',values=dict(quantity='1',label='alpha'))]
        self.value['current']=[dict(id='c',values=dict(quantity='6',label='beta'))]
        self.assertTrue(all(fraction(row['total_variation_distance'])==1 for row in self.call()['comparisons']))

    def test_duplicates_do_not_reweight_distribution(self):
        self.value['reference'].append(copy.deepcopy(self.value['reference'][0]))
        result=self.call(); self.assertEqual(result['counts']['reference']['duplicate_rows'],1)
        self.assertEqual(fraction(result['comparisons'][0]['total_variation_distance']),Fraction(1,2))

    def test_conflicting_rows_withhold_comparisons(self):
        self.value['current'].append(dict(id='c0',values=dict(quantity='1',label='alpha')))
        self.assertEqual(self.review()['counts']['current']['conflict_rows'],2)

    def test_invalid_decimal_or_wrong_field_set_is_rejected(self):
        self.value['current'][0]['values']['quantity']='NaN'
        self.assertEqual(self.review()['counts']['current']['rejected_rows'],1)

    def test_empty_side_is_undefined_not_zero_difference(self):
        self.value['reference']=[]; self.review()

    def test_unordered_duplicate_or_too_few_boundaries(self):
        for values in (['0'],['0','0'],['5','0']):
            self.value['fields'][0]['boundaries']=values
            with self.assertRaises(t.Rejected): self.call()

    def test_duplicate_field_or_category_policy_refused(self):
        self.value['fields'][1]['categories']=['alpha','alpha']
        with self.assertRaises(t.Rejected): self.call()

    def test_shared_bin_policy_never_fitted_to_current(self):
        before=self.call()['policy_sha256']; self.value['current'][0]['values']['quantity']='999'
        self.assertEqual(self.call()['policy_sha256'],before)

    def test_policy_order_and_pin_are_explicit(self):
        before=self.call()['policy_sha256']; self.value['fields'][1]['categories'].reverse()
        self.assertNotEqual(self.call()['policy_sha256'],before)

    def test_all_missing_values_are_accounted_not_dropped(self):
        for side in ('reference','current'):
            for row in self.value[side]: row['values']={key:None for key in row['values']}
        self.assertTrue(all(fraction(v['total_variation_distance'])==0 for v in self.call()['comparisons']))

    def test_no_joint_distribution_or_drift_conclusion(self):
        result=self.call(); self.assertFalse(result['drift_conclusion_verified']); self.assertFalse(result['joint_distribution_compared'])

    def test_exact_share_denominators(self):
        row=self.call()['comparisons'][0]['buckets'][0]
        self.assertEqual(fraction(row['delta']),Fraction(1,4))

    def test_immutable_inputs_and_repeatability(self):
        before=copy.deepcopy(self.value); self.assertEqual(self.call(),self.call()); self.assertEqual(self.value,before)
