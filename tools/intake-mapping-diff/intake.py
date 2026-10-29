"""Preview caller-mapped CSV or a bounded plain-cell XLSX subset, offline."""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import date
from decimal import Decimal
import io
import posixpath
import re
import zipfile

import toolkit as t

S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
C = 'http://schemas.openxmlformats.org/package/2006/content-types'


def mapping(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'identity', 'fields', 'unknown_columns'})
    t.require(value['format'] == 'outlands-table-map-v1' and
              value['unknown_columns'] in ('reject', 'ignore'), 'MAP_INVALID')
    fields = value['fields']
    t.require(type(fields) is list and 1 <= len(fields) <= 32, 'MAP_INVALID')
    for field in fields:
        t.fields(field, {'source', 'target', 'type', 'required'})
        t.require(type(field['source']) is str and 0 < len(field['source']) <= 256 and
                  all(ord(c) >= 32 and ord(c) != 127 for c in field['source']), 'MAP_INVALID')
        t.identifier(field['target'])
        t.require(field['type'] in ('text', 'integer', 'decimal', 'boolean', 'date') and
                  type(field['required']) is bool, 'MAP_INVALID')
    for name in ('source', 'target'):
        t.require(len({f[name] for f in fields}) == len(fields), 'MAP_DUPLICATE_FIELD')
    identity = value['identity']
    t.require(type(identity) is list and 1 <= len(identity) <= 4 and
              all(type(k) is str for k in identity) and len(set(identity)) == len(identity),
              'MAP_IDENTITY_INVALID')
    required = {f['target'] for f in fields if f['required']}
    t.require(set(identity) <= required, 'MAP_IDENTITY_INVALID')
    return value


def csv_rows(raw):
    t.require(type(raw) is bytes and len(raw) <= t.MAX_INPUT, 'INPUT_LIMIT')
    try:
        text = raw.decode('utf-8-sig')
        t.require('\x00' not in text, 'CSV_INVALID')
        reader = csv.reader(io.StringIO(text, newline=''), strict=True)
        rows = []
        for row in reader:
            t.require(len(rows) < 1001 and len(row) <= 32 and
                      all(len(cell) <= 4096 for cell in row), 'TABLE_LIMIT')
            rows.append(row)
        return rows
    except (csv.Error, UnicodeError):
        raise t.Rejected('CSV_INVALID') from None


def _target(base, target):
    t.require(type(target) is str and target and '\\' not in target and
              not any(c in target for c in ':?#%') and
              '..' not in target.split('/'), 'XLSX_RELATIONSHIP_INVALID')
    result = target.lstrip('/') if target.startswith('/') else posixpath.join(base, target)
    t.require(posixpath.normpath(result) == result and not result.startswith('/'),
              'XLSX_RELATIONSHIP_INVALID')
    return result


def _relations(raw, base, entries, allowed):
    root = t.xml(raw)
    t.require(root.tag == '{' + P + '}Relationships' and not root.attrib,
              'XLSX_RELATIONSHIP_INVALID')
    result = {}
    for item in root:
        t.require(item.tag == '{' + P + '}Relationship' and len(item) == 0 and
                  set(item.attrib) == {'Id', 'Type', 'Target'}, 'XLSX_RELATIONSHIP_INVALID')
        key, kind = item.attrib['Id'], item.attrib['Type']
        t.require(key and key not in result and kind in allowed, 'XLSX_RELATIONSHIP_INVALID')
        target = _target(base, item.attrib['Target'])
        t.require(target in entries, 'XLSX_RELATIONSHIP_INVALID')
        result[key] = (kind, target)
    t.require(len({v[1] for v in result.values()}) == len(result), 'XLSX_RELATIONSHIP_INVALID')
    return result


def _plain_string(element):
    t.require(not element.attrib and len(element) == 1 and element[0].tag == '{' + S + '}t' and
              len(element[0]) == 0 and set(element[0].attrib) <= {'{http://www.w3.org/XML/1998/namespace}space'},
              'XLSX_RICH_STRING_UNSUPPORTED')
    text = element[0].text or ''
    t.require(len(text) <= 4096, 'TABLE_LIMIT')
    return text


