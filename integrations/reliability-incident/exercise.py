"""Installed fictional health-to-recovery declarations; no collection or recovery."""
import copy
import hashlib
import json
from importlib.resources import files
from outlands_component_health_snapshot_checker.health import check as health
from outlands_incident_timeline_checker.incidents import check as timeline
from outlands_alert_correlation_planner.alerts import check as correlate
from outlands_recovery_readiness_planner.recovery import check as readiness

def raw(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sample(package):
    return json.loads(files(package).joinpath('examples','input.json').read_bytes())
def adapted(scope,health_report,timeline_report):
    scope=copy.deepcopy(scope)
    by_role={row['role']:row for row in scope['checks']}
    by_check={row['check']:row for row in scope['evidence']}
    for role,report,passed in [
        ('component-health',health_report,health_report['assessment']['all_declared_healthy_and_fresh']),
        ('incident-resolution',timeline_report,timeline_report['assessment']['incidents'][0]['resolved_as_of'])]:
        by_check[by_role[role]['id']].update(outcome='pass' if passed else 'fail',observed_at=scope['as_of'],artifact_sha256=hashlib.sha256(raw(report)).hexdigest())
    return readiness(raw(scope))

def main():
    h=sample('outlands_component_health_snapshot_checker');t=sample('outlands_incident_timeline_checker')
    a=sample('outlands_alert_correlation_planner');r=sample('outlands_recovery_readiness_planner')
    assert h['as_of']==t['as_of']==r['as_of']
    healthy=health(raw(h));resolved=timeline(raw(t));groups=correlate(raw(a))
    assert healthy['status']==resolved['status']==groups['status']=='PASS'
    for report in [resolved,groups]:assert report['components_sha256']==healthy['components_sha256']
    assert resolved['assessment']['incidents'][0]['resolved_as_of'] is True
    assert groups['assessment']['selected_alerts']==groups['assessment']['grouped_alerts']==3
    assert len(groups['assessment']['groups'])==2 and groups['assessment']['suppressed_alerts']==0
    assert groups['alerts_suppressed'] is False and groups['notifications_sent'] is False
    ready=adapted(r,healthy,resolved)
    assert ready['status']=='PASS' and ready['assessment']['incidents'][0]['ready_for_manual_recovery_review']
    assert ready['incidents_sha256']==resolved['incidents_sha256']
    open_input=copy.deepcopy(t);open_input['events']=open_input['events'][:-1]
    open_report=timeline(raw(open_input));assert open_report['status']=='PASS'
    assert open_report['assessment']['incidents'][0]['resolved_as_of'] is False
    blocked=adapted(r,healthy,open_report)
    assert blocked['status']=='REVIEW_REQUIRED' and not blocked['assessment']['incidents'][0]['ready_for_manual_recovery_review']
    boundary=copy.deepcopy(h);boundary['as_of']=boundary['observations'][0]['observed_at']+boundary['components'][0]['maximum_age']
    assert health(raw(boundary))['status']=='PASS'
    boundary['as_of']+=1;assert health(raw(boundary))['status']=='REVIEW_REQUIRED'
    missing=copy.deepcopy(r);missing['evidence']=[]
    assert readiness(raw(missing))['status']=='REVIEW_REQUIRED'
    stale=copy.deepcopy(a);stale['alerts'][0]['component_sha256']='0'*64
    withheld=correlate(raw(stale));assert withheld['status']=='REVIEW_REQUIRED' and withheld['assessment'] is None
    for report in [healthy,resolved,groups,ready,blocked]:
        assert report['actual_health_verified'] is False and report['recovery_authorized'] is False
        assert report['recovery_performed'] is False and report['records_changed'] is False
    print(json.dumps(dict(status='PASS',health='PASS',timeline='PASS',alert_groups=2,recovery='PASS',valid_unresolved_timeline='PASS',unresolved_recovery='REVIEW_REQUIRED',freshness_boundary='inclusive',stale_binding='assessment withheld'),sort_keys=True))

if __name__=='__main__':
    main()
