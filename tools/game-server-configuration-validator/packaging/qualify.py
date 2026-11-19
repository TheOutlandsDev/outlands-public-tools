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
PACKAGE = 'game-server-configuration-validator'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_config.GameServerConfigOriginalTests.test_config_rejects_non_loopback',
    'test_config.GameServerConfigOriginalTests.test_config_rejects_invalid_expected_state',
    'test_probe_config.PlayerProbeConfigOriginalTests.test_player_probe_accepts_loopback',
    'test_probe_config.PlayerProbeConfigOriginalTests.test_player_probe_rejects_non_loopback',
    'test_probe_config.PlayerProbeConfigOriginalTests.test_player_probe_rejects_unknown_type',
}
FOCUSED_TESTS = {
    'test_validator.GameServerConfigValidationTests.test_accepts_ipv6_loopback_health_and_player_probe',
    'test_validator.GameServerConfigValidationTests.test_validates_port_boundaries',
    'test_validator.GameServerConfigValidationTests.test_credential_diagnostics_omit_input',
    'test_validator.GameServerConfigValidationTests.test_accepts_portable_absolute_jsonl_paths',
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
    a2s = {"type": "a2s", "host": "127.0.0.1", "port": 1}
    quake = {"type": "quake3", "host": "::1", "port": 65535}
    sessions = {"type": "tcp_sessions", "host": "localhost", "port": 27015}
    probe_path = {"type": "jsonl_population", "path": "/fictional/players.jsonl"}

    def declaration(**fields):
        return {
            "schema_version": 1,
            "servers": [{"id": "fictional-server", "root": "/fictional/service", **fields}],
        }

    def encoded(config):
        return json.dumps(config, ensure_ascii=False).encode("utf-8")

    baseline = encoded(declaration(
        expected_state="online", health_urls=["http://127.0.0.1:1/health"],
        player_probe=a2s,
    ))
    credentials = "https://fictional-user-42:fictional-secret-83@[::1]:443/secret-path-76?token=fictional-token-95"
    fixtures = {
        "ipv4.json": baseline,
        "ipv6.json": encoded(declaration(
            expected_state="planned_off", health_urls=["https://[::1]:65535/status"],
            player_probe=quake, root=r"C:\Fictional\Service",
        )),
        "localhost.json": encoded(declaration(
            health_urls=["https://localhost/status"], player_probe=sessions,
        )),
        "absolute-posix.json": encoded(declaration(player_probe=probe_path)),
        "absolute-windows.json": encoded(declaration(
            player_probe={**probe_path, "path": r"C:\Fictional\Players.jsonl"},
        )),
        "relative-path.json": encoded(declaration(player_probe={**probe_path, "path": "some-private-file.jsonl"})),
        "unknown-probe.json": encoded(declaration(player_probe={**a2s, "type": "fictional-invalid-probe"})),
        "expected-state.json": encoded(declaration(expected_state="fictional-invalid-state")),
        "health-remote.json": encoded(declaration(health_urls=["https://fictional-host.invalid/health"])),
        "probe-remote.json": encoded(declaration(player_probe={**a2s, "host": "192.0.2.10"})),
        "credentials.json": encoded(declaration(health_urls=[credentials], id="fictional-private-server-id")),
        "port-too-low.json": encoded(declaration(player_probe={**a2s, "port": 0})),
        "port-too-high.json": encoded(declaration(player_probe={**a2s, "port": 65536})),
        "port-bool.json": encoded(declaration(player_probe={**a2s, "port": True})),
        "port-fraction.json": encoded(declaration(player_probe={**a2s, "port": 1.5})),
        "health-port-too-low.json": encoded(declaration(health_urls=["http://localhost:0/health"])),
        "health-port-too-high.json": encoded(declaration(health_urls=["http://localhost:65536/health"])),
        "health-port-empty.json": encoded(declaration(health_urls=["http://localhost:/health"])),
        "version-bool.json": encoded({"schema_version": True, "servers": []}),
        "bom.json": b"\xef\xbb\xbf" + baseline,
        "duplicate.json": baseline.replace(b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1'),
        "nested-duplicate.json": baseline.replace(b'"port": 1', b'"port": 1, "port": 1'),
        "nonfinite.json": baseline[:-1] + b', "uncounted_value": NaN}',
        "float-overflow.json": baseline[:-1] + b', "uncounted_value": 1e309}',
        "invalid-json.json": b'{"schema_version":',
        "invalid-utf8.json": b'\xff\xfe',
        "not-object.json": b'[]',
        "empty.json": b'',
        "size-limit.json": baseline.ljust(limit, b' '),
        "oversized.json": baseline.ljust(limit + 1, b' '),
    }

    example = source / "examples/server-config.json"
    for name, raw in fixtures.items():
        (workspace / name).write_bytes(raw)

    inputs = [example, *(workspace / name for name in fixtures)]
    initial = {path: digest(path) for path in inputs}
    before = set(workspace.iterdir())
    env = {"PYTHONPATH": str(source)}
    base = [sys.executable, "-B", "-S", "-W", "error"]
    cli = [*base, "-m", "game_server_config"]

    def invoke(name, *, expected=0):
        return run([*cli, "--input", workspace / name], expected=expected, extra_env=env)

    def valid(process, count=1):
        assert not process.stderr
        assert json.loads(process.stdout) == {"status": "valid", "server_count": count}

    def refused(process, message=None, omitted=()):
        assert process.stderr and not process.stdout and "Traceback" not in process.stderr
        if message is not None:
            assert message in process.stderr
        for value in omitted:
            assert value not in process.stderr

    audit = """
import os
from pathlib import Path
import runpy
import sys


source = Path(sys.argv.pop(1))


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn'} or event.startswith('socket.'):
        raise AssertionError('Configuration validator attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Configuration validator attempted a write')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp'}:
        raise AssertionError('Configuration validator attempted a filesystem mutation')


sys.addaudithook(verify_offline)
import game_server_config
assert Path(game_server_config.__file__).resolve().parent == source / 'game_server_config'
runpy.run_module('game_server_config', run_name='__main__', alter_sys=True)
"""

    packaged = run([*base, "-c", audit, source, "--input", example], extra_env=env)
    valid(packaged, count=4)
    for name in ("ipv4.json", "ipv6.json", "localhost.json", "absolute-posix.json",
                 "absolute-windows.json", "bom.json", "size-limit.json"):
        valid(invoke(name))

    invalid = (
        ("relative-path.json", "JSONL player probe path must be absolute", ("some-private-file.jsonl",)),
        ("unknown-probe.json", "Unsupported player probe", ("fictional-invalid-probe",)),
        ("expected-state.json", "Invalid expected state", ("fictional-invalid-state",)),
        ("health-remote.json", "Non-loopback health URL", ("fictional-host.invalid",)),
        ("probe-remote.json", "Non-loopback player probe", ("192.0.2.10",)),
        ("credentials.json", "Credentials are forbidden in health URLs", (
            credentials, "fictional-user-42", "fictional-secret-83", "secret-path-76",
            "fictional-token-95", "fictional-private-server-id",
        )),
    )
    for name, message, omitted in invalid:
        refused(invoke(name, expected=2), message, omitted)
    for name in ("port-too-low.json", "port-too-high.json", "port-bool.json", "port-fraction.json"):
        refused(invoke(name, expected=2), "Invalid player probe port")
    for name in ("health-port-too-low.json", "health-port-too-high.json", "health-port-empty.json"):
        refused(invoke(name, expected=2), "Invalid health URL port", ("localhost",))
    for name in ("version-bool.json", "duplicate.json", "nested-duplicate.json", "nonfinite.json",
                 "float-overflow.json", "invalid-json.json", "invalid-utf8.json", "not-object.json",
                 "empty.json", "oversized.json", "missing.json", "."):
        refused(invoke(name, expected=2))
    refused(run([*cli], expected=2, extra_env=env))
    refused(run([*cli, "--input", example, "--fictional-private-argument"], expected=2, extra_env=env),
            omitted=("fictional-private-argument",))

    assert {path: digest(path) for path in initial} == initial
    assert set(workspace.iterdir()) == before
    return [
        "packaged_fictional_server_config",
        "ipv4_and_ipv6_loopback",
        "supported_player_probe_types",
        "expected_runtime_state_validation",
        "player_probe_port_boundaries",
        "nonloopback_health_urls_and_probe_hosts_refused",
        "credentials_omitted_from_diagnostics",
        "absolute_jsonl_path_portability",
        "utf8_bom_and_strict_json",
        "malformed_unreadable_or_oversized_input_refused",
        "offline_validator_with_process_and_network_audit_guard",
        "source_and_input_files_unchanged",
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
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_config_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('GAMECONFIG_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
