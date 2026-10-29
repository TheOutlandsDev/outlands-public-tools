"""Inspect bounded DOCX text/tables and export only explicit content selections."""
import docx_core
import toolkit as t


def inspect(raw, tables=(), include_paragraphs=False):
    t.require(type(tables) in (list, tuple) and all(type(k) is str for k in tables) and
              len(tables) <= 32 and len(set(tables)) == len(tables) and
              type(include_paragraphs) is bool, 'SELECTION_INVALID')
    content = docx_core.extract(raw)
    indexed = {b['id']: b for b in content['blocks'] if b['kind'] == 'table'}
    t.require(set(tables) <= indexed.keys(), 'TABLE_SELECTION_NOT_FOUND')
    return dict(format='outlands-docx-table-extract-v1', status='PASS',
                source_sha256=content['source_sha256'], content_sha256=content['content_sha256'],
                counts=content['counts'],
                table_index=[dict(id=b['id'], position=b['position'], rows=len(b['rows']),
                                  columns=len(b['rows'][0])) for b in indexed.values()],
                selected_tables=[indexed[key] for key in tables],
                selected_paragraphs=[b for b in content['blocks'] if b['kind'] == 'paragraph'] if include_paragraphs else [],
                document_properties_exported=False, external_resources_followed=False,
                document_executed=False)


def main(argv=None):
    parser = t.Parser(prog='docx-table-extractor', description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--table', action='append', default=[])
    parser.add_argument('--include-paragraphs', action='store_true')
    parser.add_argument('--out')
    return t.run(parser, lambda a: inspect(t.read(a.input), a.table, a.include_paragraphs), argv)


if __name__ == '__main__':
    raise SystemExit(main())
