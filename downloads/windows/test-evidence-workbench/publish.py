"""Publish matching Windows bundles only after exact-source and Test & Evidence acceptance."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile
from build import ROOT,TAG,FILENAME,PREFIX,encoded,git,payload,sha

OWNER='TheOutlandsDev/outlands-public-tools'
CAPTURES={'evidence-trust.jpg','evidence-results.jpg','evidence-export.jpg','evidence-pending.jpg'}

def publish(artifacts):
    assert os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_REPOSITORY')==OWNER
    head=git('rev-parse','HEAD').decode().strip()
    assert {p.name for p in artifacts.iterdir()}=={'test-evidence-workbench-portable-Windows','test-evidence-workbench-portable-Linux'}
    windows=artifacts/'test-evidence-workbench-portable-Windows';linux=artifacts/'test-evidence-workbench-portable-Linux';common={FILENAME,'release-receipt.json','SHA256SUMS.txt'};all_assets=common|{'acceptance.json'}|CAPTURES
    assert {p.name for p in windows.iterdir()}==all_assets and {p.name for p in linux.iterdir()}==common
    for name in common:assert (windows/name).read_bytes()==(linux/name).read_bytes()
    receipt=json.loads((windows/'release-receipt.json').read_bytes());assert receipt['packaging_source']==head and receipt['tag']==TAG and receipt['sha256']==sha((windows/FILENAME).read_bytes())
    accepted=json.loads((windows/'acceptance.json').read_bytes())
    assert accepted['status']=='PASS' and accepted['browser'] is True and accepted['default_windows_workspace_qualified'] is True
    assert accepted['core_tests']==56 and accepted['core_skips']==1 and accepted['core_skip_methods']==['test_posix_fifo_refused_without_blocking'] and accepted['required_windows_methods']==5
    assert accepted['original_browser_tests']==16 and accepted['original_browser_python'].startswith('3.12.')
    assert accepted['package_sha256']==receipt['sha256'] and accepted['packaging_source']==head and len(accepted['checks'])==17
    assert accepted['app_source']==receipt['app_source'] and accepted['runtime']==receipt['runtime_version'] and receipt['files']==73
    exercise=accepted['exercise'];browser=accepted['browser_data'];assert exercise['status']=='PASS' and exercise['command_checks']==33
    for result in (exercise,browser):
        assert [result[k] for k in ('cases','case_revisions','planned','attempted','matched','unmatched','timeouts','artifacts','owned_children_started','export_files','export_data_files')]==[4,5,4,4,2,2,1,2,6,13,12]
        assert all(result[k] for k in ('expected_nonzero_matched','independent_case_artifact_script_input_hashes','independent_raw_capture_verdicts','independent_export_members_and_hashes','untrusted_plan_refused_without_children','missing_trust_checks_refused','missing_review_checks_refused','fresh_run_review_pending','pending_export_refused','review_revocation_blocks_future_export','new_case_revision_requires_trust','stale_plan_refused_without_children','old_artifact_payload_unchanged','old_exports_unchanged','original_inputs_unchanged','backup_integrity_and_logical_rows','saved_records_reopened'))
        assert all(result[k] is False for k in ('execution_sandbox','descendant_containment','original_operational_checks_executed','external_services_used','publication_authorized','complete_restore_performed'))
    assert exercise['stale_review_refused'] and exercise['existing_initialization_refused_without_writes'] and browser['journal_unchanged_on_reopen'] and browser['dirty_draft_blocks_execution']
    assert set(accepted['captures'])==CAPTURES
    for name,row in accepted['captures'].items():assert row['bytes']==(windows/name).stat().st_size and row['sha256']==sha((windows/name).read_bytes())
    files=payload();files['PACKAGE-MANIFEST.json']=encoded(dict(schema=1,package_version='0.1.0-windows.1',app_source=receipt['app_source'],packaging_source=head,runtime=receipt['runtime_version'],files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())]))
    with zipfile.ZipFile(windows/FILENAME) as archive:
        assert len(archive.namelist())==len(files)==receipt['files'] and set(archive.namelist())=={PREFIX+n for n in files}
        for name,body in files.items():assert archive.read(PREFIX+name)==body
    (windows/'SHA256SUMS.txt').write_text(''.join(sha((windows/n).read_bytes())+'  '+n+'\n' for n in sorted(all_assets-{'SHA256SUMS.txt'})),encoding='utf-8',newline='\n')
    existing=subprocess.run(['gh','api','repos/'+OWNER+'/releases/tags/'+TAG],capture_output=True)
    if existing.returncode==0:
        release=json.loads(existing.stdout);assert not release['draft'] and release['target_commitish']==head and {a['name'] for a in release['assets']}==all_assets
        for asset in release['assets']:assert asset['size']==(windows/asset['name']).stat().st_size and asset['digest']=='sha256:'+sha((windows/asset['name']).read_bytes())
        print('Existing exact release retained.');return
    subprocess.run(['gh','release','create',TAG,*[str(windows/n) for n in sorted(all_assets)],'--repo',OWNER,'--target',head,'--title','Offline Test & Evidence Workbench - portable Windows x64','--notes-file',str(ROOT/'downloads/windows/test-evidence-workbench/RELEASE.md')],check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);publish(p.parse_args().artifacts)
