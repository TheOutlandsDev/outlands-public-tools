"""Validate supplied incident history and replay declared actions at an explicit ordinal."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import health_core as r

TRANSITIONS={('not_opened','open'):'open',('open','acknowledge'):'acknowledged',('open','resolve'):'resolved',
    ('acknowledged','resolve'):'resolved',('resolved','reopen'):'open'}

def event(row):
    key,out=c.record(row,{'id','incident','incident_revision','incident_sha256','ordinal','at','action'},('id','incident'),('incident_revision',))
    t.sha(row['incident_sha256']);t.integer(row['ordinal'],1000,1);t.integer(row['at']);t.require(row['action'] in ('open','acknowledge','resolve','reopen'),'ACTION_INVALID');return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','components','incidents','events','as_of'});t.require(v['format']=='outlands-incident-timeline-v1','FORMAT_INVALID');t.integer(v['as_of'])
    counts={};issues=[];components=r.collect(v['components'],r.component,'components',counts,issues)
    incidents=r.collect(v['incidents'],r.incident,'incidents',counts,issues)
    events=r.collect(v['events'],event,'events',counts,issues,False)
    r.slots(events,lambda row:(row['incident'],row['ordinal']),'events',issues)
    for position,row in incidents.values():r.reference(row,'component',components,'incidents',position,issues)
    grouped=defaultdict(list)
    for position,row in events.values():
        r.reference(row,'incident',incidents,'events',position,issues);grouped[row['incident']].append((position,row))
    histories={}
    for key,(_,incident) in sorted(incidents.items()):
        state='not_opened';effective='not_opened';previous=None;history=sorted(grouped[key],key=lambda pair:pair[1]['ordinal']);effective_ids=[];future_ids=[]
        for expected,(position,row) in enumerate(history,1):
            if row['ordinal']!=expected:c.issue(issues,'events',position,'ORDINAL_GAP')
            if previous is not None and row['at']<previous:c.issue(issues,'events',position,'TIME_REVERSED')
            next_state=TRANSITIONS.get((state,row['action']))
            if next_state is None:c.issue(issues,'events',position,'TRANSITION_INVALID')
            else:state=next_state
            if row['at']<=v['as_of']:effective=state;effective_ids.append(row['id'])
            else:future_ids.append(row['id'])
            previous=row['at']
        histories[key]=dict(id=key,state_as_of=effective,resolved_as_of=effective=='resolved',effective_event_ids=effective_ids,future_event_ids=future_ids)
    qualified=not issues;assessment=None
    if qualified:
        out=[]
        for key,(position,incident) in sorted(incidents.items()):
            row=histories[key]
            if not grouped[key]:c.issue(issues,'incidents',position,'HISTORY_MISSING')
            elif row['state_as_of']=='not_opened':c.issue(issues,'incidents',position,'NO_EFFECTIVE_OPEN')
            out.append(row)
        assessment=dict(incidents=out,all_selected_histories_present_and_effective=not issues)
    return r.output(raw,'outlands-incident-timeline-report-v1',counts,issues,qualified,assessment,dict(components=components,incidents=incidents,events=events),context=dict(as_of=v['as_of']))

def main(argv=None):return c.cli('Check declared incident histories; no incident updates or notifications.',check,argv)
if __name__=='__main__':raise SystemExit(main())
