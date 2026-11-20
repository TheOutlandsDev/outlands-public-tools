"""Build a deterministic ZIP of the reviewed Offline Order and Part Mapping Workbook Extractor."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'internal-production-record-validator'
VERSION = '0.1.0'


def build(destination, *, working_tree=False):
    if not __debug__:
        raise RuntimeError('Build requires assertions')
    assert destination.is_absolute() and destination.parent.is_dir()
    assert not os.path.lexists(destination)
    assert not destination.resolve().is_relative_to(ROOT)
    assert (ROOT / 'VERSION').read_text(encoding='ascii').strip() == VERSION
    subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'source_check.py')], check=True)
    inventory = json.loads((ROOT / 'SOURCE-MANIFEST.json').read_bytes())
    names = sorted([row['path'] for row in inventory['files']] + ['SOURCE-MANIFEST.json'])
    revision = None
    if not working_tree:
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()

    members = {}
    for name in names:
        data = (ROOT / name).read_bytes()
        if revision is not None:
            expected = subprocess.check_output(
                ['git', 'show', f'{revision}:tools/{PACKAGE}/{name}'], cwd=ROOT,
            )
            assert data == expected, f'Commit reviewed source before building: {name}'
        assert b'\x00' not in data and len(data) < 1024 * 1024
        members[name] = data

    destination.mkdir()
    stem = f'{PACKAGE}-{VERSION}'
    archive = destination / f'{stem}.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as target:
        for name, data in sorted(members.items()):
            item = zipfile.ZipInfo(f'{stem}/{name}', date_time=(1980, 1, 1, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            target.writestr(item, data)

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    receipt = dict(schema=1, package=PACKAGE, version=VERSION, source_revision=revision,
                   filename=archive.name, bytes=archive.stat().st_size, files=len(members), sha256=digest)
    with (destination / 'build-manifest.json').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(receipt, indent=2) + '\n')
    with (destination / 'SHA256SUMS.txt').open('x', encoding='ascii', newline='\n') as stream:
        stream.write(f'{digest}  {archive.name}\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--working-tree', action='store_true', help='Build a preview without a commit receipt')
    args = parser.parse_args()
    build(args.out, working_tree=args.working_tree)
