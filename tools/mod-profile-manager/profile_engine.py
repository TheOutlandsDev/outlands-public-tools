"""Original MIT managed mod-profile workspace; retained copies, no game deployment."""
from __future__ import annotations
import os
from pathlib import Path
import re
import stat
import sys
import uuid
import profile_fs as fs
from profile_fs import ProfileError

MAX_PROFILES = 32
MAX_OPERATIONS = 250
MAX_FILES = fs.MAX_FILES
MAX_FILE_BYTES = fs.MAX_FILE_BYTES
MAX_TOTAL_BYTES = fs.MAX_TOTAL_BYTES
MAX_PATH = fs.MAX_PATH
SLUG = re.compile(r'[a-z][a-z0-9-]{0,39}')
TOKEN = re.compile(r'[0-9a-f]{32}')
PHASES = {'intent','ready','previous_retained','active_committed','state_saved','complete','aborted'}
TERMINAL = {'complete','aborted'}
PREPARATION = 'retained_preparation'


def require(condition, code): fs.require(condition, code)


def slug(value):
    require(type(value) is str and SLUG.fullmatch(value), 'PROFILE_NAME_INVALID');return value


def _entries(path, allowed=None, tokens=False, temps=False):
    fs.checked_directory(path);names=set();count=0
    for child in path.iterdir():
        count+=1;require(count<=MAX_OPERATIONS+10,'WORKSPACE_ENTRY_LIMIT')
        fs.guard_links(child)
        if temps and re.fullmatch(r'\.tmp-[0-9a-f]{32}',child.name):
            require(fs.regular_info(child).st_size<=fs.MAX_JSON,'METADATA_SIZE_LIMIT');continue
        if allowed is not None:require(child.name in allowed,'UNEXPECTED_WORKSPACE_ENTRY')
        if tokens:require(bool(TOKEN.fullmatch(child.name)),'OPERATION_NAME_INVALID')
        names.add(child.name)
        limit=len(allowed) if allowed is not None else MAX_OPERATIONS if tokens else MAX_PROFILES
        require(len(names)<=limit,'WORKSPACE_ENTRY_LIMIT')
    return names


def _validate_state(value):
    require(type(value) is dict and set(value)=={'schema_version','active_profile','pending'},'STATE_INVALID')
    require(type(value['schema_version']) is int and value['schema_version']==1,'STATE_INVALID')
    if value['active_profile'] is not None:slug(value['active_profile'])
    require(value['pending'] is None or type(value['pending']) is str and TOKEN.fullmatch(value['pending']),'STATE_INVALID')
    return value


def _validate_intent(value, token):
    require(type(value) is dict and set(value)=={'schema_version','id','action','profile','before','phase','outcome'},'INTENT_INVALID')
    require(type(value['schema_version']) is int and value['schema_version']==1 and value['id']==token,'INTENT_INVALID')
    require(type(value['action']) is str and value['action'] in {'import','activate','deactivate'}
            and type(value['phase']) is str and value['phase'] in PHASES,'INTENT_INVALID')
    require(value['outcome'] is None or type(value['outcome']) is str
            and value['outcome'] in {'complete','aborted_incomplete_stage'},'INTENT_INVALID')
    if value['before'] is not None:slug(value['before'])
    if value['action'] in {'import','activate'}:slug(value['profile'])
    else:require(value['profile'] is None,'INTENT_INVALID')
    require((value['phase']=='complete')==(value['outcome']=='complete'),'INTENT_INVALID')
    require((value['phase']=='aborted')==(value['outcome']=='aborted_incomplete_stage'),'INTENT_INVALID')
    return value


def _profile(root, profile):
    folder=root/'profiles'/slug(profile)
    require(folder.exists(),'PROFILE_NOT_FOUND')
    require(_entries(folder,{'manifest.json','payload'})=={'manifest.json','payload'},'PROFILE_LAYOUT_INVALID')
    fs.checked_directory(folder/'payload')
    return fs.validate_manifest(fs.read_json(folder/'manifest.json'))


