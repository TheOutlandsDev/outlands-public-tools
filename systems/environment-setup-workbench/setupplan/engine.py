"""Pure supplied-declaration evaluation and ordered nonexecuting setup plans."""
from . import contracts as c,runtime as r
from .vendor import configuration,connections

def evaluate(profile,observations):
    c.profile(profile);c.observations(observations)
    declared={row['id']:row for row in profile['prerequisites']}
    if set(observations['prerequisites'])-set(declared):c.fail('PREREQUISITE_UNDECLARED')
    rows=[]
    for row in profile['prerequisites']:
        observed=observations['prerequisites'].get(row['id'],'UNKNOWN')
        rows.append(dict(id='prerequisite:'+row['id'],status='PASS' if observed=='PRESENT' else observed,required=row['required'],evidence='OPERATOR_DECLARATION_ONLY'))
    config=c.vendor_call(configuration.check_configuration,profile['configuration'],observations['settings'])
    required={row['id']:row['required'] for row in profile['configuration']['fields']}
    for row in config['checks']:rows.append(dict(id='configuration:'+row['id'],status=row['status'],required=required.get(row['id'],True),evidence=row['evidence']))
    for row in profile['layout']:rows.append(dict(id='layout:'+row['id'],status='PASS' if row['path'] in observations['files'] else 'MISSING',required=True,evidence='EXACT_SUPPLIED_RELATIVE_NAME_ONLY'))
    connection=c.vendor_call(connections.check_plan,profile['connections'])
    for row in connection['checks']:rows.append(dict(id='connection:'+row['id'],status='PASS' if row['status']=='DISTINCT' else 'CONFLICT',required=True,evidence=row['evidence']))
    statuses={row['id']:row['status'] for row in rows};ordered=[];remaining=list(profile['steps']);finished={}
    while remaining:
        ready=[row for row in remaining if set(row['depends_on'])<=set(finished)]
        for row in ready:
            blockers=[ref for ref in row['checks'] if statuses[ref]!='PASS']
            waiting=[dep for dep in row['depends_on'] if finished[dep]!='READY_FOR_MANUAL_REVIEW']
            status='BLOCKED' if blockers or waiting else 'READY_FOR_MANUAL_REVIEW';finished[row['id']]=status
            ordered.append(dict(id=row['id'],label=row['label'],status=status,blocked_checks=blockers,blocked_steps=waiting,verification=row['verification'],verification_status='NOT_PERFORMED',depends_on=row['depends_on']))
        remaining=[row for row in remaining if row not in ready]
    def is_blocking(row):return row['status']!='PASS' and (row['required'] or (row['id'].startswith('configuration:') and row['status']!='NOT_SUPPLIED'))
    blocking=sum(is_blocking(row) for row in rows)+config['counts']['unexpected_settings']
    warnings=sum(row['status']!='PASS' and not is_blocking(row) for row in rows)
    summary=dict(checks=len(rows),blocking_checks=blocking,optional_unresolved=warnings,steps=len(ordered),blocked_steps=sum(row['status']=='BLOCKED' for row in ordered),unexpected_settings=config['counts']['unexpected_settings'])
    result=dict(format='outlands-setup-evaluation-v1',profile_sha256=r.digest(r.encode(profile)),observations_sha256=r.digest(r.encode(observations)),status='REVIEW_REQUIRED' if blocking or summary['blocked_steps'] else 'DECLARATIONS_SATISFIED',summary=summary,checks=rows,steps=ordered,plan_only=True,runtime_verified=False,network_probed=False,programs_executed=False,host_inventory_collected=False,configuration_modified=False)
    if len(r.encode(result))>c.MAX_REPORT:c.fail('REPORT_LIMIT')
    return result

def plan(evaluation,request):
    c.request('plan',request)
    return dict(format='outlands-reviewed-setup-plan-v1',evaluation_id=request['evaluation_id'],evaluation_sha256=request['evaluation_sha256'],profile_sha256=evaluation['profile_sha256'],observations_sha256=evaluation['observations_sha256'],status=evaluation['status'],summary=evaluation['summary'],steps=evaluation['steps'],review_assertions=request['checks'],plan_only=True,execution_authorized=False,runtime_verified=False,public_release_authorized=False)

def differences(first,second):
    """Return changed identifiers and digests, never arbitrary configuration values."""
    def list_diff(left,right,key):
        a={row[key]:row for row in left};b={row[key]:row for row in right}
        return dict(added=sorted(b.keys()-a.keys()),removed=sorted(a.keys()-b.keys()),changed=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k]),order_changed=list(a)!=list(b))
    if first['format']!=second['format']:c.fail('COMPARISON_KIND_MISMATCH')
    if first['format']=='outlands-setup-profile-v1':
        value={key:list_diff(first[key],second[key],'id') for key in ('prerequisites','layout','steps')}
        value['configuration_changed']=first['configuration']!=second['configuration'];value['connections_changed']=first['connections']!=second['connections'];value['label_changed']=first['label']!=second['label']
    else:
        value={key:list_diff(first[key],second[key],'id') for key in ('checks','steps')};value['status_changed']=first['status']!=second['status'];value['summary_changed']=first['summary']!=second['summary']
    return dict(first_sha256=r.digest(r.encode(first)),second_sha256=r.digest(r.encode(second)),same_bytes=r.encode(first)==r.encode(second),changes=value)
