"""Index a literal subset of explicitly selected Android init files. MIT."""
from __future__ import annotations
import json
import re
from text_support import (Parser, TextError, bounded_append, cli_error, finish,
                          issue, require, source_inputs, source_record, text_lines,
                          write_report)

NAME = re.compile(r'[A-Za-z0-9_.-]{1,128}\Z')
REFERENCE = {'start', 'stop', 'restart', 'exec_start'}


def inspect(inputs, details=False):
    report = {'schema_version': 1, 'tool': 'Android Init Service Inspector',
              'scope': 'Literal selected-file declarations; no import, property, trigger or runtime evaluation.',
              'details_included': details, 'inputs': [], 'services': [], 'actions': [],
              'imports': [], 'references': [], 'mount_all': [], 'findings': [], 'coverage_issues': []}
    services = {}; references = []
    for source, data in inputs:
        report['inputs'].append(source_record(source, data)); context = None
        for line, raw in text_lines(data):
            value = raw.strip(' \t')
            if not value or value.startswith('#'): continue
            words = re.split(r'[ \t]+', value); command = words[0]
            # Never partially interpret quoting, escaping, expansions or continuations.
            if any(c in value for c in ('"', "'", '\\', '$')):
                issue(report['coverage_issues'], 'NONLITERAL_STATEMENT', source, line)
                context = None
                continue
            location = {'source': source, 'line': line}
            if command == 'service':
                context = None
                if len(words) < 3 or not NAME.fullmatch(words[1]):
                    issue(report['coverage_issues'], 'INVALID_SERVICE_DECLARATION', source, line); continue
                row = {'id': f'service-{len(report["services"])+1:04d}', **location,
                       'argument_count': len(words)-3, 'options': [], 'restart_commands': 0}
                if details: row.update(name=words[1], executable=words[2])
                bounded_append(report['services'], row)
                services.setdefault(words[1], []).append(row); context = ('service', row)
            elif command == 'on':
                context = None
                if len(words) < 2:
                    issue(report['coverage_issues'], 'INVALID_ACTION_DECLARATION', source, line); continue
                row = {'id': f'action-{len(report["actions"])+1:04d}', **location}
                if details: row['trigger_text'] = ' '.join(words[1:])
                bounded_append(report['actions'], row); context = ('action', row)
            elif command == 'import':
                context = None
                row = {**location, 'operand_count': len(words)-1}
                if details and len(words) == 2: row['declared_path'] = words[1]
                bounded_append(report['imports'], row)
                issue(report['coverage_issues'], 'IMPORTS_NOT_FOLLOWED', source, line)
            elif context and context[0] == 'service':
                row = context[1]
                accepted = False
                if command in {'disabled', 'oneshot', 'override'} and len(words) == 1: accepted = True
                elif command in {'class', 'user', 'group'} and len(words) >= 2: accepted = True
                elif command == 'critical' and 1 <= len(words) <= 3:
                    accepted = True; issue(report['findings'], 'CRITICAL_SERVICE_DECLARED', source, line)
                elif command == 'reboot_on_failure' and len(words) == 2:
                    accepted = True; issue(report['findings'], 'REBOOT_ON_FAILURE_DECLARED', source, line)
                elif command == 'onrestart' and len(words) >= 2:
                    accepted = True; row['restart_commands'] += 1
                    if words[1] == 'reboot': issue(report['findings'], 'RESTART_REBOOT_DECLARED', source, line)
                    elif words[1] in REFERENCE and len(words) == 3 and NAME.fullmatch(words[2]):
                        bounded_append(references, (words[2], {**location, 'command': words[1], 'context': row['id']}))
                    else: issue(report['coverage_issues'], 'UNINSPECTED_RESTART_COMMAND', source, line)
                if accepted:
                    if command not in row['options']: row['options'].append(command)
                else: issue(report['coverage_issues'], 'UNINSPECTED_SERVICE_OPTION', source, line)
            elif context and context[0] == 'action':
                if command in REFERENCE and len(words) == 2 and NAME.fullmatch(words[1]):
                    bounded_append(references, (words[1], {**location, 'command': command, 'context': context[1]['id']}))
                elif command == 'mount_all' and len(words) in {2, 3} and (len(words) == 2 or words[2] in {'--early', '--late'}):
                    row = {**location, 'mode': words[2] if len(words) == 3 else 'unspecified'}
                    if details: row['declared_path'] = words[1]
                    bounded_append(report['mount_all'], row)
                else: issue(report['coverage_issues'], 'UNINSPECTED_ACTION_COMMAND', source, line)
            else: issue(report['coverage_issues'], 'STATEMENT_WITHOUT_SUPPORTED_SECTION', source, line)
    for name, rows in services.items():
        if len(rows) > 1:
            for row in rows: issue(report['findings'], 'DUPLICATE_SERVICE_DECLARATION', row['source'], row['line'])
    for name, row in references:
        matches = services.get(name, [])
        row['resolution'] = 'unique_selected_declaration' if len(matches) == 1 else ('ambiguous_selected_declarations' if matches else 'not_declared_in_selected_files')
        row['service_ids'] = [item['id'] for item in matches]
        if details: row['declared_name'] = name
        bounded_append(report['references'], row)
        if len(matches) != 1: issue(report['findings'], 'REFERENCE_NEEDS_SELECTED_FILE_REVIEW', row['source'], row['line'])
    return finish(report)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--file', action='append', required=True, help='Explicit absolute UTF-8 .rc file; repeat up to 32 times.')
    parser.add_argument('--output', required=True, help='New absolute report directory; parent must exist.')
    parser.add_argument('--include-details', action='store_true', help='Include declared names/paths/triggers; never argv.')
    try:
        args = parser.parse_args(argv); report = inspect(source_inputs(args.file), args.include_details)
        write_report(report, args.output, args.file)
        print(json.dumps({'status': report['status'], 'services': len(report['services']), 'findings': len(report['findings']), 'coverage_issues': len(report['coverage_issues'])}, sort_keys=True))
        return int(report['status'] != 'NO_SCOPE_FINDINGS')
    except (TextError, OSError, ValueError, RecursionError) as error: return cli_error(error)


if __name__ == '__main__': raise SystemExit(main())
