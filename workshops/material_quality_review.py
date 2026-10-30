"""Twenty-four CLI checks of one fictional material-to-quality review; no operations."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = dict(bom=('bom-contract-checker', 'bom.py'),
             identities=('lot-identity-checker', 'identities.py'),
             allocations=('material-allocation-checker', 'allocations.py'),
             handoffs=('handoff-lifecycle-checker', 'handoffs.py'),
             measurements=('measurement-contract-checker', 'measurements.py'),
             inspections=('inspection-coverage-checker', 'inspections.py'),
             rework=('rework-history-checker', 'rework.py'),
             yields=('yield-scrap-reconciler', 'yields.py'))


def require(ok, code):
    if not ok:
        raise ValueError(code)


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'))+'\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(workspace):
    require(workspace.is_absolute() and '..' not in workspace.parts and not workspace.exists()
            and workspace.parent.is_dir(), 'NEW_EXTERNAL_WORKSPACE_REQUIRED')
    require(workspace.resolve() == workspace and not workspace.is_relative_to(ROOT), 'TRUSTED_EXTERNAL_PARENT_REQUIRED')
    for parent in workspace.parents:
        require(not parent.is_symlink() and not parent.is_junction(), 'ORDINARY_PARENT_REQUIRED')
    require(all((ROOT/'tools'/folder/script).is_file() for folder, script in TOOLS.values()), 'COMPLETE_PACKAGE_REQUIRED')
    workspace.mkdir(mode=0o700)
    inputs, reports, receipts = {}, {}, []

    def write(name, value):
        raw = value if isinstance(value, bytes) else encoded(value)
        with (workspace/name).open('xb') as stream:
            stream.write(raw)
        return raw

    def call(kind, stage, value, expected):
        name = kind+'-'+stage
        raw = write(name+'-input.json', value)
        inputs[name+'-input.json'] = sha(raw)
        folder, script = TOOLS[kind]
        env = {k:v for k,v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN', 'OUTLANDS_CATALOG_READ_TOKEN')}
        response = subprocess.run([sys.executable, '-B', str(ROOT/'tools'/folder/script), '--input', str(workspace/(name+'-input.json'))],
                                  capture_output=True, timeout=90, env={**env, 'PYTHONUTF8':'1', 'PYTHONDONTWRITEBYTECODE':'1'})
        if response.returncode != expected or response.stderr:
            write(name+'-private-failure.log', response.stdout+response.stderr)
            raise ValueError('COMMAND_FAILED_PRIVATE_LOG_RETAINED')
        result = json.loads(response.stdout)
        require(result['input_sha256'] == sha(raw), 'INPUT_PIN_MISMATCH')
        require(result['status'] == ('REVIEW_REQUIRED' if expected else 'PASS'), 'EXPECTED_STATUS_MISMATCH')
        for key in ('declarations_independently_verified', 'content_privacy_verified', 'execution_authorized', 'target_changes_performed'):
            require(result[key] is False, 'AUTHORITY_BOUNDARY_CHANGED')
        for counts in result['counts'].values():
            require(counts['input_rows'] == sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')), 'ROW_ACCOUNTING_FAILED')
        write(name+'-report.json', response.stdout)
        reports[name] = response.stdout
        receipts.append(dict(case=name, exit_code=response.returncode, input_sha256=sha(raw), report_sha256=sha(response.stdout)))
        return result

    # Four invented kits, each declaring one motor and two filters. No orders are placed.
    bom = dict(format='outlands-bom-contract-v1',
               components=[dict(id=x,unit='pieces') for x in ('sample-kit','sample-module','sample-motor','sample-filter')],
               links=[dict(id='kit-module',parent_id='sample-kit',component_id='sample-module',quantity=1),
                      dict(id='module-motor',parent_id='sample-module',component_id='sample-motor',quantity=1),
                      dict(id='kit-filters',parent_id='sample-kit',component_id='sample-filter',quantity=2)],
               orders=[dict(id='sample-proposal',component_id='sample-kit',quantity=4)])
    invalid = copy.deepcopy(bom)
    invalid['links'].append(dict(id='invalid-cycle',parent_id='sample-motor',component_id='sample-kit',quantity=1))
    bad_bom = call('bom','cycle',invalid,1)
    require(bad_bom['requirements'] is None, 'CYCLIC_REQUIREMENTS_MUST_BE_WITHHELD')
    requirements = call('bom','reviewed',bom,0)
    leaves = {r['component_id']:r for r in requirements['requirements'] if r['is_leaf']}
    require({key:r['quantity'] for key,r in leaves.items()} == {'sample-motor':4,'sample-filter':8}, 'BOM_ARITHMETIC_FAILED')

    lots = [dict(id='sample-motor-lot',item_id='sample-motor',unit='pieces',quantity=4),
            dict(id='sample-filter-lot',item_id='sample-filter',unit='pieces',quantity=8)]
    aliases = [dict(id='sample-bin-label',target_id='sample-motor-lot'),dict(id='sample-service-label',target_id='sample-bin-label')]
    identity = dict(format='outlands-lot-identities-v1',lots=lots,aliases=aliases)
    invalid = copy.deepcopy(identity); invalid['lots'].append({**lots[0],'quantity':5})
    conflict = call('identities','conflict',invalid,1)
    require(conflict['identities'] is None and conflict['canonical_totals'] is None and conflict['lot_contract_sha256'] is None, 'CONFLICTING_LOT_MUST_WITHHOLD_ALL')
    resolved = call('identities','reviewed',identity,0)
    require({r['item_id']:r['quantity'] for r in resolved['canonical_totals']}=={'sample-motor':4,'sample-filter':8}, 'ALIASES_MUST_NOT_ADD_STOCK')
    canonical = {r['id']:r['canonical_lot_id'] for r in resolved['identities']}
    require(canonical['sample-service-label']==canonical['sample-bin-label']=='sample-motor-lot', 'EXPLICIT_ALIAS_CHAIN_REQUIRED')
    duplicate = copy.deepcopy(identity); duplicate['lots'].append(copy.deepcopy(lots[0]))
    replay = call('identities','replay',duplicate,0)
    require(replay['canonical_totals']==resolved['canonical_totals'] and replay['counts']['lots']['duplicate_rows']==1, 'LOT_REPLAY_INFLATED')

    demands = [dict(id='demand-'+r['component_id'],item_id=r['component_id'],unit=r['unit'],quantity=r['quantity']) for r in leaves.values()]
    allocation = dict(format='outlands-material-allocations-v1',lots=lots,aliases=aliases,demands=demands,
                      allocations=[dict(id='motor-first',demand_id='demand-sample-motor',lot_id='sample-bin-label',quantity=2),
                                   dict(id='motor-second',demand_id='demand-sample-motor',lot_id='sample-service-label',quantity=3),
                                   dict(id='filter-selection',demand_id='demand-sample-filter',lot_id='sample-filter-lot',quantity=7)])
    over = call('allocations','overreserved',allocation,1)
    motor = next(r for r in over['lots'] if r['id']=='sample-motor-lot')
    require((motor['available'],motor['reserved'],motor['unreserved'],motor['excess'])==(4,5,-1,1), 'CANONICAL_OVERRESERVATION_NOT_CAUGHT')
    require(next(r for r in over['demands'] if r['item_id']=='sample-filter')['shortage']==1, 'FILTER_SHORTAGE_NOT_CAUGHT')
    corrected = copy.deepcopy(allocation); corrected['allocations'][1]['quantity']=2; corrected['allocations'][2]['quantity']=8
    allocated = call('allocations','reviewed',corrected,0)
    require(all(r['shortage']==r['excess']==0 for r in allocated['demands']) and all(r['unreserved']==0 for r in allocated['lots']), 'ALLOCATION_ARITHMETIC_FAILED')
    require(allocated['lot_contract_sha256']==resolved['lot_contract_sha256'], 'SHARED_LOT_PIN_MISMATCH')
    duplicate = copy.deepcopy(corrected); duplicate['allocations'].append(copy.deepcopy(corrected['allocations'][0]))
    replay = call('allocations','replay',duplicate,0)
    require(replay['lots']==allocated['lots'] and replay['counts']['allocations']['duplicate_rows']==1, 'ALLOCATION_REPLAY_INFLATED')

    # Explicit mapping selects the canonical ID and reviewed reserved quantity.
    selected = next(r for r in allocated['lots'] if r['id']==canonical['sample-service-label'])
    handoff = dict(format='outlands-handoff-lifecycle-v1',unit='pieces',
                   handoffs=[dict(id='sample-handoff',lot_id=selected['id'],quantity=selected['reserved'],from_bucket='sample-shelf',to_bucket='sample-bench')],
                   events=[dict(id='handoff-'+kind,handoff_id='sample-handoff',at=i,kind=kind) for i,kind in enumerate(('prepare','dispatch','accept'))],
                   receipts=[dict(id='sample-receipt',handoff_id='sample-handoff',event_id='handoff-accept',quantity=3)])
    bad_receipt = call('handoffs','receipt-mismatch',handoff,1)
    require(bad_receipt['handoffs'] is None and bad_receipt['accepted_quantity'] is None, 'BAD_RECEIPT_TOTAL_MUST_BE_WITHHELD')
    handoff['receipts'][0]['quantity']=4
    accepted = call('handoffs','reviewed',handoff,0)
    require(accepted['accepted_quantity']==4 and accepted['delivery_independently_verified'] is False and accepted['inventory_coverage_checked'] is False, 'RECEIPT_IS_NOT_DELIVERY_PROOF')
    duplicate = copy.deepcopy(handoff); duplicate['events'].append(copy.deepcopy(handoff['events'][2]))
    replay = call('handoffs','replay',duplicate,0)
    require(replay['accepted_quantity']==4 and replay['counts']['events']['duplicate_rows']==1, 'HANDOFF_REPLAY_INFLATED')

    cohort = [dict(id='sample-kit-'+x) for x in ('alpha','bravo','charlie','delta')]
    rule = dict(id='sample-teaching-window',revision=1,unit='demo-units',minimum='1',maximum='3',minimum_inclusive=True,maximum_inclusive=False)
    measured = dict(format='outlands-measurement-contract-v1',rules=[rule],measurements=[
        dict(id='measurement-'+r['id'],specimen_id=r['id'],check_id='sample-check',rule_id=rule['id'],rule_revision=1,unit='demo-units',value=v)
        for r,v in zip(cohort,('2','1','3','0'))])
    initial = call('measurements','initial',measured,1)
    initial_assessments = {r['specimen_id']:r for r in initial['assessments']}
    require(sum(r['within_declared_limits'] for r in initial['assessments'])==2
            and initial_assessments[cohort[2]['id']]['reasons']==['ABOVE_MAXIMUM'], 'EXCLUSIVE_DECIMAL_BOUNDARY_FAILED')
    later = copy.deepcopy(measured); later['measurements'][2]['value']='2'
    remeasured = call('measurements','selected-later',later,1)
    require(sum(r['within_declared_limits'] for r in remeasured['assessments'])==3 and remeasured['rule_contract_sha256']==initial['rule_contract_sha256'], 'LATER_SELECTION_OR_RULE_PIN_FAILED')
    duplicate = copy.deepcopy(later); duplicate['measurements'].append(copy.deepcopy(later['measurements'][0]))
    replay = call('measurements','replay',duplicate,1)
    require(replay['assessments']==remeasured['assessments'] and replay['counts']['measurements']['duplicate_rows']==1, 'MEASUREMENT_REPLAY_CHANGED_OUTCOME')

    def coverage(stage, result):
        # The runner pins the whole retained report. The coverage tool never opens it.
        pin = sha(reports['measurements-'+stage])
        return dict(format='outlands-inspection-coverage-v1',specimens=cohort,
                    checks=[dict(id='sample-check',rule_id=rule['id'],rule_revision=1)],
                    records=[dict(id='record-'+r['specimen_id'],specimen_id=r['specimen_id'],check_id=r['check_id'],rule_id=r['rule_id'],rule_revision=r['rule_revision'],
                                  source_sha256=pin,outcome='within_limits' if r['within_declared_limits'] else 'outside_limits') for r in result['assessments']])
    initial_coverage = coverage('initial',initial)
    missing = copy.deepcopy(initial_coverage); missing['records'].pop()
    gap = call('inspections','missing',missing,1)
    require(gap['summary']['expected_pairs']==4 and gap['summary']['recorded_pairs']==3 and gap['summary']['missing_pairs']==1, 'MISSING_COVERAGE_NOT_CAUGHT')
    complete = call('inspections','complete-initial',initial_coverage,1)
    require(complete['summary']['records_complete'] and not complete['summary']['all_records_within_limits'] and complete['summary']['outside_limits']==2, 'COMPLETE_RECORDS_ARE_NOT_ACCEPTANCE')
    later_coverage = coverage('selected-later',remeasured)
    selected_coverage = call('inspections','selected-later',later_coverage,1)
    require(selected_coverage['summary']['within_limits']==3 and selected_coverage['summary']['outside_limits']==1
            and selected_coverage['source_bytes_verified'] is False, 'COVERAGE_BOUNDARY_CHANGED')

    # Explicitly authored teaching protocol; these are supplied event assertions.
    events = []
    for row in initial['assessments']:
        events.append(dict(id='initial-'+row['specimen_id'],specimen_id=row['specimen_id'],at=0,attempt=1,kind='inspect_pass' if row['within_declared_limits'] else 'inspect_fail'))
    events += [dict(id='sample-rework',specimen_id=cohort[2]['id'],at=1,attempt=1,kind='rework'),
               dict(id='sample-reinspection',specimen_id=cohort[2]['id'],at=2,attempt=2,kind='inspect_pass'),
               dict(id='sample-scrap',specimen_id=cohort[3]['id'],at=1,attempt=1,kind='scrap')]
    history = dict(format='outlands-rework-histories-v1',units=cohort,events=events)
    invalid = copy.deepcopy(history); invalid['events'][-2]['attempt']=1
    bad_history = call('rework','invalid-attempt',invalid,1)
    require(bad_history['histories'] is None and bad_history['dispositions'] is None and bad_history['totals'] is None, 'INVALID_HISTORY_MUST_WITHHOLD_COHORT')
    histories = call('rework','reviewed',history,0)
    require(histories['totals']==dict(inspection_attempts=5,rework_events=1), 'HISTORY_TOTALS_FAILED')
    require([r['disposition'] for r in histories['dispositions']]==['first_pass_good','first_pass_good','reworked_good','scrap'], 'AUTHORED_PROTOCOL_ORACLE_FAILED')
    duplicate = copy.deepcopy(history); duplicate['events'].append(copy.deepcopy(events[0]))
    replay = call('rework','replay',duplicate,0)
    require(replay['dispositions']==histories['dispositions'] and replay['counts']['events']['duplicate_rows']==1, 'REWORK_REPLAY_INFLATED')

    yielding = dict(format='outlands-yield-scrap-v1',cohort=cohort,dispositions=histories['dispositions'])
    ambiguous = copy.deepcopy(yielding); ambiguous['dispositions'].append({**histories['dispositions'][0],'id':'contradictory-selection','disposition':'scrap'})
    withheld = call('yields','inconsistent',ambiguous,1)
    require(withheld['summary'] is None and withheld['fractions'] is None, 'INCONSISTENT_DISPOSITIONS_MUST_WITHHOLD_TOTALS')
    reconciled = call('yields','reviewed',yielding,0)
    require(reconciled['summary']==dict(closed_cohort=True,cohort=4,first_pass_good=2,reworked_good=1,scrap=1,pending=0,good=3), 'YIELD_COUNTS_FAILED')
    fractions = {key:r['exact_fraction'] for key,r in reconciled['fractions'].items()}
    require(fractions==dict(first_pass_yield='1/2',eventual_yield='3/4',scrap_fraction='1/4',pending_fraction='0/1') and 2+1+1==4, 'EXACT_FRACTIONS_FAILED')
    duplicate = copy.deepcopy(yielding); duplicate['dispositions'].append(copy.deepcopy(yielding['dispositions'][0]))
    replay = call('yields','replay',duplicate,0)
    require(replay['summary']==reconciled['summary'] and replay['fractions']==reconciled['fractions'] and replay['counts']['dispositions']['duplicate_rows']==1, 'YIELD_REPLAY_INFLATED')
    pending = copy.deepcopy(yielding); pending['dispositions'][3]['disposition']='pending'
    provisional = call('yields','pending',pending,1)
    require(provisional['summary']['pending']==1 and not provisional['summary']['closed_cohort']
            and provisional['fractions']['pending_fraction']==dict(numerator=1,denominator=4,exact_fraction='1/4'), 'PENDING_DENOMINATOR_CHANGED')

    require(len(receipts)==24 and sum(r['exit_code']==1 for r in receipts)==13, 'EXACT_TWENTY_FOUR_CHECKS_REQUIRED')
    require(all(sha((workspace/name).read_bytes())==pin for name,pin in inputs.items()), 'ORIGINAL_INPUT_CHANGED')
    for row in receipts:
        require(sha((workspace/(row['case']+'-report.json')).read_bytes())==row['report_sha256'], 'REPORT_HASH_MISMATCH')
    links = dict(bom_report_sha256=sha(reports['bom-reviewed']),lot_contract_sha256=resolved['lot_contract_sha256'],
                 allocation_report_sha256=sha(reports['allocations-reviewed']),handoff_canonical_lot_id=selected['id'],
                 measurement_report_sha256={stage:sha(reports['measurements-'+stage]) for stage in ('initial','selected-later')},
                 rework_report_sha256=sha(reports['rework-reviewed']),explicit_specimen_cohort=[r['id'] for r in cohort])
    write('authored-mapping.json',links)
    summary = dict(status='PASS',mode='FICTIONAL_MATERIAL_QUALITY_REVIEW',command_checks=24,expected_review_outcomes=13,
                   operator_review='REQUIRED',kits=4,motor_requirement=4,filter_requirement=8,canonical_motor_stock=4,
                   overreserved_motor_units=1,filter_shortage_before=1,accepted_receipt_quantity=4,initial_within_limits=2,
                   later_within_limits=3,coverage_missing_before=1,coverage_complete_still_requires_review=True,
                   inspection_attempts=5,rework_events=1,final_counts=reconciled['summary'],exact_fractions=fractions,
                   pending_fraction='1/4',duplicates_do_not_inflate=True,lot_pins_match=True,explicit_report_mappings=True,
                   original_inputs_unchanged=True,report_hashes_recomputed=True,mapping_sha256=sha(encoded(links)),
                   orders_created=False,stock_changed=False,reservations_changed=False,transfers_performed=False,
                   inspections_performed=False,rework_performed=False,physical_traceability_verified=False,
                   quality_target_evaluated=False,execution_authorized=False,publication_authorized=False,receipts=receipts)
    write('observed-results.json',summary)
    return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(run(args.workspace)))
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print(json.dumps(dict(error=str(error) if isinstance(error,ValueError) else 'EXERCISE_FAILED_PRIVATE_STATE_RETAINED')))
        raise SystemExit(1)
