"""Exercise installed fictional form checks without opening a browser."""
from __future__ import annotations

import copy
import hashlib
import json
from importlib.resources import files

from outlands_form_definition_contract_checker.forms import check as forms
from outlands_form_submission_contract_checker.submissions import check as submissions
from outlands_ui_transition_history_checker.histories import check as histories
from outlands_ui_interaction_scenario_comparator.scenarios import check as scenarios

CHECKS = (forms, submissions, histories, scenarios)
PACKAGES = (
    'outlands_form_definition_contract_checker',
    'outlands_form_submission_contract_checker',
    'outlands_ui_transition_history_checker',
    'outlands_ui_interaction_scenario_comparator',
)


def raw(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')


def pin(value):
    return hashlib.sha256(raw(value)).hexdigest()


def sample(index, name='input.json'):
    return json.loads(files(PACKAGES[index]).joinpath('examples', name).read_bytes())


def main():
    values = [sample(index) for index in range(4)]
    reports = [check(raw(value)) for check, value in zip(CHECKS, values)]
    assert all(report['status'] == 'PASS' and report['qualified_scope_sha256'] for report in reports)
    definition, submission, history, comparison = reports
    assert definition['forms_sha256'] == submission['forms_sha256'] == history['forms_sha256']
    assert submission['submissions_sha256'] == history['submissions_sha256']
    for name in ('forms', 'flows', 'submissions', 'histories'):
        assert comparison['baseline_' + name + '_sha256'] == history[name + '_sha256']
    assert submission['assessment']['submissions'][0]['valid'] is True
    assert history['assessment']['histories'][0]['terminal_reached'] is True
    assert comparison['assessment']['all_declared_outcomes_equal'] is True
    assert all(report['browser_started'] is False and report['dom_inspected'] is False for report in reports)

    reviews = [check(raw(sample(index, 'needs-review.json'))) for index, check in enumerate(CHECKS)]
    assert all(report['status'] == 'REVIEW_REQUIRED' for report in reviews)

    # A changed declared field rule changes selected outcomes, after exact repinning.
    changed = copy.deepcopy(values[3])
    form = changed['candidate_forms'][0]
    form['revision'] = 2
    next(field for field in form['fields'] if field['id'] == 'priority')['maximum'] = 1
    flow = changed['candidate_flows'][0]
    flow.update(revision=2, form_revision=2, form_sha256=pin(form))
    selected = changed['candidate_submissions'][0]
    selected.update(form_revision=2, form_sha256=pin(form))
    interaction = changed['candidate_histories'][0]
    interaction.update(flow_revision=2, flow_sha256=pin(flow))
    for event in interaction['events']:
        if event['submission'] == selected['id']:
            event['submission_sha256'] = pin(selected)
    changed_report = scenarios(raw(changed))
    assert changed_report['status'] == 'REVIEW_REQUIRED'
    assert changed_report['assessment']['submissions'][0]['state'] == 'observed_outcomes_changed'
    assert changed_report['assessment']['histories'][0]['state'] == 'observed_outcomes_changed'

    # The same expected-negative observations can compare equal without becoming valid.
    negative = copy.deepcopy(values[3])
    for side in ('baseline', 'candidate'):
        selected = negative[side + '_submissions'][0]
        selected['values']['priority'] = 6
        selected['expected_valid'] = False
        interaction = negative[side + '_histories'][0]
        interaction['expected_valid'] = False
        for event in interaction['events']:
            if event['submission'] == selected['id']:
                event['submission_sha256'] = pin(selected)
    equal_negative = scenarios(raw(negative))
    assert equal_negative['status'] == 'PASS'
    assert equal_negative['assessment']['submissions'][0]['baseline']['valid'] is False
    assert equal_negative['assessment']['histories'][0]['baseline']['valid'] is False

    print(json.dumps({'status': 'PASS', 'source_examples': 4, 'review_examples': 4,
                      'version_change': 'REVIEW_REQUIRED', 'equal_negative': 'PASS',
                      'browser_started': False}, sort_keys=True))


if __name__ == '__main__':
    main()
