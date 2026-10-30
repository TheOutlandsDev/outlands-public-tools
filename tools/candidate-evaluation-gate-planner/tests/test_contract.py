from gates import check as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t
import decision_core as c

def sample():return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value):return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_fictional_example_passes(self):self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_wrong_format_and_unknown_fields(self):
        for change in ({'format':'unsupported'},{'extra':0}):
            with self.assertRaises(t.Rejected):run(dict(sample(),**change))

    def test_strict_json_and_outer_shapes(self):
        for raw in (b'null',b'[]',b'{}',b'NaN',b'1.0',b'"\\ud800"',b'{"format":1,"format":2}'):
            with self.assertRaises(t.Rejected):OP(raw)

    def test_raw_input_pin_no_mutation_or_authorization(self):
        value=sample();before=copy.deepcopy(value);raw=t.encode(value);result=OP(raw)
        self.assertEqual(value,before);self.assertEqual(result['input_sha256'],t.digest(raw));self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_changes_performed'])

    def test_report_round_trip(self):
        result=run(sample());self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_same_cohort_exact_counts_and_gate(self):
        result=run(sample());self.assertTrue(result['assessment']['eligible_for_manual_review'])
        self.assertEqual((result['metrics']['baseline']['correct'],result['metrics']['candidate']['correct']),(1,2))
        self.assertEqual(result['metrics']['candidate']['accuracy'],dict(numerator=2,denominator=3,exact_fraction='2/3'))
        self.assertEqual(result['assessment']['accuracy_delta']['exact_fraction'],'1/3');self.assertFalse(result['deploy_authorized'])

    def test_fractional_thresholds_are_not_rounded(self):
        value=sample();value['policy']['minimum_accuracy']='0.666666';self.assertTrue(run(value)['assessment']['eligible_for_manual_review'])
        value['policy']['minimum_accuracy']='0.666667';self.assertIn('MINIMUM_ACCURACY_NOT_MET',run(value)['assessment']['failed_criteria'])

    def test_regression_and_abstention_increase_are_separate(self):
        value=sample();value['candidate']['predictions'][0]['label']=None;value['candidate']['predictions'][1]['label']='needs-review'
        result=run(value);failed=result['assessment']['failed_criteria'];self.assertIn('ACCURACY_REGRESSION_EXCEEDED',failed);self.assertIn('ABSTENTION_INCREASE_EXCEEDED',failed)

    def test_policy_equality_and_signed_improvement(self):
        value=sample();value['candidate']['predictions']=copy.deepcopy(value['baseline']['predictions']);value['policy']['minimum_accuracy']='0.3'
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertEqual(result['assessment']['accuracy_delta']['exact_fraction'],'0/1')

    def test_explicit_all_abstention_policy_is_not_quality_approval(self):
        value=sample();value['policy']['minimum_accuracy']='0'
        for side in ('baseline','candidate'):
            for row in value[side]['predictions']:row['label']=None
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertEqual(result['metrics']['candidate']['accuracy']['numerator'],0);self.assertFalse(result['holdout_independence_verified'])

    def test_missing_extra_or_unknown_label_predictions_withhold_metrics(self):
        for kind in ('missing','extra','unknown'):
            value=sample()
            if kind=='missing':value['candidate']['predictions'].pop()
            elif kind=='extra':value['candidate']['predictions'].append(dict(id='missing-case',label=None))
            else:value['candidate']['predictions'][0]['label']='unknown'
            self.assertIsNone(run(value)['metrics'])

    def test_scope_and_required_candidate_pins_are_exact(self):
        for side,field in [('baseline','cohort_sha256'),('candidate','taxonomy_sha256'),('candidate','prompt_sha256'),('candidate','decision_policy_sha256')]:
            value=sample();value[side][field]='0'*64;self.assertIsNone(run(value)['assessment'])

    def test_model_identity_and_candidate_revision_are_not_inferred(self):
        for change in ({'id':'other'},{'revision':1}):
            value=sample();value['candidate'].update(change);self.assertIsNone(run(value)['assessment'])

    def test_actual_embedded_truth_changes_invalidate_old_cohort_pin(self):
        value=sample();value['cohort'][0]['expected_label']='needs-review';self.assertIsNone(run(value)['metrics'])

    def test_duplicate_snapshots_never_inflate_denominator(self):
        value=sample();before=run(value);value['cohort']*=2
        for side in ('baseline','candidate'):value[side]['predictions']*=2
        after=run(value);self.assertEqual(after['metrics'],before['metrics']);self.assertEqual(after['cohort_sha256'],before['cohort_sha256'])

    def test_conflicting_cohort_withholds_partial_scope_pin(self):
        value=sample();value['cohort'].append(dict(value['cohort'][0],expected_label='needs-review'));result=run(value)
        self.assertIsNone(result['metrics']);self.assertIsNone(result['cohort_sha256'])

    def test_prediction_conflicts_and_empty_cohort_withhold(self):
        value=sample();value['candidate']['predictions'].append(dict(value['candidate']['predictions'][0],label=None));self.assertIsNone(run(value)['metrics'])
        value=sample();value['cohort']=[];self.assertIsNone(run(value)['metrics'])

    def test_exact_accounting_and_no_authenticity_or_execution_claim(self):
        result=run(sample())
        for metrics in result['metrics'].values():self.assertEqual(metrics['cohort'],metrics['correct']+metrics['incorrect']+metrics['abstained'])
        for key in ('artifact_bytes_verified','label_truth_verified','holdout_independence_verified','deploy_authorized','release_performed','training_performed'):self.assertFalse(result[key])

    def test_input_order_cannot_change_gate(self):
        value=sample();before=run(value);value['cohort'].reverse();value['labels']['labels'].reverse()
        for side in ('baseline','candidate'):value[side]['predictions'].reverse()
        after=run(value);self.assertEqual(before['metrics'],after['metrics']);self.assertEqual(before['assessment'],after['assessment'])
