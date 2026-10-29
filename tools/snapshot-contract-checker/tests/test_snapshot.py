"""Fictional declaration accounting and explicit source-byte evidence."""
from pathlib import Path
import unittest
from unittest.mock import patch

import snapshot as a
import toolkit as t

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.manifest = (EXAMPLES / 'manifest.json').read_bytes()
        self.policy = (EXAMPLES / 'policy.json').read_bytes()
        self.inputs = {'records': (EXAMPLES / 'records.txt').read_bytes()}

    def check(self, manifest=None, policy=None, inputs=None):
        return a.check(self.manifest if manifest is None else manifest,
                       self.policy if policy is None else policy,
                       self.inputs if inputs is None else inputs)

    def codes(self, result):
        return {v['code'] for v in result['issues']}

    def test_fictional_exact_pins_and_freshness_boundary(self):
        result = self.check()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['age_seconds'], 3600)
        self.assertFalse(result['record_counts_independently_verified'])
        self.assertFalse(result['external_system_writes'])

    def test_stale_one_second_beyond_boundary(self):
        policy = t.decode(self.policy); policy['max_age_seconds'] = 3599
        self.assertEqual(self.codes(self.check(policy=t.encode(policy))), {'SNAPSHOT_STALE'})

    def test_future_capture_refused_as_review(self):
        policy = t.decode(self.policy); policy['as_of'] = '2029-12-31T23:59:59Z'
        self.assertIn('CAPTURE_AFTER_AS_OF', self.codes(self.check(policy=t.encode(policy))))

    def test_no_host_clock_or_file_discovery(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected file access')):
            self.assertEqual(self.check()['status'], 'PASS')

    def test_exact_raw_manifest_pin(self):
        self.assertIn('MANIFEST_PIN_MISMATCH', self.codes(self.check(manifest=self.manifest + b' ')))

    def test_version_mismatch(self):
        policy = t.decode(self.policy); policy['expected_version'] = 'v2'
        self.assertIn('VERSION_MISMATCH', self.codes(self.check(policy=t.encode(policy))))

    def test_item_size_and_hash_mismatch(self):
        result = self.check(inputs={'records': b'Fictional replacement'})
        self.assertEqual(self.codes(result), {'ITEM_HASH_MISMATCH', 'ITEM_SIZE_MISMATCH'})

    def test_same_length_tamper_detected(self):
        result = self.check(inputs={'records': self.inputs['records'].replace(b'a', b'z', 1)})
        self.assertEqual(self.codes(result), {'ITEM_HASH_MISMATCH'})

    def test_missing_or_extra_buffers_refused(self):
        for inputs in ({}, {**self.inputs, 'extra': b'x'}):
            with self.assertRaisesRegex(t.Rejected, 'BINDING_COVERAGE_INVALID'):
                self.check(inputs=inputs)

    def test_expected_item_coverage_mismatch(self):
        policy = t.decode(self.policy); policy['expected_items'][0]['id'] = 'other'
        self.assertIn('EXPECTED_ITEM_COVERAGE_MISMATCH', self.codes(self.check(policy=t.encode(policy))))

    def test_declared_record_count_mismatch(self):
        policy = t.decode(self.policy); policy['expected_items'][0]['records'] = 3
        self.assertIn('DECLARED_RECORD_COUNT_MISMATCH', self.codes(self.check(policy=t.encode(policy))))

    def test_declared_accounting_conservation(self):
        manifest = t.decode(self.manifest); manifest['reconciliation']['input_records'] = 4
        self.assertIn('DECLARED_ACCOUNTING_MISMATCH', self.codes(self.check(manifest=t.encode(manifest))))

    def test_declared_accepted_total_conservation(self):
        manifest = t.decode(self.manifest); manifest['items'][0]['records'] = 1
        self.assertIn('DECLARED_ACCEPTED_TOTAL_MISMATCH', self.codes(self.check(manifest=t.encode(manifest))))

    def test_duplicate_items_refused(self):
        for side in ('manifest', 'policy'):
            value = t.decode(getattr(self, side)); key = 'items' if side == 'manifest' else 'expected_items'
            value[key].append(value[key][0])
            with self.assertRaisesRegex(t.Rejected, 'DUPLICATE_ITEM'):
                self.check(**{side: t.encode(value)})

    def test_boolean_counts_and_undeclared_fields_refused(self):
        for value in (True, -1, '2'):
            manifest = t.decode(self.manifest); manifest['items'][0]['records'] = value
            with self.assertRaises(t.Rejected):
                self.check(manifest=t.encode(manifest))
        manifest = t.decode(self.manifest); manifest['path'] = 'fictional.txt'
        with self.assertRaises(t.Rejected):
            self.check(manifest=t.encode(manifest))

    def test_timestamps_require_exact_valid_utc(self):
        for value in ('2030-01-01', '2030-02-30T00:00:00Z', '2030-01-01T00:00:00+00:00'):
            policy = t.decode(self.policy); policy['as_of'] = value
            with self.assertRaises(t.Rejected):
                self.check(policy=t.encode(policy))

    def test_invalid_hash_and_buffer_type_refused(self):
        manifest = t.decode(self.manifest); manifest['items'][0]['sha256'] = 'invalid'
        with self.assertRaises(t.Rejected):
            self.check(manifest=t.encode(manifest))
        with self.assertRaises(t.Rejected):
            self.check(inputs={'records': 'not bytes'})

    def test_matching_false_counts_are_explicitly_unverified(self):
        # Matching declarations cannot prove actual logical records in opaque bytes.
        manifest = t.decode(self.manifest); policy = t.decode(self.policy)
        manifest['items'][0]['records'] = 9
        manifest['reconciliation'] = dict(input_records=9, accepted_records=9,
                                           duplicate_records=0, rejected_records=0)
        raw = t.encode(manifest); policy['manifest_sha256'] = t.digest(raw)
        policy['expected_items'][0]['records'] = 9
        result = self.check(manifest=raw, policy=t.encode(policy))
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['record_counts_independently_verified'])


if __name__ == '__main__':
    unittest.main()
