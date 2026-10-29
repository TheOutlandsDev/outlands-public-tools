"""Publish matching Windows bundles only after exact-source and Corpus & Model acceptance."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile
from build import ROOT,TAG,FILENAME,PREFIX,encoded,git,payload,sha

OWNER='TheOutlandsDev/outlands-public-tools'
CAPTURES={'corpus-imported.jpg','corpus-exports.jpg','corpus-models.jpg','corpus-reopened.jpg'}

def publish(artifacts):
    assert os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_REPOSITORY')==OWNER
    head=git('rev-parse','HEAD').decode().strip()
    assert {p.name for p in artifacts.iterdir()}=={'corpus-model-workbench-portable-Windows','corpus-model-workbench-portable-Linux'}
    windows=artifacts/'corpus-model-workbench-portable-Windows';linux=artifacts/'corpus-model-workbench-portable-Linux';common={FILENAME,'release-receipt.json','SHA256SUMS.txt'};all_assets=common|{'acceptance.json'}|CAPTURES
    assert {p.name for p in windows.iterdir()}==all_assets and {p.name for p in linux.iterdir()}==common
    for name in common:assert (windows/name).read_bytes()==(linux/name).read_bytes()
    receipt=json.loads((windows/'release-receipt.json').read_bytes());assert receipt['packaging_source']==head and receipt['tag']==TAG and receipt['sha256']==sha((windows/FILENAME).read_bytes())
    accepted=json.loads((windows/'acceptance.json').read_bytes())
    assert accepted['status']=='PASS' and accepted['browser'] is True and accepted['sqlite_fts5'] is True
    assert accepted['core_tests']==82 and accepted['core_skips']==1 and accepted['core_skip_methods']==['test_posix_fifo_refused_without_blocking'] and accepted['required_windows_methods']==7
    assert accepted['original_browser_tests']==22 and accepted['original_browser_python'].startswith('3.12.')
    assert accepted['package_sha256']==receipt['sha256'] and accepted['packaging_source']==head and len(accepted['checks'])==17
    assert accepted['app_source']==receipt['app_source'] and accepted['runtime']==receipt['runtime_version'] and receipt['files']==74
    exercise=accepted['exercise'];browser=accepted['browser_data'];assert exercise['status']=='PASS' and exercise['command_checks']==21
    for result in (exercise,browser):
        assert [result[k] for k in ('input_rows','imported_records','records','approved_records','pending_records','source_row_receipts','sft_train','sft_test','sft_validation','sft_files','rag_train_chunks','rag_files','simulated_responses','invented_scores','discussion_turns','pending_generated_candidates','embeddings')]==[5,4,5,4,1,5,1,1,0,5,1,2,6,3,4,1,1]
        assert all(result[k] for k in ('exact_sft_rag_bytes_and_hashes','backup_integrity_and_logical_rows','missing_checks_refused','queue_idempotent','revocation_blocks_future_export','old_exports_unchanged','original_inputs_unchanged','saved_records_reopened'))
        assert all(result[k] is False for k in ('real_inference_verified','model_trained','generated_code_executed','publication_authorized','complete_restore_performed'))
    assert exercise['independent_ids_splits_provenance'] and exercise['unconfigured_real_backend_refused'] and exercise['reimport_preserves_reviews'] and exercise['existing_initialization_refused_without_writes']
    assert browser['journal_unchanged_on_reopen']
    assert set(accepted['captures'])==CAPTURES
    for name,row in accepted['captures'].items():assert row['bytes']==(windows/name).stat().st_size and row['sha256']==sha((windows/name).read_bytes())
    files=payload();files['PACKAGE-MANIFEST.json']=encoded(dict(schema=1,package_version='0.1.1-windows.1',app_source=receipt['app_source'],packaging_source=head,runtime=receipt['runtime_version'],files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())]))
    with zipfile.ZipFile(windows/FILENAME) as archive:
        assert len(archive.namelist())==len(files)==receipt['files'] and set(archive.namelist())=={PREFIX+n for n in files}
        for name,body in files.items():assert archive.read(PREFIX+name)==body
    (windows/'SHA256SUMS.txt').write_text(''.join(sha((windows/n).read_bytes())+'  '+n+'\n' for n in sorted(all_assets-{'SHA256SUMS.txt'})),encoding='utf-8',newline='\n')
    existing=subprocess.run(['gh','api','repos/'+OWNER+'/releases/tags/'+TAG],capture_output=True)
    if existing.returncode==0:
        release=json.loads(existing.stdout);assert not release['draft'] and release['target_commitish']==head and {a['name'] for a in release['assets']}==all_assets
        for asset in release['assets']:assert asset['size']==(windows/asset['name']).stat().st_size and asset['digest']=='sha256:'+sha((windows/asset['name']).read_bytes())
        print('Existing exact release retained.');return
    subprocess.run(['gh','release','create',TAG,*[str(windows/n) for n in sorted(all_assets)],'--repo',OWNER,'--target',head,'--title','Offline Corpus & Model Workbench - portable Windows x64','--notes-file',str(ROOT/'downloads/windows/corpus-model-workbench/RELEASE.md')],check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);publish(p.parse_args().artifacts)
