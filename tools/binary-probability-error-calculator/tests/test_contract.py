import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import errors as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment']);return r
    def test_positive_and_truth_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('probability_interpretation_verified','label_truth_verified','cohort_independence_verified','calibration_established','model_fitted','model_updated','inference_performed','artifact_bytes_verified','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_format_unknown_fields_and_duplicate_keys_refuse(self):
        for v in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(v)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_preserves_normalized_pins(self):
        before=self.run_value()
        for path in [['cohort'], ['predictions'], ['outcomes']]:
            rows=self.value
            for key in path:rows=rows[key]
            rows.reverse()
        after=self.run_value()
        for key in ['cohort_sha256', 'contract_sha256', 'predictions_sha256', 'outcomes_sha256', 'evaluation_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_snapshots_count_once_with_complete_accounting(self):
        for path in [['cohort'], ['predictions'], ['outcomes']]:
            value=copy.deepcopy(self.value);rows=value
            for key in path:rows=rows[key]
            rows.append(copy.deepcopy(rows[0]));r=self.run_value(value);self.assertEqual(r['status'],'PASS')
            side=path[-1] if len(path)==1 else path[0]+'_points';counts=r['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_rejected_rows_withhold_qualified_result_and_omit_values(self):
        for path in [['cohort'], ['predictions'], ['outcomes']]:
            value=copy.deepcopy(self.value);rows=value
            for key in path:rows=rows[key]
            rows.append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_refuse(self):
        for path in [['cohort'], ['predictions'], ['outcomes']]:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);selected=value
                for key in path[:-1]:selected=selected[key]
                selected[path[-1]]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_known_individual_errors_total_and_full_cohort_mean(self):
        r=self.run_value();self.assertEqual([x['squared_error']['exact_fraction'] for x in r['assessment']['cases']],['1/16','1/16','1/4','0/1'])
        self.assertEqual(r['metrics']['total_squared_error']['exact_fraction'],'3/8');self.assertEqual(r['metrics']['mean_squared_error']['exact_fraction'],'3/32')
    def test_perfect_and_certainly_wrong_predictions_have_exact_extremes(self):
        outcomes={o['case']:o['label'] for o in self.value['outcomes']}
        for p in self.value['predictions']:p['probability']='1' if outcomes[p['case']]=='service-needed' else '0'
        self.assertEqual(self.run_value()['metrics']['mean_squared_error']['exact_fraction'],'0/1')
        for p in self.value['predictions']:p['probability']='0' if p['probability']=='1' else '1'
        self.assertEqual(self.run_value()['metrics']['mean_squared_error']['exact_fraction'],'1/1')
    def test_label_direction_is_explicit_not_inferred(self):
        self.value['contract'].update(positive_label='no-service',negative_label='service-needed')
        self.assertEqual(self.run_value()['metrics']['mean_squared_error']['exact_fraction'],'19/32')
    def test_missing_outcome_withholds_aggregate_instead_of_intersection_scoring(self):
        self.value['outcomes'].pop();r=self.review();self.assertIsNone(r['metrics']);self.assertIsNone(r['evaluation_sha256'])
        self.assertEqual(r['assessment']['missing_outcomes'],['case-delta']);self.assertIsNotNone(r['assessment']['cases'][0]['squared_error'])
    def test_missing_prediction_is_not_zero_or_abstention(self):
        self.value['predictions'].pop();r=self.review();self.assertIsNone(r['metrics']);self.assertFalse(r['assessment']['cases'][3]['prediction_present'])
    def test_explicit_unknown_probability_and_outcome_remain_present(self):
        self.value['predictions'][0]['probability']=None;self.value['outcomes'][1]['label']=None;r=self.review()
        self.assertEqual(r['assessment']['unknown_probabilities'],['case-alpha']);self.assertEqual(r['assessment']['unknown_outcomes'],['case-bravo']);self.assertTrue(r['assessment']['cases'][0]['prediction_present']);self.assertIsNone(r['metrics'])
    def test_unknown_label_is_not_reclassified_negative(self):
        self.value['outcomes'][0]['label']='other';r=self.withheld();self.assertIsNone(r['metrics'])
    def test_stale_case_pin_revision_and_model_binding_withhold(self):
        for change in ({'case':'missing'},{'case_revision':2},{'case_sha256':'0'*64},{'model':'other-model'},{'model_revision':2}):
            value=copy.deepcopy(self.value);value['predictions'][0].update(change);self.withheld(value)
        value=copy.deepcopy(self.value);value['outcomes'][0]['case_sha256']='0'*64;self.withheld(value)
    def test_ambiguous_prediction_or_outcome_slot_withholds(self):
        for key in ('predictions','outcomes'):
            value=copy.deepcopy(self.value);value[key].append(dict(value[key][0],id='other-row'));self.withheld(value)
    def test_conflicting_cohort_revision_withholds_all_pins(self):
        self.value['cohort'].append(dict(self.value['cohort'][0],revision=2));r=self.withheld()
        for key in ('cohort_sha256','contract_sha256','predictions_sha256','outcomes_sha256','evaluation_sha256'):self.assertIsNone(r[key])
    def test_empty_cohort_and_empty_evidence_have_distinct_accounting(self):
        value=copy.deepcopy(self.value);value['cohort']=[];self.withheld(value)
        self.value['predictions']=[];self.value['outcomes']=[];r=self.review();self.assertEqual(len(r['assessment']['missing_predictions']),4);self.assertEqual(len(r['assessment']['missing_outcomes']),4);self.assertIsNone(r['metrics'])
    def test_contract_identity_labels_and_boolean_revisions_are_refused(self):
        for change in ({'positive_label':'no-service'},{'revision':True},{'model_revision':0},{'extra':0}):
            value=copy.deepcopy(self.value);value['contract'].update(change)
            with self.assertRaises(t.Rejected):self.run_value(value)
    def test_bad_probability_and_outcome_types_reject_rows(self):
        for value in ('-0.1','1.1','NaN','0.0000001',True):
            v=copy.deepcopy(self.value);v['predictions'][0]['probability']=value;self.withheld(v)
        v=copy.deepcopy(self.value);v['outcomes'][0]['label']=False;self.withheld(v)
    def test_actual_normalized_scope_hashes_bind_evaluation(self):
        r=self.run_value();self.assertEqual(r['cohort_sha256'],pin(self.value['cohort']))
        self.assertEqual(r['evaluation_sha256'],pin({k:r[k] for k in ('contract_sha256','cohort_sha256','predictions_sha256','outcomes_sha256')}))
