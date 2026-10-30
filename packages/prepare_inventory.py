"""Prepare a deterministic source-release review inventory; never activate a release."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def prepare(revision, version):
    if not re.fullmatch('[0-9a-f]{40}', revision) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('EXACT_SOURCE_PIN_AND_VERSION_REQUIRED')
    if git('rev-parse', revision + '^{commit}').decode().strip() != revision:
        raise ValueError('COMMIT_REQUIRED')
    registry = json.loads(git('show', revision + ':catalog/registry.json'))
    baseline = registry['published_toolkit']
    if version == baseline['version']:
        raise ValueError('NEW_VERSION_REQUIRED')
    paths = set(git('ls-tree', '-r', '--name-only', revision).decode().splitlines())
    old_paths = set(git('ls-tree', '-r', '--name-only', baseline['source_revision']).decode().splitlines())
    components = {p.rsplit('/', 1)[0] for p in paths if re.fullmatch(r'(tools|systems)/[^/]+/README.md', p)}
    old_components = {p.rsplit('/', 1)[0] for p in old_paths if re.fullmatch(r'(tools|systems)/[^/]+/README.md', p)}
    if components != {c['path'] for c in registry['components']}:
        raise ValueError('REGISTRY_SOURCE_DRIFT')
    changes = set(git('diff', '--name-only', baseline['source_revision'], revision, '--', 'tools', 'systems').decode().splitlines())
    rows = []
    for c in registry['components']:
        name = c['path']
        changed = sum(p.startswith(name + '/') for p in changes)
        rows.append(dict(id=c['id'], path=name, title=c['title'], kind=c['kind'],
                         family=c['group'], requirements=c['requirements'],
                         change='added' if name not in old_components else 'changed' if changed else 'unchanged',
                         changed_paths=changed,
                         readme_sha256=hashlib.sha256(git('show', revision + ':' + name + '/README.md')).hexdigest()))
    return dict(format='outlands-source-release-review-inventory-v1', status='PREPARATION_ONLY_NOT_RELEASED',
                candidate_version=version, source_revision=revision, baseline=baseline,
                counts=dict(components=len(rows), tools=sum(c['kind'] == 'tool' for c in rows),
                            systems=sum(c['kind'] == 'system' for c in rows),
                            added=sum(c['change'] == 'added' for c in rows),
                            changed=sum(c['change'] == 'changed' for c in rows),
                            unchanged=sum(c['change'] == 'unchanged' for c in rows),
                            removed=len(old_components - components)),
                removed_components=sorted(old_components - components), components=rows,
                runtimes_bundled=False, release_assets_built=False, new_public_downloads_verified=False,
                windows_demo_included=False, clean_windows_acceptance=False,
                release_pointer_changed=False, publication_authorized=False,
                remaining=['Review every changed component and exact source/privacy inventory',
                           'Create a separate reviewed packaging plan and explicit source/supplement pins',
                           'Run fresh archive qualification on Windows and Ubuntu',
                           'Compare independently built archive inventories and checksums',
                           'Publish a new release without replacing previous assets',
                           'Verify fresh public downloads before activating the catalog pointer'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-revision', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute() or not output.parent.is_dir() or output.exists() or output.is_symlink():
        raise ValueError('NEW_ABSOLUTE_OUTPUT_REQUIRED')
    result = prepare(args.source_revision, args.version)
    with output.open('x', encoding='ascii', newline='\n') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=True)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], counts=result['counts'])))


if __name__ == '__main__':
    main()
