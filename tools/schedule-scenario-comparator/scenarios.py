"""Compare declared schedule scenarios without ranking plans or concealing changed scopes."""
import toolkit as t
import decision_core as c
import schedule_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','baseline','candidate'});t.require(v['format']=='outlands-schedule-scenarios-v1','FORMAT_INVALID')
    counts={};issues=[];left=r.bundle(v['baseline'],counts,issues,'baseline_');right=r.bundle(v['candidate'],counts,issues,'candidate_')
    if left['plan']['id']==right['plan']['id']:c.issue(issues,'plans',0,'PLAN_ID_REUSED')
    qualified=not issues;assessment=None;lp=r.bundle_pins(left);rp=r.bundle_pins(right)
    if qualified:
        a={row['id']:row for row in r.evaluate(left)};b={row['id']:row for row in r.evaluate(right)};out=[]
        same_context=all(lp[field]==rp[field] for field in ('dependencies_sha256','calendars_sha256'))
        for key in sorted(set(a)|set(b)):
            before=a.get(key);after=b.get(key);delta=None
            if before is None:state='added'
            elif after is None:state='removed'
            elif before['task_sha256']!=after['task_sha256']:state='incomparable_task'
            elif not same_context:state='incomparable_context'
            elif before['placement_id'] is None or after['placement_id'] is None:state='incomplete'
            elif before['calendar']!=after['calendar']:state='incomparable_calendar'
            else:
                state='comparable';delta={field:after[field]-before[field] for field in ('start','finish','lateness')}
            if state!='comparable':c.issue(issues,'comparison',0,state.upper())
            for side,row in [('BASELINE',before),('CANDIDATE',after)]:
                if row is not None and not row['declared_timing_feasible']:c.issue(issues,'comparison',0,side+'_TIMING_NOT_FEASIBLE')
            out.append(dict(id=key,state=state,baseline=before,candidate=after,delta=delta))
        complete=all(row['state']=='comparable' for row in out)
        totals=None
        if complete:
            totals={side:dict(latest_finish=max(row['finish'] for row in rows.values()),total_lateness=sum(row['lateness'] for row in rows.values())) for side,rows in [('baseline',a),('candidate',b)]}
            totals['delta']={field:totals['candidate'][field]-totals['baseline'][field] for field in ('latest_finish','total_lateness')}
        assessment=dict(tasks=out,all_tasks_comparable=complete,totals=totals,preferred_plan=None)
    pins={side+'_'+key:value for side,values in [('baseline',lp),('candidate',rp)] for key,value in values.items()}
    return r.output(raw,'outlands-schedule-scenarios-report-v1',counts,issues,qualified,assessment,pins)

def main(argv=None):return c.cli('Compare declared schedule scenarios; no ranking, optimization or dispatch.',check,argv)
if __name__=='__main__':raise SystemExit(main())
