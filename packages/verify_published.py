"""Read-only hosted verification of actual public downloads and a fresh fictional exercise."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import zipfile
from build import verify_archive

ROOT=Path(__file__).resolve().parents[1]
OWNER='TheOutlandsDev/outlands-public-tools'

def require(value,code):
    if not value: raise ValueError(code)

def verify(workspace,evidence):
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')==OWNER,'HOSTED_OWN_REPOSITORY_REQUIRED')
    for path in (workspace,evidence):require(path.is_absolute() and not path.exists() and path.parent.is_dir() and not path.resolve().is_relative_to(ROOT),'NEW_EXTERNAL_DIRECTORIES_REQUIRED')
    plan=json.loads((ROOT/'packages/catalog.json').read_bytes());tag=plan['tag']
    require(re.fullmatch(r'toolkit-v[0-9]+\.[0-9]+\.[0-9]+',tag) is not None,'FIXED_RELEASE_TAG_REQUIRED')
    release=json.loads(subprocess.check_output(['gh','api','repos/'+OWNER+'/releases/tags/'+tag]))
    require(not release['draft'] and not release['prerelease'] and re.fullmatch('[0-9a-f]{40}',release['target_commitish']) is not None,'PUBLISHED_PINNED_RELEASE_REQUIRED')
    assets={row['name']:row for row in release['assets']};expected={'SHA256SUMS.txt','catalog.json','release-matrix.json','outlands-complete-'+plan['version']+'.zip'}|{'outlands-'+g['id']+'-'+plan['version']+'.zip' for g in plan['groups']}
    require(set(assets)==expected and len(release['assets'])==12,'EXACT_TWELVE_ASSETS_REQUIRED')
    workspace.mkdir();evidence.mkdir();downloads=workspace/'downloads';downloads.mkdir()
    def fetch(name):
        row=assets[name];url='https://github.com/'+OWNER+'/releases/download/'+tag+'/'+name
        require(row['browser_download_url']==url and 0<row['size']<32*1024*1024,'RELEASE_URL_OR_BOUND_INVALID')
        with urllib.request.urlopen(url,timeout=90) as f:data=f.read(32*1024*1024)
        require(len(data)==row['size'] and 'sha256:'+hashlib.sha256(data).hexdigest()==row['digest'],'PUBLIC_ASSET_DIGEST_MISMATCH')
        with (downloads/name).open('xb') as stream:stream.write(data)
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fetch,sorted(expected)))
    sums={}
    for line in (downloads/'SHA256SUMS.txt').read_text(encoding='ascii').splitlines():
        pin,name=line.split('  ');require(name not in sums and re.fullmatch('[0-9a-f]{64}',pin) is not None,'CHECKSUM_LIST_INVALID');sums[name]=pin
    require(set(sums)==expected-{'SHA256SUMS.txt'},'EXACT_CHECKSUM_MEMBERS_REQUIRED')
    for name,pin in sums.items():require(hashlib.sha256((downloads/name).read_bytes()).hexdigest()==pin,'CHECKSUM_MISMATCH')
    catalog=json.loads((downloads/'catalog.json').read_bytes())
    require(catalog['source_revision']==plan['source_revision'] and catalog['packaging_revision']==release['target_commitish'] and catalog['tag']==tag,'PUBLIC_PIN_MISMATCH')
    paths={'tools/'+n for g in plan['groups'] for n in g['tools']}|{'systems/'+n for n in plan['systems']}
    require(len(paths)==119 and {r['path'] for r in catalog['components']}==paths,'PUBLIC_COMPONENT_INVENTORY_MISMATCH')
    record=next(row for row in catalog['downloads'] if row['id']=='complete');raw=(downloads/record['filename']).read_bytes();manifest=verify_archive(raw)
    require(set(manifest['components'])==paths and manifest['packaging_revision']==catalog['packaging_revision'] and manifest['source_revision']==plan['source_revision'],'COMPLETE_MANIFEST_PIN_MISMATCH')
    extracted=workspace/'extracted'
    with zipfile.ZipFile(downloads/record['filename']) as z:z.extractall(extracted)
    root=next(extracted.iterdir());private=workspace/'fictional-intake-evidence'
    exercise_env={k:v for k,v in os.environ.items() if k not in ('GH_TOKEN','GITHUB_TOKEN','OUTLANDS_CATALOG_READ_TOKEN')}
    result=subprocess.run([sys.executable,'-B',str(root/'workshops/ingestion_evidence.py'),'--workspace',str(private)],cwd=root,capture_output=True,timeout=180,env={**exercise_env,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1'})
    (workspace/'private-exercise.log').write_bytes(result.stdout+result.stderr)
    require(result.returncode==0 and not result.stderr,'PUBLIC_EXERCISE_FAILED_PRIVATE_LOG_RETAINED');exercise=json.loads(result.stdout)
    require(exercise['status']=='PASS' and exercise['command_checks']==23 and exercise['private_export_files']==9 and exercise['matched']==exercise['unmatched']==1,'PUBLIC_EXERCISE_ORACLE_FAILED')
    manufacturing_run=subprocess.run([sys.executable,'-B',str(root/'workshops/manufacturing_review.py'),'--workspace',str(workspace/'fictional-manufacturing-review')],cwd=root,capture_output=True,timeout=120,env={**exercise_env,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1'})
    (workspace/'private-manufacturing.log').write_bytes(manufacturing_run.stdout+manufacturing_run.stderr)
    require(manufacturing_run.returncode==0 and not manufacturing_run.stderr,'PUBLIC_MANUFACTURING_FAILED_PRIVATE_LOG_RETAINED')
    manufacturing=json.loads(manufacturing_run.stdout)
    require(manufacturing['status']=='PASS' and manufacturing['command_checks']==12 and manufacturing['expected_review_outcomes']==4 and manufacturing['operator_review']=='REQUIRED','PUBLIC_MANUFACTURING_ORACLE_FAILED')
    value=dict(status='PASS',tag=tag,source_revision=plan['source_revision'],packaging_revision=catalog['packaging_revision'],components=119,public_assets_downloaded_and_verified=12,
        complete_sha256=hashlib.sha256(raw).hexdigest(),exercise=exercise,manufacturing_review=manufacturing,runtime_bundled=False,raw_logs_published=False,private_instances_published=False)
    (evidence/'public-download.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');print(json.dumps(value))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();verify(a.workspace,a.evidence)
