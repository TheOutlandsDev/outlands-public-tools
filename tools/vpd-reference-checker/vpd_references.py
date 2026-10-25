"""Bounded offline VPD JSON reference inventory; no editor or media-body access."""
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
import sys
import unicodedata

MAX_PROJECT_BYTES = 8 * 1024 * 1024
MAX_MAPPING_BYTES = 1024 * 1024
MAX_DEPTH = 32
MAX_NODES = 100_000
MAX_STRING = 65_536
MAX_KEY = 256
MAX_REFERENCES = 5_000
MAX_REPORT_BYTES = 16 * 1024 * 1024
MEDIA_BINS = ('videolist', 'audiolist', 'imagelist', 'subtitlelist')
DOS_NAME = re.compile(r'(?i:CON|PRN|AUX|NUL|COM[1-9\u00b9\u00b2\u00b3]|LPT[1-9\u00b9\u00b2\u00b3])(?:\.|$)')


class CheckError(Exception):
    """Stable error code; never upstream exception text or input paths."""


def require(condition, code):
    if not condition:
        raise CheckError(code)


def is_link(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def local_path(value):
    path = Path(value)
    raw = str(value)
    require(path.is_absolute() and '..' not in path.parts and not raw.startswith(('\\\\', '//')),
            'LOCAL_ABSOLUTE_PATH_REQUIRED')
    require(not any(unicodedata.category(c).startswith('C') for c in raw), 'INVALID_LOCAL_PATH')
    if os.name == 'nt':
        require(not raw[2:].count(':'), 'DEVICE_OR_STREAM_PATH_REJECTED')
    return path


def no_links(path):
    for item in reversed((path, *path.parents)):
        require(not is_link(item.lstat()), 'LINKED_PATH_REJECTED')


def identity(info):
    # Windows path stat/fstat ctime conventions differ; compare portable fields
    # across APIs and the descriptor's own ctime before/after within one API.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_snapshot(value, maximum):
    path = local_path(value)
    no_links(path)
    expected = path.lstat()
    require(stat.S_ISREG(expected.st_mode), 'REGULAR_INPUT_REQUIRED')
    require(expected.st_size <= maximum, 'INPUT_BYTE_LIMIT')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and not is_link(before), 'REGULAR_INPUT_REQUIRED')
        require(identity(expected) == identity(before), 'INPUT_CHANGED')
        chunks = []
        size = 0
        while True:
            block = os.read(fd, min(65536, maximum + 1 - size))
            if not block:
                break
            chunks.append(block)
            size += len(block)
            require(size <= maximum, 'INPUT_BYTE_LIMIT')
        after = os.fstat(fd)
        require(identity(before) == identity(after) and before.st_ctime_ns == after.st_ctime_ns
                and size == before.st_size and identity(after) == identity(path.lstat()), 'INPUT_CHANGED')
        return b''.join(chunks)
    finally:
        os.close(fd)


def pairs(values):
    result = {}
    for key, value in values:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def number(text):
    require(len(text) <= 128, 'JSON_NUMBER_LIMIT')
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise CheckError('INVALID_JSON_NUMBER') from None
    require(value.is_finite() and abs(value.as_tuple().exponent) <= 4096, 'JSON_NUMBER_LIMIT')
    return value


def integer(text):
    require(len(text) <= 128, 'JSON_NUMBER_LIMIT')
    return int(text)


def parse_json(data):
    try:
        text = data.decode('utf-8')
    except UnicodeError:
        raise CheckError('UTF8_REQUIRED') from None
    # Bound nesting before CPython's recursive JSON decoder sees it. Escaped
    # quotes/brackets in strings do not affect this lexical depth counter.
    depth = 0
    in_string = escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in '[{':
            depth += 1
            require(depth <= MAX_DEPTH, 'JSON_DEPTH_LIMIT')
        elif char in ']}':
            depth -= 1
            require(depth >= 0, 'INVALID_JSON')
    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_int=integer, parse_float=number,
                           parse_constant=lambda _value: (_ for _ in ()).throw(CheckError('NONFINITE_JSON_NUMBER')))
    except (ValueError, RecursionError):
        raise CheckError('INVALID_JSON') from None
    queue = [(value, 0)]
    nodes = 0
    while queue:
        item, level = queue.pop()
        nodes += 1
        require(nodes <= MAX_NODES and level <= MAX_DEPTH, 'JSON_NODE_OR_DEPTH_LIMIT')
        if isinstance(item, dict):
            require(all(len(key) <= MAX_KEY and not any(unicodedata.category(c).startswith('C') for c in key)
                        for key in item), 'JSON_KEY_LIMIT')
            queue.extend((child, level + 1) for child in item.values())
        elif isinstance(item, list):
            queue.extend((child, level + 1) for child in item)
        elif isinstance(item, str):
            require(len(item) <= MAX_STRING and not any(0xD800 <= ord(c) <= 0xDFFF for c in item), 'JSON_STRING_LIMIT')
    return value


