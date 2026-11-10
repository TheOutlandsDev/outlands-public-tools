"""CI-only immutable publication of focused downloads after platform acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

OWNER = 'TheOutlandsDev/outlands-public-tools'
ROOT = Path(__file__).resolve().parents[1]

def monitor_assets(output, item, reports):
    assert reports is not None
    lanes = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(reports.rglob('qualification.json'))]
    expected = {(platform, version) for platform in ('win32', 'linux') for version in ('3.12', '3.13', '3.14', '3.15')}
    assert len(lanes) == 8 and {(lane['platform'], '.'.join(lane['python'].split('.')[:2])) for lane in lanes} == expected
    for lane in lanes:
        assert lane['status'] == 'PASS' and lane['source_revision'] == item['source_revision'] and lane['zip_sha256'] == item['sha256']
        assert lane['exact_extracted_source'] and lane['native_features_required'] and lane['demo_download_check']
        assert lane['frontend_tests'] == 13 and lane['frontend_failures'] == lane['frontend_skips'] == 0 and not lane['live_values_published']
        assert {mode['mode'] for mode in lane['modes']} == {'demo', 'live'} and len(lane['modes']) == 2
        for mode in lane['modes']:
            assert mode['status'] == 'PASS' and mode['tests'] == mode['passed'] == (49 if mode['mode'] == 'demo' else 5)
            assert mode['skipped'] == mode['failures'] == mode['errors'] == 0
            assert mode['fresh_venv'] and mode['extracted_import']
            assert mode['psutil'] == ('absent' if mode['mode'] == 'demo' else '7.2.2')
    proof = dict(schema=1, app='resource-monitor', version=item['version'], status='PASS',
                 source_revision=item['source_revision'], zip_sha256=item['sha256'], lanes=lanes,
                 workflow='https://github.com/'+OWNER+'/actions/runs/'+os.environ['GITHUB_RUN_ID'],
                 python_tests_passed=sum(mode['passed'] for lane in lanes for mode in lane['modes']),
                 limits=['Live readings and capability tokens are not published.',
                         'Browser rendering/export interaction is not qualified by these HTTP and frontend tests.',
                         'Windows x64 and Ubuntu x86_64 regular CPython only; other architectures and free-threaded builds are not qualified.',
                         'No admin, firewall, service or startup-policy changes are required by the application.'])
    release_assets = output / 'resource-monitor-release-assets'
    release_assets.mkdir()
    validation = release_assets / 'VALIDATION.json'
    validation.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    guide = release_assets / 'START-HERE.md'
    guide.write_bytes((ROOT / 'tools/resource-monitor/START-HERE.md').read_bytes())
    sums = release_assets / 'SHA256SUMS.txt'
    sums.write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n'
                           for path in (output/item['filename'], guide, validation, output/'release-matrix.json')), encoding='ascii', newline='\n')
    return [str(guide), str(validation), str(sums)]

def publish(output, resource_monitor_reports=None):
    assert os.environ.get('GITHUB_REPOSITORY') == OWNER and os.environ.get('GITHUB_REF') == 'refs/heads/main'
    matrix = json.loads((output / 'release-matrix.json').read_text(encoding='utf-8'))
    for item in matrix['applications']:
        assert item['source_revision'] == os.environ['GITHUB_SHA']
        target = output / item['filename']; assert hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256']
        prior = subprocess.run(['gh', 'release', 'view', item['tag'], '--repo', OWNER, '--json', 'url'], capture_output=True)
        if prior.returncode == 0:
            print('Existing focused release retained unchanged: ' + item['tag']); continue
        assets = monitor_assets(output, item, resource_monitor_reports) if item['app'] == 'resource-monitor' else [str(output / 'SHA256SUMS.txt')]
        subprocess.run(['gh', 'release', 'create', item['tag'], str(target), *assets, str(output / 'release-matrix.json'),
                        '--repo', OWNER, '--target', item['source_revision'], '--title', item['app'] + ' ' + item['version'] + ' - verified first run',
                        '--latest=false', '--notes-file', str(ROOT / 'tools' / item['app'] / 'docs/RELEASE.md')], check=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resource-monitor-reports', type=Path)
    args=parser.parse_args(); publish(args.output, args.resource_monitor_reports)
