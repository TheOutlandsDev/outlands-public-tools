import unittest
import docx_tables as a
import fictional_docx as f
import toolkit as t


class Selection(unittest.TestCase):
    def test_default_summary_exports_no_body_values(self):
        result = a.inspect(f.document())
        self.assertEqual(result['selected_tables'], [])
        self.assertEqual(result['selected_paragraphs'], [])
        self.assertEqual(result['table_index'], [dict(id='table-1', position=2, rows=4, columns=4)])

    def test_explicit_table_and_paragraph_selection(self):
        result = a.inspect(f.document(), ['table-1'], True)
        self.assertEqual(result['selected_tables'][0]['rows'][1][0], 'sample-a')
        self.assertEqual(result['selected_paragraphs'][0]['text'], 'Fictional intake example.')

    def test_duplicate_missing_and_invalid_selection_refused(self):
        for selection in (['table-1', 'table-1'], ['table-2'], [True]):
            with self.assertRaises(t.Rejected):
                a.inspect(f.document(), selection)

    def test_multiple_tables_selected_in_caller_order(self):
        raw = f.document([dict(kind='table', rows=[['A']]), dict(kind='table', rows=[['B']])])
        result = a.inspect(raw, ['table-2', 'table-1'])
        self.assertEqual([x['rows'] for x in result['selected_tables']], [[['B']], [['A']]])

    def test_literal_markup_is_data(self):
        raw = f.document([dict(kind='table', rows=[['<script>literal</script>']])])
        self.assertEqual(a.inspect(raw, ['table-1'])['selected_tables'][0]['rows'][0][0], '<script>literal</script>')


if __name__ == '__main__':
    unittest.main()
