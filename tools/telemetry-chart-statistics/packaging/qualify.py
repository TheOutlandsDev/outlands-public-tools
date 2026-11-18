"""Validate a fresh extraction with the public Python API."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'telemetry-chart-statistics-0.1.0.zip'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(packages, workspace, receipt_path, receipt, reference=None):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    archive = packages / ARCHIVE
    manifest = packages / 'build-manifest.json'
    build = json.loads(manifest.read_bytes())
    assert build['filename'] == ARCHIVE and build['version'] == '0.1.0'
    assert build['sha256'] == digest(archive) and build['bytes'] == archive.stat().st_size
    if reference is not None:
        assert archive.read_bytes() == (reference / ARCHIVE).read_bytes()
        assert manifest.read_bytes() == (reference / manifest.name).read_bytes()
    sdk = json.loads(receipt.read_bytes())
    lock = json.loads((ROOT / 'PYTHON-LOCK.json').read_bytes())
    minor = f'{sys.version_info.major}.{sys.version_info.minor}'
    pin = lock['python_archives'][sys.platform][minor]
    assert sdk['status'] == 'PASS' and sdk['archive'] == pin
    assert sdk['platform'] == sys.platform and sdk['python_version'] == platform.python_version() == pin['python']
    assert sdk['python_lock_sha256'] == digest(ROOT / 'PYTHON-LOCK.json')
    assert sdk['preparation_helper_sha256'] == digest(ROOT / 'packaging/prepare_python.py')
    assert sdk['executable_sha256'] == digest(Path(sys._base_executable))

    workspace = workspace.resolve()
    workspace.mkdir()
    source = workspace / ARCHIVE.removesuffix('.zip')
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        assert len({item.filename.casefold() for item in members}) == len(members) == build['files']
        for item in members:
            name = item.filename
            parts = name.split('/')
            assert len(parts) > 1 and parts[0] == source.name
            assert str(PurePosixPath(name)) == name and all(part not in ('', '.', '..') for part in parts)
            assert ':' not in name and '\\' not in name and item.file_size < 1024 * 1024
            assert stat.S_ISREG(item.external_attr >> 16)
        assert bundle.testzip() is None
        bundle.extractall(workspace)

    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1')

    def run(args, cwd, expected=0):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                capture_output=True, encoding='utf-8', timeout=90)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    run([sys.executable, '-I', '-B', '-m', 'venv', workspace / 'venv'], workspace)
    python = workspace / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    report_path = workspace / 'pip-private.json'
    wheel_lock = json.loads((source / 'WHEEL-LOCK.json').read_bytes())
    expected_packages = dict(wheel_lock['packages'])
    if os.name != 'nt':
        expected_packages.pop('colorama')
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'install',
         '--index-url', wheel_lock['index'], '--only-binary=:all:', '--require-hashes',
         '--report', report_path, '-r', source / 'requirements-test.txt'], workspace)
    receipt = json.loads(report_path.read_bytes())
    installed = {}
    for item in receipt['install']:
        name = item['metadata']['name'].lower().replace('_', '-')
        pin = expected_packages[name]
        assert name not in installed and item['metadata']['version'] == pin['version']
        download = item['download_info']
        sha256 = download['archive_info']['hashes']['sha256']
        wheel, = [record for record in pin['wheels'] if record['sha256'] == sha256 and record['url'] == download['url']]
        installed[name] = dict(version=pin['version'], filename=wheel['filename'], sha256=sha256)
    assert installed.keys() == expected_packages.keys()
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'check'], workspace)
    versions = json.loads(run([python, '-I', '-B', '-c',
        'import importlib.metadata as m,json; print(json.dumps({d.metadata["Name"].lower().replace("_", "-"): d.version for d in m.distributions()}))'], workspace).stdout)
    assert {n: v for n, v in versions.items() if n not in {'pip', 'setuptools'}} == {n: d['version'] for n, d in installed.items()}
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    junit = workspace / 'pytest-results.xml'
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    run([python, '-B', '-W', 'error', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
         '--junitxml', junit, 'tests'], source)
    suite = ET.parse(junit).getroot().find('testsuite')
    assert tuple(int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')) == (5, 0, 0, 0)
    test_ids = [node.get('classname') + '.' + node.get('name') for node in suite.findall('testcase')]
    assert len(set(test_ids)) == len(test_ids) == 5

    env['PYTHONPATH'] = str(source)
    report = run([python, '-B', '-W', 'error', '-c', '''
import json
import math
from pathlib import Path
import sys

from sentinel_monitor import charting, formatting


root = Path(sys.argv[1]).resolve() / 'sentinel_monitor'
assert Path(charting.__file__).resolve() == root / 'charting.py'
assert Path(formatting.__file__).resolve() == root / 'formatting.py'

empty_samples = [None, math.nan, math.inf, -math.inf]
assert charting.percentile(empty_samples, 0.5) is None
assert charting.series_stats(empty_samples) is None
assert charting.nice_axis_max(empty_samples) == 1.0

samples = [10.0, None, 0.0, 20.0, math.nan, math.inf]
assert charting.percentile(samples, 0.0) == 0.0
assert charting.percentile(samples, 0.25) == 5.0
assert charting.percentile(samples, 1.0) == 20.0
assert charting.percentile([None, 3.0], 0.95) == 3.0

for fraction in (-0.01, 1.01):
    try:
        charting.percentile(samples, fraction)
    except ValueError as error:
        assert 'between 0 and 1' in str(error)
    else:
        raise AssertionError('Out-of-range percentile accepted')

stats = charting.series_stats([10.0, -10.0, None, math.nan, 20.0, math.inf])
assert stats is not None
assert (stats.minimum, stats.maximum) == (-10.0, 20.0)
assert math.isclose(stats.average, 20.0 / 3.0)
assert math.isclose(stats.p95, 19.0)

assert [charting.nice_axis_max([v], headroom=1.0)
        for v in (1.0, 1.1, 2.1, 5.1, 10.1)] == [1.0, 2.0, 5.0, 10.0, 20.0]
assert charting.nice_axis_max([10.0]) == 20.0
assert charting.nice_axis_max([-5000.0, None], minimum=0.5) == 0.5

assert formatting.format_bytes(1023) == '1023 B'
assert formatting.format_bytes(1024) == '1.0 KB'
assert formatting.format_bytes(-1536) == '-1.5 KB'

assert formatting.format_bytes(512, per_second=True) == '512 B/s'
assert formatting.format_bytes(1024 ** 2, per_second=True) == '1.0 MB/s'
assert formatting.format_bytes(1024 ** 3, per_second=True) == '1.0 GB/s'

assert formatting.format_duration(-60.0) == '0h 0m'
assert formatting.format_duration(59.9) == '0h 0m'
assert formatting.format_duration(60.0) == '0h 1m'
assert formatting.format_duration(86399) == '23h 59m'
assert formatting.format_duration(86400) == '1d 0h 0m'
assert formatting.format_duration(90061) == '1d 1h 1m'

print(json.dumps([
    'empty_non_finite_samples',
    'percentile_endpoints_and_interpolation',
    'invalid_percentile_fraction',
    'series_summary',
    'axis_rounding_and_headroom',
    'byte_unit_boundaries',
    'transfer_rate_units',
    'duration_boundaries',
]))
''', source], workspace)
    api_checks = json.loads(report.stdout)
    assert len(api_checks) == len(set(api_checks)) == 8 and not report.stderr
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    evidence = dict(status='PASS', package='telemetry-chart-statistics', version='0.1.0', platform=sys.platform,
        python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=5, passed=5, failures=0, errors=0, skipped=0, test_ids=test_ids,
        api_checks=api_checks, synthetic_samples=True, dependencies=installed, pip_version=versions['pip'],
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with receipt_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('TELEMETRYCHART_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
