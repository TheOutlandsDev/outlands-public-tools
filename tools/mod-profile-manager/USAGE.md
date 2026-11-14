# Mod Profile Activation Manager 0.1.0 — executable fictional guide

This walkthrough creates invented orchard/meadow sources, imports copies, previews,
activates/switches/deactivates and verifies retained trees. It injects four
controlled API exceptions at documented fault hooks and recovers the resulting
owned workspace. These are synthetic interruption windows, not power loss or
actual games/mods. No game directory, save, external loader or Tk window is used.

## Prepare a new private run

Verify release checksums and extract the source ZIP to a fresh owned directory.
Use Python 3.12–3.15; formal guide proof uses a fresh no-pip Python 3.15.2 environment.
Copy only the six runtime/generator files to a separate module folder, preserving
the `examples` subdirectory. No Python package, admin, login or network is needed.
The guide exercises CLI/native filesystem behavior; native Tk has separate
required release evidence and is not inferred from this run.

Save the single Python block as `fictional_profile_walkthrough.py` outside source.
Choose an existing absolute private parent outside source and the copied runtime.
Each run creates a unique owned child and retains all its files, including an
8 MiB+1 byte authored refusal fixture. Never use `-O`, hand-edit valuable manager
metadata or run this experiment against an actual profile store. Replace these
fictional placeholder paths with the selected owned parent:

```powershell
$module = (Resolve-Path .).Path
$privateWork = 'D:\Private-Review'
python -I -B fictional_profile_walkthrough.py "$module" "$privateWork"
```

```sh
module="$PWD"
privateWork='/owned/private-review'
python3 -I -B fictional_profile_walkthrough.py "$module" "$privateWork"
```

The selected module must contain only `profile_manager.py`, `profile_engine.py`,
`profile_fs.py`, `profile_gui.py`, `inspection_support.py` and `examples/generate.py`.
Formal verification makes that byte-for-byte copy before executing this exact
block. The CLI/API helper children run `-E -s -B`; the driver runs isolated `-I -B`.

## What the assertions establish

The generator's four exact authored files remain unchanged. Expected profile
manifests/digests are computed independently from those fixture bytes and the
documented canonical JSON representation, without importing runtime verification
or matching logic. Full copies, directory layout, state, intents, lock byte,
history and retained trees are checked against independent expectations.

Random workspace/operation IDs are preserved in the private observation ledger.
Their lowercase-hex format, uniqueness and state/intent/history/directory relations
are checked rather than replaced with invented stable IDs. History is sorted by
actual ID, not interpreted as chronology. Read-only status/preview/no-change and
refusal cases retain complete file/tree byte snapshots. Imported sources and the
unrelated authored guard trees stay unchanged.

The flow deliberately changes only its own fictional active README to show drift
review/refusals, then restores its known authored bytes. Recovery is not used as
an overwrite/repair command. Controlled exceptions after intent, verified stage,
previous retention and active rename exercise conservative abort/resume behavior.
An absent stage aborts with its history retained; verified stages/retained trees
are checked before completion, including rename-before-journal windows.

The driver holds a real OS lock while a child must refuse the busy workspace;
it snapshots files before locking and after unlocking. Normal operations exercise
the native no-replace commits; an existing rename destination must also remain
untouched. These checks use only created fictional directories and do not prove
power-loss durability, full metadata preservation or arbitrary-host compatibility.

