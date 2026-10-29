"""Resolve exact supplied observation revisions at inclusive declared cutoffs."""
import toolkit as t
import temporal_core as c


def request(row):
    t.fields(row,{'id','series','period','as_of'}); t.identifier(row['id']); t.identifier(row['series'])
    c.ordinal(row['period']); c.ordinal(row['as_of']); t.require(row['period']<=row['as_of'],'CUTOFF_BEFORE_PERIOD')
    return row['id'],dict(row)


def resolve(raw):
    value=t.decode(raw); t.fields(value,{'format','observations','requests'})
    t.require(value['format']=='outlands-point-in-time-observations-v1','FORMAT_INVALID')
    ids,periods,oc,issues=c.prepare(value['observations'])
    requests,rc,other=c.rows(value['requests'],request,'requests'); issues+=other
    if not requests: c.problem(issues,'requests',0,'EMPTY_REQUEST_COHORT')
    resolved=[]
    for key,(index,row) in sorted(requests.items()):
        try:
            selected=c.latest(periods,row['series'],row['period'],row['as_of'])
            resolved.append(dict(request_id=key,as_of=row['as_of'],observation=c.public_reference(selected)))
        except t.Rejected as error: c.problem(issues,'requests',index,str(error))
    result=c.base(raw,'outlands-point-in-time-observation-review-v1',dict(observations=oc,requests=rc),issues)
    result.update(resolutions=resolved if not issues else None,cutoff_inclusive=True,observation_values_emitted=False)
    return result


def main(argv=None): return c.cli('Resolve supplied pinned observation revisions as of explicit cutoffs.',resolve,argv)
if __name__=='__main__': raise SystemExit(main())
