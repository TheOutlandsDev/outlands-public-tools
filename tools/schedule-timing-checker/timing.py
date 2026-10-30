"""Check pinned proposed placements against declared windows, releases, due values and lags."""
import toolkit as t
import decision_core as c
import schedule_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','tasks','dependencies','calendars','plan','placements'});t.require(v['format']=='outlands-schedule-timing-v1','FORMAT_INVALID')
    counts={};issues=[];b=r.bundle({k:value for k,value in v.items() if k!='format'},counts,issues);qualified=not issues;assessment=None
    if qualified:
        outcomes=r.evaluate(b)
        for row in outcomes:
            for code in row['failed_criteria']:c.issue(issues,'tasks',b['tasks'][row['id']][0],code)
        assessment=dict(tasks=outcomes,all_declared_timing_feasible=not issues)
    return r.output(raw,'outlands-schedule-timing-report-v1',counts,issues,qualified,assessment,r.bundle_pins(b))

def main(argv=None):return c.cli('Check declared schedule timing; no capacity check or dispatch.',check,argv)
if __name__=='__main__':raise SystemExit(main())
