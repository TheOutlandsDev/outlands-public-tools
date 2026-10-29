"""Explicit identity accounting, bounded graphs and declared lot resolution."""
from collections import defaultdict
import heapq
import toolkit as t

def problem(issues,side,row,code): issues.append(dict(side=side,row=row,code=code))

def rows(value,parser,side):
    t.require(type(value) is list and len(value)<=1000,'ROW_LIMIT')
    groups=defaultdict(list);issues=[];rejected=0
    for index,row in enumerate(value,1):
        try:
            key,record=parser(row);groups[key].append((index,record))
        except t.Rejected as error:
            rejected+=1;problem(issues,side,index,str(error))
    accepted={};duplicates=conflicts=0
    for key,entries in groups.items():
        if len({t.encode(record) for _,record in entries})!=1:
            conflicts+=len(entries)
            for index,_ in entries:problem(issues,side,index,'IDENTITY_CONFLICT')
        else:accepted[key]=entries[0];duplicates+=len(entries)-1
    counts=dict(input_rows=len(value),accepted_records=len(accepted),duplicate_rows=duplicates,
                conflict_rows=conflicts,rejected_rows=rejected)
    t.require(sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows'))==len(value),'ACCOUNTING_FAILED')
    return accepted,counts,issues

def record(row,names,ids=(),amounts=()):
    t.fields(row,names)
    for name in ids:t.identifier(row[name])
    for name,minimum,maximum in amounts:t.integer(row[name],maximum,minimum)
    return row['id'],dict(row)

def lot(row):return record(row,{'id','item_id','unit','quantity'},('id','item_id','unit'),(('quantity',0,10**12),))
def alias(row):return record(row,{'id','target_id'},('id','target_id'))

def resolve(lots,aliases,issues):
    """All-or-none resolution; aliases never create stock or select a latest row."""
    if not lots:problem(issues,'lots',0,'EMPTY_LOT_COHORT')
    for key in sorted(set(lots)&set(aliases)):
        problem(issues,'aliases',aliases[key][0],'LOT_ALIAS_COLLISION')
    units={}
    for index,row in lots.values():
        prior=units.setdefault(row['item_id'],row['unit'])
        if prior!=row['unit']:problem(issues,'lots',index,'ITEM_UNIT_CONFLICT')
    for index,row in aliases.values():
        if row['target_id'] not in lots and row['target_id'] not in aliases:
            problem(issues,'aliases',index,'ALIAS_TARGET_MISSING')
    if issues:return None
    resolved={key:key for key in lots}
    for key in sorted(aliases):
        chain=[];seen=set();current=key
        while current not in resolved:
            if current in seen:
                problem(issues,'aliases',aliases[current][0],'ALIAS_CYCLE');break
            seen.add(current);chain.append(current);current=aliases[current][1]['target_id']
        else:
            target=resolved[current]
            for member in chain:resolved[member]=target
    return None if issues else resolved

def lot_pin(lots,aliases):
    return t.digest(t.encode(dict(lots=[lots[k][1] for k in sorted(lots)],aliases=[aliases[k][1] for k in sorted(aliases)])))

def topology(nodes,edges):
    """Iterative stable Kahn traversal. Edges are explicit parent-to-child pairs."""
    outgoing={key:[] for key in nodes};incoming={key:0 for key in nodes}
    for parent,child in edges:outgoing[parent].append(child);incoming[child]+=1
    ready=[key for key,count in incoming.items() if count==0];heapq.heapify(ready);order=[]
    while ready:
        key=heapq.heappop(ready);order.append(key)
        for child in sorted(outgoing[key]):
            incoming[child]-=1
            if incoming[child]==0:heapq.heappush(ready,child)
    return order if len(order)==len(nodes) else None

def base(raw,fmt,counts,issues):
    return dict(format=fmt,status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=t.digest(raw),counts=counts,
                issues=sorted(issues,key=lambda i:(i['side'],i['row'],i['code'])),
                declarations_independently_verified=False,content_privacy_verified=False,
                execution_authorized=False,target_changes_performed=False)

def cli(description,operation,argv=None):
    parser=t.Parser(description=description);parser.add_argument('--input',required=True);parser.add_argument('--out')
    return t.run(parser,lambda a:operation(t.read(a.input)),argv)