def _load(root):
    names=_entries(root,{'owner.json','state.json','.lock','profiles','operations','active'},temps=True)
    require({'owner.json','state.json','.lock','profiles','operations'}<=names,'WORKSPACE_LAYOUT_INVALID')
    owner=fs.read_json(root/'owner.json')
    require(type(owner) is dict and set(owner)=={'schema_version','workspace_id'}
            and type(owner['schema_version']) is int and owner['schema_version']==1
            and type(owner['workspace_id']) is str and TOKEN.fullmatch(owner['workspace_id']),'OWNER_INVALID')
    state=_validate_state(fs.read_json(root/'state.json'))
    profile_names=_entries(root/'profiles')
    require(len(profile_names)<=MAX_PROFILES,'PROFILE_COUNT_LIMIT')
    profiles={}
    for name in sorted(profile_names):profiles[slug(name)]=_profile(root,name)
    if state['active_profile'] is not None:require(state['active_profile'] in profiles,'STATE_PROFILE_MISSING')
    operations={};operation_names=_entries(root/'operations',tokens=True)
    require(len(operation_names)<=MAX_OPERATIONS,'OPERATION_COUNT_LIMIT')
    for token in sorted(operation_names):
        folder=root/'operations'/token
        found=_entries(folder,{'intent.json','stage','previous'},temps=True)
        if 'intent.json' not in found:
            # mkdir and metadata creation are separate operations. A process can
            # stop before the first durable intent; retain only that strictly
            # empty/temp-only preparation, never an unexplained managed tree.
            require(state['pending']!=token,'PENDING_INTENT_MISSING')
            require(not found,'OPERATION_INTENT_MISSING')
            operations[token]={'id':token,'action':'preparation','profile':None,
                               'before':None,'phase':PREPARATION,'outcome':PREPARATION}
            continue
        for tree in ('stage','previous'):
            if tree in found:fs.checked_directory(folder/tree)
        operations[token]=_validate_intent(fs.read_json(folder/'intent.json'),token)
    if state['pending'] is not None:require(state['pending'] in operations,'PENDING_INTENT_MISSING')
    unfinished=[token for token,row in operations.items() if row['phase'] not in TERMINAL|{PREPARATION}]
    require(len(unfinished)<=1,'MULTIPLE_PENDING_OPERATIONS')
    if unfinished and state['pending'] is not None:require(unfinished==[state['pending']],'PENDING_STATE_INCONSISTENT')
    pending=state['pending'] or (unfinished[0] if unfinished else None)
    if pending is not None:
        intent=operations[pending]
        # State may still name the old tree, or already name the committed tree
        # before the intent/pending metadata catches up. No unrelated profile
        # is legitimate in either interruption window.
        allowed={intent['before']}
        if intent['action']=='activate':allowed.add(intent['profile'])
        if intent['action']=='deactivate':allowed.add(None)
        # _finish saves the resulting state before writing a terminal intent.
        # Therefore a terminal intent cannot legitimately retain the old state.
        if intent['phase'] in TERMINAL:
            result=intent['before']
            if intent['outcome']=='complete' and intent['action']=='activate':result=intent['profile']
            if intent['outcome']=='complete' and intent['action']=='deactivate':result=None
            allowed={result}
        require(state['active_profile'] in allowed,'PENDING_STATE_INCONSISTENT')
    return state,profiles,operations,pending


def _current(root,state,profiles):
    active=root/'active';profile=state['active_profile']
    if profile is None:require(not active.exists() and not active.is_symlink(),'ACTIVE_TREE_MISMATCH')
    else:
        try:fs.verify_tree(active,profiles[profile])
        except (ProfileError,OSError):raise ProfileError('ACTIVE_TREE_MISMATCH') from None


def _hook(callback, phase):
    if callback is not None:callback(phase)


def _set_intent(root,intent,phase,outcome=None):
    intent=dict(intent,phase=phase,outcome=outcome)
    fs.save_json(root/'operations'/intent['id']/'intent.json',intent)
    return intent


