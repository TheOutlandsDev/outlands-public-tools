"""Verify the exact twenty-four-tool ZIP and fresh offline install choices."""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile

from build import ROOT, HERE, ZIP_NAME, SELECTOR, inputs, encoded


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True,
                          env={**os.environ, 'PIP_NO_INDEX': '1', 'PYTHONNOUSERSITE': '1'})


def wheel_members(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if not names or names != sorted(names) or len(names) != len(set(names)) or archive.comment:
            raise ValueError('WHEEL_LAYOUT_INVALID')
        for info in archive.infolist():
            name = info.filename
            if (name.endswith('/') or name.startswith('/') or '\\' in name or ':' in name
                or '..' in PurePosixPath(name).parts or info.date_time != (1980, 1, 1, 0, 0, 0)
                or info.create_system != 3 or info.external_attr != 0o100644 << 16
                or info.extra or info.comment or info.compress_type != zipfile.ZIP_STORED):
                raise ValueError('WHEEL_METADATA_INVALID')
            body = archive.read(name)
            if re.search(rb'[A-Za-z]:[\\/]|/(?:home|Users)/|AppData', body, re.I):
                raise ValueError('WHEEL_PRIVATE_PATH_REFUSED')
        records = [name for name in names if name.endswith('.dist-info/RECORD')]
        if len(records) != 1:
            raise ValueError('WHEEL_RECORD_REQUIRED')
        rows = list(csv.reader(io.StringIO(archive.read(records[0]).decode('utf-8'))))
        if len(rows) != len(names) or {row[0] for row in rows} != set(names):
            raise ValueError('WHEEL_RECORD_INVALID')
        for name, value, size in rows:
            if name == records[0]:
                if value or size:
                    raise ValueError('WHEEL_RECORD_SELF_INVALID')
            else:
                body = archive.read(name)
                expected = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b'=').decode('ascii')
                if value != 'sha256=' + expected or size != str(len(body)):
                    raise ValueError('WHEEL_RECORD_DIGEST_MISMATCH')