def _sheet(raw, shared):
    root = t.xml(raw)
    t.require(root.tag == '{' + S + '}worksheet' and not root.attrib, 'XLSX_SHEET_INVALID')
    t.require(all(x.tag in {'{' + S + '}' + k for k in
                  ('sheetData', 'dimension', 'sheetViews', 'sheetFormatPr', 'pageMargins', 'cols', 'sheetPr')}
                  for x in root), 'XLSX_SHEET_FEATURE_UNSUPPORTED')
    for item in root.iter():
        t.require(item.tag not in {'{' + S + '}' + k for k in ('f', 'formula', 'mergeCell', 'hyperlink')} and
                  item.attrib.get('hidden', '0') not in ('1', 'true'), 'XLSX_ACTIVE_OR_HIDDEN_CONTENT')
    tables = root.findall('{' + S + '}sheetData')
    t.require(len(tables) == 1 and not tables[0].attrib, 'XLSX_SHEET_INVALID')
    rows, cells = [], 0
    for row in tables[0]:
        t.require(row.tag == '{' + S + '}row' and row.attrib.get('r') == str(len(rows) + 1) and
                  set(row.attrib) <= {'r', 'spans', 'ht', 'customHeight', 's', 'customFormat'},
                  'XLSX_ROW_INVALID')
        values, last = [], 0
        for cell in row:
            cells += 1
            t.require(cells <= 20000 and cell.tag == '{' + S + '}c' and
                      set(cell.attrib) <= {'r', 't', 's'}, 'XLSX_CELL_INVALID')
            match = re.fullmatch(r'([A-Z]{1,2})([1-9][0-9]{0,3})', cell.attrib.get('r', ''))
            t.require(match and int(match[2]) == len(rows) + 1, 'XLSX_CELL_INVALID')
            column = 0
            for char in match[1]:
                column = column * 26 + ord(char) - 64
            t.require(last < column <= 32, 'XLSX_CELL_ORDER_INVALID')
            values.extend([''] * (column - last - 1))
            kind = cell.attrib.get('t', 'n')
            if kind == 'inlineStr':
                t.require(len(cell) == 1 and cell[0].tag == '{' + S + '}is', 'XLSX_CELL_INVALID')
                value = _plain_string(cell[0])
            elif not len(cell):
                t.require(kind == 'n', 'XLSX_CELL_INVALID')
                value = ''
            else:
                t.require(len(cell) == 1 and cell[0].tag == '{' + S + '}v' and
                          not cell[0].attrib and len(cell[0]) == 0, 'XLSX_CELL_INVALID')
                value = cell[0].text or ''
                if kind == 's':
                    t.require(re.fullmatch(r'0|[1-9][0-9]{0,4}', value) and
                              int(value) < len(shared), 'XLSX_SHARED_STRING_INVALID')
                    value = shared[int(value)]
                elif kind == 'b':
                    t.require(value in ('0', '1'), 'XLSX_BOOLEAN_INVALID')
                    value = 'true' if value == '1' else 'false'
                elif kind == 'n':
                    t.require(re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', value),
                              'XLSX_NUMBER_INVALID')
                elif kind == 'd':
                    t.require(len(value) <= 64, 'XLSX_DATE_INVALID')
                else:
                    raise t.Rejected('XLSX_CELL_TYPE_UNSUPPORTED')
            t.require(len(value) <= 4096, 'TABLE_LIMIT')
            values.append(value)
            last = column
        rows.append(values)
        t.require(len(rows) <= 1001, 'TABLE_LIMIT')
    return rows


