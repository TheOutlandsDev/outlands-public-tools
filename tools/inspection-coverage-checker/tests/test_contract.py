from inspections import check as OP

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

    def test_known_cartesian_scope_and_complete_records(self):
        result=run(sample());self.assertEqual(len(result['coverage']),4)
        self.assertEqual(result['summary'],dict(expected_pairs=4,recorded_pairs=4,missing_pairs=0,within_limits=4,outside_limits=0,not_evaluated=0,records_complete=True,all_records_within_limits=True))
        self.assertFalse(result['source_bytes_verified']);self.assertFalse(result['measurement_results_recomputed'])

    def test_no_records_is_explicit_missing_coverage(self):
        value=sample();value['records']=[];result=run(value)
        self.assertEqual(result['summary']['missing_pairs'],4);self.assertFalse(result['summary']['records_complete']);self.assertEqual(result['status'],'REVIEW_REQUIRED')

    def test_complete_records_can_have_outside_or_unevaluated_outcomes(self):
        for outcome in ('outside_limits','not_evaluated'):
            value=sample();value['records'][0]['outcome']=outcome;result=run(value)
            self.assertTrue(result['summary']['records_complete']);self.assertFalse(result['summary']['all_records_within_limits']);self.assertEqual(result['status'],'REVIEW_REQUIRED')

    def test_distinct_ids_for_same_check_are_ambiguous(self):
        value=sample();value['records'].append(dict(value['records'][0],id='another-record'));result=run(value)
        self.assertIsNone(result['coverage']);self.assertIsNone(result['summary'])

    def test_orphan_references_and_rule_selection_withhold_all(self):
        for update in ({'specimen_id':'missing'},{'check_id':'missing'},{'rule_id':'other'},{'rule_revision':2}):
            value=sample();value['records'][0].update(update);self.assertIsNone(run(value)['coverage'])

    def test_exact_duplicate_snapshots_never_inflate_coverage(self):
        value=sample();before=run(value)
        for key in ('specimens','checks','records'):value[key]*=2
        self.assertEqual(run(value)['summary'],before['summary'])

    def test_conflicts_or_invalid_pins_withhold_all(self):
        value=sample();value['records'].append(dict(value['records'][0],outcome='outside_limits'));self.assertIsNone(run(value)['summary'])
        value=sample();value['records'][0]['source_sha256']='not-a-pin';self.assertIsNone(run(value)['summary'])

    def test_expected_pair_limit_refuses_even_when_records_empty(self):
        value=sample();value['specimens']=[dict(id='unit-'+str(i)) for i in range(101)];value['checks']=[dict(id='check-'+str(i),rule_id='demo',rule_revision=1) for i in range(100)];value['records']=[]
        with self.assertRaisesRegex(t.Rejected,'EXPECTED_PAIR_LIMIT'):run(value)
        value['specimens'].pop();self.assertEqual(run(value)['summary']['expected_pairs'],10000)

    def test_empty_required_cohorts_withhold_all(self):
        for key in ('specimens','checks'):
            value=sample();value[key]=[];self.assertIsNone(run(value)['summary'])

    def test_declared_pin_is_not_source_byte_verification(self):
        value=sample();value['records'][0]['source_sha256']='0'*64;result=run(value)
        self.assertEqual(result['status'],'PASS');self.assertFalse(result['source_bytes_verified'])

    def test_order_invariant_coverage(self):
        value=sample();before=run(value)
        for key in ('specimens','checks','records'):value[key].reverse()
        self.assertEqual(before['coverage'],run(value)['coverage'])
