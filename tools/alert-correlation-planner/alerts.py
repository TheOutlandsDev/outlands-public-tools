"""Group declared alerts in anchored inclusive windows without sending or suppressing any."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import health_core as r

SEVERITIES=('info','warning','critical')

def policy(value):
    _,out=c.record(value,{'id','revision','window'},('id',),('revision',));t.integer(value['window'],10**6);return out

def alert(row):
    key,out=c.record(row,{'id','component','component_revision','component_sha256','key','at','severity'},('id','component','key'),('component_revision',))
    t.sha(row['component_sha256']);t.integer(row['at']);t.require(row['severity'] in SEVERITIES,'SEVERITY_INVALID');return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','components','policy','alerts'});t.require(v['format']=='outlands-alert-correlation-v1','FORMAT_INVALID')
    rule=policy(v['policy']);counts={};issues=[];components=r.collect(v['components'],r.component,'components',counts,issues)
    alerts=r.collect(v['alerts'],alert,'alerts',counts,issues)
    for position,row in alerts.values():r.reference(row,'component',components,'alerts',position,issues)
    qualified=not issues;assessment=None
    if qualified:
        partitions=defaultdict(list)
        for _,row in alerts.values():partitions[(row['component'],row['key'])].append(row)
        groups=[]
        for (component,key),rows in sorted(partitions.items()):
            rows.sort(key=lambda row:(row['at'],row['id']));batches=[]
            for row in rows:
                if not batches or row['at']>batches[-1][0]['at']+rule['window']:batches.append([])
                batches[-1].append(row)
            for batch in batches:
                material=dict(policy_sha256=c.pin(rule),alerts=sorted(batch,key=lambda row:row['id']))
                groups.append(dict(group_sha256=c.pin(material),component=component,key=key,anchor_at=batch[0]['at'],window_end=batch[0]['at']+rule['window'],last_alert_at=batch[-1]['at'],
                    alert_ids=[row['id'] for row in batch],highest_declared_severity=max((row['severity'] for row in batch),key=SEVERITIES.index)))
        t.require(sum(len(row['alert_ids']) for row in groups)==len(alerts),'GROUP_ACCOUNTING_FAILED')
        assessment=dict(groups=groups,selected_alerts=len(alerts),grouped_alerts=sum(len(row['alert_ids']) for row in groups),suppressed_alerts=0)
    return r.output(raw,'outlands-alert-correlation-report-v1',counts,issues,qualified,assessment,dict(components=components,alerts=alerts),rule)

def main(argv=None):return c.cli('Plan declared alert groups; no sending, suppression or incident creation.',check,argv)
if __name__=='__main__':raise SystemExit(main())
