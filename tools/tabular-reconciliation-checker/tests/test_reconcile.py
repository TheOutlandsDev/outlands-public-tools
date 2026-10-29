from pathlib import Path
import unittest
from unittest.mock import patch

import reconcile as a
import toolkit as t

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class Reconcile(unittest.TestCase):
    def setUp(self):
        self.before = (EXAMPLES / 'before.json').read_bytes()
        self.after = (EXAMPLES / 'after.json').read_bytes()
        self.contract = (EXAMPLES / 'contract.json').read_bytes()

    def check(self, before=None, after=None, contract=None, show=False):
        return a.compare(self.before if before is None else before,
                         self.after if after is None else after,
                         self.contract if contract is None else contract, show)

    def test_equal_totals_do_not_hide_changed_missing_or_added_records(self):
        value = self.check()
        self.assertEqual(value['status'], 'DIFFERENCES')
        self.assertEqual(value['totals']['units'], dict(before='19', after='19', delta='0'))
        self.assertEqual([r['classification'] for r in value['changes']],
                         ['CHANGED', 'ONLY_IN_BEFORE', 'ONLY_IN_AFTER'])

    def test_identical_sets_match(self):
        value = self.check(after=self.before)
        self.assertEqual(value['status'], 'MATCH')
        self.assertEqual(value['unchanged_records'], 2)

    def test_record_order_and_identical_duplicates_are_accounted(self):
        value = t.decode(self.before)
        value['records'] = list(reversed(value['records'])) + [value['records'][0]]
        result = self.check(after=t.encode(value))
        self.assertEqual(result['status'], 'MATCH')
        self.assertEqual(result['after_counts']['duplicate_rows'], 1)

    def test_conflict_withholds_all_comparison_and_totals(self):
        value = t.decode(self.before); row = dict(value['records'][0]); row['units'] = 99
        value['records'].append(row)
        result = self.check(after=t.encode(value))
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertEqual(result['after_counts']['conflict_rows'], 2)
        self.assertIsNone(result['changes']); self.assertIsNone(result['totals'])

    def test_rejected_row_values_not_retained_and_accounting_conserved(self):
        value = t.decode(self.before); value['records'][0]['units'] = 'SYNTHETIC_SENTINEL'
        result = self.check(before=t.encode(value))
        self.assertNotIn(b'SYNTHETIC_SENTINEL', t.encode(result))
        for side in ('before', 'after'):
            counts = result[side + '_counts']
            self.assertEqual(counts['input_rows'], sum(counts[k] for k in
                ('accepted_records', 'duplicate_rows', 'rejected_rows', 'conflict_rows')))

    def test_json_booleans_are_not_integer_quantities(self):
        value = t.decode(self.before); value['records'][0]['units'] = True
        self.assertEqual(self.check(before=t.encode(value))['before_counts']['rejected_rows'], 1)

    def test_decimal_arithmetic_is_exact(self):
        contract = dict(format='outlands-reconciliation-contract-v1', identity=['id'],
            fields=[dict(name='id', type='text', nullable=False), dict(name='amount', type='decimal', nullable=False)], totals=['amount'])
        before = dict(format='outlands-record-set-v1', records=[dict(id='a', amount='0.1'), dict(id='b', amount='0.2')])
        after = dict(format='outlands-record-set-v1', records=[dict(id='a', amount='0.3'), dict(id='b', amount='0.4')])
        result = self.check(t.encode(before), t.encode(after), t.encode(contract))
        self.assertEqual(result['totals']['amount'], dict(before='0.3', after='0.7', delta='0.4'))

    def test_decimal_spellings_and_negative_zero_normalize(self):
        field = dict(name='x', type='decimal', nullable=False)
        self.assertEqual(a.scalar('-0.000', field), '0')
        self.assertEqual(a.scalar('1.500', field), '1.5')

    def test_nullable_non_total_fields_are_explicit(self):
        contract = t.decode(self.contract); contract['fields'][2]['nullable'] = True
        value = t.decode(self.before); value['records'][0]['due'] = None
        self.assertEqual(self.check(t.encode(value), t.encode(value), t.encode(contract))['status'], 'MATCH')
        with self.assertRaises(t.Rejected):
            contract['fields'][1]['nullable'] = True
            self.check(contract=t.encode(contract))

    def test_identity_and_total_types_must_be_suitable(self):
        for key, names in [('identity', ['active']), ('totals', ['due'])]:
            value = t.decode(self.contract); value[key] = names
            with self.assertRaises(t.Rejected):
                self.check(contract=t.encode(value))

    def test_duplicate_fields_and_selection_are_refused(self):
        for mode in ('fields', 'identity', 'totals'):
            value = t.decode(self.contract); value[mode].append(value[mode][0])
            with self.assertRaises(t.Rejected):
                self.check(contract=t.encode(value))

    def test_empty_sets_and_one_sided_records(self):
        empty = t.encode(dict(format='outlands-record-set-v1', records=[]))
        self.assertEqual(self.check(empty, empty)['status'], 'MATCH')
        value = self.check(empty, self.before)
        self.assertEqual(value['totals']['units']['before'], '0')
        self.assertEqual(len(value['changes']), 2)

    def test_strict_text_dates_decimals_and_unknown_row_fields(self):
        for field, supplied in [('due', '2030-02-30'), ('active', 'true'), ('record_id', ''), ('units', 10**12 + 1)]:
            value = t.decode(self.before); value['records'][0][field] = supplied
            self.assertEqual(self.check(before=t.encode(value))['status'], 'REVIEW_REQUIRED')
        value = t.decode(self.before); value['records'][0]['extra'] = 'not mapped'
        self.assertEqual(self.check(before=t.encode(value))['status'], 'REVIEW_REQUIRED')

    def test_default_values_omitted_explicit_values_retained(self):
        self.assertNotIn('before', self.check()['changes'][0])
        self.assertEqual(self.check(show=True)['changes'][0]['before']['units'], 12)

    def test_duplicate_json_keys_float_literals_and_oversized_sets_refused(self):
        for raw in (b'{"format":1,"format":2}', b'{"x":1.0}',
                    t.encode(dict(format='outlands-record-set-v1', records=[{}] * 1001))):
            with self.assertRaises(t.Rejected):
                self.check(before=raw)

    def test_no_file_network_or_process_access(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected file read')), \
             patch('socket.socket', side_effect=AssertionError('unexpected network access')):
            self.assertEqual(self.check()['status'], 'DIFFERENCES')


if __name__ == '__main__':
    unittest.main()
