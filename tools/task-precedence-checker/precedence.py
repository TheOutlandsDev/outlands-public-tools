"""Check declared task DAGs and precedence-only release/duration lower bounds."""
import toolkit as t
import decision_core as c
import schedule_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','tasks','dependencies'});t.require(v['format']=='outlands-task-precedence-v1','FORMAT_INVALID')
    counts={};issues=[];tasks=r.collect(v['tasks'],r.task,'tasks',counts,issues);dependencies=r.collect(v['dependencies'],r.dependency,'dependencies',counts,issues,False)
    order,incoming=r.graph(tasks,dependencies,'dependencies',issues);qualified=not issues;assessment=None
    if qualified:
        computed={}
        for key in order:
            task=tasks[key][1];start=max([task['release']]+[computed[row['predecessor']]['earliest_finish']+row['minimum_lag'] for row in incoming[key]])
            finish=start+task['duration'];late=max(0,finish-task['due'])
            if late:c.issue(issues,'tasks',tasks[key][0],'EARLIEST_FINISH_AFTER_DUE')
            computed[key]=dict(id=key,earliest_start=start,earliest_finish=finish,unavoidable_lateness=late,predecessor_ids=sorted(row['predecessor'] for row in incoming[key]))
        assessment=dict(tasks=[computed[key] for key in sorted(tasks)],all_precedence_lower_bounds_within_due=not issues,calendar_and_capacity_constraints_applied=False)
    return r.output(raw,'outlands-task-precedence-report-v1',counts,issues,qualified,assessment,dict(tasks_sha256=c.cohort_pin(tasks),dependencies_sha256=c.cohort_pin(dependencies)))

def main(argv=None):return c.cli('Check declared task precedence; no scheduling or optimization.',check,argv)
if __name__=='__main__':raise SystemExit(main())
