"""Bounded, deliberately narrow OOXML text/table extraction from supplied bytes."""
import io
import posixpath
import re
import struct
import zipfile
import zlib

import toolkit as t

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
C = 'http://schemas.openxmlformats.org/package/2006/content-types'
MAIN_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
FORMAT_PARTS = {'styles', 'settings', 'fontTable', 'numbering'}
PARTS = {'[Content_Types].xml', '_rels/.rels', 'word/document.xml',
         'word/_rels/document.xml.rels', 'docProps/core.xml', 'docProps/app.xml',
         'word/theme/theme1.xml'} | {'word/' + k + '.xml' for k in FORMAT_PARTS}
RELATIONS = {R + '/' + k: 'word/' + k + '.xml' for k in FORMAT_PARTS}
RELATIONS[R + '/theme'] = 'word/theme/theme1.xml'
BLOCKED = {'altChunk', 'hyperlink', 'fldSimple', 'fldChar', 'instrText', 'drawing',
           'pict', 'object', 'sdt', 'ins', 'del', 'moveFrom', 'moveTo', 'vanish',
           'webHidden', 'specVanish', 'gridSpan', 'vMerge', 'hMerge', 'gridBefore',
           'gridAfter', 'pPrChange', 'rPrChange', 'tblPrChange', 'trPrChange', 'tcPrChange',
           'headerReference', 'footerReference', 'footnoteReference', 'endnoteReference',
           'commentReference', 'commentRangeStart', 'commentRangeEnd'}
PROPERTIES = {'pPr', 'rPr', 'tblPr', 'tblGrid', 'trPr', 'tcPr', 'sectPr',
              'bookmarkStart', 'bookmarkEnd'}
CONTENT = {'document', 'body', 'p', 'r', 't', 'tbl', 'tr', 'tc', 'tab', 'br', 'cr'}


def _relations(raw, base, entries, allowed):
    root = t.xml(raw)
    t.require(root.tag == '{' + P + '}Relationships' and not root.attrib,
              'DOCX_RELATIONSHIP_INVALID')
    seen, targets = set(), set()
    for item in root:
        t.require(item.tag == '{' + P + '}Relationship' and len(item) == 0 and
                  set(item.attrib) == {'Id', 'Type', 'Target'}, 'DOCX_RELATIONSHIP_INVALID')
        key, kind, target = (item.attrib[k] for k in ('Id', 'Type', 'Target'))
        t.require(key and key not in seen and kind in allowed and target and
                  not any(c in target for c in '\\:?#%') and '..' not in target.split('/'),
                  'DOCX_RELATIONSHIP_INVALID')
        target = target.lstrip('/') if target.startswith('/') else posixpath.join(base, target)
        t.require(posixpath.normpath(target) == target and target == allowed[kind] and
                  target in entries and target not in targets, 'DOCX_RELATIONSHIP_INVALID')
        seen.add(key); targets.add(target)
    return targets


