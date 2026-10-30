"""Bounded identity snapshots, exact decimal declarations and private reports."""
from collections import defaultdict
from fractions import Fraction
import re
import toolkit as t

def issue(issues,side,row,code):issues.append(dict(side=side,row=row,code=code))

def rows(value,parser,side):
    t.require(type(value) is list and len(value)<=1000,'ROW_LIMIT')
    groups=defaultdict(list);issues=[];rejected=0
    for index,row in enumerate(value,1):
        try:
            key,normalized=parser(row);groups[key].append((index,normalized))
        except t.Rejected as error:
            rejected+=1;issue(issues,side,index,str(error))
    accepted={};duplicates=conflicts=0
    for key,entries in groups.items():
        if len({t.encode(record) for _,record in entries})>1:
            conflicts+=len(entries)
            for index,_ in entries:issue(issues,side,index,'IDENTITY_CONFLICT')
        else:accepted[key]=entries[0];duplicates+=len(entries)-1
    counts=dict(input_rows=len(value),accepted_records=len(accepted),duplicate_rows=duplicates,conflict_rows=conflicts,rejected_rows=rejected)
    t.require(len(value)==len(accepted)+duplicates+conflicts+rejected,'ACCOUNTING_FAILED')
    return accepted,counts,issues

def record(row,fields,ids=(),integers=()):
    t.fields(row,fields)
    for key in ids:t.identifier(row[key])
    for key,minimum,maximum in integers:t.integer(row[key],maximum,minimum)
    return row['id'],dict(row)

def entity(row):return record(row,{'id'},('id',))

def decimal(value):
    t.require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?',value),'DECIMAL_INVALID')
    exact=Fraction(value);t.require(abs(exact)<=10**12,'DECIMAL_LIMIT')
    canonical=value.rstrip('0').rstrip('.') if '.' in value else value
    if exact==0:canonical='0'
    return exact,canonical

def rule(row):
    key,out=record(row,{'id','revision','unit','minimum','maximum','minimum_inclusive','maximum_inclusive'},('id','unit'),(('revision',1,10**6),))
    for field in ('minimum_inclusive','maximum_inclusive'):t.require(type(row[field]) is bool,'BOUND_FLAG_INVALID')
    low,out['minimum']=decimal(row['minimum']);high,out['maximum']=decimal(row['maximum'])
    t.require(low<high or (low==high and row['minimum_inclusive'] and row['maximum_inclusive']),'EMPTY_LIMIT_INTERVAL')
    return key,out

def pin(records):return t.digest(t.encode([records[key][1] for key in sorted(records)]))

def unique_pairs(records,fields,side,issues,code):
    groups=defaultdict(list)
    for index,row in records.values():groups[tuple(row[key] for key in fields)].append(index)
    for indices in groups.values():
        if len(indices)>1:
            for index in indices:issue(issues,side,index,code)

def ratio(numerator,denominator):
    t.require(type(numerator) is int and type(denominator) is int and 0<=numerator<=denominator and denominator>0,'RATIO_INVALID')
    value=Fraction(numerator,denominator)
    return dict(numerator=numerator,denominator=denominator,exact_fraction=str(value.numerator)+'/'+str(value.denominator))

def base(raw,fmt,counts,issues):
    return dict(format=fmt,status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=t.digest(raw),counts=counts,
        issues=sorted(issues,key=lambda i:(i['side'],i['row'],i['code'])),
        declarations_independently_verified=False,content_privacy_verified=False,execution_authorized=False,target_changes_performed=False)

def cli(description,operation,argv=None):
    parser=t.Parser(description=description);parser.add_argument('--input',required=True);parser.add_argument('--out')
    return t.run(parser,lambda a:operation(t.read(a.input)),argv)
