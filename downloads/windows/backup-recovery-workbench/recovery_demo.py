"""New-only fictional recovery exercise; never accepts an existing private instance."""
import hashlib
import shutil
from recovery import application as app, runtime as r


def tree(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def exercise(workspace):
    if workspace.exists():raise ValueError('EXERCISE_REQUIRES_NEW_INSTANCE')
    r.configure(workspace,create=True);r.initialize()
    source=workspace/'inbox/sample-files-v1'
    def run(fn,request):
        return fn(r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',
                               reason='Fictional portable recovery exercise',request=request)))
    first=run(app.snapshot,dict(source='inbox/sample-files-v1',exclusions=['cache'],quiescent=True))['job']['result']
    snapshot=workspace/'snapshots'/first['snapshot_id']
    before=tree(snapshot)
    original=(source/'data/sample.csv').read_bytes()
    if original!=b'item,count\nsample,3\n' or first['file_count']!=3 or first['total_bytes']!=39:
        raise ValueError('FICTIONAL_FIXTURE_MISMATCH')
    # Only this new disposable exercise's invented CSV changes. The core app never
    # writes source content. This scripted edit represents a change after backup.
    changed=b'item,count\nsample,9\n'
    (source/'data/sample.csv').write_bytes(changed)
    restored=run(app.restore,dict(snapshot_id=first['snapshot_id']))['job']['result']
    target=workspace/restored['target']/'files'
    if tree(target)!=tree(snapshot/'files') or (target/'data/sample.csv').read_bytes()!=original:
        raise ValueError('RESTORE_ORACLE_MISMATCH')
    if not (target/'empty-dir').is_dir():raise ValueError('EMPTY_DIRECTORY_MISSING')
    restored_before=tree(workspace/'restores')
    damaged=workspace/'inbox/damaged-snapshot'
    shutil.copytree(snapshot,damaged)
    (damaged/'files/empty.txt').write_bytes(b'fictional damage')
    refusal=None
    try:run(app.restore_imported,dict(source='inbox/damaged-snapshot',manifest_sha256=first['manifest_sha256']))
    except r.WorkbenchError as error:refusal=str(error)
    if refusal!='SNAPSHOT_CONTENT_MISMATCH':raise ValueError('DAMAGED_COPY_NOT_REFUSED')
    if tree(workspace/'restores')!=restored_before or tree(snapshot)!=before:
        raise ValueError('PRESERVATION_ORACLE_MISMATCH')
    if (source/'data/sample.csv').read_bytes()!=changed:raise ValueError('CHANGED_SOURCE_NOT_PRESERVED')
    run(app.verify,dict(snapshot_id=first['snapshot_id']))
    state=app.overview()
    if state['unfinished_jobs'] or state['jobs'][-2]['status']!='failed':raise ValueError('JOURNAL_ORACLE_MISMATCH')
    return dict(status='PASS',mode='FICTIONAL_RECOVERY_EXERCISE',files=3,bytes=39,
                original_csv_count=3,changed_source_csv_count=9,restored_csv_count=3,
                changed_source_preserved=True,original_snapshot_unchanged=True,
                restored_tree_unchanged_after_refusal=True,damaged_copy_error=refusal,
                damaged_copy_restore_created=False,failed_job_retained=True,
                empty_directory_preserved=True,deletion_performed=False,
                completed_jobs=3,failed_jobs=1)