def safe_relative(value):
    require(type(value) is str and 0 < len(value) <= 4096, 'INVALID_RELATIVE_MAPPING')
    require(not value.startswith('/') and not any(c in value for c in '\\:<>"|?*')
            and not any(unicodedata.category(c).startswith('C') for c in value), 'INVALID_RELATIVE_MAPPING')
    pieces = value.split('/')
    require(len(pieces) <= 64 and all(part not in ('', '.', '..') and len(part) <= 255
            and not part.endswith(('.', ' ')) and not DOS_NAME.match(part) for part in pieces),
            'INVALID_RELATIVE_MAPPING')
    return tuple(pieces)


def path_kind(text):
    if not text:
        return 'empty'
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', text) and not re.match(r'^[A-Za-z]:[\\/]', text):
        return 'scheme_or_device_text'
    if text.startswith(('\\\\', '//')):
        return 'network_or_device_text'
    if re.match(r'^[A-Za-z]:[\\/]', text):
        return 'windows_absolute'
    if text.startswith('/'):
        return 'posix_absolute'
    try:
        safe_relative(text)
    except CheckError:
        return 'unsupported_relative_text'
    return 'portable_relative'


def _location(pointer):
    # Known schema pointers contain only fixed keys/array indexes. Unknown keys
    # may identify a private project, so their pointer text is opt-in too.
    if re.fullmatch(r'/(videolist|audiolist|imagelist|subtitlelist)/subitems/[0-9]+/path', pointer):
        return pointer, pointer.split('/')[1] + '_path'
    if pointer == '/projinfo/projectfile':
        return pointer, 'project_record_path'
    return 'outside_supported_bin_structure', 'unclassified_path'


def analyze_project(data, *, include_path_text=False):
    require(type(data) is bytes and len(data) <= MAX_PROJECT_BYTES, 'INPUT_BYTE_LIMIT')
    require(type(include_path_text) is bool, 'INVALID_OPTION')
    obj = parse_json(data)
    require(type(obj) is dict and type(obj.get('projinfo')) is dict
            and type(obj['projinfo'].get('projectfile')) is str
            and type(obj.get('timeline')) is dict and type(obj['timeline'].get('subitems')) is list,
            'UNSUPPORTED_PROJECT_STRUCTURE')
    for name in MEDIA_BINS:
        require(type(obj.get(name)) is dict and type(obj[name].get('subitems')) is list,
                'UNSUPPORTED_PROJECT_STRUCTURE')
    issues = []
    tracks = obj['timeline']['subitems']
    blocks = 0
    for track in tracks:
        if type(track) is dict and type(track.get('subitems')) is list:
            blocks += len(track['subitems'])
        else:
            issues.append('UNCOUNTED_TIMELINE_ENTRY')
    for name in MEDIA_BINS:
        for item in obj[name]['subitems']:
            if type(item) is not dict or type(item.get('path')) is not str:
                issues.append('BIN_ENTRY_WITHOUT_STRING_PATH')
    queue = [('', obj)]
    observed = []
    while queue:
        pointer, value = queue.pop()
        if type(value) is dict:
            for key, child in value.items():
                escaped_key = key.replace('~', '~0').replace('/', '~1')
                where = pointer + '/' + escaped_key
                if (key == 'path' and type(child) is str) or where == '/projinfo/projectfile':
                    observed.append((where, child))
                    require(len(observed) <= MAX_REFERENCES, 'REFERENCE_LIMIT')
                queue.append((where, child))
        elif type(value) is list:
            queue.extend((pointer + '/' + str(index), child) for index, child in enumerate(value))
    references = []
    for index, (pointer, text) in enumerate(sorted(observed), 1):
        location, role = _location(pointer)
        row = {'id': f'ref-{index:06d}', 'location': location, 'role': role,
               'path_kind': path_kind(text), 'availability': 'uninspected', 'metadata_check_attempted': False,
               'media_content_read': False, 'rights_verified': False}
        if include_path_text:
            row['embedded_path_text'] = text
            row['json_pointer'] = pointer
        if role == 'unclassified_path':
            issues.append('UNCLASSIFIED_PATH_FIELD')
        if role != 'project_record_path' and not text:
            issues.append('EMPTY_REFERENCE_TEXT')
        references.append(row)
    report = {'schema_version': 1, 'tool': 'vpd-reference-checker',
              'project_sha256': hashlib.sha256(data).hexdigest(), 'project_bytes': len(data),
              'format_scope': 'observed_vpd_json_structural_subset', 'editor_compatibility_verified': False,
              'embedded_path_text_included': include_path_text,
              'timeline_track_entries': len(tracks), 'timeline_block_entries': blocks,
              'reference_count': len(references), 'media_bin_reference_count': sum(r['role'].endswith('list_path') for r in references),
              'references': references, 'coverage_issues': sorted(set(issues)), 'mapping_used': False,
              'interpretation': 'Reference text and optional mapped-file metadata only. No media body, editor, relinking, playback, integrity or redistribution-rights validation.'}
    finish(report)
    return report


