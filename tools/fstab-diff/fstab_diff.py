"""Compare a documented text subset of Linux or Android fstab. MIT."""
from __future__ import annotations
import json
import re
from text_support import (Parser, TextError, bounded_append, cli_error, finish,
                          issue, require, source_inputs, source_record,
                          text_lines, write_report)

ESCAPES = {'040': ' ', '011': '\t', '134': '\\'}


def decode_field(value):
    def replace(match):
        require(match[1] in ESCAPES, 'UNSUPPORTED_FIELD_ESCAPE')
        return ESCAPES[match[1]]
    require(not re.search(r'\\(?![0-7]{3})', value), 'UNSUPPORTED_FIELD_ESCAPE')
    return re.sub(r'\\([0-7]{3})', replace, value)


def parse(data, source, mode, report):
    rows = []
    for line, raw in text_lines(data):
        words = re.split(r'[ \t]+', raw.strip(' \t')) if raw.strip(' \t') else []
        if not words or words[0].startswith('#'): continue
        # A separate # token starts a trailing comment. Embedded # is data.
        for index, word in enumerate(words):
            if word.startswith('#'):
                words = words[:index]; break
        if (mode == 'linux' and not 4 <= len(words) <= 6) or (mode == 'android' and len(words) != 5):
            issue(report['coverage_issues'], 'UNSUPPORTED_FIELD_COUNT', source, line); continue
        try: values = [decode_field(word) for word in words]
        except TextError:
            issue(report['coverage_issues'], 'UNSUPPORTED_FIELD_ESCAPE', source, line); continue
        if mode == 'linux':
            numbers = values[4:] + ['0'] * (6-len(values))
            if not all(re.fullmatch(r'[0-9]{1,5}', number) and int(number) <= 65535 for number in numbers):
                issue(report['coverage_issues'], 'UNSUPPORTED_NUMERIC_FIELD', source, line); continue
            fields = dict(zip(('source', 'target', 'fstype', 'options'), values[:4]))
            fields.update(dump=int(numbers[0]), pass_number=int(numbers[1]))
        else: fields = dict(zip(('source', 'target', 'fstype', 'options', 'fs_mgr_flags'), values))
        row = {'source_id': source, 'line': line, 'fields': fields}
        for key in ('options', 'fs_mgr_flags'):
            if key in fields:
                options = fields[key].split(',')
                if any(not option for option in options): issue(report['findings'], 'EMPTY_OPTION_TOKEN', source, line)
                if len(set(options)) != len(options): issue(report['findings'], 'DUPLICATE_OPTION_TOKEN', source, line)
        bounded_append(rows, row)
    return rows


def inspect(before, after, mode, details=False):
    require(mode in {'linux', 'android'}, 'INVALID_FORMAT')
    report = {'schema_version': 1, 'tool': 'Fstab Configuration Diff', 'format': mode,
              'scope': 'Selected text records only; no mount, boot, filesystem or effective flag evaluation.',
              'details_included': details, 'inputs': [source_record('before', before), source_record('after', after)],
              'records': [], 'changes': [], 'ambiguous_targets': [], 'findings': [], 'coverage_issues': []}
    old = parse(before, 'before', mode, report); new = parse(after, 'after', mode, report)
    indexes = []
    for rows in (old, new):
        index = {}
        for row in rows: index.setdefault(row['fields']['target'], []).append(row)
        indexes.append(index)
    old_index, new_index = indexes
    targets = list(dict.fromkeys([*old_index, *new_index])); ambiguous = set()
    for number, target in enumerate(targets, 1):
        group = f'target-{number:04d}'; left = old_index.get(target, []); right = new_index.get(target, [])
        for row in [*left, *right]:
            record = {'target_id': group, 'side': row['source_id'], 'line': row['line']}
            if details: record['fields'] = row['fields']
            bounded_append(report['records'], record)
        if len(left)>1 or len(right)>1:
            ambiguous.add(target)
            item = {'target_id': group, 'before_lines': [r['line'] for r in left], 'after_lines': [r['line'] for r in right]}
            if details: item['target'] = target
            bounded_append(report['ambiguous_targets'], item)
            for row in [*left, *right]: issue(report['findings'], 'AMBIGUOUS_TARGET_NO_PAIRING', row['source_id'], row['line'])
            continue
        kind = 'added' if not left else ('removed' if not right else 'changed')
        fields = list(right[0]['fields']) if not left else list(left[0]['fields']) if not right else [key for key in left[0]['fields'] if left[0]['fields'][key] != right[0]['fields'][key]]
        if kind != 'changed' or fields:
            change = {'target_id': group, 'kind': kind, 'fields_changed': fields,
                      'before_line': left[0]['line'] if left else None, 'after_line': right[0]['line'] if right else None}
            if details: change.update(before=left[0]['fields'] if left else None, after=right[0]['fields'] if right else None)
            bounded_append(report['changes'], change)
    common = (set(old_index) & set(new_index)) - ambiguous
    old_order = [r['fields']['target'] for r in old if r['fields']['target'] in common]
    new_order = [r['fields']['target'] for r in new if r['fields']['target'] in common]
    report['relative_order_changed'] = old_order != new_order
    report['order_scope'] = 'Unique common parsed targets only; additions, removals, ambiguous and unsupported rows excluded.'
    if report['relative_order_changed']: issue(report['findings'], 'RELATIVE_RECORD_ORDER_CHANGED', 'comparison', 0)
    if report['changes']: issue(report['findings'], 'CONFIGURATION_VALUES_CHANGED', 'comparison', 0)
    report['parsed_counts'] = {'before': len(old), 'after': len(new)}
    return finish(report)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--before', required=True); parser.add_argument('--after', required=True)
    parser.add_argument('--format', choices=('linux', 'android'), required=True)
    parser.add_argument('--output', required=True); parser.add_argument('--include-details', action='store_true')
    try:
        args = parser.parse_args(argv); inputs = source_inputs([args.before, args.after])
        report = inspect(inputs[0][1], inputs[1][1], args.format, args.include_details)
        write_report(report, args.output, [args.before, args.after])
        print(json.dumps({'status': report['status'], 'changes': len(report['changes']), 'ambiguous_targets': len(report['ambiguous_targets']), 'relative_order_changed': report['relative_order_changed'], 'coverage_issues': len(report['coverage_issues'])}, sort_keys=True))
        return int(report['status'] != 'NO_SCOPE_FINDINGS')
    except (TextError, OSError, ValueError, RecursionError) as error: return cli_error(error)


if __name__ == '__main__': raise SystemExit(main())
