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
PACKAGE = 'player-telemetry-snapshot-normalizer'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_update_player_metrics.OriginalNormalizationTests.test_availability_only_point_preserves_original_fallback',
    'test_update_player_metrics.OriginalNormalizationTests.test_portal_population_preserves_player_and_connection_units',
}
FOCUSED_TESTS = {
    'test_normalizer.NormalizationTests.test_collector_maps_both_population_fields',
    'test_normalizer.NormalizationTests.test_malformed_counts_are_null_and_negative_counts_clamp',
    'test_normalizer.NormalizationTests.test_unknown_ids_and_unrelated_metadata_are_omitted',
    'test_normalizer.NormalizationTests.test_mapping_rejects_malformed_rules',
    'test_normalizer.NormalizationTests.test_snapshot_rejects_invalid_shapes',
    'test_normalizer.NormalizationTests.test_limits_reject_excessive_rows_and_mappings',
    'test_normalizer.NormalizationTests.test_input_read_rejects_oversize_and_nonregular_paths',
    'test_normalizer.NormalizationTests.test_json_rejects_duplicate_keys_and_nonfinite_numbers',
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
    sample_mapping = source / "examples/mapping.json"
    portal = source / "examples/portal-snapshot.json"
    collector = source / "examples/collector-snapshot.json"
    mapping_bytes = sample_mapping.read_bytes()
    marker = "fictional-private-diagnostic-marker"
    empty = b'{"servers": []}'

    def payload(value):
        return json.dumps(value, ensure_ascii=False).encode("utf-8")

    def point(server_id, state, population, capacity, metric_kind):
        return {
            "server_id": server_id, "state": state, "population": population,
            "capacity": capacity, "metric_kind": metric_kind,
        }

    cases = {
        "empty.json": empty,
        "unmapped.json": payload({"servers": [{"id": "fictional-does-not-exist", "label": marker}]}),
        "invalid-json.json": b'{"servers": ["' + marker.encode("ascii"),
        "invalid-utf8.json": bytes.fromhex("fffe"),
        "duplicate.json": b'{"servers": [], "servers": []}',
        "nonfinite.json": b'{"servers": [], "other": NaN}',
        "float-overflow.json": b'{"servers": [], "other": 1e309}',
        "wrong-document.json": b'[]',
        "wrong-rows.json": b'{"servers": {}}',
        "wrong-row.json": payload({"servers": [marker]}),
        "max-bytes.json": empty.ljust(limit, b" "),
        "too-many-bytes.json": empty.ljust(limit + 1, b" "),
        "too-many-rows.json": payload({"servers": [{}] * 10_001}),
        "invalid-mapping.json": payload({
            "portal": {marker: {"server_id": "sample-target", "metric_kind": marker}},
            "collector": {},
        }),
        "invalid-collector-mapping.json": payload({
            "portal": {}, "collector": {marker: {"server_id": "sample-target", "metric_kind": "auto"}},
        }),
        "duplicate-mapping.json": b'{"portal": {}, "collector": {}, "portal": {}}',
        "nonfinite-mapping.json": b'{"portal": {}, "collector": {}, "other": Infinity}',
        "oversized-mapping.json": mapping_bytes.ljust(limit + 1, b" "),
        "too-many-mappings.json": payload({
            "portal": {f"source-{index}": {"server_id": f"target-{index}", "metric_kind": "players"}
                       for index in range(10_001)},
            "collector": {},
        }),
    }
    for name, raw in cases.items():
        (workspace / name).write_bytes(raw)

    inputs = [sample_mapping, portal, collector, *(workspace / name for name in cases)]
    initial = {path: digest(path) for path in inputs}
    before = set(workspace.iterdir())
    env = {"PYTHONPATH": str(source)}
    python = [sys.executable, "-B", "-S", "-W", "error"]
    cli = [*python, "-m", "player_telemetry_normalizer"]

    def arguments(path, mapping, kind):
        return ["--input", path, "--mapping", mapping, "--format", kind]

    def invoke(path, *, mapping=sample_mapping, kind="portal", expected=0):
        return run([*cli, *arguments(path, mapping, kind)], expected=expected, extra_env=env)

    def valid(result, expected):
        assert not result.stderr
        report = json.loads(result.stdout)
        assert report == {"points": expected}
        for row in report["points"]:
            for name in ("population", "capacity"):
                assert row[name] is None or type(row[name]) is int

    def refused(result):
        assert not result.stdout and result.stderr
        assert all(value not in result.stderr for value in (
            "Traceback", marker, str(workspace), str(source),
        ))

    portal_points = [
        point("lantern-lobby", "online", 8, 16, "players"),
        point("lantern-relay", "degraded", 3, 8, "connections"),
        point("lantern-beacon", "online", 1, None, "availability_only"),
    ]
    collector_points = [
        point("lantern-lobby", "online", 8, 16, "players"),
        point("lantern-relay", "degraded", 3, 8, "connections"),
        point("lantern-beacon", "offline", None, None, "availability_only"),
    ]
    valid(invoke(portal), portal_points)
    valid(invoke(collector, kind="collector"), collector_points)
    for name in ("empty.json", "unmapped.json", "max-bytes.json"):
        valid(invoke(workspace / name), [])

    for name in (
        "invalid-json.json", "invalid-utf8.json", "duplicate.json", "nonfinite.json",
        "float-overflow.json", "wrong-document.json", "wrong-rows.json",
        "wrong-row.json", "too-many-bytes.json", "too-many-rows.json", "missing.json", ".",
    ):
        refused(invoke(workspace / name, expected=2))

    for name in (
        "invalid-mapping.json", "invalid-collector-mapping.json", "duplicate-mapping.json",
        "nonfinite-mapping.json", "oversized-mapping.json", "too-many-mappings.json", "missing.json", ".",
    ):
        refused(invoke(portal, mapping=workspace / name, expected=2))

    refused(run([*cli, "--input", portal, "--mapping", sample_mapping], expected=2, extra_env=env))
    refused(invoke(portal, kind=marker, expected=2))

    audit = """
import os
from pathlib import Path
import runpy
import sys


source = Path(sys.argv.pop(1))


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn'} or event.startswith('socket.'):
        raise AssertionError('Snapshot normalizer attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Snapshot normalizer attempted a write')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp', 'sqlite3.connect'}:
        raise AssertionError('Snapshot normalizer attempted mutation or database access')


sys.addaudithook(verify_offline)
import player_telemetry_normalizer
assert Path(player_telemetry_normalizer.__file__).resolve().parent == source / 'player_telemetry_normalizer'
runpy.run_module('player_telemetry_normalizer', run_name='__main__', alter_sys=True)
"""
    for path, kind, expected in (
        (portal, "portal", portal_points), (collector, "collector", collector_points),
    ):
        result = run([*python, "-c", audit, source, *arguments(path, sample_mapping, kind)], extra_env=env)
        valid(result, expected)

    assert {path: digest(path) for path in initial} == initial
    assert set(workspace.iterdir()) == before
    return [
        "portal_automatic_and_explicit_metric_kinds",
        "collector_uses_connection_sessions",
        "availability_only_and_malformed_counts",
        "unknown_ids_and_metadata_omitted",
        "unmapped_and_empty_snapshots",
        "strict_json_input_and_mapping",
        "invalid_document_and_mapping_shapes",
        "input_byte_and_row_limits",
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
    print('TELEMETRY_NORMALIZER_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