def verify(archive_path, checksums_path):
    plan = json.loads((HERE / 'release.json').read_text(encoding='utf-8'))
    if plan['format'] != 'outlands-public-tools-twenty-four-bundle-release-v1' or plan['version'] != '1.4.0':
        raise ValueError('BUNDLE_RELEASE_PLAN_INVALID')
    if archive_path.name != ZIP_NAME or checksums_path.name != 'SHA256SUMS.txt':
        raise ValueError('ASSET_NAME_INVALID')
    for path in (archive_path, checksums_path):
        if not path.is_file() or digest(path.read_bytes()) != plan['assets'][path.name]:
            raise ValueError('RELEASE_ASSET_DIGEST_MISMATCH')
    raw = archive_path.read_bytes()
    if checksums_path.read_text(encoding='ascii') != digest(raw) + '  ' + ZIP_NAME + '\n':
        raise ValueError('OUTER_CHECKSUM_INVALID')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if len(names) != 35 or names != sorted(names) or len(names) != len(set(names)) or archive.comment:
            raise ValueError('BUNDLE_MEMBERS_INVALID')
        members = {}
        for info in archive.infolist():
            name = info.filename
            if (name.endswith('/') or name.startswith('/') or '\\' in name or ':' in name
                or '..' in PurePosixPath(name).parts or info.date_time != (1980, 1, 1, 0, 0, 0)
                or info.create_system != 3 or info.external_attr != 0o100644 << 16
                or info.extra or info.comment or info.compress_type != zipfile.ZIP_STORED):
                raise ValueError('BUNDLE_METADATA_INVALID')
            members[name] = archive.read(name)
    pinned, components = inputs()
    expected = {'MANIFEST.json', 'COMPONENTS.json', 'START-HERE.md', 'SHA256SUMS.txt',
                *('wheels/' + name for name in pinned), 'wheels/' + SELECTOR}
    if set(members) != expected:
        raise ValueError('BUNDLE_INVENTORY_MISMATCH')
    if members['COMPONENTS.json'] != encoded(components):
        raise ValueError('COMPONENT_LIST_MISMATCH')
    if members['START-HERE.md'] != (HERE / 'START-HERE.md').read_bytes():
        raise ValueError('START_GUIDE_MISMATCH')
    manifest = json.loads(members['MANIFEST.json'])
    if (manifest['format'] != 'outlands-public-tools-twenty-four-bundle-v1'
        or manifest['version'] != '1.4.0' or manifest['wheels'] != 31
        or manifest['components'] != 24 or set(manifest['members']) != set(members) - {'MANIFEST.json'}):
        raise ValueError('BUNDLE_MANIFEST_INVALID')
    for name, pin in manifest['members'].items():
        if pin != {'bytes': len(members[name]), 'sha256': digest(members[name])}:
            raise ValueError('BUNDLE_MEMBER_DIGEST_MISMATCH')
    for name, sha in pinned.items():
        if digest(members['wheels/' + name]) != sha:
            raise ValueError('COHORT_WHEEL_DIGEST_MISMATCH')
    wheel_names = sorted(name for name in members if name.startswith('wheels/'))
    if members['SHA256SUMS.txt'] != ''.join(
        digest(members[name]) + '  ' + name + '\n' for name in wheel_names).encode('ascii'):
        raise ValueError('INNER_CHECKSUM_INVALID')
    for name in wheel_names:
        wheel_members(members[name])

    groups = {'single-routing': ('outlands-model-capability-checker==1.0.0', {'model-capability-checker'}),
              'single-ai': ('outlands-prompt-contract-diff==1.0.0', {'prompt-contract-diff'}),
              'single-probability': ('outlands-probability-vector-checker==1.0.0', {'probability-vector-checker'}),
              'single-cache': ('outlands-cache-key-contract-checker==1.0.0', {'cache-key-contract-checker'}),
              'single-review': ('outlands-review-queue-contract-checker==1.0.0', {'review-queue-contract-checker'}),
              'single-test': ('outlands-test-case-manifest-checker==1.0.0', {'test-case-manifest-checker'}),
              'routing': ('outlands-public-tools-collection[routing]==1.4.0',
                          {row['id'] for row in components['components'] if row['group'] == 'routing'}),
              'ai': ('outlands-public-tools-collection[ai]==1.4.0',
                     {row['id'] for row in components['components'] if row['group'] == 'ai'}),
              'probability': ('outlands-public-tools-collection[probability]==1.4.0',
                              {row['id'] for row in components['components'] if row['group'] == 'probability'}),
              'cache': ('outlands-public-tools-collection[cache]==1.4.0',
                        {row['id'] for row in components['components'] if row['group'] == 'cache'}),
              'review': ('outlands-public-tools-collection[review]==1.4.0',
                         {row['id'] for row in components['components'] if row['group'] == 'review'}),
              'test': ('outlands-public-tools-collection[test]==1.4.0',
                       {row['id'] for row in components['components'] if row['group'] == 'test'}),
              'all': ('outlands-public-tools-collection[all]==1.4.0',
                      {row['id'] for row in components['components']})}
    results = []
    with tempfile.TemporaryDirectory(prefix='outlands-twenty-four-install-') as directory:
        base = Path(directory)
        wheel_dir = base / 'wheels'; wheel_dir.mkdir()
        for name in wheel_names:
            (wheel_dir / PurePosixPath(name).name).write_bytes(members[name])
        for choice, (requirement, expected_tools) in groups.items():
            environment = base / ('env-' + choice)
            run(sys.executable, '-m', 'venv', str(environment))
            python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            scripts = environment / ('Scripts' if os.name == 'nt' else 'bin')
            run(str(python), '-m', 'pip', 'install', '--no-index', '--find-links', str(wheel_dir), requirement)
            if choice in ('routing', 'ai', 'probability', 'cache', 'review', 'test', 'all'):
                listed = json.loads(run(str(scripts / ('outlands-public-tools.exe' if os.name == 'nt'
                                                      else 'outlands-public-tools'))).stdout)
                installed = {row['id'] for row in listed['components'] if row['installed']}
                if listed['format'] != 'outlands-public-tools-selector-v1' or installed != expected_tools:
                    raise ValueError('SELECTOR_STATE_MISMATCH')
            for row in components['components']:
                if row['id'] not in expected_tools:
                    continue
                demo = scripts / (row['command'] + '-demo' + ('.exe' if os.name == 'nt' else ''))
                report = json.loads(run(str(demo)).stdout)
                if report['status'] != 'PASS' or report['format'] != row['result_format']:
                    raise ValueError('FRESH_DEMO_FAILED')
            results.append({'choice': choice, 'tools': len(expected_tools), 'status': 'PASS'})
    return {'status': 'PASS', 'archive_sha256': digest(raw), 'members': len(members),
            'wheels': len(wheel_names), 'components': 24, 'fresh_installs': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--checksums', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.checksums)))
