"""Bounded declared identities, integer quantities and exact references without stock access."""
import toolkit as t
import decision_core as c

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def stock(row):
    key,out=c.record(row,{'id','revision','item','unit','on_hand','at'},('id','item','unit'),('revision',));t.integer(row['on_hand'],10**12);t.integer(row['at']);return key,out

def reference(row,field,records,side,position,issues):
    target=records.get(row[field])
    if target is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    target=target[1]
    if row[field+'_revision']!=target['revision'] or row[field+'_sha256']!=c.pin(target):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return target

def item_unit(row,target,side,position,issues):
    if target and (row['item']!=target['item'] or row['unit']!=target['unit']):c.issue(issues,side,position,'ITEM_OR_UNIT_MISMATCH')

def slots(records,slot,side,issues):
    seen=set()
    for position,row in records.values():
        key=slot(row)
        if key in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen.add(key)

def output(raw,fmt,counts,issues,qualified,assessment,records,context=None):
    pins={side+'_sha256':c.cohort_pin(rows) for side,rows in records.items()};context={} if context is None else context
    report=c.base(raw,fmt,counts,issues);report.update(context)
    report.update(assessment=assessment,qualified_scope_sha256=c.pin(dict(format=fmt,**pins,**context)) if qualified and not issues else None,
        physical_stock_verified=False,inbound_eligibility_verified=False,delivery_verified=False,records_changed=False,
        stock_updated=False,purchase_order_created=False,reservations_changed=False,shipment_executed=False,procurement_authorized=False)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
