"""Publish matching Windows bundles only after exact-source and planning acceptance."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile
from build import ROOT,TAG,FILENAME,PREFIX,encoded,git,payload,sha

OWNER='TheOutlandsDev/outlands-public-tools'
CAPTURES={'visual-proposal.jpg','visual-correction.jpg','visual-reviewed.jpg','visual-heldout.jpg'}

def publish(artifacts):
    assert os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_REPOSITORY')==OWNER
    head=git('rev-parse','HEAD').decode().strip()
    assert {p.name for p in artifacts.iterdir()}=={'visual-portable-Windows','visual-portable-Linux'}
    windows=artifacts/'visual-portable-Windows';linux=artifacts/'visual-portable-Linux';common={FILENAME,'release-receipt.json','SHA256SUMS.txt'};all_assets=common|{'acceptance.json'}|CAPTURES
    assert {p.name for p in windows.iterdir()}==all_assets and {p.name for p in linux.iterdir()}==common
    for name in common:assert (windows/name).read_bytes()==(linux/name).read_bytes()
    receipt=json.loads((windows/'release-receipt.json').read_bytes());assert receipt['packaging_source']==head and receipt['tag']==TAG and receipt['sha256']==sha((windows/FILENAME).read_bytes())
    accepted=json.loads((windows/'acceptance.json').read_bytes())
    assert accepted['status']=='PASS' and accepted['browser'] is True and accepted['core_tests']==72 and accepted['core_skips']==1 and accepted['original_browser_tests']==9 and accepted['original_browser_python'].startswith('3.12.')
    assert accepted['package_sha256']==receipt['sha256'] and accepted['packaging_source']==head and len(accepted['checks'])==15
    assert accepted['app_source']==receipt['app_source'] and accepted['runtime']==receipt['runtime_version']
    exercise=accepted['exercise'];browser=accepted['browser_data'];assert exercise['status']=='PASS' and exercise['command_checks']==25
    for result in (exercise,browser):
        assert [result[k] for k in ('practice_views','train_specimens','test_specimens','training_views','evaluation_views','unreviewed_training_views','training_versions','report_files_per_selected_view','first_class_foreground_pixels','second_class_foreground_pixels')]==[2,1,1,1,1,0,3,5,2480,192]
        assert result['first_class_iou']==1280/2480
        assert all(result[k] for k in ('independent_mask_pixels_checked','report_hashes_independently_verified','held_out_training_refused','missing_review_checks_refused','new_version_does_not_inherit_review','historical_correction_retained','old_report_unchanged','original_inputs_unchanged','specimen_splits_disjoint','backup_integrity_checked','saved_correction_reopened'))
        assert all(result[k] is False for k in ('backup_includes_images','trained_model_executed','real_images_or_model_weights_included'))
    assert exercise['stale_review_refused'] and exercise['existing_initialization_refused_without_writes'] and browser['journal_bytes_unchanged_on_reopen']
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
    subprocess.run(['gh','release','create',TAG,*[str(windows/n) for n in sorted(all_assets)],'--repo',OWNER,'--target',head,'--title','Visual Dataset & Annotation Workbench - portable Windows x64','--notes-file',str(ROOT/'downloads/windows/visual-annotation-workbench/RELEASE.md')],check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);publish(p.parse_args().artifacts)
