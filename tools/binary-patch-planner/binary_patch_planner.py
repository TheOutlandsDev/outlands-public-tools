"""Preview bounded exact byte replacements; explicitly create a separate output. MIT."""
from __future__ import annotations
import hashlib
import json
import os
import re
import stat
from inspection_support import (MAX_BYTES, MAX_TOTAL, Parser, TextError, bounded_append,
    canonical_directory, cli_error, finish, linked, local_path, no_links,
    require, snapshot, source_record, strict_json, write_report)

MAX_SOURCE_BYTES = MAX_TOTAL
MAX_PATCHES = 1000
MAX_PATCH_BYTES = 4096
MAX_CHANGED_BYTES = MAX_BYTES


def digest(data): return hashlib.sha256(data).hexdigest()


def parse_plan(data):
    value = strict_json(data, MAX_BYTES, 40000, 8192)
    require(type(value) is dict and set(value) == {'schema_version', 'source', 'patches'}, 'PLAN_FIELDS_INVALID')
    require(type(value['schema_version']) is int and value['schema_version'] == 1, 'PLAN_VERSION_UNSUPPORTED')
    source = value['source']
    require(type(source) is dict and set(source) == {'bytes', 'sha256'}, 'SOURCE_FIELDS_INVALID')
    require(type(source['bytes']) is int and 1 <= source['bytes'] <= MAX_SOURCE_BYTES, 'SOURCE_SIZE_INVALID')
    require(type(source['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', source['sha256']) is not None,
            'SOURCE_HASH_INVALID')
    rows = value['patches']
    require(type(rows) is list and 1 <= len(rows) <= MAX_PATCHES, 'PATCH_COUNT_LIMIT')
    patches = []; total = 0
    for number, row in enumerate(rows, 1):
        require(type(row) is dict and set(row) == {'offset', 'expected_hex', 'replacement_hex'}, 'PATCH_FIELDS_INVALID')
        offset = row['offset']
        require(type(offset) is int and 0 <= offset < source['bytes'], 'PATCH_OFFSET_INVALID')
        values = []
        for field in ('expected_hex', 'replacement_hex'):
            text = row[field]
            require(type(text) is str and 2 <= len(text) <= 2*MAX_PATCH_BYTES and len(text)%2 == 0
                    and re.fullmatch(r'[0-9a-fA-F]+', text) is not None, 'PATCH_HEX_INVALID')
            values.append(bytes.fromhex(text))
        expected, replacement = values
        require(len(expected) == len(replacement), 'PATCH_LENGTH_MISMATCH')
        require(offset + len(expected) <= source['bytes'], 'PATCH_RANGE_INVALID')
        total += len(expected); require(total <= MAX_CHANGED_BYTES, 'PATCH_TOTAL_LIMIT')
        bounded_append(patches, {'index': number, 'offset': offset, 'expected': expected, 'replacement': replacement})
    end = -1
    for row in sorted(patches, key=lambda item: item['offset']):
        require(row['offset'] >= end, 'PATCH_OVERLAP'); end = row['offset'] + len(row['expected'])
    return {'source': source, 'patches': patches, 'declared_patch_bytes': total}


def analyze(source, plan_data):
    require(type(source) is bytes and len(source) <= MAX_SOURCE_BYTES, 'INPUT_BYTE_LIMIT')
    plan = parse_plan(plan_data)
    report = {'schema_version': 1, 'tool': 'Verified Binary Patch Planner',
        'scope': 'Exact declared equal-length byte replacements in one selected regular file.',
        'sources': [source_record('source', source), source_record('plan', plan_data)],
        'declared_source': dict(plan['source']), 'patches': [],
        'declared_patch_bytes': plan['declared_patch_bytes'], 'candidate_sha256': None,
        'application': {'requested': False, 'created': False, 'verified': False},
        'findings': [], 'coverage_issues': []}
    def flag(code, patch=None): bounded_append(report['findings'], {'code': code, 'patch_index': patch})
    if len(source) != plan['source']['bytes']: flag('SOURCE_SIZE_MISMATCH')
    if digest(source) != plan['source']['sha256']: flag('SOURCE_HASH_MISMATCH')
    for row in plan['patches']:
        offset = row['offset']; size = len(row['expected']); within = offset+size <= len(source)
        matches = source[offset:offset+size] == row['expected'] if within else False
        bounded_append(report['patches'], {'index': row['index'], 'offset_bytes': offset,
            'bytes': size, 'within_selected_source': within, 'expected_bytes_match': matches,
            'changes_bytes': row['expected'] != row['replacement']})
        if not within: flag('PATCH_OUTSIDE_SELECTED_SOURCE', row['index'])
        elif not matches: flag('EXPECTED_BYTES_MISMATCH', row['index'])
    candidate = None
    if not report['findings']:
        output = bytearray(source)
        for row in plan['patches']:
            output[row['offset']:row['offset']+len(row['replacement'])] = row['replacement']
        candidate = bytes(output); report['candidate_sha256'] = digest(candidate)
    return finish(report), candidate


def fresh_destination(value):
    path = local_path(value); parent = canonical_directory(path.parent)
    if os.name == 'nt':
        for component in path.parts[1:]:
            require(component == component.rstrip(' .') and not re.fullmatch(
                r'(?i)(?:CON|CONIN\$|CONOUT\$|PRN|AUX|NUL|COM[0-9¹²³]|LPT[0-9¹²³])(?:\..*)?', component),
                'WINDOWS_PATH_COMPONENT_UNSUPPORTED')
    require(not path.exists() and not path.is_symlink(), 'OUTPUT_EXISTS')
    return parent/path.name


def distinct_inputs(paths):
    tokens = set()
    for value in paths:
        path = local_path(value); no_links(path); info = path.lstat()
        require(stat.S_ISREG(info.st_mode), 'REGULAR_FILE_REQUIRED')
        token = (info.st_dev, info.st_ino)
        require(token not in tokens, 'DUPLICATE_INPUT_FILE'); tokens.add(token)


def apply_candidate(candidate, destination):
    require(type(candidate) is bytes and len(candidate) <= MAX_SOURCE_BYTES, 'INPUT_BYTE_LIMIT')
    output = fresh_destination(destination); no_links(output.parent)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_BINARY', 0), 0o600)
    try:
        opened = os.fstat(fd)
        require(stat.S_ISREG(opened.st_mode) and not linked(opened), 'REGULAR_FILE_REQUIRED')
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(candidate); stream.flush(); os.fsync(fd)
    finally: os.close(fd)
    actual = snapshot(output, MAX_SOURCE_BYTES)
    require(actual == candidate and digest(actual) == digest(candidate), 'APPLIED_OUTPUT_VERIFICATION_FAILED')
    return {'requested': True, 'created': True, 'verified': True,
            'bytes': len(actual), 'sha256': digest(actual), 'receipt_scope': 'Separate explicitly selected output file; local filename omitted.'}


def run(source_path, plan_path, report_path, apply_path=None):
    inputs = [source_path, plan_path]; distinct_inputs(inputs)
    output = fresh_destination(report_path)
    for value in inputs:
        path = local_path(value); route = canonical_directory(path.parent)/path.name
        require(not route.is_relative_to(output), 'OUTPUT_OVERLAPS_INPUT')
    applied = None
    if apply_path is not None:
        applied = fresh_destination(apply_path)
        require(not applied.is_relative_to(output) and not output.is_relative_to(applied), 'OUTPUT_DESTINATIONS_OVERLAP')
    source = snapshot(source_path, MAX_SOURCE_BYTES); plan = snapshot(plan_path, MAX_BYTES)
    report, candidate = analyze(source, plan)
    report['application']['requested'] = apply_path is not None
    if applied is not None and candidate is not None:
        # Recheck the report parent/destination immediately before any byte output.
        fresh_destination(output)
        report['application'] = apply_candidate(candidate, applied)
    write_report(report, output, inputs)
    return report


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--source', required=True); parser.add_argument('--plan', required=True)
    parser.add_argument('--output', required=True); parser.add_argument('--apply-output')
    try:
        args = parser.parse_args(argv)
        report = run(args.source, args.plan, args.output, args.apply_output)
        print(json.dumps({'status': report['status'], 'patches': len(report['patches']),
            'findings': len(report['findings']), 'application_requested': report['application']['requested'],
            'output_created': report['application']['created'], 'output_verified': report['application']['verified']}, sort_keys=True))
        return int(report['status'] != 'NO_SCOPE_FINDINGS')
    except (TextError, OSError, ValueError, RecursionError) as error: return cli_error(error)


if __name__ == '__main__': raise SystemExit(main())
