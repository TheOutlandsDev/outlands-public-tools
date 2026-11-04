"""Exact ISO week assignment for a bounded cohort of date-only declarations."""
from datetime import date
import re
import toolkit as t


def parse_date(value):
    t.require(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'DATE_INVALID')
    try:
        selected = date.fromisoformat(value)
    except ValueError:
        raise t.Rejected('DATE_INVALID') from None
    t.require(1900 <= selected.year <= 2099, 'DATE_RANGE')
    return selected


def analyze(snapshot):
    t.fields(snapshot, {'id', 'revision', 'rows'})
    t.identifier(snapshot['id']); t.integer(snapshot['revision'], 10**6, 1)
    t.require(type(snapshot['rows']) is list and 1 <= len(snapshot['rows']) <= 512, 'ROW_LIMIT')
    seen, assignments, groups = set(), [], {}
    for row in snapshot['rows']:
        t.fields(row, {'id', 'date'})
        t.identifier(row['id'])
        t.require(row['id'] not in seen, 'ROW_DUPLICATE')
        seen.add(row['id'])
        selected = parse_date(row['date'])
        iso = selected.isocalendar()
        week_id = f'{iso.year:04d}-W{iso.week:02d}'
        groups[week_id] = groups.get(week_id, 0) + 1
        assignments.append({'id': row['id'], 'week': week_id, 'weekday': iso.weekday})
    normalized = dict(snapshot, rows=sorted(snapshot['rows'], key=lambda x: x['id']))
    weeks = []
    for week_id, count in sorted(groups.items()):
        year, week = int(week_id[:4]), int(week_id[6:])
        weeks.append({'week': week_id, 'rows': count,
                      'monday': date.fromisocalendar(year, week, 1).isoformat(),
                      'sunday': date.fromisocalendar(year, week, 7).isoformat()})
    result = {'snapshot_sha256': t.digest(t.encode(normalized)),
              'row_count': len(assignments), 'assignments': sorted(assignments, key=lambda x: x['id']),
              'weeks': weeks}
    return result, t.digest(t.encode(result))
