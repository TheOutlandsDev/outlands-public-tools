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
PACKAGE = 'player-activity-history-reporter'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_update_player_metrics.OriginalHistoryTests.test_two_layer_baseline_and_archived_totals_balance',
    'test_update_player_metrics.OriginalHistoryTests.test_availability_only_history_never_becomes_human_playtime',
}
FOCUSED_TESTS = {
    'test_history.HistoryReportTests.test_distinct_metric_units_and_no_mixed_total',
    'test_history.HistoryReportTests.test_report_windows_and_cumulative_across_missing_days',
    'test_history.HistoryReportTests.test_duplicate_ids_across_and_within_active_and_archive_refused',
    'test_history.HistoryReportTests.test_duplicate_daily_rows_and_state_instants_refused',
    'test_history.HistoryReportTests.test_transitions_use_fixed_offset_and_leading_state',
    'test_history.HistoryReportTests.test_transitions_are_latest_first_and_capped',
    'test_history.HistoryReportTests.test_malformed_or_future_rows_refused',
    'test_history.HistoryReportTests.test_report_is_repeatable_without_mutating_input',
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
    report_date = "2040-07-28"
    sample = source / "examples/history.json"
    marker = "fictional-private-diagnostic-marker"
    empty = b'{"active": [], "archived": []}'

    def active(server_id, *, kind="players", baseline=0, daily=(), states=()):
        return {
            "server_id": server_id, "metric_kind": kind, "baseline_hours": baseline,
            "daily": [{"date": date, "activity_seconds": seconds} for date, seconds in daily],
            "states": [{"observed_at": observed_at, "state": state} for observed_at, state in states],
        }

    def archive(server_id):
        return {
            "server_id": server_id, "metric_kind": "players",
            "baseline_hours": 3, "observed_activity_seconds": 3600,
        }

    def payload(*servers, archives=(), **fields):
        return json.dumps({"active": list(servers), "archived": list(archives), **fields}).encode("utf-8")

    boundary = active(
        "fictional-boundaries",
        baseline=2,
        daily=[
            ("2040-06-28", 3600), ("2040-06-29", 7200), ("2040-07-21", 14400),
            ("2040-07-22", 28800), ("2040-07-23", 57600), ("2040-07-28", 115200),
        ],
    )
    boundary["metadata"] = marker
    boundary["daily"][0]["metadata"] = marker
    availability = active(
        "fictional-beacon",
        kind="availability_only",
        baseline=17,
        daily=[("2040-07-28", 36000)],
        states=[
            ("2040-06-29T03:59:59Z", "online"),
            ("2040-06-29T04:00:00Z", "offline"),
            ("2040-07-29T03:59:59Z", "degraded"),
        ],
    )
    availability["states"][0]["metadata"] = marker
    archived_sample = archive("fictional-archive")
    archived_sample["metadata"] = marker
    cases = {
        "empty.json": empty,
        "boundaries.json": payload(boundary, availability, archives=[archived_sample], metadata=marker),
        f"{marker}.json": b'{"active": ["' + marker.encode("ascii"),
        "invalid-utf8.json": bytes.fromhex("fffe"),
        "duplicate-json-key.json": b'{"active": [], "archived": [], "active": []}',
        "nonfinite.json": b'{"active": [], "archived": [], "extra": NaN}',
        "wrong-document.json": b'[]',
        "duplicate-active.json": payload(boundary, boundary),
        "duplicate-archive.json": payload(archives=[archive("same-archive"), archive("same-archive")]),
        "duplicate-cross-group.json": payload(boundary, archives=[archive("fictional-boundaries")]),
        "duplicate-days.json": payload(active("duplicate-day", daily=[("2040-07-28", 1), ("2040-07-28", 2)])),
        "duplicate-states.json": payload(active("duplicate-state", states=[
            ("2040-07-28T00:00:00Z", "online"), ("2040-07-27T20:00:00-04:00", "offline"),
        ])),
        "future-day.json": payload(active("future-day", daily=[("2040-07-29", 1)])),
        "future-state.json": payload(active("future-state", states=[("2040-07-29T04:00:00Z", "online")])),
        "negative-baseline.json": payload(active("bad-baseline", baseline=-1)),
        "too-large-numeric.json": payload(active("large-baseline", baseline=10**12 + 1)),
        "max-bytes.json": empty.ljust(limit, b" "),
        "too-many-bytes.json": empty.ljust(limit + 1, b" "),
        "too-many-servers.json": payload(*(active(f"fictional-{index}") for index in range(1001))),
    }
    for name, raw in cases.items():
        (workspace / name).write_bytes(raw)

    inputs = [sample, *(workspace / name for name in cases)]
    initial = {path: digest(path) for path in inputs}
    before = set(workspace.iterdir())
    env = {"PYTHONPATH": str(source)}
    python = [sys.executable, "-B", "-S", "-W", "error"]
    cli = [*python, "-m", "player_activity_history"]

    def arguments(path, *, as_of=report_date, offset="-04:00"):
        return ["--input", path, "--as-of", as_of, f"--display-offset={offset}"]

    def invoke(path, *, expected=0, **options):
        return run([*cli, *arguments(path, **options)], expected=expected, extra_env=env)

    def valid(result):
        assert not result.stderr
        report = json.loads(result.stdout)
        assert set(report) == {"as_of", "display_offset", "totals", "servers", "archived", "events"}
        assert report["as_of"] == report_date and report["display_offset"] == "-04:00"
        assert set(report["totals"]) == {"players", "connections"}
        assert marker not in result.stdout
        return report

    def refused(result):
        assert not result.stdout and result.stderr
        assert all(value not in result.stderr for value in ("Traceback", marker, str(workspace), str(source)))

    sample_report = valid(invoke(sample))
    players = sample_report["totals"]["players"]
    assert players == {
        "baseline_hours": 14, "observed_7d_hours": 0.03, "observed_30d_hours": 0.03,
        "observed_lifetime_hours": 1.03, "active_lifetime_hours": 10.03, "archived_lifetime_hours": 5,
        "lifetime_hours": 15.03, "seeded_7d_hours": 14.03, "seeded_30d_hours": 14.03,
    }
    connections = sample_report["totals"]["connections"]
    assert connections == {
        "baseline_hours": 20, "observed_7d_hours": 0.05, "observed_30d_hours": 0.05,
        "observed_lifetime_hours": 0.05, "active_lifetime_hours": 20.05, "archived_lifetime_hours": 0,
        "lifetime_hours": 20.05, "seeded_7d_hours": 20.05, "seeded_30d_hours": 20.05,
    }
    assert len(sample_report["archived"]) == 1 and sample_report["archived"][0]["lifetime_hours"] == 5
    assert sample_report["events"] == [{
        "server_id": "lantern-beacon", "observed_at": "2040-07-27T22:00:00-04:00",
        "from_state": "online", "to_state": "offline",
    }]

    report = valid(invoke(workspace / "boundaries.json"))
    by_id = {row["server_id"]: row for row in report["servers"]}
    history = by_id["fictional-boundaries"]
    assert history["totals"]["observed_7d_hours"] == 56
    assert history["totals"]["observed_30d_hours"] == 62
    assert history["totals"]["observed_lifetime_hours"] == 63
    assert history["totals"]["lifetime_hours"] == 65
    daily = history["daily_30d"]
    assert len(daily) == 30 and daily[0]["date"] == "2040-06-29"
    assert daily[1]["date"] == "2040-06-30" and daily[1]["activity_hours"] == 0
    assert daily[1]["cumulative_hours"] == 5 and daily[-1]["cumulative_hours"] == 65
    weekly = [row for row in history["weekly_lifetime"] if row["activity_hours"] > 0]
    assert [(row["date"], row["activity_hours"]) for row in weekly] == [
        ("2040-07-01", 3), ("2040-07-22", 12), ("2040-07-28", 48),
    ]
    assert history["weekly_lifetime"][-1]["cumulative_hours"] == 65
    assert report["totals"]["players"]["lifetime_hours"] == 69
    assert report["totals"]["players"]["seeded_7d_hours"] == 61
    assert report["totals"]["players"]["seeded_30d_hours"] == 67
    beacon = by_id["fictional-beacon"]
    assert beacon["activity_tracked"] is False and not beacon["weekly_lifetime"]
    assert not any(beacon["totals"].values())
    assert all(row["activity_hours"] == row["cumulative_hours"] == 0 for row in beacon["daily_30d"])
    assert report["events"] == [
        {"server_id": "fictional-beacon", "observed_at": "2040-07-28T23:59:59-04:00",
         "from_state": "offline", "to_state": "degraded"},
        {"server_id": "fictional-beacon", "observed_at": "2040-06-29T00:00:00-04:00",
         "from_state": "online", "to_state": "offline"},
    ]

    for name in ("empty.json", "max-bytes.json"):
        empty_report = valid(invoke(workspace / name))
        assert not any(empty_report[key] for key in ("servers", "archived", "events"))
        assert all(not any(summary.values()) for summary in empty_report["totals"].values())

    for name in (*cases, "missing.json", "."):
        if name not in {"empty.json", "max-bytes.json", "boundaries.json"}:
            refused(invoke(workspace / name, expected=2))
    refused(invoke(sample, as_of="2040-02-30", expected=2))
    refused(invoke(sample, offset=marker, expected=2))
    refused(run([*cli, "--input", sample], expected=2, extra_env=env))

    audit = """
import os
from pathlib import Path
import runpy
import sys


source = Path(sys.argv.pop(1))


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn'} or event.startswith('socket.'):
        raise AssertionError('Activity history reporter attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Activity history reporter attempted a write')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp', 'sqlite3.connect'}:
        raise AssertionError('Activity history reporter attempted mutation or database access')


sys.addaudithook(verify_offline)
import player_activity_history
assert Path(player_activity_history.__file__).resolve().parent == source / 'player_activity_history'
runpy.run_module('player_activity_history', run_name='__main__', alter_sys=True)
"""
    for path, expected in ((sample, sample_report), (workspace / "boundaries.json", report)):
        result = run([*python, "-c", audit, source, *arguments(path)], extra_env=env)
        assert valid(result) == expected

    assert {path: digest(path) for path in initial} == initial
    assert set(workspace.iterdir()) == before
    return [
        "packaged_fictional_activity_history",
        "baseline_observed_and_archived_totals_balance",
        "separate_player_and_connection_rollups",
        "seven_and_thirty_day_as_of_boundaries",
        "monday_week_rollover_and_lifetime_cumulative",
        "availability_only_has_transitions_and_zero_activity",
        "fixed_offset_event_window",
        "duplicate_and_future_records_refused",
        "strict_json_and_bounded_input",
        "metadata_omitted_from_report",
        "errors_omit_payload_and_paths",
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
    print('ACTIVITY_HISTORY_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
