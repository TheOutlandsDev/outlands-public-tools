"""Validate the released source ZIP on a verified interpreter and a fresh test environment."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import sqlite3
import stat
import subprocess
import sys
import zipfile
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'sqlite-integrity-backup'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_sqlite_tools.SQLiteToolsTests.test_check_and_backup',
    'test_sqlite_tools.SQLiteToolsTests.test_backup_refuses_overwrite',
}
FOCUSED_TESTS = {
    'test_sqlite_safety.SQLiteSafetyTests.test_quick_and_full_integrity_and_foreign_keys',
    'test_sqlite_safety.SQLiteSafetyTests.test_wal_backup_includes_committed_rows_without_changing_source',
    'test_sqlite_safety.SQLiteSafetyTests.test_late_destination_is_not_overwritten',
    'test_sqlite_safety.SQLiteSafetyTests.test_same_file_and_hard_link_alias_are_refused',
    'test_sqlite_safety.SQLiteSafetyTests.test_explicit_force_replaces_a_regular_destination',
    'test_sqlite_safety.SQLiteSafetyTests.test_invalid_backup_cleans_staging_and_preserves_source',
    'test_sqlite_safety.SQLiteSafetyTests.test_destination_source_sidecar_is_refused',
    'test_sqlite_safety.SQLiteSafetyTests.test_active_destination_sidecars_are_refused',
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
    cli = [*python, "-m", "opskit", "sqlite"]
    env = {"PYTHONPATH": str(source)}
    marker = "fictional-private-diagnostic-marker"
    fixture = workspace / "sample space # %.sqlite"
    output = workspace / "sample-backup.sqlite"
    generator = source / "examples/create_sample.py"

    def valid(result):
        assert not result.stderr
        return json.loads(result.stdout)

    def invoke(*args, expected=0):
        return valid(run([*cli, *args], expected=expected, extra_env=env))

    def refused(*args):
        result = run([*cli, *args], expected=2, extra_env=env)
        assert not result.stdout and result.stderr
        assert all(value not in result.stderr for value in ("Traceback", marker, str(workspace), str(source)))

    def read_rows(path):
        with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True)) as connection:
            return connection.execute("SELECT id, value FROM sample ORDER BY id").fetchall()

    def verify_copy(report, path, rows):
        assert report["validated"] is True
        assert report["bytes"] == path.stat().st_size
        assert report["sha256"] == digest(path)
        assert read_rows(path) == rows
        assert not any(path.with_name(path.name + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))

    run([*python, generator, fixture])
    before = digest(fixture)
    assert read_rows(fixture) == [(1, "fictional sample")]
    checking_files = set(workspace.iterdir())
    for switch, pragma in (([], "quick_check"), (["--full"], "integrity_check")):
        report = invoke("check", fixture, *switch)
        assert report["check"] == pragma and report["ok"] is True and report["read_only"] is True
        assert report["integrity_messages"] == ["ok"] and report["foreign_key_violations"] == []
        assert report["page_count"] > 0 and report["page_size"] > 0
        assert report["estimated_bytes"] == report["page_count"] * report["page_size"]
        assert report["file_bytes"] == fixture.stat().st_size
    assert digest(fixture) == before and set(workspace.iterdir()) == checking_files

    report = invoke("backup", fixture, output)
    assert report["force_requested"] is False and report["replaced_existing"] is False
    verify_copy(report, output, [(1, "fictional sample")])

    foreign = workspace / "foreign-key.sqlite"
    with closing(sqlite3.connect(foreign)) as connection:
        connection.executescript(
            "PRAGMA foreign_keys=OFF; "
            "CREATE TABLE parent(id INTEGER PRIMARY KEY); "
            "CREATE TABLE child(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id)); "
            "INSERT INTO child VALUES (1, 99);"
        )
    foreign_hash = digest(foreign)
    broken = invoke("check", foreign, "--full", expected=1)
    assert broken["ok"] is False and broken["integrity_messages"] == ["ok"]
    assert broken["foreign_key_violations"] == [
        {"table": "child", "rowid": 1, "parent": "parent", "foreign_key_index": 0}
    ]

    wal_db = workspace / "source-wal.sqlite"
    wal_log = wal_db.with_name(wal_db.name + "-wal")
    wal_output = workspace / "backup-wal.sqlite"
    with closing(sqlite3.connect(wal_db)) as writer:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.executescript("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT NOT NULL); "
                             "INSERT INTO sample VALUES (1, 'fictional checkpoint');")
        assert writer.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone() == (0, 0, 0)
        writer.execute("INSERT INTO sample VALUES (2, 'fictional WAL row')")
        writer.commit()
        assert wal_log.stat().st_size > 32
        assert read_rows(wal_db) == [(1, "fictional checkpoint")]
        wal_sources = {path: digest(path) for path in (wal_db, wal_log)}
        before_wal_check = set(workspace.iterdir())
        report = invoke("check", wal_db)
        assert report["journal_mode"] == "wal" and report["ok"] is True and report["read_only"] is True
        assert set(workspace.iterdir()) == before_wal_check
        assert {path: digest(path) for path in wal_sources} == wal_sources
        report = invoke("backup", wal_db, wal_output)
        verify_copy(report, wal_output, [(1, "fictional checkpoint"), (2, "fictional WAL row")])
        assert {path: digest(path) for path in wal_sources} == wal_sources
        assert set(workspace.iterdir()) == before_wal_check | {wal_output}

    preserved = workspace / "destination.sqlite"
    sentinel = b"fictional pre-existing destination bytes"
    preserved.write_bytes(sentinel)
    alias = workspace / "source-hardlink.sqlite"
    os.link(fixture, alias)
    refused("backup", fixture, preserved)
    refused("backup", fixture, fixture)
    refused("backup", fixture, alias, "--force")
    refused("backup", fixture, fixture.with_name(fixture.name + "-wal"), "--force")
    assert preserved.read_bytes() == sentinel and digest(alias) == before
    assert not fixture.with_name(fixture.name + "-wal").exists()

    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = preserved.with_name(preserved.name + suffix)
        sidecar.write_bytes(sentinel)
        refused("backup", fixture, preserved, "--force")
        assert preserved.read_bytes() == sentinel and sidecar.read_bytes() == sentinel
        sidecar.unlink()

    report = invoke("backup", fixture, preserved, "--force")
    assert report["force_requested"] is True and report["replaced_existing"] is True
    verify_copy(report, preserved, [(1, "fictional sample")])

    corrupted = workspace / f"{marker}.sqlite"
    corrupted.write_bytes(b"fictional invalid SQLite input")
    saved_invalid = digest(corrupted)
    failure_target = workspace / "invalid-backup.sqlite"
    before_invalid = set(workspace.iterdir())
    refused("check", corrupted)
    refused("check", workspace / f"{marker}-missing.sqlite")
    refused("check", workspace)
    refused("backup", corrupted, failure_target)
    refused("backup", foreign, failure_target)
    refused(f"--{marker}")
    assert set(workspace.iterdir()) == before_invalid
    assert digest(corrupted) == saved_invalid and digest(foreign) == foreign_hash

    audit = """
