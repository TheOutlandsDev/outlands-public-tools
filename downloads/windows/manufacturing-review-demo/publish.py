"""Publish previously verified artifacts when invoked by an authorized release job."""
import argparse,json,os,subprocess
from pathlib import Path
from build import ROOT,TAG,FILENAME,sha
from verify_artifacts import RELEASE_ASSETS, validate

def publish(artifacts):
 assert os.environ.get('GITHUB_REF')=='refs/heads/main'
 assert os.environ.get('GITHUB_REPOSITORY')=='TheOutlandsDev/outlands-public-tools'
 w,receipt=validate(artifacts)
 assets=RELEASE_ASSETS
 (w/'SHA256SUMS.txt').write_text(''.join(sha((w/n).read_bytes())+'  '+n+'\n' for n in sorted(assets-{'SHA256SUMS.txt'})),encoding='ascii',newline='\n')
 old=subprocess.run(['gh','api','repos/TheOutlandsDev/outlands-public-tools/releases/tags/'+TAG],capture_output=True)
 if old.returncode==0:
  release=json.loads(old.stdout);assert not release['draft'] and release['target_commitish']==receipt['packaging_revision'] and {r['name'] for r in release['assets']}==assets
  assert next(r for r in release['assets'] if r['name']==FILENAME)['digest']=='sha256:'+receipt['sha256']
  print('Existing immutable release retained.');return
 subprocess.run(['gh','release','create',TAG,*[str(w/n) for n in sorted(assets)],'--repo','TheOutlandsDev/outlands-public-tools','--target',receipt['packaging_revision'],'--title','Manufacturing Review Demo — Python included for Windows x64','--notes-file',str(ROOT/'downloads/windows/manufacturing-review-demo/RELEASE.md')],check=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--artifacts',type=Path,required=True)
 parser.add_argument('--verify-only',action='store_true')
 args=parser.parse_args()
 if args.verify_only:
  validate(args.artifacts)
  print('PASS: identical platform builds and verified Windows native and browser evidence')
 else:
  publish(args.artifacts)
