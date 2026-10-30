"""Explicit pinned snapshots and bounded ordinal history without cache or service access."""
import toolkit as t
import decision_core as c

FAILURES=('timeout','unavailable','rate-limited','transient')

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def inputs(value,minimum=0):
    t.require(type(value) is list and minimum<=len(value)<=32,'DEPENDENCY_LIMIT')
    rows=[];seen=set()
    for row in value:
        key,out=c.record(row,{'id','revision','sha256'},('id',),('revision',));t.sha(row['sha256'])
        t.require(key not in seen,'DEPENDENCY_AMBIGUOUS');seen.add(key);rows.append(out)
    return sorted(rows,key=lambda r:r['id'])

def operation(row):
    key,out=c.record(row,{'id','revision','key_sha256','payload_sha256'},('id',),('revision',))
    t.sha(row['key_sha256']);t.sha(row['payload_sha256']);return key,out

def operation_reference(row,operations,side,position,issues):
    selected=operations.get(row['operation'])
    if selected is None:c.issue(issues,side,position,'OPERATION_UNKNOWN');return None
    target=selected[1]
    if row['operation_revision']!=target['revision'] or row['operation_sha256']!=c.pin(target):c.issue(issues,side,position,'OPERATION_SNAPSHOT_MISMATCH')
    return target

def unique_slots(rows,slot,side,issues):
    seen={}
    for position,row in rows.values():
        key=slot(row)
        if key in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen[key]=row
    return seen

def ordinal(value):return t.integer(value,10**12)

def output(raw,fmt,counts,issues,**values):
    report=c.base(raw,fmt,counts,issues)
    report.update(artifact_bytes_verified=False,record_authenticity_verified=False,
        actual_cache_state_verified=False,cache_mutated=False,execution_performed=False,
        exactly_once_verified=False,retry_authorized=False,provider_contacted=False,**values)
    return report