def package(raw):
    t.require(type(raw) is bytes and len(raw) <= t.MAX_INPUT, 'INPUT_LIMIT')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            t.require(3 <= len(infos) <= 64 and len({x.filename for x in infos}) == len(infos),
                      'DOCX_ARCHIVE_INVALID')
            expanded = 0
            for info in infos:
                expanded += info.file_size
                t.require(info.filename in PARTS and info.compress_type in
                          (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) and not info.flag_bits & 1 and
                          (info.external_attr >> 16) & 0o170000 in (0, 0o100000), 'DOCX_PART_UNSUPPORTED')
                t.require(info.file_size <= 2 * 1024 * 1024 and expanded <= 8 * 1024 * 1024 and
                          info.file_size <= 200 * max(1, info.compress_size), 'DOCX_EXPANSION_LIMIT')
            entries = {info.filename: archive.read(info) for info in infos}
        t.require({'[Content_Types].xml', '_rels/.rels', 'word/document.xml'} <= entries.keys(),
                  'DOCX_REQUIRED_PART_MISSING')
        types = t.xml(entries['[Content_Types].xml'])
        t.require(types.tag == '{' + C + '}Types' and not types.attrib, 'DOCX_CONTENT_TYPES_INVALID')
        overrides, defaults = {}, set()
        for item in types:
            if item.tag == '{' + C + '}Override':
                t.require(set(item.attrib) == {'PartName', 'ContentType'} and len(item) == 0,
                          'DOCX_CONTENT_TYPES_INVALID')
                name = item.attrib['PartName']
                t.require(name.startswith('/') and name[1:] in entries and name not in overrides,
                          'DOCX_CONTENT_TYPES_INVALID')
                overrides[name] = item.attrib['ContentType']
            elif item.tag == '{' + C + '}Default':
                t.require(set(item.attrib) == {'Extension', 'ContentType'} and len(item) == 0 and
                          item.attrib['Extension'] in ('xml', 'rels') and
                          item.attrib['Extension'] not in defaults, 'DOCX_CONTENT_TYPES_INVALID')
                defaults.add(item.attrib['Extension'])
            else:
                raise t.Rejected('DOCX_CONTENT_TYPES_INVALID')
            t.require(not any(k in item.attrib['ContentType'].casefold() for k in
                              ('macro', 'vba', 'activex', 'template')), 'DOCX_ACTIVE_CONTENT')
        t.require(overrides.get('/word/document.xml') == MAIN_TYPE, 'DOCX_MAIN_TYPE_INVALID')
        root_allowed = {R + '/officeDocument': 'word/document.xml',
                        P + '/metadata/core-properties': 'docProps/core.xml',
                        R + '/extended-properties': 'docProps/app.xml'}
        targets = _relations(entries['_rels/.rels'], '', entries, root_allowed)
        t.require('word/document.xml' in targets, 'DOCX_MAIN_RELATIONSHIP_MISSING')
        if 'word/_rels/document.xml.rels' in entries:
            targets |= _relations(entries['word/_rels/document.xml.rels'], 'word', entries, RELATIONS)
        t.require(set(entries) - {'[Content_Types].xml', '_rels/.rels', 'word/_rels/document.xml.rels'} == targets,
                  'DOCX_UNBOUND_PART')
        # Metadata/format parts are bounded opaque bytes and are never returned,
        # rendered, evaluated or used to resolve additional files/URLs.
        return entries['word/document.xml']
    except t.Rejected:
        raise
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError, NotImplementedError,
            EOFError, struct.error, zlib.error):
        raise t.Rejected('DOCX_ARCHIVE_INVALID') from None


def _tag(element):
    t.require(element.tag.startswith('{' + W + '}'), 'DOCX_NAMESPACE_UNSUPPORTED')
    return element.tag[len(W) + 2:]


def _structural_text(element):
    t.require(not (element.text or '').strip() and not (element.tail or '').strip(),
              'DOCX_MIXED_TEXT_UNSUPPORTED')


def paragraph(element):
    values = []
    for child in element:
        kind = _tag(child)
        if kind in ('pPr', 'bookmarkStart', 'bookmarkEnd'):
            continue
        t.require(kind == 'r', 'DOCX_PARAGRAPH_FEATURE_UNSUPPORTED')
        _structural_text(child)
        for part in child:
            kind = _tag(part)
            if kind == 'rPr':
                continue
            t.require(len(part) == 0, 'DOCX_RUN_FEATURE_UNSUPPORTED')
            if kind == 't':
                t.require(set(part.attrib) <= {'{http://www.w3.org/XML/1998/namespace}space'},
                          'DOCX_RUN_FEATURE_UNSUPPORTED')
                values.append(part.text or '')
            elif kind in ('tab', 'br', 'cr'):
                t.require(not part.attrib and not (part.text or ''), 'DOCX_BREAK_UNSUPPORTED')
                values.append('\t' if kind == 'tab' else '\n')
            else:
                raise t.Rejected('DOCX_RUN_FEATURE_UNSUPPORTED')
    value = ''.join(values)
    t.require(len(value) <= 4096, 'DOCX_TEXT_LIMIT')
    return value


