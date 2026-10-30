from handoffs import check as OP

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

    def test_unknown_fields_and_format(self):
        for update in ({'extra':0},{'format':'unsupported'}):
            with self.assertRaises(t.Rejected):run(dict(sample(),**update))

    def test_strict_json_and_outer_shapes(self):
        for raw in (b'null',b'[]',b'{}',b'NaN',b'1.0',b'"\\ud800"',b'{"format":1,"format":2}'):
            with self.assertRaises(t.Rejected):OP(raw)

    def test_raw_input_pin_no_mutation_or_authorization(self):
        value=sample();before=copy.deepcopy(value);raw=t.encode(value);result=OP(raw)
        self.assertEqual(value,before);self.assertEqual(result['input_sha256'],t.digest(raw))
        self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_changes_performed']);self.assertFalse(result['declarations_independently_verified'])

    def test_report_round_trip(self):
        result=run(sample());self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_service_kit_acceptance(self):
        result=run(sample());self.assertEqual(result['accepted_quantity'],2);self.assertEqual(result['cancelled_quantity'],0)
        self.assertEqual(result['handoffs'][0]['state'],'accepted');self.assertFalse(result['delivery_independently_verified'])

    def test_cancel_prepared_or_dispatched_without_receipts(self):
        for after_dispatch in (False,True):
            value=sample();value['events']=value['events'][:2 if after_dispatch else 1]+[dict(id='cancelled',handoff_id='service-kit-handoff',at=3,kind='cancel')];value['receipts']=[]
            result=run(value);self.assertEqual(result['status'],'PASS');self.assertEqual(result['cancelled_quantity'],2)

    def test_no_terminal_history_is_not_complete(self):
        value=sample();value['events'].pop();value['receipts']=[];self.assertIsNone(run(value)['handoffs'])

    def test_invalid_transition_matrix(self):
        for kinds in [('dispatch','accept'),('prepare','accept'),('prepare','prepare','dispatch','accept'),('prepare','dispatch','cancel','accept')]:
            value=sample();value['events']=[dict(id='event-'+str(i),handoff_id='service-kit-handoff',at=i,kind=kind) for i,kind in enumerate(kinds)]
            value['receipts']=[];self.assertIsNone(run(value)['handoffs'])

    def test_distinct_event_ids_at_same_ordinal_are_ambiguous(self):
        value=sample();value['events'][1]['at']=0;result=run(value)
        self.assertIsNone(result['handoffs']);self.assertIn('EVENT_TIME_TIE',[i['code'] for i in result['issues']])

    def test_missing_extra_or_mismatched_receipts_withhold_totals(self):
        changes=[[],[dict(sample()['receipts'][0],quantity=1)],sample()['receipts']+[dict(sample()['receipts'][0],id='another')]]
        for receipts in changes:
            value=sample();value['receipts']=receipts;self.assertIsNone(run(value)['accepted_quantity'])

    def test_receipt_must_reference_same_handoff_accept_event(self):
        for event_id in ('missing','handoff-dispatched'):
            value=sample();value['receipts'][0]['event_id']=event_id;self.assertIsNone(run(value)['handoffs'])
        value=sample();value['handoffs'].append(dict(value['handoffs'][0],id='another'))
        value['receipts'][0]['handoff_id']='another';self.assertIsNone(run(value)['handoffs'])

    def test_receipts_for_cancelled_handoffs_are_invalid(self):
        value=sample();value['events'][-1]['kind']='cancel';self.assertIsNone(run(value)['handoffs'])

    def test_orphans_and_invalid_endpoints_quantities(self):
        for list_name in ('events','receipts'):
            value=sample();value[list_name][0]['handoff_id']='missing';self.assertIsNone(run(value)['handoffs'])
        for update in ({'quantity':True},{'quantity':0},{'to_bucket':'parts-shelf'}):
            value=sample();value['handoffs'][0].update(update);self.assertIsNone(run(value)['handoffs'])

    def test_duplicate_snapshots_count_once_and_conflicts_withhold(self):
        value=sample();before=run(value)
        for key in ('handoffs','events','receipts'):value[key]*=2
        self.assertEqual(run(value)['accepted_quantity'],before['accepted_quantity'])
        value['receipts'].append(dict(value['receipts'][0],quantity=3));self.assertIsNone(run(value)['handoffs'])

    def test_input_order_is_not_event_order(self):
        value=sample();before=run(value)
        for key in ('handoffs','events','receipts'):value[key].reverse()
        self.assertEqual(run(value)['handoffs'],before['handoffs'])

    def test_mixed_accepted_and_cancelled_cohort(self):
        value=sample();value['handoffs'].append(dict(value['handoffs'][0],id='cancelled-kit',quantity=3))
        value['events']+=[dict(id='cancel-prepare',handoff_id='cancelled-kit',at=1,kind='prepare'),dict(id='cancel-end',handoff_id='cancelled-kit',at=2,kind='cancel')]
        result=run(value);self.assertEqual((result['accepted_quantity'],result['cancelled_quantity']),(2,3))

    def test_invalid_cohort_withholds_other_valid_handoffs(self):
        value=sample();value['handoffs'].append(dict(value['handoffs'][0],id='incomplete-kit'))
        self.assertIsNone(run(value)['handoffs']);self.assertIsNone(run(value)['accepted_quantity'])
