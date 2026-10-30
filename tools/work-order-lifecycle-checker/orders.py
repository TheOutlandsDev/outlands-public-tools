"""Check selected order snapshots against explicit, complete revision histories."""
from collections import defaultdict
import toolkit as t
import service_core as c

def event(row):
    key,out=c.record(row,{'id','order_id','revision','at','kind'},('id','order_id'),(('revision',1,1000),('at',0,10**9)))
    t.require(row['kind'] in ('create','start','hold','resume','complete','cancel'),'ORDER_EVENT_KIND_INVALID');return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','orders','events'})
    t.require(value['format']=='outlands-work-order-lifecycle-v1','FORMAT_INVALID')
    orders,oc,issues=c.rows(value['orders'],c.order,'orders');events,ec,other=c.rows(value['events'],event,'events');issues+=other
    if not orders:c.issue(issues,'orders',0,'EMPTY_ORDER_COHORT')
    c.unique(events,('order_id','revision'),'events',issues,'ORDER_REVISION_AMBIGUOUS')
    grouped=defaultdict(list)
    for index,row in events.values():
        if row['order_id'] not in orders:c.issue(issues,'events',index,'ORDER_MISSING')
        else:grouped[row['order_id']].append((index,row))
    transitions={('new','create'):'open',('open','start'):'in_progress',('in_progress','hold'):'on_hold',
                 ('on_hold','resume'):'in_progress',('in_progress','complete'):'completed',
                 ('open','cancel'):'cancelled',('in_progress','cancel'):'cancelled',('on_hold','cancel'):'cancelled'}
    summaries=[]
    for key,(index,row) in sorted(orders.items()):
        ordered=sorted(grouped[key],key=lambda p:(p[1]['at'],p[1]['id']));state='new';revision=0;last=-1
        for ei,entry in ordered:
            if entry['at']<=last:c.issue(issues,'events',ei,'ORDER_TIME_TIE')
            if entry['revision']!=revision+1:c.issue(issues,'events',ei,'ORDER_REVISION_NOT_CONTIGUOUS')
            next_state=transitions.get((state,entry['kind']))
            if next_state is None:c.issue(issues,'events',ei,'ORDER_TRANSITION_INVALID')
            else:state=next_state
            last=entry['at'];revision=entry['revision']
        if not ordered:c.issue(issues,'orders',index,'ORDER_HISTORY_MISSING')
        if revision!=row['revision'] or state!=row['state']:c.issue(issues,'orders',index,'ORDER_SNAPSHOT_MISMATCH')
        summaries.append(dict(row,order_sha256=c.order_pin(row),event_count=len(ordered),first_at=ordered[0][1]['at'] if ordered else None,last_at=last if ordered else None))
    result=c.base(raw,'outlands-work-order-lifecycle-review-v1',dict(orders=oc,events=ec),issues)
    result.update(orders=summaries if not issues else None,service_work_verified=False,completion_evidence_checked=False,orders_changed=False)
    return result

def main(argv=None):return c.cli('Check declared order histories; no dispatch or order changes.',check,argv)
if __name__=='__main__':raise SystemExit(main())
