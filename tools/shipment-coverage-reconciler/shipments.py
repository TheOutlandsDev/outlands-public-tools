"""Reconcile declared order-line, shipment-content and receipt quantities; never ship."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import stock_core as r

def order(row):
    key,out=c.record(row,{'id','revision','item','unit','quantity'},('id','item','unit'),('revision',));t.integer(row['quantity'],10**12,1);return key,out

def shipment(row):return c.record(row,{'id','revision'},('id',),('revision',))

def line(row):
    key,out=c.record(row,{'id','shipment','shipment_revision','shipment_sha256','order','order_revision','order_sha256','item','unit','quantity'},('id','shipment','order','item','unit'),('shipment_revision','order_revision'))
    t.sha(row['shipment_sha256']);t.sha(row['order_sha256']);t.integer(row['quantity'],10**12,1);return key,out

def receipt(row):
    key,out=c.record(row,{'id','line','line_sha256','quantity'},('id','line'));t.sha(row['line_sha256']);t.integer(row['quantity'],10**12,1);return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','orders','shipments','lines','receipts'});t.require(v['format']=='outlands-shipment-coverage-v1','FORMAT_INVALID')
    counts={};issues=[];orders=r.collect(v['orders'],order,'orders',counts,issues);shipments=r.collect(v['shipments'],shipment,'shipments',counts,issues,False)
    lines=r.collect(v['lines'],line,'lines',counts,issues,False);receipts=r.collect(v['receipts'],receipt,'receipts',counts,issues,False)
    r.slots(lines,lambda row:(row['shipment'],row['order']),'lines',issues);r.slots(receipts,lambda row:row['line'],'receipts',issues)
    for number,row in lines.values():
        r.reference(row,'shipment',shipments,'lines',number,issues);r.item_unit(row,r.reference(row,'order',orders,'lines',number,issues),'lines',number,issues)
    for number,row in receipts.values():
        target=lines.get(row['line'])
        if target is None:c.issue(issues,'receipts',number,'LINE_UNKNOWN')
        elif row['line_sha256']!=c.pin(target[1]):c.issue(issues,'receipts',number,'LINE_SNAPSHOT_MISMATCH')
    qualified=not issues;assessment=None
    if qualified:
        by_line={row['line']:row for _,row in receipts.values()};dispatched=defaultdict(int);received=defaultdict(int);shipment_orders=defaultdict(list);line_report=[]
        for key,(number,row) in sorted(lines.items()):
            selected=by_line.get(key);quantity=selected['quantity'] if selected else 0;codes=[]
            if selected is None:codes.append('RECEIPT_MISSING')
            elif quantity<row['quantity']:codes.append('RECEIPT_SHORTFALL')
            elif quantity>row['quantity']:codes.append('RECEIPT_EXCEEDS_DISPATCH')
            for code in codes:c.issue(issues,'lines',number,code)
            dispatched[row['order']]+=row['quantity'];received[row['order']]+=quantity;shipment_orders[row['shipment']].append(row['order'])
            line_report.append(dict(id=key,receipt_id=selected['id'] if selected else None,dispatched_quantity=row['quantity'],declared_received_quantity=quantity,declared_unreceived=row['quantity']-quantity,failed_criteria=codes))
        order_report=[]
        for key,(number,row) in sorted(orders.items()):
            shortage=max(0,row['quantity']-dispatched[key]);excess=max(0,dispatched[key]-row['quantity']);receipt_shortage=max(0,row['quantity']-received[key]);receipt_excess=max(0,received[key]-row['quantity'])
            for code,amount in [('ORDER_UNSHIPPED',shortage),('ORDER_OVERSHIPPED',excess),('ORDER_RECEIPT_SHORTAGE',receipt_shortage),('ORDER_RECEIPT_EXCESS',receipt_excess)]:
                if amount:c.issue(issues,'orders',number,code)
            order_report.append(dict(id=key,item=row['item'],unit=row['unit'],required_quantity=row['quantity'],dispatched_quantity=dispatched[key],declared_received_quantity=received[key],unshipped=shortage,over_shipped=excess,receipt_shortage=receipt_shortage,receipt_excess=receipt_excess))
        shipment_report=[]
        for key,(number,row) in sorted(shipments.items()):
            if not shipment_orders[key]:c.issue(issues,'shipments',number,'SHIPMENT_CONTENT_MISSING')
            shipment_report.append(dict(id=key,order_ids=sorted(shipment_orders[key]),line_count=len(shipment_orders[key])))
        assessment=dict(orders=order_report,shipments=shipment_report,lines=line_report)
    return r.output(raw,'outlands-shipment-coverage-report-v1',counts,issues,qualified,assessment,dict(orders=orders,shipments=shipments,lines=lines,receipts=receipts))

def main(argv=None):return c.cli('Reconcile declared shipment coverage; no stock, shipment or delivery actions.',check,argv)
if __name__=='__main__':raise SystemExit(main())
