"""Twelve original CLI checks over one invented manufacturing review; no operations."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def require(value, code):
    if not value:
        raise ValueError(code)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(workspace):
    require(workspace.is_absolute() and '..' not in workspace.parts and not workspace.exists()
            and workspace.parent.is_dir(), 'NEW_EXTERNAL_WORKSPACE_REQUIRED')
    require(workspace.resolve() == workspace and not workspace.is_relative_to(ROOT), 'TRUSTED_EXTERNAL_PARENT_REQUIRED')
    for parent in workspace.parents:
        require(not parent.is_symlink() and not parent.is_junction(), 'ORDINARY_PARENT_REQUIRED')
    tools = dict(reservations=('resource-reservation-checker', 'reservations.py'),
                 eligibility=('assignment-eligibility-checker', 'assignments.py'),
                 durations=('process-event-duration-analyzer', 'durations.py'),
                 flows=('flow-balance-reconciler', 'flows.py'))
    require(all((ROOT/'tools'/folder/script).is_file() for folder, script in tools.values()), 'COMPLETE_PACKAGE_REQUIRED')
    workspace.mkdir(mode=0o700)
    inputs, results, receipts = {}, {}, []
    def write(name, value):
        raw = value if isinstance(value, bytes) else encoded(value)
        with (workspace/name).open('xb') as stream:
            stream.write(raw)
        return raw
    def call(kind, stage, value, expected):
        name = kind+'-'+stage
        raw = write(name+'-input.json', value)
        inputs[name+'-input.json'] = sha(raw)
        folder, script = tools[kind]
        env = {k:v for k,v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN', 'OUTLANDS_CATALOG_READ_TOKEN')}
        response = subprocess.run([sys.executable, '-B', str(ROOT/'tools'/folder/script), '--input', str(workspace/(name+'-input.json'))],
                                  capture_output=True, timeout=90, env={**env, 'PYTHONUTF8':'1', 'PYTHONDONTWRITEBYTECODE':'1'})
        if response.returncode != expected or response.stderr:
            write(name+'-private-failure.log', response.stdout+response.stderr)
            raise ValueError('COMMAND_FAILED_PRIVATE_LOG_RETAINED')
        result = json.loads(response.stdout)
        require(result['input_sha256'] == sha(raw), 'INPUT_PIN_MISMATCH')
        require(result['status'] == ('REVIEW_REQUIRED' if expected else 'PASS'), 'EXPECTED_STATUS_MISMATCH')
        for key in ('claims_authority_verified', 'content_privacy_verified', 'execution_authorized', 'target_changes_performed'):
            require(result[key] is False, 'AUTHORITY_BOUNDARY_CHANGED')
        write(name+'-report.json', response.stdout)
        results[name] = result
        receipts.append(dict(case=name, exit_code=response.returncode, input_sha256=sha(raw), report_sha256=sha(response.stdout)))
        return result

    # The same two declared resource snapshots feed both independent checks.
    resources = [dict(id='sample-station-a', capacity=2, capabilities=['assemble','inspect'], availability=[dict(start=0,end=20)]),
                 dict(id='sample-station-b', capacity=1, capabilities=['calibrate'], availability=[dict(start=0,end=20)])]
    tasks = [dict(id='sample-task-a',start=0,end=6,units=1,required_capabilities=['assemble']),
             dict(id='sample-task-b',start=3,end=12,units=2,required_capabilities=['inspect']),
             dict(id='sample-task-c',start=12,end=16,units=1,required_capabilities=['calibrate'])]
    assignments = [dict(id='sample-proposal-'+x,task_id='sample-task-'+x,resource_id='sample-station-a') for x in ('a','b','c')]
    proposal = dict(format='outlands-assignment-eligibility-v1',resources=resources,tasks=tasks,assignments=assignments)
    before = call('eligibility','before',proposal,1)
    by_task = {row['task_id']:row for row in before['assessments']}
    require(by_task['sample-task-c']['reasons'] == ['MISSING_CAPABILITY']
            and sum(row['eligible_under_declarations'] for row in before['assessments']) == 2, 'ELIGIBILITY_ORACLE_FAILED')
    fixed = copy.deepcopy(proposal)
    fixed['assignments'][2]['resource_id'] = 'sample-station-b'
    eligible = call('eligibility','capability-corrected',fixed,0)
    require(all(row['eligible_under_declarations'] for row in eligible['assessments'])
            and eligible['combined_reservation_capacity_checked'] is False, 'ELIGIBILITY_IS_NOT_COMBINED_CAPACITY')
    def reservations(document):
        declared = {row['id']:row for row in document['tasks']}
        return dict(format='outlands-resource-reservations-v1',resources=document['resources'],reservations=[
            dict(id=row['id'],resource_id=row['resource_id'],**{key:declared[row['task_id']][key] for key in ('start','end','units')})
            for row in document['assignments']])
    conflict = call('reservations','overlap',reservations(fixed),1)
    station = next(row for row in conflict['summary'] if row['id']=='sample-station-a')
    require(station['peak_units']==3 and station['over_capacity_spans']==[dict(start=3,end=6,units=3)], 'CAPACITY_ORACLE_FAILED')
    require(conflict['resource_contract_sha256']==eligible['resource_contract_sha256'], 'SHARED_RESOURCE_PIN_MISMATCH')
    # Author a separate proposed revision. No reservation or task is applied.
    revised = copy.deepcopy(fixed); revised['tasks'][1]['start'] = 6
    final_eligibility = call('eligibility','revised',revised,0)
    fits = call('reservations','revised',reservations(revised),0)
    final_station = next(row for row in fits['summary'] if row['id']=='sample-station-a')
    require(final_station['peak_units']==2 and final_station['over_capacity_spans']==[]
            and fits['resource_contract_sha256']==final_eligibility['resource_contract_sha256'], 'ADJACENT_BOUNDARY_ORACLE_FAILED')
    duplicate = reservations(revised); duplicate['reservations'].append(copy.deepcopy(duplicate['reservations'][0]))
    repeated = call('reservations','duplicate',duplicate,0)
    require(repeated['summary']==fits['summary'] and repeated['counts']['reservations']['duplicate_rows']==1, 'RESERVATION_REPLAY_INFLATED')

    events = [dict(id='sample-start',run_id='sample-run',at=0,kind='start'),
              dict(id='sample-hold',run_id='sample-run',at=2,kind='hold'),
              dict(id='sample-resume',run_id='sample-run',at=5,kind='resume'),
              dict(id='sample-finish',run_id='sample-run',at=12,kind='finish')]
    process = dict(format='outlands-process-event-durations-v1',runs=[dict(id='sample-run',start=0,end=12)],events=events)
    incomplete = copy.deepcopy(process); incomplete['events'].pop()
    missing = call('durations','incomplete',incomplete,1)
    require(missing['totals'] is None and missing['durations'] is None, 'INCOMPLETE_DURATIONS_MUST_BE_WITHHELD')
    durations = call('durations','complete',process,0)
    expected = dict(elapsed_ticks=12,active_ticks=9,hold_ticks=3,hold_count=1)
    require(durations['totals']==expected and 2+(12-5)==9 and 5-2==3 and 9+3==12, 'DURATION_ARITHMETIC_FAILED')
    duplicate = copy.deepcopy(process); duplicate['events'].append(copy.deepcopy(events[1]))
    repeated = call('durations','duplicate',duplicate,0)
    require(repeated['totals']==expected and repeated['counts']['events']['duplicate_rows']==1, 'EVENT_REPLAY_INFLATED')

    flow = dict(format='outlands-flow-balance-v1',unit='pieces',balances=[dict(id='sample-stock',opening=20,closing=17),dict(id='sample-wip',opening=0,closing=5)],
                movements=[dict(id='sample-receipt',from_bucket=None,to_bucket='sample-stock',quantity=5),
                           dict(id='sample-transfer',from_bucket='sample-stock',to_bucket='sample-wip',quantity=8),
                           dict(id='sample-dispatch',from_bucket='sample-wip',to_bucket=None,quantity=3)],
                adjustments=[dict(id='sample-scrap-declaration',bucket='sample-wip',delta=-1)])
    mismatch = call('flows','mismatch',flow,1)
    require(next(row for row in mismatch['balances'] if row['id']=='sample-wip')['delta']==1, 'BALANCE_MISMATCH_NOT_CAUGHT')
    corrected = copy.deepcopy(flow); corrected['balances'][1]['closing']=4
    balanced = call('flows','corrected',corrected,0)
    require(balanced['totals']['computed_closing']==20+5-3-1==21
            and {row['id']:row['computed_closing'] for row in balanced['balances']}=={'sample-stock':17,'sample-wip':4}, 'FLOW_ARITHMETIC_FAILED')
    duplicate = copy.deepcopy(corrected); duplicate['movements'].append(copy.deepcopy(corrected['movements'][1]))
    repeated = call('flows','duplicate',duplicate,0)
    require(repeated['totals']==balanced['totals'] and repeated['counts']['movements']['duplicate_rows']==1, 'MOVEMENT_REPLAY_INFLATED')
    require(all(sha((workspace/name).read_bytes())==pin for name,pin in inputs.items()), 'ORIGINAL_INPUT_CHANGED')
    require(len(receipts)==12 and sum(row['exit_code']==1 for row in receipts)==4, 'EXACT_TWELVE_CHECKS_REQUIRED')
    summary = dict(status='PASS',mode='FICTIONAL_MANUFACTURING_REVIEW',command_checks=12,expected_review_outcomes=4,
                   operator_review='REQUIRED',individual_eligibility_does_not_prove_combined_capacity=True,
                   eligible_before=2,eligible_after=3,peak_units_before=3,peak_units_after=2,capacity=2,
                   conflict_span=dict(start=3,end=6),duration_ticks=expected,stock_closing=17,wip_closing=4,total_closing=21,
                   initial_flow_delta=1,missing_finish_withholds_totals=True,duplicates_do_not_inflate=True,
                   resource_pins_match=True,original_inputs_unchanged=True,report_hashes_recomputed=True,
                   work_assigned=False,reservations_changed=False,schedule_optimized=False,balances_changed=False,
                   physical_quantities_verified=False,qualifications_certified=False,live_clock_used=False,
                   execution_authorized=False,publication_authorized=False,receipts=receipts)
    for row in receipts:
        require(sha((workspace/(row['case']+'-report.json')).read_bytes())==row['report_sha256'], 'REPORT_HASH_MISMATCH')
    write('observed-results.json',summary)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(run(args.workspace)))
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print(json.dumps(dict(error=str(error) if isinstance(error,ValueError) else 'EXERCISE_FAILED_PRIVATE_STATE_RETAINED')))
        raise SystemExit(1)
