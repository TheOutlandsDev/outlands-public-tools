"""Deterministic incident lifecycle and time-weighted coverage over supplied facts."""
from datetime import timedelta
from . import contracts as c,runtime as r

RANK={'warning':1,'critical':2}
BUCKETS=('healthy','degraded','down','unknown','maintenance','planned_off')

def identity(service,signal,kind):
    # Deliberately excludes volatile severity, note text and measured values.
    return r.digest(r.encode(dict(service_id=service,signal_id=signal,kind=kind)))

def signals_at(case,snapshot,service,at):
    row=next((row for row in snapshot['services'] if row['service_id']==service['id']),None)
    supplied={signal['id']:signal for signal in row['signals']} if row else {}
    result=[]
    for identifier in service['signals']:
        signal=supplied.get(identifier);reason='missing' if signal is None else 'fresh'
        if signal is not None:
            if (at-c.timestamp(signal['observed_at'])).total_seconds()>case['policy']['maximum_age_seconds']:reason='stale'
            elif signal['state']=='unknown':reason='declared_unknown'
        result.append(dict(id=identifier,state=signal['state'] if reason=='fresh' else 'unknown',reason=reason,observed_at=signal['observed_at'] if signal else None,note=signal['note'] if signal else ''))
    return result

def classify(case,snapshot,service,at):
    facts=signals_at(case,snapshot,service,at)
    if service['expected_state']=='planned_off':return 'planned_off',facts,None
    window=next((window for window in case['maintenance'] if window['service_id']==service['id'] and c.timestamp(window['start'])<=at<c.timestamp(window['end'])),None)
    if window:return 'maintenance',facts,window['id']
    states=[fact['state'] for fact in facts]
    status='down' if 'down' in states else 'unknown' if 'unknown' in states else 'degraded' if 'degraded' in states else 'healthy'
    return status,facts,None

def _issue(incidents,service,fact,kind,severity,snapshot):
    key=identity(service['id'],fact['id'],kind);at=snapshot['at'];row=incidents.get(key)
    evidence_key=at if kind=='freshness' else fact['observed_at']
    if row is None:
        row=dict(incident_id=key,service_id=service['id'],signal_id=fact['id'],kind=kind,state='active',severity=severity,peak_severity=severity,episode=1,escalations=0,first_seen=at,episode_started=at,last_seen=at,resolved_at=None,occurrences=0,episode_occurrences=0,clean_count=0,last_clean_evidence_at=None,last_issue_evidence_at=None,recovery_after=None,held=False,hold_reason='',episodes=[])
        incidents[key]=row
    elif row['state']=='resolved':
        row['episode']+=1;row['episode_started']=at;row['episode_occurrences']=0;row['escalations']=0;row['severity']=severity;row['peak_severity']=severity;row['resolved_at']=None;row['last_issue_evidence_at']=None;row['recovery_after']=None
    elif RANK[severity]>RANK[row['severity']]:row['escalations']+=1
    if evidence_key!=row['last_issue_evidence_at']:
        row['occurrences']+=1;row['episode_occurrences']+=1
    row.update(state='active',severity=severity,peak_severity=max((row['peak_severity'],severity),key=RANK.get),last_seen=at,last_issue_evidence_at=evidence_key,clean_count=0,last_clean_evidence_at=None,held=False,hold_reason='',latest_evidence=dict(snapshot_id=snapshot['id'],at=at,**fact))
    row['recovery_after']=max(row['recovery_after'] or evidence_key,evidence_key)

def _hold(row,reason,after=None):
    if row is not None and row['state']!='resolved':
        row.update(clean_count=0,last_clean_evidence_at=None,held=True,hold_reason=reason)
        if after is not None:row['recovery_after']=max(row['recovery_after'] or after,after)

def _clean(row,evidence_at,at,required):
    if row is None or row['state']=='resolved':return
    if evidence_at<(row['recovery_after'] or evidence_at):
        _hold(row,'fresh_evidence_required');return
    row.update(held=False,hold_reason='')
    if evidence_at==row['last_clean_evidence_at']:return
    row['clean_count']+=1;row['last_clean_evidence_at']=evidence_at
    if row['clean_count']>=required:
        row['state']='resolved';row['resolved_at']=at;row['episodes'].append(dict(episode=row['episode'],started=row['episode_started'],resolved_at=at,occurrences=row['episode_occurrences'],peak_severity=row['peak_severity']))
    else:row['state']='monitoring'

