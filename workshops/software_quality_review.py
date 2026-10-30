"""Ten offline CLI checks on one fictional service-request workflow."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    'form': ('form-submission-contract-checker', 'submissions.py'),
    'request': ('api-request-contract-checker', 'requests.py'),
    'response': ('api-response-contract-checker', 'responses.py'),
    'history': ('ui-transition-history-checker', 'histories.py'),
    'comparison': ('ui-interaction-scenario-comparator', 'scenarios.py'),
}


def encode(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                      separators=(',', ':')).encode('ascii') + b'\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(value):
    return digest(encode(value))


def require(condition, code):
    if not condition:
        raise ValueError(code)


def field(name, kind, maximum=None):
    return dict(id=name, type=kind, required=True,
                minimum=1 if kind == 'integer' else None, maximum=maximum,
                min_length=None, max_length=None, choices=[],
                visible_when=[], required_when=[])


def fixtures():
    # Field/transition arrays are already in the documented lexical normal form.
    form = dict(id='service-request', revision=1,
                fields=[field('equipment', 'string'), field('priority', 'integer', 5)])
    flow = dict(id='service-intake', revision=1, form=form['id'],
                form_revision=1, form_sha256=pin(form), states=['draft', 'recorded'],
                initial_state='draft', terminal_states=['recorded'], transitions=[dict(
                    id='submit-request', **{'from': 'draft', 'to': 'recorded'},
                    action='submit', submission_requirement='valid')])

    def submission(valid):
        return dict(id='proposal', revision=2 if valid else 1, form=form['id'],
                    form_revision=1, form_sha256=pin(form),
                    values=dict(equipment='air-handler', priority=5 if valid else True),
                    expected_valid=True)

    def history(sub):
        return dict(id='intake-history', revision=1, flow=flow['id'], flow_revision=1,
                    flow_sha256=pin(flow), expected_valid=True, events=[dict(
                        sequence=1, action='submit', **{'from': 'draft', 'to': 'recorded'},
                        submission=sub['id'], submission_revision=sub['revision'],
                        submission_sha256=pin(sub))])

    request_fields = []
    for item in form['fields']:
        entry = {k: v for k, v in item.items() if k not in ('visible_when', 'required_when')}
        entry.update(id='field-' + item['id'], name=item['id'], location='body')
        request_fields.append(entry)
    accepted = dict(id='field-accepted', location='body', name='accepted', type='boolean',
                    required=True, minimum=None, maximum=None, min_length=None,
                    max_length=None, choices=[])
    operation = dict(id='preview-service', revision=1, method='POST', route=['service-preview'],
                     request_media_type='application/json', request_fields=request_fields,
                     responses=[dict(id='accepted-preview', status=200,
                                     media_type='application/json', request_valid=True,
                                     fields=[accepted])])

    def request(valid):
        return dict(id='preview-request', revision=2 if valid else 1,
                    operation=operation['id'], operation_revision=1, operation_sha256=pin(operation),
                    method='POST', path=['service-preview'], media_type='application/json',
                    query={}, headers={}, body=copy.deepcopy(submission(valid)['values']),
                    expected_valid=True)

    def response(valid):
        req = request(True)
        return dict(id='preview-response', revision=2 if valid else 1,
                    request=req['id'], request_revision=req['revision'], request_sha256=pin(req),
                    status=200, media_type='application/json', headers={},
                    body=dict(accepted=True if valid else 'yes'), expected_valid=True)

    cases = []
    for valid in (False, True):
        suffix = 'corrected' if valid else 'failure'
        cases.append(('form-' + suffix, 'form', dict(format='outlands-form-submissions-v1',
                      forms=[form], submissions=[submission(valid)]), valid))
        cases.append(('request-' + suffix, 'request', dict(format='outlands-api-requests-v1',
                      operations=[operation], requests=[request(valid)]), valid))
        cases.append(('response-' + suffix, 'response', dict(format='outlands-api-responses-v1',
                      operations=[operation], requests=[request(True)], responses=[response(valid)]), valid))
        sub = submission(valid)
        cases.append(('history-' + suffix, 'history', dict(format='outlands-ui-histories-v1',
                      forms=[form], submissions=[sub], flows=[flow], histories=[history(sub)]), valid))
    for restored in (False, True):
        candidate_form = copy.deepcopy(form)
        candidate_form['revision'] = 3 if restored else 2
        candidate_form['fields'][1]['maximum'] = 5 if restored else 4
        candidate_sub = submission(True)
        candidate_sub.update(form_revision=candidate_form['revision'], form_sha256=pin(candidate_form))
        candidate_flow = copy.deepcopy(flow)
        candidate_flow.update(revision=candidate_form['revision'], form_revision=candidate_form['revision'],
                              form_sha256=pin(candidate_form))
        candidate_history = history(submission(True))
        candidate_history.update(flow_revision=candidate_flow['revision'], flow_sha256=pin(candidate_flow))
        candidate_history['events'][0]['submission_sha256'] = pin(candidate_sub)
        cases.append(('comparison-' + ('restored' if restored else 'narrowed'), 'comparison', dict(
            format='outlands-ui-interaction-scenarios-v1', baseline_forms=[form],
            candidate_forms=[candidate_form], baseline_flows=[flow], candidate_flows=[candidate_flow],
            baseline_submissions=[submission(True)], candidate_submissions=[candidate_sub],
            baseline_histories=[history(submission(True))], candidate_histories=[candidate_history]), restored))
    return cases


def verify_outcome(kind, good, report):
    require(report['status'] == ('PASS' if good else 'REVIEW_REQUIRED'), 'UNEXPECTED_VERDICT')
    assessment = report.get('assessment')
    require(isinstance(assessment, dict), 'ASSESSMENT_WITHHELD')
    if kind in ('form', 'request'):
        rows = assessment['submissions' if kind == 'form' else 'requests']
        require(len(rows) == 1 and rows[0]['valid'] is good, 'VALIDITY_MISMATCH')
        priority = next(r for r in rows[0]['fields'] if r['id'] == ('priority' if kind == 'form' else 'field-priority'))
        require(priority['state'] == ('valid' if good else 'type_invalid'), 'PRIORITY_CHECK_MISMATCH')
    elif kind == 'response':
        row = assessment['responses'][0]
        require(row['valid'] is good, 'RESPONSE_VALIDITY_MISMATCH')
        require(row['fields'][0]['state'] == ('valid' if good else 'type_invalid'), 'RESPONSE_TYPE_MISMATCH')
    elif kind == 'history':
        row = assessment['histories'][0]
        require(row['valid'] is good and row['terminal_reached'] is good, 'HISTORY_VALIDITY_MISMATCH')
        require(row['last_confirmed_state'] == ('recorded' if good else 'draft'), 'HISTORY_STATE_MISMATCH')
        if not good:
            require('SUBMISSION_VALIDITY_MISMATCH' in row['steps'][0]['failed_criteria'], 'MISSING_GUARD_FAILURE')
    else:
        require(assessment['all_declared_outcomes_equal'] is good, 'COMPARISON_EQUALITY_MISMATCH')
        require(len(assessment['submissions']) == len(assessment['histories']) == 1, 'COMPARISON_SCOPE_MISMATCH')
        row = assessment['histories'][0]
        require(row['baseline']['terminal_reached'] is True and row['candidate']['terminal_reached'] is good,
                'COMPARISON_STATE_MISMATCH')
        priority = next(r for r in assessment['submissions'][0]['candidate']['fields'] if r['id'] == 'priority')
        require(priority['state'] == ('valid' if good else 'out_of_range'), 'COMPARISON_RANGE_MISMATCH')
    require(report.get('network_requests_performed') is False, 'NETWORK_BOUNDARY_MISMATCH')


def source_hashes():
    return {p.relative_to(ROOT).as_posix(): digest(p.read_bytes())
            for name, _ in TOOLS.values() for p in sorted((ROOT / 'tools' / name).glob('*.py'))}


def run(workspace):
    target = Path(workspace)
    require(target.is_absolute(), 'NEW_ABSOLUTE_EXTERNAL_WORKSPACE_REQUIRED')
    require(not target.exists() and not target.is_symlink(), 'NEW_ABSOLUTE_EXTERNAL_WORKSPACE_REQUIRED')
    for parent in target.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and not parent.is_symlink()
                and not (getattr(info, 'st_file_attributes', 0) & 0x400), 'LINKED_PARENT_REFUSED')
    target = target.resolve()
    require(not target.is_relative_to(ROOT), 'NEW_ABSOLUTE_EXTERNAL_WORKSPACE_REQUIRED')
    before = source_hashes()
    target.mkdir(mode=0o700)
    (target / 'inputs').mkdir()
    (target / 'reports').mkdir()
    results = []
    for name, kind, payload, good in fixtures():
        raw = encode(payload)
        input_path = target / 'inputs' / (name + '.json')
        input_path.write_bytes(raw)
        folder, script = TOOLS[kind]
        process = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / folder / script),
                                  '--input', str(input_path)], cwd=ROOT / 'tools' / folder,
                                 capture_output=True, timeout=30)
        (target / 'reports' / (name + '.json')).write_bytes(process.stdout)
        if process.stderr:
            (target / 'reports' / (name + '.stderr-private.txt')).write_bytes(process.stderr)
        if process.returncode != (0 if good else 1):
            raise ValueError('CLI_CHECK_FAILED_' + name.upper().replace('-', '_'))
        report = json.loads(process.stdout)
        verify_outcome(kind, good, report)
        require(input_path.read_bytes() == raw, 'INPUT_CHANGED')
        results.append(dict(id=name, tool=folder, expected_status='PASS' if good else 'REVIEW_REQUIRED',
                            observed_status=report['status'], exit_code=process.returncode,
                            input_sha256=digest(raw), report_sha256=digest(process.stdout)))
    require(source_hashes() == before, 'TOOL_SOURCE_CHANGED')
    result = dict(format='outlands-software-quality-exercise-v1', status='PASS',
                  command_checks=len(results), expected_review_outcomes=5, results=results,
                  source_hashes=before, original_sources_unchanged=True, input_bytes_unchanged=True,
                  fictional_data_only=True, network_requests_performed=False,
                  browser_application_tested=False, real_service_verified=False,
                  clean_windows_acceptance=False, publication_authorized=False)
    (target / 'result.json').write_bytes(encode(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    options = parser.parse_args()
    try:
        result = run(options.workspace)
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, StopIteration):
        print(json.dumps(dict(status='REFUSED_OR_FAILED', code='EXERCISE_NOT_COMPLETED')))
        return 2
    print(json.dumps({k: result[k] for k in ('status', 'command_checks', 'expected_review_outcomes',
                                           'original_sources_unchanged', 'network_requests_performed')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
