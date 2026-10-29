"""Assess selected task/resource proposals against supplied capability/availability claims."""
from collections import defaultdict
import toolkit as t
import resource_core as c


def proposal(row):
    t.fields(row,{'id','task_id','resource_id'})
    for key in row: t.identifier(row[key])
    return row['id'],dict(row)


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','resources','tasks','assignments'})
    t.require(value['format']=='outlands-assignment-eligibility-v1','FORMAT_INVALID')
    resources,rc,issues=c.rows(value['resources'],c.resource,'resources'); resource_issues=bool(issues)
    tasks,tc,other=c.rows(value['tasks'],c.task,'tasks'); issues+=other
    proposals,ac,other=c.rows(value['assignments'],proposal,'assignments'); issues+=other
    if not resources: c.problem(issues,'resources',0,'EMPTY_RESOURCE_COHORT')
    if not tasks: c.problem(issues,'tasks',0,'EMPTY_TASK_COHORT')
    used=defaultdict(list)
    for key,(index,row) in proposals.items():
        used[row['task_id']].append(index)
        if row['task_id'] not in tasks: c.problem(issues,'assignments',index,'TASK_MISSING')
        if row['resource_id'] not in resources: c.problem(issues,'assignments',index,'RESOURCE_MISSING')
    for task_id,indices in used.items():
        if len(indices)>1:
            for index in indices: c.problem(issues,'assignments',index,'MULTIPLE_PROPOSALS_FOR_TASK')
    for key,(index,_) in tasks.items():
        if key not in used: c.problem(issues,'tasks',index,'ASSIGNMENT_MISSING')
    assessments=None
    if not issues:
        assessments=[]
        for key,(index,row) in sorted(proposals.items()):
            task=tasks[row['task_id']][1]; resource=resources[row['resource_id']][1]; reasons=[]
            missing=set(task['required_capabilities'])-set(resource['capabilities'])
            if missing: reasons.append('MISSING_CAPABILITY')
            if task['units']>resource['capacity']: reasons.append('UNITS_EXCEED_CAPACITY')
            if not c.covered(resource,task['start'],task['end']): reasons.append('OUTSIDE_AVAILABILITY')
            if reasons: c.problem(issues,'assignments',index,'ASSIGNMENT_INELIGIBLE')
            assessments.append(dict(id=key,task_id=row['task_id'],resource_id=row['resource_id'],
                eligible_under_declarations=not reasons,reasons=reasons,missing_capabilities_count=len(missing),execution_authorized=False))
    result=c.base(raw,'outlands-assignment-eligibility-review-v1',dict(resources=rc,tasks=tc,assignments=ac),issues)
    result.update(assessments=assessments,resource_contract_sha256=c.resource_pin(resources) if not resource_issues else None,
                  qualifications_certified=False,combined_reservation_capacity_checked=False,work_assigned=False)
    return result


def main(argv=None): return c.cli('Check selected resource/task proposals without allocating work.',check,argv)
if __name__=='__main__': raise SystemExit(main())
