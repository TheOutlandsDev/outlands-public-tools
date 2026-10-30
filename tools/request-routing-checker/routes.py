"""Check explicit model assignments and pinned route policy without dispatch."""
import toolkit as t
import decision_core as c
import routing_core as r

def proposal(row):
    key,out=c.record(row,{'id','request','request_revision','request_sha256','model','model_revision','model_sha256','policy_sha256'},('id','request','model'),('request_revision','model_revision'))
    for field in ('request_sha256','model_sha256','policy_sha256'):t.sha(row[field])
    return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','models','requests','policy','proposals'})
    t.require(value['format']=='outlands-request-routing-v1','FORMAT_INVALID')
    counts={};issues=[];catalog=r.models(value['models'],counts,issues);rule=r.policy(value['policy']);r.policy_scope(rule,catalog,issues)
    requests=r.collect(value['requests'],r.request,'requests',counts,issues)
    proposals=r.collect(value['proposals'],proposal,'proposals',counts,issues)
    slots=r.unique_slots(proposals,'request','proposals',issues)
    if set(slots)!=set(requests):c.issue(issues,'proposals',0,'REQUEST_COVERAGE_MISMATCH')
    for position,row in proposals.values():
        target=requests.get(row['request'])
        if target is None:c.issue(issues,'proposals',position,'REQUEST_UNKNOWN')
        elif row['request_revision']!=target[1]['revision'] or row['request_sha256']!=c.pin(target[1]):c.issue(issues,'proposals',position,'REQUEST_SNAPSHOT_MISMATCH')
        r.model_reference(row,catalog,'proposals',position,issues)
        if row['policy_sha256']!=c.pin(rule):c.issue(issues,'proposals',position,'POLICY_PIN_MISMATCH')
    qualified=not issues;assessment=None;plan_pin=None
    pins=dict(models_sha256=c.cohort_pin(catalog),requests_sha256=c.cohort_pin(requests),policy_sha256=c.pin(rule),proposals_sha256=c.cohort_pin(proposals))
    if qualified:
        outcomes=[]
        for key,(position,row) in sorted(proposals.items()):
            failures=r.eligible(requests[row['request']][1],catalog[row['model']][1],rule)
            for code in failures:c.issue(issues,'proposals',position,code)
            outcomes.append(dict(id=key,request=row['request'],model=row['model'],eligible=not failures,failed_criteria=failures))
        assessment=dict(proposals=outcomes,eligible_proposals=sum(row['eligible'] for row in outcomes),eligible_for_manual_routing_review=all(row['eligible'] for row in outcomes))
        if assessment['eligible_for_manual_routing_review']:plan_pin=c.pin(pins)
    return r.output(raw,'outlands-request-routing-report-v1',counts,issues,assessment=assessment,
        route_plan_sha256=plan_pin,**{key:pin if qualified else None for key,pin in pins.items()})

def main(argv=None):return c.cli('Review exact proposed request/model assignments; never route requests.',check,argv)
if __name__=='__main__':raise SystemExit(main())
