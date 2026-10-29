"""Immutable release only after matching builds, native methods and actual bundled GUI qualification."""
import argparse,json,os,subprocess,zipfile
from pathlib import Path
from build import ROOT,TAG,FILENAME,PREFIX,encoded,git,payload,sha
PROFILE=json.loads(Path(__file__).with_name('profile.json').read_bytes());KIND=PROFILE['module'];OWNER='TheOutlandsDev/outlands-public-tools'
CAPTURES={KIND+'-'+name+'.jpg' for name in (('triaged','retest','resolved','export') if KIND=='assessment' else ('coverage','acknowledged','cached','export'))}
def publish(artifacts):
    assert os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_REPOSITORY')==OWNER
    head=git('rev-parse','HEAD').decode().strip();prefix=PROFILE['id']+'-portable-';assert {p.name for p in artifacts.iterdir()}=={prefix+'Windows',prefix+'Linux'}
    windows=artifacts/(prefix+'Windows');linux=artifacts/(prefix+'Linux');common={FILENAME,'release-receipt.json','SHA256SUMS.txt'};assets=common|{'acceptance.json'}|CAPTURES
    assert {p.name for p in windows.iterdir()}==assets and {p.name for p in linux.iterdir()}==common
    for n in common:assert (windows/n).read_bytes()==(linux/n).read_bytes()
    receipt=json.loads((windows/'release-receipt.json').read_bytes());a=json.loads((windows/'acceptance.json').read_bytes())
    assert receipt['packaging_source']==head and receipt['app_source']==PROFILE['pin'] and receipt['source_zip_sha256']==PROFILE['sha'] and receipt['tag']==TAG and receipt['files']==72 and receipt['sha256']==sha((windows/FILENAME).read_bytes())
    assert a['status']=='PASS' and a['browser'] is True and a['default_windows_workspace_qualified'] is True and a['package_sha256']==receipt['sha256'] and a['packaging_source']==head and a['runtime']=='3.14.10'
    assert a['core_tests']==PROFILE['core'] and a['core_skips']==1 and a['core_skip_methods']==['test_posix_fifo_refused_without_blocking'] and a['required_windows_methods']==5
    assert a['original_browser_tests']==PROFILE['browser'] and a['original_browser_python'].startswith('3.12.') and len(a['checks'])==19
    assert a['exercise']['status']=='PASS' and a['exercise']['command_checks']==(32 if KIND=='assessment' else 24)
    for row in (a['exercise'],a['browser_data']):
        assert row['versions']==(7 if KIND=='assessment' else 4) and row['private_export_files']==(6 if KIND=='assessment' else 9)
        assert all(row[k] for k in ('independent_revision_and_receipt_hashes','independent_export_members_and_hashes','stale_change_refused_without_writes','review_refused_without_writes','original_inputs_unchanged','old_exports_unchanged','database_backup_integrity_and_rows','state_reopened_without_replay','operator_assertions_unverified'))
        assert all(row[k] is False for k in ('execution_performed','network_probed','publication_authorized','complete_restore_performed'))
        if KIND=='assessment':assert row['submissions']==2 and row['finding_state']=='Resolved' and row['manual_retest_review']=='accept'
        else:assert row['baseline_seconds']==dict(healthy=30,down=25,unknown=25,maintenance=20) and row['snapshots']==12 and row['baseline_snapshots']==10 and row['acknowledgement_does_not_resolve'] and row['cached_recovery_refused']
    assert set(a['captures'])==CAPTURES
    for n,v in a['captures'].items():assert v['bytes']==(windows/n).stat().st_size and v['sha256']==sha((windows/n).read_bytes())
    files=payload();files['PACKAGE-MANIFEST.json']=encoded(dict(schema=1,package_version='0.1.0-windows.1',app_source=receipt['app_source'],packaging_source=head,runtime=receipt['runtime_version'],files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())]))
    with zipfile.ZipFile(windows/FILENAME) as z:
        assert len(z.namelist())==len(files)==72 and set(z.namelist())=={PREFIX+n for n in files}
        for n,b in files.items():assert z.read(PREFIX+n)==b
    (windows/'SHA256SUMS.txt').write_text(''.join(sha((windows/n).read_bytes())+'  '+n+'\n' for n in sorted(assets-{'SHA256SUMS.txt'})),encoding='utf-8',newline='\n')
    old=subprocess.run(['gh','api','repos/'+OWNER+'/releases/tags/'+TAG],capture_output=True)
    if old.returncode==0:
        release=json.loads(old.stdout);assert not release['draft'] and release['target_commitish']==head and {v['name'] for v in release['assets']}==assets
        for v in release['assets']:assert v['size']==(windows/v['name']).stat().st_size and v['digest']=='sha256:'+sha((windows/v['name']).read_bytes())
        print('Existing exact release retained.');return
    subprocess.run(['gh','release','create',TAG,*[str(windows/n) for n in sorted(assets)],'--repo',OWNER,'--target',head,'--title',PROFILE['title']+' — portable Windows x64','--notes-file',str(ROOT/'downloads/windows'/PROFILE['id']/'RELEASE.md')],check=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);publish(p.parse_args().artifacts)
