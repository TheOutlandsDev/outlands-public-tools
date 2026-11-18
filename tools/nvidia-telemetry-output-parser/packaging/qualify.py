"""Validate the released source ZIP on a verified interpreter and a fresh test environment."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
import zipfile
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'nvidia-telemetry-output-parser'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_number_handles_nvidia_missing_values',
    'test_collect_parses_driver_and_pci_metadata',
    'test_parse_replay_counters_maps_each_pci_bus',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unpack(packages, workspace, reference):
    archive = packages / ARCHIVE
    build = json.loads((packages / 'build-manifest.json').read_bytes())
    assert build['schema'] == 1 and build['package'] == PACKAGE
    assert build['filename'] == ARCHIVE and build['version'] == VERSION
    assert isinstance(build['source_revision'], str)
    assert re.fullmatch('[0-9a-f]{40}', build['source_revision'])
    assert build['sha256'] == digest(archive) and build['bytes'] == archive.stat().st_size
    line = f"{build['sha256']}  {ARCHIVE}\n"
    assert (packages / 'SHA256SUMS.txt').read_bytes() == line.encode('ascii')
    if reference is not None:
        for filename in (ARCHIVE, 'build-manifest.json', 'SHA256SUMS.txt'):
            assert (packages / filename).read_bytes() == (reference / filename).read_bytes()

    workspace.mkdir()
    source = workspace / ARCHIVE.removesuffix('.zip')
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        assert len({item.filename.casefold() for item in members}) == len(members) == build['files']
        assert 0 < len(members) < 100
        names = set()
        for item in members:
            name = item.filename
            parts = name.split('/')
            assert len(parts) > 1 and parts[0] == source.name
            assert str(PurePosixPath(name)) == name and all(part not in ('', '.', '..') for part in parts)
            assert ':' not in name and '\\' not in name and item.file_size < 1024 * 1024
            assert stat.S_ISREG(item.external_attr >> 16)
            names.add('/'.join(parts[1:]))
        assert bundle.testzip() is None
        bundle.extractall(workspace)
    return build, source, names


def check_interpreter(receipt):
    sdk = json.loads(receipt.read_bytes())
    lock = json.loads((ROOT / 'PYTHON-LOCK.json').read_bytes())
    minor = f'{sys.version_info.major}.{sys.version_info.minor}'
    pin = lock['python_archives'][sys.platform][minor]
    assert sdk['status'] == 'PASS' and sdk['archive'] == pin
    assert sdk['platform'] == sys.platform and sdk['python_version'] == platform.python_version() == pin['python']
    assert sdk['python_lock_sha256'] == digest(ROOT / 'PYTHON-LOCK.json')
    assert sdk['preparation_helper_sha256'] == digest(ROOT / 'packaging/prepare_python.py')
    assert sdk['executable_sha256'] == digest(Path(sys._base_executable))
    return sdk


def install_and_test(run, source, workspace):
    run([sys.executable, '-I', '-B', '-m', 'venv', workspace / 'venv'])
    python = workspace / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    report_path = workspace / 'pip-private.json'
    wheel_lock = json.loads((source / 'WHEEL-LOCK.json').read_bytes())
    pins = dict(wheel_lock['packages'])
    if os.name != 'nt':
        pins.pop('colorama')
    pip = [python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check']
    run([*pip, 'install', '--index-url', wheel_lock['index'], '--only-binary=:all:', '--require-hashes',
         '--report', report_path, '-r', source / 'requirements-test.txt'])

    installed = {}
    for item in json.loads(report_path.read_bytes())['install']:
        name = item['metadata']['name'].lower().replace('_', '-')
        pin = pins[name]
        assert name not in installed and item['metadata']['version'] == pin['version']
        download = item['download_info']
        sha256 = download['archive_info']['hashes']['sha256']
        wheel, = [record for record in pin['wheels']
                  if record['sha256'] == sha256 and record['url'] == download['url']]
        installed[name] = dict(version=pin['version'], filename=wheel['filename'], sha256=sha256)
    assert installed.keys() == pins.keys()
    run([*pip, 'check'])
    versions_code = ('import importlib.metadata as m,json; '
                     'print(json.dumps({d.metadata["Name"].lower().replace("_", "-"): d.version '
                     'for d in m.distributions()}))')
    versions = json.loads(run([python, '-I', '-B', '-c', versions_code]).stdout)
    assert {n: v for n, v in versions.items() if n not in {'pip', 'setuptools'}} == {
        n: d['version'] for n, d in installed.items()
    }
    run([python, '-I', '-B', source / 'source_check.py'])
    junit = workspace / 'pytest-results.xml'
    run([python, '-B', '-W', 'error', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
         '--junitxml', junit, 'tests'], cwd=source)
    suite = ElementTree.parse(junit).getroot().find('testsuite')
    assert tuple(int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')) == (6, 0, 0, 0)
    cases = suite.findall('testcase')
    ids = [node.get('classname') + '.' + node.get('name') for node in cases]
    assert len(set(ids)) == len(ids) == 6
    assert ORIGINAL_TESTS <= {node.get('name') for node in cases}
    return installed, versions['pip'], ids


def check_offline_cli(run, source, workspace):
    version = '000.42'
    alpha_bus = '0000:01:00.0'
    beta_bus = '0000:02:00.0'
    alpha = (0, 'synthetic-alpha', 'Synthetic GPU, Alpha', '40', '5', '7', '112', '1024',
             '45', '60', '12', 'P8', '350', '450', 'fictional-alpha', alpha_bus, version, 'TCC', 'TCC')
    beta = (1, 'synthetic-beta', 'Synthetic GPU Beta', '[N/A]', '15', 'NOT SUPPORTED', '96', '1024',
            '[N/A]', '65', '', 'P8', 'NaN', 'inf', 'fictional-beta', beta_bus, version, 'WDDM', 'WDDM')
    query = workspace / 'fictional-query.csv'
    replay = workspace / 'fictional-replay.txt'
    with query.open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerows((alpha, ('wrong shape',), ('bad index', *beta[1:]), beta))
    replay.write_text(
        f'Replays Since Reset : 89\n'
        f'Bus Id : {beta_bus}\n    Replays Since Reset : 0\n'
        f'Bus Id : {alpha_bus}\n    Replays Since Reset : 7\n',
        encoding='utf-8',
    )
    invalid_text = workspace / 'invalid-encoding.csv'
    invalid_text.write_bytes(b'\xff')
    oversized = workspace / 'oversized.csv'
    oversized.write_bytes(b'x' * (4 * 1024 * 1024 + 1))
    oversized_field = workspace / 'oversized-field.csv'
    oversized_field.write_bytes(b'x' * (2 * 1024 * 1024))
    example_query = source / 'examples/query.csv'
    example_replay = source / 'examples/replay.txt'
    inputs = {path: digest(path) for path in (query, replay, invalid_text, oversized, oversized_field, example_query, example_replay)}
    before = set(workspace.iterdir())
    env = {'PYTHONPATH': str(source)}
    base = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*base, '-m', 'sentinel_monitor']

    def output(result):
        assert not result.stderr
        payload = json.loads(result.stdout)
        assert set(payload) == {'readings', 'status'}
        return payload

    first = output(run([*cli, '--csv', query, '--replay', replay], extra_env=env))
    reading_alpha, reading_beta = first['readings']
    assert [reading_alpha['index'], reading_beta['index']] == [0, 1]
    assert [reading_alpha['name'], reading_beta['name']] == ['Synthetic GPU, Alpha', 'Synthetic GPU Beta']
    assert reading_alpha['temperature_c'] == 40.0 and reading_beta['temperature_c'] is None
    assert all(reading_beta[field] is None for field in ('power_draw_w', 'fan_percent', 'memory_utilization_percent'))
    assert all(reading_beta[field] is None for field in ('graphics_clock_mhz', 'memory_clock_mhz'))
    assert [reading_alpha['pci_bus_id'], reading_beta['pci_bus_id']] == [alpha_bus, beta_bus]
    assert [reading_alpha['pcie_replays_since_reset'], reading_beta['pcie_replays_since_reset']] == [7, 0]
    assert reading_alpha['driver_version'] == reading_beta['driver_version'] == version
    assert [reading_alpha['driver_model_current'], reading_beta['driver_model_current']] == ['TCC', 'WDDM']
    assert first['status'] == 'Active: 2 NVIDIA GPU(s) | driver 000.42 | TCC/WDDM | PCIe replay GPU 0=7 GPU 1=0'
    without_replay = output(run([*cli, '--csv', query], extra_env=env))
    assert [item['pcie_replays_since_reset'] for item in without_replay['readings']] == [None, None]
    assert 'PCIe replay' not in without_replay['status']

    offline_check = '''
from pathlib import Path
import runpy
import sys

def verify_offline(event, args):
    if event in {"subprocess.Popen", "os.exec", "os.system", "os.spawn", "os.posix_spawn"} or event.startswith("socket."):
        raise AssertionError("The offline CLI attempted process or network access")

sys.addaudithook(verify_offline)
import sentinel_monitor
assert Path(sentinel_monitor.__file__).resolve().parent == Path(sys.argv.pop(1)) / "sentinel_monitor"
runpy.run_module("sentinel_monitor", run_name="__main__", alter_sys=True)
'''
    checked = output(run([*base, '-c', offline_check, source, '--csv', query, '--replay', replay], extra_env=env))
    assert checked == first
    example = output(run([*cli, '--csv', example_query, '--replay', example_replay], extra_env=env))
    assert sorted(item['pcie_replays_since_reset'] for item in example['readings']) == [0, 7]
    assert any(item['temperature_c'] is None for item in example['readings'])

    for wrong in (invalid_text, oversized, oversized_field, workspace, workspace / 'missing.csv'):
        rejected = run([*cli, '--csv', wrong], expected=2, extra_env=env)
        assert rejected.stderr and not rejected.stdout and 'Traceback' not in rejected.stderr
    rejected_replay = run([*cli, '--csv', query, '--replay', oversized], expected=2, extra_env=env)
    assert rejected_replay.stderr and not rejected_replay.stdout and 'Traceback' not in rejected_replay.stderr
    assert {path: digest(path) for path in inputs} == inputs and set(workspace.iterdir()) == before
    return [
        'copied_cli_utf8_bom_and_csv_quoted_fields',
        'malformed_rows_skipped',
        'missing_and_nonfinite_numeric_fields_are_null',
        'driver_and_pci_bus_metadata',
        'per_bus_replay_counts_include_zero',
        'optional_replay_counts_omitted_as_null',
        'offline_cli_with_process_and_network_audit_guard',
        'packaged_fictional_examples',
        'invalid_or_oversize_input_refused',
        'source_and_input_files_unchanged',
    ]


def qualify(packages, workspace, report, receipt, reference):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    workspace = workspace.resolve()
    sdk = check_interpreter(receipt)
    build, source, names = unpack(packages, workspace, reference)
    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PIP_', 'LD_', 'DYLD_', 'PYTEST_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')

    def run(args, *, cwd=workspace, expected=0, extra_env=None):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env | (extra_env or {}),
                                capture_output=True, encoding='utf-8', timeout=90)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    installed, pip_version, test_ids = install_and_test(run, source, workspace)
    cli_checks = check_offline_cli(run, source, workspace)
    run([sys.executable, '-I', '-B', source / 'source_check.py'])
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} == names
    evidence = dict(
        status='PASS', package=PACKAGE, version=VERSION, platform=sys.platform, python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=len(ORIGINAL_TESTS), passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_hardware_used=False,
        runtime_dependencies=[], dependencies=installed, pip_version=pip_version,
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=reference is not None, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('NVIDIAPARSER_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
