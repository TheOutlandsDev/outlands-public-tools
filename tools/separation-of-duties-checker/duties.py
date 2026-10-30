"""Check explicit prohibited role/action pairs on supplied fictional declarations."""
import toolkit as t
import decision_core as c
import access_core as r

def role_constraint(row):
    key,out=c.record(row,{'id','roles'},('id',));out['roles']=c.tags(row['roles'],2);t.require(len(out['roles'])==2,'ROLE_PAIR_REQUIRED');return key,out
def workflow_constraint(row):
    key,out=c.record(row,{'id','left_action','right_action'},('id','left_action','right_action'));t.require(row['left_action']!=row['right_action'],'DISTINCT_ACTIONS_REQUIRED')
    out['left_action'],out['right_action']=sorted([row['left_action'],row['right_action']]);return key,out
def event(row):
    key,out=c.record(row,{'id','actor','action','resource','policy_sha256'},('id','actor','action','resource'));t.sha(row['policy_sha256']);return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','policy','role_constraints','workflow_constraints','events'});t.require(v['format']=='outlands-separation-of-duties-v1','FORMAT_INVALID');counts={};issues=[];context=r.policy(v['policy'],'policy',counts,issues)
    roles=r.collect(v['role_constraints'],role_constraint,'role_constraints',counts,issues,False);flows=r.collect(v['workflow_constraints'],workflow_constraint,'workflow_constraints',counts,issues,False);events=r.collect(v['events'],event,'events',counts,issues,False)
    if not roles and not flows:c.issue(issues,'constraints',0,'CONSTRAINTS_EMPTY')
    r.slots(roles,lambda row:tuple(row['roles']),'role_constraints',issues);r.slots(flows,lambda row:(row['left_action'],row['right_action']),'workflow_constraints',issues)
    for position,row in roles.values():
        for role in row['roles']:r.reference(role,context['sets']['roles'],'role_constraints',position,issues)
    for position,row in flows.values():
        for field in ('left_action','right_action'):r.reference(row[field],context['sets']['actions'],'workflow_constraints',position,issues)
    for position,row in events.values():
        for field,cohort in [('action','actions'),('resource','resources')]:r.reference(row[field],context['sets'][cohort],'events',position,issues)
        if row['policy_sha256']!=c.pin(context['value']):c.issue(issues,'events',position,'POLICY_PIN_MISMATCH')
    t.require(len(roles)*len(context['actors'])+len(flows)*max(1,len(events))<=20000,'DUTY_SCOPE_LIMIT');qualified=not issues;assessment=None
    if qualified:
        role_findings=[];workflow_findings=[];groups={}
        if roles and not context['actors']:c.issue(issues,'assignments',0,'ACTOR_ASSIGNMENTS_EMPTY')
        if flows and not events:c.issue(issues,'events',0,'WORKFLOW_EVIDENCE_EMPTY')
        for key,(position,row) in sorted(roles.items()):
            for actor,effective in sorted(context['actors'].items()):
                if set(row['roles'])<=effective:role_findings.append(dict(constraint=key,actor=actor,roles=row['roles']));c.issue(issues,'role_constraints',position,'PROHIBITED_ROLE_COMBINATION')
        for key,(_,row) in sorted(events.items()):groups.setdefault((row['actor'],row['resource']),{}).setdefault(row['action'],[]).append(key)
        for key,(position,row) in sorted(flows.items()):
            for (actor,resource),actions in sorted(groups.items()):
                if row['left_action'] in actions and row['right_action'] in actions:
                    workflow_findings.append(dict(constraint=key,actor=actor,resource=resource,left_event_ids=actions[row['left_action']],right_event_ids=actions[row['right_action']]));c.issue(issues,'workflow_constraints',position,'PROHIBITED_WORKFLOW_COMBINATION')
        assessment=dict(role_conflicts=role_findings,workflow_conflicts=workflow_findings,declared_actor_count=len(context['actors']),declared_event_count=len(events),event_permissions_checked=False,workflow_history_complete=False)
    return r.output(raw,'outlands-separation-of-duties-report-v1',counts,issues,qualified,assessment,dict(policy_sha256=c.pin(context['value']),role_constraints_sha256=c.cohort_pin(roles),workflow_constraints_sha256=c.cohort_pin(flows),events_sha256=c.cohort_pin(events)))

def main(argv=None):return c.cli('Check declared separation of duties; no identity, authority or actual workflow proof.',check,argv)
if __name__=='__main__':raise SystemExit(main())
