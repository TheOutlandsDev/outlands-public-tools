"""CI-only immutable release publication after platform verification."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'TheOutlandsDev/outlands-public-tools'

def publish(output):
    plan = json.loads((ROOT / 'packages/catalog.json').read_text(encoding='utf-8'))
    if os.environ.get('GITHUB_REPOSITORY') != OWNER or os.environ.get('GITHUB_REF') not in ('refs/heads/main', 'refs/tags/' + plan['tag']):
        raise ValueError('REVIEWED_MAIN_OR_TAG_CI_REQUIRED')
    revision = os.environ.get('GITHUB_SHA', '')
    if not re.fullmatch('[0-9a-f]{40}', revision) or plan['tag'] != 'toolkit-v' + plan['version']:
        raise ValueError('RELEASE_IDENTITY_INVALID')
    present = subprocess.run(['gh', 'release', 'view', plan['tag'], '--repo', OWNER, '--json', 'url'], capture_output=True, text=True)
    if present.returncode == 0:
        print('Existing release retained unchanged.'); return
    output = Path(output).resolve()
    expected = {'catalog.json', 'release-matrix.json', 'SHA256SUMS.txt',
                'outlands-complete-' + plan['version'] + '.zip'}
    expected |= {'outlands-' + group['id'] + '-' + plan['version'] + '.zip' for group in plan['groups']}
    if {p.name for p in output.iterdir()} != expected: raise ValueError('EXACT_RELEASE_ASSETS_REQUIRED')
    command = ['gh', 'release', 'create', plan['tag'], *[str(output / n) for n in sorted(expected)],
               '--repo', OWNER, '--target', revision, '--title', 'OUTLANDS Toolkit ' + plan['version'] + ' - source and family workshops',
               '--notes-file', str(ROOT / 'packages/RELEASE.md')]
    subprocess.run(command, check=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', required=True)
    publish(parser.parse_args().output)
