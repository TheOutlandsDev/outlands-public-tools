"""Validate a narrow, explicit inspect/rework/scrap history protocol without execution."""
from collections import defaultdict
import toolkit as t
import quality_core as c

def event(row):
    key,out=c.record(row,{'id','specimen_id','at','attempt','kind'},('id','specimen_id'),(('at',0,10**9),('attempt',1,1000)))
    t.require(row['kind'] in ('inspect_pass','inspect_fail','rework','scrap'),'EVENT_KIND_INVALID');return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','units','events'})
    t.require(value['format']=='outlands-rework-histories-v1','FORMAT_INVALID')
    units,uc,issues=c.rows(value['units'],c.entity,'units');events,ec,other=c.rows(value['events'],event,'events');issues+=other
    if not units:c.issue(issues,'units',0,'EMPTY_UNIT_COHORT')
    grouped=defaultdict(list)
    for index,row in events.values():
        if row['specimen_id'] not in units:c.issue(issues,'events',index,'SPECIMEN_MISSING')
        else:grouped[row['specimen_id']].append((index,row))
    histories=[];dispositions=[]
    for key,(index,_) in sorted(units.items()):
        ordered=sorted(grouped[key],key=lambda pair:(pair[1]['at'],pair[1]['id']));times=defaultdict(list)
        for ei,row in ordered:times[row['at']].append(ei)
        for positions in times.values():
            if len(positions)>1:
                for ei in positions:c.issue(issues,'events',ei,'EVENT_TIME_TIE')
        state='new';current=inspections=repairs=0
        for ei,row in ordered:
            kind=row['kind'];attempt=row['attempt'];valid=False
            if kind in ('inspect_pass','inspect_fail') and state in ('new','awaiting_reinspection') and attempt==current+1:
                current=attempt;inspections+=1;state='passed' if kind=='inspect_pass' else 'failed';valid=True
            elif kind=='rework' and state=='failed' and attempt==current:
                repairs+=1;state='awaiting_reinspection';valid=True
            elif kind=='scrap' and state=='failed' and attempt==current:state='scrapped';valid=True
            if not valid:c.issue(issues,'events',ei,'REWORK_TRANSITION_OR_ATTEMPT_INVALID')
        if state not in ('passed','scrapped'):c.issue(issues,'units',index,'HISTORY_NOT_TERMINAL')
        outcome='scrap' if state=='scrapped' else 'first_pass_good' if inspections==1 else 'reworked_good'
        histories.append(dict(id=key,disposition=outcome,inspection_attempts=inspections,rework_events=repairs,
                              first_at=ordered[0][1]['at'] if ordered else None,last_at=ordered[-1][1]['at'] if ordered else None))
        dispositions.append(dict(id=key,specimen_id=key,disposition=outcome))
    result=c.base(raw,'outlands-rework-history-review-v1',dict(units=uc,events=ec),issues)
    result.update(histories=histories if not issues else None,dispositions=dispositions if not issues else None,
        totals={key:sum(row[key] for row in histories) for key in ('inspection_attempts','rework_events')} if not issues else None,
        manufacturing_route_verified=False,inspection_outcomes_recomputed=False,rework_performed=False)
    return result

def main(argv=None):return c.cli('Check declared inspection attempts and rework histories; no process actions.',check,argv)
if __name__=='__main__':raise SystemExit(main())