def xlsx_rows(raw, sheet):
    t.require(type(raw) is bytes and len(raw) <= t.MAX_INPUT and
              type(sheet) is str and 0 < len(sheet) <= 31, 'XLSX_SELECTION_INVALID')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            t.require(4 <= len(infos) <= 64 and len({i.filename for i in infos}) == len(infos),
                      'XLSX_ARCHIVE_INVALID')
            expanded = 0
            for item in infos:
                name = item.filename
                t.require(re.fullmatch(r'(?:\[Content_Types\]\.xml|_rels/\.rels|docProps/(?:core|app)\.xml|xl/(?:workbook\.xml|styles\.xml|sharedStrings\.xml|_rels/workbook\.xml\.rels|worksheets/sheet[1-9][0-9]?\.xml))', name),
                          'XLSX_PART_UNSUPPORTED')
                t.require(item.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) and
                          not item.flag_bits & 1 and not (item.external_attr >> 16) & 0o170000 == 0o120000,
                          'XLSX_ARCHIVE_INVALID')
                expanded += item.file_size
                t.require(item.file_size <= 2 * 1024 * 1024 and expanded <= 8 * 1024 * 1024 and
                          item.file_size <= 200 * max(1, item.compress_size), 'XLSX_EXPANSION_LIMIT')
            entries = {i.filename: archive.read(i) for i in infos}
        needed = {'[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml', 'xl/_rels/workbook.xml.rels'}
        t.require(needed <= entries.keys(), 'XLSX_PART_MISSING')
        types = t.xml(entries['[Content_Types].xml'])
        t.require(types.tag == '{' + C + '}Types', 'XLSX_CONTENT_TYPES_INVALID')
        for item in types:
            t.require(item.tag in ('{' + C + '}Default', '{' + C + '}Override') and
                      not any(word in item.attrib.get('ContentType', '').casefold()
                              for word in ('macro', 'vba', 'activex')), 'XLSX_CONTENT_TYPES_INVALID')
        relations = _relations(entries['_rels/.rels'], '', entries,
                               {R + '/officeDocument', P + '/metadata/core-properties', R + '/extended-properties'})
        t.require([v[1] for v in relations.values() if v[0] == R + '/officeDocument'] == ['xl/workbook.xml'],
                  'XLSX_WORKBOOK_INVALID')
        relations = _relations(entries['xl/_rels/workbook.xml.rels'], 'xl', entries,
                               {R + '/worksheet', R + '/styles', R + '/sharedStrings'})
        shared_targets = [target for kind, target in relations.values() if kind == R + '/sharedStrings']
        t.require(shared_targets in ([], ['xl/sharedStrings.xml']), 'XLSX_SHARED_STRING_INVALID')
        t.require(('xl/sharedStrings.xml' in entries) == bool(shared_targets), 'XLSX_SHARED_STRING_INVALID')
        shared = []
        if shared_targets:
            root = t.xml(entries[shared_targets[0]])
            t.require(root.tag == '{' + S + '}sst' and len(root) <= 20000 and
                      all(x.tag == '{' + S + '}si' for x in root), 'XLSX_SHARED_STRING_INVALID')
            shared = [_plain_string(x) for x in root]
        workbook = t.xml(entries['xl/workbook.xml'])
        t.require(workbook.tag == '{' + S + '}workbook' and not workbook.attrib and
                  all(x.tag in {'{' + S + '}' + k for k in
                      ('workbookPr', 'bookViews', 'sheets', 'calcPr', 'definedNames')} for x in workbook) and
                  all(not len(x) for x in workbook.findall('{' + S + '}definedNames')),
                  'XLSX_WORKBOOK_FEATURE_UNSUPPORTED')
        sheet_sets = workbook.findall('{' + S + '}sheets')
        t.require(len(sheet_sets) == 1 and 1 <= len(sheet_sets[0]) <= 16, 'XLSX_WORKBOOK_INVALID')
        names, targets, sheet_ids, selected = set(), set(), set(), None
        for item in sheet_sets[0]:
            t.require(item.tag == '{' + S + '}sheet' and
                      set(item.attrib) <= {'name', 'sheetId', '{' + R + '}id', 'state'} and
                      {'name', 'sheetId', '{' + R + '}id'} <= item.attrib.keys(), 'XLSX_SHEET_INVALID')
            name, rid = item.attrib['name'], item.attrib['{' + R + '}id']
            sid = item.attrib['sheetId']
            t.require(1 <= len(name) <= 31 and all(ord(c) >= 32 and c not in '[]:*?/\\' for c in name) and
                      re.fullmatch(r'[1-9][0-9]{0,8}', sid) and sid not in sheet_ids and
                      name.casefold() not in names and rid in relations and
                      relations[rid][0] == R + '/worksheet', 'XLSX_SHEET_INVALID')
            target = relations[rid][1]
            t.require(target not in targets and item.attrib.get('state', 'visible') == 'visible',
                      'XLSX_ACTIVE_OR_HIDDEN_CONTENT')
            names.add(name.casefold()); targets.add(target); sheet_ids.add(sid)
            rows = _sheet(entries[target], shared)
            if name == sheet:
                selected = rows
        t.require(targets == {n for n in entries if n.startswith('xl/worksheets/')}, 'XLSX_UNBOUND_SHEET')
        t.require(selected is not None, 'XLSX_SHEET_NOT_FOUND')
        return selected
    except t.Rejected:
        raise
    except (zipfile.BadZipFile, RuntimeError, OSError, ValueError, NotImplementedError):
        raise t.Rejected('XLSX_INVALID') from None


