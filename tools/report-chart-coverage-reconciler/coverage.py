"""Reconcile declared chart point IDs to one pinned row cohort."""
from collections import defaultdict
import toolkit as t

FORMAT = 'outlands-report-chart-coverage-v1'


def snapshot(row):
    t.fields(row, {'id', 'revision', 'rows'})
    t.identifier(row['id']); t.integer(row['revision'], 10**6, 1)
    t.require(type(row['rows']) is list and len(row['rows']) <= 512, 'ROW_LIMIT')
    seen = set()
    for entry in row['rows']:
        t.fields(entry, {'id', 'series'})
        t.identifier(entry['id'])
        t.require(entry['series'] is None or type(entry['series']) is str and t.identifier(entry['series']), 'SERIES_INVALID')
        t.require(entry['id'] not in seen, 'ROW_DUPLICATE'); seen.add(entry['id'])
    return row


def chart(row):
    t.fields(row, {'id', 'revision', 'snapshot', 'snapshot_revision', 'snapshot_sha256', 'series'})
    for key in ('id', 'snapshot'): t.identifier(row[key])
    for key in ('revision', 'snapshot_revision'): t.integer(row[key], 10**6, 1)
    t.sha(row['snapshot_sha256'])
    t.require(type(row['series']) is list and 1 <= len(row['series']) <= 32, 'SERIES_LIMIT')
    seen = set()
    for entry in row['series']:
        t.fields(entry, {'id', 'point_row_ids'})
        t.identifier(entry['id'])
        t.require(entry['id'] not in seen, 'SERIES_DUPLICATE'); seen.add(entry['id'])
        t.require(type(entry['point_row_ids']) is list and len(entry['point_row_ids']) <= 512, 'POINT_LIMIT')
        for key in entry['point_row_ids']: t.identifier(key)


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'snapshots', 'charts'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    t.require(type(value['snapshots']) is list and 1 <= len(value['snapshots']) <= 32, 'SNAPSHOT_LIMIT')
    t.require(type(value['charts']) is list and 1 <= len(value['charts']) <= 32, 'CHART_LIMIT')
    snapshots = {}
    for item in value['snapshots']:
        snapshot(item)
        t.require(item['id'] not in snapshots, 'SNAPSHOT_DUPLICATE')
        snapshots[item['id']] = (item, t.digest(t.encode(item)))
    seen, assessments = set(), []
    for item in value['charts']:
        chart(item)
        t.require(item['id'] not in seen, 'CHART_DUPLICATE'); seen.add(item['id'])
        selected = snapshots.get(item['snapshot'])
        t.require(selected is not None and item['snapshot_revision'] == selected[0]['revision'] and item['snapshot_sha256'] == selected[1], 'SNAPSHOT_PIN_INVALID')
        expected = defaultdict(list)
        for row in selected[0]['rows']:
            if row['series'] is not None: expected[row['series']].append(row['id'])
        declared = {entry['id']: entry['point_row_ids'] for entry in item['series']}
        series_results = []
        for key in sorted(set(expected) | set(declared)):
            actual = declared.get(key, [])
            target = expected.get(key, [])
            actual_set, target_set = set(actual), set(target)
            issues = []
            if key not in expected: issues.append('UNEXPECTED_SERIES')
            if key not in declared: issues.append('MISSING_SERIES')
            if len(actual) != len(actual_set): issues.append('DUPLICATE_POINT')
            if target_set - actual_set: issues.append('MISSING_POINT')
            if actual_set - target_set: issues.append('UNEXPECTED_POINT')
            if actual != target and not (target_set - actual_set or actual_set - target_set or len(actual) != len(actual_set)):
                issues.append('ORDER_MISMATCH')
            series_results.append({'id': key, 'expected_count': len(target), 'claimed_count': len(actual), 'valid': not issues, 'issues': issues})
        assessments.append({'id': item['id'], 'chart_sha256': t.digest(t.encode(item)), 'valid': all(x['valid'] for x in series_results), 'series': series_results})
    return {'format': FORMAT, 'status': 'REVIEW_REQUIRED' if any(not x['valid'] for x in assessments) else 'PASS', 'input_sha256': t.digest(raw), 'snapshots': [{'id': key, 'sha256': snapshots[key][1]} for key in sorted(snapshots)], 'charts': sorted(assessments, key=lambda x: x['id']), 'source_completeness_verified': False, 'chart_rendered': False, 'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__); parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
