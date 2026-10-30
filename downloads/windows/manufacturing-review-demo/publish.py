"""Require matching builds, report acceptance and actual Windows execution after Python removal."""
import argparse,json,os,subprocess,urllib.request,zipfile
from pathlib import Path
from build import ROOT,TAG,FILENAME,PREFIX,SOURCE,SOURCE_SHA,RUNTIME_SHA,git,payload,encoded,sha,verify

CAPTURES={'manufacturing-'+x+'.jpg' for x in ('overview','capacity','materials','inspection','outcomes','evidence','narrow')}
COMMON={FILENAME,'release-receipt.json','SHA256SUMS.txt'}
MEDIA={'manufacturing-review-walkthrough.mp4','manufacturing-review-walkthrough.vtt'}

def validate(artifacts):
 w=artifacts/'manufacturing-demo-Windows';l=artifacts/'manufacturing-demo-Linux';c=artifacts/'manufacturing-demo-clean'
 assert {p.name for p in artifacts.iterdir()}=={w.name,l.name,c.name}
 assert {p.name for p in w.iterdir()}==COMMON|MEDIA|CAPTURES|{'acceptance.json'}
 assert {p.name for p in l.iterdir()}==COMMON and {p.name for p in c.iterdir()}=={'clean-acceptance.json'}
 for n in COMMON:assert (w/n).read_bytes()==(l/n).read_bytes()
 head=git('rev-parse','HEAD').decode().strip();receipt=json.loads((w/'release-receipt.json').read_bytes());a=json.loads((w/'acceptance.json').read_bytes());clean=json.loads((c/'clean-acceptance.json').read_bytes())
 assert receipt['tag']==TAG and receipt['filename']==FILENAME and receipt['source_zip_sha256']==SOURCE_SHA and receipt['runtime_sha256']==RUNTIME_SHA and receipt['tools']==12 and receipt['exercises']==2
 assert receipt['packaging_revision']==a['packaging_revision']==clean['packaging_revision']==head
 assert receipt['source_revision']==a['source_revision']==SOURCE
 assert receipt['sha256']==a['package_sha256']==clean['package_sha256']==sha((w/FILENAME).read_bytes())
 assert a['status']==clean['status']=='PASS' and a['runtime']==clean['runtime']=='3.14.10'
 assert a['browser'] is True and a['browser_checks']==9 and a['cli_checks']==36 and a['expected_review_outcomes']==17
 assert clean['environment_kind']=='full-windows-host-preinstalled-python-executables-removed' and clean['native_windows_host'] is True
 assert clean['python_absent_before_extraction'] is True and clean['python_executables_removed']>0 and clean['python_executables_remaining_before_extraction']==0 and clean['registered_python_available']==0 and clean['runtime_scan_errors']==0
 assert clean['original_storage_guard_passed'] is True and clean['bundled_runtime'] is True and clean['isolated'] is True
 assert clean['command_checks']==36 and clean['expected_review_outcomes']==17 and clean['existing_run_refused_unchanged'] and clean['saved_run_reopened_without_writes']
 assert clean['desktop_browser_tested_in_absence_job'] is False and clean['physical_operations_performed'] is False
 assert set(a['captures'])==CAPTURES
 for name,row in a['captures'].items():assert (w/name).stat().st_size==row['bytes'] and sha((w/name).read_bytes())==row['sha256']
 assert a['video']['seconds']==60 and a['video']['actual_windows_bundle_report'] is True
 assert sha((w/a['video']['filename']).read_bytes())==a['video']['sha256'] and sha((w/a['video']['captions']).read_bytes())==a['video']['captions_sha256']
 expected=payload();expected['PACKAGE-MANIFEST.json']=encoded(dict(schema=1,version='0.1.0-windows.1',source_revision=SOURCE,source_zip_sha256=receipt['source_zip_sha256'],packaging_revision=head,runtime='3.14.10',files=[dict(path=n,bytes=len(raw),sha256=sha(raw)) for n,raw in sorted(expected.items())]))
 verify((w/FILENAME).read_bytes())
 with zipfile.ZipFile(w/FILENAME) as z:
  assert set(z.namelist())=={PREFIX+n for n in expected} and len(z.namelist())==len(expected)==receipt['files']
  for name,raw in expected.items():assert z.read(PREFIX+name)==raw
 return w,c,receipt

def publish(artifacts):
 w,c,receipt=validate(artifacts);assert os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_REPOSITORY')=='TheOutlandsDev/outlands-public-tools'
 (w/'clean-acceptance.json').write_bytes((c/'clean-acceptance.json').read_bytes())
 assets=COMMON|MEDIA|CAPTURES|{'acceptance.json','clean-acceptance.json'};assert len(assets)==14
 (w/'SHA256SUMS.txt').write_text(''.join(sha((w/n).read_bytes())+'  '+n+'\n' for n in sorted(assets-{'SHA256SUMS.txt'})),encoding='ascii',newline='\n')
 old=subprocess.run(['gh','api','repos/TheOutlandsDev/outlands-public-tools/releases/tags/'+TAG],capture_output=True)
 if old.returncode==0:
  release=json.loads(old.stdout);assert not release['draft'] and release['target_commitish']==receipt['packaging_revision'] and {r['name'] for r in release['assets']}==assets
  assert next(r for r in release['assets'] if r['name']==FILENAME)['digest']=='sha256:'+receipt['sha256']
  print('Existing immutable release retained.');return
 subprocess.run(['gh','release','create',TAG,*[str(w/n) for n in sorted(assets)],'--repo','TheOutlandsDev/outlands-public-tools','--target',receipt['packaging_revision'],'--title','Manufacturing Review Demo — Python included for Windows x64','--notes-file',str(ROOT/'downloads/windows/manufacturing-review-demo/RELEASE.md')],check=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--verify-only',action='store_true');a=p.parse_args()
 if a.verify_only:validate(a.artifacts);print('PASS: exact matching ZIPs, actual report capture, captioned walkthrough and Windows execution after Python removal')
 else:publish(a.artifacts)
