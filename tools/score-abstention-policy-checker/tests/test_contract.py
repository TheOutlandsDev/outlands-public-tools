from scores import check as OP

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

    def test_known_decisions_include_valid_abstention(self):
        result=run(sample());self.assertEqual(result['summary'],dict(cases=3,abstentions=1,declaration_mismatches=0))
        self.assertEqual([r['computed_label'] for r in result['decisions']],['filter-check','noise-check',None]);self.assertEqual(result['status'],'PASS')

    def test_exact_score_and_margin_equalities_pass(self):
        value=sample();value['cases']=value['cases'][:1];value['policy'].update(minimum_score='0.6',minimum_margin='0.1')
        for row,amount in zip(value['cases'][0]['scores'],('0.6','0.5','0.1')):row['value']=amount
        self.assertEqual(run(value)['status'],'PASS');self.assertEqual(run(value)['decisions'][0]['margin'],'0.1')

    def test_tie_abstention_and_explicit_lexical_policy(self):
        value=sample();value['cases']=value['cases'][:1];value['policy'].update(minimum_score='0',minimum_margin='0')
        for row in value['cases'][0]['scores']:row['value']='0.5'
        value['cases'][0]['declared_label']=None;result=run(value);self.assertEqual(result['status'],'PASS');self.assertIn('TOP_SCORE_TIE',result['decisions'][0]['abstention_reasons'])
        value['policy']['tie_policy']='lexical';value['cases'][0]['declared_label']='filter-check';self.assertEqual(run(value)['decisions'][0]['computed_label'],'filter-check')

    def test_margin_abstention_survives_lexical_tie_selection(self):
        value=sample();value['cases']=value['cases'][:1];value['policy'].update(minimum_score='0',minimum_margin='0.000001',tie_policy='lexical')
        for row in value['cases'][0]['scores']:row['value']='0.5'
        value['cases'][0]['declared_label']=None;self.assertIn('MARGIN_BELOW_MINIMUM',run(value)['decisions'][0]['abstention_reasons'])

    def test_all_abstention_reasons_are_retained(self):
        value=sample();value['cases']=value['cases'][:1]
        for row in value['cases'][0]['scores']:row['value']='0.2'
        value['cases'][0]['declared_label']=None;reasons=run(value)['decisions'][0]['abstention_reasons'];self.assertEqual(reasons,['SCORE_BELOW_MINIMUM','MARGIN_BELOW_MINIMUM','TOP_SCORE_TIE'])

    def test_vectors_need_not_sum_to_one_and_are_not_calibrated(self):
        value=sample();value['cases']=value['cases'][:1]
        for row,amount in zip(value['cases'][0]['scores'],('0.9','0.7','0.6')):row['value']=amount
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertFalse(result['confidence_calibrated']);self.assertFalse(result['label_truth_verified'])

    def test_missing_duplicate_unknown_or_out_of_range_score_withholds_all(self):
        for kind in ('missing','duplicate','unknown','outside'):
            value=sample();scores=value['cases'][0]['scores']
            if kind=='missing':scores.pop()
            elif kind=='duplicate':scores[1]['label']=scores[0]['label']
            elif kind=='unknown':scores[0]['label']='missing'
            else:scores[0]['value']='1.1'
            self.assertIsNone(run(value)['decisions'])

    def test_wrong_recorded_decision_retains_complete_diagnostics(self):
        value=sample();value['cases'][0]['declared_label']='noise-check';result=run(value)
        self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertEqual(len(result['decisions']),3);self.assertFalse(result['decisions'][0]['agrees_with_policy'])

    def test_unknown_declared_label_is_structural(self):
        value=sample();value['cases'][0]['declared_label']='missing';self.assertIsNone(run(value)['decisions'])

    def test_normalized_duplicates_and_conflicts(self):
        value=sample();before=run(value);dupe=copy.deepcopy(value['cases'][0]);dupe['scores'].reverse();dupe['scores'][-1]['value']='0.800000';value['cases'].append(dupe)
        self.assertEqual(run(value)['decisions'],before['decisions']);value['cases'].append(dict(value['cases'][0],declared_label=None));self.assertIsNone(run(value)['decisions'])

    def test_empty_cases_and_invalid_policies(self):
        value=sample();value['cases']=[];self.assertIsNone(run(value)['decisions'])
        for change in ({'labels':['single']},{'tie_policy':'guess'},{'minimum_score':'0.0000001'}):
            value=sample();value['policy'].update(change)
            with self.assertRaises(t.Rejected):run(value)

    def test_fictional_game_event_fixture(self):
        value=json.loads((Path(__file__).parent.parent/'examples/game-events.json').read_text(encoding='utf-8'));result=run(value)
        self.assertEqual(result['status'],'PASS');self.assertEqual([r['computed_label'] for r in result['decisions']],['quest',None])

    def test_case_and_label_order_do_not_choose_winner(self):
        value=sample();before=run(value);value['cases'].reverse();value['policy']['labels'].reverse()
        for row in value['cases']:row['scores'].reverse()
        after=run(value);self.assertEqual(before['decisions'],after['decisions']);self.assertEqual(before['policy_sha256'],after['policy_sha256'])