import os
from pathlib import Path
import runpy
import sys
from urllib.parse import urlsplit
from urllib.request import url2pathname

source, (template, sandbox), command = Path(sys.argv[1]), map(Path, sys.argv[2:4]), sys.argv[4]
sys.path.insert(0, str(source))
sys.argv = sys.argv[4:]


def require_output_path(path, descriptor=None):
    candidate = Path(os.fsdecode(path))
    if not candidate.is_absolute() and descriptor is not None and descriptor >= 0 and sys.platform.startswith('linux'):
        candidate = Path(os.readlink(f'/proc/self/fd/{descriptor}')) / candidate
    assert candidate.is_absolute() and candidate.resolve().is_relative_to(sandbox)
    assert command == 'backup'


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn', 'os.startfile',
                 'os.kill', 'ctypes.dlopen', 'sqlite3.enable_load_extension', 'sqlite3.load_extension'}:
        raise AssertionError('Unexpected process, installer, or extension access')
    if event.startswith('socket.'):
        raise AssertionError('SQLite tool attempted network access')
    if event == 'sqlite3.connect':
        location = os.fsdecode(args[0])
        if location == template.as_uri() + '?mode=ro':
            return
        if location.startswith('file:'):
            uri = urlsplit(location)
            assert not uri.netloc
            location = url2pathname(uri.path)
        require_output_path(location)
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        require_output_path(args[0])
    if event in {'os.rename', 'os.link'}:
        require_output_path(args[0], args[2])
        require_output_path(args[1], args[3])
    if event in {'os.remove', 'os.rmdir'}:
        require_output_path(args[0], args[1])
    if event == 'os.mkdir':
        require_output_path(args[0], args[2])
    if event in {'tempfile.mkdtemp', 'tempfile.mkstemp', 'shutil.rmtree'}:
        require_output_path(args[0])
    if event in {'os.symlink', 'os.truncate', 'os.chmod', 'os.utime'}:
        raise AssertionError('Unexpected filesystem mutation')


sys.addaudithook(verify_offline)
import opskit
assert Path(opskit.__file__).resolve().parent == source / 'opskit'
runpy.run_module('opskit', run_name='__main__', alter_sys=True)
"""
    sandbox = workspace / "audit-output"
    sandbox.mkdir()
    audited_output = sandbox / "backup.sqlite"
    # The isolated child takes the copied tree explicitly and cannot use installed modules.
    audited = [sys.executable, "-I", "-B", "-W", "error", "-c", audit, source, fixture, sandbox]
    checked = valid(run([*audited, "check", "sqlite", "check", fixture, "--full"]))
    assert checked["ok"] is True and checked["read_only"] is True and not list(sandbox.iterdir())
    report = valid(run([*audited, "backup", "sqlite", "backup", fixture, audited_output]))
    verify_copy(report, audited_output, [(1, "fictional sample")])
    assert list(sandbox.iterdir()) == [audited_output]
    assert digest(fixture) == digest(alias) == before
    assert digest(foreign) == foreign_hash and digest(corrupted) == saved_invalid
    assert not any(fixture.with_name(fixture.name + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))

    return [
        "fictional_example_generator",
        "sqlite_quick_and_full_read_only",
        "foreign_key_violation_exit_status",
        "verified_backup_rows_and_sha256",
        "committed_wal_rows_in_backup",
        "wal_source_database_and_log_unchanged",
        "existing_destination_and_source_alias_refused",
        "force_regular_destination",
        "active_destination_sidecars_refused",
        "failed_backup_isolation_and_cleanup",
        "opaque_cli_operational_errors",
        "offline_scoped_mutation_no_install_audit_guard",
        "extracted_source_and_inputs_unchanged",
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
    print('SQLITE_BACKUP_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