def availability(case):
    samples=case['snapshots'];rows=[];policy=case['policy']
    for service in case['services']:
        buckets=dict.fromkeys(BUCKETS,0)
        for current,following in zip(samples,samples[1:]):
            start=c.timestamp(current['at']);end=c.timestamp(following['at']);gap=start+timedelta(seconds=policy['maximum_gap_seconds']);points={start,end}
            if start<gap<end:points.add(gap)
            for fact in signals_at(case,current,service,start):
                if fact['observed_at'] is not None:
                    expiry=c.timestamp(fact['observed_at'])+timedelta(seconds=policy['maximum_age_seconds'])
                    if start<expiry<end:points.add(expiry)
            for window in case['maintenance']:
                if window['service_id']==service['id']:
                    for boundary in ('start','end'):
                        point=c.timestamp(window[boundary])
                        if start<point<end:points.add(point)
            points=sorted(points)
            for left,right in zip(points,points[1:]):
                middle=left+(right-left)/2;status=classify(case,current,service,middle)[0]
                if middle>=gap and status not in ('maintenance','planned_off'):status='unknown'
                buckets[status]+=int((right-left).total_seconds())
        known=buckets['healthy']+buckets['degraded']+buckets['down'];eligible=known+buckets['unknown'];total=sum(buckets.values())
        rows.append(dict(service_id=service['id'],seconds=buckets,total_seconds=total,eligible_seconds=eligible,known_seconds=known,healthy_fraction_of_known_seconds=buckets['healthy']/known if known else None,observation_coverage_fraction=known/eligible if eligible else None))
    return dict(start=samples[0]['at'] if samples else None,end=samples[-1]['at'] if samples else None,tail_extrapolated=False,services=rows)

def analyse(case):
    incidents={};timeline=[];prior=None;policy=case['policy']
    for snapshot in case['snapshots']:
        at=c.timestamp(snapshot['at'])
        if prior is not None and (at-prior).total_seconds()>policy['maximum_gap_seconds']:
            for row in incidents.values():_hold(row,'observation_gap',c.stamp(prior+timedelta(seconds=1)))
        prior=at
        for service in case['services']:
            status,facts,window=classify(case,snapshot,service,at)
            timeline.append(dict(snapshot_id=snapshot['id'],at=snapshot['at'],service_id=service['id'],status=status,maintenance_id=window,fresh_signals=sum(f['reason']=='fresh' for f in facts),required_signals=len(facts),uncertain_signals=[f['id'] for f in facts if f['state']=='unknown']))
            if status in ('maintenance','planned_off'):
                for row in incidents.values():
                    if row['service_id']==service['id']:
                        end=next(w['end'] for w in case['maintenance'] if w['id']==window) if window else snapshot['at']
                        _hold(row,status,end)
                continue
            for fact in facts:
                health=incidents.get(identity(service['id'],fact['id'],'health'));freshness=incidents.get(identity(service['id'],fact['id'],'freshness'))
                if fact['state']=='unknown':
                    _issue(incidents,service,fact,'freshness','warning',snapshot);_hold(health,fact['reason'],snapshot['at'])
                else:
                    _clean(freshness,fact['observed_at'],snapshot['at'],policy['clean_samples'])
                    if fact['state'] in ('down','degraded'):_issue(incidents,service,fact,'health','critical' if fact['state']=='down' else 'warning',snapshot)
                    else:_clean(health,fact['observed_at'],snapshot['at'],policy['clean_samples'])
    rows=sorted(incidents.values(),key=lambda row:(row['service_id'],row['signal_id'],row['kind']))
    for row in rows:
        acknowledgement=next((a for a in reversed(case['acknowledgements']) if a['incident_id']==row['incident_id'] and a['expected_episode']==row['episode'] and a['expected_escalations']==row['escalations']),None)
        row['acknowledgement']=acknowledgement;row['acknowledged']=acknowledgement is not None and row['state']!='resolved'
    return dict(format='outlands-reliability-report-v1',case_id=case['case_id'],snapshots=len(case['snapshots']),incidents=rows,timeline=timeline,availability=availability(case),counts={state:sum(row['state']==state for row in rows) for state in ('active','monitoring','resolved')},observations_independently_verified=False,execution_performed=False,network_probed=False)
