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
PACKAGE = 'game-telemetry-snapshot-verifier-replay'
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
    'tests/test_telemetry_snapshot_replay.py::TelemetryExporterTests::test_tampered_snapshot_is_rejected',
    'tests/test_telemetry_snapshot_replay.py::TelemetryExporterTests::test_offline_replay_runs_compute_without_model_gpu_or_writes',
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
    script = source / "telemetry_snapshot_replay.py"
    fixtures = sorted((source / "examples").glob("*.json"))
    programs = {"rust", "dayz", "main_spt", "modern_warfare", "zomboid"}
    assert {path.stem for path in fixtures} == programs
    before = {path: digest(path) for path in fixtures}
    edited = workspace / "snapshot.json"
    dayz = source / "examples/dayz.json"
    original = json.loads(dayz.read_bytes())

    def invoke(mode, path=dayz, *, error=None):
        result = run([python, "-E", "-s", "-B", "-W", "error", script, mode, path],
                     expected=2 if error else 0)
        if error:
            assert not result.stdout and error in result.stderr and "DO-NOT-ECHO" not in result.stderr
            return None
        assert not result.stderr
        return result.stdout

    def write(snapshot):
        edited.write_text(json.dumps(snapshot), encoding="utf-8")
        return edited

    def sha(value):
        data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def seal(snapshot):
        body = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
        return {**body, "snapshot_sha256": sha(body)}

    for fixture in fixtures:
        snapshot = json.loads(fixture.read_bytes())
        assert seal(snapshot) == snapshot
        assert json.loads(invoke("verify", fixture)) == {
            "ok": True, "program": fixture.stem, "record_count": len(snapshot["records"]),
            "snapshot_sha256": snapshot["snapshot_sha256"],
        }
        output = invoke("replay", fixture)
        assert output == invoke("replay", fixture)
        report = json.loads(output)
        assert report["source_snapshot_sha256"] == snapshot["snapshot_sha256"]
        assert report["program"] == fixture.stem and report["record_count"] == len(snapshot["records"])
        assert not any(report["runtime"].values())
        normalized = report["normalized"]["result"]
        features = report["features"]["result"]
        manifest = report["training_manifest"]["result"]
        assert report["features"]["audit"]["read_only"] is True
        assert manifest["dataset_name"] == f"{fixture.stem}-sanitized-replay"
        assert manifest["normalized_event_sha256"] == sha(normalized["events"])
        assert manifest["feature_sha256"] == sha(features)
        assert manifest["labels"] == sorted({row["event"] for row in normalized["events"]} - {"other"})
        assert manifest["output_path"] is None
        assert not any(manifest[name] for name in ("model_selected", "gpu_selected", "write_performed"))
        assert not manifest["ready_for_training"]
        for job in ("normalized", "features", "training_manifest"):
            assert "generated_utc" not in report[job]
            assert report[job]["result_sha256"] == sha(report[job]["result"])

    changed = {**original, "records": [{**original["records"][0], "event": "different"},
                                       *original["records"][1:]]}
    for mode in ("verify", "replay"):
        invoke(mode, write(changed), error="snapshot hash validation failed")
    reversed_items = dict(reversed(list(original.items())))
    assert invoke("replay", write(reversed_items)) == invoke("replay")
    for key, value, expected in (
        ("message", "DO-NOT-ECHO", "prohibited raw field"),
        ("actor", "DO-NOT-ECHO", "actor is not pseudonymized"),
        ("target", "DO-NOT-ECHO", "target is not pseudonymized"),
        ("map", "192.0.2.10", "network or platform ID"),
        ("mode", "999999999999", "network or platform ID"),
        ("team", "token", "secret-like field"),
    ):
        body = {**original, "records": [{**original["records"][0], key: value}]}
        invoke("replay", write(seal(body)), error=expected)
    invoke("verify", write(seal({**original, "program": ["DO-NOT-ECHO"]})), error="Unsupported telemetry program")
    invoke("verify", write(seal({**original, "schema_version": 2})), error="Unsupported telemetry snapshot schema")
    invoke("verify", write(seal({**original, "records": [False]})), error="records must be JSON objects")
    invoke("verify", write(seal({**original, "records": [{}] * 10001})), error="Invalid telemetry record array")
    edited.write_text('{"records": [], "records": "DO-NOT-ECHO"}', encoding="utf-8")
    invoke("verify", edited, error="Invalid telemetry JSON")
    edited.write_bytes(b" " * 2000001)
    invoke("verify", edited, error="exceeds 2,000,000 bytes")
    assert {path: digest(path) for path in fixtures} == before
    return ["all_five_profiles_verify_and_replay", "changed_record_refused_before_replay",
            "raw_fields_and_identity_rules", "manifest_hashes_and_read_only_audit",
            "malformed_and_oversized_input_refusal", "deterministic_read_only_inputs"]


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
    print('GAME_TELEMETRY_SNAPSHOT_REPLAY_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
