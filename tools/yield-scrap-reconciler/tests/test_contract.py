from yields import check as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t

def sample():return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value):return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_hvac_example_passes(self):self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_wrong_format_and_unknown_fields(self):
        for update in ({'format':'unsupported'},{'extra':0}):
            with self.assertRaises(t.Rejected):run(dict(sample(),**update))

    def test_strict_json_and_outer_shapes(self):
        for raw in (b'null',b'[]',b'{}',b'NaN',b'1.0',b'"\\ud800"',b'{"format":1,"format":2}'):
            with self.assertRaises(t.Rejected):OP(raw)

    def test_raw_input_pin_no_mutation_or_authorization(self):
        value=sample();before=copy.deepcopy(value);raw=t.encode(value);result=OP(raw)
        self.assertEqual(value,before);self.assertEqual(result['input_sha256'],t.digest(raw));self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_changes_performed'])

    def test_report_round_trip(self):
        result=run(sample());self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_exact_hvac_cohort_fractions(self):
        result=run(sample());self.assertEqual(result['summary'],dict(first_pass_good=2,reworked_good=1,scrap=1,pending=0,cohort=4,good=3,closed_cohort=True))
        self.assertEqual(result['fractions']['first_pass_yield'],dict(numerator=2,denominator=4,exact_fraction='1/2'))
        self.assertEqual(result['fractions']['eventual_yield']['exact_fraction'],'3/4');self.assertEqual(result['fractions']['scrap_fraction']['exact_fraction'],'1/4')

    def test_pending_stays_in_every_denominator(self):
        value=sample();value['dispositions'][-1]['disposition']='pending';result=run(value)
        self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertFalse(result['summary']['closed_cohort'])
        self.assertTrue(all(f['denominator']==4 for f in result['fractions'].values()));self.assertEqual(result['fractions']['pending_fraction']['exact_fraction'],'1/4')

    def test_all_scrap_is_reconciled_not_a_quality_target_pass(self):
        value=sample()
        for row in value['dispositions']:row['disposition']='scrap'
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertFalse(result['quality_target_evaluated']);self.assertEqual(result['fractions']['eventual_yield']['numerator'],0)

    def test_all_pending_is_accounted_but_provisional(self):
        value=sample()
        for row in value['dispositions']:row['disposition']='pending'
        result=run(value);self.assertEqual(result['summary']['pending'],4);self.assertEqual(result['fractions']['pending_fraction']['exact_fraction'],'1/1')

    def test_missing_disposition_is_not_implicitly_pending(self):
        value=sample();value['dispositions'].pop();result=run(value);self.assertIsNone(result['summary']);self.assertIsNone(result['fractions'])

    def test_distinct_dispositions_for_same_unit_are_not_events(self):
        value=sample();value['dispositions'].append(dict(value['dispositions'][0],id='another-result'))
        self.assertIsNone(run(value)['summary'])

    def test_rework_pass_is_one_good_unit(self):
        value=sample()
        for row in value['dispositions']:row['disposition']='reworked_good'
        result=run(value);self.assertEqual(result['summary']['good'],4);self.assertEqual(result['fractions']['first_pass_yield']['numerator'],0)

    def test_duplicate_snapshots_count_once_and_conflicts_withhold(self):
        value=sample();before=run(value)
        for key in ('cohort','dispositions'):value[key]*=2
        self.assertEqual(run(value)['summary'],before['summary'])
        value['dispositions'].append(dict(value['dispositions'][0],disposition='scrap'));self.assertIsNone(run(value)['summary'])

    def test_unknown_unit_invalid_outcome_or_empty_cohort_withholds(self):
        for update in ({'specimen_id':'missing'},{'disposition':'unknown'}):
            value=sample();value['dispositions'][0].update(update);self.assertIsNone(run(value)['summary'])
        value=sample();value['cohort']=[];self.assertIsNone(run(value)['summary'])

    def test_no_independent_coverage_or_physical_cohort_claim(self):
        result=run(sample());self.assertFalse(result['inspection_coverage_verified']);self.assertFalse(result['physical_cohort_completeness_verified'])

    def test_order_invariant_counts_and_fractions(self):
        value=sample();before=run(value)
        for key in ('cohort','dispositions'):value[key].reverse()
        after=run(value);self.assertEqual(before['summary'],after['summary']);self.assertEqual(before['fractions'],after['fractions'])
