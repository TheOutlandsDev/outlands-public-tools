"""Explicit maintainer/CI PyPI advisory check; never called during PDF inspection."""
import importlib.metadata
import json
import sys
import urllib.request
from pdf_bounds import PINS

ALL_PINS = {**PINS, 'pypdf': '6.21.2'}


def check():
    results = []
    for name, selected in ALL_PINS.items():
        if importlib.metadata.version(name) != selected:
            raise ValueError('Installed dependency differs from reviewed pins')
        with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{selected}/json', timeout=30) as response:
            data = response.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise ValueError('Advisory response too large')
        record = json.loads(data)
        if record['info']['version'] != selected or type(record.get('vulnerabilities')) is not list:
            raise ValueError('Invalid advisory response')
        results.append({'name': name, 'version': selected,
                        'advisories': [item['id'] for item in record['vulnerabilities']]})
    if any(row['advisories'] for row in results):
        raise ValueError('PyPI reports an advisory; maintainer review required')
    return {'status': 'PASS', 'packages': len(results), 'known_pypi_advisories': 0,
            'scope': 'Current PyPI version records only; not exhaustive vulnerability or safety certification.'}


if __name__ == '__main__':
    try:
        if len(sys.argv) != 1:
            raise ValueError('No custom packages or endpoints supported')
        print(json.dumps(check(), sort_keys=True))
    except Exception:
        print(json.dumps({'status': 'FAIL', 'error': 'PIN_OR_ADVISORY_CHECK_FAILED'}), file=sys.stderr)
        raise SystemExit(1)
