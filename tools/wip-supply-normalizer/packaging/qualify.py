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
PACKAGE = 'wip-supply-normalizer'
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
    'tests/test_original_offline.py::test_legacy_normalization_and_completed_material_are_explicit',
    'tests/test_original_offline.py::test_unlisted_step_preserves_raw_quantity',
    'tests/test_original_offline.py::test_blank_quantities_become_zero_without_mutating_input',
    'tests/test_original_offline.py::test_duplicate_lot_identity_fails_closed',
}
FOCUSED_TESTS = {
    'tests/test_safeguards.py::test_exact_half_tie_rounds_up',
    'tests/test_safeguards.py::test_duplicate_source_row_fails_closed',
    'tests/test_safeguards.py::test_repeated_cli_runs_preserve_totals_hashes_and_input',
}
RUNTIME_DEPENDENCIES = [
    'annotated-types', 'pydantic', 'pydantic-core', 'typing-extensions', 'typing-inspection',
]


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
    assert len(identifiers) == len(ORIGINAL_TESTS) + len(FOCUSED_TESTS)
    assert set(identifiers) == ORIGINAL_TESTS | FOCUSED_TESTS
    return identifiers


def check_offline_cli(run, python, source, workspace):
    from decimal import Decimal, ROUND_FLOOR, localcontext

    script = source / 'wip_supply.py'
    cli = [python, '-I', '-B', '-W', 'error', script]
    examples = source / 'examples'
    normalization = examples / 'normalization.json'
    marker = 'fictional-private-marker'
    hidden = (marker, str(workspace), str(source), 'Traceback')
    samples = {}

    def sample(name, data):
        path = workspace / f'fictional-{name}.json'
        path.write_bytes(data)
        samples[path] = digest(path)
        return path

    def validate(path, *, expected=0):
        return run([*cli, '--input', path], expected=expected)

    def refused(path, *, reason=None, secrets=()):
        result = validate(path, expected=2)
        assert not result.stdout and result.stderr.strip()
        assert all(value not in result.stderr for value in (*hidden, path.name, *secrets))
        if reason is not None:
            assert reason in result.stderr

    def mutation(name, change):
        value = json.loads(normalization.read_bytes())
        change(value)
        return sample(name, (json.dumps(value, ensure_ascii=True) + '\n').encode('ascii'))

    def canonical_digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    help_text = run([*cli, '--help'])
    assert not help_text.stderr and '--input' in help_text.stdout
    selected = json.loads(normalization.read_bytes())
    configuration = selected['configuration']
    rate = Decimal(str(configuration['early_stage_loss_rate']))
    expected_records = []
    has_half_tie = False
    completion_fields = ('packaging_quantity', 'qa_far_quantity', 'pack_and_ship_quantity')
    with localcontext() as context:
        context.prec = 80
        for row in selected['records']:
            raw = row.get('wip_quantity') or 0
            applies = row['step_name'] in configuration['early_stage_steps']
            unrounded_loss = raw * rate if applies else Decimal(0)
            loss = int((unrounded_loss + Decimal('0.5')).to_integral_value(rounding=ROUND_FLOOR))
            has_half_tie |= applies and unrounded_loss % 1 == Decimal('0.5')
            expected_records.append({
                'source_row': row['source_row'],
                'product': row['product_name'],
                'lot_id': row['material_name'],
                'current_step': row['step_name'],
                'quantity_in_process_raw': raw,
                'normalization_applied': applies,
                'yield_loss_quantity': loss,
                'quantity_in_process': raw - loss,
                'parts_completed': sum(row.get(key) or 0 for key in completion_fields),
            })
    assert has_half_tie, 'Fictional fixture must exercise an exact half-tie'
    assert any(not row['normalization_applied'] and row['quantity_in_process_raw'] > 0
               for row in expected_records), 'Fictional fixture must exercise selected-step pass-through'
    assert any(row.get('wip_quantity') is None for row in selected['records'])
    assert any(row['parts_completed'] > 0 for row in expected_records)
    expected = {
        'status': 'normalized',
        'records': expected_records,
        'input_record_count': len(expected_records),
        'affected_record_count': sum(row['normalization_applied'] for row in expected_records),
        'zero_or_blank_wip_count': sum(row['quantity_in_process_raw'] == 0 for row in expected_records),
        'raw_wip_total': sum(row['quantity_in_process_raw'] for row in expected_records),
        'normalized_wip_total': sum(row['quantity_in_process'] for row in expected_records),
        'yield_loss_total': sum(row['yield_loss_quantity'] for row in expected_records),
        'completed_total': sum(row['parts_completed'] for row in expected_records),
        'row_set_sha256': canonical_digest(expected_records),
        'configuration_sha256': canonical_digest({
            'early_stage_steps': configuration['early_stage_steps'],
            'early_stage_loss_rate': str(rate),
        }),
    }
    before_output = validate(normalization)
    assert not before_output.stderr and json.loads(before_output.stdout) == expected
    repeated = validate(normalization)
    assert not repeated.stderr and repeated.stdout == before_output.stdout

    refused(examples / 'invalid.json', reason='duplicate WIP source row')

    def duplicate_lot(data):
        records = data['records']
        records[1]['material_name'] = records[0]['material_name']

    refused(mutation('duplicate-lot', duplicate_lot), reason='duplicate WIP lot identity')
    refused(mutation('bad-number', lambda data: data['records'][0].update(wip_quantity=marker)))
    refused(mutation('unknown-field', lambda data: data['records'][0].update(unknown=marker)))
    refused(mutation('missing-records', lambda data: data.pop('records')))
    refused(sample('malformed-input', f'{{"{marker}"'.encode('ascii')))
    refused(sample('duplicate-key', b'{"configuration":{},"records":[],"records":[]}'))
    refused(sample('invalid-utf8', b'"\xff"'))
    refused(sample('oversized', b' ' * (1024 * 1024 + 1)))
    refused(workspace / f'{marker}-missing.json')

    audit = """
import os
from pathlib import Path
import runpy
import sys

script, selected = (Path(item).resolve() for item in sys.argv[1:])
sys.argv = [str(script), '--input', str(selected)]
selected = os.path.normcase(str(selected))
reads = []


def verify_offline(event, args):
    if event.startswith(('socket.', 'ctypes.', 'winreg.')):
        raise AssertionError('Unexpected network or platform probe')
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn',
                 'os.startfile', 'os.kill'}:
        raise AssertionError('Unexpected process invocation')
    if event == 'open':
        flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        if args[2] & flags:
            raise AssertionError('Unexpected file write')
        path = args[0]
        if isinstance(path, (bytes, str)) and os.path.normcase(os.fsdecode(path)) == selected:
            reads.append(selected)
    if event in {'os.rename', 'os.link', 'os.remove', 'os.rmdir', 'os.mkdir', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkdtemp', 'tempfile.mkstemp',
                 'shutil.rmtree'}:
        raise AssertionError('Unexpected filesystem mutation')


sys.addaudithook(verify_offline)
try:
    runpy.run_path(str(script), run_name='__main__')
except SystemExit as exc:
    if exc.code not in (0, None):
        raise
assert reads == [selected]
"""
    audited = run([python, '-I', '-B', '-W', 'error', '-c', audit, script, normalization])
    assert audited.stdout == before_output.stdout and not audited.stderr
    assert all(digest(path) == before for path, before in samples.items())

    return [
        'normalizer_help',
        'fictional_normalization',
        'exact_half_up_rounding',
        'unlisted_step_passthrough',
        'blank_quantities_and_completed_total',
        'deterministic_row_and_configuration_hashes',
        'duplicate_source_row_refusal',
        'duplicate_lot_identity_refusal',
        'invalid_saved_input_refusal',
        'offline_read_only_audit_guard',
        'extracted_source_and_inputs_unchanged',
    ]


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
                    selected.keys() - set(RUNTIME_DEPENDENCIES))
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
        original_tests=len(ORIGINAL_TESTS), passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=RUNTIME_DEPENDENCIES, dependencies=selected, test_runner='pytest',
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), pip_version=bootstrap['pip'],
        offline_wheel_install=True, fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('WIP_SUPPLY_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