def _convert(value, field):
    if value == '':
        t.require(not field['required'], 'REQUIRED_VALUE_MISSING')
        return None
    t.require(type(value) is str and len(value) <= 256 and
              all(ord(c) >= 32 and ord(c) != 127 for c in value), 'VALUE_TEXT_INVALID')
    kind = field['type']
    if kind == 'integer':
        t.require(re.fullmatch(r'0|-?[1-9][0-9]{0,12}', value) and abs(int(value)) <= 10**12,
                  'VALUE_INTEGER_INVALID')
        return int(value)
    if kind == 'decimal':
        t.require(re.fullmatch(r'-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?', value) and
                  abs(Decimal(value)) <= 10**12, 'VALUE_DECIMAL_INVALID')
        return format(Decimal(value).normalize(), 'f')
    if kind == 'boolean':
        t.require(value in ('true', 'false'), 'VALUE_BOOLEAN_INVALID')
        return value == 'true'
    if kind == 'date':
        t.require(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value), 'VALUE_DATE_INVALID')
        try:
            date.fromisoformat(value)
        except ValueError:
            raise t.Rejected('VALUE_DATE_INVALID') from None
    return value


def preview(raw, contract_raw, kind, sheet=None):
    contract = mapping(contract_raw)
    t.require(kind in ('csv', 'xlsx') and (kind == 'xlsx' or sheet is None), 'FORMAT_INVALID')
    rows = csv_rows(raw) if kind == 'csv' else xlsx_rows(raw, sheet)
    t.require(rows and 1 <= len(rows[0]) <= 32 and all(rows[0]) and
              len(set(rows[0])) == len(rows[0]), 'HEADER_INVALID')
    header = rows[0]
    sources = {field['source'] for field in contract['fields']}
    t.require(sources <= set(header), 'MAPPED_HEADER_MISSING')
    unknown = len(set(header) - sources)
    t.require(not unknown or contract['unknown_columns'] == 'ignore', 'UNMAPPED_HEADER')
    groups, issues, rejected = defaultdict(list), [], 0
    for position, row in enumerate(rows[1:], 2):
        if kind == 'xlsx' and len(row) <= len(header):
            row = row + [''] * (len(header) - len(row))
        try:
            t.require(len(row) == len(header), 'ROW_WIDTH_INVALID')
            values = dict(zip(header, row))
            record = {field['target']: _convert(values[field['source']], field)
                      for field in contract['fields']}
            key = t.encode([record[k] for k in contract['identity']])
            groups[key].append((position, record))
        except t.Rejected as error:
            rejected += 1
            issues.append({'row': position, 'code': str(error)})
    accepted, duplicates, conflicts = [], 0, 0
    for key in sorted(groups):
        entries = groups[key]
        if len({t.encode(record) for _, record in entries}) != 1:
            conflicts += len(entries)
            issues.extend({'row': pos, 'code': 'IDENTITY_CONFLICT'} for pos, _ in entries)
        else:
            accepted.append({'record': entries[0][1], 'source_rows': [pos for pos, _ in entries]})
            duplicates += len(entries) - 1
    counts = dict(input_rows=len(rows) - 1, accepted_records=len(accepted),
                  duplicate_rows=duplicates, rejected_rows=rejected, conflict_rows=conflicts)
    t.require(counts['input_rows'] == len(accepted) + duplicates + rejected + conflicts,
              'ACCOUNTING_FAILED')
    status = 'PASS' if accepted and not issues else 'REVIEW_REQUIRED'
    return dict(format='outlands-intake-preview-v1', status=status, source_sha256=t.digest(raw),
                mapping_sha256=t.digest(contract_raw), source_format=kind, sheet=sheet,
                mapping=contract['fields'], ignored_columns=unknown, counts=counts,
                accepted=accepted, issues=sorted(issues, key=lambda r: r['row']),
                ready_for_explicit_review=status == 'PASS', imported=False)


def main(argv=None):
    parser = t.Parser(prog='workbook-intake-checker', description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--mapping', required=True)
    parser.add_argument('--format', required=True, choices=('csv', 'xlsx'))
    parser.add_argument('--sheet')
    parser.add_argument('--out')
    return t.run(parser, lambda a: preview(t.read(a.input), t.read(a.mapping), a.format, a.sheet), argv)


if __name__ == '__main__':
    raise SystemExit(main())
