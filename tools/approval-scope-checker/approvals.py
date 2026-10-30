"""Review exact declared approval grants/revocations at a supplied ordinal."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import review_core as r

def event(row,roles):
    key,out=c.record(row,{'id','item','item_revision','item_sha256','policy_sha256','reviewer','role','at','action','grant'},('id','item','reviewer','role'),('item_revision',))
    t.sha(row['item_sha256']);t.sha(row['policy_sha256']);t.integer(row['at']);t.require(row['role'] in roles,'ROLE_UNKNOWN')
    t.require(row['action'] in ('approve','revoke'),'ACTION_INVALID')
    if row['action']=='approve':t.require(row['grant'] is None,'GRANT_MUST_BE_NULL')
    else:t.identifier(row['grant'])
    return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','policy','items','events','as_of'});t.require(v['format']=='outlands-approval-scope-v1','FORMAT_INVALID')
    t.integer(v['as_of']);policy=r.roles(v['policy']);counts={};issues=[]
    items=r.collect(v['items'],r.snapshot,'items',counts,issues)
    events=r.collect(v['events'],lambda row:event(row,policy['required_roles']),'events',counts,issues,False)
    r.slots(events,lambda row:(row['item'],row['reviewer'],row['role'],row['at']),'events',issues)
    revocations=defaultdict(list)
    for position,row in events.values():
        r.reference(row,'item',items,'events',position,issues)
        if row['policy_sha256']!=c.pin(policy):c.issue(issues,'events',position,'POLICY_PIN_MISMATCH')
        if row['action']=='revoke':
            grant=events.get(row['grant'])
            if grant is None:c.issue(issues,'events',position,'GRANT_UNKNOWN');continue
            grant=grant[1]
            if grant['action']!='approve':c.issue(issues,'events',position,'GRANT_NOT_APPROVAL')
            if any(row[field]!=grant[field] for field in ('item','item_revision','item_sha256','policy_sha256','reviewer','role')):c.issue(issues,'events',position,'REVOCATION_SCOPE_MISMATCH')
            if row['at']<=grant['at']:c.issue(issues,'events',position,'REVOCATION_ORDER_INVALID')
            revocations[row['grant']].append(row)
    qualified=not issues;assessment=None
    if qualified:
        out=[];future=sorted(key for key,(_,row) in events.items() if row['at']>v['as_of'])
        for key,(position,item) in sorted(items.items()):
            grants=[row for _,row in events.values() if row['item']==key and row['action']=='approve' and row['at']<=v['as_of']]
            active=sorted((row for row in grants if not any(revoke['at']<=v['as_of'] for revoke in revocations[row['id']])),key=lambda row:row['id'])
            missing=sorted(set(policy['required_roles'])-{row['role'] for row in active})
            if missing:c.issue(issues,'items',position,'APPROVAL_COVERAGE_MISSING')
            out.append(dict(id=key,active_grant_ids=[row['id'] for row in active],revoked_grant_ids=sorted({row['id'] for row in grants}-{row['id'] for row in active}),missing_roles=missing,declared_scope_covered=not missing))
        assessment=dict(items=out,future_event_ids=future,as_of=v['as_of'],all_declared_scopes_covered=not issues)
    # As-of is part of the qualified scope, not just report presentation.
    result=r.output(raw,'outlands-approval-scope-report-v1',counts,issues,qualified,assessment,dict(items=items,events=events),policy)
    if result['review_scope_sha256'] is not None:result['review_scope_sha256']=c.pin(dict(cohort_sha256=result['review_scope_sha256'],as_of=v['as_of']))
    return result

def main(argv=None):return c.cli('Check declared approval scopes; no identity authentication or authorization.',check,argv)
if __name__=='__main__':raise SystemExit(main())
