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

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'process-listener-evidence'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_process_listener_evidence.OriginalEvidenceTests.test_exact_identity_requires_one_exact_executable',
    'test_process_listener_evidence.OriginalEvidenceTests.test_listener_proof_requires_every_port_owned_by_exact_pid',
    'test_process_listener_evidence.OriginalEvidenceTests.test_rooted_identity_accepts_versioned_release_but_rejects_other_roots',
}
FOCUSED_TESTS = {
    'test_process_listener_evidence.EvidenceRegressionTests.test_multiple_matching_processes_fail_identity',
    'test_process_listener_evidence.EvidenceRegressionTests.test_empty_and_mixed_listener_owners_fail',
    'test_process_listener_evidence.EvidenceRegressionTests.test_windows_lexical_paths_use_windows_rules',
    'test_process_listener_evidence.EvidenceRegressionTests.test_posix_paths_are_case_sensitive_and_check_component_boundaries',
    'test_process_listener_evidence.EvidenceRegressionTests.test_fictional_windows_and_posix_examples',
    'test_process_listener_evidence.EvidenceRegressionTests.test_cli_never_credits_listeners_to_ambiguous_processes',
    'test_process_listener_evidence.EvidenceRegressionTests.test_malformed_evidence_is_refused_without_exposing_input',
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


def run_tests(run, source, workspace):
    prefix = workspace / 'venv'
    run([sys.executable, '-I', '-B', '-m', 'venv', '--without-pip', prefix])
    python = prefix / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    test_code = """
import importlib.metadata
import json
from pathlib import Path
import sys
import unittest


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item.id()


source = Path(sys.argv[1])
assert Path(sys.prefix) == Path(sys.argv[2])
assert sys.prefix != sys.base_prefix
assert not list(importlib.metadata.distributions())
sys.path.insert(0, str(source))
loader = unittest.TestLoader()
suite = loader.discover(str(source / 'tests'))
identifiers = sorted(cases(suite))
assert not loader.errors
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun == len(identifiers)
assert result.wasSuccessful()
assert not (result.skipped or result.expectedFailures or result.unexpectedSuccesses)
print(json.dumps(identifiers))
"""
    result = run([python, '-I', '-B', '-W', 'error', '-c', test_code, source, prefix], cwd=source)
    identifiers = json.loads(result.stdout)
    assert len(identifiers) == len(ORIGINAL_TESTS) + len(FOCUSED_TESTS)
    assert set(identifiers) == ORIGINAL_TESTS | FOCUSED_TESTS
    return identifiers


def check_offline_cli(run, source, workspace):
    limit = 4 * 1024 * 1024
    windows_sample = source / "examples/proven-windows.json"
    posix_sample = source / "examples/unavailable-posix.json"
    marker = "fictional-private-diagnostic-marker"
    created = "2042-03-18T12:00:00Z"
    pid = 6201
    tcp = {"protocol": "tcp", "port": 46106}
    udp = {"protocol": "udp", "port": 46106}

    def record(executable, *, process_id=pid):
        return {
            "pid": process_id, "ppid": 1, "name": "lantern-service",
            "executable": executable, "created_utc": created,
        }

    def evidence(style, mode, path, processes, *, expected=(tcp, udp), owners=None):
        if owners is None:
            owners = [{**listener, "pids": [pid]} for listener in expected]
        return {
            "identity": {"path_style": style, "mode": mode, "name": "LANTERN-SERVICE", "path": path},
            "processes": processes, "expected_listeners": list(expected), "listener_owners": owners,
        }

    def encoded(document):
        return json.dumps(document).encode("utf-8")

    def receipt(status, identity, pids, listener, timestamp=None):
        return {
            "status": status,
            "identity": {"state": identity, "pids": pids, "created_utc": timestamp},
            "listener_state": listener,
        }

    windows = evidence("windows", "exact", "Q:/Example/Build/lantern.exe", [
        record(r"q:\example\build\staged\..\LANTERN.EXE"),
    ])
    windows["metadata"] = marker
    windows["identity"]["metadata"] = marker
    windows["processes"][0]["metadata"] = marker
    windows["listener_owners"][0]["metadata"] = marker
    posix = evidence("posix", "rooted", "/fixture/lantern/versions", [
        record("/fixture/lantern/versions/r012/lantern"),
    ])
    posix_sibling = evidence("posix", "rooted", "/fixture/lantern/versions", [
        record("/fixture/lantern/versions-copy/r012/lantern"),
    ])
    posix_different_case = evidence("posix", "exact", "/fixture/lantern/Lantern", [
        record("/fixture/lantern/lantern"),
    ])
    windows_sibling = evidence("windows", "rooted", r"Q:\Example\Build", [
        record(r"Q:\Example\Build-copy\lantern.exe"),
    ])
    duplicates = evidence("windows", "exact", r"Q:\Example\Build\lantern.exe", [
        record(r"Q:\Example\Build\lantern.exe"),
        record(r"Q:\Example\Build\lantern.exe", process_id=6202),
    ])
    empty_listeners = {**windows, "expected_listeners": []}
    unexpected_owner = {**windows, "listener_owners": [
        {**tcp, "pids": [pid]},
        {**udp, "pids": [pid, 7301]},
    ]}
    wrong_protocol = {**windows, "listener_owners": [{**tcp, "pids": [pid]}]}

    cases = {
        "windows.json": encoded(windows),
        "windows-sibling.json": encoded(windows_sibling),
        "posix.json": encoded(posix),
        "posix-sibling.json": encoded(posix_sibling),
        "posix-wrong-case.json": encoded(posix_different_case),
        "duplicates.json": encoded(duplicates),
        "empty-listeners.json": encoded(empty_listeners),
        "unexpected-owner.json": encoded(unexpected_owner),
        "wrong-protocol.json": encoded(wrong_protocol),
        "max-bytes.json": encoded(windows).ljust(limit, b" "),
        "too-many-bytes.json": encoded(windows).ljust(limit + 1, b" "),
        "invalid-utf8.json": bytes.fromhex("fffe"),
        "duplicate-json-key.json": b'{"identity": {}, "identity": {}}',
        "nonfinite.json": encoded({**windows, "metadata": float("nan")}),
        "wrong-document.json": b"[]",
        "repeated-pid.json": encoded({**windows, "processes": [windows["processes"][0]] * 2}),
        "repeated-ownership.json": encoded({**windows, "listener_owners": [windows["listener_owners"][0]] * 2}),
        "boolean-pid.json": encoded({**windows, "processes": [record(r"Q:\Example\Build\lantern.exe", process_id=True)]}),
        "bad-port.json": encoded({**windows, "expected_listeners": [{"protocol": "tcp", "port": 65536}]}),
        "bad-style.json": encoded({**windows, "identity": {**windows["identity"], "path_style": marker}}),
        "drive-relative.json": encoded({**windows, "identity": {**windows["identity"], "path": "Q:lantern.exe"}}),
        f"{marker}.json": b'{"identity": "' + marker.encode("ascii"),
    }
    for name, raw in cases.items():
        (workspace / name).write_bytes(raw)

    inputs = [windows_sample, posix_sample, *(workspace / name for name in cases)]
    initial = {path: digest(path) for path in inputs}
    original_paths = set(workspace.iterdir())
    env = {"PYTHONPATH": str(source)}
    python = [sys.executable, "-B", "-S", "-W", "error"]
    cli = [*python, "-m", "process_listener_evidence"]

    def valid(result):
        assert not result.stderr
        report = json.loads(result.stdout)
        assert marker not in result.stdout
        return report

    def invoke(path, expected=0):
        result = run([*cli, "--input", path], expected=expected, extra_env=env)
        return valid(result)

    def refused(*args):
        result = run([*cli, *args], expected=2, extra_env=env)
        assert not result.stdout and result.stderr
        assert all(value not in result.stderr for value in ("Traceback", marker, str(workspace), str(source)))

    windows_sample_report = receipt("proven", "proven", [4101], "proven", created)
    posix_sample_report = receipt("unavailable", "unavailable", [], "failed")
    assert invoke(windows_sample) == windows_sample_report
    assert invoke(posix_sample, expected=1) == posix_sample_report
    accepted = receipt("proven", "proven", [pid], "proven", created)
    for name in ("windows.json", "posix.json", "max-bytes.json"):
        assert invoke(workspace / name) == accepted
    no_match = receipt("failed", "failed", [], "failed")
    for name in ("windows-sibling.json", "posix-sibling.json", "posix-wrong-case.json"):
        assert invoke(workspace / name, expected=1) == no_match
    assert invoke(workspace / "duplicates.json", expected=1) == receipt("failed", "failed", [pid, 6202], "failed")
    no_listeners = receipt("failed", "proven", [pid], "failed", created)
    for name in ("empty-listeners.json", "unexpected-owner.json", "wrong-protocol.json"):
        assert invoke(workspace / name, expected=1) == no_listeners

    invalid_cases = (
        "too-many-bytes.json", "invalid-utf8.json", "duplicate-json-key.json", "nonfinite.json",
        "wrong-document.json", "repeated-pid.json", "repeated-ownership.json", "boolean-pid.json",
        "bad-port.json", "bad-style.json", "drive-relative.json", f"{marker}.json", "missing.json", ".",
    )
    for name in invalid_cases:
        refused("--input", workspace / name)
    refused(f"--{marker}")

    audit = """
import os
from pathlib import Path
import runpy
import sys


source = Path(sys.argv.pop(1))


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn', 'os.startfile',
                 'os.kill', 'ctypes.dlopen'} or event.startswith('socket.'):
        raise AssertionError('Evidence checker attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Evidence checker attempted a write')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp', 'sqlite3.connect'}:
        raise AssertionError('Evidence checker attempted mutation or database access')


sys.addaudithook(verify_offline)
import process_listener_evidence
assert Path(process_listener_evidence.__file__).resolve().parent == source / 'process_listener_evidence'
runpy.run_module('process_listener_evidence', run_name='__main__', alter_sys=True)
"""
    for path, code, expected in ((windows_sample, 0, windows_sample_report), (posix_sample, 1, posix_sample_report)):
        result = run([*python, "-c", audit, source, "--input", path], expected=code, extra_env=env)
        assert valid(result) == expected

    assert {path: digest(path) for path in initial} == initial
    assert set(workspace.iterdir()) == original_paths
    return [
        "packaged_proven_windows",
        "packaged_unavailable_posix",
        "portable_windows_path_comparison",
        "portable_posix_path_comparison",
        "duplicate_matches_fail",
        "empty_listener_declarations_fail",
        "unexpected_listener_owner_fails",
        "strict_json_and_bounded_input",
        "malformed_saved_evidence_refused",
        "opaque_diagnostics",
        "metadata_omitted_from_report",
        "offline_read_only_audit_guard",
        "extracted_source_and_input_bytes_unchanged",
    ]

def qualify(packages, workspace, report, receipt, reference):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    workspace = workspace.resolve()
    sdk = check_interpreter(receipt)
    build, source, names = unpack(packages, workspace, reference)
    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1')

    def run(args, *, cwd=workspace, expected=0, extra_env=None):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env | (extra_env or {}),
                                capture_output=True, encoding='utf-8', timeout=90)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    test_ids = run_tests(run, source, workspace)
    cli_checks = check_offline_cli(run, source, workspace)
    run([sys.executable, '-I', '-B', source / 'source_check.py'])
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} == names
    evidence = dict(
        status='PASS', package=PACKAGE, version=VERSION, platform=sys.platform, python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=len(ORIGINAL_TESTS), passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('PROCESS_LISTENER_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
