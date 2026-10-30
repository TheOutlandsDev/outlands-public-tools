"""Plan declared cache freshness at an explicit ordinal without reading a clock."""
import toolkit as t
import decision_core as c
import cache_core as r

def policy(row):
    _,out=c.record(row,{'id','revision','lifetime'},('id',),('revision',));t.integer(row['lifetime'],10**9);return out

def entry(row):
    key,out=c.record(row,{'id','revision','key_sha256','content_sha256','created_at','inputs'},('id',),('revision',))
    t.sha(row['key_sha256']);t.sha(row['content_sha256']);r.ordinal(row['created_at']);out['inputs']=r.inputs(row['inputs'],1);return key,out

def invalidation(row):
    key,out=c.record(row,{'id','dependency','dependency_revision','dependency_sha256','at'},('id','dependency'),('dependency_revision',))
    t.sha(row['dependency_sha256']);r.ordinal(row['at']);return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','policy','entries','invalidations','as_of'})
    t.require(value['format']=='outlands-cache-freshness-v1','FORMAT_INVALID')
    rule=policy(value['policy']);as_of=r.ordinal(value['as_of']);counts={};issues=[]
    entries=r.collect(value['entries'],entry,'entries',counts,issues)
    invalidations=r.collect(value['invalidations'],invalidation,'invalidations',counts,issues,False)
    r.unique_slots(entries,lambda row:row['key_sha256'],'entries',issues)
    snapshots={(p['id'],p['revision'],p['sha256']) for _,row in entries.values() for p in row['inputs']}
    for position,row in invalidations.values():
        if (row['dependency'],row['dependency_revision'],row['dependency_sha256']) not in snapshots:c.issue(issues,'invalidations',position,'DEPENDENCY_SNAPSHOT_UNKNOWN')
    qualified=not issues;assessment=None
    if qualified:
        outcomes=[]
        for key,(position,row) in sorted(entries.items()):
            expiry=row['created_at']+rule['lifetime'];inputs={(p['id'],p['revision'],p['sha256']) for p in row['inputs']}
            applicable=sorted(k for k,(_,i) in invalidations.items() if i['at']<=as_of and (i['dependency'],i['dependency_revision'],i['dependency_sha256']) in inputs)
            future=row['created_at']>as_of;expired=not future and as_of>=expiry;codes=[]
            if future:codes.append('CREATION_AFTER_AS_OF')
            if applicable:codes.append('DEPENDENCY_INVALIDATED')
            if expired:codes.append('LIFETIME_EXPIRED')
            for code in codes:c.issue(issues,'entries',position,code)
            state='future_creation' if future else 'invalidated' if applicable else 'expired' if expired else 'fresh'
            outcomes.append(dict(id=key,state=state,age=None if future else as_of-row['created_at'],expires_at=expiry,
                invalidation_ids=applicable,expired=expired,eligible_for_manual_read_review=not codes,failed_criteria=codes))
        assessment=dict(as_of=as_of,entries=outcomes,fresh_entries=sum(o['state']=='fresh' for o in outcomes))
    pins=dict(policy_sha256=c.pin(rule),entries_sha256=c.cohort_pin(entries),invalidations_sha256=c.cohort_pin(invalidations))
    return r.output(raw,'outlands-cache-freshness-report-v1',counts,issues,assessment=assessment,
        **{key:pin if qualified else None for key,pin in pins.items()},as_of=as_of)

def main(argv=None):return c.cli('Review declared freshness at an explicit ordinal; no clock or cache changes.',check,argv)
if __name__=='__main__':raise SystemExit(main())
