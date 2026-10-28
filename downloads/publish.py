"""CI-only immutable publication of focused downloads after platform acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

OWNER = 'TheOutlandsDev/outlands-public-tools'
ROOT = Path(__file__).resolve().parents[1]

def publish(output):
    assert os.environ.get('GITHUB_REPOSITORY') == OWNER and os.environ.get('GITHUB_REF') == 'refs/heads/main'
    matrix = json.loads((output / 'release-matrix.json').read_text(encoding='utf-8'))
    for item in matrix['applications']:
        assert item['source_revision'] == os.environ['GITHUB_SHA']
        target = output / item['filename']; assert hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256']
        prior = subprocess.run(['gh', 'release', 'view', item['tag'], '--repo', OWNER, '--json', 'url'], capture_output=True)
        if prior.returncode == 0:
            print('Existing focused release retained unchanged: ' + item['tag']); continue
        subprocess.run(['gh', 'release', 'create', item['tag'], str(target), str(output / 'SHA256SUMS.txt'), str(output / 'release-matrix.json'),
                        '--repo', OWNER, '--target', item['source_revision'], '--title', item['app'] + ' ' + item['version'] + ' - verified first run',
                        '--latest=false', '--notes-file', str(ROOT / 'tools' / item['app'] / 'docs/RELEASE.md')], check=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    publish(parser.parse_args().output)
