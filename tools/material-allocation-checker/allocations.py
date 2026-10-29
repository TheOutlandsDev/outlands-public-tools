"""Reconcile declared demand and reservations against canonical lot quantities."""
import toolkit as t
import material_core as c

def demand(row):return c.record(row,{'id','item_id','unit','quantity'},('id','item_id','unit'),(('quantity',1,10**12),))
def allocation(row):return c.record(row,{'id','demand_id','lot_id','quantity'},('id','demand_id','lot_id'),(('quantity',1,10**12),))

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','lots','aliases','demands','allocations'})
    t.require(value['format']=='outlands-material-allocations-v1','FORMAT_INVALID')
    lots,lc,issues=c.rows(value['lots'],c.lot,'lots');aliases,ac,other=c.rows(value['aliases'],c.alias,'aliases');issues+=other
    resolved=c.resolve(lots,aliases,issues);inventory_valid=resolved is not None
    demands,dc,other=c.rows(value['demands'],demand,'demands');issues+=other
    allocations,rc,other=c.rows(value['allocations'],allocation,'allocations');issues+=other
    if not demands:c.problem(issues,'demands',0,'EMPTY_DEMAND_COHORT')
    for index,row in allocations.values():
        if row['demand_id'] not in demands:c.problem(issues,'allocations',index,'DEMAND_MISSING')
        if resolved is not None:
            if row['lot_id'] not in resolved:c.problem(issues,'allocations',index,'LOT_MISSING')
            elif row['demand_id'] in demands:
                source=lots[resolved[row['lot_id']]][1];target=demands[row['demand_id']][1]
                if (source['item_id'],source['unit'])!=(target['item_id'],target['unit']):c.problem(issues,'allocations',index,'ITEM_OR_UNIT_MISMATCH')
    demand_summary=lot_summary=None
    if not issues:
        consumed={key:0 for key in lots};assigned={key:0 for key in demands}
        for _,row in allocations.values():consumed[resolved[row['lot_id']]]+=row['quantity'];assigned[row['demand_id']]+=row['quantity']
        demand_summary=[];lot_summary=[]
        for key,(index,row) in sorted(demands.items()):
            shortage=max(0,row['quantity']-assigned[key]);excess=max(0,assigned[key]-row['quantity'])
            if shortage:c.problem(issues,'demands',index,'DEMAND_SHORTAGE')
            if excess:c.problem(issues,'demands',index,'DEMAND_OVERALLOCATED')
            demand_summary.append(dict(id=key,item_id=row['item_id'],unit=row['unit'],required=row['quantity'],allocated=assigned[key],shortage=shortage,excess=excess))
        for key,(index,row) in sorted(lots.items()):
            excess=max(0,consumed[key]-row['quantity'])
            if excess:c.problem(issues,'lots',index,'LOT_OVERRESERVED')
            lot_summary.append(dict(id=key,item_id=row['item_id'],unit=row['unit'],available=row['quantity'],reserved=consumed[key],unreserved=row['quantity']-consumed[key],excess=excess))
    result=c.base(raw,'outlands-material-allocation-review-v1',dict(lots=lc,aliases=ac,demands=dc,allocations=rc),issues)
    result.update(demands=demand_summary,lots=lot_summary,lot_contract_sha256=c.lot_pin(lots,aliases) if inventory_valid else None,
                  allocation_policy_selected=False,reservations_changed=False,physical_stock_verified=False)
    return result

def main(argv=None):return c.cli('Check explicit material reservations; no stock updates or allocation selection.',check,argv)
if __name__=='__main__':raise SystemExit(main())
