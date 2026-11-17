"""Verify finite source inventory and exact retained Rev 3b originals."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NAMES=['.gitattributes', '.gitignore', 'BASELINE.json', 'CHANGELOG.md', 'DEPENDENCIES.json', 'DEPENDENCY-REVIEW.json', 'LICENSE', 'PYTHON-LOCK.json', 'README.md', 'SETUP.md', 'THIRD-PARTY-NOTICES.md', 'VERSION', 'docs/ORIGINS.md', 'docs/QUALIFICATION.md', 'original/PATCH_NOTES.md', 'original/Vern_Analyze_v2.py', 'original/Vern_Analyze_v3b.py', 'original/verify_patch.py', 'packaging/build.py', 'packaging/prepare_python.py', 'packaging/qualify.py', 'requirements.in', 'requirements.lock', 'run_checks.py', 'source_check.py', 'synthetic.py', 'tests/test_analyzer.py', 'vernier.py']
def verify(write=False):
 assert __debug__
 baseline=json.loads((ROOT/'BASELINE.json').read_bytes());assert baseline['original_files']==4 and baseline['original_verification_scripts']==1
 for name,pin in baseline['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin,'ORIGINAL_CHANGED'
 rows=[]
 for name in NAMES:
  p=ROOT/name;assert p.is_file() and not p.is_symlink();raw=p.read_bytes();raw.decode('utf-8');assert b'\0' not in raw and len(raw)<1048576
  rows.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
 value=dict(format='outlands-source-pins-v2',files=rows)
 if write:(ROOT/'SOURCE-MANIFEST.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
 else:assert json.loads((ROOT/'SOURCE-MANIFEST.json').read_bytes())==value,'SOURCE_MISMATCH'
 return dict(status='SOURCE_MATCH',source_files=len(rows),original_files=4,original_checks=1)
if __name__=='__main__':
 assert sys.argv[1:] in ([],['--write-manifest']);print(json.dumps(verify(sys.argv[1:]==['--write-manifest'])))
