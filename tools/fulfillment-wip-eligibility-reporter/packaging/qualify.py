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
PACKAGE = 'fulfillment-wip-eligibility-reporter'
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
    'tests/test_fulfillment_wip_eligibility.py::test_verification_supply_is_excluded_from_standard_production_allocation',
}
RUNTIME_DEPENDENCIES = {
    "pydantic", "pydantic-core",
    "annotated-types", "typing-inspection", "typing-extensions",
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
    assignment = source / "examples/assigned-wip.json"
    overrides = source / "examples/overrides.json"
    baseline = [digest(path) for path in (assignment, overrides)]
    script = source / "fulfillment_wip_eligibility.py"
    candidate = workspace / "input.json"
    inputs = json.loads(assignment.read_bytes())
    rule = json.loads(overrides.read_bytes())["contextual_kanban_overrides"][0]

    def invoke(source_path=assignment, *, override_path=None, error=None):
        args = [python, "-I", "-B", "-W", "error", script, source_path]
        if override_path is not None:
            args.extend(["--overrides", override_path])
        result = run(args, expected=2 if error else 0)
        if error:
            assert not result.stdout and error in result.stderr and "DO-NOT-ECHO" not in result.stderr
            return None
        assert not result.stderr
        return result.stdout

    def write(payload):
        candidate.write_text(json.dumps(payload), encoding="utf-8")
        return candidate

    output = invoke(override_path=overrides)
    assert output == invoke(override_path=overrides)
    report = json.loads(output)
    assert report["status"] == "PASS" and report["input_parts"] == 128
    assert report["eligible_parts"] == 80 and report["verification_parts"] == 48
    assert report["input_parts"] == report["eligible_parts"] + report["verification_parts"]
    assert report["eligible_by_product"] == {"DEMO-A": 65, "DEMO-B": 15}

    verified = {row["lot_id"]: row for row in report["verification_supply"]}
    assert {lot: row["quantity"] for lot, row in verified.items()} == {
        "DEMO-ALIAS-LOT": 11, "v-DEMO-PREFIX": 7,
        "DEMO-SUFFIX-LOT": 13, "DEMO-DASH-SUFFIX-LOT": 17,
    }
    assert all(row["policy"] == "Excluded from standard production allocation" for row in verified.values())
    assert [row["lot_id"] for row in report["verification_supply"]] == sorted(verified)
    assert verified["DEMO-ALIAS-LOT"]["kanban"] == 2

    unchanged = json.loads(invoke())
    assert unchanged["eligible_supply"][0]["kanban"] == 2
    unchanged["eligible_supply"][0]["kanban"] = 5
    assert unchanged == report
    near_misses = [{**rule, "operation": "stage 1"}, {**rule, "part_number": "demo-a"}]
    assert invoke(override_path=write({"contextual_kanban_overrides": near_misses})) == invoke()

    empty = json.loads(invoke(write({"records": []})))
    assert empty["input_parts"] == empty["eligible_parts"] == empty["verification_parts"] == 0
    assert empty["eligible_by_product"] == {}
    only_verification = [row for row in inputs["records"] if row["lot_id"] in verified]
    projected = json.loads(invoke(write({"records": only_verification})))
    assert projected["input_parts"] == projected["verification_parts"] == 48
    assert projected["eligible_parts"] == 0 and projected["eligible_supply"] == []

    invoke(override_path=write({"contextual_kanban_overrides": [rule, rule]}),
           error="Invalid override configuration JSON")
    invoke(override_path=write({"contextual_kanban_overrides": [{**rule, "kanban": 7}]}),
           error="Invalid override configuration JSON")
    row = inputs["records"][0]
    invoke(write({"records": [row, {**row, "lot_id": row["lot_id"].lower()}]}),
           error="Invalid assignment report JSON")
    invoke(write({"records": [{**row, "total_parts": "DO-NOT-ECHO"}]}),
           error="Invalid assignment report JSON")
    candidate.write_bytes(b" " * (4 * 1024 * 1024 + 1))
    invoke(candidate, error="exceeds the 4 MiB limit")

    assert [digest(path) for path in (assignment, overrides)] == baseline
    return ["eligible_product_totals_and_quantity_reconciliation", "original_verification_rules_and_policy",
            "exact_override_only_changes_eligible_match", "empty_and_verification_only_supply",
            "invalid_duplicate_and_oversized_input_refusal", "deterministic_read_only_inputs"]


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

    install_offline(run, python, source, prefix, wheels, selected, 'runtime', RUNTIME_DEPENDENCIES)
    verify_installs(run, python, prefix, bootstrap, selected, RUNTIME_DEPENDENCIES)
    cli_checks = check_offline_cli(run, python, source, workspace)
    install_offline(run, python, source, prefix, wheels, selected, 'test',
                    selected.keys() - RUNTIME_DEPENDENCIES)
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
        runtime_dependencies=sorted(RUNTIME_DEPENDENCIES), dependencies=selected, test_runner='pytest',
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), pip_version=bootstrap['pip'],
        offline_wheel_install=True, fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('FULFILLMENT_WIP_ELIGIBILITY_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
