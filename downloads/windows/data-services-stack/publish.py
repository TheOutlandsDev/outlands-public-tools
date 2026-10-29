"""Publish matching Windows bundles only after exact-source and fake-transport acceptance."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile
from build import ROOT,TAG,FILENAME,PREFIX,encoded,git,payload,sha

OWNER='TheOutlandsDev/outlands-public-tools'
CAPTURES={'data-preview.jpg','data-result.jpg','data-retry.jpg','data-held.jpg'}

def publish(artifacts):
    assert os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_REPOSITORY')==OWNER
    head=git('rev-parse','HEAD').decode().strip()
    assert {p.name for p in artifacts.iterdir()}=={'data-services-portable-Windows','data-services-portable-Linux'}
    windows=artifacts/'data-services-portable-Windows';linux=artifacts/'data-services-portable-Linux';common={FILENAME,'release-receipt.json','SHA256SUMS.txt'};all_assets=common|{'acceptance.json'}|CAPTURES
    assert {p.name for p in windows.iterdir()}==all_assets and {p.name for p in linux.iterdir()}==common
    for name in common:assert (windows/name).read_bytes()==(linux/name).read_bytes()
    receipt=json.loads((windows/'release-receipt.json').read_bytes());assert receipt['packaging_source']==head and receipt['tag']==TAG and receipt['sha256']==sha((windows/FILENAME).read_bytes())
    accepted=json.loads((windows/'acceptance.json').read_bytes())
    assert accepted['status']=='PASS' and accepted['browser'] is True and accepted['core_tests']==101 and accepted['core_skips']==1 and accepted['original_browser_tests']==25 and accepted['original_browser_python'].startswith('3.12.')
    assert accepted['package_sha256']==receipt['sha256'] and accepted['packaging_source']==head and len(accepted['checks'])==18
    assert accepted['app_source']==receipt['app_source'] and accepted['runtime']==receipt['runtime_version']
    exercise=accepted['exercise'];browser=accepted['browser_data'];assert exercise['status']=='PASS' and exercise['command_checks']==22
    for result in (exercise,browser):
        assert [result[k] for k in ('input_records','holdout_predictions','mae','rmse','retry_attempts','retry_due_tick','accepted_attempts','unknown_attempts','future_replay_calls')]==[6,3,4,4,1,1,2,1,0]
        assert result['predictions']==[10,10,10] and result['unknown_state']=='REVIEW_REQUIRED'
        assert result['uncertain_delivery_assertion_refused'] and result['saved_results_reopened']
        assert all(result[k] is False for k in ('real_delivery_verified','real_forecast_usefulness_measured','automatic_dispatch'))
    assert all(exercise[k] for k in ('invalid_input_refused','idempotent_run_preserves_journal','existing_demo_refused_without_writes','input_bytes_unchanged','result_export_independently_read'))
    assert browser['private_report_files']==3 and browser['not_due_fake_calls']==0
    assert all(browser[k] for k in ('report_hashes_independently_verified','missing_review_refused','jsonl_and_csv_runs','historical_result_unchanged','journal_bytes_unchanged_on_reopen','previous_reports_retained','fresh_report_roots'))
    assert set(accepted['captures'])==CAPTURES
    for name,row in accepted['captures'].items():assert row['bytes']==(windows/name).stat().st_size and row['sha256']==sha((windows/name).read_bytes())
    files=payload();files['PACKAGE-MANIFEST.json']=encoded(dict(schema=1,package_version='0.2.0-windows.1',app_source=receipt['app_source'],packaging_source=head,runtime=receipt['runtime_version'],files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())]))
    with zipfile.ZipFile(windows/FILENAME) as archive:
        assert len(archive.namelist())==len(files)==receipt['files'] and set(archive.namelist())=={PREFIX+n for n in files}
        for name,body in files.items():assert archive.read(PREFIX+name)==body
    (windows/'SHA256SUMS.txt').write_text(''.join(sha((windows/n).read_bytes())+'  '+n+'\n' for n in sorted(all_assets-{'SHA256SUMS.txt'})),encoding='utf-8',newline='\n')
    existing=subprocess.run(['gh','api','repos/'+OWNER+'/releases/tags/'+TAG],capture_output=True)
    if existing.returncode==0:
        release=json.loads(existing.stdout);assert not release['draft'] and release['target_commitish']==head and {a['name'] for a in release['assets']}==all_assets
        for asset in release['assets']:assert asset['size']==(windows/asset['name']).stat().st_size and asset['digest']=='sha256:'+sha((windows/asset['name']).read_bytes())
        print('Existing exact release retained.');return
    subprocess.run(['gh','release','create',TAG,*[str(windows/n) for n in sorted(all_assets)],'--repo',OWNER,'--target',head,'--title','Data & Services Stack - portable Windows x64','--notes-file',str(ROOT/'downloads/windows/data-services-stack/RELEASE.md')],check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);publish(p.parse_args().artifacts)
