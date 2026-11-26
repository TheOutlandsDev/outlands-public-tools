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
PACKAGE = 'game-event-normalizer-actor-statistics-reporter'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
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



ORIGINAL_TESTS = {
    'tests/test_game_event_statistics.py::ComputeBackendTests::test_normalization_discards_raw_messages_and_maps_game_events',
    'tests/test_game_event_statistics.py::ComputeBackendTests::test_behavior_features_are_deterministic_and_actor_scoped',
}


def installed_versions(run, python, prefix):
    code = """
from importlib.metadata import distributions
import json
from pathlib import Path
import sys

assert Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve()
assert sys.prefix != sys.base_prefix
print(json.dumps({d.metadata['Name'].lower().replace('_', '-'): d.version for d in distributions()}))
"""
    result = run([python, '-I', '-B', '-W', 'error', '-c', code, prefix])
    assert not result.stderr
    return json.loads(result.stdout)


def install_offline(run, python, source, prefix, wheels, selected, requirement, expected):
    report = prefix / f'{requirement}-pip-private.json'
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'install',
         '--no-index', '--find-links', wheels, '--only-binary=:all:', '--require-hashes',
         '--no-deps', '--no-cache-dir', '--report', report, '-r', source / f'requirements-{requirement}.txt'])
    from urllib.parse import urlsplit
    from urllib.request import url2pathname

    receipt = json.loads(report.read_bytes())
    added = set()
    for item in receipt['install']:
        name = item['metadata']['name'].lower().replace('_', '-')
        pin = selected[name]
        download = item['download_info']
        uri = urlsplit(download['url'])
        assert name not in added and item['metadata']['version'] == pin['version']
        assert uri.scheme == 'file' and not uri.netloc and not uri.query and not uri.fragment
        assert Path(url2pathname(uri.path)).resolve() == (wheels / pin['filename']).resolve()
        assert download['archive_info']['hashes']['sha256'] == pin['sha256']
        added.add(name)
    assert added == set(expected)
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'check'])


def verify_installs(run, python, prefix, bootstrap, selected, names):
    expected = dict(bootstrap)
    expected.update({name: selected[name]['version'] for name in names})
    assert installed_versions(run, python, prefix) == expected


def run_tests(run, python, source):
    code = """
import json
from pathlib import Path
import sys

import pytest


class Evidence:
    def __init__(self):
        self.collected = []
        self.passed = []
        self.problem = False

    def pytest_collection_finish(self, session):
        self.collected = [item.nodeid for item in session.items]

    def pytest_runtest_logreport(self, report):
        if report.failed or report.skipped or hasattr(report, 'wasxfail'):
            self.problem = True
        elif report.when == 'call' and report.passed:
            self.passed.append(report.nodeid)


source = Path(sys.argv[1])
sys.path.insert(0, str(source))
proof = Evidence()
exit_code = pytest.main(['-q', '-p', 'no:cacheprovider', 'tests'], plugins=[proof])
assert exit_code == 0 and not proof.problem
assert sorted(proof.collected) == sorted(proof.passed)
print(json.dumps(sorted(proof.passed)))
"""
    result = run([python, '-I', '-B', '-W', 'error', '-c', code, source], cwd=source)
    assert not result.stderr
    identifiers = json.loads(result.stdout.strip().splitlines()[-1])
    assert len(identifiers) == len(ORIGINAL_TESTS)
    assert set(identifiers) == ORIGINAL_TESTS
    return identifiers


