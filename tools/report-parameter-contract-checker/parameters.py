"""Offline report parameter declarations and supplied binding cases."""
import argparse
import toolkit as t

FORMAT = 'outlands-report-parameters-v1'
TYPES = {'string', 'integer', 'boolean'}


def scalar(value, kind):
    if kind == 'string':
        return type(value) is str and len(value) <= 256
    if kind == 'integer':
        return type(value) is int and -10**12 <= value <= 10**12
    return type(value) is bool


def parse_parameter(row):
    t.fields(row, {'id', 'type', 'required', 'default', 'choices', 'minimum', 'maximum', 'when'})
    t.identifier(row['id'])
    t.require(row['type'] in TYPES, 'PARAMETER_TYPE_INVALID')
    t.require(type(row['required']) is bool, 'REQUIRED_INVALID')
    kind = row['type']
    t.require(type(row['choices']) is list and len(row['choices']) <= 16, 'CHOICES_INVALID')
    if kind == 'string':
        t.require(all(type(x) is str and len(x) <= 256 for x in row['choices']), 'CHOICES_INVALID')
        t.require(len(set(row['choices'])) == len(row['choices']), 'CHOICES_INVALID')
        t.require(row['minimum'] is None and row['maximum'] is None, 'RANGE_INVALID')
    else:
        t.require(not row['choices'], 'CHOICES_INVALID')
        if kind == 'integer':
            for key in ('minimum', 'maximum'):
                t.require(row[key] is None or type(row[key]) is int and -10**12 <= row[key] <= 10**12, 'RANGE_INVALID')
            t.require(row['minimum'] is None or row['maximum'] is None or row['minimum'] <= row['maximum'], 'RANGE_INVALID')
        else:
            t.require(row['minimum'] is None and row['maximum'] is None, 'RANGE_INVALID')
    if row['default'] is not None:
        t.require(valid_value(row['default'], row), 'DEFAULT_INVALID')
    if row['when'] is not None:
        t.fields(row['when'], {'parameter', 'equals'})
        t.identifier(row['when']['parameter'])
    return row


def valid_value(value, spec):
    if not scalar(value, spec['type']):
        return False
    if spec['type'] == 'string' and spec['choices'] and value not in spec['choices']:
        return False
    if spec['type'] == 'integer':
        if spec['minimum'] is not None and value < spec['minimum']:
            return False
        if spec['maximum'] is not None and value > spec['maximum']:
            return False
    return True


def parse_report(row):
    t.fields(row, {'id', 'revision', 'parameters'})
    t.identifier(row['id']); t.integer(row['revision'], 10**6, 1)
    t.require(type(row['parameters']) is list and 1 <= len(row['parameters']) <= 32, 'PARAMETER_LIMIT')
    specs = {p['id']: parse_parameter(p) for p in row['parameters']}
    t.require(len(specs) == len(row['parameters']), 'PARAMETER_DUPLICATE')
    for spec in specs.values():
        condition = spec['when']
        if condition is not None:
            parent = specs.get(condition['parameter'])
            t.require(parent is not None and parent['id'] != spec['id'], 'DEPENDENCY_INVALID')
            t.require(valid_value(condition['equals'], parent), 'DEPENDENCY_VALUE_INVALID')
    visiting, visited = set(), set()
    def visit(key):
        t.require(key not in visiting, 'DEPENDENCY_CYCLE')
        if key in visited: return
        visiting.add(key)
        condition = specs[key]['when']
        if condition is not None: visit(condition['parameter'])
        visiting.remove(key); visited.add(key)
    for key in specs: visit(key)
    normalized = dict(row, parameters=sorted(row['parameters'], key=lambda p: p['id']))
    return normalized, specs


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'reports', 'cases'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    t.require(type(value['reports']) is list and 1 <= len(value['reports']) <= 32, 'REPORT_LIMIT')
    t.require(type(value['cases']) is list and len(value['cases']) <= 128, 'CASE_LIMIT')
    reports = {}
    for row in value['reports']:
        normalized, specs = parse_report(row)
        t.require(row['id'] not in reports, 'REPORT_DUPLICATE')
        reports[row['id']] = (normalized, specs, t.digest(t.encode(normalized)))
    seen, issues, outcomes = set(), [], []
    for row in value['cases']:
        t.fields(row, {'id', 'report', 'report_revision', 'report_sha256', 'values'})
        t.identifier(row['id']); t.identifier(row['report'])
        t.require(row['id'] not in seen, 'CASE_DUPLICATE'); seen.add(row['id'])
        t.integer(row['report_revision'], 10**6, 1); t.sha(row['report_sha256'])
        t.require(type(row['values']) is dict and len(row['values']) <= 32, 'VALUES_INVALID')
        selected = reports.get(row['report'])
        t.require(selected is not None and row['report_revision'] == selected[0]['revision'] and row['report_sha256'] == selected[2], 'REPORT_PIN_INVALID')
        specs = selected[1]
        t.require(all(t.identifier(key) in specs for key in row['values']), 'VALUE_KEY_UNKNOWN')
        resolved = {key: row['values'].get(key, spec['default']) for key, spec in specs.items()}
        active = {}
        def enabled(key):
            if key in active: return active[key]
            condition = specs[key]['when']
            active[key] = condition is None or (enabled(condition['parameter']) and type(resolved[condition['parameter']]) is type(condition['equals']) and resolved[condition['parameter']] == condition['equals'])
            return active[key]
        for key in specs: enabled(key)
        findings = []
        for key, spec in specs.items():
            supplied = key in row['values']
            if not active[key]:
                if supplied: findings.append({'parameter': key, 'code': 'INACTIVE_VALUE'})
            elif resolved[key] is None:
                if spec['required']: findings.append({'parameter': key, 'code': 'REQUIRED_MISSING'})
            elif not valid_value(resolved[key], spec):
                findings.append({'parameter': key, 'code': 'VALUE_INVALID'})
        findings.sort(key=lambda x: (x['parameter'], x['code']))
        if findings: issues.append({'case': row['id'], 'codes': sorted({x['code'] for x in findings})})
        outcomes.append({'id': row['id'], 'valid': not findings, 'findings': findings, 'active_count': sum(active.values())})
    return {'format': FORMAT, 'status': 'REVIEW_REQUIRED' if issues else 'PASS', 'input_sha256': t.digest(raw), 'reports': [{'id': key, 'sha256': reports[key][2]} for key in sorted(reports)], 'cases': outcomes, 'issues': issues, 'source_completeness_verified': False, 'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__); parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