def _begin(root,state,operations,action,profile):
    require(len(operations)<MAX_OPERATIONS,'OPERATION_COUNT_LIMIT')
    token=uuid.uuid4().hex;folder=fs.fresh_directory(root/'operations'/token)
    intent={'schema_version':1,'id':token,'action':action,'profile':profile,
            'before':state['active_profile'],'phase':'intent','outcome':None}
    fs.save_json(folder/'intent.json',intent)
    fs.save_json(root/'state.json',dict(state,pending=token))
    return intent


def _finish(root,state,intent,active,outcome='complete',hook=None):
    fs.save_json(root/'state.json',dict(state,active_profile=active,pending=intent['id']))
    _hook(hook,'after_state_saved')
    intent=_set_intent(root,intent,'complete' if outcome=='complete' else 'aborted',outcome)
    fs.save_json(root/'state.json',dict(state,active_profile=active,pending=None))
    return {'status':'OK','action':intent['action'],'profile':intent['profile'],
            'active_profile':active,'pending':None,'operation':intent['id'],'outcome':outcome}


def _partial_stage(path,manifest):
    """Recognize bounded expected-name partial copies; never deploy partial bytes."""
    actual=fs.scan_tree(path)
    require(set(actual['directories'])<=set(manifest['directories']),'STAGE_DRIFT')
    expected={row['path']:row for row in manifest['files']}
    for row in actual['files']:
        require(row['path'] in expected and row['bytes']<=expected[row['path']]['bytes'],'STAGE_DRIFT')
        if row['bytes']==expected[row['path']]['bytes']:
            require(row==expected[row['path']],'STAGE_DRIFT')
    return actual==manifest


def initialize(workspace):
    require(os.name=='nt' or sys.platform.startswith('linux'),'PLATFORM_UNSUPPORTED')
    path=fs.safe_path(workspace);parent=fs.checked_directory(path.parent)
    path=parent/path.name;fs.fresh_directory(path)
    fs.write_new(path/'.lock',b'0')
    with fs.lock_workspace(path) as root:
        fs.fresh_directory(root/'profiles');fs.fresh_directory(root/'operations')
        fs.save_json(root/'owner.json',{'schema_version':1,'workspace_id':uuid.uuid4().hex})
        fs.save_json(root/'state.json',{'schema_version':1,'active_profile':None,'pending':None})
    return {'status':'OK','active_profile':None,'pending':None,'profiles':[],'history':[]}


def status(workspace):
    with fs.lock_workspace(workspace) as root:
        state,profiles,operations,pending=_load(root);issues=[]
        if pending is not None:issues.append({'code':'PENDING_OPERATION'})
        if any(row['phase']==PREPARATION for row in operations.values()):
            issues.append({'code':'RETAINED_PREPARATION'})
        try:_current(root,state,profiles)
        except ProfileError as error:issues.append({'code':str(error)})
        return {'status':'REVIEW_REQUIRED' if issues else 'OK','active_profile':state['active_profile'],
                'pending':pending,'profiles':[{'id':name,'files':len(value['files']),'bytes':value['total_bytes']}
                    for name,value in sorted(profiles.items())],
                'history':[{'id':token,**{key:row[key] for key in ['action','profile','phase','outcome']}}
                    for token,row in sorted(operations.items())], 'issues':issues}


def _plan_locked(root,state,profiles,operations,pending,action,profile=None):
    require(pending is None,'RECOVERY_REQUIRED');_current(root,state,profiles)
    require(type(action) is str and action in {'activate','deactivate'},'ACTION_INVALID')
    require(len(operations)<MAX_OPERATIONS,'OPERATION_COUNT_LIMIT')
    manifest=None
    if action=='activate':
        profile=slug(profile);require(profile in profiles,'PROFILE_NOT_FOUND');manifest=profiles[profile]
        fs.verify_tree(root/'profiles'/profile/'payload',manifest)
    else:require(profile is None,'PROFILE_NOT_APPLICABLE')
    return {'status':'OK','allowed':True,'action':action,'profile':profile,
            'active_before':state['active_profile'],'files':len(manifest['files']) if manifest else 0,
            'bytes':manifest['total_bytes'] if manifest else 0,
            'source_copies_preserved':True,'previous_active_retained':state['active_profile'] is not None}


