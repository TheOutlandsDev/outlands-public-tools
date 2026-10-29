"""Invented OPC/XML refusals, stored text fidelity and metadata exclusion."""
import io
import unittest
import zipfile
from unittest.mock import patch

import docx_core as d
import fictional_docx as f
import toolkit as t


def mutate(raw, edits):
    result = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(result, 'w') as output:
        parts = {name: source.read(name) for name in source.namelist()}
        for name, edit in edits.items():
            parts[name] = edit(parts.get(name, b''))
        for name, value in parts.items():
            output.writestr(name, value)
    return result.getvalue()


class Docx(unittest.TestCase):
    def test_fictional_text_tables_and_provenance(self):
        value = d.extract(f.document())
        self.assertEqual(value['counts'], dict(paragraphs=1, tables=1, rows=4, cells=16))
        self.assertEqual(value['blocks'][1]['rows'][1], ['sample-a', '12', '2030-01-10', 'true'])
        self.assertEqual(value['blocks'][1]['id'], 'table-1')
        self.assertEqual(value['blocks'][1]['position'], 2)

    def test_formatting_and_metadata_do_not_change_content_hash(self):
        first, second = d.extract(f.document()), d.extract(f.document(author='SYNTHETIC_AUTHOR', bold=True))
        self.assertEqual(first['content_sha256'], second['content_sha256'])
        self.assertNotEqual(first['source_sha256'], second['source_sha256'])
        self.assertNotIn(b'SYNTHETIC_AUTHOR', t.encode(second))
        self.assertFalse(second['document_properties_exported'])

    def test_paragraph_whitespace_unicode_tabs_and_breaks_preserved(self):
        raw = f.document([dict(kind='paragraph', text='  Fictional \u03bb & example  ')])
        raw = mutate(raw, {'word/document.xml': lambda b: b.replace(b'</w:t>', b'</w:t><w:tab/><w:t>Next</w:t><w:br/><w:t>Last</w:t>', 1)})
        self.assertEqual(d.extract(raw)['blocks'][0]['text'], '  Fictional \u03bb & example  \tNext\nLast')

    def test_multiple_cell_paragraphs_preserved(self):
        raw = mutate(f.document(), {'word/document.xml': lambda b: b.replace(b'</w:tc>', b'<w:p><w:r><w:t>Second</w:t></w:r></w:p></w:tc>', 1)})
        self.assertEqual(d.extract(raw)['blocks'][1]['rows'][0][0], 'Record\nSecond')

    def test_no_source_network_or_process_access(self):
        raw = f.document()
        with patch('builtins.open', side_effect=AssertionError('unexpected file read')), \
             patch('socket.socket', side_effect=AssertionError('unexpected network access')):
            self.assertEqual(d.extract(raw)['counts']['tables'], 1)

    def test_not_a_zip_and_truncated_zip(self):
        for raw in (b'Fictional invalid input', f.document()[:50]):
            with self.assertRaises(t.Rejected):
                d.extract(raw)

    def test_external_relationship_refused(self):
        raw = mutate(f.document(), {'_rels/.rels': lambda b: b.replace(b'Target=', b'TargetMode="External" Target=', 1)})
        with self.assertRaisesRegex(t.Rejected, 'RELATIONSHIP'):
            d.extract(raw)

    def test_traversal_macro_image_and_unknown_parts_refused(self):
        for name in ('../fictional.xml', 'word/vbaProject.bin', 'word/media/image1.png', 'customXml/item1.xml'):
            with self.assertRaises(t.Rejected):
                d.extract(mutate(f.document(), {name: lambda _: b'Fictional refused part'}))

    def test_macro_content_type_refused(self):
        raw = mutate(f.document(), {'[Content_Types].xml': lambda b: b.replace(d.MAIN_TYPE.encode(), b'application/vnd.ms-word.document.macroEnabled.main+xml')})
        with self.assertRaises(t.Rejected):
            d.extract(raw)

    def test_missing_main_relationship_refused(self):
        raw = mutate(f.document(), {'_rels/.rels': lambda b: b.replace(b'word/document.xml', b'docProps/core.xml', 1)})
        with self.assertRaises(t.Rejected):
            d.extract(raw)

    def test_unbound_part_refused(self):
        raw = mutate(f.document(), {'word/styles.xml': lambda _: b'<styles/>'})
        with self.assertRaisesRegex(t.Rejected, 'UNBOUND_PART'):
            d.extract(raw)

    def test_duplicate_zip_member_refused(self):
        value = io.BytesIO(f.document())
        with self.assertWarns(UserWarning), zipfile.ZipFile(value, 'a') as z:
            z.writestr('word/document.xml', b'<x/>')
        with self.assertRaises(t.Rejected):
            d.extract(value.getvalue())

    def test_expansion_ratio_refused(self):
        value = io.BytesIO()
        with zipfile.ZipFile(value, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name in ('[Content_Types].xml', '_rels/.rels', 'word/document.xml'):
                z.writestr(name, b'a' * 100000)
        with self.assertRaisesRegex(t.Rejected, 'EXPANSION'):
            d.extract(value.getvalue())

    def test_corrupt_deflate_errors_are_fixed_codes(self):
        with patch('zipfile.ZipFile.read', side_effect=d.zlib.error('SYNTHETIC_SENTINEL')):
            with self.assertRaisesRegex(t.Rejected, '^DOCX_ARCHIVE_INVALID$'):
                d.extract(f.document())

    def test_dtd_entity_and_processing_instruction_refused_in_both_encodings(self):
        for prefix in ('<!DOCTYPE w:document [<!ENTITY sample "data">]>', '<?sample data?>'):
            for encoding in ('utf-8', 'utf-16'):
                raw = mutate(f.document(), {'word/document.xml': lambda b: (prefix + b.decode()).encode(encoding)})
                with self.assertRaises(t.Rejected):
                    d.extract(raw)

    def test_fields_tracked_changes_hyperlinks_and_hidden_runs_refused(self):
        for markup in (b'<w:fldSimple/>', b'<w:ins/>', b'<w:hyperlink/>', b'<w:rPr><w:vanish/></w:rPr>'):
            raw = mutate(f.document(), {'word/document.xml': lambda b: b.replace(b'<w:r>', b'<w:r>' + markup, 1)})
            with self.assertRaises(t.Rejected):
                d.extract(raw)

    def test_nested_table_merged_cells_and_grid_omissions_refused(self):
        for markup in (b'<w:tbl/>', b'<w:tcPr><w:gridSpan w:val="2"/></w:tcPr>',
                       b'<w:tcPr><w:vMerge/></w:tcPr>', b'<w:tcPr><w:gridBefore/></w:tcPr>'):
            raw = mutate(f.document(), {'word/document.xml': lambda b: b.replace(b'<w:tc>', b'<w:tc>' + markup, 1)})
            with self.assertRaises(t.Rejected):
                d.extract(raw)

    def test_non_rectangular_table_refused(self):
        raw = f.document([dict(kind='table', rows=[['A', 'B'], ['Only one']])])
        with self.assertRaisesRegex(t.Rejected, 'NOT_RECTANGULAR'):
            d.extract(raw)

    def test_invalid_grid_width_refused(self):
        raw = mutate(f.document(), {'word/document.xml': lambda b: b.replace(b'<w:tbl>', b'<w:tbl><w:tblGrid><w:gridCol/></w:tblGrid>', 1)})
        with self.assertRaisesRegex(t.Rejected, 'GRID_INVALID'):
            d.extract(raw)

    def test_property_payload_cannot_be_silently_dropped(self):
        raw = mutate(f.document(), {'word/document.xml': lambda b: b.replace(b'<w:p>', b'<w:p><w:pPr><w:t>Hidden payload</w:t></w:pPr>', 1)})
        with self.assertRaisesRegex(t.Rejected, 'PROPERTY_PAYLOAD'):
            d.extract(raw)

    def test_unknown_body_and_namespace_refused(self):
        for edit in (lambda b: b.replace(b'<w:body>', b'<w:body><w:unknown/>'),
                     lambda b: b.replace(d.W.encode(), b'urn:fictional:other')):
            with self.assertRaises(t.Rejected):
                d.extract(mutate(f.document(), {'word/document.xml': edit}))

    def test_empty_document_and_empty_table_refused(self):
        for blocks in ([], [dict(kind='table', rows=[])]):
            with self.assertRaises(t.Rejected):
                d.extract(f.document(blocks))

    def test_text_column_and_paragraph_limits(self):
        for blocks in ([dict(kind='paragraph', text='x' * 4097)],
                       [dict(kind='table', rows=[['x'] * 33])],
                       [dict(kind='paragraph', text='x')] * 2001):
            with self.assertRaises(t.Rejected):
                d.extract(f.document(blocks))


if __name__ == '__main__':
    unittest.main()
