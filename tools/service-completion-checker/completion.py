"""Reconcile supplied completion requirements against exact selected order snapshots."""
import toolkit as t
import service_core as c

def contract(row):
    key,out=c.record(row,{'id','order_id','order_revision','order_sha256','required_tasks','required_evidence','expected_parts'},('id','order_id'),(('order_revision',1,1000),))
    t.sha(row['order_sha256']);out['required_tasks']=c.tags(row['required_tasks']);out['required_evidence']=c.tags(row['required_evidence'])
    t.require(type(row['expected_parts']) is list and len(row['expected_parts'])<=32,'PART_REQUIREMENT_LIMIT')
    parts=[];seen=set()
    for part in row['expected_parts']:
        t.fields(part,{'item_id','unit','installed_quantity'});t.identifier(part['item_id']);t.identifier(part['unit']);t.integer(part['installed_quantity'],10**12)
        t.require(part['item_id'] not in seen,'PART_REQUIREMENT_DUPLICATE');seen.add(part['item_id']);parts.append(dict(part))
    out['expected_parts']=sorted(parts,key=lambda p:p['item_id']);return key,out
def task(row):
    key,out=c.record(row,{'id','order_id','order_revision','task_id','outcome'},('id','order_id','task_id'),(('order_revision',1,1000),))
    t.require(row['outcome'] in ('done','blocked','not_done'),'TASK_OUTCOME_INVALID');return key,out
def part(row):return c.record(row,{'id','order_id','order_revision','item_id','unit','issued','installed','returned','scrapped'},('id','order_id','item_id','unit'),(('order_revision',1,1000),('issued',0,10**12),('installed',0,10**12),('returned',0,10**12),('scrapped',0,10**12)))
def evidence(row):
    key,out=c.record(row,{'id','order_id','order_revision','kind','sha256'},('id','order_id','kind'),(('order_revision',1,1000),))
    t.sha(row['sha256']);return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','orders','contracts','tasks','parts','evidence'})
    t.require(value['format']=='outlands-service-completion-v1','FORMAT_INVALID')
    orders,oc,issues=c.rows(value['orders'],c.order,'orders');counts=dict(orders=oc);tables={}
    for name,parser in [('contracts',contract),('tasks',task),('parts',part),('evidence',evidence)]:
        records,counts[name],other=c.rows(value[name],parser,name);issues+=other;tables[name]=records
    if not orders:c.issue(issues,'orders',0,'EMPTY_ORDER_COHORT')
    c.unique(tables['contracts'],('order_id',),'contracts',issues,'MULTIPLE_ORDER_CONTRACTS')
    for name,field in [('tasks','task_id'),('parts','item_id'),('evidence','kind')]:c.unique(tables[name],('order_id',field),name,issues,'MULTIPLE_REQUIREMENT_RECORDS')
    by_order={row['order_id']:row for _,row in tables['contracts'].values()}
    for key,(index,_) in orders.items():
        if key not in by_order:c.issue(issues,'orders',index,'ORDER_CONTRACT_MISSING')
    t.require(sum(len(r['required_tasks'])+len(r['required_evidence'])+len(r['expected_parts']) for _,r in tables['contracts'].values())<=10000,'COMPLETION_REQUIREMENT_LIMIT')
    for name,records in tables.items():
        for index,row in records.values():
            if row['order_id'] not in orders:c.issue(issues,name,index,'ORDER_MISSING');continue
            selected=orders[row['order_id']][1]
            if row['order_revision']!=selected['revision']:c.issue(issues,name,index,'ORDER_REVISION_MISMATCH')
            expected=by_order.get(row['order_id'])
            if name=='contracts':
                if row['order_sha256']!=c.order_pin(selected):c.issue(issues,name,index,'ORDER_PIN_MISMATCH')
            elif expected is not None:
                allowed=expected['required_tasks'] if name=='tasks' else expected['required_evidence'] if name=='evidence' else {p['item_id']:p for p in expected['expected_parts']}
                field='task_id' if name=='tasks' else 'kind' if name=='evidence' else 'item_id'
                if row[field] not in allowed:c.issue(issues,name,index,'REQUIREMENT_NOT_DECLARED')
                elif name=='parts' and row['unit']!=allowed[row['item_id']]['unit']:c.issue(issues,name,index,'PART_UNIT_MISMATCH')
    assessments=None
    if not issues:
        selected={name:{(r['order_id'],r[field]):r for _,r in tables[name].values()} for name,field in [('tasks','task_id'),('parts','item_id'),('evidence','kind')]}
        assessments=[]
        for key,(index,order) in sorted(orders.items()):
            expected=by_order[key];reasons=[];missing_tasks=[];unfinished=[];missing_evidence=[];missing_parts=[];part_findings=[]
            if order['state']!='completed':reasons.append('ORDER_NOT_COMPLETED')
            for tag in expected['required_tasks']:
                entry=selected['tasks'].get((key,tag))
                if entry is None:missing_tasks.append(tag)
                elif entry['outcome']!='done':unfinished.append(tag)
            for tag in expected['required_evidence']:
                if (key,tag) not in selected['evidence']:missing_evidence.append(tag)
            for requirement in expected['expected_parts']:
                entry=selected['parts'].get((key,requirement['item_id']))
                if entry is None:missing_parts.append(requirement['item_id']);continue
                if entry['issued']!=entry['installed']+entry['returned']+entry['scrapped']:part_findings.append(dict(item_id=entry['item_id'],code='PARTS_NOT_BALANCED'))
                if entry['installed']!=requirement['installed_quantity']:part_findings.append(dict(item_id=entry['item_id'],code='INSTALLED_QUANTITY_MISMATCH'))
            for condition,code in [(missing_tasks,'TASKS_MISSING'),(unfinished,'TASKS_UNFINISHED'),(missing_evidence,'EVIDENCE_MISSING'),(missing_parts,'PART_RECORDS_MISSING'),(part_findings,'PART_ACCOUNTING_REQUIRES_REVIEW')]:
                if condition:reasons.append(code)
            if reasons:c.issue(issues,'orders',index,'SERVICE_COMPLETION_REQUIRES_REVIEW')
            assessments.append(dict(id=key,order_revision=order['revision'],order_sha256=c.order_pin(order),completed_under_contract=not reasons,
                missing_tasks=missing_tasks,unfinished_tasks=unfinished,missing_evidence=missing_evidence,missing_parts=missing_parts,parts_findings=part_findings,reasons=reasons))
    result=c.base(raw,'outlands-service-completion-review-v1',counts,issues)
    result.update(assessments=assessments,lifecycle_recomputed=False,evidence_bytes_verified=False,physical_service_verified=False,stock_or_orders_changed=False)
    return result

def main(argv=None):return c.cli('Review supplied completion contracts; no service approval or operational updates.',check,argv)
if __name__=='__main__':raise SystemExit(main())
