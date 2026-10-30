"""Validate complete declared handoff histories and receipt references offline."""
from collections import defaultdict
import toolkit as t
import material_core as c

def handoff(row):
    key,result=c.record(row,{'id','lot_id','quantity','from_bucket','to_bucket'},('id','lot_id','from_bucket','to_bucket'),(('quantity',1,10**12),))
    t.require(row['from_bucket']!=row['to_bucket'],'HANDOFF_ENDPOINTS_INVALID');return key,result
def event(row):
    key,result=c.record(row,{'id','handoff_id','at','kind'},('id','handoff_id'),(('at',0,10**9),))
    t.require(row['kind'] in ('prepare','dispatch','accept','cancel'),'EVENT_KIND_INVALID');return key,result
def receipt(row):return c.record(row,{'id','handoff_id','event_id','quantity'},('id','handoff_id','event_id'),(('quantity',1,10**12),))

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','unit','handoffs','events','receipts'})
    t.require(value['format']=='outlands-handoff-lifecycle-v1','FORMAT_INVALID');t.identifier(value['unit'])
    handoffs,hc,issues=c.rows(value['handoffs'],handoff,'handoffs')
    events,ec,other=c.rows(value['events'],event,'events');issues+=other
    receipts,rc,other=c.rows(value['receipts'],receipt,'receipts');issues+=other
    if not handoffs:c.problem(issues,'handoffs',0,'EMPTY_HANDOFF_COHORT')
    histories=defaultdict(list);proofs=defaultdict(list)
    for index,row in events.values():
        if row['handoff_id'] not in handoffs:c.problem(issues,'events',index,'HANDOFF_MISSING')
        else:histories[row['handoff_id']].append((index,row))
    for index,row in receipts.values():
        if row['handoff_id'] not in handoffs:c.problem(issues,'receipts',index,'HANDOFF_MISSING')
        else:proofs[row['handoff_id']].append((index,row))
        if row['event_id'] not in events:c.problem(issues,'receipts',index,'RECEIPT_EVENT_MISSING')
        else:
            target=events[row['event_id']][1]
            if target['handoff_id']!=row['handoff_id'] or target['kind']!='accept':c.problem(issues,'receipts',index,'RECEIPT_EVENT_MISMATCH')
    summaries=[]
    transitions={('pending','prepare'):'prepared',('prepared','dispatch'):'dispatched',
                 ('dispatched','accept'):'accepted',('prepared','cancel'):'cancelled',('dispatched','cancel'):'cancelled'}
    for key,(index,row) in sorted(handoffs.items()):
        ordered=sorted(histories[key],key=lambda p:(p[1]['at'],p[1]['id']));times=defaultdict(list);state='pending'
        for ei,entry in ordered:times[entry['at']].append(ei)
        for indices in times.values():
            if len(indices)>1:
                for ei in indices:c.problem(issues,'events',ei,'EVENT_TIME_TIE')
        for ei,entry in ordered:
            next_state=transitions.get((state,entry['kind']))
            if next_state is None:c.problem(issues,'events',ei,'HANDOFF_TRANSITION_INVALID')
            else:state=next_state
        if state not in ('accepted','cancelled'):c.problem(issues,'handoffs',index,'HANDOFF_NOT_TERMINAL')
        selected=proofs[key]
        if state=='accepted':
            if len(selected)!=1:c.problem(issues,'handoffs',index,'ACCEPTANCE_RECEIPT_COUNT')
            for ri,proof in selected:
                if proof['quantity']!=row['quantity']:c.problem(issues,'receipts',ri,'RECEIPT_QUANTITY_MISMATCH')
        elif selected:
            for ri,_ in selected:c.problem(issues,'receipts',ri,'RECEIPT_WITHOUT_ACCEPTANCE')
        summaries.append(dict(id=key,lot_id=row['lot_id'],quantity=row['quantity'],state=state,
                              receipt_id=selected[0][1]['id'] if state=='accepted' and len(selected)==1 else None))
    result=c.base(raw,'outlands-handoff-lifecycle-review-v1',dict(handoffs=hc,events=ec,receipts=rc),issues)
    result.update(unit=value['unit'],handoffs=summaries if not issues else None,
                  accepted_quantity=sum(r['quantity'] for r in summaries if r['state']=='accepted') if not issues else None,
                  cancelled_quantity=sum(r['quantity'] for r in summaries if r['state']=='cancelled') if not issues else None,
                  delivery_independently_verified=False,inventory_coverage_checked=False,transfers_performed=False)
    return result

def main(argv=None):return c.cli('Review declared handoffs and receipts; no transfer or delivery proof.',check,argv)
if __name__=='__main__':raise SystemExit(main())
