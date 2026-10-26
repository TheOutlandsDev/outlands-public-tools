"""Original MIT helpers for bounded, explicit local inputs and fresh reports."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import stat
import unicodedata

MAX_BYTES = 1024 * 1024
MAX_TOTAL = 4 * MAX_BYTES
MAX_FILES = 32
MAX_LINES = 20000
MAX_LINE = 8192
MAX_ITEMS = 4000
MAX_REPORT = 8 * MAX_BYTES

class TextError(Exception):
    """Fixed code only, never untrusted source text or upstream exceptions."""

def require(value, code):
    if not value:
        raise TextError(code)

def local_path(value):
    raw = str(value); path = Path(value)
    require(path.is_absolute() and '..' not in path.parts and not raw.startswith(('\\\\', '//')),
            'LOCAL_ABSOLUTE_PATH_REQUIRED')
    require(not any(unicodedata.category(c).startswith('C') for c in raw), 'INVALID_LOCAL_PATH')
    require(os.name != 'nt' or ':' not in raw[2:], 'DEVICE_OR_STREAM_PATH_REJECTED')
    return path

def linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)

def no_links(path):
    for part in reversed((path, *path.parents)):
        require(not linked(part.lstat()), 'LINKED_PATH_REJECTED')

def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns

def canonical_directory(value):
    path = local_path(value); no_links(path); before = path.lstat()
    require(stat.S_ISDIR(before.st_mode), 'DIRECTORY_REQUIRED')
    result = local_path(path.resolve(strict=True)); no_links(result)
    require(identity(before) == identity(result.lstat()), 'INPUT_CHANGED')
    return result

def snapshot(value, maximum=MAX_BYTES):
    require(type(maximum) is int and 0 < maximum <= MAX_TOTAL, 'INVALID_BYTE_LIMIT')
    path = local_path(value); no_links(path); before = path.lstat()
    require(stat.S_ISREG(before.st_mode), 'REGULAR_FILE_REQUIRED')
    require(before.st_size <= maximum, 'INPUT_BYTE_LIMIT')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        require(stat.S_ISREG(opened.st_mode) and not linked(opened), 'REGULAR_FILE_REQUIRED')
        require(identity(before) == identity(opened), 'INPUT_CHANGED')
        data = bytearray()
        while True:
            chunk = os.read(descriptor, min(65536, maximum + 1 - len(data)))
            if not chunk: break
            data.extend(chunk); require(len(data) <= maximum, 'INPUT_BYTE_LIMIT')
        after = os.fstat(descriptor)
        require(len(data) == before.st_size and identity(opened) == identity(after)
                and opened.st_ctime_ns == after.st_ctime_ns
                and identity(after) == identity(path.lstat()), 'INPUT_CHANGED')
        return bytes(data)
    finally:
        os.close(descriptor)

def text_lines(data):
    require(type(data) is bytes and len(data) <= MAX_BYTES, 'INPUT_BYTE_LIMIT')
    try: text = data.decode('utf-8-sig')
    except UnicodeError: raise TextError('UTF8_REQUIRED') from None
    text = text.replace('\r\n', '\n')
    require(not any((unicodedata.category(c).startswith('C') and c not in '\n\t')
                    or c in '\u2028\u2029' for c in text), 'TEXT_CONTROL_UNSUPPORTED')
    lines = text.split('\n')
    require(len(lines) <= MAX_LINES and all(len(s) <= MAX_LINE for s in lines), 'TEXT_LINE_LIMIT')
    return list(enumerate(lines, 1))

def source_inputs(paths):
    require(type(paths) is list and 1 <= len(paths) <= MAX_FILES, 'INPUT_COUNT_LIMIT')
    result = []; total = 0; seen = set()
    for index, path in enumerate(paths, 1):
        route = local_path(path); no_links(route); info = route.lstat()
        token = (info.st_dev, info.st_ino)
        require(token not in seen, 'DUPLICATE_INPUT_FILE'); seen.add(token)
        data = snapshot(route); total += len(data); require(total <= MAX_TOTAL, 'TOTAL_BYTE_LIMIT')
        result.append((f'input-{index:04d}', data))
    return result

def source_record(label, data):
    return {'id': label, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def issue(rows, code, source, line):
    require(len(rows) < MAX_ITEMS, 'FINDING_LIMIT')
    row = {'code': code, 'source': source, 'line': line}
    if row not in rows: rows.append(row)

def bounded_append(rows, row):
    require(len(rows) < MAX_ITEMS, 'RECORD_LIMIT'); rows.append(row)

def finish(report):
    report['status'] = 'REVIEW_REQUIRED' if report['findings'] or report['coverage_issues'] else 'NO_SCOPE_FINDINGS'
    return report

def strict_json(data, maximum=65536, max_nodes=1000, max_text=1024):
    require(type(maximum) is int and 0 < maximum <= MAX_BYTES and type(max_nodes) is int
            and 1 <= max_nodes <= 40000 and type(max_text) is int and 1 <= max_text <= 8192, 'JSON_LIMIT_INVALID')
    require(type(data) is bytes and len(data) <= maximum, 'JSON_BYTE_LIMIT')
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'DUPLICATE_JSON_KEY'); result[key] = value
        return result
    def bad_number(_value): raise TextError('JSON_NUMBER_UNSUPPORTED')
    try:
        value = json.loads(data.decode('utf-8-sig'), object_pairs_hook=pairs,
                           parse_float=bad_number, parse_constant=bad_number)
    except (UnicodeError, ValueError, RecursionError): raise TextError('INVALID_JSON') from None
    pending = [(value, 0)]; count = 0
    while pending:
        item, depth = pending.pop(); count += 1
        require(depth <= 8 and count <= max_nodes, 'JSON_STRUCTURE_LIMIT')
        if type(item) is dict:
            for key, child in item.items():
                require(len(key) <= 256 and not any(unicodedata.category(c).startswith('C') for c in key), 'JSON_TEXT_UNSUPPORTED')
                pending.append((child, depth + 1))
        elif type(item) is list: pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            require(len(item) <= max_text and not any(unicodedata.category(c).startswith('C') for c in item), 'JSON_TEXT_UNSUPPORTED')
    return value

def write_report(report, value, inputs):
    output = local_path(value); parent = canonical_directory(output.parent)
    require(not output.exists() and not output.is_symlink(), 'OUTPUT_EXISTS')
    output = parent / output.name
    for item in inputs:
        path = local_path(item); base = canonical_directory(path.parent) / path.name
        require(not base.is_relative_to(output), 'OUTPUT_OVERLAPS_INPUT')
    encoded = (json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
    title = html.escape(report['tool'], quote=True)
    rendered = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
                '<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; style-src &apos;unsafe-inline&apos;">'
                '<title>' + title + '</title><style>body{font:16px system-ui;margin:2rem;max-width:90rem}'
                'pre{white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid #888;padding:1rem}</style><h1>'
                + title + '</h1><p>Selected metadata only. No input was executed and no partition, filesystem, device or module was modified. '
                'Review scope and coverage before interpreting this private report.</p><pre>'
                + html.escape(encoded.decode('utf-8'), quote=True) + '</pre></html>\n').encode('utf-8')
    require(len(encoded) <= MAX_REPORT and len(rendered) <= MAX_REPORT, 'REPORT_BYTE_LIMIT')
    payloads = {'report.json': encoded, 'report.html': rendered}
    manifest = {'schema_version': 1, 'files': [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                                             for name, data in sorted(payloads.items())]}
    output.mkdir(mode=0o700, exist_ok=False)
    for name, data in [*payloads.items(), ('MANIFEST.json', (json.dumps(manifest, indent=2) + '\n').encode('utf-8'))]:
        no_links(output)
        fd = os.open(output/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0), 0o600)
        with os.fdopen(fd, 'wb') as stream: stream.write(data)

class Parser(argparse.ArgumentParser):
    def error(self, _message): raise TextError('ARGUMENTS_INVALID')

def cli_error(error):
    code = str(error) if isinstance(error, TextError) else 'IO_OR_INPUT_ERROR'
    print(json.dumps({'status': 'INCOMPLETE', 'error': code}, sort_keys=True)); return 2
