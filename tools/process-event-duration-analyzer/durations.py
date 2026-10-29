"""Compute complete supplied run durations with explicit start/hold/resume/finish states."""
from collections import defaultdict
import toolkit as t
import resource_core as c


def run_row(row):
    t.fields(row,{'id','start','end'}); t.identifier(row['id']); c.interval(row['start'],row['end'])
    return row['id'],dict(row)


def event(row):
    t.fields(row,{'id','run_id','at','kind'}); t.identifier(row['id']); t.identifier(row['run_id'])
    t.integer(row['at'],10**9); t.require(row['kind'] in ('start','hold','resume','finish'),'EVENT_KIND_INVALID')
    return row['id'],dict(row)


def analyze(raw):
    value=t.decode(raw); t.fields(value,{'format','runs','events'})
    t.require(value['format']=='outlands-process-event-durations-v1','FORMAT_INVALID')
    runs,rc,issues=c.rows(value['runs'],run_row,'runs'); events,ec,other=c.rows(value['events'],event,'events'); issues+=other
    if not runs: c.problem(issues,'runs',0,'EMPTY_RUN_COHORT')
    grouped=defaultdict(list)
    for index,row in events.values():
        if row['run_id'] not in runs: c.problem(issues,'events',index,'RUN_MISSING'); continue
        run=runs[row['run_id']][1]
        if not run['start']<=row['at']<=run['end']: c.problem(issues,'events',index,'EVENT_OUTSIDE_RUN')
        grouped[row['run_id']].append((index,row))
    durations=[]
    for key,(ri,run) in sorted(runs.items()):
        ordered=sorted(grouped[key],key=lambda pair:(pair[1]['at'],pair[1]['id']))
        times=defaultdict(list)
        for index,row in ordered: times[row['at']].append(index)
        for indices in times.values():
            if len(indices)>1:
                for index in indices: c.problem(issues,'events',index,'EVENT_TIME_TIE')
        if not ordered or ordered[0][1]['kind']!='start' or ordered[-1][1]['kind']!='finish':
            c.problem(issues,'runs',ri,'MISSING_RUN_BOUNDARIES'); continue
        if ordered[0][1]['at']!=run['start']: c.problem(issues,'runs',ri,'START_BOUNDARY_MISMATCH')
        if ordered[-1][1]['at']!=run['end']: c.problem(issues,'runs',ri,'END_BOUNDARY_MISMATCH')
        state='pending'; previous=run['start']; active=held=holds=0
        for index,row in ordered:
            elapsed=row['at']-previous
            if state=='active': active+=elapsed
            elif state=='held': held+=elapsed
            next_state=None
            if state=='pending' and row['kind']=='start': next_state='active'
            elif state=='active' and row['kind']=='hold': next_state='held'; holds+=1
            elif state=='held' and row['kind']=='resume': next_state='active'
            elif state in ('active','held') and row['kind']=='finish': next_state='finished'
            if next_state is None: c.problem(issues,'events',index,'EVENT_TRANSITION_INVALID')
            else: state=next_state
            previous=row['at']
        if state!='finished': c.problem(issues,'runs',ri,'RUN_NOT_FINISHED')
        durations.append(dict(id=key,elapsed_ticks=run['end']-run['start'],active_ticks=active,hold_ticks=held,hold_count=holds))
    if not issues:
        t.require(all(row['active_ticks']+row['hold_ticks']==row['elapsed_ticks'] for row in durations),'DURATION_ACCOUNTING_FAILED')
    result=c.base(raw,'outlands-process-event-duration-review-v1',dict(runs=rc,events=ec),issues)
    result.update(durations=durations if not issues else None,
        totals={key:sum(row[key] for row in durations) for key in ('elapsed_ticks','active_ticks','hold_ticks','hold_count')} if not issues else None,
        wall_clock_makespan_calculated=False,live_clock_used=False,events_changed=False)
    return result


def main(argv=None): return c.cli('Analyze complete declared process event histories without a live clock.',analyze,argv)
if __name__=='__main__': raise SystemExit(main())
