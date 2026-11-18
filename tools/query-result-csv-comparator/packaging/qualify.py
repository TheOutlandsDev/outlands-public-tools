"""Validate a fresh extraction with the public Python module entry point."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'query-result-csv-comparator-0.1.0.zip'


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
    fixtures = workspace / 'fictional exports'
    shutil.copytree(source / 'examples', fixtures)
    input_pins = {path.name: digest(path) for path in fixtures.iterdir()}

    def cli(right, *options, expected=0, reason=None):
        completed = run([python, '-B', '-m', 'rdl_query_lab.compare_results',
                         fixtures / 'left.csv', fixtures / right, *options], workspace, expected)
        if expected == 2:
            assert not completed.stdout and reason in completed.stderr
            return None
        assert not completed.stderr
        return json.loads(completed.stdout)

    exact = cli('same.csv')
    assert exact['status'] == 'match' and exact['matched_rows'] == 3
    assert exact['columns_compared'] == 2 and not exact['column_mapping_used']
    assert (exact['left_rows'], exact['right_rows'], exact['left_only_rows'], exact['right_only_rows']) == (3, 3, 0, 0)
    mapped = cli('renamed.csv', '--mapping', fixtures / 'columns.json')
    assert mapped == {**exact, 'column_mapping_used': True}
    different = cli('changed.csv', '--max-examples', '1', expected=1)
    assert different['status'] == 'mismatch' and different['matched_rows'] == 2
    for side in ('left', 'right'):
        assert different[f'{side}_only_rows'] == 1 and different[f'{side}_only_distinct_rows'] == 1
        example, = different[f'{side}_only_examples']
        assert set(example) == {'sha256', 'count'} and example['count'] == 1
        assert re.fullmatch(r'[0-9a-f]{64}', example['sha256'])
    assert not any(word in json.dumps(different) for word in ('Larch', 'Cedar', 'fictional mismatch'))
    hidden = cli('changed.csv', '--max-examples', '0', expected=1)
    assert hidden == {**different, 'left_only_examples': [], 'right_only_examples': []}
    cli('invalid-header.csv', expected=2, reason='duplicate column names')
    cli('invalid-width.csv', expected=2, reason='different column count')
    cli('renamed.csv', expected=2, reason='provide a complete column mapping')
    cli('renamed.csv', '--mapping', fixtures / 'invalid-columns.json', expected=2, reason='duplicate key')
    cli('same.csv', '--max-examples', '21', expected=2, reason='max_examples must be an integer')
    assert {path.name: digest(path) for path in fixtures.iterdir()} == input_pins

    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    original_pins = json.loads((source / 'ORIGINAL-SHA256.json').read_bytes())
    assert len(original_pins) == 3 and all(digest(source / name) == pin for name, pin in original_pins.items())
    result = dict(status='PASS', package='query-result-csv-comparator', version='0.1.0',
        platform=sys.platform, python=platform.python_version(), source_revision=build['source_revision'],
        zip_sha256=build['sha256'], zip_bytes=build['bytes'], archive_members=build['files'],
        source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'), original_pins=original_pins,
        original_tests=7, passed=7, failures=0, errors=0, skipped=0, test_ids=test_ids,
        cli_checks=['reordered_bom_multiline_match', 'mapped_match', 'duplicate_count_mismatch',
                    'zero_digest_examples', 'duplicate_header', 'wrong_width', 'missing_mapping',
                    'duplicate_mapping_key', 'out_of_range_example_limit'],
        dependencies=[], fresh_extraction=True, fresh_venv=True, source_bytes_unchanged=True,
        input_bytes_unchanged=True, independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with report.open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print('CSVCMP_QUALIFICATION ' + json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
