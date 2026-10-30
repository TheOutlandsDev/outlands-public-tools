"""Bounded field metadata and exact declarative references; no values, includes or runtime reads."""
import toolkit as t
import decision_core as c

TYPES=('boolean','integer','string')

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def field(row):
    key,out=c.record(row,{'id','type','required','default_sha256','constraint_sha256'},('id',))
    t.require(row['type'] in TYPES,'FIELD_TYPE_INVALID');t.require(type(row['required']) is bool,'REQUIRED_FLAG_INVALID')
    if row['default_sha256'] is not None:t.sha(row['default_sha256'])
    t.sha(row['constraint_sha256']);return key,out

def contract(value,side,counts,issues):
    t.fields(value,{'id','revision','fields'});t.identifier(value['id']);t.integer(value['revision'],10**6,1)
    t.require(type(value['fields']) is list and len(value['fields'])<=128,'FIELD_LIMIT')
    fields=collect(value['fields'],field,side+'_fields',counts,issues,False)
    return dict(id=value['id'],revision=value['revision'],fields=[fields[key][1] for key in sorted(fields)])

def contract_record(value):
    # Nested definitions are structural rows here; the whole row is withheld if any field is invalid.
    counts={};issues=[];out=contract(value,'contract',counts,issues)
    t.require(not issues,'CONTRACT_FIELDS_INVALID');return out['id'],out

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

def output(raw,fmt,counts,issues,qualified,assessment,pins,**extra):
    report=c.base(raw,fmt,counts,issues)
    report.update(assessment=assessment,qualified_scope_sha256=c.pin(dict(format=fmt,**pins)) if qualified and not issues else None,
        raw_setting_values_emitted=False,settings_values_validated=False,runtime_compatibility_verified=False,
        adapter_bytes_verified=False,migration_executed=False,configuration_changed=False,installation_performed=False,execution_performed=False,**extra)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
