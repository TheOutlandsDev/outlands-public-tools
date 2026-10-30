"""Recompute selected metric/span scopes and review explicit links; never infer causation."""
import toolkit as t
import decision_core as c
import telemetry_core as r
def requirement(row):
    key,out=c.record(row,{'id','point','point_sha256'},('id','point'));t.sha(row['point_sha256']);return key,out
def link(row):
    key,out=c.record(row,{'id','point','point_sha256','span','span_sha256','at'},('id','point','span'));t.sha(row['point_sha256']);t.sha(row['span_sha256']);t.integer(row['at'],10**12);return key,out
def check(raw):
    v=t.decode(raw);t.fields(v,{'format','definitions','series','runs','points','traces','spans','requirements','links'});t.require(v['format']=='outlands-metric-trace-correlations-v1','FORMAT_INVALID');counts={};issues=[];metrics=r.metric_context(v,counts,issues);traces=r.trace_context(v,counts,issues,metrics['runs'])
    requirements=r.collect(v['requirements'],requirement,'requirements',counts,issues);links=r.collect(v['links'],link,'links',counts,issues,False);r.slots(requirements,lambda row:row['point'],'requirements',issues);r.slots(links,lambda row:(row['point'],row['span']),'links',issues)
    selected={row['point'] for _,row in requirements.values()}
    for position,row in requirements.values():r.reference(row,'point',metrics['points'],'requirements',position,issues,False)
    for position,row in links.values():
        r.reference(row,'point',metrics['points'],'links',position,issues,False);r.reference(row,'span',traces['spans'],'links',position,issues,False)
        if row['point'] not in selected:c.issue(issues,'links',position,'POINT_NOT_SELECTED')
    qualified=not issues;assessment=None
    if qualified:
        out=[];valid={key:[] for key in selected}
        for key,(position,row) in sorted(links.items()):
            point=metrics['points'][row['point']][1];span=traces['spans'][row['span']][1];trace=traces['traces'][span['trace']][1];failed=[]
            if point['run']!=trace['run']:failed.append('LINK_RUN_MISMATCH')
            if row['at']!=point['at']:failed.append('LINK_POINT_TIME_MISMATCH')
            if not span['start']<=row['at']<span['end']:failed.append('LINK_TIME_OUTSIDE_SPAN')
            if not failed:valid[row['point']].append(key)
            for code in failed:c.issue(issues,'links',position,code)
            out.append(dict(id=key,point=row['point'],span=row['span'],consistent=not failed,failed_criteria=failed))
        coverage=[]
        for key,(position,row) in sorted(requirements.items()):
            if not valid[row['point']]:c.issue(issues,'requirements',position,'REQUIRED_LINK_MISSING')
            coverage.append(dict(id=key,point=row['point'],consistent_link_ids=valid[row['point']],covered=bool(valid[row['point']])))
        assessment=dict(links=out,requirements=coverage,clock_synchronization_verified=False,semantic_relationship_verified=False)
    pins={key+'_sha256':c.cohort_pin(metrics[key]) for key in ('definitions','series','runs','points')};pins.update({key+'_sha256':c.cohort_pin(traces[key]) for key in ('traces','spans')});pins.update(requirements_sha256=c.cohort_pin(requirements),links_sha256=c.cohort_pin(links))
    return r.output(raw,'outlands-metric-trace-correlations-report-v1',counts,issues,qualified,assessment,pins)
def main(argv=None):return c.cli('Check explicit metric/span links; no service access, clock verification or causal inference.',check,argv)
if __name__=='__main__':raise SystemExit(main())
