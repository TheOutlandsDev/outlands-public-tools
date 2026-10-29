"""Bounded explicit intervals, resource declarations and complete identity accounting."""
from collections import defaultdict
import toolkit as t


def problem(issues,side,row,code,**metadata): issues.append(dict(side=side,row=row,code=code,**metadata))


def rows(value,parser,side):
    t.require(type(value) is list and len(value)<=1000,'ROW_LIMIT')
    groups=defaultdict(list); issues=[]; rejected=0
    for index,row in enumerate(value,1):
        try:
            key,normalized=parser(row); groups[key].append((index,normalized))
        except t.Rejected as error:
            rejected+=1; problem(issues,side,index,str(error))
    accepted={}; duplicate=conflict=0
    for key,entries in groups.items():
        if len({t.encode(record) for _,record in entries})!=1:
            conflict+=len(entries)
            for index,_ in entries: problem(issues,side,index,'IDENTITY_CONFLICT')
        else:
            accepted[key]=entries[0]; duplicate+=len(entries)-1
    counts=dict(input_rows=len(value),accepted_records=len(accepted),duplicate_rows=duplicate,
                conflict_rows=conflict,rejected_rows=rejected)
    t.require(len(value)==len(accepted)+duplicate+conflict+rejected,'ACCOUNTING_FAILED')
    return accepted,counts,issues


def interval(start,end):
    t.integer(start,10**9); t.integer(end,10**9)
    t.require(start<end,'INTERVAL_INVALID')
    return dict(start=start,end=end)


def tags(value):
    t.require(type(value) is list and len(value)<=32,'CAPABILITY_LIMIT')
    for item in value: t.identifier(item)
    t.require(len(set(value))==len(value),'DUPLICATE_CAPABILITY')
    return sorted(value)


def resource(row):
    t.fields(row,{'id','capacity','capabilities','availability'}); t.identifier(row['id'])
    t.integer(row['capacity'],10**6,1); capabilities=tags(row['capabilities'])
    raw=row['availability']; t.require(type(raw) is list and len(raw)<=32,'AVAILABILITY_LIMIT')
    periods=[]
    for entry in raw:
        t.fields(entry,{'start','end'}); periods.append(interval(entry['start'],entry['end']))
    periods.sort(key=lambda span:(span['start'],span['end'])); merged=[]
    for span in periods:
        if merged:
            t.require(span['start']>=merged[-1]['end'],'AVAILABILITY_OVERLAP')
            if span['start']==merged[-1]['end']:
                merged[-1]['end']=span['end']; continue
        merged.append(dict(span))
    return row['id'],dict(id=row['id'],capacity=row['capacity'],capabilities=capabilities,availability=merged)


def covered(resource,start,end):
    return any(span['start']<=start and end<=span['end'] for span in resource['availability'])


def task(row):
    t.fields(row,{'id','start','end','units','required_capabilities'}); t.identifier(row['id'])
    interval(row['start'],row['end']); t.integer(row['units'],10**6,1)
    return row['id'],dict(row,required_capabilities=tags(row['required_capabilities']))


def resource_pin(resources): return t.digest(t.encode([resources[key][1] for key in sorted(resources)]))


def base(raw,fmt,counts,issues):
    return dict(format=fmt,status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=t.digest(raw),counts=counts,
                issues=sorted(issues,key=lambda row:(row['side'],row['row'],row['code'])),
                claims_authority_verified=False,content_privacy_verified=False,
                execution_authorized=False,target_changes_performed=False)


def cli(description,operation,argv=None):
    p=t.Parser(description=description); p.add_argument('--input',required=True); p.add_argument('--out')
    return t.run(p,lambda a:operation(t.read(a.input)),argv)
