"""Check an explicit component DAG and calculate bounded whole-unit requirements."""
from collections import defaultdict
import toolkit as t
import material_core as c

def component(row):return c.record(row,{'id','unit'},('id','unit'))
def link(row):return c.record(row,{'id','parent_id','component_id','quantity'},('id','parent_id','component_id'),(('quantity',1,10**6),))
def order(row):return c.record(row,{'id','component_id','quantity'},('id','component_id'),(('quantity',1,10**9),))

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','components','links','orders'})
    t.require(value['format']=='outlands-bom-contract-v1','FORMAT_INVALID')
    components,cc,issues=c.rows(value['components'],component,'components')
    links,lc,other=c.rows(value['links'],link,'links');issues+=other
    orders,oc,other=c.rows(value['orders'],order,'orders');issues+=other
    if not components:c.problem(issues,'components',0,'EMPTY_COMPONENT_COHORT')
    if not orders:c.problem(issues,'orders',0,'EMPTY_ORDER_COHORT')
    pairs=defaultdict(list)
    for index,row in links.values():
        pairs[(row['parent_id'],row['component_id'])].append(index)
        for endpoint in (row['parent_id'],row['component_id']):
            if endpoint not in components:c.problem(issues,'links',index,'COMPONENT_MISSING')
    for indices in pairs.values():
        if len(indices)>1:
            for index in indices:c.problem(issues,'links',index,'PARALLEL_COMPONENT_EDGE')
    for index,row in orders.values():
        if row['component_id'] not in components:c.problem(issues,'orders',index,'COMPONENT_MISSING')
    ordered=None;requirements=None
    if not issues:
        ordered=c.topology(components,pairs)
        if ordered is None:c.problem(issues,'links',0,'COMPONENT_CYCLE')
    if not issues:
        children=defaultdict(list);needed={key:0 for key in components}
        for _,row in orders.values():needed[row['component_id']]+=row['quantity']
        for _,row in links.values():children[row['parent_id']].append(row)
        for key in ordered:
            t.require(needed[key]<=10**18,'REQUIREMENT_LIMIT')
            for row in children[key]:
                child=row['component_id'];needed[child]+=needed[key]*row['quantity']
                t.require(needed[child]<=10**18,'REQUIREMENT_LIMIT')
        requirements=[dict(component_id=key,unit=components[key][1]['unit'],quantity=needed[key],is_leaf=not children[key])
                      for key in sorted(components) if needed[key]]
    result=c.base(raw,'outlands-bom-review-v1',dict(components=cc,links=lc,orders=oc),issues)
    result.update(requirements=requirements,topological_order=ordered if not issues else None,
                  inventory_availability_checked=False,engineering_suitability_verified=False,orders_created=False)
    return result

def main(argv=None):return c.cli('Check supplied component declarations; no equipment sizing or orders.',check,argv)
if __name__=='__main__':raise SystemExit(main())
