import copy
from fractions import Fraction
from pathlib import Path
import unittest
import forecast_errors as a
import toolkit as t


def fraction(value): return Fraction(int(value['numerator']),int(value['denominator']))


class Errors(unittest.TestCase):
    def setUp(self): self.value=t.decode((Path(__file__).absolute().parents[1]/'examples/input.json').read_bytes())
    def call(self): return a.analyze(t.encode(self.value))
    def review(self):
        result=self.call(); self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertIsNone(result['metrics'])
        self.assertEqual(result['by_horizon'],[]); return result

    def test_hand_calculated_exact_metrics_and_direction(self):
        result=self.call(); metrics=result['metrics']
        self.assertEqual(fraction(metrics['mean_error']),Fraction(1,3)); self.assertEqual(fraction(metrics['mae']),Fraction(5,3))
        self.assertEqual(fraction(metrics['mse']),3); self.assertEqual(metrics['rmse_approx'],'1.732050807569')
        self.assertEqual(result['error_direction'],'PREDICTED_MINUS_OBSERVED')

    def test_explicit_horizon_groups(self):
        groups={r['horizon']:r['metrics'] for r in self.call()['by_horizon']}
        self.assertEqual(groups[1]['count'],2); self.assertEqual(fraction(groups[1]['mae']),2)
        self.assertEqual(groups[2]['count'],1); self.assertEqual(fraction(groups[2]['mae']),1)

    def test_pending_and_missing_outcomes_withhold_entire_cohort(self):
        self.value['outcomes'][0]['value']=None; self.assertEqual(self.review()['counts']['pending_forecasts'],1)
        self.value['outcomes'].pop(); self.assertEqual(self.review()['counts']['missing_forecasts'],1)

    def test_unused_outcome_is_not_silently_ignored(self):
        self.value['outcomes'].append(dict(series='sample',period=99,value='1'))
        self.assertEqual(self.review()['counts']['unused_outcomes'],1)

    def test_normalized_duplicates_do_not_reweight_metrics(self):
        duplicate=copy.deepcopy(self.value['forecasts'][0]); duplicate['predicted']='4.000'
        self.value['forecasts'].append(duplicate); self.value['outcomes'].append(copy.deepcopy(self.value['outcomes'][0]))
        result=self.call(); self.assertEqual(result['metrics']['count'],3)
        self.assertEqual(result['counts']['forecasts']['duplicate_rows'],1)

    def test_forecast_and_outcome_conflicts_are_withheld(self):
        self.value['forecasts'].append(dict(self.value['forecasts'][0],predicted='9'))
        self.assertEqual(self.review()['counts']['forecasts']['conflict_rows'],2)

    def test_multiple_revisions_are_not_auto_selected(self):
        self.value['forecasts'].append(dict(self.value['forecasts'][0],revision=2))
        self.assertEqual(self.review()['counts']['forecasts']['conflict_rows'],2)

    def test_pending_and_observed_duplicate_conflict(self):
        self.value['outcomes'].append(dict(self.value['outcomes'][0],value=None))
        self.assertEqual(self.review()['counts']['outcomes']['conflict_rows'],2)

    def test_bad_rows_count_and_do_not_leak_values(self):
        self.value['forecasts'].append(dict(private='FICTIONAL_SENTINEL'))
        result=self.review(); self.assertEqual(result['counts']['forecasts']['rejected_rows'],1)
        self.assertNotIn('FICTIONAL_SENTINEL',t.encode(result).decode())

    def test_invalid_horizon_and_boolean_revision_are_rejected_rows(self):
        self.value['forecasts'][0]['target']=0; self.review()
        self.value['forecasts'][1]['revision']=True; self.assertEqual(self.review()['counts']['forecasts']['rejected_rows'],2)

    def test_one_outcome_can_match_distinct_horizons(self):
        row=dict(self.value['forecasts'][0],id='sample-other',origin=0,target=2)
        self.value['forecasts'].append(row); self.assertEqual(self.call()['metrics']['count'],4)

    def test_large_error_metrics_roundtrip_without_integer_loss(self):
        for row in self.value['forecasts']: row['predicted']='1000000000000'
        for row in self.value['outcomes']: row['value']='-1000000000000'
        result=self.call(); self.assertEqual(fraction(result['metrics']['mse']),4*10**24)
        self.assertEqual(t.decode(t.encode(result)),result)

    def test_empty_forecasts_are_invalid(self):
        self.value['forecasts']=[]
        with self.assertRaises(t.Rejected): self.call()

    def test_empty_outcomes_are_explicitly_unresolved(self):
        self.value['outcomes']=[]; self.assertEqual(self.review()['counts']['missing_forecasts'],3)

    def test_unknown_top_level_metadata_refused(self):
        self.value['private_path']='invented'
        with self.assertRaises(t.Rejected): self.call()

    def test_inputs_immutable_and_source_timing_not_verified(self):
        before=copy.deepcopy(self.value); result=self.call(); self.assertEqual(self.value,before)
        self.assertFalse(result['forecast_timing_verified']); self.assertFalse(result['source_authority_verified'])
