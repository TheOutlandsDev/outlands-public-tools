"""Map one explicitly selected DOCX table through the public typed intake rules."""
import csv
import io

import docx_core
import intake
import toolkit as t


def preview(raw, mapping_raw, table_id):
    t.require(type(table_id) is str, 'TABLE_SELECTION_INVALID')
    content = docx_core.extract(raw)
    selected = next((b for b in content['blocks'] if b['kind'] == 'table' and b['id'] == table_id), None)
    t.require(selected is not None, 'TABLE_SELECTION_NOT_FOUND')
    output = io.StringIO(newline='')
    csv.writer(output, lineterminator='\n').writerows(selected['rows'])
    csv_raw = output.getvalue().encode('utf-8')
    result = intake.preview(csv_raw, mapping_raw, 'csv')
    result.update(format='outlands-document-intake-v1', source_format='docx-table',
                  source_sha256=t.digest(raw), normalized_table_sha256=t.digest(csv_raw),
                  content_sha256=content['content_sha256'], selected_table=table_id,
                  table_position=selected['position'], source_row_basis='ONE_BASED_SELECTED_TABLE_ROW',
                  document_properties_exported=False, source_transformed=False)
    del result['sheet']
    return result


def main(argv=None):
    parser = t.Parser(prog='document-intake-checker', description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--mapping', required=True)
    parser.add_argument('--table', required=True)
    parser.add_argument('--out')
    return t.run(parser, lambda a: preview(t.read(a.input), t.read(a.mapping), a.table), argv)


if __name__ == '__main__':
    raise SystemExit(main())
