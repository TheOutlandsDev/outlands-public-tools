"""Pure pinned candidate descriptors, limited lock differences and manual update plans."""
from . import contracts as c,runtime as r
from .vendor import lock_diff

def candidate(request):
    c.request('candidate',request);lock=request['dependency_lock']
    return dict(format='outlands-release-candidate-v1',label=request['label'],manifest_sha256=request['manifest_sha256'],inventory=c.inventory(request['manifest']),dependency_lock=None if lock is None else dict(path=lock['path'],sha256=r.digest(lock['text'].encode()),records=c.vendor_call(lock_diff.parse_lock,lock['text'].encode())),launcher=request['launcher'],launcher_sha256=r.digest(r.encode(request['launcher'])),files=len(request['manifest']['inventory']),payload_bytes=sum(row['size'] for row in request['manifest']['inventory']),runtime_verified=False)

def compare(baseline,candidate_value,request,old_request,new_request):
    c.request('comparison',request);left={row['path']:row for row in baseline['inventory']};right={row['path']:row for row in candidate_value['inventory']};rows=[];counts={name:0 for name in ('ADD','REMOVE','REPLACE','UNCHANGED')}
    for path in sorted(left.keys()|right.keys()):
        old=left.get(path);new=right.get(path);action='ADD' if old is None else 'REMOVE' if new is None else 'UNCHANGED' if old==new else 'REPLACE';counts[action]+=1;rows.append(dict(path=path,action=action,before=old,after=new))
    old_lock=old_request['dependency_lock'];new_lock=new_request['dependency_lock']
    if old_lock is not None and new_lock is not None:lock=c.vendor_call(lock_diff.compare_locks,old_lock['text'].encode(),new_lock['text'].encode());dependency_changed=lock['status']!='MATCHING_LOCK_RECORDS' or old_lock['path']!=new_lock['path']
    else:lock=dict(status='NO_LOCKS_DECLARED' if old_lock is new_lock is None else 'LOCK_DECLARATION_ADDED_OR_REMOVED',dependencies_resolved=False,artifacts_verified=False);dependency_changed=old_lock!=new_lock
    policy=request['policy'];blockers=[]
    for key,code in (('backup_confirmed','BACKUP_ASSERTION_REQUIRED'),('target_stopped_confirmed','STOPPED_ASSERTION_REQUIRED'),('readiness_confirmed','READINESS_ASSERTION_REQUIRED')):
        if not policy[key]:blockers.append(code)
    if counts['REMOVE'] and not policy['allow_removals']:blockers.append('REMOVALS_REQUIRE_REVIEW')
    if dependency_changed and not policy['dependency_reviewed']:blockers.append('DEPENDENCY_REVIEW_REQUIRED')
    def prefixes(paths):return {prefix.casefold():prefix for path in paths for i in range(1,len(path.split('/'))+1) for prefix in ['/'.join(path.split('/')[:i])]}
    left_prefixes=prefixes(left);right_prefixes=prefixes(right)
    if any(left_prefixes[key]!=right_prefixes[key] for key in left_prefixes.keys()&right_prefixes.keys()):blockers.append('CASE_ONLY_LAYOUT_CHANGE')
    for a in left:
        for b in right:
            if a.casefold().startswith(b.casefold()+'/') or b.casefold().startswith(a.casefold()+'/'):blockers.append('FILE_DIRECTORY_LAYOUT_CHANGE')
    blockers=sorted(set(blockers));value=dict(format='outlands-release-comparison-v1',baseline_id=request['baseline_id'],baseline_sha256=request['baseline_sha256'],candidate_id=request['candidate_id'],candidate_sha256=request['candidate_sha256'],counts=counts,files=rows,dependency_lock=lock,dependency_changed=dependency_changed,launcher_changed=baseline['launcher_sha256']!=candidate_value['launcher_sha256'],policy=policy,blockers=blockers,status='REVIEW_REQUIRED' if blockers else 'READY_FOR_MANUAL_REVIEW',target_updates_performed=False,target_state_verified=False,network_probed=False,programs_executed=False)
    if len(r.encode(value))>c.MAX_REPORT:c.fail('REPORT_LIMIT')
    return value

def plan(comparison,request):
    c.request('plan',request)
    return dict(format='outlands-release-update-plan-v1',comparison_id=request['comparison_id'],comparison_sha256=request['comparison_sha256'],baseline_id=comparison['baseline_id'],baseline_sha256=comparison['baseline_sha256'],candidate_id=comparison['candidate_id'],candidate_sha256=comparison['candidate_sha256'],status=comparison['status'],counts=comparison['counts'],blockers=comparison['blockers'],steps=[dict(id=identifier,checkpoint=text,status='NOT_PERFORMED') for identifier,text in [('review','Independently review the pinned snapshots, differences and scope.'),('backup','Independently verify a stopped consistent target, readiness and recoverable private backup.'),('update','Use a separately reviewed process for any target change; this workbench cannot apply updates.'),('acceptance','Perform actual application and runtime acceptance independently.'),('recovery','If needed, restore a verified backup into a fresh directory and review it before switching.')]],rollback=dict(baseline_paths=[row['path'] for row in comparison['files'] if row['before'] is not None],candidate_only_paths=[row['path'] for row in comparison['files'] if row['before'] is None],backup_independently_verified=False,restore_performed=False),plan_only=True,execution_authorized=False,public_release_authorized=False,runtime_verified=False)
