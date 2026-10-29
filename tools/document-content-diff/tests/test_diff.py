import unittest
import document_diff as a
import fictional_docx as f
import toolkit as t


class Diff(unittest.TestCase):
    def test_exact_match(self):
        result = a.compare(f.document(), f.document())
        self.assertEqual(result['status'], 'MATCH')
        self.assertFalse(result['raw_bytes_changed'])
        self.assertEqual(result['changes'], [])

    def test_metadata_and_formatting_only_changes_preserve_content_match(self):
        result = a.compare(f.document(), f.document(author='SYNTHETIC_AUTHOR', bold=True))
        self.assertEqual(result['status'], 'MATCH')
        self.assertTrue(result['raw_bytes_changed'])
        self.assertFalse(result['document_properties_compared'])
        self.assertFalse(result['formatting_compared'])

    def test_paragraph_change_is_hashed_without_default_payload(self):
        result = a.compare(f.document([dict(kind='paragraph', text='Fictional before')]),
                           f.document([dict(kind='paragraph', text='SYNTHETIC_SENTINEL')]))
        self.assertEqual(result['changes'][0]['classification'], 'CHANGED')
        self.assertNotIn(b'SYNTHETIC_SENTINEL', t.encode(result))

    def test_explicit_values_include_literal_content(self):
        result = a.compare(f.document([dict(kind='paragraph', text='Before')]),
                           f.document([dict(kind='paragraph', text='<literal>')]), True)
        self.assertEqual(result['changes'][0]['after']['value'], '<literal>')

    def test_cell_coordinates_and_missing_cells_are_reported(self):
        before = f.document([dict(kind='table', rows=[['A', 'B'], ['x', '1']])])
        after = f.document([dict(kind='table', rows=[['A', 'B'], ['x', '2'], ['y', '3']])])
        changes = a.compare(before, after)['changes'][0]['cell_changes']
        self.assertEqual([(v['row'], v['column']) for v in changes], [(2, 2), (3, 1), (3, 2)])
        self.assertIsNone(changes[1]['before_sha256'])

    def test_added_removed_and_kind_changed_blocks(self):
        first = f.document([dict(kind='paragraph', text='A')])
        second = f.document([dict(kind='paragraph', text='A'), dict(kind='paragraph', text='B')])
        table = f.document([dict(kind='table', rows=[['A']])])
        self.assertEqual(a.compare(first, second)['changes'][0]['classification'], 'ADDED')
        self.assertEqual(a.compare(second, first)['changes'][0]['classification'], 'REMOVED')
        self.assertEqual(a.compare(first, table)['changes'][0]['classification'], 'KIND_CHANGED')

    def test_position_comparison_does_not_claim_semantic_move_detection(self):
        first = f.document([dict(kind='paragraph', text='A'), dict(kind='paragraph', text='B')])
        second = f.document([dict(kind='paragraph', text='B'), dict(kind='paragraph', text='A')])
        self.assertEqual(len(a.compare(first, second)['changes']), 2)

    def test_unsupported_input_withholds_any_successful_comparison(self):
        with self.assertRaises(t.Rejected):
            a.compare(f.document(), b'Fictional invalid document')

    def test_block_and_cell_change_caps_refuse_instead_of_truncating(self):
        before = f.document([dict(kind='paragraph', text='A')] * 513)
        after = f.document([dict(kind='paragraph', text='B')] * 513)
        with self.assertRaisesRegex(t.Rejected, 'BLOCK_CHANGE_LIMIT'):
            a.compare(before, after)
        before = f.document([dict(kind='table', rows=[['A'] * 8] * 513)])
        after = f.document([dict(kind='table', rows=[['B'] * 8] * 513)])
        with self.assertRaisesRegex(t.Rejected, 'CELL_CHANGE_LIMIT'):
            a.compare(before, after)

    def test_show_values_requires_boolean(self):
        with self.assertRaises(t.Rejected):
            a.compare(f.document(), f.document(), 'true')


if __name__ == '__main__':
    unittest.main()