def finish(report):
    references = report['references']
    media = [r for r in references if r['role'].endswith('list_path')]
    report['metadata_check_attempt_count'] = sum(r['metadata_check_attempted'] for r in references)
    report['unmapped_media_reference_count'] = sum(r['availability'] == 'uninspected' for r in media)
    if report['coverage_issues']:
        report['status'] = 'REVIEW_REQUIRED'
    elif not report['mapping_used']:
        report['status'] = 'INVENTORY_ONLY'
    elif any(r['availability'] != 'present_regular_file' for r in media):
        report['status'] = 'REVIEW_REQUIRED'
    else:
        report['status'] = 'NO_MAPPING_FINDINGS'


def exact_fields(obj, names):
    require(type(obj) is dict and set(obj) == set(names), 'INVALID_MAPPING_FIELDS')


def apply_mapping(report, data, root_value):
    require(type(data) is bytes and len(data) <= MAX_MAPPING_BYTES, 'INPUT_BYTE_LIMIT')
    mapping = parse_json(data)
    exact_fields(mapping, ('schemaVersion', 'projectSha256', 'files'))
    require(type(mapping['schemaVersion']) is int and mapping['schemaVersion'] == 1
            and type(mapping['projectSha256']) is str
            and re.fullmatch(r'[0-9a-fA-F]{64}', mapping['projectSha256'])
            and mapping['projectSha256'].lower() == report['project_sha256'], 'MAPPING_PROJECT_MISMATCH')
    require(type(mapping['files']) is list and len(mapping['files']) <= MAX_REFERENCES, 'INVALID_MAPPING_FILES')
    root = local_path(root_value)
    no_links(root)
    require(stat.S_ISDIR(root.lstat().st_mode) and root.parent != root, 'MEDIA_DIRECTORY_REQUIRED')
    by_id = {row['id']: row for row in report['references']}
    selected = []
    seen_ids = set()
    portable = {}
    for item in mapping['files']:
        exact_fields(item, ('referenceId', 'relativePath'))
        ref_id, relative = item['referenceId'], item['relativePath']
        require(type(ref_id) is str and ref_id in by_id and ref_id not in seen_ids
                and by_id[ref_id]['role'].endswith('list_path'), 'INVALID_MAPPING_REFERENCE')
        pieces = safe_relative(relative)
        normalized = unicodedata.normalize('NFC', relative).casefold()
        require(normalized not in portable or portable[normalized] == relative, 'PORTABLE_MAPPING_COLLISION')
        portable[normalized] = relative
        selected.append((by_id[ref_id], pieces))
        seen_ids.add(ref_id)
    # Validate all mappings before making any file metadata observations.
    report['mapping_used'] = True
    unique_copies = sorted(set(pieces for _row, pieces in selected))
    copy_ids = {pieces: f'copy-{index:06d}' for index, pieces in enumerate(unique_copies, 1)}
    report['mapping_summary'] = {'mapped_references': len(selected), 'unique_relative_paths': len(unique_copies),
                                 'reused_relative_path_references': len(selected) - len(unique_copies)}
    for row, pieces in selected:
        cursor = root
        row['mapped_copy_id'] = copy_ids[pieces]
        row['metadata_check_attempted'] = True
        row['availability'] = 'present_regular_file'
        try:
            for index, piece in enumerate(pieces):
                cursor = cursor / piece
                info = cursor.lstat()
                if is_link(info):
                    row['availability'] = 'linked_path_rejected'
                    break
                if index < len(pieces) - 1 and not stat.S_ISDIR(info.st_mode):
                    row['availability'] = 'non_directory_component'
                    break
                if index == len(pieces) - 1 and not stat.S_ISREG(info.st_mode):
                    row['availability'] = 'not_regular_file'
        except FileNotFoundError:
            row['availability'] = 'missing'
        except (OSError, ValueError):
            row['availability'] = 'metadata_unavailable'
    finish(report)
    return root


