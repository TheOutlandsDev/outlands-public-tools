"""Build the committed reviewed Markdown Document Builder source with deterministic ZIP bytes."""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'

def build(out):
    assert out.is_absolute() and out.parent.is_dir() and not out.exists() and not out.is_symlink()
    assert not getattr(out,'is_junction',lambda:False)()
    assert not out.resolve().is_relative_to(ROOT.resolve())
    assert (ROOT / 'VERSION').read_text().strip() == VERSION
    subprocess.run([sys.executable, '-B', str(ROOT / 'source_check.py')], check=True)
    inventory = json.loads((ROOT / 'SOURCE-MANIFEST.json').read_text())
    names = sorted([row['path'] for row in inventory['files']] + ['SOURCE-MANIFEST.json'])
    members = {}
    for name in names:
        data = (ROOT / name).read_bytes()
        expected = subprocess.check_output(['git', 'show', 'HEAD:tools/document-builders/' + name], cwd=ROOT)
        assert data == expected, 'COMMIT_REVIEWED_SOURCE_BEFORE_BUILD'
        assert b'\x00' not in data and len(data) < 1024*1024
        members[name] = data
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    out.mkdir()
    filename = 'document-builders-' + VERSION + '.zip'
    archive = out / filename
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as target:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo('document-builders-' + VERSION + '/' + name, date_time=(1980,1,1,0,0,0))
            info.create_system = 3; info.external_attr = 0o100644 << 16
            target.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    receipt = dict(schema=1, package='document-builders', version=VERSION, source_revision=revision,
                   filename=filename, bytes=archive.stat().st_size, files=len(members), sha256=digest)
    (out / 'build-manifest.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8', newline='\n')
    (out / 'SHA256SUMS.txt').write_text(digest+'  '+filename+'\n', encoding='ascii', newline='\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    build(parser.parse_args().out)
