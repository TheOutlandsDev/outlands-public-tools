"""Bounded synthetic test snapshots and exact observation contracts; no execution."""
import toolkit as t
import decision_core as c

STATES=('completed','timeout','cancelled','refused','not-run','output-limited','unknown')

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def case(row):
    key,out=c.record(row,{'id','revision','definition_sha256','input_sha256','expectation_sha256'},('id',),('revision',))
    for field in ('definition_sha256','input_sha256','expectation_sha256'):t.sha(row[field])
    return key,out

def expectation(row):
    key,out=c.record(row,{'id','case','case_revision','case_sha256','expected_exit','stdout_sha256','stderr_sha256'},('id','case'),('case_revision',))
    t.integer(row['expected_exit'],255)
    for field in ('case_sha256','stdout_sha256','stderr_sha256'):t.sha(row[field])
    return key,out

def expectation_pin(row):return c.pin(dict(exit_code=row['expected_exit'],stdout_sha256=row['stdout_sha256'],stderr_sha256=row['stderr_sha256']))

def slots(records,slot,side,issues):
    seen=set()
    for position,row in records.values():
        key=slot(row)
        if key in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen.add(key)

def reference(row,field,records,side,position,issues):
    target=records.get(row[field])
    if target is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    target=target[1]
    if row[field+'_revision']!=target['revision'] or row[field+'_sha256']!=c.pin(target):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return target

def select(v,counts,issues,prefix=''):
    cases=collect(v['cases'],case,prefix+'cases',counts,issues)
    expectations=collect(v['expectations'],expectation,prefix+'expectations',counts,issues,False)
    slots(expectations,lambda row:row['case'],prefix+'expectations',issues)
    for position,row in expectations.values():
        target=reference(row,'case',cases,prefix+'expectations',position,issues)
        if target and target['expectation_sha256']!=expectation_pin(row):c.issue(issues,prefix+'expectations',position,'EXPECTATION_DERIVATION_MISMATCH')
    return cases,expectations

def run(value):
    _,out=c.record(value,{'id','revision','subject_sha256','cases_sha256','expectations_sha256'},('id',),('revision',))
    for field in ('subject_sha256','cases_sha256','expectations_sha256'):t.sha(value[field])
    return out

def result(row):
    key,out=c.record(row,{'id','run','run_revision','run_sha256','case','case_revision','case_sha256','state','observed_exit','stdout_sha256','stderr_sha256','output_complete'},('id','run','case'),('run_revision','case_revision'))
    t.sha(row['run_sha256']);t.sha(row['case_sha256']);t.require(row['state'] in STATES,'STATE_INVALID');t.require(type(row['output_complete']) is bool,'COMPLETENESS_INVALID')
    if row['state']=='completed':
        t.integer(row['observed_exit'],255,-128);t.sha(row['stdout_sha256']);t.sha(row['stderr_sha256'])
    else:t.require(row['observed_exit'] is None and row['stdout_sha256'] is None and row['stderr_sha256'] is None and row['output_complete'] is False,'NONCOMPLETED_PAYLOAD_INVALID')
    return key,out

def bundle(v,counts,issues,prefix=''):
    t.fields(v,{'cases','expectations','run','results'})
    cases,expectations=select(v,counts,issues,prefix);header=run(v['run'])
    if header['cases_sha256']!=c.cohort_pin(cases) or header['expectations_sha256']!=c.cohort_pin(expectations):c.issue(issues,prefix+'run',0,'RUN_COHORT_MISMATCH')
    results=collect(v['results'],result,prefix+'results',counts,issues,False)
    slots(results,lambda row:row['case'],prefix+'results',issues)
    for position,row in results.values():
        reference(row,'case',cases,prefix+'results',position,issues)
        if row['run']!=header['id'] or row['run_revision']!=header['revision'] or row['run_sha256']!=c.pin(header):c.issue(issues,prefix+'results',position,'RUN_SNAPSHOT_MISMATCH')
    return dict(cases=cases,expectations=expectations,results=results,run=header)

def evaluate(b):
    expected={row['case']:row for _,row in b['expectations'].values()};observed={row['case']:row for _,row in b['results'].values()};out=[]
    for key,(position,case) in sorted(b['cases'].items()):
        exp=expected.get(key);row=observed.get(key);codes=[];matched=None
        if exp is None:codes.append('EXPECTATION_MISSING')
        if row is None:codes.append('RESULT_MISSING')
        elif row['state']!='completed':codes.append('RESULT_NOT_COMPLETED')
        elif not row['output_complete']:codes.append('OUTPUT_INCOMPLETE')
        elif exp is not None:
            matched=row['observed_exit']==exp['expected_exit'] and row['stdout_sha256']==exp['stdout_sha256'] and row['stderr_sha256']==exp['stderr_sha256']
            if not matched:codes.append('EXPECTED_RESULT_MISMATCH')
        out.append(dict(id=key,case_sha256=c.pin(case),result_id=row['id'] if row else None,state=row['state'] if row else 'missing',
            output_complete=row['output_complete'] if row else False,matched=matched,failed_criteria=codes))
    return out

def bundle_pins(b):return dict(cases_sha256=c.cohort_pin(b['cases']),expectations_sha256=c.cohort_pin(b['expectations']),results_sha256=c.cohort_pin(b['results']),run_sha256=c.pin(b['run']))

def output(raw,fmt,counts,issues,qualified,assessment,pins):
    report=c.base(raw,fmt,counts,issues)
    report.update(assessment=assessment,qualified_scope_sha256=c.pin(dict(format=fmt,**pins)) if qualified and not issues else None,
        artifact_bytes_verified=False,test_execution_verified=False,tests_executed=False,evidence_authenticity_verified=False,
        approval_authority_verified=False,records_changed=False)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
