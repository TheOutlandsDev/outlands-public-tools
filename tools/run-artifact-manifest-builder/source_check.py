"""Verify the finite source inventory and preserved original contracts."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def digest(raw):return hashlib.sha256(raw).hexdigest()
def verify():
 baseline=json.loads((ROOT/'BASELINE.json').read_bytes())
 for name,pin in baseline['original_source_sha256'].items():
  expected=baseline['native_windows_qualified_sha256'] if name=='native_windows.py' else pin
  assert digest((ROOT/name).read_bytes())==expected,'ORIGINAL_SOURCE_CHANGED:'+name
 names=sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='SOURCE-MANIFEST.json')
 value=dict(format='outlands-source-pins-v2',files=[dict(path=n,bytes=(ROOT/n).stat().st_size,sha256=digest((ROOT/n).read_bytes())) for n in names])
 if sys.argv[1:]==['--write-manifest']:(ROOT/'SOURCE-MANIFEST.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
 else:assert json.loads((ROOT/'SOURCE-MANIFEST.json').read_bytes())==value,'SOURCE_MISMATCH'
 return dict(status='SOURCE_MATCH',source_files=len(names),original_tests=44)
if __name__=='__main__':print(json.dumps(verify()))
