"""Generate a minimal invented XLSX in memory; no real workbook is bundled."""
import io
import json
import zipfile
from xml.sax.saxutils import escape

import toolkit as t

S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
C = 'http://schemas.openxmlformats.org/package/2006/content-types'


def workbook(rows=None, *, shared=False):
    if rows is None:
        rows = [['Record', 'Units', 'Due', 'Active'], ['sample-a', '12', '2030-01-10', 'true'],
                ['sample-b', '7', '2030-01-11', 'false'], ['sample-a', '12', '2030-01-10', 'true']]
    values = list(dict.fromkeys(value for row in rows for value in row))
    items = []
    for r, row in enumerate(rows, 1):
        cells = []
        for c, value in enumerate(row, 1):
            ref = chr(64 + c) + str(r)
            if shared:
                cells.append('<c r="' + ref + '" t="s"><v>' + str(values.index(value)) + '</v></c>')
            else:
                cells.append('<c r="' + ref + '" t="inlineStr"><is><t>' + escape(value) + '</t></is></c>')
        items.append('<row r="' + str(r) + '">' + ''.join(cells) + '</row>')
    parts = {
        '[Content_Types].xml': '<Types xmlns="' + C + '"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' + ('<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>' if shared else '') + '</Types>',
        '_rels/.rels': '<Relationships xmlns="' + P + '"><Relationship Id="rId1" Type="' + R + '/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': '<workbook xmlns="' + S + '" xmlns:r="' + R + '"><sheets><sheet name="Records" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<Relationships xmlns="' + P + '"><Relationship Id="rId1" Type="' + R + '/worksheet" Target="worksheets/sheet1.xml"/>' + ('<Relationship Id="rId2" Type="' + R + '/sharedStrings" Target="sharedStrings.xml"/>' if shared else '') + '</Relationships>',
        'xl/worksheets/sheet1.xml': '<worksheet xmlns="' + S + '"><sheetData>' + ''.join(items) + '</sheetData></worksheet>'}
    if shared:
        parts['xl/sharedStrings.xml'] = '<sst xmlns="' + S + '">' + ''.join('<si><t>' + escape(v) + '</t></si>' for v in values) + '</sst>'
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as archive:
        for name, text in sorted(parts.items()):
            info = zipfile.ZipInfo(name, date_time=(2030, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text.encode('utf-8'))
    return result.getvalue()


def main(argv=None):
    parser = t.Parser(prog='fictional-workbook', description=__doc__)
    parser.add_argument('--out', required=True)
    try:
        args = parser.parse_args(argv)
        raw = workbook()
        t.write_new(args.out, raw)
        print(json.dumps(dict(status='PASS', fictional=True, bytes=len(raw), sha256=t.digest(raw))))
        return 0
    except t.Rejected as error:
        print(json.dumps(dict(status='ERROR', code=str(error))))
        return 2
    except (OSError, ValueError, TypeError):
        print('{"status":"ERROR","code":"OUTPUT_REFUSED"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
