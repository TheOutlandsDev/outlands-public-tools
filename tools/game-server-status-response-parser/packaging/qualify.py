"""Validate the released source ZIP on a verified interpreter and a fresh test environment."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'game-server-status-response-parser'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_player_telemetry.OriginalPlayerTelemetryTests.test_parse_a2s_info_player_counts',
    'test_player_telemetry.OriginalPlayerTelemetryTests.test_parse_quake3_status_player_lines',
    'test_player_telemetry.OriginalPlayerTelemetryTests.test_player_parser_rejects_invalid_packets',
}
FOCUSED_TESTS = {
    'test_parser.GameServerStatusParserTests.test_a2s_rejects_truncated_fields',
    'test_parser.GameServerStatusParserTests.test_quake3_handles_missing_and_invalid_capacity',
    'test_parser.GameServerStatusParserTests.test_parser_output_contains_only_allowlisted_metadata',
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
    limit = 64 * 1024
    a2s_fields = (
        bytes([17]) + b"Local Test Server\x00fictional_harbor\x00test_mod\x00Test Game\x00"
    )
    a2s = b"\xff\xff\xff\xffI" + a2s_fields + struct.pack("<HBBB", 4321, 2, 16, 1)

    def quake3(capacity: bytes | None):
        info = b"\\sv_hostname\\Local Test Arena\\mapname\\fictional_atrium"
        if capacity is not None:
            info += b"\\sv_maxclients\\" + capacity
        return (
            b"\xff\xff\xff\xffstatusResponse\r\n" + info
            + b'\r\n10 40 "Fictional Player A"\r\n'
            + b'12 50 "Fictional Player B"\r\n'
        )

    q3 = quake3(b"24")
    max_size_q3 = q3.ljust(limit, b" ")
    fixtures = {
        "a2s.bin": a2s,
        "quake3.bin": q3,
        "q3-missing-capacity.bin": quake3(None),
        "q3-invalid-capacity.bin": quake3(b"invalid"),
        "q3-uppercase-capacity.bin": q3.replace(b"sv_maxclients", b"sv_maxClients"),
        "a2s-short-header.bin": a2s[:4],
        "a2s-short-string.bin": b"\xff\xff\xff\xffI" + bytes([17]) + b"No terminator",
        "a2s-short-fields.bin": a2s[:-1],
        "wrong-response.bin": b"not a status response",
        "empty.bin": b"",
        "size-limit.bin": max_size_q3,
        "oversized.bin": max_size_q3 + b" ",
    }

    a2s_hex = source / "examples/a2s-info.hex"
    q3_example = source / "examples/quake3-status.txt"
    fixtures["a2s-example.bin"] = bytes.fromhex(a2s_hex.read_text(encoding="ascii"))
    for name, raw in fixtures.items():
        (workspace / name).write_bytes(raw)

    inputs = [a2s_hex, q3_example, *(workspace / name for name in fixtures)]
    initial = {path: digest(path) for path in inputs}
    before = set(workspace.iterdir())
    env = {"PYTHONPATH": str(source)}
    base = [sys.executable, "-B", "-S", "-W", "error"]
    cli = [*base, "-m", "game_server_status"]

    def invoke(name, format_name, *, expected=0):
        return run([*cli, "--format", format_name, "--input", workspace / name],
                   expected=expected, extra_env=env)

    def output(process):
        assert not process.stderr
        result = json.loads(process.stdout)
        assert isinstance(result, dict)
        return result

    def refused(process):
        assert process.stderr and not process.stdout and "Traceback" not in process.stderr

    audit = """
import os
from pathlib import Path
import runpy
import sys


source = Path(sys.argv.pop(1))


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn'} or event.startswith('socket.'):
        raise AssertionError('Response parser attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Response parser attempted a write')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp'}:
        raise AssertionError('Response parser attempted a filesystem mutation')


sys.addaudithook(verify_offline)
import game_server_status
assert Path(game_server_status.__file__).resolve().parent == source / 'game_server_status'
runpy.run_module('game_server_status', run_name='__main__', alter_sys=True)
"""

    expected_a2s = {
        "protocol": 17, "server_name": "Local Test Server", "map": "fictional_harbor",
        "folder": "test_mod", "game": "Test Game", "app_id": 4321,
        "players": 2, "max_players": 16, "bots": 1,
    }
    expected_q3 = {
        "players": 2, "max_players": 24, "bots": None,
        "server_name": "Local Test Arena", "map": "fictional_atrium",
    }
    for filename, protocol, expected in (
        ("a2s.bin", "a2s-info", expected_a2s),
        ("quake3.bin", "quake3-status", expected_q3),
    ):
        process = run([*base, "-c", audit, source, "--format", protocol, "--input", workspace / filename],
                      extra_env=env)
        assert output(process) == expected
        assert "Fictional Player" not in process.stdout

    assert output(invoke("a2s-example.bin", "a2s-info")) == {
        "protocol": 17, "server_name": "Fictional A2S Server", "map": "fictional_station",
        "folder": "fictional_mod", "game": "Fictional Arena", "app_id": 1234,
        "players": 4, "max_players": 20, "bots": 2,
    }
    packaged_q3 = run([*cli, "--format", "quake3-status", "--input", q3_example], extra_env=env)
    assert output(packaged_q3) == {
        "players": 2, "max_players": 18, "bots": None,
        "server_name": "Fictional Quake Server", "map": "fictional_courtyard",
    }
    assert "Fictional Visitor" not in packaged_q3.stdout

    for name in ("q3-missing-capacity.bin", "q3-invalid-capacity.bin"):
        assert output(invoke(name, "quake3-status")) == {**expected_q3, "max_players": None}
    assert output(invoke("q3-uppercase-capacity.bin", "quake3-status")) == expected_q3

    for name in ("a2s-short-header.bin", "a2s-short-string.bin", "a2s-short-fields.bin"):
        refused(invoke(name, "a2s-info", expected=2))
    for protocol in ("a2s-info", "quake3-status"):
        for name in ("wrong-response.bin", "empty.bin", "missing.bin", "."):
            refused(invoke(name, protocol, expected=2))
    assert output(invoke("size-limit.bin", "quake3-status")) == expected_q3
    refused(invoke("oversized.bin", "quake3-status", expected=2))
    refused(invoke("quake3.bin", "a2s-info", expected=2))
    refused(invoke("a2s.bin", "quake3-status", expected=2))
    refused(invoke("a2s.bin", "unknown", expected=2))
    refused(run([*cli], expected=2, extra_env=env))
    refused(run([*cli, "--format", "a2s-info"], expected=2, extra_env=env))
    refused(run([*cli, "--input", q3_example], expected=2, extra_env=env))
    refused(run([*cli, "--format", "quake3-status", "--input", q3_example, "--unknown"],
                expected=2, extra_env=env))

    assert {path: digest(path) for path in initial} == initial
    assert set(workspace.iterdir()) == before
    return [
        "packaged_fictional_a2s_response",
        "packaged_fictional_quake3_response",
        "a2s_metadata_and_counts",
        "quake3_metadata_and_aggregate_counts",
        "quake3_omits_player_names",
        "a2s_truncated_header_string_and_fields_refused",
        "quake3_missing_and_invalid_capacity_as_null",
        "malformed_or_unreadable_input_refused",
        "response_size_boundary",
        "format_dispatch_and_cli_arguments_refused",
        "offline_parser_with_process_and_network_audit_guard",
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
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_status_queries_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('GAMESTATUS_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
