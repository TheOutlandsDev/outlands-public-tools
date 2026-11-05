"""Installed cache/retry methodology using embedded fictional records only."""
import hashlib
import json
from importlib.resources import files
from outlands_cache_key_contract_checker import keys
from outlands_cache_freshness_planner import freshness
from outlands_retry_budget_checker import retries
from outlands_idempotency_ledger_reconciler import ledger


def example(package, name='input.json'):
    return json.loads(files(package).joinpath('examples', name).read_text(encoding='utf-8'))


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')


def pin(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def exercise():
    key_input = example('outlands_cache_key_contract_checker')
    key_report = keys.check(encoded(key_input)); source = key_input['entries'][0]
    assert key_report['assessment']['all_bindings_valid']
    assert key_report['assessment']['entries'][0]['expected_key_sha256'] == source['key_sha256']
    fresh_input = example('outlands_cache_freshness_planner')
    for field in ('key_sha256', 'content_sha256', 'inputs'):
        fresh_input['entries'][0][field] = source[field]
    fresh_input['as_of'] = 40
    fresh_report = freshness.check(encoded(fresh_input))
    assert fresh_report['status'] == 'REVIEW_REQUIRED'
    assert fresh_report['assessment']['entries'][0]['state'] == 'invalidated'
    assert fresh_report['assessment']['entries'][0]['expired']
    retry_input = example('outlands_retry_budget_checker'); operation = retry_input['operations'][0]
    operation['key_sha256'] = pin({'namespace': 'fictional-hvac-refresh', 'cache_key_sha256': source['key_sha256']})
    operation['payload_sha256'] = source['content_sha256']
    for attempt in retry_input['attempts']:
        attempt['operation_sha256'] = pin(operation)
    retry_input['as_of'] = fresh_input['as_of']
    retry_report = retries.check(encoded(retry_input))
    assert retry_report['status'] == 'PASS'
    assert retry_report['assessment']['operations'][0]['state'] == 'ready_for_manual_review'
    assert retry_report['assessment']['operations'][0]['earliest_next_at'] == 15
    ledger_input = example('outlands_idempotency_ledger_reconciler')
    ledger_input['operations'] = retry_input['operations']; claim = ledger_input['records'][0]
    claim.update(operation_sha256=pin(operation), key_sha256=operation['key_sha256'],
                 payload_sha256=operation['payload_sha256'], state=retry_input['attempts'][0]['status'],
                 result_sha256=retry_input['attempts'][0]['result_sha256'])
    ledger_report = ledger.check(encoded(ledger_input))
    assert ledger_report['status'] == 'PASS'
    assert ledger_report['operations_sha256'] == retry_report['operations_sha256']
    assert ledger_report['assessment']['key_groups'][0]['declared_state'] == 'failed'
    assert ledger_report['assessment']['all_terminal_claims_unambiguous']
    unknown_retry = retries.check(encoded(example('outlands_retry_budget_checker', 'needs-review.json')))
    unknown_ledger = ledger.check(encoded(example('outlands_idempotency_ledger_reconciler', 'needs-review.json')))
    assert unknown_retry['assessment']['operations'][0]['state'] == 'unknown'
    assert unknown_retry['budget_review_sha256'] is None
    assert not unknown_retry['assessment']['operations'][0]['eligible_for_manual_attempt_review']
    assert unknown_ledger['assessment']['key_groups'][0]['declared_state'] == 'unresolved'
    assert unknown_ledger['ledger_reconciliation_sha256'] is None
    for report in (key_report, fresh_report, retry_report, ledger_report, unknown_retry, unknown_ledger):
        for field in ('cache_mutated', 'execution_performed', 'exactly_once_verified', 'retry_authorized',
                      'provider_contacted', 'artifact_bytes_verified', 'record_authenticity_verified', 'target_changes_performed'):
            assert report[field] is False
    return {'status': 'PASS', 'cache_bindings': 'consistent', 'freshness': 'invalidated_and_expired',
            'retry_deadline': 15, 'ledger_claim': 'failed', 'unknown_outcomes': 'unresolved',
            'execution_performed': False}


if __name__ == '__main__':
    print(json.dumps(exercise(), sort_keys=True))
