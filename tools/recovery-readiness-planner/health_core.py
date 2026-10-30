"""Bounded declared component/incident identities and ordinal freshness; no collectors."""
import toolkit as t
import decision_core as c

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def component(row):
    key,out=c.record(row,{'id','revision','maximum_age'},('id',),('revision',));t.integer(row['maximum_age'],10**9);return key,out

def incident(row):
    key,out=c.record(row,{'id','revision','component','component_revision','component_sha256'},('id','component'),('revision','component_revision'));t.sha(row['component_sha256']);return key,out

def reference(row,field,records,side,position,issues):
    target=records.get(row[field])
    if target is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    target=target[1]
    if row[field+'_revision']!=target['revision'] or row[field+'_sha256']!=c.pin(target):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return target

def slots(records,slot,side,issues):
    seen=set()
    for position,row in records.values():
        key=slot(row)
        if key in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen.add(key)

def freshness(observed_at,as_of,maximum_age):
    future=observed_at>as_of;age=None if future else as_of-observed_at
    return dict(age=age,future=future,fresh=not future and age<=maximum_age)

def output(raw,fmt,counts,issues,qualified,assessment,records,policy=None,context=None):
    pins={side+'_sha256':c.cohort_pin(rows) for side,rows in records.items()}
    if policy is not None:pins['policy_sha256']=c.pin(policy)
    context={} if context is None else context
    report=c.base(raw,fmt,counts,issues)
    report.update(context)
    report.update(assessment=assessment,qualified_scope_sha256=c.pin(dict(format=fmt,**pins,**context)) if qualified and not issues else None,
        observations_independently_verified=False,artifact_bytes_verified=False,actual_health_verified=False,
        notifications_sent=False,alerts_suppressed=False,recovery_authorized=False,recovery_performed=False,records_changed=False)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
