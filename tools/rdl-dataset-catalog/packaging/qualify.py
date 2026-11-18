"""Validate a fresh extraction with the public Python module entry point."""
import argparse
import csv
import io
import pyexpat
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
ARCHIVE = 'rdl-dataset-catalog-0.1.0.zip'


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
    assert len(test_ids) == len(set(test_ids)) == 10 and 'Ran 10 tests' in completed.stderr
    assert completed.stderr.rstrip().endswith('OK')

    env['PYTHONPATH'] = str(source)
    external = workspace / 'fictional reports'
    external.mkdir()
    fixtures = external / 'examples'
    shutil.copytree(source / 'examples', fixtures)

    def contents(directory):
        return {path.relative_to(directory).as_posix(): path.read_bytes()
                for path in directory.rglob('*') if path.is_file()}

    input_files = contents(fixtures)
    output = workspace / 'new catalog'
    base_cli = [python, '-B', '-m', 'rdl_query_lab.build_catalog']

    def cli(*flags, expected=0):
        completed = run([*base_cli, '--source', fixtures, '--out', output, *flags], workspace, expected)
        if expected == 0:
            assert not completed.stderr
        return completed

    generated = cli()
    assert '2 RDLs, 3 datasets, 2 exact command files' in generated.stdout
    expected = contents(output)
    assert len(expected) == 6
    catalog = json.loads(expected['catalog.json'])
    assert catalog['format_version'] == 2 and catalog['source_root_name'] == 'examples'
    summary = catalog['summary']
    assert (summary['report_count'], summary['dataset_count']) == (2, 3)
    reports = {row['source_path']: row for row in catalog['reports']}
    detail = reports['DemoDetail.rdl']
    logic = reports['DemoLogic.rdl']
    assert detail['source_sha256'] == hashlib.sha256(input_files['DemoDetail.rdl']).hexdigest()
    assert detail['report_parameters'][0]['name'] == 'Day' and detail['subreports'] == ['OtherReport']
    assert logic['report_logic']['counts']['embedded_code_blocks'] == 1
    assert logic['report_logic']['counts']['calculated_fields'] == 1
    select, procedure = detail['datasets']
    assert select['lexical_class'] == 'select_sql' and select['shared_source_reference'] == '/Datasources/DEMO_MESODS'
    exact_command = "  SELECT 'café' AS Caption,\n    1 < 2 AS Flag\n".encode('utf-8')
    select_path = select['command_file']
    assert expected[select_path] == exact_command
    assert select['command_sha256'] == hashlib.sha256(exact_command).hexdigest()
    assert procedure['lexical_class'] == 'text_procedure_call'
    assert expected[procedure['command_file']] == b'EXEC [Reports].[GetParts]'
    assert logic['datasets'][0]['command_file'] is None
    queue = list(csv.DictReader(io.StringIO(expected['review_queue.csv'].decode('utf-8'))))
    assert len(queue) == 2 and all(row['tier'] == '05_dependency_review' for row in queue)

    second = workspace / 'independent output'
    run([*base_cli, '--out', second], workspace)
    assert contents(second) == expected
    assert 'PASS: 2 RDLs, 3 datasets, 2 exact command files' in cli('--check').stdout
    assert contents(output) == expected

    (output / select_path).write_bytes(b'changed fictional command\n')
    tampered = contents(output)
    changed = cli('--check', expected=1)
    assert f'Content mismatch: {select_path}' in changed.stderr and contents(output) == tampered
    (output / select_path).write_bytes(exact_command)
    (output / 'summary.md').unlink()
    (output / 'extra.txt').write_bytes(b'fictional stale output\n')
    stale = contents(output)
    changed = cli('--check', expected=1)
    assert 'Missing: summary.md' in changed.stderr and 'Unexpected: extra.txt' in changed.stderr
    assert contents(output) == stale
    refusal = cli(expected=1)
    assert 'Refusing to leave 1 stale generated files' in refusal.stderr and contents(output) == stale
    assert contents(fixtures) == input_files

    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    result = dict(status='PASS', package='rdl-dataset-catalog', version='0.1.0',
        platform=sys.platform, python=platform.python_version(), expat=pyexpat.EXPAT_VERSION,
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=10, passed=10, failures=0, errors=0, skipped=0, test_ids=test_ids,
        cli_checks=['catalog_generation', 'parsed_command_bytes_and_hashes', 'metadata_and_review_queue',
                    'repeatable_outputs_with_default_fixtures', 'check_clean_outputs',
                    'check_detects_byte_change', 'check_detects_missing_and_extra', 'stale_output_refusal'],
        fictional_reports=2, datasets=3, command_files=2, dependencies=[],
        fresh_extraction=True, fresh_venv=True, source_bytes_unchanged=True, input_bytes_unchanged=True,
        independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print('RDLCAT_QUALIFICATION ' + json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