```python
"""Fictional managed-workspace operations only; no game, external installation or Tk."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

if not __debug__:raise RuntimeError('ASSERTIONS_REQUIRED')
module=Path(sys.argv[1]).resolve(strict=True);parent=Path(sys.argv[2]).resolve(strict=True)
assert parent.is_dir() and not parent.is_relative_to(module) and not module.is_relative_to(parent)
assert not parent.is_symlink() and not getattr(parent,'is_junction',lambda:False)()
work=Path(tempfile.mkdtemp(prefix='fictional-profile-manager-',dir=parent)).resolve();assert work.parent==parent
runtimes=('profile_manager.py','profile_engine.py','profile_fs.py','profile_gui.py','inspection_support.py','examples/generate.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
runtime_hashes={name:sha((module/name).read_bytes()) for name in runtimes}
fixtures={
 'orchard/README.txt':b'Fictional Orchard profile. This is not an installable game mod.\n',
 'orchard/config/demo.ini':b'[fictional]\ncolor=orange\nmode=orchard\n',
 'meadow/README.txt':b'Fictional Meadow profile. This is not an installable game mod.\n',
 'meadow/config/demo.ini':b'[fictional]\ncolor=green\nmode=meadow\n'}
sources=work/'sources';workspace=work/'managed';guards=work/'guards';guards.mkdir()
(guards/'empty').mkdir();(guards/'unsupported').mkdir();(guards/'oversized').mkdir()
(guards/'unsupported/bad^name.txt').write_bytes(b'Fictional unsupported portable name.\n')
(guards/'oversized/large.bin').write_bytes(b'X'*(8*1024*1024+1))
(guards/'rename-source').mkdir();(guards/'rename-destination').mkdir()
(guards/'rename-source/marker.txt').write_bytes(b'Fictional source retained.\n')
(guards/'rename-destination/marker.txt').write_bytes(b'Fictional destination retained.\n')

def inventory(root):
    rows={}
    if not root.exists():return rows
    for path in sorted(root.rglob('*')):
        info=path.lstat();assert not path.is_symlink() and not getattr(path,'is_junction',lambda:False)()
        name=path.relative_to(root).as_posix()
        if stat.S_ISDIR(info.st_mode):rows[name]=dict(kind='directory')
        else:
            assert stat.S_ISREG(info.st_mode)
            raw=path.read_bytes();rows[name]=dict(kind='file',bytes=len(raw),sha256=sha(raw))
    return rows

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()
def profile_files(name):return {key.split('/',1)[1]:raw for key,raw in fixtures.items() if key.startswith(name+'/')}
def expected_manifest(name):
    files=profile_files(name)
    body=dict(schema_version=1,directories=['config'],files=[dict(path=key,bytes=len(raw),sha256=sha(raw)) for key,raw in sorted(files.items())],total_bytes=sum(map(len,files.values())))
    return dict(body,digest=sha(canonical(body)))
manifests={name:expected_manifest(name) for name in ('orchard','meadow')}
checks=0;manifest_readbacks=0;payload_hashes_checked=0;retained_tree_readbacks=0;readonly_cases=0

def exact_tree(path,name):
    global payload_hashes_checked
    expected={'config':dict(kind='directory')}
    expected.update({key:dict(kind='file',bytes=len(raw),sha256=sha(raw)) for key,raw in profile_files(name).items()})
    assert path.is_dir() and inventory(path)==expected,(path,name)
    payload_hashes_checked+=len(profile_files(name))

operations={};owner_id=None;profiles=[]
def add_operation(label,token,action,profile,before,phase='complete',outcome='complete',previous=None,stage=None):
    assert re.fullmatch('[a-f0-9]{32}',token) and token not in {row['id'] for row in operations.values()} and label not in operations
    operations[label]=dict(id=token,action=action,profile=profile,before=before,phase=phase,outcome=outcome,previous=previous,stage=stage)
    return token
def history():return [dict(id=row['id'],action=row['action'],profile=row['profile'],phase=row['phase'],outcome=row['outcome']) for row in sorted(operations.values(),key=lambda row:row['id'])]
def status_value(active,pending=None,issues=()):
    return dict(status='REVIEW_REQUIRED' if issues else 'OK',active_profile=active,pending=pending,
      profiles=[dict(id=name,files=2,bytes=manifests[name]['total_bytes']) for name in sorted(profiles)],history=history(),issues=[dict(code=code) for code in issues])
def state_check(active,actual_tree=None,pending=None):
    global owner_id,checks,manifest_readbacks,retained_tree_readbacks
    owner=json.loads((workspace/'owner.json').read_bytes());assert set(owner)=={'schema_version','workspace_id'} and owner['schema_version']==1
    assert re.fullmatch('[a-f0-9]{32}',owner['workspace_id'])
    if owner_id is None:owner_id=owner['workspace_id']
    assert owner['workspace_id']==owner_id
    assert (workspace/'owner.json').read_bytes()==canonical(owner)
    assert (workspace/'state.json').read_bytes()==canonical(dict(schema_version=1,active_profile=active,pending=pending))
    assert (workspace/'.lock').read_bytes()==b'0'
    assert {p.name for p in workspace.iterdir()}=={'owner.json','state.json','.lock','profiles','operations'}|({'active'} if actual_tree else set())
    assert {p.name for p in (workspace/'profiles').iterdir()}==set(profiles)
    for name in profiles:
        folder=workspace/'profiles'/name
        assert {p.name for p in folder.iterdir()}=={'manifest.json','payload'}
        assert (folder/'manifest.json').read_bytes()==canonical(manifests[name]);manifest_readbacks+=1
        exact_tree(folder/'payload',name)
    assert {p.name for p in (workspace/'operations').iterdir()}=={row['id'] for row in operations.values()}
    for row in operations.values():
        folder=workspace/'operations'/row['id']
        expected={key:row[key] for key in ('id','action','profile','before','phase','outcome')};expected['schema_version']=1
        assert (folder/'intent.json').read_bytes()==canonical(expected)
        assert {p.name for p in folder.iterdir()}=={'intent.json'}|({'previous'} if row['previous'] else set())|({'stage'} if row['stage'] else set())
        if row['previous']:exact_tree(folder/'previous',row['previous']);retained_tree_readbacks+=1
        if row['stage']:exact_tree(folder/'stage',row['stage'])
    if actual_tree:exact_tree(workspace/'active',actual_tree)
    checks+=1

outcomes=[];observations=[]
def run_case(case,arguments,code,expected,*,readonly=False,script='profile_manager.py',operation=None,helper=None):
    global readonly_cases
    before=inventory(work) if readonly else None
    command=[sys.executable,'-E','-s','-B',*(['-c',helper] if helper else [str(module/script)]),*map(str,arguments)]
    result=subprocess.run(command,cwd=module,capture_output=True,timeout=30)
    assert result.returncode==code and not result.stderr,(case,result.returncode,result.stdout,result.stderr)
    value=json.loads(result.stdout)
    if operation:
        label,action,profile,old,active,previous=operation
        token=value.get('operation');add_operation(label,token,action,profile,old,previous=previous)
        expected=dict(status='OK',action=action,profile=profile,active_profile=active,pending=None,operation=token,outcome='complete')
    assert value==expected,(case,value,expected)
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    if readonly:assert inventory(work)==before,case;readonly_cases+=1
    outcomes.append(dict(case=case,exit_code=code));observations.append(dict(case=case,exit_code=code,result=value))
    return value
def cli(command,*args):return [command,'--workspace',workspace,*args]
def refusal(case,arguments,error):return run_case(case,arguments,2,dict(status='INCOMPLETE',error=error),readonly=True)
def plan_value(action,profile,active):
    return dict(status='OK',allowed=True,action=action,profile=profile,active_before=active,
      files=2 if profile else 0,bytes=manifests[profile]['total_bytes'] if profile else 0,
      source_copies_preserved=True,previous_active_retained=active is not None)

run_case('generate-fictional-sources',['--output',sources],0,dict(status='FICTIONAL_EXAMPLES_CREATED',profiles=2,files=4),script='examples/generate.py')
assert {p.relative_to(sources).as_posix():p.read_bytes() for p in sources.rglob('*') if p.is_file()}==fixtures
source_snapshot=inventory(sources);guard_snapshot=inventory(guards)
run_case('initialize-new-owned-workspace',cli('init'),0,dict(status='OK',active_profile=None,pending=None,profiles=[],history=[]));state_check(None)
run_case('read-empty-status-without-changing-files',cli('status'),0,status_value(None),readonly=True)
run_case('import-orchard-copy',cli('import-profile','--profile','orchard','--source',sources/'orchard'),0,None,operation=('import-orchard','import','orchard',None,None,None));profiles.append('orchard');state_check(None)
run_case('import-meadow-copy',cli('import-profile','--profile','meadow','--source',sources/'meadow'),0,None,operation=('import-meadow','import','meadow',None,None,None));profiles.append('meadow');state_check(None)
run_case('list-two-profiles-and-random-id-history',cli('list'),0,status_value(None),readonly=True)
run_case('preview-orchard-is-read-only',cli('plan','--action','activate','--profile','orchard'),0,plan_value('activate','orchard',None),readonly=True)
run_case('already-disabled-does-not-add-operation',cli('deactivate'),0,dict(status='OK',active_profile=None,pending=None,outcome='already_disabled'),readonly=True)
run_case('activate-orchard',cli('activate','--profile','orchard'),0,None,operation=('first-orchard','activate','orchard',None,'orchard',None));state_check('orchard','orchard')
run_case('already-active-does-not-add-operation',cli('activate','--profile','orchard'),0,dict(status='OK',active_profile='orchard',pending=None,outcome='already_active'),readonly=True)
run_case('preview-meadow-reserves-nothing',cli('plan','--action','activate','--profile','meadow'),0,plan_value('activate','meadow','orchard'),readonly=True)
run_case('switch-to-meadow-retains-orchard',cli('activate','--profile','meadow'),0,None,operation=('first-meadow','activate','meadow','orchard','meadow','orchard'));state_check('meadow','meadow')
run_case('preview-deactivation-is-read-only',cli('plan','--action','deactivate'),0,plan_value('deactivate',None,'meadow'),readonly=True)
run_case('deactivate-retains-meadow',cli('deactivate'),0,None,operation=('first-disable','deactivate',None,'meadow',None,'meadow'));state_check(None)
run_case('recovery-without-pending-work-is-read-only',cli('recover'),0,dict(status='OK',active_profile=None,pending=None,outcome='no_pending_operation'),readonly=True)
run_case('reactivate-imported-orchard',cli('activate','--profile','orchard'),0,None,operation=('second-orchard','activate','orchard',None,'orchard',None));state_check('orchard','orchard')

# Deliberately change only an authored active copy, then restore its known bytes.
active_readme=workspace/'active/README.txt';original=active_readme.read_bytes();active_readme.write_bytes(b'Fictional changed active copy.\n')
run_case('active-drift-is-review-not-overwrite',cli('status'),1,status_value('orchard',issues=('ACTIVE_TREE_MISMATCH',)),readonly=True)
refusal('refuse-switch-while-active-drifted',cli('activate','--profile','meadow'),'ACTIVE_TREE_MISMATCH')
refusal('refuse-deactivate-while-active-drifted',cli('deactivate'),'ACTIVE_TREE_MISMATCH')
refusal('refuse-recover-as-drift-repair',cli('recover'),'ACTIVE_TREE_MISMATCH')
active_readme.write_bytes(original);state_check('orchard','orchard')
run_case('restored-fictional-bytes-review-clean',cli('status'),0,status_value('orchard'),readonly=True)

hook_code="""import json,sys
import profile_engine as engine
class FictionalInterruption(Exception):pass
def stop(phase):
    if phase==sys.argv[3]:raise FictionalInterruption
try:engine.activate(sys.argv[1],sys.argv[2],fault_hook=stop)
except FictionalInterruption:print(json.dumps({'controlled_interruption':sys.argv[3]}))
else:raise AssertionError('INTERRUPTION_NOT_REACHED')
"""
def interrupt(case,label,profile,before,hook,phase,stage=None,previous=None):
    run_case(case,[workspace,profile,hook],0,dict(controlled_interruption=hook),helper=hook_code)
    token=json.loads((workspace/'state.json').read_bytes())['pending']
    add_operation(label,token,'activate',profile,before,phase=phase,outcome=None,stage=stage,previous=previous)
    return token
def recovered(label,active,outcome='complete'):
    row=operations[label];row.update(phase='complete' if outcome=='complete' else 'aborted',outcome=outcome,stage=None)
    return dict(status='OK',action='activate',profile=row['profile'],active_profile=active,pending=None,operation=row['id'],outcome=outcome)

token=interrupt('controlled-stop-after-intent','abort-intent','meadow','orchard','after_intent_written','intent')
state_check('orchard','orchard',token)
run_case('pending-intent-status-is-read-only',cli('status'),1,status_value('orchard',token,('PENDING_OPERATION',)),readonly=True)
refusal('pending-operation-blocks-another-activation',cli('activate','--profile','meadow'),'RECOVERY_REQUIRED')
run_case('recover-absent-stage-aborts-without-deleting-history',cli('recover'),0,recovered('abort-intent','orchard','aborted_incomplete_stage'));state_check('orchard','orchard')
token=interrupt('controlled-stop-after-stage-verification','recover-stage','meadow','orchard','after_stage_verified','intent',stage='meadow')
state_check('orchard','orchard',token)
operations['recover-stage']['previous']='orchard'
run_case('recover-verified-stage-retains-old-and-commits',cli('recover'),0,recovered('recover-stage','meadow'));state_check('meadow','meadow')
token=interrupt('controlled-stop-after-previous-retention','recover-retained','orchard','meadow','after_previous_retained','ready',stage='orchard',previous='meadow')
state_check('meadow',None,token)
run_case('retention-window-status-does-not-claim-clean-active',cli('status'),1,status_value('meadow',token,('PENDING_OPERATION','ACTIVE_TREE_MISMATCH')),readonly=True)
run_case('recover-retained-window-commits-verified-stage',cli('recover'),0,recovered('recover-retained','orchard'));state_check('orchard','orchard')
token=interrupt('controlled-stop-after-active-rename','recover-committed','meadow','orchard','after_active_committed','previous_retained',previous='orchard')
state_check('orchard','meadow',token)
run_case('recover-rename-before-journal-catches-up',cli('recover'),0,recovered('recover-committed','meadow'));state_check('meadow','meadow')
run_case('final-state-history-and-retained-copies',cli('status'),0,status_value('meadow'),readonly=True)

refusal('refuse-reused-profile-id',cli('import-profile','--profile','orchard','--source',sources/'orchard'),'PROFILE_EXISTS')
refusal('refuse-invalid-profile-id',cli('activate','--profile','Orchard'),'PROFILE_NAME_INVALID')
refusal('refuse-importing-workspace-as-source',cli('import-profile','--profile','nested','--source',workspace),'SOURCE_WORKSPACE_OVERLAP')
refusal('refuse-adopting-existing-workspace',cli('init'),'DESTINATION_EXISTS')
refusal('refuse-relative-workspace',['status','--workspace','relative-fictional-workspace'],'LOCAL_ABSOLUTE_PATH_REQUIRED')
refusal('refuse-empty-source-profile',cli('import-profile','--profile','empty','--source',guards/'empty'),'EMPTY_PROFILE_UNSUPPORTED')
refusal('refuse-nonportable-source-name',cli('import-profile','--profile','unsupported','--source',guards/'unsupported'),'RELATIVE_PATH_UNSUPPORTED')
refusal('refuse-source-file-byte-bound',cli('import-profile','--profile','oversized','--source',guards/'oversized'),'FILE_BYTE_LIMIT')
run_case('refuse-reusing-generator-output',['--output',sources],2,dict(status='INCOMPLETE',error='OUTPUT_EXISTS'),readonly=True,script='examples/generate.py')

# Hold the actual operating-system lock in this process; the child must refuse it.
lock_snapshot=inventory(work)
descriptor=os.open(workspace/'.lock',os.O_RDWR|getattr(os,'O_BINARY',0))
try:
    if os.name=='nt':
        import msvcrt
        os.lseek(descriptor,0,os.SEEK_SET);msvcrt.locking(descriptor,msvcrt.LK_NBLCK,1)
    else:
        import fcntl
        fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
    run_case('native-busy-lock-refuses-another-process',cli('status'),2,dict(status='INCOMPLETE',error='WORKSPACE_BUSY'))
finally:
    if os.name=='nt':os.lseek(descriptor,0,os.SEEK_SET);msvcrt.locking(descriptor,msvcrt.LK_UNLCK,1)
    else:fcntl.flock(descriptor,fcntl.LOCK_UN)
    os.close(descriptor)
assert inventory(work)==lock_snapshot
readonly_cases+=1
rename_code="""import json,sys
from profile_fs import ProfileError,rename_no_replace
try:rename_no_replace(sys.argv[1],sys.argv[2])
except ProfileError as error:
    print(json.dumps({'status':'INCOMPLETE','error':str(error)},sort_keys=True));raise SystemExit(2)
raise AssertionError('EXISTING_DESTINATION_WAS_NOT_REFUSED')
"""
run_case('existing-rename-destination-is-never-replaced',[guards/'rename-source',guards/'rename-destination'],2,
         dict(status='INCOMPLETE',error='DESTINATION_EXISTS'),readonly=True,helper=rename_code)
state_check('meadow','meadow')
assert inventory(sources)==source_snapshot and inventory(guards)==guard_snapshot
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,workspace_id=owner_id,operations=operations)
(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode())
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode())
assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,1,2)},
    readonly_cases=readonly_cases,managed_state_readbacks=checks,profile_manifest_readbacks=manifest_readbacks,
    payload_hashes_checked=payload_hashes_checked,retained_tree_readbacks=retained_tree_readbacks,
    controlled_fault_hooks=4,operation_records=len(operations),imported_profiles=2,source_files_preserved=4,
    artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,
    unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,
    fictional_workspace_flow_checked=True,native_lock_and_rename_checked=True,native_tk_widgets_checked=False,
    real_game_files_used=False,real_mod_profiles_used=False,game_integrations_verified=False,gameplay_verified=False,
    saves_accessed=False,external_game_directories_modified=False,power_loss_durability_verified=False,full_metadata_preservation_verified=False),sort_keys=True))
```

