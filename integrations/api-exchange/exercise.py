"""Installed fictional API review; no service, network or target changes."""
import copy
import hashlib
import json
from importlib.resources import files
from outlands_api_operation_contract_checker.operations import check as operations
from outlands_api_request_contract_checker.requests import check as requests
from outlands_api_response_contract_checker.responses import check as responses
from outlands_api_exchange_scenario_comparator.scenarios import check as scenarios

OPS = (operations, requests, responses, scenarios)
PACKAGES = ('outlands_api_operation_contract_checker', 'outlands_api_request_contract_checker',
            'outlands_api_response_contract_checker', 'outlands_api_exchange_scenario_comparator')

def raw(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)+'\n').encode('ascii')

def pin(value):
    return hashlib.sha256(raw(value)).hexdigest()

def sample(index, name='input.json'):
    return json.loads(files(PACKAGES[index]).joinpath('examples', name).read_bytes())

def codes(report):
    return {row['code'] for row in report['issues']}

def main():
    values = [sample(i) for i in range(4)]
    checked = []
    def run(index, value):
        report = OPS[index](raw(value)); checked.append(report); return report
    reports = [run(i, value) for i, value in enumerate(values)]
    definition, request, response, comparison = reports
    assert all(r['status'] == 'PASS' and r['qualified_scope_sha256'] for r in reports)
    assert definition['operations_sha256'] == request['operations_sha256'] == response['operations_sha256']
    assert request['requests_sha256'] == response['requests_sha256']
    for key in ('operations', 'requests', 'responses'):
        assert comparison['baseline_'+key+'_sha256'] == response[key+'_sha256']
    assert comparison['assessment']['all_declared_outcomes_equal'] is True
    assert comparison['assessment']['whole_api_compatibility_verified'] is False
    for i in range(4):
        review = run(i, sample(i, 'needs-review.json'))
        assert review['status'] == 'REVIEW_REQUIRED' and review['qualified_scope_sha256'] is None
        assert (review['assessment'] is None) == (i == 0)

    # Invalid input may have an explicitly valid error answer.
    negative = copy.deepcopy(values[2])
    negative['requests'][0]['body']['priority'] = 6
    negative['requests'][0]['expected_valid'] = False
    negative['responses'][0].update(request_sha256=pin(negative['requests'][0]), status=400,
                                   headers={}, body={'error': 'invalid-proposal'})
    invalid = run(1, dict(format='outlands-api-requests-v1', operations=negative['operations'], requests=negative['requests']))
    assert invalid['status'] == 'REVIEW_REQUIRED' and invalid['assessment']['requests'][0]['valid'] is False
    assert invalid['assessment']['requests'][0]['expectation_met'] is True
    error = run(2, negative)
    assert error['status'] == 'PASS' and error['assessment']['requests'][0]['valid'] is False
    assert error['assessment']['responses'][0]['valid'] is True

    # Compare the same negative observations under identical definitions.
    negatives = dict(format='outlands-api-exchange-scenarios-v1')
    for side in ('baseline', 'candidate'):
        for key in ('operations', 'requests', 'responses'):
            negatives[side+'_'+key] = copy.deepcopy(negative[key])
    equal_negative = run(3, negatives)
    assert equal_negative['status'] == 'PASS'
    assert equal_negative['assessment']['scenarios'][0]['baseline']['request_valid'] is False

    # Fixture operation fields/variants and choices are already normalized by ID/value.
    changed = copy.deepcopy(values[3]); operation = changed['candidate_operations'][0]
    assert [f['id'] for f in operation['request_fields']] == sorted(f['id'] for f in operation['request_fields'])
    operation['revision'] += 1
    next(f for f in operation['request_fields'] if f['name'] == 'priority')['maximum'] = 1
    selected = changed['candidate_requests'][0]
    selected.update(operation_revision=operation['revision'], operation_sha256=pin(operation))
    changed['candidate_responses'][0]['request_sha256'] = pin(selected)
    changed_report = run(3, changed)
    assert changed_report['status'] == 'REVIEW_REQUIRED'
    assert changed_report['assessment']['scenarios'][0]['state'] == 'validation_changed'
    assert changed_report['assessment']['scenarios'][0]['baseline']['request_valid'] is True
    assert changed_report['assessment']['scenarios'][0]['candidate']['request_valid'] is False

    changed_case = copy.deepcopy(values[3]); selected = changed_case['candidate_requests'][0]
    selected['body']['priority'] = 1
    changed_case['candidate_responses'][0]['request_sha256'] = pin(selected)
    report = run(3, changed_case)
    assert report['status'] == 'REVIEW_REQUIRED' and report['assessment']['scenarios'][0]['state'] == 'request_scope_changed'
    missing = copy.deepcopy(values[3]); missing['candidate_responses'] = []
    report = run(3, missing)
    assert report['status'] == 'REVIEW_REQUIRED' and report['assessment']['scenarios'][0]['state'] == 'response_coverage_missing'
    missing = copy.deepcopy(values[3]); missing['candidate_requests'] = []; missing['candidate_responses'] = []
    assert run(3, missing)['assessment']['scenarios'][0]['state'] == 'candidate_missing'

    # Supplied pins must match; no automatic revision or hash repair occurs.
    stale = copy.deepcopy(values[1]); stale['requests'][0]['operation_sha256'] = '0'*64
    report = run(1, stale)
    assert report['status'] == 'REVIEW_REQUIRED' and report['assessment'] is None
    assert report['operations_sha256'] is None and report['requests_sha256'] is None
    conflict = copy.deepcopy(values[0]); other = copy.deepcopy(conflict['operations'][0]); other['revision'] += 1
    conflict['operations'].append(other)
    report = run(0, conflict)
    assert report['status'] == 'REVIEW_REQUIRED' and report['assessment'] is None
    duplicate = copy.deepcopy(values[0]); duplicate['operations'].append(copy.deepcopy(duplicate['operations'][0]))
    report = run(0, duplicate)
    assert report['status'] == 'PASS' and report['operations_sha256'] == definition['operations_sha256']
    assert report['counts']['operations']['duplicate_rows'] == 1
    nested = copy.deepcopy(values[0]); fields = nested['operations'][0]['request_fields']; fields.append(copy.deepcopy(fields[0]))
    report = run(0, nested)
    assert report['status'] == 'REVIEW_REQUIRED' and report['assessment'] is None

    for report in checked:
        for field in ('network_requests_performed', 'servers_started', 'authentication_performed',
                      'credentials_verified', 'service_behavior_verified', 'wire_protocol_verified',
                      'records_changed', 'raw_values_emitted', 'target_changes_performed', 'execution_authorized'):
            assert report[field] is False
        if report['status'] == 'REVIEW_REQUIRED':
            assert report['qualified_scope_sha256'] is None
    print(json.dumps(dict(status='PASS', shared_pins='matched', reports_checked=len(checked),
        invalid_request='review required', declared_error_response='valid',
        equal_negative_scenarios='pass; not valid traffic', tightened_rule='validation changed',
        changed_payload='incomparable', missing_observations='review required',
        stale_pins='assessment withheld', top_level_duplicates='counted once',
        nested_duplicates='operation rejected', network_requests_performed=False,
        service_behavior_verified=False), sort_keys=True))

if __name__ == '__main__':
    main()
