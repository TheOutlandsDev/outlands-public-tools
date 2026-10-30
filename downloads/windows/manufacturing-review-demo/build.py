"""Build a focused Windows bundle from exact public Toolkit and CPython bytes."""
import argparse,hashlib,io,json,stat,subprocess,urllib.request,zipfile
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[3]
PACKAGE_PATH='downloads/windows/manufacturing-review-demo/'
SOURCE='5ace0cacafe0874fa4db816a11c5cc0cf04089d2'
SOURCE_URL='https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/toolkit-v0.9.0/outlands-complete-0.9.0.zip'
SOURCE_SHA='b7b8fb6ad1e36587bb0a744b7b43468093209dfb06657c254011a576f3d4bdcb'
RUNTIME='3.14.10'
RUNTIME_URL='https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip'
RUNTIME_SHA='90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
TAG='manufacturing-review-demo-windows-v0.1.0-1'
FILENAME='manufacturing-review-demo-0.1.0-windows-x64.zip'
PREFIX='manufacturing-review-demo-0.1.0-windows-x64/'
TOOLS=('resource-reservation-checker','assignment-eligibility-checker','process-event-duration-analyzer','flow-balance-reconciler',
       'bom-contract-checker','lot-identity-checker','material-allocation-checker','handoff-lifecycle-checker',
       'measurement-contract-checker','inspection-coverage-checker','yield-scrap-reconciler','rework-history-checker')
WORKSHOPS=('manufacturing_review.py','manufacturing-review.md','material_quality_review.py','material-quality-review.md')
EXTRAS=('launch.py','viewer.py','Manufacturing Review Demo.cmd','START-HERE.txt','FIVE-MINUTE.txt','THIRD-PARTY-NOTICES.txt')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def members(raw):
 files={}
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  for row in archive.infolist():
   name=row.orig_filename;p=PurePosixPath(name)
   if row.is_dir() or p.is_absolute() or '\\' in name or ':' in name or any(x in ('','.','..') for x in name.split('/')) or name.casefold() in {n.casefold() for n in files} or stat.S_IFMT(row.external_attr>>16) not in (0,stat.S_IFREG) or row.file_size>32*1024*1024:raise ValueError('UNSAFE_ARCHIVE_MEMBER')
   files[name]=archive.read(row)
 return files

def download(url,pin,limit,cached=None):
 if cached:raw=cached.read_bytes()
 else:
  with urllib.request.urlopen(url,timeout=120) as response:raw=response.read(limit+1)
 if len(raw)>limit or sha(raw)!=pin:raise ValueError('UPSTREAM_PIN_MISMATCH')
 return raw

def payload(runtime=None,source=None):
 original=members(download(SOURCE_URL,SOURCE_SHA,32*1024*1024,source));prefix='outlands-complete-0.9.0/'
 manifest=json.loads(original[prefix+'PACKAGE-MANIFEST.json']);assert manifest['packaging_revision']==SOURCE
 assert set(original)=={prefix+n for n in manifest['files']}|{prefix+'PACKAGE-MANIFEST.json'}
 for name,row in manifest['files'].items():
  raw=original[prefix+name];assert row['bytes']==len(raw) and row['sha256']==sha(raw)
 selected={n for n in manifest['files'] if any(n.startswith('tools/'+tool+'/') for tool in TOOLS) or n in {'workshops/'+x for x in WORKSHOPS} or n in {'LICENSE','LICENSING.md'}}
 assert {n.split('/')[1] for n in selected if n.startswith('tools/')}==set(TOOLS)
 files={}
 for name in sorted(selected):
  raw=original[prefix+name];assert raw==git('show',SOURCE+':'+name),name
  files['application/'+name]=raw
 upstream=members(download(RUNTIME_URL,RUNTIME_SHA,20*1024*1024,runtime))
 assert {'python.exe','python314.zip','python314.dll','python314._pth','LICENSE.txt'}<=set(upstream)
 # Isolated module paths stay local. The adapter selects only named bundled entrypoints.
 upstream['python314._pth']=b'python314.zip\n.\nimport site\n'
 files.update({'runtime/'+name:raw for name,raw in upstream.items()})
 files['runtime/sitecustomize.py']=git('show','HEAD:'+PACKAGE_PATH+'sitecustomize.py')
 for name in EXTRAS:files[name]=git('show','HEAD:'+PACKAGE_PATH+name)
 return files

def verify(raw):
 files=members(raw);manifest=json.loads(files[PREFIX+'PACKAGE-MANIFEST.json'])
 assert len(manifest['files'])==len({row['path'] for row in manifest['files']}) and len(files)==len(manifest['files'])+1
 assert set(files)=={PREFIX+row['path'] for row in manifest['files']}|{PREFIX+'PACKAGE-MANIFEST.json'}
 for row in manifest['files']:
  data=files[PREFIX+row['path']];assert len(data)==row['bytes'] and sha(data)==row['sha256']
 return manifest

def build(output,runtime=None,source=None):
 assert output.is_absolute() and not output.exists() and output.parent.is_dir() and not output.resolve().is_relative_to(ROOT)
 assert not git('diff','HEAD','--name-only','--',PACKAGE_PATH).strip(),'COMMIT_PACKAGING_FIRST'
 files=payload(runtime,source);revision=git('rev-parse','HEAD').decode().strip()
 manifest=dict(schema=1,version='0.1.0-windows.1',source_revision=SOURCE,source_zip_sha256=SOURCE_SHA,packaging_revision=revision,runtime=RUNTIME,
               files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())])
 files['PACKAGE-MANIFEST.json']=encoded(manifest);output.mkdir()
 with zipfile.ZipFile(output/FILENAME,'x',compression=zipfile.ZIP_STORED) as archive:
  for name,raw in sorted(files.items()):
   info=zipfile.ZipInfo(PREFIX+name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;archive.writestr(info,raw)
 verify((output/FILENAME).read_bytes())
 receipt=dict(schema=1,tag=TAG,filename=FILENAME,source_revision=SOURCE,source_zip_sha256=SOURCE_SHA,packaging_revision=revision,runtime=RUNTIME,
              runtime_url=RUNTIME_URL,runtime_sha256=RUNTIME_SHA,tools=12,exercises=2,expected_cli_calls=36,expected_review_outcomes=17,
              files=len(files),bytes=(output/FILENAME).stat().st_size,sha256=sha((output/FILENAME).read_bytes()))
 (output/'release-receipt.json').write_bytes(encoded(receipt))
 (output/'SHA256SUMS.txt').write_text(''.join(sha((output/n).read_bytes())+'  '+n+'\n' for n in (FILENAME,'release-receipt.json')),encoding='ascii',newline='\n')
 print(json.dumps(receipt))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--runtime',type=Path);p.add_argument('--source',type=Path)
 a=p.parse_args();build(a.output,a.runtime,a.source)
