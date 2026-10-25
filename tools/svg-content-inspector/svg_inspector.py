"""Inspect a bounded SVG text subset without rendering or opening references."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import html
import json
import os
from pathlib import Path
import re
import stat
import unicodedata
from xml.parsers import expat

SVG = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
XML = 'http://www.w3.org/XML/1998/namespace'
MAX_BYTES = 2 * 1024 * 1024
MAX_DEPTH = 64
MAX_NODES = 20_000
MAX_ATTRIBUTES = 100_000
MAX_NODE_ATTRIBUTES = 64
MAX_ATTRIBUTE_CHARS = 16_384
MAX_TEXT_CHARS = 1024 * 1024
MAX_STYLE_CHARS = 65_536
MAX_TOTAL_STYLE_CHARS = 262_144
MAX_REFERENCES = 2_000
MAX_FINDINGS = 2_000
MAX_REPORT_BYTES = 8 * 1024 * 1024
MIN_EXPAT = (2, 7, 2)
NUMBER = r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
NUM = re.compile(NUMBER + r'\Z')
LENGTH = re.compile(r'(?P<number>' + NUMBER + r')(?P<unit>%|[A-Za-z]+)?\Z')
VIEWBOX = re.compile(r'\s*(' + NUMBER + r')(?:\s*,\s*|\s+)(' + NUMBER + r')(?:\s*,\s*|\s+)('
                     + NUMBER + r')(?:\s*,\s*|\s+)(' + NUMBER + r')\s*\Z')
FRAGMENT = re.compile(r'[A-Za-z_][A-Za-z0-9_.:-]{0,127}\Z')
CSS_IDENT = re.compile(r'[-_A-Za-z][-_A-Za-z0-9]*')
KNOWN = frozenset(('svg g defs symbol use path rect circle ellipse line polyline polygon text tspan textPath '
                  'title desc metadata a image linearGradient radialGradient stop pattern clipPath mask filter '
                  'marker view switch style script foreignObject animate animateMotion animateTransform set mpath '
                  'feBlend feColorMatrix feComponentTransfer feComposite feConvolveMatrix feDiffuseLighting '
                  'feDisplacementMap feDistantLight feDropShadow feFlood feFuncA feFuncB feFuncG feFuncR '
                  'feGaussianBlur feImage feMerge feMergeNode feMorphology feOffset fePointLight '
                  'feSpecularLighting feSpotLight feTile feTurbulence').split())
ACTIVE = frozenset(('script', 'foreignObject', 'animate', 'animateMotion', 'animateTransform', 'set', 'mpath'))
URL_ATTRIBUTES = frozenset(('fill', 'stroke', 'filter', 'clip-path', 'mask', 'marker', 'marker-start',
                            'marker-mid', 'marker-end', 'cursor', 'color-profile'))
LENGTH_UNITS = frozenset(('', '%', 'px', 'em', 'ex', 'cm', 'mm', 'in', 'pt', 'pc', 'q', 'rem', 'ch',
                          'vw', 'vh', 'vmin', 'vmax'))


class InspectionError(Exception):
    """Only fixed codes are exposed; input content never becomes an error."""


def require(condition, code):
    if not condition:
        raise InspectionError(code)


def local_path(value):
    path = Path(value)
    raw = str(value)
    require(path.is_absolute() and '..' not in path.parts and not raw.startswith(('\\\\', '//')),
            'LOCAL_ABSOLUTE_PATH_REQUIRED')
    require(not any(unicodedata.category(c).startswith('C') for c in raw), 'INVALID_LOCAL_PATH')
    require(os.name != 'nt' or ':' not in raw[2:], 'DEVICE_OR_STREAM_PATH_REJECTED')
    return path


def linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def no_links(path):
    for item in reversed((path, *path.parents)):
        require(not linked(item.lstat()), 'LINKED_PATH_REJECTED')


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def snapshot(value):
    path = local_path(value)
    no_links(path)
    expected = path.lstat()
    require(stat.S_ISREG(expected.st_mode), 'REGULAR_INPUT_REQUIRED')
    require(expected.st_size <= MAX_BYTES, 'INPUT_BYTE_LIMIT')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and not linked(before), 'REGULAR_INPUT_REQUIRED')
        require(identity(expected) == identity(before), 'INPUT_CHANGED')
        data = bytearray()
        while True:
            block = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
            if not block:
                break
            data.extend(block)
            require(len(data) <= MAX_BYTES, 'INPUT_BYTE_LIMIT')
        after = os.fstat(fd)
        require(len(data) == before.st_size and identity(before) == identity(after)
                and before.st_ctime_ns == after.st_ctime_ns and identity(after) == identity(path.lstat()), 'INPUT_CHANGED')
        return bytes(data)
    finally:
        os.close(fd)


def check_runtime():
    # The security floor follows Python's XML-security guidance. It is necessary,
    # not a claim that every future parser bug or SVG rendering issue is excluded.
    require(tuple(expat.version_info) >= MIN_EXPAT, 'EXPAT_SECURITY_UPDATE_REQUIRED')


def decimal_token(text):
    require(len(text) <= 64 and NUM.fullmatch(text) is not None, 'INVALID_DIMENSION_TOKEN')
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise InspectionError('INVALID_DIMENSION_TOKEN') from None
    require(value.is_finite() and abs(value.as_tuple().exponent) <= 64 and abs(value) <= Decimal('1e12'),
            'DIMENSION_VALUE_LIMIT')
    return value


def decimal_text(value):
    # Keep decimal values exact instead of silently converting to binary floats.
    return format(value, 'f')


def dimensions(attrs):
    result, issues = {}, []
    for name in ('width', 'height'):
        if name not in attrs:
            result[name] = {'present': False}
            continue
        match = LENGTH.fullmatch(attrs[name].strip())
        try:
            require(match is not None, 'INVALID_DIMENSION_TOKEN')
            value = decimal_token(match.group('number'))
            unit = (match.group('unit') or '').lower()
            require(unit in LENGTH_UNITS and value >= 0, 'INVALID_DIMENSION_TOKEN')
            result[name] = {'present': True, 'status': 'literal_length', 'value': decimal_text(value),
                            'unit': unit or 'user_units'}
            if value == 0:
                issues.append('ZERO_DIMENSION_DECLARATION')
        except InspectionError:
            result[name] = {'present': True, 'status': 'invalid_or_unsupported'}
            issues.append('DIMENSION_INVALID_OR_UNSUPPORTED')
    if 'viewBox' not in attrs:
        result['viewBox'] = {'present': False}
    else:
        match = VIEWBOX.fullmatch(attrs['viewBox'])
        try:
            require(match is not None, 'INVALID_DIMENSION_TOKEN')
            values = [decimal_token(v) for v in match.groups()]
            require(values[2] > 0 and values[3] > 0, 'INVALID_DIMENSION_TOKEN')
            result['viewBox'] = {'present': True, 'status': 'literal_viewbox', 'values': [decimal_text(v) for v in values]}
        except InspectionError:
            result['viewBox'] = {'present': True, 'status': 'invalid_or_unsupported'}
            issues.append('VIEWBOX_INVALID_OR_UNSUPPORTED')
    result['interpretation'] = 'Declared literals only; no unit conversion, viewport, CSS cascade or rendered bounds were evaluated.'
    return result, issues


def split_name(name):
    if '}' in name:
        return name.rsplit('}', 1)
    return '', name


def reference_kind(text):
    value = text.strip(' \t\r\n\f')
    if not value:
        return 'empty'
    if any(unicodedata.category(c).startswith('C') for c in value):
        return 'uncertain_text'
    if value.startswith('#'):
        return 'internal_fragment' if FRAGMENT.fullmatch(value[1:]) else 'unsupported_fragment'
    lower = value.lower()
    if lower.startswith('data:'):
        return 'data'
    if lower.startswith(('javascript:', 'vbscript:')):
        return 'active_scheme'
    if lower.startswith(('http:', 'https:', '//')):
        return 'external_network'
    if lower.startswith('file:') or value.startswith(('/', '\\')) or re.match(r'[A-Za-z]:', value):
        return 'external_file'
    if re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', value):
        return 'unknown_scheme'
    return 'external_relative'


def css_references(text):
    """A conservative literal-token subset; it is deliberately not CSS evaluation."""
    require(len(text) <= MAX_STYLE_CHARS, 'STYLE_CHARACTER_LIMIT')
    refs, issues = [], set()
    if '\\' in text:
        # Escapes can change identifiers (including url/import). Never imply
        # complete discovery after seeing one; no guessed decoding is attempted.
        issues.add('CSS_ESCAPES_UNINSPECTED')
    if any(ord(c) > 127 or (unicodedata.category(c).startswith('C') and c not in '\t\r\n\f') for c in text):
        issues.add('CSS_TEXT_OUTSIDE_LITERAL_SUBSET')
    length, i = len(text), 0

    def skip_space(pos):
        while pos < length and text[pos] in ' \t\r\n\f':
            pos += 1
        return pos

    def string(pos):
        quote, start = text[pos], pos + 1
        pos += 1
        while pos < length:
            if text[pos] == '\\':
                return None, length  # Entire escaped string is uncertain.
            if text[pos] == quote:
                return text[start:pos], pos + 1
            if text[pos] in '\r\n\f':
                return None, pos + 1
            pos += 1
        return None, length

    def url(pos):
        pos = skip_space(pos)
        if pos < length and text[pos] in "\"'":
            value, pos = string(pos)
            pos = skip_space(pos)
            if value is not None and pos < length and text[pos] == ')':
                return value, pos + 1
            return None, min(length, pos + 1)
        start = pos
        while pos < length and text[pos] != ')':
            if text[pos] in "\"'(\\" or text.startswith('/*', pos):
                return None, pos + 1
            pos += 1
        if pos == length:
            return None, pos
        value = text[start:pos].strip(' \t\r\n\f')
        if any(c in ' \t\r\n\f' for c in value):
            return None, pos + 1
        return value, pos + 1

    while i < length:
        if text.startswith('/*', i):
            end = text.find('*/', i + 2)
            if end < 0:
                issues.add('CSS_UNTERMINATED_COMMENT')
                break
            i = end + 2
            continue
        if text[i] in "\"'":
            value, i = string(i)
            if value is None:
                issues.add('CSS_UNSUPPORTED_STRING')
            continue
        if text[i] == '@':
            match = CSS_IDENT.match(text, i + 1)
            if match:
                issues.add('CSS_AT_RULE_NOT_INTERPRETED')
                if match.group().lower() == 'import':
                    at = skip_space(match.end())
                    if at < length and text[at] in "\"'":
                        value, i = string(at)
                        if value is None:
                            issues.add('CSS_IMPORT_UNINSPECTED')
                        else:
                            refs.append(('css_import', value))
                        continue
                i = match.end()
                continue
        match = CSS_IDENT.match(text, i)
        if match:
            at = skip_space(match.end())
            if at < length and text[at] == '(':
                if match.group().lower() == 'url':
                    value, i = url(at + 1)
                    if value is None:
                        issues.add('CSS_URL_UNINSPECTED')
                    else:
                        refs.append(('css_url', value))
                    continue
                issues.add('CSS_FUNCTION_NOT_INTERPRETED')
            i = match.end()
            continue
        i += 1
    return refs, sorted(issues)


class Inspector:
    def __init__(self, include_details):
        self.details = include_details
        self.nodes = self.attributes = self.characters = self.style_characters = self.namespace_count = 0
        self.stack = []
        self.ids = {}
        self.references = []
        self.findings = []
        self.coverage = set()
        self.style_text = {}
        self.style_lengths = {}
        self.geometry = None
        self.parser = expat.ParserCreate(encoding='utf-8', namespace_separator='}')
        self.parser.ordered_attributes = True
        self.parser.StartElementHandler = self.start
        self.parser.EndElementHandler = self.end
        self.parser.CharacterDataHandler = self.text
        self.parser.StartDoctypeDeclHandler = self.reject_declaration
        self.parser.EntityDeclHandler = self.reject_declaration
        self.parser.ExternalEntityRefHandler = self.reject_declaration
        self.parser.ProcessingInstructionHandler = self.processing_instruction
        self.parser.XmlDeclHandler = self.xml_declaration
        self.parser.StartNamespaceDeclHandler = self.namespace
        self.parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
        if hasattr(self.parser, 'SetReparseDeferralEnabled'):
            self.parser.SetReparseDeferralEnabled(True)

    def reject_declaration(self, *args):
        raise InspectionError('DTD_AND_ENTITIES_REJECTED')

    def xml_declaration(self, version, encoding, standalone):
        require(version == '1.0' and (encoding is None or encoding.lower() in ('utf-8', 'utf8')), 'XML_DECLARATION_UNSUPPORTED')

    def namespace(self, prefix, uri):
        self.namespace_count += 1
        require(self.namespace_count <= 1024 and len(prefix or '') <= 256 and len(uri or '') <= 2048, 'NAMESPACE_LIMIT')
        if uri not in (SVG, XLINK, XML, None):
            self.coverage.add('FOREIGN_NAMESPACE_DECLARATION')

    def processing_instruction(self, target, data):
        self.coverage.add('PROCESSING_INSTRUCTION_UNINSPECTED')

    def finding(self, code, node):
        require(len(self.findings) < MAX_FINDINGS, 'FINDING_LIMIT')
        self.findings.append({'code': code, 'node': node, 'line': self.parser.CurrentLineNumber})

    def reference(self, source, value, node):
        require(len(self.references) < MAX_REFERENCES, 'REFERENCE_LIMIT')
        kind = reference_kind(value)
        row = {'id': f'ref-{len(self.references) + 1:06d}', 'node': node, 'source': source,
               'kind': kind, 'resolution': 'not_inspected'}
        if self.details:
            row['reference_text'] = value
        if kind == 'internal_fragment':
            row['_target'] = value.strip(' \t\r\n\f')[1:]
        elif kind in ('empty', 'unsupported_fragment', 'uncertain_text'):
            self.coverage.add('REFERENCE_TEXT_UNSUPPORTED')
        else:
            self.finding('NON_FRAGMENT_REFERENCE', node)
        self.references.append(row)

    def css(self, value, node, source):
        self.style_characters += len(value)
        require(self.style_characters <= MAX_TOTAL_STYLE_CHARS, 'TOTAL_STYLE_CHARACTER_LIMIT')
        refs, issues = css_references(value)
        self.coverage.update(issues)
        for kind, text in refs:
            self.reference(source + ':' + kind, text, node)

    def start(self, name, values):
        self.nodes += 1
        require(self.nodes <= MAX_NODES and len(self.stack) < MAX_DEPTH, 'NODE_OR_DEPTH_LIMIT')
        require(len(values) // 2 <= MAX_NODE_ATTRIBUTES, 'ATTRIBUTE_LIMIT')
        self.attributes += len(values) // 2
        require(self.attributes <= MAX_ATTRIBUTES, 'ATTRIBUTE_LIMIT')
        attrs = dict(zip(values[::2], values[1::2]))
        require(all(len(k) <= 2304 and len(v) <= MAX_ATTRIBUTE_CHARS for k, v in attrs.items()), 'ATTRIBUTE_CHARACTER_LIMIT')
        uri, local = split_name(name)
        node = f'node-{self.nodes:06d}'
        if not self.stack:
            require((uri, local) == (SVG, 'svg'), 'SVG_NAMESPACE_ROOT_REQUIRED')
            self.geometry, issues = dimensions(attrs)
            for issue in issues:
                self.finding(issue, node)
        if uri != SVG:
            self.finding('FOREIGN_NAMESPACE_ELEMENT', node)
            self.coverage.add('FOREIGN_MARKUP_UNINSPECTED')
        elif local not in KNOWN:
            self.finding('UNRECOGNIZED_SVG_ELEMENT', node)
            self.coverage.add('SVG_ELEMENT_OUTSIDE_SUBSET')
        if uri == SVG and local in ACTIVE:
            self.finding('ACTIVE_OR_ANIMATED_ELEMENT', node)
        if uri == SVG and local in ('image', 'feImage'):
            self.finding('IMAGE_ELEMENT', node)
        if uri == SVG and local == 'a':
            self.finding('LINK_ELEMENT', node)
        hrefs = 0
        for key, value in attrs.items():
            attr_uri, attr = split_name(key)
            if attr_uri not in ('', XML, XLINK):
                self.coverage.add('FOREIGN_ATTRIBUTE_NAMESPACE')
            if attr.lower().startswith('on'):
                self.finding('EVENT_HANDLER_ATTRIBUTE', node)
            if attr_uri == XML and attr == 'base':
                self.finding('XML_BASE_DECLARATION', node)
                self.coverage.add('BASE_URL_NOT_RESOLVED')
            if attr_uri == '' and attr == 'id':
                require(len(value) <= 1024, 'ID_CHARACTER_LIMIT')
                self.ids.setdefault(value, []).append(node)
                if FRAGMENT.fullmatch(value) is None:
                    self.coverage.add('ID_TEXT_OUTSIDE_FRAGMENT_SUBSET')
            if attr == 'href' and attr_uri in ('', XLINK):
                hrefs += 1
                self.reference('href' if not attr_uri else 'xlink_href', value, node)
            if attr_uri == '' and attr == 'style':
                self.finding('INLINE_STYLE_DECLARATION', node)
                self.coverage.add('CSS_CASCADE_AND_DECLARATIONS_NOT_EVALUATED')
                self.css(value, node, 'inline_style')
            elif attr_uri == '' and attr in URL_ATTRIBUTES:
                # Presentation values use CSS syntax. Plain literals such as a
                # color remain in scope; escapes/functions get visible coverage.
                self.css(value, node, 'presentation_attribute')
            elif attr_uri == '' and attr in ('begin', 'end'):
                self.coverage.add('ANIMATION_TIMING_UNINSPECTED')
        if hrefs > 1:
            self.finding('MULTIPLE_HREF_ATTRIBUTES', node)
            self.coverage.add('HREF_PRECEDENCE_NOT_EVALUATED')
        self.stack.append((uri, local, node))
        if uri == SVG and local == 'style':
            self.style_text[node] = []
            self.style_lengths[node] = 0
            self.finding('STYLESHEET_ELEMENT', node)
            self.coverage.add('STYLESHEET_RULES_NOT_EVALUATED')

    def text(self, value):
        self.characters += len(value)
        require(self.characters <= MAX_TEXT_CHARS, 'TEXT_CHARACTER_LIMIT')
        # CSS child text is collected even across CDATA chunks; style content
        # outside SVG namespace is foreign markup and never treated as complete.
        for uri, local, node in self.stack:
            if uri == SVG and local == 'style':
                self.style_text[node].append(value)
                self.style_lengths[node] += len(value)
                require(self.style_lengths[node] <= MAX_STYLE_CHARS, 'STYLE_CHARACTER_LIMIT')

    def end(self, name):
        uri, local, node = self.stack.pop()
        if uri == SVG and local == 'style':
            self.css(''.join(self.style_text.pop(node)), node, 'stylesheet')
            self.style_lengths.pop(node)

    def report(self, data):
        id_rows = []
        for number, (value, nodes) in enumerate(sorted(self.ids.items()), 1):
            row = {'id': f'id-{number:06d}', 'nodes': nodes, 'duplicates': len(nodes) > 1}
            if self.details:
                row['id_text'] = value
            if len(nodes) > 1:
                self.findings.append({'code': 'DUPLICATE_ID', 'node': nodes[0], 'line': None})
                require(len(self.findings) <= MAX_FINDINGS, 'FINDING_LIMIT')
            id_rows.append(row)
        for row in self.references:
            target = row.pop('_target', None)
            if target is not None:
                nodes = self.ids.get(target, [])
                row['resolution'] = 'missing' if not nodes else 'resolved_unique' if len(nodes) == 1 else 'ambiguous_duplicate_id'
                row['target_nodes'] = nodes
                if len(nodes) != 1:
                    self.findings.append({'code': 'INTERNAL_REFERENCE_' + ('MISSING' if not nodes else 'AMBIGUOUS'), 'node': row['node'], 'line': None})
                    require(len(self.findings) <= MAX_FINDINGS, 'FINDING_LIMIT')
        return {'schema_version': 1, 'tool': 'svg-content-inspector',
                'status': 'REVIEW_REQUIRED' if self.findings or self.coverage else 'NO_SCOPE_FINDINGS',
                'source_sha256': hashlib.sha256(data).hexdigest(), 'source_bytes': len(data),
                'parser_expat': '.'.join(map(str, expat.version_info)), 'details_included': self.details,
                'node_count': self.nodes, 'attribute_count': self.attributes, 'text_characters': self.characters,
                'dimensions': self.geometry, 'ids': id_rows, 'references': self.references,
                'findings': self.findings, 'coverage_issues': sorted(self.coverage),
                'limits': {'max_input_bytes': MAX_BYTES, 'max_nodes': MAX_NODES, 'max_depth': MAX_DEPTH,
                           'max_attributes': MAX_ATTRIBUTES, 'max_node_attributes': MAX_NODE_ATTRIBUTES,
                           'max_attribute_characters': MAX_ATTRIBUTE_CHARS, 'max_text_characters': MAX_TEXT_CHARS,
                           'max_style_characters': MAX_STYLE_CHARS, 'max_total_style_characters': MAX_TOTAL_STYLE_CHARS,
                           'max_references': MAX_REFERENCES, 'max_findings': MAX_FINDINGS,
                           'max_report_bytes_each': MAX_REPORT_BYTES},
                'interpretation': 'Static declared markup and a conservative literal-reference subset only. Nothing was rendered, fetched, opened as a reference, executed or sanitized. No safety or visual-quality verdict.'}


def inspect(data, *, include_details=False):
    require(type(data) is bytes and len(data) <= MAX_BYTES, 'INPUT_BYTE_LIMIT')
    require(type(include_details) is bool, 'INVALID_OPTION')
    check_runtime()
    try:
        data.decode('utf-8-sig')
    except UnicodeError:
        raise InspectionError('UTF8_REQUIRED') from None
    inspector = Inspector(include_details)
    try:
        inspector.parser.Parse(data, True)
    except expat.ExpatError:
        raise InspectionError('INVALID_XML') from None
    require(inspector.nodes > 0, 'SVG_NAMESPACE_ROOT_REQUIRED')
    return inspector.report(data)


def visible(value):
    return ''.join(('\\u%04x' % ord(c)) if unicodedata.category(c).startswith('C') else c for c in str(value))


def render_html(report):
    esc = lambda text: html.escape(visible(text), quote=True)
    # JSON escapes controls inside source values. Preserve its own trusted
    # indentation/newlines so the preformatted diagnostic sections stay readable.
    esc_json = lambda value: html.escape(json.dumps(value, indent=2, ensure_ascii=True), quote=True)
    rows = []
    for ref in report['references']:
        cells = [ref['id'], ref['node'], ref['source'], ref['kind'], ref['resolution']]
        if report['details_included']:
            cells.append(ref['reference_text'])
        rows.append('<tr>' + ''.join('<td>' + esc(c) + '</td>' for c in cells) + '</tr>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; style-src &apos;unsafe-inline&apos;">'
            '<title>SVG Content Report</title><style>body{font:16px system-ui;margin:2rem;max-width:100rem}table{border-collapse:collapse}'
            'td,th{border:1px solid #777;padding:.6rem;text-align:left;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
            '<h1>SVG Content Report</h1><p>Status: <strong>' + esc(report['status']) + '</strong></p><p>'
            + esc(report['interpretation']) + '</p><p>Reference payloads and ID text are omitted by default. This report never embeds the inspected SVG.</p>'
            '<p>Source SHA-256: <code>' + esc(report['source_sha256']) + '</code></p><h2>Declared dimensions</h2><pre>'
            + esc_json(report['dimensions']) + '</pre><h2>Review findings</h2><pre>'
            + esc_json(report['findings']) + '</pre><h2>Coverage issues</h2><pre>'
            + esc_json(report['coverage_issues']) + '</pre><h2>Reference observations</h2><table><thead><tr>'
            '<th>ID</th><th>Node</th><th>Source</th><th>Kind</th><th>Resolution</th>'
            + ('<th>Private reference text</th>' if report['details_included'] else '') + '</tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></html>\n')


def write_exclusive(path, data):
    no_links(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(data)


def write_report(report, value):
    output = local_path(value)
    no_links(output.parent)
    require(stat.S_ISDIR(output.parent.lstat().st_mode), 'OUTPUT_PARENT_REQUIRED')
    require(not output.exists() and not output.is_symlink(), 'OUTPUT_EXISTS')
    payloads = {'report.json': (json.dumps(report, indent=2, ensure_ascii=True) + '\n').encode('utf-8'),
                'report.html': render_html(report).encode('utf-8')}
    require(all(len(data) <= MAX_REPORT_BYTES for data in payloads.values()), 'REPORT_BYTE_LIMIT')
    manifest = {'schema_version': 1, 'files': [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                                             for name, data in sorted(payloads.items())]}
    output.mkdir(mode=0o700, exist_ok=False)
    for name, data in payloads.items():
        write_exclusive(output / name, data)
    write_exclusive(output / 'MANIFEST.json', (json.dumps(manifest, indent=2) + '\n').encode('utf-8'))


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise InspectionError('ARGUMENTS_INVALID')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--svg', type=Path, required=True)
        parser.add_argument('--output', type=Path, required=True)
        parser.add_argument('--include-details', action='store_true', help='Opt in to private reference payloads and ID strings in reports.')
        args = parser.parse_args(argv)
        report = inspect(snapshot(args.svg), include_details=args.include_details)
        write_report(report, args.output)
        print(json.dumps({'status': report['status'], 'node_count': report['node_count'],
                          'reference_count': len(report['references']), 'finding_count': len(report['findings']),
                          'coverage_issues': report['coverage_issues']}, sort_keys=True))
        return 1 if report['status'] == 'REVIEW_REQUIRED' else 0
    except InspectionError as error:
        print(json.dumps({'status': 'INCOMPLETE', 'error': str(error)}, sort_keys=True))
        return 2
    except (OSError, ValueError, OverflowError, RecursionError):
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'IO_OR_METADATA_ERROR'}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
