"""Check explicit attempt budgets and capped delays without waiting or retrying."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import cache_core as r

def policy(row):
    _,out=c.record(row,{'id','revision','maximum_attempts','base_delay','maximum_delay','retryable_failures'},('id',),('revision',))
    t.integer(row['maximum_attempts'],32,1);t.integer(row['base_delay'],10**6);t.integer(row['maximum_delay'],10**9)
    t.require(row['base_delay']<=row['maximum_delay'],'DELAY_POLICY_INVALID')
    out['retryable_failures']=c.tags(row['retryable_failures']);t.require(set(out['retryable_failures'])<=set(r.FAILURES),'FAILURE_CLASS_UNKNOWN');return out

def attempt(row):
    key,out=c.record(row,{'id','operation','operation_revision','operation_sha256','policy_sha256','ordinal','at','status','failure_class','result_sha256'},('id','operation'),('operation_revision',))
    t.sha(row['operation_sha256']);t.sha(row['policy_sha256']);t.integer(row['ordinal'],32,1);r.ordinal(row['at'])
    t.require(row['status'] in ('failed','succeeded','unknown'),'ATTEMPT_STATUS_INVALID')
    if row['status']=='unknown':t.require(row['failure_class'] is None and row['result_sha256'] is None,'UNKNOWN_RECEIPT_INVALID')
    else:
        t.sha(row['result_sha256']);t.require(row['failure_class'] in r.FAILURES if row['status']=='failed' else row['failure_class'] is None,'FAILURE_CLASS_INVALID')
    return key,out

def delay(rule,ordinal):return min(rule['maximum_delay'],rule['base_delay']*2**(ordinal-1))

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','policy','operations','attempts','as_of'})
    t.require(value['format']=='outlands-retry-budget-v1','FORMAT_INVALID')
    rule=policy(value['policy']);as_of=r.ordinal(value['as_of']);counts={};issues=[]
    operations=r.collect(value['operations'],r.operation,'operations',counts,issues)
    attempts=r.collect(value['attempts'],attempt,'attempts',counts,issues,False)
    r.unique_slots(operations,lambda row:row['key_sha256'],'operations',issues)
    r.unique_slots(attempts,lambda row:(row['operation'],row['ordinal']),'attempts',issues)
    histories=defaultdict(list)
    for key,(position,row) in attempts.items():
        r.operation_reference(row,operations,'attempts',position,issues)
        if row['policy_sha256']!=c.pin(rule):c.issue(issues,'attempts',position,'POLICY_PIN_MISMATCH')
        if row['at']>as_of:c.issue(issues,'attempts',position,'ATTEMPT_AFTER_AS_OF')
        histories[row['operation']].append((position,row))
    if not issues:
        for rows in histories.values():
            rows.sort(key=lambda p:p[1]['ordinal'])
            if [row['ordinal'] for _,row in rows]!=list(range(1,len(rows)+1)):c.issue(issues,'attempts',0,'ORDINAL_GAP')
            for (_,before),(position,after) in zip(rows,rows[1:]):
                if before['at']>after['at']:c.issue(issues,'attempts',position,'TIME_ORDER_INVALID')
                if before['status']!='failed' or before['failure_class'] not in rule['retryable_failures']:c.issue(issues,'attempts',position,'TRANSITION_NOT_ALLOWED')
    qualified=not issues;assessment=None
    if qualified:
        outcomes=[]
        for key,(_,operation) in sorted(operations.items()):
            rows=histories[key];n=len(rows);last=rows[-1][1] if rows else None;codes=[];early=[];earliest=None;eligible=False
            for (_,before),(position,after) in zip(rows,rows[1:]):
                if after['at']<before['at']+delay(rule,before['ordinal']):early.append(after['id'])
            if early:codes.append('RETRY_BEFORE_REQUIRED_DELAY')
            if n>rule['maximum_attempts']:codes.append('ATTEMPT_CAP_EXCEEDED')
            if last is None:state='no_receipts';codes.append('ATTEMPT_HISTORY_MISSING')
            elif last['status']=='unknown':state='unknown';codes.append('OUTCOME_UNKNOWN')
            elif last['status']=='succeeded':state='succeeded'
            elif last['failure_class'] not in rule['retryable_failures']:state='terminal_failed'
            elif n>=rule['maximum_attempts']:state='exhausted'
            else:
                earliest=last['at']+delay(rule,last['ordinal']);state='policy_review_required' if codes else 'waiting' if as_of<earliest else 'ready_for_manual_review';eligible=as_of>=earliest and not codes
            for code in codes:c.issue(issues,'operations',0,code)
            outcomes.append(dict(id=key,attempts=n,remaining_attempts=max(0,rule['maximum_attempts']-n),state=state,
                earliest_next_at=earliest,early_attempt_ids=early,eligible_for_manual_attempt_review=eligible,failed_criteria=codes))
        assessment=dict(as_of=as_of,operations=outcomes)
    pins=dict(policy_sha256=c.pin(rule),operations_sha256=c.cohort_pin(operations),attempts_sha256=c.cohort_pin(attempts),as_of=as_of)
    return r.output(raw,'outlands-retry-budget-report-v1',counts,issues,assessment=assessment,
        budget_review_sha256=c.pin(pins) if qualified and not issues else None,
        **{key:pin if qualified or key=='as_of' else None for key,pin in pins.items()})

def main(argv=None):return c.cli('Review explicit attempt/delay declarations; no waits, retries or dispatch.',check,argv)
if __name__=='__main__':raise SystemExit(main())
