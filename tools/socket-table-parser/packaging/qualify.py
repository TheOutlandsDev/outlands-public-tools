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
PACKAGE = 'socket-table-parser'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_ports.PortParserTests.test_windows_netstat_listeners_only',
    'test_ports.PortParserTests.test_windows_netstat_can_include_connections',
    'test_ports.PortParserTests.test_proc_net_tcp_listener',
}
FOCUSED_TESTS = {
    'test_socket_table_safety.SocketTableTests.test_windows_ipv6_and_udp_rows',
    'test_socket_table_safety.SocketTableTests.test_linux_ipv6_and_udp_rows',
    'test_socket_table_safety.SocketTableTests.test_malformed_windows_rows_do_not_stop_parsing',
    'test_socket_table_safety.SocketTableTests.test_malformed_linux_rows_do_not_stop_parsing',
    'test_socket_table_safety.SocketTableTests.test_remote_fields_require_opt_in',
    'test_socket_table_safety.SocketTableTests.test_platform_pid_fields',
    'test_socket_table_safety.SocketTableTests.test_cli_reads_supplied_files',
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
assert not loader.errors, loader.errors
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
    python = [sys.executable, "-B", "-S", "-W", "error"]
    cli = [*python, "-m", "opskit", "ports"]
    env = {"PYTHONPATH": str(source)}
    samples = source / "examples"
    fixture = workspace / "fictional tables"
    fixture.mkdir()
    marker = "fictional-invalid-input-marker"
    fields = {"protocol", "local_address", "local_port", "remote_address", "remote_port", "state", "pid"}

    def fixture_text(name, text):
        path = fixture / name
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def parsed(result):
        assert not result.stderr
        payload = json.loads(result.stdout)
        assert set(payload) == {"rows"}
        assert isinstance(payload["rows"], list)
        assert all(set(row) == fields for row in payload["rows"])
        return payload["rows"]

    def invoke(table_format, path, *options):
        return parsed(run([*cli, "--format", table_format, "--input", path, *options], extra_env=env))

    def row_at(rows, port):
        row, = [row for row in rows if row["local_port"] == port]
        return row

    def privacy(rows):
        return all(row["remote_address"] is None and row["remote_port"] is None for row in rows)

    def file_hashes(root):
        return {path.relative_to(root).as_posix(): digest(path)
                for path in root.rglob("*") if path.is_file()}

    header = "  sl  local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n"

    def proc_row(index, local, remote, state):
        return f"{index:4}: {local} {remote} {state} 00000000:00000000 00:00000000 00000000 1000 0 12345 1\n"

    ipv4 = fixture_text("linux-tcp.txt", header + proc_row(0, "0100007F:1F90", "00000000:0000", "0A"))
    udp6 = fixture_text(
        "linux-udp6.txt",
        header + proc_row(0, "B80D012000000000000000000A000000:14E9", "00000000000000000000000000000000:0000", "07"),
    )
    malformed_windows = fixture_text(
        "malformed-windows.txt",
        "TCP 127.0.0.1:8080 0.0.0.0:0 LISTENING 1234\n"
        "TCP 127.0.0.1 0.0.0.0:0 LISTENING 1234\n"
        "TCP 127.0.0.1:65536 0.0.0.0:0 LISTENING 1234\n"
        "TCP 127.0.0.1:8082 0.0.0.0:0 LISTENING invalid\n"
        "TCP [2001:db8::b]:8083 [::]:0 LISTENING 4321\n",
    )
    malformed_linux = fixture_text(
        "malformed-linux.txt",
        header
        + proc_row(0, "0100007F:1F90", "00000000:0000", "0A")
        + proc_row(1, "missing_colon", "00000000:0000", "0A")
        + proc_row(2, "NOTHEX00:1F91", "00000000:0000", "0A")
        + proc_row(3, "0100007F:10000", "00000000:0000", "0A")
        + proc_row(4, "0100007F:1F93", "00000000:0000", "0A"),
    )
    empty = fixture_text("empty.txt", "")
    bad_encoding = fixture / f"{marker}.txt"
    bad_encoding.write_bytes(b"\xff\xfe\x00")
    oversized = fixture / "oversized.txt"
    oversized.write_bytes(b"x" * (4 * 1024 * 1024 + 1))
    utf16 = fixture / "windows-utf16.txt"
    utf16.write_bytes((samples / "windows-netstat.txt").read_text(encoding="utf-8").encode("utf-16"))
    before_inputs = file_hashes(fixture)
    before_samples = file_hashes(samples)

    windows = invoke("windows-netstat", samples / "windows-netstat.txt")
    assert [row["local_port"] for row in windows] == [8080, 8081, 5353]
    assert row_at(windows, 8080)["protocol"] == row_at(windows, 8081)["protocol"] == "tcp"
    assert ":" not in row_at(windows, 8080)["local_address"]
    assert ":" in row_at(windows, 8081)["local_address"]
    assert row_at(windows, 8081)["state"] == "LISTENING"
    assert invoke("windows-netstat", utf16) == windows
    udp = row_at(windows, 5353)
    assert udp["protocol"] == "udp" and udp["state"] == "BOUND"
    assert privacy(windows)
    windows_connected = invoke("windows-netstat", samples / "windows-netstat.txt", "--include-connections")
    assert len(windows_connected) == 4
    connected = row_at(windows_connected, 50000)
    assert (connected["state"], connected["remote_address"], connected["remote_port"]) == (
        "ESTABLISHED", "198.51.100.10", 443,
    )

    linux4 = invoke("linux-tcp", ipv4)
    linux6 = invoke("linux-tcp6", samples / "linux-tcp6.txt")
    assert len(linux4) == len(linux6) == 1
    assert (linux4[0]["local_address"], linux4[0]["local_port"], linux4[0]["state"]) == (
        "127.0.0.1", 8080, "LISTEN",
    )
    assert (linux6[0]["local_address"], linux6[0]["local_port"], linux6[0]["state"]) == (
        "2001:db8::a", 8080, "LISTEN",
    )
    assert privacy([*linux4, *linux6])
    linux_connected = invoke("linux-tcp6", samples / "linux-tcp6.txt", "--include-connections")
    assert len(linux_connected) == 2
    connected = row_at(linux_connected, 50000)
    assert (connected["state"], connected["remote_address"], connected["remote_port"]) == (
        "ESTABLISHED", "2001:db8::b", 443,
    )

    linux_udp4 = invoke("linux-udp", samples / "linux-udp.txt")
    linux_udp6 = invoke("linux-udp6", udp6)
    assert len(linux_udp4) == len(linux_udp6) == 1
    assert [(row["local_address"], row["local_port"], row["protocol"], row["state"])
            for row in [*linux_udp4, *linux_udp6]] == [
        ("192.0.2.5", 5353, "udp", "BOUND"),
        ("2001:db8::a", 5353, "udp", "BOUND"),
    ]
    assert privacy([*linux_udp4, *linux_udp6])
    assert all(type(row["pid"]) is int for row in windows_connected)
    assert all(row["pid"] is None for row in [*linux4, *linux_connected, *linux_udp4, *linux_udp6])
    assert [row["local_port"] for row in invoke("windows-netstat", malformed_windows)] == [8080, 8083]
    assert [row["local_port"] for row in invoke("linux-tcp", malformed_linux)] == [8080, 8083]
    assert invoke("windows-netstat", empty) == []
    assert invoke("linux-tcp", empty) == []

    for path in (bad_encoding, oversized, fixture, fixture / f"{marker}-missing.txt"):
        failed = run([*cli, "--format", "windows-netstat", "--input", path], expected=2, extra_env=env)
        assert not failed.stdout and failed.stderr.strip()
        assert all(item not in failed.stderr for item in (marker, str(fixture), "Traceback"))
    failed = run([*cli, "--format", marker, "--input", empty], expected=2, extra_env=env)
    assert not failed.stdout and failed.stderr.strip()
    assert marker not in failed.stderr and "Traceback" not in failed.stderr

    audit = """
import os
from pathlib import Path
import runpy
import sys

source = Path(sys.argv[1]).resolve()
input_path = Path(sys.argv[2]).resolve()
runtime = source / "opskit"
interpreter = Path(sys.base_prefix).resolve()
sys.path.insert(0, str(source))
sys.argv = ["opskit", "ports", "--format", "windows-netstat", "--input", str(input_path)]


def verify_offline(event, args):
    if event.startswith("socket.") or event in {
        "subprocess.Popen", "os.exec", "os.system", "os.spawn", "os.posix_spawn",
        "os.startfile", "os.startfile/2", "os.kill", "ctypes.dlopen",
    }:
        raise AssertionError("Parser attempted live collection or execution")
    if event == "open":
        path, _, flags = args
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise AssertionError("Parser opened a file for writing")
        if not isinstance(path, int):
            target = Path(os.fsdecode(path)).resolve()
            if target != input_path and not any(target.is_relative_to(root) for root in (runtime, interpreter)):
                raise AssertionError("Parser opened a file outside the selected input or runtime")
    if event in {
        "os.chmod", "os.link", "os.mkdir", "os.remove", "os.rename", "os.rmdir",
        "os.symlink", "os.truncate", "os.utime", "shutil.copyfile", "shutil.rmtree",
        "tempfile.mkdtemp", "tempfile.mkstemp",
    }:
        raise AssertionError("Parser attempted a filesystem mutation")


sys.addaudithook(verify_offline)
import opskit
assert Path(opskit.__file__).resolve().parent == runtime
runpy.run_module("opskit", run_name="__main__", alter_sys=True)
"""
    audited = [sys.executable, "-I", "-B", "-W", "error", "-c", audit, source, samples / "windows-netstat.txt"]
    assert parsed(run(audited)) == windows
    assert file_hashes(fixture) == before_inputs
    assert file_hashes(samples) == before_samples

    return [
        "windows_ipv4_ipv6_listeners",
        "windows_udp_bound_rows",
        "windows_connections_remote_opt_in",
        "linux_ipv4_ipv6_listeners",
        "linux_udp4_udp6_bound_rows",
        "linux_connections_remote_opt_in",
        "malformed_windows_rows_continue",
        "malformed_linux_rows_continue",
        "platform_pid_records",
        "invalid_input_opaque_diagnostics",
        "empty_table_is_valid",
        "offline_read_only_audit_guard",
        "extracted_source_and_inputs_unchanged",
    ]


def qualify(packages, workspace, report, receipt, reference):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    workspace = workspace.resolve()
    sdk = check_interpreter(receipt)
    build, source, names = unpack(packages, workspace, reference)
    before_source = {name: digest(source / name) for name in names}
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
    assert {name: digest(source / name) for name in names} == before_source
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
    print('SOCKET_TABLE_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
