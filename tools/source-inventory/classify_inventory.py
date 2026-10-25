"""Classify a supported Source Inventory report without reopening inventoried files."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat

import source_inventory as inventory

MAX_CSV_BYTES = 16 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024
MAX_RULE_BYTES = 256 * 1024
MAX_ROWS = 10000
MAX_RULES = 128
MAX_PATH_CHARS = 4096
MAX_PATTERN_CHARS = 1024
MAX_COMPARISONS = 1_000_000
MAX_MATCH_WORK = 64 * 1024 * 1024
MAX_REPORT_BYTES = 32 * 1024 * 1024
MAX_REPORT_CSV_BYTES = 16 * 1024 * 1024
HEADERS = ['path', 'path_escaped', 'bytes', 'modified_utc', 'sha256', 'status']
ENCODING = 'Remove one leading apostrophe only when path_escaped is true.'
SUMMARY_KEYS = {'schema_version', 'label', 'created_at_utc', 'coverage', 'file_count',
                'hashed_file_count', 'total_bytes', 'top_level_counts', 'skipped',
                'files_csv_sha256', 'path_encoding', 'limits',
                'default_excluded_directories', 'default_excluded_suffixes',
                'additional_excluded_directories', 'tree'}
SUMMARY_REQUIRED = SUMMARY_KEYS - {'additional_excluded_directories', 'tree'}


class ClassificationError(Exception):
    """A fixed code, never input text or a filesystem path."""


def require(value: bool, code: str) -> None:
    if not value:
        raise ClassificationError(code)


def _absolute(path: Path) -> Path:
    raw = str(path)
    require(not raw.startswith(('\\\\', '//')) and (os.name != 'nt' or ':' not in raw[2:]), 'LOCAL_PATH_REQUIRED')
    require(path.is_absolute() and '..' not in path.parts, 'ABSOLUTE_PATH_REQUIRED')
    return path.absolute()


def _read(path: Path, maximum: int) -> tuple[bytes, tuple[int, ...]]:
    """Read a bounded ordinary file with source identity checks and no native execution."""
    path = _absolute(path)
    inventory._no_links(path)
    expected = path.lstat()
    require(stat.S_ISREG(expected.st_mode) and not inventory._is_link(expected), 'REGULAR_INPUT_REQUIRED')
    require(expected.st_size <= maximum, 'INPUT_BYTE_LIMIT')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and not inventory._is_link(before), 'REGULAR_INPUT_REQUIRED')
        require(inventory._identity(expected) == inventory._identity(before), 'INPUT_CHANGED')
        output = bytearray()
        while True:
            block = os.read(fd, min(65536, maximum + 1 - len(output)))
            if not block:
                break
            output.extend(block)
            require(len(output) <= maximum, 'INPUT_BYTE_LIMIT')
        after = os.fstat(fd)
        require(len(output) == expected.st_size and inventory._descriptor_identity(before) == inventory._descriptor_identity(after)
                and inventory._identity(path.lstat()) == inventory._identity(after), 'INPUT_CHANGED')
        return bytes(output), inventory._identity(after)
    finally:
        os.close(fd)


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        require(key not in result, 'JSON_DUPLICATE_KEY')
        result[key] = value
    return result


def _not_number(_value: str):
    raise ClassificationError('JSON_INTEGER_REQUIRED')


def _json(data: bytes) -> dict:
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_float=_not_number, parse_constant=_not_number)
    except (UnicodeError, ValueError, RecursionError):
        raise ClassificationError('INVALID_JSON') from None
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        require(depth <= 16 and nodes <= 50000, 'JSON_STRUCTURE_LIMIT')
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for v in item.values())
            require(all(isinstance(k, str) and len(k) <= MAX_PATH_CHARS for k in item), 'JSON_STRING_LIMIT')
            try:
                for key in item:
                    key.encode('utf-8')
            except UnicodeError:
                raise ClassificationError('INVALID_JSON_TEXT') from None
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
        elif isinstance(item, str):
            require(len(item) <= MAX_PATH_CHARS, 'JSON_STRING_LIMIT')
            try:
                item.encode('utf-8')
            except UnicodeError:
                raise ClassificationError('INVALID_JSON_TEXT') from None
    require(type(value) is dict, 'JSON_OBJECT_REQUIRED')
    return value


def _keys(value: object, required: set[str], allowed: set[str]) -> None:
    require(type(value) is dict and required <= value.keys() <= allowed, 'JSON_FIELDS_INVALID')


def _integer(value: object, maximum: int) -> bool:
    return type(value) is int and 0 <= value <= maximum


def _utc(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)
    except ValueError:
        return False


def _digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r'[0-9A-Fa-f]{64}', value) is not None


def parse_rules(data: bytes) -> dict:
    require(len(data) <= MAX_RULE_BYTES, 'INPUT_BYTE_LIMIT')
    obj = _json(data)
    _keys(obj, {'schema_version', 'case_sensitive', 'rules'}, {'schema_version', 'case_sensitive', 'rules'})
    require(obj['schema_version'] == 'outlands.path_rules.v1' and type(obj['case_sensitive']) is bool, 'RULE_SCHEMA_INVALID')
    rules = obj['rules']
    require(type(rules) is list and 1 <= len(rules) <= MAX_RULES, 'RULE_COUNT_LIMIT')
    identifiers = set()
    for rule in rules:
        _keys(rule, {'id', 'category', 'kind', 'value'}, {'id', 'category', 'kind', 'value'})
        for key in ('id', 'category'):
            require(isinstance(rule[key], str) and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,47}', rule[key]) is not None, 'RULE_LABEL_INVALID')
        require(rule['id'] not in identifiers, 'RULE_ID_DUPLICATE')
        identifiers.add(rule['id'])
        require(rule['kind'] in ('exact', 'prefix', 'suffix'), 'RULE_KIND_UNSUPPORTED')
        require(isinstance(rule['value'], str) and 1 <= len(rule['value']) <= MAX_PATTERN_CHARS
                and '\x00' not in rule['value'], 'RULE_PATTERN_INVALID')
    return obj


def parse_inventory(csv_bytes: bytes, summary_bytes: bytes) -> tuple[list[dict], dict]:
    require(len(csv_bytes) <= MAX_CSV_BYTES and len(summary_bytes) <= MAX_JSON_BYTES, 'INPUT_BYTE_LIMIT')
    summary = _json(summary_bytes)
    _keys(summary, SUMMARY_REQUIRED, SUMMARY_KEYS)
    require(summary['schema_version'] == 'outlands.source_inventory.v1'
            and summary['coverage'] == 'selected_regular_files_only' and summary['path_encoding'] == ENCODING, 'INVENTORY_SCHEMA_UNSUPPORTED')
    require(_digest(summary['files_csv_sha256']) and hashlib.sha256(csv_bytes).hexdigest().upper() == summary['files_csv_sha256'].upper(), 'CSV_HASH_MISMATCH')
    require(_integer(summary['file_count'], MAX_ROWS) and summary['hashed_file_count'] == summary['file_count']
            and type(summary['hashed_file_count']) is int and _integer(summary['total_bytes'], 256 * 1024 * 1024), 'INVENTORY_TOTALS_INVALID')
    require(isinstance(summary['label'], str) and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,47}', summary['label']) is not None
            and _utc(summary['created_at_utc']), 'INVENTORY_METADATA_INVALID')
    _keys(summary['skipped'], {'directories', 'files', 'links', 'nonregular'}, {'directories', 'files', 'links', 'nonregular'})
    require(all(_integer(n, 10000) for n in summary['skipped'].values()), 'INVENTORY_METADATA_INVALID')
    _keys(summary['limits'], {'max_files', 'max_file_bytes', 'max_total_bytes', 'max_entries'}, {'max_files', 'max_file_bytes', 'max_total_bytes', 'max_entries'})
    require(all(type(n) is int and 0 < n <= ceiling for n, ceiling in zip(
        (summary['limits'][k] for k in ('max_files', 'max_file_bytes', 'max_total_bytes', 'max_entries')),
        (MAX_ROWS, 64 * 1024 * 1024, 256 * 1024 * 1024, 10000))), 'INVENTORY_METADATA_INVALID')
    for key in ('default_excluded_directories', 'default_excluded_suffixes', 'additional_excluded_directories'):
        if key in summary:
            require(type(summary[key]) is list and len(summary[key]) <= 256 and all(isinstance(s, str) and 0 < len(s) <= 255 for s in summary[key]), 'INVENTORY_METADATA_INVALID')
    require(type(summary['top_level_counts']) is dict and all(_integer(n, MAX_ROWS) for n in summary['top_level_counts'].values()), 'INVENTORY_METADATA_INVALID')
    if 'tree' in summary:
        require(type(summary['tree']) is dict, 'INVENTORY_METADATA_INVALID')
    try:
        text = csv_bytes.decode('utf-8')
        reader = csv.reader(io.StringIO(text, newline=''), strict=True)
        require(next(reader, None) == HEADERS, 'CSV_HEADER_INVALID')
        rows, seen, total, top = [], set(), 0, {}
        for fields in reader:
            require(len(rows) < MAX_ROWS and len(fields) == len(HEADERS), 'CSV_ROWS_INVALID')
            row = dict(zip(HEADERS, fields))
            encoded, escaped = row['path'], row['path_escaped']
            require(escaped in ('true', 'false') and 0 < len(encoded) <= MAX_PATH_CHARS + 1, 'CSV_PATH_INVALID')
            require(escaped == 'false' or encoded.startswith("'"), 'CSV_ESCAPE_INVALID')
            path = encoded[1:] if escaped == 'true' else encoded
            require(inventory._csv_path(path) == (encoded, escaped), 'CSV_ESCAPE_INVALID')
            # These strings are data only. They are never joined to a filesystem root.
            require(path and len(path) <= MAX_PATH_CHARS and not path.startswith(('/', '\\'))
                    and re.match(r'^[A-Za-z]:', path) is None and '\x00' not in path
                    and all(part not in ('', '.', '..') for part in path.split('/')), 'CSV_PATH_INVALID')
            require(path not in seen, 'CSV_PATH_DUPLICATE')
            seen.add(path)
            require(re.fullmatch(r'0|[1-9][0-9]{0,8}', row['bytes']) is not None, 'CSV_BYTES_INVALID')
            size = int(row['bytes'])
            require(size <= summary['limits']['max_file_bytes'] and _digest(row['sha256'])
                    and row['status'] == 'ok' and _utc(row['modified_utc']), 'CSV_ROW_INVALID')
            total += size
            require(total <= summary['limits']['max_total_bytes'], 'INVENTORY_TOTALS_INVALID')
            top[path.split('/', 1)[0]] = top.get(path.split('/', 1)[0], 0) + 1
            rows.append({'path': path, 'bytes': size})
    except (UnicodeError, csv.Error):
        raise ClassificationError('CSV_INVALID') from None
    require(len(rows) == summary['file_count'] and len(rows) <= summary['limits']['max_files']
            and total == summary['total_bytes'] and top == summary['top_level_counts'], 'INVENTORY_TOTALS_MISMATCH')
    rows.sort(key=lambda row: (row['path'].casefold(), row['path']))
    return rows, summary


def classify_rows(rows: list[dict], rules: dict) -> dict:
    require(type(rows) is list and len(rows) <= MAX_ROWS, 'ROW_COUNT_LIMIT')
    require(all(type(row) is dict and set(row) == {'path', 'bytes'} and isinstance(row['path'], str)
                and 0 < len(row['path']) <= MAX_PATH_CHARS and _integer(row['bytes'], 64 * 1024 * 1024)
                for row in rows), 'ROW_INVALID')
    # parse_rules enforces the entire public rules contract for programmatic callers too.
    rules = parse_rules(json.dumps(rules, ensure_ascii=True).encode('utf-8'))
    patterns = [(rule, rule['value'] if rules['case_sensitive'] else rule['value'].casefold()) for rule in rules['rules']]
    output, totals, unmatched, overlaps = [], {}, 0, 0
    comparisons = work = 0
    seen = set()
    for row in sorted(rows, key=lambda item: (item['path'].casefold(), item['path'])):
        require(type(row) is dict and set(row) == {'path', 'bytes'} and isinstance(row['path'], str)
                and 0 < len(row['path']) <= MAX_PATH_CHARS and _integer(row['bytes'], 64 * 1024 * 1024), 'ROW_INVALID')
        require(row['path'] not in seen, 'CSV_PATH_DUPLICATE'); seen.add(row['path'])
        text = row['path'] if rules['case_sensitive'] else row['path'].casefold()
        matching = []
        for rule, needle in patterns:
            comparisons += 1
            work += len(text) + len(needle)
            require(comparisons <= MAX_COMPARISONS and work <= MAX_MATCH_WORK, 'MATCH_WORK_LIMIT')
            hit = text == needle if rule['kind'] == 'exact' else text.startswith(needle) if rule['kind'] == 'prefix' else text.endswith(needle)
            if hit:
                matching.append(rule)
        category = matching[0]['category'] if matching else None
        if category is None:
            unmatched += 1
        else:
            aggregate = totals.setdefault(category, {'files': 0, 'bytes': 0})
            aggregate['files'] += 1; aggregate['bytes'] += row['bytes']
        overlaps += len(matching) > 1
        output.append({**row, 'category': category, 'matching_rule_ids': [r['id'] for r in matching], 'overlap': len(matching) > 1})
    return {'schema_version': 'outlands.inventory_classification.v1',
            'coverage': 'supplied_selected_inventory_rows_only',
            'case_sensitive': rules['case_sensitive'], 'selection': 'first_matching_rule',
            'rows': output, 'file_count': len(output), 'total_bytes': sum(r['bytes'] for r in output),
            'category_totals': dict(sorted(totals.items())), 'unmatched_files': unmatched,
            'overlapping_files': overlaps, 'rule_order': [r['id'] for r in rules['rules']],
            'comparisons': comparisons, 'match_work_units': work,
            'limits': {'max_rows': MAX_ROWS, 'max_rules': MAX_RULES, 'max_comparisons': MAX_COMPARISONS, 'max_match_work_units': MAX_MATCH_WORK},
            'interpretation': 'User-supplied path rules only; no file bodies, provenance, safety, necessity or license rights were verified.'}


def classify(run: Path, rule_path: Path, output: Path) -> dict:
    run, rule_path, output = _absolute(run), _absolute(rule_path), _absolute(output)
    inventory._directory(run)
    inventory._directory(output.parent)
    require(not output.is_relative_to(run) and output != rule_path and not rule_path.is_relative_to(output), 'OUTPUT_OVERLAPS_INPUT')
    require(not output.exists() and not output.is_symlink(), 'OUTPUT_EXISTS')
    paths = [(run / 'files.csv', MAX_CSV_BYTES), (run / 'summary.json', MAX_JSON_BYTES), (rule_path, MAX_RULE_BYTES)]
    snapshots = [_read(path, maximum) for path, maximum in paths]
    rows, _summary = parse_inventory(snapshots[0][0], snapshots[1][0])
    report = classify_rows(rows, parse_rules(snapshots[2][0]))
    report['inputs'] = {name: hashlib.sha256(snapshots[index][0]).hexdigest().upper()
                        for index, name in enumerate(('files_csv_sha256', 'summary_json_sha256', 'rules_json_sha256'))}
    report_bytes = (json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')
    require(len(report_bytes) <= MAX_REPORT_BYTES, 'REPORT_BYTE_LIMIT')
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(['path', 'path_escaped', 'bytes', 'category', 'matching_rule_ids', 'overlap'])
    for row in report['rows']:
        escaped, flag = inventory._csv_path(row['path'])
        writer.writerow([escaped, flag, row['bytes'], row['category'] or '', '|'.join(row['matching_rule_ids']), str(row['overlap']).lower()])
    csv_bytes = buffer.getvalue().encode('utf-8')
    require(len(csv_bytes) <= MAX_REPORT_CSV_BYTES, 'REPORT_BYTE_LIMIT')
    for index, (path, _) in enumerate(paths):
        inventory._no_links(path)
        require(inventory._identity(path.lstat()) == snapshots[index][1], 'INPUT_CHANGED')
    inventory._no_links(output.parent)
    output.mkdir(mode=0o700, exist_ok=False)
    # Errors can leave a new partial directory. Existing paths are never replaced.
    payloads = {'classification.json': report_bytes, 'classified-paths.csv': csv_bytes}
    manifest = {'schema_version': 'outlands.classification_manifest.v1', 'files': [
        {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest().upper()}
        for name, data in sorted(payloads.items())]}
    for name, data in payloads.items():
        inventory._exclusive_write(output / name, data)
    inventory._exclusive_write(output / 'MANIFEST.json', (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode('utf-8'))
    return report


class Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise ClassificationError('ARGUMENTS_INVALID')


def main(argv: list[str] | None = None) -> int:
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--inventory', required=True, type=Path)
        parser.add_argument('--rules', required=True, type=Path)
        parser.add_argument('--output', required=True, type=Path)
        args = parser.parse_args(argv)
        report = classify(args.inventory, args.rules, args.output)
        print(json.dumps({'result': 'CLASSIFIED_SUPPLIED_ROWS', 'file_count': report['file_count'],
                          'unmatched_files': report['unmatched_files'], 'overlapping_files': report['overlapping_files']}, sort_keys=True))
        return 0
    except ClassificationError as error:
        print(json.dumps({'result': 'INCOMPLETE', 'error': str(error)}, sort_keys=True))
        return 2
    except inventory.InventoryError:
        print(json.dumps({'result': 'INCOMPLETE', 'error': 'UNSUPPORTED_OR_LINKED_PATH'}, sort_keys=True))
        return 2
    except (OSError, ValueError, OverflowError, RecursionError, TypeError):
        print(json.dumps({'result': 'INCOMPLETE', 'error': 'IO_OR_INPUT_ERROR'}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
