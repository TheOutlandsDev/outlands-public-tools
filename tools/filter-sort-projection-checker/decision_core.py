"""Bounded explicit identities, normalized contracts and exact arithmetic."""
from collections import defaultdict
from fractions import Fraction
import re
import toolkit as t

def issue(issues,side,row,code):issues.append(dict(side=side,row=row,code=code))

def rows(value,parser,side):
    t.require(type(value) is list and len(value)<=1000,'ROW_LIMIT')
    groups=defaultdict(list);issues=[];rejected=0
    for position,row in enumerate(value,1):
        try:
            key,normalized=parser(row);groups[key].append((position,normalized))
        except t.Rejected as error:rejected+=1;issue(issues,side,position,str(error))
    accepted={};duplicates=conflicts=0
    for key,members in groups.items():
        if len({t.encode(row) for _,row in members})>1:
            conflicts+=len(members)
            for position,_ in members:issue(issues,side,position,'IDENTITY_CONFLICT')
        else:accepted[key]=members[0];duplicates+=len(members)-1
    counts=dict(input_rows=len(value),accepted_records=len(accepted),duplicate_rows=duplicates,conflict_rows=conflicts,rejected_rows=rejected)
    t.require(len(value)==len(accepted)+duplicates+conflicts+rejected,'ACCOUNTING_FAILED')
    return accepted,counts,issues

def record(row,fields,ids=(),revisions=()):
    t.fields(row,fields)
    for key in ids:t.identifier(row[key])
    for key in revisions:t.integer(row[key],10**6,1)
    return row['id'],dict(row)

def tags(value,minimum=0):
    t.require(type(value) is list and minimum<=len(value)<=32,'LABEL_OR_TAG_LIMIT')
    for item in value:t.identifier(item)
    t.require(len(set(value))==len(value),'DUPLICATE_LABEL_OR_TAG');return sorted(value)

def taxonomy(value):
    _,out=record(value,{'id','revision','labels'},('id',),('revision',));out['labels']=tags(value['labels'],1);return out

def decimal(value):
    t.require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?',value),'DECIMAL_INVALID')
    exact=Fraction(value);t.require(0<=exact<=1,'UNIT_INTERVAL_REQUIRED')
    text=value.rstrip('0').rstrip('.') if '.' in value else value
    return exact,'0' if exact==0 else text

def decimal_text(value):
    scaled=value*10**6;t.require(scaled.denominator==1,'DECIMAL_RENDER_INVALID')
    sign='-' if scaled<0 else '';whole,part=divmod(abs(scaled.numerator),10**6)
    return sign+str(whole)+('.'+str(part).zfill(6).rstrip('0') if part else '')

def ratio(numerator,denominator):
    t.require(type(numerator) is int and type(denominator) is int and denominator>0 and abs(numerator)<=denominator,'RATIO_INVALID')
    exact=Fraction(numerator,denominator)
    return dict(numerator=numerator,denominator=denominator,exact_fraction=str(exact.numerator)+'/'+str(exact.denominator))

def pin(value):return t.digest(t.encode(value))
def cohort_pin(records):return pin([records[k][1] for k in sorted(records)])

def policy(value):
    _,out=record(value,{'id','revision','labels','minimum_score','minimum_margin','tie_policy'},('id',),('revision',))
    out['labels']=tags(value['labels'],2)
    for key in ('minimum_score','minimum_margin'):_,out[key]=decimal(value[key])
    t.require(value['tie_policy'] in ('abstain','lexical'),'TIE_POLICY_INVALID');return out

def base(raw,fmt,counts,issues):
    return dict(format=fmt,status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=t.digest(raw),counts=counts,
        issues=sorted(issues,key=lambda i:(i['side'],i['row'],i['code'])),declarations_independently_verified=False,
        content_privacy_verified=False,execution_authorized=False,target_changes_performed=False)

def cli(description,operation,argv=None):
    parser=t.Parser(description=description);parser.add_argument('--input',required=True);parser.add_argument('--out')
    return t.run(parser,lambda a:operation(t.read(a.input)),argv)
