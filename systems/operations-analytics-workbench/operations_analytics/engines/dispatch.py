"""Versioned declared eligibility/score policy; scores are not probabilities."""
from ..contracts import fields,token,number,boolean,finite
from ..runtime import WorkbenchError


def calculate(value):
    policy=value['policy'];fields(policy,('id','age_weight','urgency_weight','age_horizon_hours','due_horizon_hours'))
    policy_id=token(policy['id']);age=number(policy['age_weight'],maximum=1);urgency=number(policy['urgency_weight'],maximum=1)
    if age+urgency!=1:raise WorkbenchError('POLICY_WEIGHTS_INVALID')
    age_limit=number(policy['age_horizon_hours'],0.000001,1000000);due_limit=number(policy['due_horizon_hours'],0.000001,1000000)
    ranked=[];blocked=[]
    for row in value['candidates']:
        fields(row,('id','wait_hours','due_in_hours','ready','on_hold','downstream_capacity_available'))
        identifier=token(row['id']);wait=number(row['wait_hours'],maximum=1000000);due=number(row['due_in_hours'],-1000000,1000000)
        ready=boolean(row['ready']);hold=boolean(row['on_hold']);space=boolean(row['downstream_capacity_available'])
        reasons=[reason for condition,reason in ((not ready,'PREREQUISITES_INCOMPLETE'),(hold,'ACTIVE_HOLD'),(not space,'NO_DOWNSTREAM_CAPACITY')) if condition]
        if reasons:blocked.append(dict(id=identifier,eligible=False,reasons=reasons));continue
        age_component=age*min(wait/age_limit,1);due_component=urgency*max(0,min(1-due/due_limit,1))
        ranked.append(dict(id=identifier,eligible=True,priority_score=age_component+due_component,age_contribution=age_component,urgency_contribution=due_component,due_in_hours=due,proposal_only=True))
    ranked.sort(key=lambda r:(-r['priority_score'],r['due_in_hours'],r['id']))
    for i,row in enumerate(ranked,1):row['rank']=i
    return finite(dict(policy_id=policy_id,ranked=ranked,blocked=sorted(blocked,key=lambda r:r['id']),trained_model=False,execution_authorized=False))
