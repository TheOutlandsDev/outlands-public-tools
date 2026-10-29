"""Check supplied snapshot declarations against explicit buffers and a pinned policy."""
from datetime import datetime, timezone
import re

import toolkit as t


def utc(value):
    t.require(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', value),
              'UTC_TIMESTAMP_INVALID')
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        raise t.Rejected('UTC_TIMESTAMP_INVALID') from None


def declarations(manifest_raw, policy_raw):
    manifest, policy = t.decode(manifest_raw), t.decode(policy_raw)
    t.fields(manifest, {'format', 'snapshot_id', 'version', 'captured_at', 'items', 'reconciliation'})
    t.require(manifest['format'] == 'outlands-snapshot-v1', 'SNAPSHOT_FORMAT_INVALID')
    t.identifier(manifest['snapshot_id']); t.identifier(manifest['version'])
    utc(manifest['captured_at'])
    items = manifest['items']
    t.require(type(items) is list and 1 <= len(items) <= 16, 'ITEM_LIMIT')
    for item in items:
        t.fields(item, {'id', 'sha256', 'bytes', 'records'})
        t.identifier(item['id']); t.sha(item['sha256'])
        t.integer(item['bytes'], t.MAX_INPUT); t.integer(item['records'], 1000000)
    t.require(len({item['id'] for item in items}) == len(items), 'DUPLICATE_ITEM')
    counts = manifest['reconciliation']
    t.fields(counts, {'input_records', 'accepted_records', 'duplicate_records', 'rejected_records'})
    for value in counts.values():
        t.integer(value, 16000000)
    t.fields(policy, {'format', 'manifest_sha256', 'expected_version', 'as_of',
                      'max_age_seconds', 'expected_items'})
    t.require(policy['format'] == 'outlands-snapshot-policy-v1', 'POLICY_FORMAT_INVALID')
    t.sha(policy['manifest_sha256']); t.identifier(policy['expected_version'])
    utc(policy['as_of']); t.integer(policy['max_age_seconds'], 366 * 86400)
    expected = policy['expected_items']
    t.require(type(expected) is list and 1 <= len(expected) <= 16, 'ITEM_LIMIT')
    for item in expected:
        t.fields(item, {'id', 'records'})
        t.identifier(item['id']); t.integer(item['records'], 1000000)
    t.require(len({item['id'] for item in expected}) == len(expected), 'DUPLICATE_ITEM')
    return manifest, policy


def check(manifest_raw, policy_raw, inputs):
    manifest, policy = declarations(manifest_raw, policy_raw)
    t.require(type(inputs) is dict and set(inputs) == {v['id'] for v in manifest['items']},
              'BINDING_COVERAGE_INVALID')
    t.require(all(type(v) is bytes and len(v) <= t.MAX_INPUT for v in inputs.values()) and
              sum(map(len, inputs.values())) <= 16 * 1024 * 1024, 'TOTAL_INPUT_LIMIT')
    issues, observed = [], []
    def issue(code, item=None):
        issues.append({'code': code, 'item': item})
    if t.digest(manifest_raw) != policy['manifest_sha256']:
        issue('MANIFEST_PIN_MISMATCH')
    if manifest['version'] != policy['expected_version']:
        issue('VERSION_MISMATCH')
    age = int((utc(policy['as_of']) - utc(manifest['captured_at'])).total_seconds())
    if age < 0:
        issue('CAPTURE_AFTER_AS_OF')
    elif age > policy['max_age_seconds']:
        issue('SNAPSHOT_STALE')
    expected = {v['id']: v['records'] for v in policy['expected_items']}
    if set(inputs) != set(expected):
        issue('EXPECTED_ITEM_COVERAGE_MISMATCH')
    for item in sorted(manifest['items'], key=lambda v: v['id']):
        raw = inputs[item['id']]
        actual = dict(id=item['id'], sha256=t.digest(raw), bytes=len(raw))
        observed.append(actual)
        if actual['sha256'] != item['sha256']:
            issue('ITEM_HASH_MISMATCH', item['id'])
        if actual['bytes'] != item['bytes']:
            issue('ITEM_SIZE_MISMATCH', item['id'])
        if item['id'] in expected and item['records'] != expected[item['id']]:
            issue('DECLARED_RECORD_COUNT_MISMATCH', item['id'])
    counts = manifest['reconciliation']
    if counts['input_records'] != sum(counts[k] for k in
                                     ('accepted_records', 'duplicate_records', 'rejected_records')):
        issue('DECLARED_ACCOUNTING_MISMATCH')
    if counts['accepted_records'] != sum(item['records'] for item in manifest['items']):
        issue('DECLARED_ACCEPTED_TOTAL_MISMATCH')
    return dict(format='outlands-snapshot-check-v1', status='PASS' if not issues else 'REVIEW_REQUIRED',
                snapshot_id=manifest['snapshot_id'], version=manifest['version'],
                manifest_sha256=t.digest(manifest_raw), policy_sha256=t.digest(policy_raw),
                as_of=policy['as_of'], age_seconds=age, observed=observed,
                reconciliation=counts, record_counts_independently_verified=False,
                issues=issues, external_system_writes=False)


def main(argv=None):
    parser = t.Parser(prog='snapshot-contract-checker', description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--policy', required=True)
    parser.add_argument('--item', nargs=2, action='append', default=[], metavar=('ID', 'FILE'))
    parser.add_argument('--out')
    def operation(args):
        manifest_raw, policy_raw = t.read(args.manifest), t.read(args.policy)
        manifest, _ = declarations(manifest_raw, policy_raw)
        selected = t.bindings(args.item)
        t.require(set(selected) == {v['id'] for v in manifest['items']}, 'BINDING_COVERAGE_INVALID')
        return check(manifest_raw, policy_raw, t.buffers(selected))
    return t.run(parser, operation, argv)


if __name__ == '__main__':
    raise SystemExit(main())
