import copy
from fractions import Fraction
from pathlib import Path
import unittest
import intervals as a
import toolkit as t


def fraction(value): return Fraction(int(value['numerator']),int(value['denominator']))


class Intervals(unittest.TestCase):
    def setUp(self): self.value=t.decode((Path(__file__).absolute().parents[1]/'examples/input.json').read_bytes())
    def call(self): return a.analyze(t.encode(self.value))
    def review(self):
        result=self.call(); self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertIsNone(result['metrics']); return result

    def test_exact_inclusive_coverage_width_and_miss_distance(self):
        result=self.call(); metrics=result['metrics']
        self.assertEqual((metrics['covered'],metrics['above'],metrics['below']),(2,1,0))
        self.assertEqual(fraction(metrics['coverage']),Fraction(2,3)); self.assertEqual(fraction(metrics['mean_width']),2)
        self.assertEqual(fraction(metrics['mean_outside_distance']),Fraction(1,3))
        self.assertEqual(fraction(metrics['coverage_minus_nominal']),Fraction(-2,15))

    def test_both_endpoints_and_zero_width_included(self):
        for row,actual in zip(self.value['intervals'],self.value['outcomes']): row.update(lower=actual['value'],upper=actual['value'])
        self.assertEqual(self.call()['metrics']['covered'],3); self.assertEqual(fraction(self.call()['metrics']['mean_width']),0)

    def test_below_interval_distance(self):
        self.value['outcomes'][0]['value']='1'
        self.assertEqual(self.call()['metrics']['below'],1)

    def test_inverted_interval_rejected_without_swapping(self):
        self.value['intervals'][0].update(lower='9',upper='1')
        self.assertEqual(self.review()['counts']['forecasts']['rejected_rows'],1)

    def test_missing_pending_and_unused_outcomes_withhold_metrics(self):
        self.value['outcomes'][0]['value']=None; self.review()
        self.value['outcomes'].append(dict(series='sample',period=99,value='1')); self.review()

    def test_duplicate_intervals_do_not_reweight(self):
        self.value['intervals'].append(copy.deepcopy(self.value['intervals'][0]))
        self.assertEqual(self.call()['metrics']['count'],3)

    def test_conflicting_interval_revision_withholds_all(self):
        self.value['intervals'].append(dict(self.value['intervals'][0],revision=2)); self.review()

    def test_horizon_groups_are_explicit(self):
        self.assertEqual([r['horizon'] for r in self.call()['by_horizon']],[1,2])

    def test_nominal_probability_is_not_percent_or_closed_endpoint(self):
        for value in ('0','1','95','-0.1',True):
            self.value['nominal_coverage']=value
            with self.assertRaises(t.Rejected): self.call()

    def test_numeric_bound_and_precision_refusal(self):
        self.value['intervals'][0]['upper']='1000000000000.000001'; self.review()

    def test_no_calibration_or_independence_claim(self):
        result=self.call(); self.assertFalse(result['calibration_verified']); self.assertFalse(result['independent_coverage_guarantee'])
        self.assertFalse(result['target_changes_performed'])

    def test_input_values_not_in_default_summary(self):
        self.assertNotIn('sample-a',t.encode(self.call()).decode())

    def test_negative_intervals_and_exact_fractions(self):
        for row,actual in zip(self.value['intervals'],self.value['outcomes']): row.update(lower='-1',upper='-0.1'); actual['value']='-0.5'
        self.assertEqual(fraction(self.call()['metrics']['coverage']),1)
        self.assertEqual(fraction(self.call()['metrics']['mean_width']),Fraction(9,10))

    def test_unknown_fields_and_empty_intervals(self):
        self.value['intervals']=[]
        with self.assertRaises(t.Rejected): self.call()

    def test_immutable_deterministic_result(self):
        before=copy.deepcopy(self.value); self.assertEqual(self.call(),self.call()); self.assertEqual(self.value,before)
