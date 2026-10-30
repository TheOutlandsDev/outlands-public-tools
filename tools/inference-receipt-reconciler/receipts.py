"""Reconcile declared attempt/result receipts against a recomputed bounded fallback plan."""
import toolkit as t
import decision_core as c
import routing_core as r

def attempt(row):
    key,out=c.record(row,{'id','ordinal','step','model','model_revision','model_sha256','request_sha256','plan_sha256','status','failure_class','output_sha256','output_units'},('id','step','model'),('model_revision',))
    t.integer(row['ordinal'],32,1)
    for field in ('model_sha256','request_sha256','plan_sha256'):t.sha(row[field])
    t.require(row['status'] in ('succeeded','failed','unknown'),'ATTEMPT_STATUS_INVALID')
    if row['status']=='succeeded':
        t.require(row['failure_class'] is None,'FAILURE_CLASS_INVALID');t.sha(row['output_sha256']);t.integer(row['output_units'],10**9)
    else:
        t.require(row['output_sha256'] is None and row['output_units'] is None,'OUTPUT_DECLARATION_INVALID')
        t.require(row['failure_class'] in r.FAILURES if row['status']=='failed' else row['failure_class'] is None,'FAILURE_CLASS_INVALID')
    return key,out

def result(row):
    t.fields(row,{'status','attempts','final_attempt','output_sha256'});t.require(row['status'] in ('succeeded','failed','unknown'),'RESULT_STATUS_INVALID')
    t.integer(row['attempts'],32)
    if row['final_attempt'] is not None:t.identifier(row['final_attempt'])
    if row['status']=='succeeded':t.sha(row['output_sha256']);t.require(row['final_attempt'] is not None,'FINAL_ATTEMPT_REQUIRED')
    else:t.require(row['output_sha256'] is None,'OUTPUT_DECLARATION_INVALID')
    return dict(row)

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','models','request','policy','chain','attempts','result'})
    t.require(value['format']=='outlands-inference-receipts-v1','FORMAT_INVALID')
    counts={};issues=[];prepared,state=r.chain_scope(value,counts,issues);declared=result(value['result'])
    attempts=r.collect(value['attempts'],attempt,'attempts',counts,issues,False)
    r.unique_slots(attempts,'ordinal','attempts',issues)
    eligible=prepared['assessment'] is not None and prepared['assessment']['eligible_for_manual_routing_review']
    if not eligible:c.issue(issues,'plan',0,'PLAN_NOT_ELIGIBLE')
    if eligible:
        steps={row['id']:row for row in state['order']}
        for position,row in attempts.values():
            step=steps.get(row['step'])
            if step is None:c.issue(issues,'attempts',position,'STEP_UNKNOWN')
            elif any(row[field]!=step[field] for field in ('model','model_revision','model_sha256')):c.issue(issues,'attempts',position,'STEP_MODEL_BINDING_MISMATCH')
            if row['request_sha256']!=prepared['request_sha256']:c.issue(issues,'attempts',position,'REQUEST_PIN_MISMATCH')
            if row['plan_sha256']!=prepared['plan_sha256']:c.issue(issues,'attempts',position,'PLAN_PIN_MISMATCH')
    ordered=sorted(attempts.values(),key=lambda pair:pair[1]['ordinal'])
    if not issues:
        if [row['ordinal'] for _,row in ordered]!=list(range(1,len(ordered)+1)):c.issue(issues,'attempts',0,'ORDINAL_GAP')
        if len(ordered)>state['chain']['maximum_attempts']:c.issue(issues,'attempts',0,'ATTEMPT_CAP_EXCEEDED')
        for index,(position,row) in enumerate(ordered):
            if index==0:
                if row['step']!=state['chain']['start']:c.issue(issues,'attempts',position,'START_STEP_MISMATCH')
            else:
                previous=ordered[index-1][1];step=steps[previous['step']]
                if previous['status']!='failed' or previous['failure_class'] not in step['on_failures'] or step['next_step']!=row['step']:
                    c.issue(issues,'attempts',position,'TRANSITION_NOT_ALLOWED')
    qualified=not issues;assessment=None
    if qualified:
        rows=[row for _,row in ordered];last=rows[-1] if rows else None;failures=[]
        status=last['status'] if last else 'unknown'
        if last and status=='failed':
            step=steps[last['step']]
            if step['next_step'] is not None and last['failure_class'] in step['on_failures']:
                status='unknown';failures.append('FALLBACK_RECEIPT_MISSING')
        if not rows:failures.append('ATTEMPTS_MISSING')
        if status=='unknown':failures.append('TERMINAL_OUTCOME_UNKNOWN')
        for row in rows:
            if row['status']=='succeeded' and row['output_units']>state['request']['output_budget']:failures.append('OUTPUT_BUDGET_EXCEEDED')
        final_id=last['id'] if last else None;output_pin=last['output_sha256'] if last and last['status']=='succeeded' else None
        for matches,code in [(declared['status']==status,'RESULT_STATUS_MISMATCH'),(declared['attempts']==len(rows),'RESULT_ATTEMPT_COUNT_MISMATCH'),
            (declared['final_attempt']==final_id,'FINAL_ATTEMPT_MISMATCH'),(declared['output_sha256']==output_pin,'RESULT_OUTPUT_PIN_MISMATCH')]:
            if not matches:failures.append(code)
        failures=sorted(set(failures))
        for code in failures:c.issue(issues,'result',0,code)
        assessment=dict(attempts=len(rows),ordered_attempt_ids=[row['id'] for row in rows],observed_terminal_status=status,
            final_attempt=final_id,output_sha256=output_pin,failed_criteria=failures,eligible_for_manual_receipt_review=not failures)
    plan_assessment=prepared.pop('assessment')
    return r.output(raw,'outlands-inference-receipts-report-v1',counts,issues,assessment=assessment,plan_assessment=plan_assessment,
        attempts_sha256=c.cohort_pin(attempts) if qualified else None,**prepared)

def main(argv=None):return c.cli('Reconcile supplied inference receipts; no inference or proof of occurrence.',check,argv)
if __name__=='__main__':raise SystemExit(main())
