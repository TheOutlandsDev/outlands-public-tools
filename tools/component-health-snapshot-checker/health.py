"""Check one explicitly selected observation per required component; never probe."""
import toolkit as t
import decision_core as c
import health_core as r

def observation(row):
    key,out=c.record(row,{'id','component','component_revision','component_sha256','observed_at','state'},('id','component'),('component_revision',))
    t.sha(row['component_sha256']);t.integer(row['observed_at']);t.require(row['state'] in ('healthy','degraded','down','unknown','maintenance'),'STATE_INVALID');return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','components','observations','as_of'});t.require(v['format']=='outlands-component-health-v1','FORMAT_INVALID');t.integer(v['as_of'])
    counts={};issues=[];components=r.collect(v['components'],r.component,'components',counts,issues)
    observations=r.collect(v['observations'],observation,'observations',counts,issues,False)
    r.slots(observations,lambda row:row['component'],'observations',issues)
    for position,row in observations.values():r.reference(row,'component',components,'observations',position,issues)
    qualified=not issues;assessment=None
    if qualified:
        selected={row['component']:row for _,row in observations.values()};out=[]
        for key,(position,component) in sorted(components.items()):
            row=selected.get(key);codes=[];age=dict(age=None,future=False,fresh=False)
            if row is None:codes.append('OBSERVATION_MISSING')
            else:
                age=r.freshness(row['observed_at'],v['as_of'],component['maximum_age'])
                if age['future']:codes.append('OBSERVATION_FUTURE')
                elif not age['fresh']:codes.append('OBSERVATION_STALE')
                if row['state']!='healthy':codes.append('DECLARED_STATE_NOT_HEALTHY')
            for code in codes:c.issue(issues,'components',position,code)
            out.append(dict(id=key,observation_id=row['id'] if row else None,declared_state=row['state'] if row else None,**age,
                declared_healthy_and_fresh=not codes,failed_criteria=codes))
        assessment=dict(components=out,all_declared_healthy_and_fresh=not issues)
    return r.output(raw,'outlands-component-health-report-v1',counts,issues,qualified,assessment,dict(components=components,observations=observations),context=dict(as_of=v['as_of']))

def main(argv=None):return c.cli('Check declared health snapshots; no probing or live collection.',check,argv)
if __name__=='__main__':raise SystemExit(main())
