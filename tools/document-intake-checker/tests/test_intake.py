from pathlib import Path
import unittest
import document_intake as a
import fictional_docx as f
import toolkit as t

MAPPING = (Path(__file__).resolve().parents[1] / 'examples/mapping.json').read_bytes()


class Intake(unittest.TestCase):
    def test_fictional_typed_rows_duplicate_accounting_and_provenance(self):
        result = a.preview(f.document(), MAPPING, 'table-1')
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['counts'], dict(input_rows=3, accepted_records=2, duplicate_rows=1,
                                              rejected_rows=0, conflict_rows=0))
        self.assertEqual(result['accepted'][0]['source_rows'], [2, 4])
        self.assertIs(result['accepted'][0]['record']['active'], True)
        self.assertEqual(result['source_sha256'], t.digest(f.document()))
        self.assertNotEqual(result['source_sha256'], result['normalized_table_sha256'])

    def test_conflicts_withhold_entire_identity_group(self):
        rows = [['Record', 'Units', 'Due', 'Active'], ['sample-a', '12', '2030-01-10', 'true'],
                ['sample-a', '13', '2030-01-10', 'true'], ['sample-c', 'invalid', '2030-01-10', 'true']]
        result = a.preview(f.document([dict(kind='table', rows=rows)]), MAPPING, 'table-1')
        self.assertEqual(result['counts']['conflict_rows'], 2)
        self.assertEqual(result['counts']['rejected_rows'], 1)
        self.assertEqual(result['accepted'], [])
        self.assertFalse(result['ready_for_explicit_review'])

    def test_explicit_table_selection_required(self):
        for selected in (None, 'table-2', 'TABLE-1'):
            with self.assertRaises(t.Rejected):
                a.preview(f.document(), MAPPING, selected)

    def test_header_mapping_not_inferred(self):
        raw = f.document([dict(kind='table', rows=[['Other'], ['sample-a']])])
        with self.assertRaises(t.Rejected):
            a.preview(raw, MAPPING, 'table-1')

    def test_false_integer_and_boolean_strings_are_rejected(self):
        rows = [['Record', 'Units', 'Due', 'Active'], ['sample-a', '1.0', '2030-01-10', 'true'],
                ['sample-b', '1', '2030-01-10', 'TRUE']]
        value = a.preview(f.document([dict(kind='table', rows=rows)]), MAPPING, 'table-1')
        self.assertEqual(value['counts']['rejected_rows'], 2)

    def test_metadata_omitted_even_when_explicitly_selected_table_is_exported(self):
        result = a.preview(f.document(author='SYNTHETIC_AUTHOR'), MAPPING, 'table-1')
        self.assertNotIn(b'SYNTHETIC_AUTHOR', t.encode(result))
        self.assertFalse(result['document_properties_exported'])

    def test_invalid_row_payload_is_not_retained(self):
        rows = [['Record', 'Units', 'Due', 'Active'], ['sample-a', 'SYNTHETIC_SENTINEL', '2030-01-10', 'true']]
        value = a.preview(f.document([dict(kind='table', rows=rows)]), MAPPING, 'table-1')
        self.assertNotIn(b'SYNTHETIC_SENTINEL', t.encode(value))

    def test_unchanged_public_intake_rules_apply_to_empty_and_unknown_columns(self):
        raw = f.document([dict(kind='table', rows=[['Record', 'Units', 'Due', 'Active']])])
        self.assertEqual(a.preview(raw, MAPPING, 'table-1')['status'], 'REVIEW_REQUIRED')
        mapping = t.decode(MAPPING); mapping['unknown_columns'] = 'ignore'
        mapping['fields'] = mapping['fields'][:2]
        result = a.preview(f.document(), t.encode(mapping), 'table-1')
        self.assertEqual(result['ignored_columns'], 2)


if __name__ == '__main__':
    unittest.main()
