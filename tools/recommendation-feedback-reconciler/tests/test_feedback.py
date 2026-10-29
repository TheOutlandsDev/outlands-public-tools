import copy
from pathlib import Path
import unittest
import feedback as a
import toolkit as t


class Feedback(unittest.TestCase):
    def setUp(self): self.value=t.decode((Path(__file__).absolute().parents[1]/'examples/input.json').read_bytes())
    def call(self): return a.reconcile(t.encode(self.value))
    def review(self):
        result=self.call(); self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertEqual(result['states'],[])
        self.assertIsNone(result['state_counts']); return result

    def test_exact_revision_states(self):
        rows={(r['recommendation_id'],r['revision']):r['state'] for r in self.call()['states']}
        self.assertEqual(rows,{('sample-a',1):'OUTCOME_RECORDED',('sample-a',2):'DEFERRED',('sample-b',1):'REJECTED'})
        self.assertTrue(self.call()['all_acceptances_have_observed_outcomes'])

    def test_pending_does_not_become_observed_or_complete(self):
        self.value['outcomes'][0].update(status='pending',observed=None)
        result=self.call(); self.assertEqual(result['status'],'PASS'); self.assertFalse(result['all_acceptances_have_observed_outcomes'])
        self.assertEqual(result['states'][0]['state'],'ACCEPTED_PENDING_OUTCOME')

    def test_no_outcome_remains_pending(self):
        self.value['outcomes']=[]; self.assertEqual(self.call()['states'][0]['state'],'ACCEPTED_PENDING_OUTCOME')

    def test_no_decisions_is_explicit_awaiting_review(self):
        self.value.update(decisions=[],outcomes=[])
        self.assertEqual(self.call()['state_counts'],{'AWAITING_REVIEW':3})
        self.assertFalse(self.call()['all_acceptances_have_observed_outcomes'])

    def test_no_automatic_latest_revision_matching(self):
        self.value['outcomes'][0]['revision']=3
        self.assertIn('ORPHAN_REVISION',{row['code'] for row in self.review()['issues']})

    def test_observed_outcome_requires_acceptance(self):
        self.value['decisions'][0]['decision']='reject'
        self.assertIn('OUTCOME_WITHOUT_ACCEPTANCE',{r['code'] for r in self.review()['issues']})

    def test_pending_outcome_also_requires_acceptance(self):
        self.value['outcomes'][0].update(status='pending',observed=None); self.value['decisions'][0]['decision']='defer'; self.review()

    def test_duplicate_rows_are_accounted_once(self):
        for key in ('recommendations','decisions','outcomes'): self.value[key].append(copy.deepcopy(self.value[key][0]))
        result=self.call()
        for key in ('recommendations','decisions','outcomes'): self.assertEqual(result['counts'][key]['duplicate_rows'],1)

    def test_conflicting_decisions_withhold_derived_states(self):
        self.value['decisions'].append(dict(self.value['decisions'][0],decision='reject'))
        self.assertEqual(self.review()['counts']['decisions']['conflict_rows'],2)

    def test_pending_to_observed_rows_are_not_auto_overwritten(self):
        self.value['outcomes'].append(dict(self.value['outcomes'][0],status='pending',observed=None))
        self.assertEqual(self.review()['counts']['outcomes']['conflict_rows'],2)

    def test_changed_action_under_same_revision_conflicts(self):
        self.value['recommendations'].append(dict(self.value['recommendations'][0],action='other'))
        self.assertEqual(self.review()['counts']['recommendations']['conflict_rows'],2)

    def test_unknown_recommendation_decision_is_retained_as_orphan(self):
        self.value['decisions'].append(dict(recommendation_id='unknown',revision=1,decision='accept')); self.review()

    def test_bad_rows_count_without_value_echo(self):
        self.value['outcomes'].append(dict(private='FICTIONAL_SENTINEL'))
        result=self.review(); self.assertEqual(result['counts']['outcomes']['rejected_rows'],1)
        self.assertNotIn('FICTIONAL_SENTINEL',t.encode(result).decode())

    def test_pending_requires_null_and_observed_requires_number(self):
        self.value['outcomes'][0]['status']='pending'; self.review()
        self.value['outcomes'][0].update(status='observed',observed=None); self.review()

    def test_numeric_normalization_is_duplicate_not_conflict(self):
        self.value['outcomes'].append(dict(self.value['outcomes'][0],observed='2.000'))
        self.assertEqual(self.call()['counts']['outcomes']['duplicate_rows'],1)

    def test_no_body_action_or_observed_value_in_summary(self):
        result=self.call(); self.assertNotIn('observed',result); self.assertNotIn('action',t.encode(result).decode())

    def test_no_truth_causality_training_or_action_claim(self):
        result=self.call()
        for key in ('outcome_truth_verified','causal_effect_estimated','model_or_policy_updated','target_changes_performed'):
            self.assertFalse(result[key])

    def test_empty_recommendations_invalid(self):
        self.value['recommendations']=[]
        with self.assertRaises(t.Rejected): self.call()

    def test_unknown_top_level_metadata_refused(self):
        self.value['server']='invented'
        with self.assertRaises(t.Rejected): self.call()

    def test_immutable_and_repeatable(self):
        before=copy.deepcopy(self.value); self.assertEqual(self.call(),self.call()); self.assertEqual(self.value,before)
