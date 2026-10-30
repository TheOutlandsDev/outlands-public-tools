"""Calculate declared stock positions from exact snapshots and selected inbound/demand claims."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import stock_core as r

def claim(row,inbound):
    fields={'id','stock','stock_revision','stock_sha256','item','unit','quantity','source','state'}|({'due_at'} if inbound else set())
    key,out=c.record(row,fields,('id','stock','item','unit','source'),('stock_revision',));t.sha(row['stock_sha256']);t.integer(row['quantity'],10**12,1)
    t.require(row['state'] in (('usable','pending','cancelled') if inbound else ('reserved','released')),'STATE_INVALID')
    if inbound:t.integer(row['due_at'])
    return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','stocks','inbound','reservations','as_of','horizon'});t.require(v['format']=='outlands-inventory-position-v1','FORMAT_INVALID');t.integer(v['as_of']);t.integer(v['horizon']);t.require(v['horizon']>=v['as_of'],'HORIZON_INVALID')
    counts={};issues=[];stocks=r.collect(v['stocks'],r.stock,'stocks',counts,issues)
    inbound=r.collect(v['inbound'],lambda row:claim(row,True),'inbound',counts,issues,False);reservations=r.collect(v['reservations'],lambda row:claim(row,False),'reservations',counts,issues,False)
    for side,rows in [('inbound',inbound),('reservations',reservations)]:
        r.slots(rows,lambda row:row['source'],side,issues)
        for position,row in rows.values():r.item_unit(row,r.reference(row,'stock',stocks,side,position,issues),side,position,issues)
    qualified=not issues;assessment=None
    if qualified:
        incoming=defaultdict(int);reserved=defaultdict(int);inbound_report=[];reservation_report=[]
        for key,(position,row) in sorted(inbound.items()):
            eligible=row['state']=='usable' and v['as_of']<=row['due_at']<=v['horizon'];reason='included' if eligible else row['state'] if row['state']!='usable' else 'overdue' if row['due_at']<v['as_of'] else 'beyond_horizon'
            if row['state']!='cancelled' and row['due_at']<v['as_of']:c.issue(issues,'inbound',position,'INBOUND_OVERDUE')
            if eligible:incoming[row['stock']]+=row['quantity']
            inbound_report.append(dict(id=key,included=eligible,reason=reason))
        for key,(_,row) in sorted(reservations.items()):
            included=row['state']=='reserved'
            if included:reserved[row['stock']]+=row['quantity']
            reservation_report.append(dict(id=key,included=included,reason='reserved' if included else 'released'))
        out=[]
        for key,(position,stock) in sorted(stocks.items()):
            current=stock['at']==v['as_of'];value=stock['on_hand']+incoming[key]-reserved[key] if current else None
            if not current:c.issue(issues,'stocks',position,'STOCK_SNAPSHOT_AS_OF_MISMATCH')
            if value is not None and value<0:c.issue(issues,'stocks',position,'POSITION_NEGATIVE')
            out.append(dict(id=key,item=stock['item'],unit=stock['unit'],on_hand=stock['on_hand'],eligible_inbound=incoming[key],reserved_demand=reserved[key],snapshot_current=current,inventory_position=value))
        assessment=dict(stocks=out,inbound=inbound_report,reservations=reservation_report)
    return r.output(raw,'outlands-inventory-position-report-v1',counts,issues,qualified,assessment,dict(stocks=stocks,inbound=inbound,reservations=reservations),dict(as_of=v['as_of'],horizon=v['horizon']))

def main(argv=None):return c.cli('Calculate declared stock positions; no inventory access or reservations.',check,argv)
if __name__=='__main__':raise SystemExit(main())
