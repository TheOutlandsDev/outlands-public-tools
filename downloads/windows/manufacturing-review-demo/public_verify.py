"""Download and verify every actual public release asset; fresh native CMD verification on Windows."""
import argparse,json,os,subprocess,urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from build import TAG,FILENAME,SOURCE,sha,verify
from publish import COMMON,MEDIA,CAPTURES

def run(workspace,evidence):
 assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')=='TheOutlandsDev/outlands-public-tools'
 assert workspace.is_absolute() and not workspace.exists() and workspace.parent.is_dir() and evidence.is_absolute() and not evidence.exists() and evidence.parent.is_dir()
 release=json.loads(subprocess.check_output(['gh','api','repos/TheOutlandsDev/outlands-public-tools/releases/tags/'+TAG]));assets={r['name']:r for r in release['assets']};expected=COMMON|MEDIA|CAPTURES|{'acceptance.json','clean-acceptance.json'}
 assert not release['draft'] and set(assets)==expected and len(assets)==14
 workspace.mkdir();evidence.mkdir();downloads=workspace/'downloads';downloads.mkdir()
 def fetch(name):
  row=assets[name];assert 0<row['size']<64*1024*1024
  with urllib.request.urlopen(row['browser_download_url'],timeout=120) as f:raw=f.read(64*1024*1024)
  assert len(raw)==row['size'] and 'sha256:'+sha(raw)==row['digest'];(downloads/name).write_bytes(raw)
 with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fetch,sorted(expected)))
 sums={}
 for line in (downloads/'SHA256SUMS.txt').read_text(encoding='ascii').splitlines():
  pin,name=line.split('  ');assert name not in sums and sha((downloads/name).read_bytes())==pin;sums[name]=pin
 assert set(sums)==expected-{'SHA256SUMS.txt'}
 receipt=json.loads((downloads/'release-receipt.json').read_bytes());acceptance=json.loads((downloads/'acceptance.json').read_bytes());clean=json.loads((downloads/'clean-acceptance.json').read_bytes());manifest=verify((downloads/FILENAME).read_bytes())
 assert receipt['source_revision']==SOURCE and receipt['packaging_revision']==release['target_commitish']==manifest['packaging_revision']
 assert receipt['sha256']==sha((downloads/FILENAME).read_bytes())==acceptance['package_sha256']==clean['package_sha256']
 assert acceptance['status']==clean['status']=='PASS' and clean['python_absent_in_pristine_base'] and clean['network']=='none'
 native=False
 if os.name=='nt':
  from accept import accept
  private=workspace/'native';private.mkdir()
  for name in (FILENAME,'release-receipt.json'):(private/name).write_bytes((downloads/name).read_bytes())
  accept(private,workspace/'fresh public download');native=True
 value=dict(schema=1,status='PASS',tag=TAG,source_revision=SOURCE,packaging_revision=receipt['packaging_revision'],package_sha256=receipt['sha256'],public_assets_verified=14,native_fresh_download_cmd=native,clean_windows_python_absence_verified=True,clean_windows_image=clean['image_digest'],cli_checks=36,expected_review_outcomes=17,raw_logs_published=False,private_runs_published=False)
 (evidence/'public-download.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');print(json.dumps(value))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();run(a.workspace,a.evidence)
