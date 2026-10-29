"""Actual pinned public planner contract with invented project and review buffers."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import handoff as a
import toolkit as t
from planner_contract import project

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class Handoff(unittest.TestCase):
    def setUp(self):
        self.project = (EXAMPLES / 'project.json').read_bytes()
        self.handoff = (EXAMPLES / 'handoff.json').read_bytes()
        self.attachments = {'provenance': (EXAMPLES / 'provenance.txt').read_bytes()}

    def check(self, project_raw=None, handoff=None, attachments=None):
        return a.check(self.project if project_raw is None else project_raw,
                       self.handoff if handoff is None else handoff,
                       self.attachments if attachments is None else attachments)

    def test_fictional_public_planner_project_passes(self):
        result = self.check()
        self.assertEqual(result['status'], 'PASS')
        self.assertTrue(result['eligible_for_explicit_import'])
        for key in ('project_transformed', 'project_imported', 'external_system_writes',
                    'lot_ids_reserved', 'shipment_execution_authorized', 'review_identity_independently_verified'):
            self.assertIs(result[key], False)

    def test_review_pins_exact_project_bytes(self):
        result = self.check(project_raw=self.project + b' ')
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertTrue({'PROJECT_PIN_MISMATCH', 'STALE_PROJECT_REVIEW'} <= set(result['issues']))
        self.assertFalse(result['eligible_for_explicit_import'])

    def test_attachment_content_and_review_pin(self):
        result = self.check(attachments={'provenance': b'Changed fictional provenance'})
        self.assertEqual(set(result['issues']), {'ATTACHMENT_PIN_MISMATCH', 'STALE_ATTACHMENT_REVIEW'})

    def test_explicit_review_each_assertion_required(self):
        for key in ('inputs_reviewed', 'mappings_reviewed', 'policies_reviewed', 'plan_only'):
            value = t.decode(self.handoff); value['review'][key] = False
            result = self.check(handoff=t.encode(value))
            self.assertEqual(result['issues'], ['EXPLICIT_REVIEW_INCOMPLETE'])

    def test_missing_flags_are_not_defaulted(self):
        value = t.decode(self.handoff); del value['review']['plan_only']
        with self.assertRaises(t.Rejected):
            self.check(handoff=t.encode(value))

    def test_boolean_assertions_are_strict(self):
        for supplied in ('true', 1, None):
            value = t.decode(self.handoff); value['review']['plan_only'] = supplied
            with self.assertRaises(t.Rejected):
                self.check(handoff=t.encode(value))

    def test_unknown_fields_and_embedded_paths_refused(self):
        value = t.decode(self.handoff); value['attachments'][0]['path'] = 'fictional.txt'
        with self.assertRaises(t.Rejected):
            self.check(handoff=t.encode(value))

    def test_missing_or_extra_attachment_bindings(self):
        for values in ({}, {**self.attachments, 'extra': b'x'}):
            with self.assertRaises(t.Rejected):
                self.check(attachments=values)

    def test_duplicate_attachment_ids(self):
        value = t.decode(self.handoff); value['attachments'].append(value['attachments'][0])
        with self.assertRaises(t.Rejected):
            self.check(handoff=t.encode(value))

    def test_attachment_pin_is_order_independent(self):
        self.assertEqual(a.attachment_pin({'one': b'1', 'two': b'2'}),
                         a.attachment_pin({'two': b'2', 'one': b'1'}))

    def test_empty_attachment_set_requires_its_own_review_pin(self):
        value = t.decode(self.handoff); value['attachments'] = []
        value['review']['attachments_sha256'] = a.attachment_pin({})
        self.assertEqual(self.check(handoff=t.encode(value), attachments={})['status'], 'PASS')

    def test_project_duplicate_keys_unknown_fields_and_nonfinite_refused(self):
        for raw in (b'{"format":1,"format":2}', b'{"format":NaN}',
                    t.encode({**t.decode(self.project), 'undeclared': True})):
            with self.assertRaises(t.Rejected):
                self.check(project_raw=raw)

    def test_actual_public_project_rules_refuse_boolean_quantity(self):
        value = t.decode(self.project); value['wip'][0]['quantity'] = True
        with self.assertRaisesRegex(t.Rejected, 'PLANNER_PROJECT_INVALID'):
            self.check(project_raw=t.encode(value))

    def test_actual_public_project_rules_refuse_mapping_mismatch(self):
        value = t.decode(self.project); value['wip'][0]['kanban'] = 7
        with self.assertRaisesRegex(t.Rejected, 'PLANNER_PROJECT_INVALID'):
            self.check(project_raw=t.encode(value))

    def test_actual_public_policy_and_order_rules(self):
        value = t.decode(self.project); value['lot_policies'][0]['lot_size'] += 1
        with self.assertRaisesRegex(t.Rejected, 'PLANNER_PROJECT_INVALID'):
            self.check(project_raw=t.encode(value))

    def test_no_files_network_or_processes_and_inputs_unchanged(self):
        before = copy.deepcopy(self.attachments)
        with patch('builtins.open', side_effect=AssertionError('unexpected file access')), \
             patch('socket.socket', side_effect=AssertionError('unexpected network access')), \
             patch('subprocess.Popen', side_effect=AssertionError('unexpected child process')):
            self.assertEqual(self.check()['status'], 'PASS')
        self.assertEqual(self.attachments, before)

    def test_actual_public_plan_conserves_demand(self):
        plan = project.calculate(project.parse(self.project))
        for product in plan['products']:
            values = product['allocation']['conservation']
            self.assertEqual(product['remaining_demand'], product['dock_allocated_quantity'] +
                             values['covered'] + values['uncovered'])


if __name__ == '__main__':
    unittest.main()