def check_offline_cli(run, python, source, workspace):
    script = source / "game_event_statistics.py"
    events = source / "examples/events.json"
    match = source / "examples/match.json"
    inputs = (events, match)
    before = [digest(path) for path in inputs]
    edited = workspace / "input.json"

    def invoke(mode="normalize", profile="fika", path=events, *, error=None):
        result = run([python, "-I", "-B", "-W", "error", script, mode, profile, path],
                     expected=2 if error else 0)
        if error:
            assert not result.stdout and error in result.stderr and "DO-NOT-ECHO" not in result.stderr
            return None
        assert not result.stderr
        return result.stdout

    def write(payload):
        edited.write_text(json.dumps(payload), encoding="utf-8")
        return edited

    output = invoke()
    assert output == invoke(profile="main_spt")
    result = json.loads(output)
    normalized = result["result"]
    assert normalized["program"] == "main_spt" and normalized["record_count"] == 3
    assert normalized["known_event_count"] == 2 and normalized["unknown_event_count"] == 1
    assert [item["event"] for item in normalized["events"]] == ["kill", "extract", "other"]
    assert normalized["events"][0]["context"] == {"weapon": "demo rifle"}
    assert normalized["events"][0]["actor"] == "Demo Actor A"
    assert normalized["raw_messages_retained"] is False
    assert "FICTIONAL-RAW-MESSAGE" not in output and "192.0.2.12" not in output
    for item in normalized["events"]:
        assert "message" not in item and "ip" not in item

    stats_output = invoke("statistics", "iw4x", match)
    assert stats_output == invoke("statistics", "modern_warfare", match)
    stats = json.loads(stats_output)
    rows = stats["result"]["actor_features"]
    assert [row["actor"] for row in rows] == ["Demo Actor A", "Demo Actor B"]
    assert [(row["events"], row["kills"], row["deaths"], row["assists"], row["damage"]) for row in rows] == [
        (4, 1, 1, 1, 75.0), (2, 1, 0, 0, 40.25),
    ]
    assert [row["engagement_score"] for row in rows] == [5.25, 3.402]
    assert stats["result"]["unique_actor_count"] == 2 and stats["result"]["session_count"] == 1
    assert stats["result"]["behavior_control_generated"] is False
    for report in (result, stats):
        assert "generated_utc" not in report and report["ok"] is True
        canonical = json.dumps(report["result"], ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False).encode("utf-8")
        assert hashlib.sha256(canonical).hexdigest() == report["result_sha256"]
        identity = {"schema_version": 1, "program": report["contract"]["program"],
                    "function": report["contract"]["function"], "payload_sha256": report["input_sha256"]}
        assert report["job_id"] == hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("ascii")
        ).hexdigest()[:24]
        assert report["audit"]["read_only"] is True
        assert not any(value for name, value in report["audit"].items() if name != "read_only")

    reordered = json.loads(events.read_bytes())
    mutated = [dict(reversed(tuple(item.items()))) for item in reordered["records"]]
    assert invoke(path=write({"records": mutated})) == output
    empty = json.loads(invoke("statistics", "iw4x", write({"records": []})))["result"]
    assert empty["record_count"] == empty["unique_actor_count"] == 0 and empty["actor_features"] == []

    invoke(path=write({"records": [], "command": "DO-NOT-ECHO"}), error="forbidden execution fields")
    invoke(path=write({"records": [None]}), error="every telemetry record")
    invoke(path=write({"records": [{}] * 10001}), error="at most 10000 items")
    invoke(profile="unlisted", error="Unknown compute program")
    edited.write_text('{"records": [], "records": "DO-NOT-ECHO"}', encoding="utf-8")
    invoke(path=edited, error="Invalid telemetry JSON")
    edited.write_bytes(b" " * 2000001)
    invoke(path=edited, error="exceeds 2,000,000 bytes")
    assert [digest(path) for path in inputs] == before

    return ["original_event_aliases_and_field_allowlist", "actor_scoped_statistics_and_session_counts",
            "stable_job_identity_and_result_sha256", "read_only_audit_and_empty_input",
            "invalid_forbidden_and_oversized_input_refusal", "deterministic_read_only_inputs"]


def qualify(packages, workspace, report, receipt, reference):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    workspace = workspace.resolve()
    sdk = check_interpreter(receipt)
    build, source, names = unpack(packages, workspace, reference)
    before_source = {name: digest(source / name) for name in names}
    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PYTEST_', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')

    def run(args, *, cwd=workspace, expected=0):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                capture_output=True, encoding='utf-8', timeout=180)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    wheels = workspace / 'wheels'
    selected = json.loads(run([sys.executable, '-I', '-B', source / 'packaging/prepare_wheels.py',
                               '--out', wheels]).stdout)
    assert {path.name for path in wheels.iterdir()} == {pin['filename'] for pin in selected.values()}
    assert all(digest(wheels / pin['filename']) == pin['sha256'] for pin in selected.values())
    prefix = workspace / 'venv'
    run([sys.executable, '-I', '-B', '-m', 'venv', prefix])
    python = prefix / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    bootstrap = installed_versions(run, python, prefix)
    assert 'pip' in bootstrap and bootstrap.keys() <= {'pip', 'setuptools'}

    verify_installs(run, python, prefix, bootstrap, selected, ())
    cli_checks = check_offline_cli(run, python, source, workspace)
    install_offline(run, python, source, prefix, wheels, selected, 'test', selected.keys())
    verify_installs(run, python, prefix, bootstrap, selected, selected.keys())
    test_ids = run_tests(run, python, source)

    run([sys.executable, '-I', '-B', source / 'source_check.py'])
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} == names
    assert {name: digest(source / name) for name in names} == before_source
    assert all(digest(wheels / pin['filename']) == pin['sha256'] for pin in selected.values())
    evidence = dict(
        status='PASS', package=PACKAGE, version=VERSION, platform=sys.platform, python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_test_functions=len(ORIGINAL_TESTS), original_test_cases=len(ORIGINAL_TESTS), passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=[], dependencies=selected, test_runner='pytest',
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), pip_version=bootstrap['pip'],
        offline_wheel_install=True, fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('GAME_EVENT_STATISTICS_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
