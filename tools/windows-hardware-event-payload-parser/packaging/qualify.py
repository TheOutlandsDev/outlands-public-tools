"""Validate the released source ZIP on a verified interpreter and a fresh test environment."""

import argparse
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
PACKAGE = 'windows-hardware-event-payload-parser'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_parse_event_payload_classifies_whea_and_nvidia',
    'test_storage_providers_are_classified_for_guardian_gating',
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
    assert packages.resolve() != reference.resolve(), 'Independent rebuild must use a separate directory'
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
    assert tuple(int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')) == (5, 0, 0, 0)
    cases = suite.findall('testcase')
    ids = [node.get('classname') + '.' + node.get('name') for node in cases]
    assert len(set(ids)) == len(ids) == 5
    assert ORIGINAL_TESTS <= {node.get('name') for node in cases}
    return installed, versions['pip'], ids


def check_offline_cli(run, source, workspace):
    timestamp = '2040-01-02T03:04:05+00:00'
    pcie = {
        'channel': 'System',
        'record_id': 31,
        'timestamp': timestamp,
        'provider': 'Microsoft-Windows-WHEA-Logger',
        'event_id': 17,
        'level': '  Warning ',
        'message': ' Fictional\tPCIe\u200b\n  warning ',
    }
    storage = {
        'channel': 'System',
        'record_id': 29,
        'timestamp': timestamp,
        'provider': 'Disk',
        'event_id': 7,
        'level': 'Error',
        'message': 'Fictional disk failure.',
    }
    generic = {
        'record_id': '32',
        'timestamp': timestamp,
        'provider': 'Fictional Provider',
        'event_id': '1',
    }

    samples = {
        'windows-events.json': (
            json.dumps([pcie, None, dict(storage, timestamp='not a date'), {}, storage])
            .encode('utf-8-sig')
        ),
        'singleton.json': json.dumps(generic).encode('utf-8'),
        'blank.json': ' \t\n'.encode('utf-8-sig'),
        'invalid-json.json': b'{"provider":',
        'invalid-encoding.json': b'\xff',
        'oversized.json': b' ' * (4 * 1024 * 1024 + 1),
    }
    for name, raw in samples.items():
        (workspace / name).write_bytes(raw)
    query = workspace / 'windows-events.json'
    example_path = source / 'examples/events.json'
    inputs = {path: digest(path) for path in [example_path, *(workspace / name for name in samples)]}
    before = set(workspace.iterdir())
    env = {'PYTHONPATH': str(source)}
    base = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*base, '-m', 'sentinel_monitor']

    def output(result):
        assert not result.stderr
        result_json = json.loads(result.stdout)
        assert set(result_json) == {'events'}
        return result_json['events']

    first = output(run([*cli, '--input', query], extra_env=env))
    expected = []
    for row, category, severity, message in (
        (pcie, 'WHEA PCIe', 'warning', 'Fictional PCIe warning'),
        (storage, 'Storage', 'critical', 'Fictional disk failure.'),
    ):
        event = {key: value for key, value in row.items() if key != 'level'}
        event.update(category=category, severity=severity, message=message)
        expected.append(event)
    assert first == expected

    singleton = output(run([*cli, '--input', workspace / 'singleton.json'], extra_env=env))
    assert singleton == [{
        'channel': 'System', 'record_id': 32, 'timestamp': timestamp,
        'provider': 'Fictional Provider', 'event_id': 1, 'category': 'System hardware',
        'severity': 'info', 'message': '',
    }]
    assert output(run([*cli, '--input', workspace / 'blank.json'], extra_env=env)) == []

    example = output(run([*cli, '--input', example_path], extra_env=env))
    assert [(row['record_id'], row['category'], row['severity']) for row in example] == [
        (101, 'WHEA Corrected Hardware', 'warning'),
        (102, 'NVIDIA driver', 'critical'),
        (103, 'Storage', 'warning'),
        (104, 'Application crash', 'critical'),
    ]

    offline_check = """
import os
from pathlib import Path
import runpy
import sys

def verify_offline(event, args):
    if event in {"subprocess.Popen", "os.exec", "os.system", "os.spawn", "os.posix_spawn"} or event.startswith("socket."):
        raise AssertionError("The offline CLI attempted process or network access")
    if event == "open" and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError("The offline CLI attempted to open a file for writing")

sys.addaudithook(verify_offline)
import sentinel_monitor
source = Path(sys.argv.pop(1))
assert Path(sentinel_monitor.__file__).resolve().parent == source / "sentinel_monitor"
runpy.run_module("sentinel_monitor", run_name="__main__", alter_sys=True)
"""
    checked = output(run([*base, '-c', offline_check, source, '--input', query], extra_env=env))
    assert checked == first

    for wrong in (
        workspace / 'invalid-json.json', workspace / 'invalid-encoding.json',
        workspace / 'oversized.json',
        workspace, workspace / 'missing.json',
    ):
        rejected = run([*cli, '--input', wrong], expected=2, extra_env=env)
        assert rejected.stderr and not rejected.stdout and 'Traceback' not in rejected.stderr
    assert {path: digest(path) for path in inputs} == inputs and set(workspace.iterdir()) == before
    return [
        'copied_cli_utf8_bom',
        'provider_and_severity_mapping',
        'message_cleaning',
        'malformed_records_skipped_in_input_order',
        'singleton_defaults_and_blank_payload',
        'packaged_fictional_example',
        'malformed_or_unreadable_input_refused',
        'oversized_input_refused',
        'offline_cli_with_process_and_network_audit_guard',
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
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_event_log_used=False,
        runtime_dependencies=[], dependencies=installed, pip_version=pip_version,
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('EVENTPAYLOAD_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
