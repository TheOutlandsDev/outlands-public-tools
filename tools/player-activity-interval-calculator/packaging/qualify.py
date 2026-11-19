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
PACKAGE = 'player-activity-interval-calculator'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_update_player_metrics.OriginalPlayerIntervalTests.test_eight_online_players_credit_eight_player_hours_per_hour',
    'test_update_player_metrics.OriginalPlayerIntervalTests.test_offline_population_never_accrues_player_hours',
}
FOCUSED_TESTS = {
    'test_calculator.ActivityIntervalTests.test_splits_at_fixed_offset_midnight',
    'test_calculator.ActivityIntervalTests.test_keeps_player_and_connection_hours_separate',
    'test_calculator.ActivityIntervalTests.test_availability_only_preserves_time_without_activity',
    'test_calculator.ActivityIntervalTests.test_rejects_malformed_and_overlapping_intervals',
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
    offset = "-04:00"

    def interval(**overrides):
        return {
            "server_id": "fictional-one", "state": "online", "metric_kind": "players",
            "population": 8, "start": "2040-07-28T04:00:00Z", "end": "2040-07-28T05:00:00Z",
            **overrides,
        }

    def saved(*intervals):
        return json.dumps({"intervals": intervals}, ensure_ascii=False).encode("utf-8")

    def totals(observed, online, players, connections):
        return {
            "observed_seconds": observed, "online_seconds": online,
            "player_hours": players, "connection_hours": connections,
        }

    def daily(day, server_id, observed, online, players, connections):
        return {"day": day, "server_id": server_id, **totals(observed, online, players, connections)}

    baseline = saved(interval())
    filenames = {
        "online.json": baseline,
        "offline.json": saved(interval(state="offline")),
        "rollover.json": saved(interval(start="2040-07-28T03:30:00Z", end="2040-07-28T04:30:00Z")),
        "mixed-units.json": saved(
            interval(server_id="fictional-two", metric_kind="connections", population=3),
            interval(),
        ),
        "availability-only.json": saved(interval(metric_kind="availability_only", population=None)),
        "naive-time.json": saved(interval(start="2040-07-28T04:00:00")),
        "fractional-time.json": saved(interval(start="2040-07-28T04:00:00.5Z")),
        "malformed-time.json": saved(interval(start="fictional-invalid-time")),
        "nonpositive-span.json": saved(interval(end="2040-07-28T04:00:00Z")),
        "too-long.json": saved(interval(end="2041-08-01T05:00:00Z")),
        "too-many-intervals.json": saved(*(
            interval(server_id=f"fictional-{index}") for index in range(10_001)
        )),
        "too-many-segments.json": saved(*(
            interval(server_id=f"fictional-{index}", end="2041-07-27T05:00:00Z")
            for index in range(28)
        )),
        "overlap.json": saved(
            interval(), interval(start="2040-07-28T04:59:00Z", end="2040-07-28T05:10:00Z")
        ),
        "negative-population.json": saved(interval(population=-1)),
        "boolean-population.json": saved(interval(population=True)),
        "wrong-state.json": saved(interval(state="fictional-invalid-state")),
        "wrong-metric.json": saved(interval(metric_kind="fictional-invalid-metric")),
        "invalid-row.json": saved("fictional-invalid-row"),
        "not-array.json": b'{"intervals": {}}',
        "bom.json": bytes.fromhex("efbbbf") + baseline,
        "duplicate.json": baseline.replace(b'"population": 8', b'"population": 8, "population": 8'),
        "nonfinite.json": baseline[:-1] + b', "uncounted_value": NaN}',
        "float-overflow.json": baseline[:-1] + b', "uncounted_value": 1e309}',
        "invalid-json.json": b'{"intervals":',
        "invalid-utf8.json": bytes.fromhex("fffe"),
        "not-object.json": b"[]",
        "empty.json": b"",
        "size-limit.json": baseline.ljust(limit, b" "),
        "oversized.json": baseline.ljust(limit + 1, b" "),
    }

    example = source / "examples/intervals.json"
    for name, raw in filenames.items():
        (workspace / name).write_bytes(raw)

    inputs = [example, *(workspace / name for name in filenames)]
    initial = {path: digest(path) for path in inputs}
    before = set(workspace.iterdir())
    env = {"PYTHONPATH": str(source)}
    base = [sys.executable, "-B", "-S", "-W", "error"]
    cli = [*base, "-m", "player_activity_intervals"]

    def invoke(name, *, expected=0, display_offset=offset):
        return run([*cli, "--input", workspace / name, f"--display-offset={display_offset}"],
                   expected=expected, extra_env=env)

    def valid(process, rows, summary):
        assert not process.stderr
        report = json.loads(process.stdout)
        assert report == {"daily": rows, "totals": summary}
        for row in [report["totals"], *report["daily"]]:
            assert type(row["observed_seconds"]) is int
            assert type(row["online_seconds"]) is int

    def refused(process, omitted=()):
        assert process.stderr and not process.stdout and "Traceback" not in process.stderr
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
        raise AssertionError('Activity calculator attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Activity calculator attempted a write')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp', 'sqlite3.connect'}:
        raise AssertionError('Activity calculator attempted mutation or database access')


sys.addaudithook(verify_offline)
import player_activity_intervals
assert Path(player_activity_intervals.__file__).resolve().parent == source / 'player_activity_intervals'
runpy.run_module('player_activity_intervals', run_name='__main__', alter_sys=True)
"""
    packaged = run([*base, "-c", audit, source, "--input", example,
                    f"--display-offset={offset}"], extra_env=env)
    valid(packaged, [
        daily("2040-07-27", "fictional-arena", 1800, 1800, 4.0, 0.0),
        daily("2040-07-28", "fictional-arena", 3600, 1800, 4.0, 0.0),
        daily("2040-07-28", "fictional-lobby", 900, 900, 0.0, 0.0),
        daily("2040-07-28", "fictional-relay", 1200, 1200, 0.0, 1.0),
    ], totals(7500, 5700, 8.0, 1.0))

    for name in ("online.json", "bom.json", "size-limit.json"):
        valid(invoke(name), [daily("2040-07-28", "fictional-one", 3600, 3600, 8.0, 0.0)],
              totals(3600, 3600, 8.0, 0.0))
    valid(invoke("offline.json"), [daily("2040-07-28", "fictional-one", 3600, 0, 0.0, 0.0)],
          totals(3600, 0, 0.0, 0.0))
    valid(invoke("rollover.json"), [
        daily("2040-07-27", "fictional-one", 1800, 1800, 4.0, 0.0),
        daily("2040-07-28", "fictional-one", 1800, 1800, 4.0, 0.0),
    ], totals(3600, 3600, 8.0, 0.0))
    valid(invoke("rollover.json", display_offset="Z"),
          [daily("2040-07-28", "fictional-one", 3600, 3600, 8.0, 0.0)],
          totals(3600, 3600, 8.0, 0.0))
    valid(invoke("mixed-units.json"), [
        daily("2040-07-28", "fictional-one", 3600, 3600, 8.0, 0.0),
        daily("2040-07-28", "fictional-two", 3600, 3600, 0.0, 3.0),
    ], totals(7200, 7200, 8.0, 3.0))
    valid(invoke("availability-only.json"), [daily("2040-07-28", "fictional-one", 3600, 3600, 0.0, 0.0)],
          totals(3600, 3600, 0.0, 0.0))

    for args in (["--input", example], [f"--display-offset={offset}"]):
        refused(run([*cli, *args], expected=2, extra_env=env))

    for bad_offset in ("fictional-invalid-offset", "+24:00", "-01:60", "-0400"):
        refused(invoke("online.json", expected=2, display_offset=bad_offset),
                omitted=("fictional-invalid-offset",))
    for name in ("naive-time.json", "fractional-time.json", "malformed-time.json", "nonpositive-span.json",
                 "too-long.json", "too-many-intervals.json", "too-many-segments.json", "overlap.json",
                 "negative-population.json", "boolean-population.json",
                 "wrong-state.json", "wrong-metric.json", "invalid-row.json", "not-array.json",
                 "duplicate.json", "nonfinite.json", "float-overflow.json", "invalid-json.json",
                 "invalid-utf8.json", "not-object.json", "empty.json", "oversized.json", "missing.json", "."):
        refused(invoke(name, expected=2), omitted=("fictional-invalid",))

    assert {path: digest(path) for path in initial} == initial
    assert set(workspace.iterdir()) == before
    return [
        "packaged_fictional_intervals",
        "online_population_activity_and_observed_seconds",
        "offline_population_never_accrues_activity",
        "fixed_offset_midnight_rollover",
        "separate_player_and_connection_hours",
        "availability_only_does_not_accrue_activity",
        "malformed_timestamps_and_offsets_refused",
        "malformed_and_overlapping_intervals_refused",
        "bounded_input_and_interval_span",
        "utf8_bom_and_strict_json",
        "offline_calculator_with_process_and_network_audit_guard",
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
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('ACTIVITYINTERVAL_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
