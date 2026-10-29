"""Publish matching Windows bundles only after exact-source and Dataset Review acceptance."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile
from build import ROOT,TAG,FILENAME,PREFIX,encoded,git,payload,sha

OWNER='TheOutlandsDev/outlands-public-tools'
CAPTURES={'dataset-imported.jpg','dataset-stale.jpg','dataset-export.jpg','dataset-reopened.jpg'}

def publish(artifacts):
    assert os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_REPOSITORY')==OWNER
    head=git('rev-parse','HEAD').decode().strip()
    assert {p.name for p in artifacts.iterdir()}=={'dataset-review-portable-Windows','dataset-review-portable-Linux'}
    windows=artifacts/'dataset-review-portable-Windows';linux=artifacts/'dataset-review-portable-Linux';common={FILENAME,'release-receipt.json','SHA256SUMS.txt'};all_assets=common|{'acceptance.json'}|CAPTURES
    assert {p.name for p in windows.iterdir()}==all_assets and {p.name for p in linux.iterdir()}==common
    for name in common:assert (windows/name).read_bytes()==(linux/name).read_bytes()
    receipt=json.loads((windows/'release-receipt.json').read_bytes());assert receipt['packaging_source']==head and receipt['tag']==TAG and receipt['sha256']==sha((windows/FILENAME).read_bytes())
    accepted=json.loads((windows/'acceptance.json').read_bytes())
    assert accepted['status']=='PASS' and accepted['browser'] is True and accepted['core_tests']==115 and 10<=accepted['core_skips']<=12 and len(accepted['core_skip_methods'])==accepted['core_skips'] and accepted['required_windows_methods']==22
    assert accepted['original_browser_tests']==25 and accepted['original_browser_python'].startswith('3.12.')
    assert accepted['package_sha256']==receipt['sha256'] and accepted['packaging_source']==head and len(accepted['checks'])==16
    assert accepted['app_source']==receipt['app_source'] and accepted['runtime']==receipt['runtime_version']
    exercise=accepted['exercise'];browser=accepted['browser_data'];assert exercise['status']=='PASS' and exercise['command_checks']==24
    for result in (exercise,browser):
        assert [result[k] for k in ('input_rows','records','train_records','validation_records','test_records','approved_records','pending_records','provenance_rows','reviews','exported_records','export_files','empty_export_records','duplicate_linked_records_in_test')]==[5,4,1,1,2,1,3,5,2,1,2,0,2]
        assert all(result[k] for k in ('independent_record_ids_and_group_splits_checked','provenance_source_rows_independently_checked','logical_state_pin_independently_checked','stale_review_refused','missing_review_checks_refused','stale_export_and_backup_refused','invalid_batch_atomicity_checked','reimport_preserves_reviews_and_pin','export_bytes_and_hashes_independently_verified','old_export_unchanged','original_inputs_unchanged','backup_integrity_and_logical_rows_checked','saved_records_reopened'))
        assert all(result[k] is False for k in ('public_release_authorized','export_automatically_training_only','model_executed','complete_restore_performed'))
    assert exercise['fresh_export_destinations'] and exercise['existing_initialization_refused_without_writes']
    assert all(browser[k] for k in ('journal_bytes_unchanged_on_reopen','two_real_browser_tabs','stale_draft_retained','explicit_discard_required','fresh_review_assertions_unchecked','uncertain_reply_gate_without_replay'))
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
    subprocess.run(['gh','release','create',TAG,*[str(windows/n) for n in sorted(all_assets)],'--repo',OWNER,'--target',head,'--title','Offline Dataset Review Workbench - portable Windows x64','--notes-file',str(ROOT/'downloads/windows/dataset-review/RELEASE.md')],check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);publish(p.parse_args().artifacts)
