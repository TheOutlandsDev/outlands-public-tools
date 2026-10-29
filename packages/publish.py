"""CI-only immutable release publication after platform verification."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import hashlib
import urllib.request

from release_check import verify_release
from build import digest

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'TheOutlandsDev/outlands-public-tools'

def publish(output):
    plan = json.loads((ROOT / 'packages/catalog.json').read_text(encoding='utf-8'))
    if os.environ.get('GITHUB_REPOSITORY') != OWNER or os.environ.get('GITHUB_REF') not in ('refs/heads/main', 'refs/tags/' + plan['tag']):
        raise ValueError('REVIEWED_MAIN_OR_TAG_CI_REQUIRED')
    revision = os.environ.get('GITHUB_SHA', '')
    if not re.fullmatch('[0-9a-f]{40}', revision) or plan['tag'] != 'toolkit-v' + plan['version']:
        raise ValueError('RELEASE_IDENTITY_INVALID')
    output = Path(output).resolve()
    expected = {'catalog.json', 'release-matrix.json', 'SHA256SUMS.txt',
                'outlands-complete-' + plan['version'] + '.zip'}
    expected |= {'outlands-' + group['id'] + '-' + plan['version'] + '.zip' for group in plan['groups']}
    if {p.name for p in output.iterdir()} != expected: raise ValueError('EXACT_RELEASE_ASSETS_REQUIRED')
    present=subprocess.run(['gh','api','repos/'+OWNER+'/releases/tags/'+plan['tag']],capture_output=True)
    if present.returncode==0:
        # Later catalog/documentation commits do not replace a versioned release.
        old=json.loads(present.stdout);assets={a['name']:a for a in old['assets']}
        if old['draft'] or set(assets)!=expected or not re.fullmatch('[0-9a-f]{40}',old['target_commitish']):raise ValueError('EXISTING_RELEASE_DIFFERS')
        def fetch(name):
            with urllib.request.urlopen(assets[name]['browser_download_url'],timeout=30) as response:return response.read(4*1024*1024)
        sums=fetch('SHA256SUMS.txt');published=fetch('catalog.json')
        if assets['SHA256SUMS.txt']['digest']!='sha256:'+digest(sums):raise ValueError('EXISTING_ASSET_DIFFERS')
        checks=dict(line.split('  ',1)[::-1] for line in sums.decode('ascii').splitlines())
        if set(checks)!=expected-{'SHA256SUMS.txt'}:raise ValueError('EXISTING_ASSET_DIFFERS')
        for name,pin in checks.items():
            if assets[name]['digest']!='sha256:'+pin:raise ValueError('EXISTING_ASSET_DIFFERS')
        if digest(published)!=checks['catalog.json']:raise ValueError('EXISTING_ASSET_DIFFERS')
        cat=json.loads(published)
        if cat['source_revision']!=plan['source_revision'] or cat['packaging_revision']!=old['target_commitish'] or cat['tag']!=plan['tag']:raise ValueError('EXISTING_RELEASE_DIFFERS')
        if len(cat['components'])!=77 or len(cat['downloads'])!=9:raise ValueError('EXISTING_RELEASE_DIFFERS')
        print('Published version pins and asset digests verified; immutable release retained.');return
    verified=verify_release(output)
    command = ['gh', 'release', 'create', plan['tag'], *[str(output / n) for n in sorted(expected)],
               '--repo', OWNER, '--target', revision, '--title', 'OUTLANDS Toolkit ' + plan['version'] + ' - source and family workshops',
               '--notes-file', str(ROOT / 'packages/RELEASE.md')]
    subprocess.run(command, check=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', required=True)
    publish(parser.parse_args().output)
