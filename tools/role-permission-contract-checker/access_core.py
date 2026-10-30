"""Bounded literal RBAC declarations and nonexecuting, closed-world decision arithmetic."""
from collections import deque
import toolkit as t
import decision_core as c

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def named(row):return c.record(row,{'id'},('id',))
def role(row):
    key,out=c.record(row,{'id','inherits'},('id',));out['inherits']=c.tags(row['inherits']);return key,out
def assignment(row):
    key,out=c.record(row,{'id','actor','roles'},('id','actor'));out['roles']=c.tags(row['roles']);return key,out
def rule(row):
    key,out=c.record(row,{'id','role','action','resource','effect'},('id','role','action','resource'));t.require(row['effect'] in ('allow','deny'),'EFFECT_INVALID');return key,out

def slots(rows,slot,side,issues):
    seen=set()
    for position,row in rows.values():
        key=slot(row)
        if key in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen.add(key)

def reference(value,records,side,position,issues):
    if value not in records:c.issue(issues,side,position,'REFERENCE_UNKNOWN')

def policy(value,side,counts,issues):
    t.fields(value,{'id','revision','roles','actions','resources','assignments','rules'});t.identifier(value['id']);t.integer(value['revision'],10**6,1)
    local=[];sets={}
    for field,parser,required in [('roles',role,True),('actions',named,True),('resources',named,True),('assignments',assignment,False),('rules',rule,False)]:sets[field]=collect(value[field],parser,side+'_'+field,counts,local,required)
    roles=sets['roles'];assignments=sets['assignments'];rules=sets['rules']
    slots(assignments,lambda row:row['actor'],side+'_assignments',local);slots(rules,lambda row:(row['role'],row['action'],row['resource']),side+'_rules',local)
    for position,row in roles.values():
        for parent in row['inherits']:reference(parent,roles,side+'_roles',position,local)
    for position,row in assignments.values():
        for key in row['roles']:reference(key,roles,side+'_assignments',position,local)
    for position,row in rules.values():
        for field,cohort in [('role','roles'),('action','actions'),('resource','resources')]:reference(row[field],sets[cohort],side+'_rules',position,local)
    normalized=dict(id=value['id'],revision=value['revision'],**{field:[rows[key][1] for key in sorted(rows)] for field,rows in sets.items()})
    closure={};actors={}
    if not local:
        waiting={key:len(row['inherits']) for key,(_,row) in roles.items()};children={key:[] for key in roles}
        for key,(_,row) in roles.items():
            for parent in row['inherits']:children[parent].append(key)
        pending=deque(sorted(key for key,n in waiting.items() if n==0));total=0
        while pending:
            key=pending.popleft();expanded={key}
            for parent in roles[key][1]['inherits']:expanded.update(closure[parent])
            total+=len(expanded);t.require(total<=16384,'ROLE_EXPANSION_LIMIT');closure[key]=expanded
            for child in sorted(children[key]):
                waiting[child]-=1
                if waiting[child]==0:pending.append(child)
        if len(closure)!=len(roles):c.issue(local,side+'_roles',0,'ROLE_CYCLE')
        else:
            total=0
            for _,row in assignments.values():
                expanded=set()
                for key in row['roles']:expanded.update(closure[key])
                total+=len(expanded);t.require(total<=16384,'ACTOR_EXPANSION_LIMIT');actors[row['actor']]=expanded
    issues.extend(local)
    return dict(value=normalized,sets=sets,closure=closure,actors=actors,valid=not local)

def request(row):
    key,out=c.record(row,{'id','revision','actor','action','resource','expected'},('id','actor','action','resource'),('revision',));t.require(row['expected'] in ('allow','deny',None),'EXPECTED_INVALID');return key,out

def requests(value,context,side,counts,issues,required=True):
    rows=collect(value,request,side,counts,issues,required)
    for position,row in rows.values():
        for field,cohort in [('action','actions'),('resource','resources')]:reference(row[field],context['sets'][cohort],side,position,issues)
    t.require(len(rows)*len(context['sets']['rules'])<=50000,'DECISION_SCOPE_LIMIT');return rows

def decide(context,row):
    roles=context['actors'].get(row['actor'],set());allows=[];denies=[]
    for key,(_,item) in sorted(context['sets']['rules'].items()):
        if item['role'] in roles and (item['action'],item['resource'])==(row['action'],row['resource']):(allows if item['effect']=='allow' else denies).append(key)
    decision='deny' if denies or not allows else 'allow';reason='explicit_deny' if denies else 'explicit_allow' if allows else 'default_deny'
    return dict(decision=decision,reason=reason,assignment_present=row['actor'] in context['actors'],matching_allow_rule_ids=allows,matching_deny_rule_ids=denies,expectation_met=None if row['expected'] is None else row['expected']==decision)

def output(raw,fmt,counts,issues,qualified,assessment,pins):
    report=c.base(raw,fmt,counts,issues)
    report.update(assessment=assessment,qualified_scope_sha256=c.pin(dict(format=fmt,**pins)) if qualified and not issues else None,
        identity_authenticated=False,authorization_verified=False,access_enforced=False,permissions_changed=False,
        accounts_changed=False,network_accessed=False,actions_executed=False,records_changed=False)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
