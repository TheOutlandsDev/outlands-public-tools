"""Inspect literal PRODUCT_COPY_FILES += declarations without evaluating Make. MIT."""
from __future__ import annotations
import json
import re
import unicodedata
from text_support import (Parser, TextError, bounded_append, cli_error, finish,
                          issue, require, snapshot, source_inputs, source_record,
                          strict_json, text_lines, write_report)

VARIABLE = re.compile(r'\$\(([A-Z][A-Z0-9_]{0,63})\)(?:/(.*))?\Z')
ASSIGN = re.compile(r'PRODUCT_COPY_FILES[ \t]*\+=[ \t]*(.*)\Z')
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1,10)), *(f'LPT{i}' for i in range(1,10))}


def relative(value):
    if not value or len(value) > 1024 or any(c in value for c in '\\:$*?"<>|\t\r\n') or value.startswith('/'): return False
    parts = value.split('/')
    return all(p and p not in {'.', '..'} and not p.endswith(('.', ' ')) and not p.startswith(' ')
               and p.split('.')[0].upper() not in RESERVED and not any(unicodedata.category(c).startswith('C') for c in p) for p in parts)


def roots_from_bytes(data):
    value = strict_json(data)
    require(type(value) is dict and set(value) == {'schema_version', 'roots'} and type(value['schema_version']) is int and value['schema_version'] == 1, 'INVALID_ROOTS_SCHEMA')
    roots = value['roots']
    require(type(roots) is dict and len(roots) <= 16, 'INVALID_ROOTS_SCHEMA')
    require(all(re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', key) and type(item) is str and relative(item) for key, item in roots.items()), 'INVALID_ROOT_VALUE')
    return roots


def resolve(value, roots):
    match = VARIABLE.fullmatch(value)
    if match:
        if match[1] not in roots: return None, 'UNRESOLVED_ROOT_VARIABLE'
        value = roots[match[1]] + ('/' + match[2] if match[2] is not None else '')
    if '$' in value: return None, 'MAKE_EXPRESSION_NOT_EVALUATED'
    return (value, None) if relative(value) else (None, 'UNSAFE_OR_UNSUPPORTED_RELATIVE_PATH')


def logical_lines(data):
    pending = ''; start = 0
    for line, raw in text_lines(data):
        # Only an unescaped terminal backslash joins physical lines.
        if not pending: start = line
        text = raw.strip(' \t')
        if pending and (not text or text.startswith('#')):
            yield start, '', 'INTERRUPTED_CONTINUATION'; pending = ''; continue
        text = text.split('#', 1)[0].rstrip(' \t')
        continuation = text.endswith('\\') and not text.endswith('\\\\')
        if continuation: text = text[:-1].rstrip(' \t')
        pending += (' ' if pending else '') + text
        require(len(pending) <= 8192, 'LOGICAL_LINE_LIMIT')
        if continuation: continue
        yield start, pending, None; pending = ''
    if pending: yield start, '', 'DANGLING_CONTINUATION'


def inspect(inputs, roots=None, details=False):
    roots = {} if roots is None else roots
    # Validate caller-supplied roots as strictly as CLI JSON.
    roots_from_bytes(json.dumps({'schema_version': 1, 'roots': roots}).encode())
    report = {'schema_version': 1, 'tool': 'Android Build Copy-Map Inspector',
              'scope': 'Declared literal append entries only; no Make evaluation, source existence or payload licensing check.',
              'details_included': details, 'root_count': len(roots), 'inputs': [], 'entries': [], 'conflicts': [], 'findings': [], 'coverage_issues': []}
    resolved = []
    for source, data in inputs:
        report['inputs'].append(source_record(source, data))
        for line, value, error in logical_lines(data):
            if error: issue(report['coverage_issues'], error, source, line); continue
            if not value: continue
            match = ASSIGN.fullmatch(value)
            if not match:
                issue(report['coverage_issues'], 'UNINSPECTED_MAKE_STATEMENT', source, line); continue
            if any(c in match[1] for c in ('"', "'", '\\')):
                issue(report['coverage_issues'], 'QUOTING_OR_ESCAPING_UNSUPPORTED', source, line); continue
            if '$' in re.sub(r'\$\([A-Z][A-Z0-9_]{0,63}\)', '', match[1]):
                issue(report['coverage_issues'], 'MAKE_EXPRESSION_NOT_EVALUATED', source, line); continue
            for word in re.split(r'[ \t]+', match[1].strip(' \t')) if match[1].strip(' \t') else []:
                fields = word.split(':')
                if len(fields) not in {2,3} or (len(fields) == 3 and not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', fields[2])):
                    issue(report['coverage_issues'], 'INVALID_COPY_WORD', source, line); continue
                src, src_error = resolve(fields[0], roots); dest, dest_error = resolve(fields[1], roots)
                row = {'id': f'entry-{len(report["entries"])+1:04d}', 'source': source, 'line': line,
                       'resolution': 'literal_or_explicit_root' if not src_error and not dest_error else 'unresolved', 'owner_present': len(fields) == 3}
                if details: row.update(declared_source=fields[0], declared_destination=fields[1], declared_owner=fields[2] if len(fields)==3 else None, resolved_source=src, resolved_destination=dest)
                bounded_append(report['entries'], row)
                for code in (src_error, dest_error):
                    if code: issue(report['coverage_issues'], code, source, line)
                if src is not None and dest is not None: resolved.append((src, dest, fields[2] if len(fields)==3 else None, row))
    # Ordered pair scan is bounded by MAX_ITEMS and stops at the conflict cap.
    for index, (src, dest, owner, row) in enumerate(resolved):
        for old_src, old_dest, old_owner, old_row in resolved[:index]:
            a = unicodedata.normalize('NFC', dest).casefold(); b = unicodedata.normalize('NFC', old_dest).casefold()
            code = None
            if dest == old_dest:
                code = 'DUPLICATE_DECLARED_COPY' if (src,owner)==(old_src,old_owner) else 'DECLARED_DESTINATION_CONFLICT'
            elif a == b: code = 'PORTABILITY_DESTINATION_COLLISION'
            elif a.startswith(b + '/') or b.startswith(a + '/'): code = 'FILE_PARENT_DESTINATION_CONFLICT'
            if code:
                bounded_append(report['conflicts'], {'code': code, 'entries': [old_row['id'], row['id']]})
                issue(report['findings'], code, source=row['source'], line=row['line'])
    return finish(report)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--file', action='append', required=True)
    parser.add_argument('--roots', help='Optional absolute JSON file of explicit literal root substitutions.')
    parser.add_argument('--output', required=True)
    parser.add_argument('--include-details', action='store_true')
    try:
        args = parser.parse_args(argv); inputs = source_inputs(args.file)
        roots_data = snapshot(args.roots, 65536) if args.roots else None
        report = inspect(inputs, roots_from_bytes(roots_data) if roots_data is not None else {}, args.include_details)
        if roots_data is not None: report['roots_input'] = source_record('roots-input', roots_data)
        write_report(report, args.output, [*args.file, *([args.roots] if args.roots else [])])
        print(json.dumps({'status': report['status'], 'entries': len(report['entries']), 'conflicts': len(report['conflicts']), 'coverage_issues': len(report['coverage_issues'])}, sort_keys=True))
        return int(report['status'] != 'NO_SCOPE_FINDINGS')
    except (TextError, OSError, ValueError, RecursionError) as error: return cli_error(error)


if __name__ == '__main__': raise SystemExit(main())
