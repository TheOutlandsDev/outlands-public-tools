"""Publish immutable matching builds after fresh Windows update-plan acceptance."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile
from build import ROOT,TAG,FILENAME,PREFIX,encoded,git,payload,sha

OWNER='TheOutlandsDev/outlands-public-tools'
CAPTURES={'update-blocked.jpg','update-approved.jpg','update-new-plan.jpg','update-revoked.jpg'}


def publish(artifacts):
    assert os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_REPOSITORY')==OWNER
    head=git('rev-parse','HEAD').decode().strip()
    assert {p.name for p in artifacts.iterdir()}=={'update-portable-Windows','update-portable-Linux'}
    windows=artifacts/'update-portable-Windows';linux=artifacts/'update-portable-Linux'
    common={FILENAME,'release-receipt.json','SHA256SUMS.txt'};all_assets=common|{'acceptance.json'}|CAPTURES
    assert {p.name for p in windows.iterdir()}==all_assets and {p.name for p in linux.iterdir()}==common
    for name in common:assert (windows/name).read_bytes()==(linux/name).read_bytes()
    receipt=json.loads((windows/'release-receipt.json').read_bytes())
    assert receipt['packaging_source']==head and receipt['tag']==TAG and receipt['sha256']==sha((windows/FILENAME).read_bytes())
    accepted=json.loads((windows/'acceptance.json').read_bytes())
    assert accepted['status']=='PASS' and accepted['browser'] is True and accepted['core_tests']==55 and accepted['core_skips']==1
    assert accepted['package_sha256']==receipt['sha256'] and accepted['packaging_source']==head and len(accepted['checks'])==16
    assert accepted['app_source']==receipt['app_source'] and accepted['runtime']==receipt['runtime_version']
    exercise=accepted['exercise'];browser=accepted['browser_update']
    assert exercise['status']=='PASS' and exercise['command_checks']==34
    for result in (exercise,browser):
        assert [result[k] for k in ('snapshots','files_per_snapshot','blockers_before','blockers_after','private_handoff_files')]==[2,4,5,0,8]
        assert result['file_counts']==dict(ADD=1,REMOVE=1,REPLACE=2,UNCHANGED=1) and result['lock_version_text_changes']==1
        assert result['manual_checkpoints']=='NOT_PERFORMED'
        assert all(result[k] is True for k in ('blocked_approval_refused','unapproved_export_refused','revoked_export_refused','input_bytes_unchanged','copied_snapshots_unchanged','fictional_target_unchanged'))
        assert all(result[k] is False for k in ('new_plan_inherits_approval','target_updates_performed','programs_executed','network_probed','rollback_restore_performed'))
    assert browser['handoff_hashes_independently_verified'] and browser['previous_handoff_retained']
    assert set(accepted['captures'])==CAPTURES
    for name,row in accepted['captures'].items():assert row['bytes']==(windows/name).stat().st_size and row['sha256']==sha((windows/name).read_bytes())
    files=payload()
    files['PACKAGE-MANIFEST.json']=encoded(dict(schema=1,package_version='0.1.0-windows.1',app_source=receipt['app_source'],packaging_source=head,runtime=receipt['runtime_version'],files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())]))
    with zipfile.ZipFile(windows/FILENAME) as archive:
        assert len(archive.namelist())==len(files) and set(archive.namelist())=={PREFIX+n for n in files}
        for name,body in files.items():assert archive.read(PREFIX+name)==body
    (windows/'SHA256SUMS.txt').write_text(''.join(sha((windows/n).read_bytes())+'  '+n+'\n' for n in sorted(all_assets-{'SHA256SUMS.txt'})),encoding='utf-8',newline='\n')
    existing=subprocess.run(['gh','api','repos/'+OWNER+'/releases/tags/'+TAG],capture_output=True)
    if existing.returncode==0:
        release=json.loads(existing.stdout);assert not release['draft'] and release['target_commitish']==head
        assert {a['name'] for a in release['assets']}==all_assets
        for asset in release['assets']:assert asset['size']==(windows/asset['name']).stat().st_size and asset['digest']=='sha256:'+sha((windows/asset['name']).read_bytes())
        print('Existing exact release retained.');return
    subprocess.run(['gh','release','create',TAG,*[str(windows/n) for n in sorted(all_assets)],'--repo',OWNER,'--target',head,'--title','Release & Update Workbench - portable Windows x64','--notes-file',str(ROOT/'downloads/windows/release-update-workbench/RELEASE.md')],check=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifacts',type=Path,required=True);publish(p.parse_args().artifacts)
