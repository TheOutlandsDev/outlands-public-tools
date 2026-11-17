"""Verify only the explicit public source inventory and original-byte pins."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NAMES=['.dockerignore', '.env.example', '.gitattributes', '.gitignore', 'BASELINE.json', 'CHANGELOG.md', 'DEPENDENCIES.json', 'DEPENDENCY-REVIEW.json', 'Dockerfile', 'LICENSE', 'PYTHON-LOCK.json', 'README.md', 'SETUP.md', 'THIRD-PARTY-NOTICES.md', 'VERSION', 'app/__init__.py', 'app/config.py', 'app/logging_config.py', 'app/main.py', 'compose.yaml', 'docs/ORIGINS.md', 'docs/QUALIFICATION.md', 'packaging/build.py', 'packaging/container_qualify.py', 'packaging/container_tests.py', 'packaging/prepare_python.py', 'packaging/qualify.py', 'packaging/smoke_http.py', 'pyproject.toml', 'requirements-runtime.in', 'requirements-runtime.lock', 'requirements-validation.in', 'requirements-validation.lock', 'source_check.py', 'tests/__init__.py', 'tests/test_health.py', 'tests/test_release_contract.py']
def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify(write=False):
 baseline=json.loads((ROOT/'BASELINE.json').read_bytes())
 assert len(baseline['source_sha256'])==6 and baseline['original_tests']==2
 for name,pin in baseline['source_sha256'].items():assert sha((ROOT/name).read_bytes())==pin,'ORIGINAL_SOURCE_CHANGED'
 rows=[]
 for name in NAMES:
  path=ROOT/name;assert path.is_file() and not path.is_symlink()
  raw=path.read_bytes();raw.decode('utf-8');assert b'\x00' not in raw and len(raw)<1048576
  rows.append(dict(path=name,bytes=len(raw),sha256=sha(raw)))
 value=dict(format='outlands-source-pins-v2',files=rows)
 if write:(ROOT/'SOURCE-MANIFEST.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
 else:assert json.loads((ROOT/'SOURCE-MANIFEST.json').read_bytes())==value,'SOURCE_MISMATCH'
 return dict(status='SOURCE_MATCH',source_files=len(rows),original_python_files=6,original_tests=2)
if __name__=='__main__':
 assert sys.argv[1:] in ([],['--write-manifest'])
 print(json.dumps(verify(sys.argv[1:]==['--write-manifest'])))
