"""Replay supplied opening/movement declarations at an explicit ordinal without stock updates."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import stock_core as r

def movement(row):
    key,out=c.record(row,{'id','stock','stock_revision','stock_sha256','ordinal','at','kind','quantity'},('id','stock'),('stock_revision',))
    t.sha(row['stock_sha256']);t.integer(row['ordinal'],1000,1);t.integer(row['at']);t.require(row['kind'] in ('receipt','issue','adjustment'),'KIND_INVALID')
    t.integer(row['quantity'],10**12,-10**12 if row['kind']=='adjustment' else 1);t.require(row['quantity']!=0,'ZERO_ADJUSTMENT_INVALID');return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','stocks','movements','as_of'});t.require(v['format']=='outlands-stock-movements-v1','FORMAT_INVALID');t.integer(v['as_of'])
    counts={};issues=[];stocks=r.collect(v['stocks'],r.stock,'stocks',counts,issues);movements=r.collect(v['movements'],movement,'movements',counts,issues,False)
    r.slots(movements,lambda row:(row['stock'],row['ordinal']),'movements',issues);grouped=defaultdict(list)
    for position,row in movements.values():
        stock=r.reference(row,'stock',stocks,'movements',position,issues)
        if stock and row['at']<stock['at']:c.issue(issues,'movements',position,'MOVEMENT_BEFORE_OPENING')
        grouped[row['stock']].append((position,row))
    for key in stocks:
        previous=None
        for expected,(position,row) in enumerate(sorted(grouped[key],key=lambda pair:pair[1]['ordinal']),1):
            if row['ordinal']!=expected:c.issue(issues,'movements',position,'ORDINAL_GAP')
            if previous is not None and row['at']<previous:c.issue(issues,'movements',position,'TIME_REVERSED')
            previous=row['at']
    qualified=not issues;assessment=None
    if qualified:
        out=[]
        for key,(position,stock) in sorted(stocks.items()):
            current=stock['at']<=v['as_of'];balance=stock['on_hand'] if current else None;history=[]
            if not current:c.issue(issues,'stocks',position,'OPENING_SNAPSHOT_FUTURE')
            for number,row in sorted(grouped[key],key=lambda pair:pair[1]['ordinal']):
                applied=current and row['at']<=v['as_of'];delta=-row['quantity'] if row['kind']=='issue' else row['quantity']
                if row['at']>v['as_of']:c.issue(issues,'movements',number,'MOVEMENT_AFTER_AS_OF')
                if applied:
                    balance+=delta
                    if balance<0:c.issue(issues,'movements',number,'NEGATIVE_DECLARED_BALANCE')
                history.append(dict(id=row['id'],ordinal=row['ordinal'],delta=delta,applied=applied,balance_after=balance if applied else None))
            out.append(dict(id=key,item=stock['item'],unit=stock['unit'],opening_quantity=stock['on_hand'],closing_quantity=balance,history=history))
        assessment=dict(stocks=out)
    return r.output(raw,'outlands-stock-movements-report-v1',counts,issues,qualified,assessment,dict(stocks=stocks,movements=movements),dict(as_of=v['as_of']))

def main(argv=None):return c.cli('Check declared stock movement histories; no stock updates.',check,argv)
if __name__=='__main__':raise SystemExit(main())
