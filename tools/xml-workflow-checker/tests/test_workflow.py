"""Fictional graph semantics, declarations and revision comparisons."""
from pathlib import Path
import unittest
from unittest.mock import patch

import workflow as a
import toolkit as t

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class Workflow(unittest.TestCase):
    def setUp(self):
        self.before = (EXAMPLES / 'before.xml').read_bytes()
        self.after = (EXAMPLES / 'after.xml').read_bytes()

    def codes(self, raw):
        return {v['code'] for v in a.check(raw)['issues']}

    def test_valid_forward_and_intentional_rework(self):
        for raw in (self.before, self.after):
            result = a.check(raw)
            self.assertEqual(result['status'], 'PASS')
            self.assertFalse(result['workflow_executed'])

    def test_rework_is_an_explicit_revision_difference(self):
        result = a.check(self.after, self.before)
        self.assertEqual(result['status'], 'DIFFERENCES')
        self.assertEqual(result['changes'], [dict(section='transitions', id='repeat', before=None,
                                                 after={'from': 'inspect', 'to': 'intake', 'kind': 'rework'})])

    def test_semantic_match_ignores_xml_whitespace(self):
        result = a.check(self.before.replace(b'><', b'>\n<'), self.before)
        self.assertEqual(result['status'], 'MATCH')
        self.assertNotEqual(result['sha256'], result['before_sha256'])

    def test_changed_graph_requires_increased_version(self):
        result = a.check(self.after.replace(b'version="2"', b'version="1"'), self.before)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertIsNone(result['changes'])

    def test_version_only_change_is_reported(self):
        result = a.check(self.before.replace(b'version="1"', b'version="2"'), self.before)
        self.assertEqual(result['status'], 'DIFFERENCES')
        self.assertEqual(result['changes'], [])

    def test_version_regression_and_unrelated_id_withhold_diff(self):
        for raw in (self.before, self.after.replace(b'sample-flow', b'another-flow')):
            result = a.check(raw, self.after)
            self.assertEqual(result['status'], 'REVIEW_REQUIRED')
            self.assertIsNone(result['changes'])

    def test_forward_cycle_refused_for_qualification(self):
        raw = self.after.replace(b'kind="rework"', b'kind="forward"')
        self.assertIn('FORWARD_CYCLE', self.codes(raw))

    def test_unreachable_step_and_no_end_path(self):
        raw = self.before.replace(b'</steps>', b'<step id="island" kind="process"/></steps>')
        self.assertTrue({'UNREACHABLE_FROM_START', 'NO_FORWARD_PATH_TO_END'} <= self.codes(raw))

    def test_rework_must_target_forward_ancestor(self):
        raw = self.after.replace(b'from="inspect" to="intake" kind="rework"',
                                 b'from="intake" to="finish" kind="rework"')
        self.assertIn('REWORK_TARGET_NOT_FORWARD_ANCESTOR', self.codes(raw))

    def test_self_transition_is_review_required(self):
        raw = self.after.replace(b'from="inspect" to="intake" kind="rework"',
                                 b'from="inspect" to="inspect" kind="rework"')
        self.assertIn('SELF_TRANSITION', self.codes(raw))

    def test_start_input_and_end_output_reported(self):
        raw = self.before.replace(b'</transitions>', b'<transition id="return" from="finish" to="intake" kind="forward"/></transitions>')
        self.assertTrue({'START_HAS_FORWARD_INPUT', 'END_HAS_FORWARD_OUTPUT'} <= self.codes(raw))

    def test_dangling_reference_and_duplicate_ids(self):
        for raw in (self.before.replace(b'to="finish"', b'to="missing"'),
                    self.before.replace(b'id="last"', b'id="first"'),
                    self.before.replace(b'id="finish"', b'id="inspect"')):
            with self.assertRaises(t.Rejected):
                a.check(raw)

    def test_duplicate_semantic_edge_refused(self):
        raw = self.before.replace(b'</transitions>', b'<transition id="again" from="intake" to="inspect" kind="forward"/></transitions>')
        with self.assertRaises(t.Rejected):
            a.check(raw)

    def test_namespace_unknown_fields_and_embedded_text_refused(self):
        for raw in (self.before.replace(b'<workflow ', b'<workflow xmlns="urn:fictional" '),
                    self.before.replace(b'<workflow ', b'<workflow extra="no" '),
                    self.before.replace(b'<steps>', b'<steps>Unexpected text'),
                    self.before.replace(b'kind="start"', b'kind="unknown"')):
            with self.assertRaises(t.Rejected):
                a.check(raw)

    def test_exactly_one_start_and_at_least_one_end(self):
        for raw in (self.before.replace(b'kind="start"', b'kind="process"'),
                    self.before.replace(b'kind="end"', b'kind="start"')):
            with self.assertRaises(t.Rejected):
                a.check(raw)

    def test_strict_version(self):
        for version in (b'0', b'01', b'-1', b'1.0', b'1000001', b'9' * 5000):
            with self.assertRaises(t.Rejected):
                a.check(self.before.replace(b'version="1"', b'version="' + version + b'"'))

    def test_reordered_steps_do_not_create_false_changes(self):
        text = self.before.replace(b'<step id="intake" kind="start"/><step id="inspect" kind="process"/>',
                                   b'<step id="inspect" kind="process"/><step id="intake" kind="start"/>')
        self.assertEqual(a.check(text, self.before)['status'], 'MATCH')

    def test_invalid_before_graph_withholds_comparison(self):
        bad = self.before.replace(b'</steps>', b'<step id="island" kind="process"/></steps>')
        result = a.check(self.after, bad)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertIsNone(result['changes'])

    def test_no_source_or_network_access(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected file access')):
            self.assertEqual(a.check(self.before)['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