def plan(workspace,action,profile=None):
    with fs.lock_workspace(workspace) as root:return _plan_locked(root,*_load(root),action,profile)


def import_profile(workspace,profile,source):
    profile=slug(profile);source=fs.checked_directory(source)
    with fs.lock_workspace(workspace) as root:
        require(not source.is_relative_to(root) and not root.is_relative_to(source),'SOURCE_WORKSPACE_OVERLAP')
        state,profiles,operations,pending=_load(root)
        require(pending is None,'RECOVERY_REQUIRED');_current(root,state,profiles)
        require(profile not in profiles,'PROFILE_EXISTS');require(len(profiles)<MAX_PROFILES,'PROFILE_COUNT_LIMIT')
        manifest=fs.scan_tree(source);require(bool(manifest['files']),'EMPTY_PROFILE_UNSUPPORTED')
        require(len(fs.json_bytes(manifest))<=fs.MAX_JSON,'METADATA_BYTE_LIMIT')
        intent=_begin(root,state,operations,'import',profile);folder=root/'operations'/intent['id']
        stage=fs.fresh_directory(folder/'stage');fs.save_json(stage/'manifest.json',manifest)
        fs.copy_tree(source,stage/'payload',manifest);intent=_set_intent(root,intent,'ready')
        fs.rename_no_replace(stage,root/'profiles'/profile)
        return _finish(root,state,intent,state['active_profile'])


def _advance_activation(root,state,profiles,intent,hook=None):
    folder=root/'operations'/intent['id'];stage=folder/'stage';previous=folder/'previous';active=root/'active'
    before=intent['before'];after=intent['profile'];candidate=profiles[after]
    if previous.exists():
        require(before is not None,'RECOVERY_LAYOUT_CONFLICT');fs.verify_tree(previous,profiles[before])
    if active.exists():
        if stage.exists():
            require(not previous.exists() and before is not None,'RECOVERY_LAYOUT_CONFLICT')
            fs.verify_tree(active,profiles[before]);fs.verify_tree(stage,candidate)
            fs.rename_no_replace(active,previous);_hook(hook,'after_previous_retained')
            intent=_set_intent(root,intent,'previous_retained')
        else:
            require(before is None or previous.exists(),'RETAINED_TREE_MISSING')
            fs.verify_tree(active,candidate)
            return _finish(root,state,intent,after,hook=hook)
    else:
        require(before is None or previous.exists(),'RETAINED_TREE_MISSING')
    require(stage.exists(),'STAGE_MISSING');fs.verify_tree(stage,candidate)
    fs.rename_no_replace(stage,active);_hook(hook,'after_active_committed')
    intent=_set_intent(root,intent,'active_committed')
    return _finish(root,state,intent,after,hook=hook)


def activate(workspace,profile,fault_hook=None):
    profile=slug(profile)
    with fs.lock_workspace(workspace) as root:
        state,profiles,operations,pending=_load(root)
        _plan_locked(root,state,profiles,operations,pending,'activate',profile)
        if state['active_profile']==profile:return {'status':'OK','active_profile':profile,'pending':None,'outcome':'already_active'}
        intent=_begin(root,state,operations,'activate',profile);_hook(fault_hook,'after_intent_written')
        fs.copy_tree(root/'profiles'/profile/'payload',root/'operations'/intent['id']/'stage',profiles[profile])
        _hook(fault_hook,'after_stage_verified');intent=_set_intent(root,intent,'ready')
        return _advance_activation(root,state,profiles,intent,fault_hook)


