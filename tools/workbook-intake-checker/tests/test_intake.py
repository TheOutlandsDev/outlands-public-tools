"""Invented tables and independently mutated OOXML packages."""
import io
from pathlib import Path
import unittest
import zipfile

import intake as a
import fictional_workbook as f
import toolkit as t

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


def mutate(raw, edits):
    result = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(result, 'w') as target:
        parts = {name: source.read(name) for name in source.namelist()}
        for name, edit in edits.items():
            parts[name] = edit(parts.get(name, b''))
        for name, value in parts.items():
            target.writestr(name, value)
    return result.getvalue()


class Intake(unittest.TestCase):
    def setUp(self):
        self.mapping = (EXAMPLES / 'mapping.json').read_bytes()
        self.csv = (EXAMPLES / 'records.csv').read_bytes()

    def preview(self, raw=None, mapping=None, kind='csv', sheet=None):
        return a.preview(self.csv if raw is None else raw,
                         self.mapping if mapping is None else mapping, kind, sheet)

    def test_csv_inline_and_shared_xlsx_parity(self):
        expected = self.preview()
        self.assertEqual(expected['counts'], dict(input_rows=3, accepted_records=2, duplicate_rows=1,
                                                rejected_rows=0, conflict_rows=0))
        for shared in (False, True):
            actual = self.preview(f.workbook(shared=shared), kind='xlsx', sheet='Records')
            for key in ('status', 'counts', 'accepted', 'issues', 'mapping'):
                self.assertEqual(actual[key], expected[key])
            self.assertNotEqual(actual['source_sha256'], expected['source_sha256'])

    def test_conflicting_identity_withholds_every_member(self):
        result = self.preview((EXAMPLES / 'needs-review.csv').read_bytes())
        self.assertEqual(result['accepted'], [])
        self.assertEqual(result['counts'], dict(input_rows=3, accepted_records=0, duplicate_rows=0,
                                              rejected_rows=1, conflict_rows=2))
        self.assertFalse(result['ready_for_explicit_review'])
        self.assertNotIn('invalid', t.encode(result).decode())

    def test_all_records_accounted_with_mixed_outcomes(self):
        result = self.preview(self.csv + b'sample-a,13,2030-01-10,true\nsample-c,bad,2030-01-10,true\n')
        counts = result['counts']
        self.assertEqual(counts['input_rows'], sum(counts[k] for k in
                         ('accepted_records', 'duplicate_rows', 'rejected_rows', 'conflict_rows')))
        self.assertEqual(counts['accepted_records'], 1)
        self.assertEqual(counts['conflict_rows'], 3)

    def test_empty_and_duplicate_headers_refused(self):
        for raw in (b'', b'A,A\nx,y\n', b',B\nx,y\n'):
            with self.assertRaises(t.Rejected):
                self.preview(raw)

    def test_missing_mapped_header_refused(self):
        with self.assertRaisesRegex(t.Rejected, 'MAPPED_HEADER_MISSING'):
            self.preview(self.csv.replace(b'Units', b'Other'))

    def test_unknown_headers_explicit_ignore(self):
        rows = b'Record,Units,Due,Active,Other\nsample-a,1,2030-01-01,true,ignored\n'
        with self.assertRaises(t.Rejected):
            self.preview(rows)
        config = t.decode(self.mapping); config['unknown_columns'] = 'ignore'
        result = self.preview(rows, t.encode(config))
        self.assertEqual(result['ignored_columns'], 1)
        self.assertEqual(result['status'], 'PASS')

    def test_duplicate_mapping_and_optional_identity_refused(self):
        for mutation in ('duplicate', 'optional'):
            config = t.decode(self.mapping)
            if mutation == 'duplicate':
                config['fields'][1]['target'] = 'record_id'
            else:
                config['fields'][0]['required'] = False
            with self.assertRaises(t.Rejected):
                self.preview(mapping=t.encode(config))

    def test_no_implicit_boolean_integer_or_date_coercion(self):
        for tail in ('1,2030-01-01,TRUE', '1.0,2030-01-01,true', '01,2030-01-01,true',
                     '1,2030-02-30,true', '1,01/01/2030,true'):
            result = self.preview(('Record,Units,Due,Active\nsample-a,' + tail + '\n').encode())
            self.assertEqual(result['counts']['rejected_rows'], 1)

    def test_decimal_normalization_and_optional_null(self):
        config = t.decode(self.mapping)
        config['fields'][1]['type'] = 'decimal'
        config['fields'][2]['required'] = False
        result = self.preview(b'Record,Units,Due,Active\nsample-a,1.500,,false\n', t.encode(config))
        self.assertEqual(result['accepted'][0]['record']['units'], '1.5')
        self.assertIsNone(result['accepted'][0]['record']['due'])

    def test_rejected_text_not_retained(self):
        result = self.preview(b'Record,Units,Due,Active\nsample-a,SYNTHETIC_SENTINEL,2030-01-01,true\n')
        self.assertNotIn(b'SYNTHETIC_SENTINEL', t.encode(result))
        self.assertEqual(result['issues'], [{'row': 2, 'code': 'VALUE_INTEGER_INVALID'}])

    def test_quoted_newlines_rejected_as_values_not_split_into_extra_records(self):
        result = self.preview(b'Record,Units,Due,Active\n"sample\nrecord",1,2030-01-01,true\n')
        self.assertEqual(result['counts']['input_rows'], 1)
        self.assertEqual(result['counts']['rejected_rows'], 1)

    def test_malformed_csv_encoding_and_row_limit(self):
        for raw in (b'\xff', b'"unclosed', self.csv.splitlines()[0] + b'\n' + b'a,1,2030-01-01,true\n' * 1001):
            with self.assertRaises(t.Rejected):
                self.preview(raw)

    def test_blank_rows_accounted_as_rejected(self):
        result = self.preview(self.csv + b'\n')
        self.assertEqual(result['counts']['input_rows'], 4)
        self.assertEqual(result['counts']['rejected_rows'], 1)

    def test_sheet_selection_required_and_exact(self):
        for sheet in (None, 'records', 'Missing'):
            with self.assertRaises(t.Rejected):
                self.preview(f.workbook(), kind='xlsx', sheet=sheet)

    def test_csv_does_not_accept_sheet_selection(self):
        with self.assertRaises(t.Rejected):
            self.preview(sheet='Records')

    def test_formula_cached_value_refused(self):
        raw = mutate(f.workbook(), {'xl/worksheets/sheet1.xml': lambda b: b.replace(b'<is>', b'<f>1+1</f><is>', 1)})
        with self.assertRaises(t.Rejected):
            self.preview(raw, kind='xlsx', sheet='Records')

    def test_external_relationship_refused(self):
        raw = mutate(f.workbook(), {'xl/_rels/workbook.xml.rels': lambda b: b.replace(b'Target=', b'TargetMode="External" Target=', 1)})
        with self.assertRaises(t.Rejected):
            self.preview(raw, kind='xlsx', sheet='Records')

    def test_traversal_and_macro_parts_refused(self):
        for name in ('../sample.xml', 'xl/vbaProject.bin', 'xl/externalLinks/link1.xml'):
            raw = mutate(f.workbook(), {name: lambda _: b'Fictional blocked part'})
            with self.assertRaises(t.Rejected):
                self.preview(raw, kind='xlsx', sheet='Records')

    def test_hidden_sheets_rows_and_merged_regions_refused(self):
        variants = [mutate(f.workbook(), {'xl/workbook.xml': lambda b: b.replace(b'name="Records"', b'name="Records" state="hidden"')}),
                    mutate(f.workbook(), {'xl/worksheets/sheet1.xml': lambda b: b.replace(b'<row r="2"', b'<row hidden="1" r="2"')}),
                    mutate(f.workbook(), {'xl/worksheets/sheet1.xml': lambda b: b.replace(b'</worksheet>', b'<mergeCells/></worksheet>')})]
        for raw in variants:
            with self.assertRaises(t.Rejected):
                self.preview(raw, kind='xlsx', sheet='Records')

    def test_duplicate_zip_member_refused(self):
        result = io.BytesIO(f.workbook())
        with self.assertWarns(UserWarning), zipfile.ZipFile(result, 'a') as z:
            z.writestr('xl/workbook.xml', b'<x/>')
        with self.assertRaises(t.Rejected):
            self.preview(result.getvalue(), kind='xlsx', sheet='Records')

    def test_archive_expansion_limit(self):
        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name in ('[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml', 'xl/worksheets/sheet1.xml'):
                z.writestr(name, b'a' * 100000)
        with self.assertRaisesRegex(t.Rejected, 'EXPANSION'):
            self.preview(result.getvalue(), kind='xlsx', sheet='Records')

    def test_invalid_shared_string_reference(self):
        raw = mutate(f.workbook(shared=True), {'xl/worksheets/sheet1.xml': lambda b: b.replace(b'<v>0</v>', b'<v>999</v>', 1)})
        with self.assertRaises(t.Rejected):
            self.preview(raw, kind='xlsx', sheet='Records')

    def test_duplicate_or_wrong_cell_coordinates(self):
        for value in (b'A1', b'B3', b'AAA2'):
            raw = mutate(f.workbook(), {'xl/worksheets/sheet1.xml': lambda b: b.replace(b'B2', value, 1)})
            with self.assertRaises(t.Rejected):
                self.preview(raw, kind='xlsx', sheet='Records')

    def test_unknown_schema_and_rich_strings_refused(self):
        for name, edit in [('xl/worksheets/sheet1.xml', lambda b: b.replace(b't="inlineStr"', b't="e"', 1)),
                           ('xl/worksheets/sheet1.xml', lambda b: b.replace(b'<t>Record</t>', b'<r><t>Record</t></r>', 1))]:
            raw = mutate(f.workbook(), {name: edit})
            with self.assertRaises(t.Rejected):
                self.preview(raw, kind='xlsx', sheet='Records')

    def test_defined_names_and_external_workbook_features_refused(self):
        for element in (b'<definedNames><definedName name="sample">1+1</definedName></definedNames>',
                        b'<externalReferences/>'):
            raw = mutate(f.workbook(), {'xl/workbook.xml': lambda b: b.replace(b'</workbook>', element + b'</workbook>')})
            with self.assertRaises(t.Rejected):
                self.preview(raw, kind='xlsx', sheet='Records')


if __name__ == '__main__':
    unittest.main()