def visible(text):
    return ''.join(('\\u%04x' % ord(char)) if unicodedata.category(char).startswith('C') else char for char in str(text))


def render_html(report):
    esc = lambda value: html.escape(visible(value), quote=True)
    rows = []
    for row in report['references']:
        cells = [row['id'], row.get('mapped_copy_id', 'unmapped'), row['location'], row['role'], row['path_kind'], row['availability']]
        if report['embedded_path_text_included']:
            cells.append(row['embedded_path_text'])
        rows.append('<tr>' + ''.join('<td>' + esc(c) + '</td>' for c in cells) + '</tr>')
    heading = '<th>Embedded path text (private)</th>' if report['embedded_path_text_included'] else ''
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; style-src &apos;unsafe-inline&apos;">'
            '<title>VPD Reference Report</title><style>body{font:16px system-ui;margin:2rem;max-width:100rem}table{border-collapse:collapse}'
            'td,th{border:1px solid #777;padding:.6rem;text-align:left;overflow-wrap:anywhere}code{overflow-wrap:anywhere}</style>'
            '<h1>VPD Reference Report</h1><p>Status: <strong>' + esc(report['status']) + '</strong></p><p>'
            + esc(report['interpretation']) + '</p><p>Paths are omitted by default. No links open referenced files.</p>'
            '<p>Project SHA-256: <code>' + esc(report['project_sha256']) + '</code></p><p>Track-array entries: '
            + str(report['timeline_track_entries']) + '; immediate block-array entries: ' + str(report['timeline_block_entries'])
            + '; mapped metadata check attempts: ' + str(report['metadata_check_attempt_count']) + '.</p><p>Coverage issues: '
            + esc(', '.join(report['coverage_issues']) or 'none in the documented structural subset') + '</p>'
            '<table><thead><tr><th>ID</th><th>Mapped copy ID</th><th>Location</th><th>Role</th><th>Path kind</th><th>Mapped availability</th>'
            + heading + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></html>\n')


def exclusive_write(path, data):
    no_links(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(data)


def write_report(report, output_value, *, media_root=None):
    output = local_path(output_value)
    no_links(output.parent)
    require(stat.S_ISDIR(output.parent.lstat().st_mode), 'OUTPUT_PARENT_REQUIRED')
    require(not output.exists() and not output.is_symlink(), 'OUTPUT_EXISTS')
    require(media_root is None or not output.is_relative_to(media_root), 'OUTPUT_INSIDE_MEDIA_ROOT')
    payloads = {'report.json': (json.dumps(report, indent=2, ensure_ascii=True) + '\n').encode('utf-8'),
                'report.html': render_html(report).encode('utf-8')}
    require(all(len(data) <= MAX_REPORT_BYTES for data in payloads.values()), 'REPORT_BYTE_LIMIT')
    manifest = {'schema_version': 1, 'files': [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                                             for name, data in sorted(payloads.items())]}
    output.mkdir(mode=0o700)
    for name, data in payloads.items():
        exclusive_write(output / name, data)
    exclusive_write(output / 'MANIFEST.json', (json.dumps(manifest, indent=2) + '\n').encode('utf-8'))


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise CheckError('ARGUMENTS_INVALID')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--project', type=Path, required=True)
        parser.add_argument('--output', type=Path, required=True)
        parser.add_argument('--mapping', type=Path)
        parser.add_argument('--media-root', type=Path)
        parser.add_argument('--include-path-text', action='store_true', help='Opt in to private embedded paths and full JSON pointers in reports.')
        args = parser.parse_args(argv)
        require((args.mapping is None) == (args.media_root is None), 'MAPPING_AND_MEDIA_ROOT_REQUIRED_TOGETHER')
        require(args.project.suffix.lower() == '.vpd', 'VPD_EXTENSION_REQUIRED')
        data = read_snapshot(args.project, MAX_PROJECT_BYTES)
        report = analyze_project(data, include_path_text=args.include_path_text)
        media_root = None
        if args.mapping is not None:
            media_root = apply_mapping(report, read_snapshot(args.mapping, MAX_MAPPING_BYTES), args.media_root)
        write_report(report, args.output, media_root=media_root)
        print(json.dumps({'status': report['status'], 'reference_count': report['reference_count'],
                          'metadata_check_attempt_count': report['metadata_check_attempt_count'],
                          'coverage_issues': report['coverage_issues']}, sort_keys=True))
        return 1 if report['status'] == 'REVIEW_REQUIRED' else 0
    except CheckError as error:
        print(json.dumps({'status': 'INCOMPLETE', 'error': str(error)}, sort_keys=True))
        return 2
    except (OSError, ValueError, OverflowError):
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'IO_OR_METADATA_ERROR'}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