The ordered `outcomes` must equal the following. Exit 0 for a controlled fault
case means the requested synthetic interruption was observed; it does not mean
activation finished. Exit 1 requires review and exit 2 is a deliberate refusal.

```json
[
  {
    "case": "generate-fictional-sources",
    "exit_code": 0
  },
  {
    "case": "initialize-new-owned-workspace",
    "exit_code": 0
  },
  {
    "case": "read-empty-status-without-changing-files",
    "exit_code": 0
  },
  {
    "case": "import-orchard-copy",
    "exit_code": 0
  },
  {
    "case": "import-meadow-copy",
    "exit_code": 0
  },
  {
    "case": "list-two-profiles-and-random-id-history",
    "exit_code": 0
  },
  {
    "case": "preview-orchard-is-read-only",
    "exit_code": 0
  },
  {
    "case": "already-disabled-does-not-add-operation",
    "exit_code": 0
  },
  {
    "case": "activate-orchard",
    "exit_code": 0
  },
  {
    "case": "already-active-does-not-add-operation",
    "exit_code": 0
  },
  {
    "case": "preview-meadow-reserves-nothing",
    "exit_code": 0
  },
  {
    "case": "switch-to-meadow-retains-orchard",
    "exit_code": 0
  },
  {
    "case": "preview-deactivation-is-read-only",
    "exit_code": 0
  },
  {
    "case": "deactivate-retains-meadow",
    "exit_code": 0
  },
  {
    "case": "recovery-without-pending-work-is-read-only",
    "exit_code": 0
  },
  {
    "case": "reactivate-imported-orchard",
    "exit_code": 0
  },
  {
    "case": "active-drift-is-review-not-overwrite",
    "exit_code": 1
  },
  {
    "case": "refuse-switch-while-active-drifted",
    "exit_code": 2
  },
  {
    "case": "refuse-deactivate-while-active-drifted",
    "exit_code": 2
  },
  {
    "case": "refuse-recover-as-drift-repair",
    "exit_code": 2
  },
  {
    "case": "restored-fictional-bytes-review-clean",
    "exit_code": 0
  },
  {
    "case": "controlled-stop-after-intent",
    "exit_code": 0
  },
  {
    "case": "pending-intent-status-is-read-only",
    "exit_code": 1
  },
  {
    "case": "pending-operation-blocks-another-activation",
    "exit_code": 2
  },
  {
    "case": "recover-absent-stage-aborts-without-deleting-history",
    "exit_code": 0
  },
  {
    "case": "controlled-stop-after-stage-verification",
    "exit_code": 0
  },
  {
    "case": "recover-verified-stage-retains-old-and-commits",
    "exit_code": 0
  },
  {
    "case": "controlled-stop-after-previous-retention",
    "exit_code": 0
  },
  {
    "case": "retention-window-status-does-not-claim-clean-active",
    "exit_code": 1
  },
  {
    "case": "recover-retained-window-commits-verified-stage",
    "exit_code": 0
  },
  {
    "case": "controlled-stop-after-active-rename",
    "exit_code": 0
  },
  {
    "case": "recover-rename-before-journal-catches-up",
    "exit_code": 0
  },
  {
    "case": "final-state-history-and-retained-copies",
    "exit_code": 0
  },
  {
    "case": "refuse-reused-profile-id",
    "exit_code": 2
  },
  {
    "case": "refuse-invalid-profile-id",
    "exit_code": 2
  },
  {
    "case": "refuse-importing-workspace-as-source",
    "exit_code": 2
  },
  {
    "case": "refuse-adopting-existing-workspace",
    "exit_code": 2
  },
  {
    "case": "refuse-relative-workspace",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-source-profile",
    "exit_code": 2
  },
  {
    "case": "refuse-nonportable-source-name",
    "exit_code": 2
  },
  {
    "case": "refuse-source-file-byte-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-reusing-generator-output",
    "exit_code": 2
  },
  {
    "case": "native-busy-lock-refuses-another-process",
    "exit_code": 2
  },
  {
    "case": "existing-rename-destination-is-never-replaced",
    "exit_code": 2
  }
]
```