def _advance_deactivation(root,state,profiles,intent,hook=None):
    folder=root/'operations'/intent['id'];active=root/'active';previous=folder/'previous'
    before=intent['before'];require(before is not None and before in profiles,'INTENT_PROFILE_MISSING')
    require(not (folder/'stage').exists(),'RECOVERY_LAYOUT_CONFLICT')
    if active.exists():
        require(not previous.exists(),'RECOVERY_LAYOUT_CONFLICT');fs.verify_tree(active,profiles[before])
        fs.rename_no_replace(active,previous);_hook(hook,'after_previous_retained')
        intent=_set_intent(root,intent,'previous_retained')
    require(previous.exists(),'RETAINED_TREE_MISSING');fs.verify_tree(previous,profiles[before])
    return _finish(root,state,intent,None,hook=hook)


def deactivate(workspace,fault_hook=None):
    with fs.lock_workspace(workspace) as root:
        state,profiles,operations,pending=_load(root)
        _plan_locked(root,state,profiles,operations,pending,'deactivate')
        if state['active_profile'] is None:return {'status':'OK','active_profile':None,'pending':None,'outcome':'already_disabled'}
        intent=_begin(root,state,operations,'deactivate',None);_hook(fault_hook,'after_intent_written')
        return _advance_deactivation(root,state,profiles,intent,fault_hook)


def recover(workspace,fault_hook=None):
    with fs.lock_workspace(workspace) as root:
        state,profiles,operations,pending=_load(root)
        if pending is None:
            _current(root,state,profiles)
            return {'status':'OK','active_profile':state['active_profile'],'pending':None,'outcome':'no_pending_operation'}
        intent=operations[pending];folder=root/'operations'/pending
        if intent['phase'] in TERMINAL:
            _current(root,state,profiles);fs.save_json(root/'state.json',dict(state,pending=None))
            return {'status':'OK','active_profile':state['active_profile'],'pending':None,'outcome':intent['outcome']}
        if intent['before'] is not None:require(intent['before'] in profiles,'INTENT_PROFILE_MISSING')
        if intent['action']=='import':
            _current(root,dict(state,active_profile=intent['before']),profiles)
            stage=folder/'stage';destination=root/'profiles'/intent['profile']
            require(not (folder/'previous').exists(),'RECOVERY_LAYOUT_CONFLICT')
            if destination.exists():
                require(not stage.exists(),'RECOVERY_LAYOUT_CONFLICT');manifest=_profile(root,intent['profile'])
                fs.verify_tree(destination/'payload',manifest)
                return _finish(root,state,intent,intent['before'],hook=fault_hook)
            if not stage.exists():return _finish(root,state,intent,intent['before'],'aborted_incomplete_stage',fault_hook)
            names=_entries(stage,{'manifest.json','payload'},temps=True)
            if not names:return _finish(root,state,intent,intent['before'],'aborted_incomplete_stage',fault_hook)
            require('manifest.json' in names,'STAGE_DRIFT')
            manifest=fs.validate_manifest(fs.read_json(stage/'manifest.json'))
            complete='payload' in names and _partial_stage(stage/'payload',manifest)
            if not complete:return _finish(root,state,intent,intent['before'],'aborted_incomplete_stage',fault_hook)
            fs.rename_no_replace(stage,destination)
            return _finish(root,state,intent,intent['before'],hook=fault_hook)
        if intent['action']=='deactivate':return _advance_deactivation(root,state,profiles,intent,fault_hook)
        require(intent['profile'] in profiles,'INTENT_PROFILE_MISSING')
        stage=folder/'stage';previous=folder/'previous'
        if not previous.exists():
            # Before retention, an absent/partial stage can be safely abandoned.
            original_ok=False
            try:_current(root,dict(state,active_profile=intent['before']),profiles);original_ok=True
            except (ProfileError,OSError):pass
            if original_ok and (not stage.exists() or not _partial_stage(stage,profiles[intent['profile']])):
                return _finish(root,state,intent,intent['before'],'aborted_incomplete_stage',fault_hook)
        return _advance_activation(root,state,profiles,intent,fault_hook)
