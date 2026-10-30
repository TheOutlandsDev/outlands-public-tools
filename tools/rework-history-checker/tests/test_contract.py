from rework import check as OP

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

    def test_known_attempts_dispositions_and_totals(self):
        result=run(sample());self.assertEqual(result['totals'],dict(inspection_attempts=4,rework_events=1))
        self.assertEqual([r['disposition'] for r in result['dispositions']],['first_pass_good','reworked_good','scrap'])
        self.assertFalse(result['inspection_outcomes_recomputed']);self.assertFalse(result['manufacturing_route_verified'])

    def test_multiple_failed_attempts_then_reworked_pass(self):
        value=dict(format=sample()['format'],units=[dict(id='air-handler-alpha')],events=[])
        for i,(attempt,kind) in enumerate([(1,'inspect_fail'),(1,'rework'),(2,'inspect_fail'),(2,'rework'),(3,'inspect_pass')]):
            value['events'].append(dict(id='event-'+str(i),specimen_id='air-handler-alpha',at=i,attempt=attempt,kind=kind))
        result=run(value);self.assertEqual(result['histories'][0]['inspection_attempts'],3);self.assertEqual(result['totals']['rework_events'],2);self.assertEqual(result['dispositions'][0]['disposition'],'reworked_good')

    def test_invalid_protocol_and_attempt_sequences(self):
        sequences=[[(2,'inspect_pass')],[(1,'scrap')],[(1,'rework')],[(1,'inspect_pass'),(1,'scrap')],
          [(1,'inspect_fail'),(2,'inspect_pass')],[(1,'inspect_fail'),(2,'rework')],
          [(1,'inspect_fail'),(1,'rework'),(3,'inspect_pass')],[(1,'inspect_fail'),(1,'rework'),(1,'rework')]]
        for sequence in sequences:
            value=dict(format=sample()['format'],units=[dict(id='air-handler-alpha')],events=[dict(id='event-'+str(i),specimen_id='air-handler-alpha',at=i,attempt=n,kind=k) for i,(n,k) in enumerate(sequence)])
            self.assertIsNone(run(value)['dispositions'])

    def test_tied_distinct_events_are_ambiguous(self):
        value=sample();value['events'][2]['at']=0;self.assertIsNone(run(value)['histories'])

    def test_missing_terminal_history_withholds_every_unit(self):
        value=sample();value['events'].pop();result=run(value)
        self.assertIsNone(result['histories']);self.assertIsNone(result['dispositions']);self.assertIsNone(result['totals'])

    def test_no_events_or_missing_unit_history_is_not_closed(self):
        value=sample();value['events']=[];self.assertIsNone(run(value)['histories'])
        value=sample();value['units'].append(dict(id='new-unit'));self.assertIsNone(run(value)['histories'])

    def test_orphan_event_withholds_all(self):
        value=sample();value['events'][0]['specimen_id']='missing';self.assertIsNone(run(value)['histories'])

    def test_duplicate_snapshots_count_once_conflicts_withhold(self):
        value=sample();before=run(value)
        for key in ('units','events'):value[key]*=2
        self.assertEqual(run(value)['histories'],before['histories'])
        value['events'].append(dict(value['events'][0],kind='inspect_fail'));self.assertIsNone(run(value)['histories'])

    def test_invalid_ordinal_attempt_and_kind_rows_withhold(self):
        for update in ({'at':True},{'at':-1},{'attempt':0},{'attempt':1001},{'kind':'unknown'}):
            value=sample();value['events'][0].update(update);self.assertIsNone(run(value)['histories'])

    def test_input_order_is_not_chronological_order(self):
        value=sample();before=run(value)
        for key in ('units','events'):value[key].reverse()
        self.assertEqual(run(value)['histories'],before['histories'])

    def test_same_ordinal_across_different_units_is_valid(self):
        result=run(sample());self.assertEqual(result['status'],'PASS');self.assertEqual({r['first_at'] for r in result['histories']},{0})

    def test_empty_unit_cohort_withholds(self):
        value=sample();value['units']=[];self.assertIsNone(run(value)['histories'])
