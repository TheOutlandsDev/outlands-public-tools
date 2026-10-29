"""Bounded ordinals, exact observation pins and explicit revision availability."""
from collections import defaultdict
from decimal import Decimal
import re
import toolkit as t


def ordinal(value): return t.integer(value,10**9)


def decimal(value):
    t.require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?',value),'DECIMAL_INVALID')
    parsed=Decimal(value); t.require(parsed.copy_abs()<=10**12,'DECIMAL_LIMIT')
    result=format(parsed,'f')
    if '.' in result: result=result.rstrip('0').rstrip('.')
    return '0' if parsed==0 else result


def problem(issues,side,row,code,**metadata): issues.append(dict(side=side,row=row,code=code,**metadata))


def rows(value,parser,side,duplicate_code=None):
    t.require(type(value) is list and len(value)<=1000,'ROW_LIMIT')
    groups=defaultdict(list); issues=[]; rejected=0
    for index,row in enumerate(value,1):
        try:
            key,normalized=parser(row); groups[key].append((index,normalized))
        except t.Rejected as error:
            rejected+=1; problem(issues,side,index,str(error))
    accepted={}; duplicates=conflicts=0
    for key,entries in groups.items():
        if len({t.encode(record) for _,record in entries})!=1:
            conflicts+=len(entries)
            for index,_ in entries: problem(issues,side,index,'IDENTITY_CONFLICT')
        else:
            accepted[key]=entries[0]; duplicates+=len(entries)-1
            if duplicate_code:
                for index,_ in entries[1:]: problem(issues,side,index,duplicate_code)
    counts=dict(input_rows=len(value),accepted_records=len(accepted),duplicate_rows=duplicates,
                conflict_rows=conflicts,rejected_rows=rejected)
    t.require(len(value)==len(accepted)+duplicates+conflicts+rejected,'ACCOUNTING_FAILED')
    return accepted,counts,issues


def grid(value):
    t.fields(value,{'start','end','step'})
    start=ordinal(value['start']); end=ordinal(value['end']); step=t.integer(value['step'],10**6,1)
    t.require(end>=start and (end-start)%step==0,'GRID_INVALID')
    count=(end-start)//step+1; t.require(count<=1000,'GRID_POINT_LIMIT')
    return dict(start=start,end=end,step=step),count


def observation(row):
    t.fields(row,{'id','series','period','revision','available_at','value','sha256'})
    t.identifier(row['id']); t.identifier(row['series']); ordinal(row['period']); ordinal(row['available_at'])
    t.integer(row['revision'],10**6,1); t.require(row['available_at']>=row['period'],'AVAILABILITY_BEFORE_PERIOD')
    payload={key:row[key] for key in ('id','series','period','revision','available_at')}
    payload['value']=decimal(row['value']); t.sha(row['sha256'])
    t.require(t.digest(t.encode(payload))==row['sha256'],'OBSERVATION_PIN_MISMATCH')
    return (row['series'],row['period'],row['revision']),dict(**payload,sha256=row['sha256'])


def prepare(raw):
    accepted,counts,issues=rows(raw,observation,'observations'); ids=defaultdict(list); periods=defaultdict(list)
    for index,row in accepted.values():
        ids[row['id']].append((index,row)); periods[(row['series'],row['period'])].append((index,row))
    for entries in ids.values():
        if len(entries)>1:
            for index,_ in entries: problem(issues,'observations',index,'OBSERVATION_ID_ALIAS')
    for entries in periods.values():
        entries.sort(key=lambda pair:pair[1]['revision'])
        for (previous_index,previous),(index,row) in zip(entries,entries[1:]):
            if row['available_at']<=previous['available_at']:
                code='REVISION_TIME_TIE' if row['available_at']==previous['available_at'] else 'REVISION_TIME_REVERSED'
                problem(issues,'observations',index,code)
    return {key:entries[0] for key,entries in ids.items()},periods,counts,issues


def latest(periods,series,period,as_of):
    candidates=[row for _,row in periods.get((series,period),[]) if row['available_at']<=as_of]
    t.require(candidates,'OBSERVATION_UNAVAILABLE_AT_CUTOFF')
    return max(candidates,key=lambda row:(row['available_at'],row['revision']))


def reference(row):
    t.fields(row,{'id','sha256'}); t.identifier(row['id']); t.sha(row['sha256']); return dict(row)


def public_reference(row):
    return {key:row[key] for key in ('id','series','period','revision','available_at','sha256')}


def base(raw,fmt,counts,issues):
    return dict(format=fmt,status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=t.digest(raw),counts=counts,
                issues=sorted(issues,key=lambda row:(row['side'],row['row'],row['code'])),
                availability_authority_verified=False,content_privacy_verified=False,
                model_trained=False,target_changes_performed=False)


def cli(description,operation,argv=None):
    p=t.Parser(description=description); p.add_argument('--input',required=True); p.add_argument('--out')
    return t.run(p,lambda a:operation(t.read(a.input)),argv)
