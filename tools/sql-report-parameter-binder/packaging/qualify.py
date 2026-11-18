"""Validate a fresh extraction with the public Python API."""
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
ARCHIVE = 'sql-report-parameter-binder-0.1.0.zip'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(packages, workspace, report, receipt, reference=None):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    archive = packages / ARCHIVE
    manifest = packages / 'build-manifest.json'
    build = json.loads(manifest.read_bytes())
    assert build['filename'] == ARCHIVE and build['version'] == '0.1.0'
    assert build['sha256'] == digest(archive) and build['bytes'] == archive.stat().st_size
    if reference is not None:
        assert archive.read_bytes() == (reference / ARCHIVE).read_bytes()
        assert manifest.read_bytes() == (reference / manifest.name).read_bytes()
    sdk = json.loads(receipt.read_bytes())
    lock = json.loads((ROOT / 'PYTHON-LOCK.json').read_bytes())
    minor = f'{sys.version_info.major}.{sys.version_info.minor}'
    pin = lock['python_archives'][sys.platform][minor]
    assert sdk['status'] == 'PASS' and sdk['archive'] == pin
    assert sdk['platform'] == sys.platform and sdk['python_version'] == platform.python_version() == pin['python']
    assert sdk['python_lock_sha256'] == digest(ROOT / 'PYTHON-LOCK.json')
    assert sdk['preparation_helper_sha256'] == digest(ROOT / 'packaging/prepare_python.py')
    assert sdk['executable_sha256'] == digest(Path(sys._base_executable))

    workspace = workspace.resolve()
    workspace.mkdir()
    source = workspace / ARCHIVE.removesuffix('.zip')
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        assert len({item.filename.casefold() for item in members}) == len(members) == build['files']
        for item in members:
            name = item.filename
            parts = name.split('/')
            assert len(parts) > 1 and parts[0] == source.name
            assert str(PurePosixPath(name)) == name and all(part not in ('', '.', '..') for part in parts)
            assert ':' not in name and '\\' not in name and item.file_size < 1024 * 1024
            assert stat.S_ISREG(item.external_attr >> 16)
        assert bundle.testzip() is None
        bundle.extractall(workspace)

    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1')

    def run(args, cwd, expected=0):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                capture_output=True, encoding='utf-8', timeout=90)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    run([sys.executable, '-I', '-B', '-m', 'venv', '--without-pip', workspace / 'venv'], workspace)
    python = workspace / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    actual = json.loads(run([python, '-I', '-B', '-c',
        'import importlib.metadata as m,json,sys; print(json.dumps([list(d.metadata["Name"] for d in m.distributions()), sys.version.split()[0]]))'], workspace).stdout)
    assert actual == [[], platform.python_version()]
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    completed = run([python, '-B', '-W', 'error', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], source)
    test_ids = re.findall(r'^(test_\w+ \([\w.]+\)) \.\.\. ok$', completed.stderr, re.MULTILINE)
    assert len(test_ids) == len(set(test_ids)) == 7 and 'Ran 7 tests' in completed.stderr
    assert completed.stderr.rstrip().endswith('OK')

    env['PYTHONPATH'] = str(source)
    completed = run([python, '-B', '-W', 'error', '-c', '''
from datetime import date, datetime
import json
from queries.report_detail.bind import build_detail_query

start = date(2026, 1, 10)
end = datetime(2026, 1, 11, 16, 30)
selected = ["DEMO-61", "Échantillon d'essai"]
options = {"DEMO-11", *selected}
sql, parameters = build_detail_query(start_date=start, end_date=end,
    selected_products=selected, product_options=options)
assert parameters == (start, end, *selected)
assert sql.count('?') == 4 and 'PR.Name IN (?, ?)' in sql
assert all(product not in sql for product in selected) and '/*PRODUCT_PARAMETERS*/' not in sql

same_day = datetime(2026, 1, 10, 8)
sql, parameters = build_detail_query(start_date=datetime(2026, 1, 10, 20), end_date=same_day,
    selected_products=selected[:1], product_options=options)
assert 'PR.Name IN (?)' in sql and parameters[1] is same_day

def reject(expected, *, first=start, last=end, products=selected, available=options):
    try:
        build_detail_query(start_date=first, end_date=last,
            selected_products=products, product_options=available)
    except ValueError as error:
        assert expected in str(error)
    else:
        raise AssertionError('Expected validation failure')

reject('end_date', first=end, last=start)
reject('unique', products=[selected[0], selected[0]])
reject('absent', products=['DEMO-UNKNOWN'])
reject('at least one', products=[])

boundary = [f'DeMo-Item-{number:04d}' for number in range(2098)]
sql, parameters = build_detail_query(start_date=start, end_date=end,
    selected_products=boundary, product_options=set(boundary))
assert sql.count('?') == len(parameters) == 2100
assert parameters[:2] == (start, end) and parameters[2:] == tuple(boundary)
assert 'DeMo-Item-' not in sql
too_many = boundary + ['DEMO-EXTRA']
reject('2098', products=too_many, available=set(too_many))

print(json.dumps(['ordered_dates_and_product_parameters', 'same_calendar_day',
    'reversed_dates', 'duplicate_selection', 'unknown_selection', 'empty_selection',
    'maximum_2100_parameters', 'reject_parameter_2101']))
'''], workspace)
    api_checks = json.loads(completed.stdout)
    assert len(api_checks) == len(set(api_checks)) == 8 and not completed.stderr
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    result = dict(status='PASS', package='sql-report-parameter-binder', version='0.1.0',
        platform=sys.platform, python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=7, passed=7, failures=0, errors=0, skipped=0, test_ids=test_ids,
        api_checks=api_checks, accepted_maximum_parameters=2100, rejected_parameters=2101,
        dependencies=[], fresh_extraction=True, fresh_venv=True, source_bytes_unchanged=True,
        independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print('SQLBIND_QUALIFICATION ' + json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
