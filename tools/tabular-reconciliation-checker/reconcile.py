"""Reconcile explicit typed record sets with exact totals and complete row accounting."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
import re

import toolkit as t


def contract(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'identity', 'fields', 'totals'})
    t.require(value['format'] == 'outlands-reconciliation-contract-v1', 'CONTRACT_FORMAT_INVALID')
    fields = value['fields']
    t.require(type(fields) is list and 1 <= len(fields) <= 32, 'FIELD_LIMIT')
    for field in fields:
        t.fields(field, {'name', 'type', 'nullable'})
        t.identifier(field['name'])
        t.require(field['type'] in ('text', 'integer', 'decimal', 'boolean', 'date') and
                  type(field['nullable']) is bool, 'FIELD_INVALID')
    names = {f['name'] for f in fields}
    t.require(len(names) == len(fields), 'DUPLICATE_FIELD')
    for key, maximum in (('identity', 4), ('totals', 32)):
        selected = value[key]
        t.require(type(selected) is list and len(selected) <= maximum and
                  all(type(k) is str for k in selected) and len(set(selected)) == len(selected) and
                  set(selected) <= names, 'FIELD_SELECTION_INVALID')
    t.require(value['identity'], 'IDENTITY_REQUIRED')
    by_name = {f['name']: f for f in fields}
    t.require(all(not by_name[k]['nullable'] and by_name[k]['type'] in ('text', 'integer')
                  for k in value['identity']), 'IDENTITY_TYPE_INVALID')
    t.require(all(not by_name[k]['nullable'] and by_name[k]['type'] in ('integer', 'decimal')
                  for k in value['totals']), 'TOTAL_TYPE_INVALID')
    return value


def decimal_text(value):
    result = format(value, 'f')
    if '.' in result:
        result = result.rstrip('0').rstrip('.')
    return '0' if value == 0 else result


def scalar(value, field):
    if value is None:
        t.require(field['nullable'], 'NULL_NOT_ALLOWED')
        return None
    kind = field['type']
    if kind == 'integer':
        t.require(type(value) is int and abs(value) <= 10**12, 'INTEGER_VALUE_INVALID')
    elif kind == 'boolean':
        t.require(type(value) is bool, 'BOOLEAN_VALUE_INVALID')
    else:
        t.require(type(value) is str and 0 < len(value) <= 256 and
                  all(ord(c) >= 32 and ord(c) != 127 for c in value), 'TEXT_VALUE_INVALID')
        if kind == 'decimal':
            t.require(re.fullmatch(r'-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?', value) and
                      abs(Decimal(value)) <= 10**12, 'DECIMAL_VALUE_INVALID')
            return decimal_text(Decimal(value))
        if kind == 'date':
            t.require(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value), 'DATE_VALUE_INVALID')
            try:
                date.fromisoformat(value)
            except ValueError:
                raise t.Rejected('DATE_VALUE_INVALID') from None
    return value


def records(raw, selected):
    value = t.decode(raw)
    t.fields(value, {'format', 'records'})
    t.require(value['format'] == 'outlands-record-set-v1' and type(value['records']) is list and
              len(value['records']) <= 1000, 'RECORD_SET_INVALID')
    groups, issues = defaultdict(list), []
    rejected = duplicates = conflicts = 0
    fields = selected['fields']
    for position, row in enumerate(value['records'], 1):
        try:
            t.fields(row, {f['name'] for f in fields})
            normalized = {f['name']: scalar(row[f['name']], f) for f in fields}
            key = t.encode([normalized[k] for k in selected['identity']])
            groups[key].append((position, normalized))
        except t.Rejected as error:
            rejected += 1
            issues.append(dict(row=position, code=str(error)))
    accepted = {}
    for key, entries in groups.items():
        if len({t.encode(row) for _, row in entries}) != 1:
            conflicts += len(entries)
            issues.extend(dict(row=position, code='IDENTITY_CONFLICT') for position, _ in entries)
        else:
            accepted[key] = entries[0][1]
            duplicates += len(entries) - 1
    counts = dict(input_rows=len(value['records']), accepted_records=len(accepted), duplicate_rows=duplicates,
                  rejected_rows=rejected, conflict_rows=conflicts)
    t.require(counts['input_rows'] == len(accepted) + duplicates + rejected + conflicts, 'ACCOUNTING_FAILED')
    return accepted, counts, sorted(issues, key=lambda r: r['row'])


def compare(before_raw, after_raw, contract_raw, show_values=False):
    t.require(type(show_values) is bool, 'OPTION_INVALID')
    selected = contract(contract_raw)
    before, before_counts, before_issues = records(before_raw, selected)
    after, after_counts, after_issues = records(after_raw, selected)
    issues = [dict(side=side, **item) for side, values in
              [('before', before_issues), ('after', after_issues)] for item in values]
    result = dict(format='outlands-reconciliation-v1', status='REVIEW_REQUIRED',
                  before_sha256=t.digest(before_raw), after_sha256=t.digest(after_raw),
                  contract_sha256=t.digest(contract_raw), before_counts=before_counts, after_counts=after_counts,
                  changes=None, unchanged_records=None, totals=None, issues=issues,
                  values_included=show_values, external_system_writes=False)
    if issues:
        return result
    changes, unchanged = [], 0
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key), after.get(key)
        if old == new:
            unchanged += 1
            continue
        identity = {name: (old if old is not None else new)[name] for name in selected['identity']}
        row = dict(identity=identity, classification='ONLY_IN_AFTER' if old is None else
                   'ONLY_IN_BEFORE' if new is None else 'CHANGED',
                   changed_fields=[f['name'] for f in selected['fields']
                                   if old is None or new is None or old[f['name']] != new[f['name']]],
                   before_sha256=t.digest(t.encode(old)) if old is not None else None,
                   after_sha256=t.digest(t.encode(new)) if new is not None else None)
        if show_values:
            row.update(before=old, after=new)
        changes.append(row)
    totals = {}
    for name in selected['totals']:
        old = sum((Decimal(row[name]) for row in before.values()), Decimal(0))
        new = sum((Decimal(row[name]) for row in after.values()), Decimal(0))
        totals[name] = dict(before=decimal_text(old), after=decimal_text(new), delta=decimal_text(new - old))
    result.update(status='DIFFERENCES' if changes else 'MATCH', changes=changes,
                  unchanged_records=unchanged, totals=totals)
    return result


def main(argv=None):
    parser = t.Parser(prog='tabular-reconciliation-checker', description=__doc__)
    parser.add_argument('--before', required=True)
    parser.add_argument('--after', required=True)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--show-values', action='store_true')
    parser.add_argument('--out')
    return t.run(parser, lambda a: compare(t.read(a.before), t.read(a.after), t.read(a.contract), a.show_values), argv)


if __name__ == '__main__':
    raise SystemExit(main())
