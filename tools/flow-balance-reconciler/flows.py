"""Reconcile a declared whole-unit flow window without changing balances or replaying records."""
import toolkit as t
import resource_core as c


def balance(row):
    t.fields(row,{'id','opening','closing'}); t.identifier(row['id'])
    t.integer(row['opening']); t.integer(row['closing']); return row['id'],dict(row)


def movement(row):
    t.fields(row,{'id','from_bucket','to_bucket','quantity'}); t.identifier(row['id']); t.integer(row['quantity'],10**12,1)
    for key in ('from_bucket','to_bucket'):
        if row[key] is not None: t.identifier(row[key])
    t.require(row['from_bucket']!=row['to_bucket'],'MOVEMENT_ENDPOINTS_INVALID')
    return row['id'],dict(row)


def adjustment(row):
    t.fields(row,{'id','bucket','delta'}); t.identifier(row['id']); t.identifier(row['bucket'])
    t.integer(row['delta'],10**12,-10**12); t.require(row['delta']!=0,'ZERO_ADJUSTMENT')
    return row['id'],dict(row)


def reconcile(raw):
    value=t.decode(raw); t.fields(value,{'format','unit','balances','movements','adjustments'})
    t.require(value['format']=='outlands-flow-balance-v1','FORMAT_INVALID'); t.identifier(value['unit'])
    balances,bc,issues=c.rows(value['balances'],balance,'balances')
    movements,mc,other=c.rows(value['movements'],movement,'movements'); issues+=other
    adjustments,ac,other=c.rows(value['adjustments'],adjustment,'adjustments'); issues+=other
    if not balances: c.problem(issues,'balances',0,'EMPTY_BALANCE_COHORT')
    for key in set(movements)&set(adjustments):
        c.problem(issues,'movements',movements[key][0],'EVENT_ID_ALIAS'); c.problem(issues,'adjustments',adjustments[key][0],'EVENT_ID_ALIAS')
    for index,row in movements.values():
        for endpoint in (row['from_bucket'],row['to_bucket']):
            if endpoint is not None and endpoint not in balances: c.problem(issues,'movements',index,'BUCKET_MISSING')
    for index,row in adjustments.values():
        if row['bucket'] not in balances: c.problem(issues,'adjustments',index,'BUCKET_MISSING')
    summary=totals=None
    if not issues:
        entries={key:dict(id=key,opening=row['opening'],incoming=0,outgoing=0,adjustment=0,declared_closing=row['closing']) for key,(_,row) in balances.items()}
        external_in=external_out=internal=0
        for _,row in movements.values():
            source,target,q=row['from_bucket'],row['to_bucket'],row['quantity']
            if source is not None: entries[source]['outgoing']+=q
            else: external_in+=q
            if target is not None: entries[target]['incoming']+=q
            else: external_out+=q
            if source is not None and target is not None: internal+=q
        for _,row in adjustments.values(): entries[row['bucket']]['adjustment']+=row['delta']
        summary=[]
        for key,row in sorted(entries.items()):
            computed=row['opening']+row['incoming']-row['outgoing']+row['adjustment']; delta=row['declared_closing']-computed
            if computed<0: c.problem(issues,'balances',balances[key][0],'NEGATIVE_COMPUTED_CLOSING')
            if delta: c.problem(issues,'balances',balances[key][0],'FLOW_BALANCE_MISMATCH')
            summary.append(dict(row,computed_closing=computed,delta=delta))
        totals=dict(opening=sum(r['opening'] for r in summary),external_incoming=external_in,external_outgoing=external_out,
                    internal_transferred_units=internal,adjustment=sum(r['adjustment'] for r in summary),
                    computed_closing=sum(r['computed_closing'] for r in summary),declared_closing=sum(r['declared_closing'] for r in summary))
        t.require(totals['opening']+external_in-external_out+totals['adjustment']==totals['computed_closing'],'FLOW_ACCOUNTING_FAILED')
    result=c.base(raw,'outlands-flow-balance-review-v1',dict(balances=bc,movements=mc,adjustments=ac),issues)
    result.update(unit=value['unit'],balances=summary,totals=totals,actual_quantities_verified=False,
                  intermediate_balances_checked=False,balances_changed=False)
    return result


def main(argv=None): return c.cli('Reconcile declared opening, movements, adjustments and closing quantities without updates.',reconcile,argv)
if __name__=='__main__': raise SystemExit(main())
