"""Immutable release after Windows qualification and independent Ubuntu input audit."""
import argparse,json,os,subprocess
from pathlib import Path
from build import ROOT,TAG,FILENAME,git,sha
from verify import verify

def publish(packages):
    assert os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_REPOSITORY')=='TheOutlandsDev/outlands-public-tools'
    r=verify(packages,True);head=git('rev-parse','HEAD').decode().strip()
    names={FILENAME,'release-receipt.json','acceptance.json','SHA256SUMS.txt'};assert {p.name for p in packages.iterdir()}==names
    (packages/'SHA256SUMS.txt').write_text(''.join(sha((packages/n).read_bytes())+'  '+n+'\n' for n in sorted(names-{'SHA256SUMS.txt'})),encoding='utf-8',newline='\n')
    owner='TheOutlandsDev/outlands-public-tools';existing=subprocess.run(['gh','api','repos/'+owner+'/releases/tags/'+TAG],capture_output=True)
    if existing.returncode==0:
        release=json.loads(existing.stdout);assert not release['draft'] and release['target_commitish']==head and {x['name'] for x in release['assets']}==names
        for a in release['assets']:assert a['size']==(packages/a['name']).stat().st_size and a['digest']=='sha256:'+sha((packages/a['name']).read_bytes())
        print('Existing exact release retained.');return
    subprocess.run(['gh','release','create',TAG,*[str(packages/n) for n in sorted(names)],'--repo',owner,'--target',head,'--title','Local Site Builder - portable Windows x64','--notes-file',str(ROOT/'downloads/windows/local-site-builder/RELEASE.md')],check=True)
    previous=subprocess.run(['gh','api','repos/'+owner+'/releases/tags/local-site-builder-windows-v1.0.2-1'],capture_output=True)
    if previous.returncode==0:
        old=json.loads(previous.stdout)
        assert old['target_commitish']=='7918db8c3e2eb9afd0220987d818899a4bfc3094'
        # JSON stdin preserves prose/newlines. No asset deletion or replacement.
        note='\n\n## Superseded Windows package\nPackage 1 requires opening the printed editor URL manually because its automatic browser dispatch has a Windows quoting defect. Use [package 2](https://github.com/'+owner+'/releases/tag/'+TAG+') for the corrected URL-handler dispatch. The application, data format and original assets are retained.\n'
        update=dict(prerelease=True,make_latest='false',body=old['body']+note)
        subprocess.run(['gh','api','--method','PATCH','repos/'+owner+'/releases/'+str(old['id']),'--input','-'],input=json.dumps(update).encode(),check=True,stdout=subprocess.DEVNULL)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);publish(p.parse_args().packages)
