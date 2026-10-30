"""Subtract declared closure unions from selected working windows without calendar updates."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import schedule_core as r

def closure(row):
    key,out=c.record(row,{'id','calendar','calendar_revision','calendar_sha256','start','end'},('id','calendar'),('calendar_revision',))
    t.sha(row['calendar_sha256']);r.span(dict(start=row['start'],end=row['end']));return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','calendars','closures'});t.require(v['format']=='outlands-availability-exceptions-v1','FORMAT_INVALID')
    counts={};issues=[];calendars=r.collect(v['calendars'],r.calendar,'calendars',counts,issues);r.calendar_scope(calendars)
    closures=r.collect(v['closures'],closure,'closures',counts,issues,False)
    for position,row in closures.values():r.reference(row,'calendar',calendars,'closures',position,issues)
    qualified=not issues;assessment=None
    if qualified:
        grouped=defaultdict(list);closure_reports=[];intersections=0
        for key,(position,row) in sorted(closures.items()):
            clipped=[]
            for window in calendars[row['calendar']][1]['windows']:
                start=max(window['start'],row['start']);end=min(window['end'],row['end'])
                if start<end:clipped.append(dict(start=start,end=end))
            intersections+=len(clipped);t.require(intersections<=4096,'CLOSURE_INTERSECTION_LIMIT')
            if not clipped:c.issue(issues,'closures',position,'CLOSURE_OUTSIDE_WORKING_TIME')
            grouped[row['calendar']].append(row)
            closure_reports.append(dict(id=key,calendar=row['calendar'],clipped_windows=clipped,clipped_units=sum(w['end']-w['start'] for w in clipped)))
        out=[]
        for key,(_,calendar) in sorted(calendars.items()):
            cuts=[]
            for row in sorted(grouped[key],key=lambda row:(row['start'],row['end'],row['id'])):
                if cuts and row['start']<=cuts[-1]['end']:cuts[-1]['end']=max(cuts[-1]['end'],row['end'])
                else:cuts.append(dict(start=row['start'],end=row['end']))
            remaining=[]
            for window in calendar['windows']:
                cursor=window['start']
                for cut in cuts:
                    if cut['end']<=cursor:continue
                    if cut['start']>=window['end']:break
                    if cut['start']>cursor:remaining.append(dict(start=cursor,end=min(cut['start'],window['end'])))
                    cursor=min(window['end'],max(cursor,cut['end']))
                    if cursor==window['end']:break
                if cursor<window['end']:remaining.append(dict(start=cursor,end=window['end']))
            original=sum(w['end']-w['start'] for w in calendar['windows']);available=sum(w['end']-w['start'] for w in remaining)
            out.append(dict(id=key,available_windows=remaining,original_units=original,removed_units=original-available,remaining_units=available,closure_ids=sorted(row['id'] for row in grouped[key])))
        assessment=dict(calendars=out,closures=closure_reports)
    return r.output(raw,'outlands-availability-exceptions-report-v1',counts,issues,qualified,assessment,dict(calendars_sha256=c.cohort_pin(calendars),closures_sha256=c.cohort_pin(closures)))

def main(argv=None):return c.cli('Plan declared working-window exceptions; no calendar changes.',check,argv)
if __name__=='__main__':raise SystemExit(main())
