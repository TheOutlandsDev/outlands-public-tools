"""Check the source inventory and its exact byte hashes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def check(root=ROOT):
    manifest = json.loads((root / 'SOURCE-MANIFEST.json').read_bytes())
    seen = set()
    for record in manifest['files']:
        name = record['path']
        path = root / name
        if name in seen or not path.resolve().is_relative_to(root) or not path.is_file() or path.is_symlink():
            raise ValueError('Invalid source entry')
        raw = path.read_bytes()
        if (len(raw), hashlib.sha256(raw).hexdigest()) != (record['bytes'], record['sha256']):
            raise ValueError(f'Source bytes differ for {name}')
        seen.add(name)
    return seen


if __name__ == '__main__':
    print(json.dumps({'status': 'PASS', 'source_files': len(check())}))
