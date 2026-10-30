from orders import check as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t
import service_core as c

def sample():return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value):return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_hvac_example_passes(self):self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_wrong_format_and_unknown_fields(self):
        for change in ({'format':'unsupported'},{'extra':0}):
            with self.assertRaises(t.Rejected):run(dict(sample(),**change))

    def test_strict_json_and_outer_shapes(self):
        for raw in (b'null',b'[]',b'{}',b'NaN',b'1.0',b'"\\ud800"',b'{"format":1,"format":2}'):
            with self.assertRaises(t.Rejected):OP(raw)

    def test_input_pin_no_mutation_or_authorization(self):
        value=sample();before=copy.deepcopy(value);raw=t.encode(value);result=OP(raw)
        self.assertEqual(value,before);self.assertEqual(result['input_sha256'],t.digest(raw));self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_changes_performed'])

    def test_report_round_trip(self):
        result=run(sample());self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_hold_resume_and_pinned_completed_snapshot(self):
        result=run(sample());row=result['orders'][0]
        self.assertEqual((row['state'],row['revision'],row['event_count']),('completed',5,5));self.assertEqual(row['order_sha256'],c.order_pin(sample()['orders'][0]))
        self.assertFalse(result['completion_evidence_checked'])

    def test_valid_open_in_progress_and_hold_prefixes(self):
        for count,state in [(1,'open'),(2,'in_progress'),(3,'on_hold')]:
            value=sample();value['events']=value['events'][:count];value['orders'][0].update(revision=count,state=state)
            self.assertEqual(run(value)['status'],'PASS')

    def test_cancel_from_open_running_or_hold(self):
        for count in (1,2,3):
            value=sample();value['events']=value['events'][:count]+[dict(id='cancel',order_id='service-order-alpha',revision=count+1,at=count,kind='cancel')]
            value['orders'][0].update(revision=count+1,state='cancelled');self.assertEqual(run(value)['status'],'PASS')

    def test_terminal_orders_cannot_resume_or_complete_again(self):
        for kind in ('resume','complete','cancel'):
            value=sample();value['events'].append(dict(id='extra',order_id='service-order-alpha',revision=6,at=5,kind=kind));value['orders'][0]['revision']=6
            self.assertIsNone(run(value)['orders'])

    def test_missing_revisions_or_creation_are_invalid(self):
        for index in (0,2):
            value=sample();value['events'].pop(index);self.assertIsNone(run(value)['orders'])

    def test_wrong_selected_revision_state_or_no_history_withholds(self):
        for change in ({'revision':4},{'state':'cancelled'}):
            value=sample();value['orders'][0].update(change);self.assertIsNone(run(value)['orders'])
        value=sample();value['events']=[];self.assertIsNone(run(value)['orders'])

    def test_wrong_transition_or_chronological_revision_order(self):
        value=sample();value['events'][1]['kind']='resume';self.assertIsNone(run(value)['orders'])
        value=sample();value['events'][0]['at']=3;self.assertIsNone(run(value)['orders'])

    def test_ties_and_distinct_ids_for_same_revision_are_ambiguous(self):
        value=sample();value['events'][1]['at']=0;self.assertIsNone(run(value)['orders'])
        value=sample();value['events'].append(dict(value['events'][0],id='same-revision'));self.assertIsNone(run(value)['orders'])

    def test_duplicates_count_once_conflicts_withhold(self):
        value=sample();before=run(value)
        for key in ('orders','events'):value[key]*=2
        self.assertEqual(run(value)['orders'],before['orders'])
        value['events'].append(dict(value['events'][0],kind='start'));self.assertIsNone(run(value)['orders'])

    def test_orphan_event_empty_cohort_and_invalid_ordinals(self):
        value=sample();value['events'][0]['order_id']='missing';self.assertIsNone(run(value)['orders'])
        value=sample();value['orders']=[];self.assertIsNone(run(value)['orders'])
        value=sample();value['events'][0]['at']=True;self.assertIsNone(run(value)['orders'])

    def test_input_row_order_does_not_change_history(self):
        value=sample();before=run(value);value['events'].reverse();self.assertEqual(run(value)['orders'],before['orders'])