## Review retained artifacts and scope

Expected totals are 44 cases:26 exit0,3 review,15 refusal. The walkthrough checks
28 read-only/refusal snapshots,17 managed-state readbacks,31 profile-manifest
readbacks,168 payload hashes and39 retained-tree readbacks. Ten operation records
retain their actual IDs, including one aborted intent and five previous active
trees; two imported profiles and all four source files remain intact. Four API
fault hooks are synthetic, separately identified observations.

`OBSERVATIONS.json` contains only these fictional results/IDs. `GUIDE-MANIFEST.json`
binds forty payload files by bytes/SHA-256, making41 total workspace files. The
formal verifier independently checks that ledger, every payload hash, metadata
relationship and exact file inventory, plus all25 selected source hashes. Hashes
show byte consistency rather than authenticity, game safety, rights or correctness.

The guide's `fictional_workspace_flow_checked` and `native_lock_and_rename_checked`
are true. Its `native_tk_widgets_checked` is false because no GUI is invoked;
accepted native widget tests/display/Tcl/Tk measurements are separate. All eight
exclusions remain false:real game files/profiles used, game integrations/gameplay
verified, saves accessed, external game directories modified, power-loss durability
verified and full metadata preservation verified. No actual game/mod or save is
an input to qualification.

Keep the workspace private. Its names, relative paths, hashes and random IDs are
identifying metadata; omission of absolute paths is not anonymization. Do not
delete pending/staged/previous data to suppress a refusal. Retention is not an
independent backup or automatic purge. Flush/readback/native rename do not make
a universal rollback transaction or a sandbox against hostile concurrent writers.
Read [README.md](README.md), [FORMAT.md](docs/FORMAT.md) and [SECURITY.md](SECURITY.md)
before any separate decision to manage valuable content.
