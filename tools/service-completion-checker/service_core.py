"""Bounded snapshots, explicit identities and normalized order pins."""
from collections import defaultdict
import toolkit as t

def issue(issues,side,row,code):issues.append(dict(side=side,row=row,code=code))

def rows(value,parser,side):
    t.require(type(value) is list and len(value)<=1000,'ROW_LIMIT')
    grouped=defaultdict(list);issues=[];rejected=0
    for position,row in enumerate(value,1):
        try:
            key,normalized=parser(row);grouped[key].append((position,normalized))
        except t.Rejected as error:
            rejected+=1;issue(issues,side,position,str(error))
    accepted={};duplicates=conflicts=0
    for key,members in grouped.items():
        if len({t.encode(row) for _,row in members})>1:
            conflicts+=len(members)
            for position,_ in members:issue(issues,side,position,'IDENTITY_CONFLICT')
        else:accepted[key]=members[0];duplicates+=len(members)-1
    counts=dict(input_rows=len(value),accepted_records=len(accepted),duplicate_rows=duplicates,conflict_rows=conflicts,rejected_rows=rejected)
    t.require(len(value)==len(accepted)+duplicates+conflicts+rejected,'ACCOUNTING_FAILED')
    return accepted,counts,issues

def record(row,fields,ids=(),integers=()):
    t.fields(row,fields)
    for key in ids:t.identifier(row[key])
    for key,minimum,maximum in integers:t.integer(row[key],maximum,minimum)
    return row['id'],dict(row)

def tags(value):
    t.require(type(value) is list and len(value)<=32,'TAG_LIMIT')
    for item in value:t.identifier(item)
    t.require(len(set(value))==len(value),'DUPLICATE_TAG');return sorted(value)

def unique(records,fields,side,issues,code):
    groups=defaultdict(list)
    for position,row in records.values():groups[tuple(row[k] for k in fields)].append(position)
    for positions in groups.values():
        if len(positions)>1:
            for position in positions:issue(issues,side,position,code)

def order(row):
    key,out=record(row,{'id','asset_id','revision','state'},('id','asset_id'),(('revision',1,1000),))
    t.require(row['state'] in ('open','in_progress','on_hold','completed','cancelled'),'ORDER_STATE_INVALID')
    return key,out

def order_pin(row):return t.digest(t.encode(order(row)[1]))

def base(raw,fmt,counts,issues):
    return dict(format=fmt,status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=t.digest(raw),counts=counts,
        issues=sorted(issues,key=lambda i:(i['side'],i['row'],i['code'])),
        declarations_independently_verified=False,content_privacy_verified=False,execution_authorized=False,target_changes_performed=False)

def cli(description,operation,argv=None):
    parser=t.Parser(description=description);parser.add_argument('--input',required=True);parser.add_argument('--out')
    return t.run(parser,lambda a:operation(t.read(a.input)),argv)
