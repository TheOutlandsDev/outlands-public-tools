"""Generate invented text/table DOCX bytes; no document assets are bundled."""
import io
import json
import zipfile
from xml.sax.saxutils import escape

import toolkit as t

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
C = 'http://schemas.openxmlformats.org/package/2006/content-types'


def document(blocks=None, *, author='Fictional Author', bold=False):
    if blocks is None:
        blocks = [{'kind': 'paragraph', 'text': 'Fictional intake example.'},
                  {'kind': 'table', 'rows': [['Record', 'Units', 'Due', 'Active'],
                   ['sample-a', '12', '2030-01-10', 'true'],
                   ['sample-b', '7', '2030-01-11', 'false'],
                   ['sample-a', '12', '2030-01-10', 'true']]}]
    def paragraph(value):
        return '<w:p><w:r>' + ('<w:rPr><w:b/></w:rPr>' if bold else '') + '<w:t xml:space="preserve">' + escape(value) + '</w:t></w:r></w:p>'
    body = []
    for block in blocks:
        if block['kind'] == 'paragraph':
            body.append(paragraph(block['text']))
        else:
            rows = ['<w:tr>' + ''.join('<w:tc>' + paragraph(v) + '</w:tc>' for v in row) + '</w:tr>'
                    for row in block['rows']]
            body.append('<w:tbl>' + ''.join(rows) + '</w:tbl>')
    parts = {
        '[Content_Types].xml': '<Types xmlns="' + C + '"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>',
        '_rels/.rels': '<Relationships xmlns="' + P + '"><Relationship Id="main" Type="' + R + '/officeDocument" Target="word/document.xml"/><Relationship Id="core" Type="' + P + '/metadata/core-properties" Target="docProps/core.xml"/></Relationships>',
        'word/document.xml': '<w:document xmlns:w="' + W + '"><w:body>' + ''.join(body) + '</w:body></w:document>',
        'docProps/core.xml': '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>' + escape(author) + '</dc:creator></cp:coreProperties>'}
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as archive:
        for name, value in sorted(parts.items()):
            info = zipfile.ZipInfo(name, date_time=(2030, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, value.encode('utf-8'))
    return result.getvalue()


def main(argv=None):
    parser = t.Parser(prog='fictional-docx', description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--variant', choices=('before', 'after', 'needs-review', 'formatting'), default='before')
    try:
        args = parser.parse_args(argv)
        blocks = None
        if args.variant in ('after', 'needs-review'):
            rows = [['Record', 'Units', 'Due', 'Active']]
            rows += ([['sample-a', '14', '2030-01-10', 'true'], ['sample-c', '5', '2030-01-12', 'true']]
                     if args.variant == 'after' else
                     [['sample-a', '12', '2030-01-10', 'true'], ['sample-a', '13', '2030-01-10', 'true'],
                      ['sample-c', 'invalid', '2030-01-12', 'true']])
            blocks = [{'kind': 'paragraph', 'text': 'Fictional revised intake example.'}, {'kind': 'table', 'rows': rows}]
        raw = document(blocks, bold=args.variant == 'formatting')
        t.write_new(args.out, raw)
        print(json.dumps(dict(status='PASS', fictional=True, bytes=len(raw), sha256=t.digest(raw))))
        return 0
    except KeyboardInterrupt:
        print('{"status":"ERROR","code":"INTERRUPTED"}')
        return 130
    except t.Rejected as error:
        print(json.dumps(dict(status='ERROR', code=str(error))))
        return 2
    except (OSError, TypeError, ValueError):
        print('{"status":"ERROR","code":"OUTPUT_REFUSED"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
