"""Installed fictional import/progress review; no import, retry or checkpoint write."""
import copy
import json
from importlib.resources import files
from outlands_intake_mapping_diff.mapping_diff import compare
from outlands_batch_replay_planner.replay import plan
from outlands_checkpoint_progression_checker.checkpoints import check as checkpoint
from outlands_ingestion_run_coverage_checker.coverage import check as coverage

def raw(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')

def sample(package,name='input.json'):
    return json.loads(files(package).joinpath('examples',name).read_bytes())

def main():
    mapping=sample('outlands_intake_mapping_diff');window=sample('outlands_checkpoint_progression_checker')
    stream=window['stream'];expected=window['expected'];receipts=window['receipts']
    replay=dict(format='outlands-batch-replay-v1',stream=stream,expected=expected,receipts=receipts[:1])
    cohort=dict(format='outlands-ingestion-run-coverage-v1',stream=stream,expected=expected,receipts=receipts)
    mr=compare(raw(mapping));pr=plan(raw(replay));cr=checkpoint(raw(window));totals=coverage(raw(cohort))
    assert mr['status']==pr['status']==cr['status']==totals['status']=='PASS'
    assert all(row['mapping_sha256']==mr['before_mapping_sha256'] for row in expected)
    assert [row['decision'] for row in pr['plan']]==['SKIP_ALREADY_COMMITTED','MANUAL_REVIEW_NEW_BATCH']
    assert cr['suggested_checkpoint']==2 and cr['advancement_eligible_for_explicit_review'] is True
    assert totals['declared_totals']==dict(input_rows=6,accepted_records=4,duplicate_rows=2,rejected_rows=0,conflict_rows=0)
    changed=compare(raw(sample('outlands_intake_mapping_diff','needs-review.json')))
    assert changed['status']=='REVIEW_REQUIRED' and len(changed['changes'])==3
    duplicate=copy.deepcopy(cohort);duplicate['expected'].append(copy.deepcopy(duplicate['expected'][0]));duplicate['receipts'].append(copy.deepcopy(duplicate['receipts'][0]))
    once=coverage(raw(duplicate));assert once['status']=='PASS' and once['declared_totals']==totals['declared_totals']
    assert once['counts']['expected']['duplicate_rows']==once['counts']['receipts']['duplicate_rows']==1
    missing=copy.deepcopy(window);missing['receipts']=missing['receipts'][:1]
    blocked=checkpoint(raw(missing));assert blocked['status']=='REVIEW_REQUIRED' and blocked['suggested_checkpoint'] is None
    gap=copy.deepcopy(window);gap['expected']=gap['expected'][1:];gap['receipts']=gap['receipts'][1:]
    gap_report=checkpoint(raw(gap));assert gap_report['status']=='REVIEW_REQUIRED' and gap_report['suggested_checkpoint'] is None
    selected=coverage(raw(dict(format=cohort['format'],stream=stream,expected=gap['expected'],receipts=gap['receipts'])))
    assert selected['status']=='PASS' and selected['cohort_complete'] is True
    history=copy.deepcopy(replay);history['expected']=history['expected'][1:];history['receipts'][0]['status']='uncertain'
    uncertain=plan(raw(history));assert uncertain['status']=='REVIEW_REQUIRED' and uncertain['plan'] is None
    no_change=checkpoint(raw(dict(format=window['format'],stream=stream,previous=2,proposed=2,expected=[],receipts=[])))
    assert no_change['status']=='PASS' and no_change['suggested_checkpoint']==2 and no_change['advancement_eligible_for_explicit_review'] is False
    stale=copy.deepcopy(window);stale['expected'][0]['source_sha256']='0'*64
    stale_report=checkpoint(raw(stale));assert stale_report['status']=='REVIEW_REQUIRED' and stale_report['suggested_checkpoint'] is None
    rejected=copy.deepcopy(cohort)
    for row in (rejected['expected'][0],rejected['receipts'][0]['batch']):row['counts'].update(duplicate_rows=0,rejected_rows=1)
    refused_counts=coverage(raw(rejected));assert refused_counts['status']=='REVIEW_REQUIRED' and refused_counts['declared_totals'] is None
    for report in (mr,pr,cr,totals,changed,once,blocked,gap_report,selected,uncertain,no_change,stale_report,refused_counts):
        assert report['target_changes_performed'] is False and report['row_counts_recomputed'] is False
        assert report['receipt_authority_verified'] is False and report['exactly_once_verified'] is False
    for report in (pr,uncertain):assert report['execution_authorized'] is False and report['retry_performed'] is False
    for row in pr['plan']:assert row['execution_authorized'] is False
    for report in (cr,blocked,gap_report,no_change,stale_report):assert report['checkpoint_written'] is False
    print(json.dumps(dict(status='PASS',replay=['skip declared match','manual review missing receipt'],suggested_ordinal=2,declared_input_rows=6,declared_accepted_records=4,duplicate_declarations='counted once',checkpoint_gap='suggestion withheld',selected_coverage='PASS',uncertain_history='plan withheld',no_change='not eligible to advance',stale_metadata='suggestion withheld',rejected_counts='totals withheld',execution_authorized=False,exactly_once_verified=False),sort_keys=True))

if __name__=='__main__':
    main()
