"""Bounded declared snapshots and scope pins without identity or artifact discovery."""
import toolkit as t
import decision_core as c

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def snapshot(row):
    key,out=c.record(row,{'id','revision','artifact_sha256'},('id',),('revision',));t.sha(row['artifact_sha256']);return key,out

def roles(value):
    _,out=c.record(value,{'id','revision','required_roles'},('id',),('revision',));out['required_roles']=c.tags(value['required_roles'],1);return out

def reference(row,field,records,side,position,issues):
    selected=records.get(row[field])
    if selected is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    target=selected[1]
    if row[field+'_revision']!=target['revision'] or row[field+'_sha256']!=c.pin(target):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return target

def slots(records,key,side,issues):
    seen=set()
    for position,row in records.values():
        slot=key(row)
        if slot in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen.add(slot)

def output(raw,fmt,counts,issues,qualified,assessment,records,policy=None):
    pins={side+'_sha256':c.cohort_pin(rows) for side,rows in records.items()}
    if policy is not None:pins['policy_sha256']=c.pin(policy)
    report=c.base(raw,fmt,counts,issues)
    report.update(assessment=assessment,review_scope_sha256=c.pin(pins) if qualified and not issues else None,
        artifact_bytes_verified=False,reviewer_identity_verified=False,approval_authority_verified=False,
        records_changed=False,execution_performed=False)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