def table(element):
    rows, width, properties, grid_width = [], None, set(), None
    for row in element:
        kind = _tag(row)
        if kind in ('tblPr', 'tblGrid'):
            t.require(kind not in properties and not rows, 'DOCX_TABLE_PROPERTIES_INVALID')
            properties.add(kind)
            if kind == 'tblGrid':
                t.require(1 <= len(row) <= 32 and all(_tag(x) == 'gridCol' and not len(x)
                          for x in row), 'DOCX_GRID_INVALID')
                grid_width = len(row)
            continue
        t.require(kind == 'tr' and len(rows) < 1001, 'DOCX_TABLE_FEATURE_UNSUPPORTED')
        values = []
        for cell in row:
            kind = _tag(cell)
            if kind == 'trPr':
                continue
            t.require(kind == 'tc' and len(values) < 32, 'DOCX_ROW_FEATURE_UNSUPPORTED')
            paragraphs = []
            for part in cell:
                kind = _tag(part)
                if kind == 'tcPr':
                    continue
                t.require(kind == 'p', 'DOCX_NESTED_OR_UNSUPPORTED_CELL')
                paragraphs.append(paragraph(part))
            t.require(paragraphs, 'DOCX_CELL_INVALID')
            value = '\n'.join(paragraphs)
            t.require(len(value) <= 4096, 'DOCX_TEXT_LIMIT')
            values.append(value)
        t.require(values and (width is None or width == len(values)), 'DOCX_TABLE_NOT_RECTANGULAR')
        width = len(values)
        rows.append(values)
    t.require(rows, 'DOCX_EMPTY_TABLE')
    t.require(grid_width is None or grid_width == width, 'DOCX_GRID_INVALID')
    return rows


def extract(raw):
    root = t.xml(package(raw))
    t.require(root.tag == '{' + W + '}document' and len(root) == 1 and
              root[0].tag == '{' + W + '}body', 'DOCX_DOCUMENT_INVALID')
    for element in root.iter():
        kind = _tag(element)
        t.require(kind not in BLOCKED, 'DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT')
        if kind in PROPERTIES:
            t.require(not any(_tag(child) in CONTENT for child in list(element.iter())[1:]),
                      'DOCX_PROPERTY_PAYLOAD_UNSUPPORTED')
        # Actual text belongs only to w:t. Properties may have attributes but
        # must not carry silently omitted text payloads.
        if kind != 't':
            _structural_text(element)
        else:
            t.require(not (element.tail or '').strip(), 'DOCX_MIXED_TEXT_UNSUPPORTED')
    blocks = []
    paragraphs = tables = cells = rows = chars = 0
    children = list(root[0])
    for position, element in enumerate(children, 1):
        kind = _tag(element)
        if kind == 'sectPr':
            t.require(position == len(children), 'DOCX_SECTION_FEATURE_UNSUPPORTED')
            continue
        if kind == 'p':
            paragraphs += 1
            value = paragraph(element); chars += len(value)
            blocks.append(dict(id='paragraph-' + str(paragraphs), position=len(blocks) + 1,
                               kind='paragraph', text=value))
        elif kind == 'tbl':
            tables += 1
            values = table(element)
            rows += len(values); cells += sum(map(len, values))
            chars += sum(len(v) for row in values for v in row)
            blocks.append(dict(id='table-' + str(tables), position=len(blocks) + 1,
                               kind='table', rows=values))
        else:
            raise t.Rejected('DOCX_BODY_FEATURE_UNSUPPORTED')
        t.require(paragraphs <= 2000 and tables <= 32 and cells <= 20000 and chars <= 1024 * 1024,
                  'DOCX_CONTENT_LIMIT')
    t.require(blocks, 'DOCX_EMPTY_DOCUMENT')
    return dict(format='outlands-docx-content-v1', source_sha256=t.digest(raw),
                content_sha256=t.digest(t.encode(blocks)), blocks=blocks,
                counts=dict(paragraphs=paragraphs, tables=tables, rows=rows, cells=cells),
                document_properties_exported=False, external_resources_followed=False)
