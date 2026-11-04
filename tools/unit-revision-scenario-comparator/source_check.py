"""Verify the explicit local text-source manifest; not authenticity or rights proof."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).absolute().parent
    manifest = json.loads((root / 'SOURCE-MANIFEST.json').read_text(encoding='utf-8'))
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.name != 'SOURCE-MANIFEST.json'}
    if manifest['format'] != 'outlands-source-pins-v1' or actual != set(manifest['files']):
        raise SystemExit('SOURCE_MISMATCH')
    for name, pin in manifest['files'].items():
        raw = (root / name).read_bytes()
        if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
            raise SystemExit('SOURCE_MISMATCH')
    print(json.dumps(dict(status='SOURCE_MATCH', files=len(actual) + 1)))


if __name__ == '__main__':
    main()
