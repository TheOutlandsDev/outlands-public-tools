"""Validate a fresh extraction with the public Python module entry point."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import sqlite3
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'program-data-hub-0.1.0.zip'


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
           if not name.upper().startswith(('PYTHON', 'PROGRAM_DATA_', 'PIP_', 'LD_', 'DYLD_'))}
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
        'import importlib.metadata as m,json,sqlite3,sys; print(json.dumps([list(d.metadata["Name"] for d in m.distributions()), sqlite3.sqlite_version, sys.version.split()[0]]))'], workspace).stdout)
    assert actual == [[], sqlite3.sqlite_version, platform.python_version()]
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    completed = run([python, '-B', '-W', 'error', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], source)
    test_ids = re.findall(r'^(test_\w+ \([\w.]+\)) \.\.\. ok$', completed.stderr, re.MULTILINE)
    assert len(test_ids) == len(set(test_ids)) == 22 and 'Ran 22 tests' in completed.stderr
    assert completed.stderr.rstrip().endswith('OK')

    env['PYTHONPATH'] = str(source)
    db = workspace / 'demo data.sqlite3'
    backup = workspace / 'demo backup.sqlite3'
    fixtures = source / 'tests/fixtures'

    def cli(*arguments, expected=0):
        return run([python, '-B', '-m', 'program_data', '--database', db, *arguments], workspace, expected)

    initialized = json.loads(cli('init-db').stdout)
    assert initialized['applied_now'] == ['001_initial.sql', '002_sql_snapshot_identity.sql']
    assert initialized['user_version'] == 2 and initialized['quick_check'] == ['ok']
    assert json.loads(cli('init-db').stdout)['applied_now'] == []
    doc = json.loads(cli('ingest-document', fixtures / 'sample_document.md').stdout)
    retry = json.loads(cli('ingest-document', fixtures / 'sample_document.md').stdout)
    assert not doc['deduplicated'] and retry['deduplicated'] and retry['asset_id'] == doc['asset_id']
    hits = json.loads(cli('search-documents', 'calibration').stdout)
    assert len(hits) == 1 and '[calibration]' in hits[0]['snippet'].casefold()
    assert json.loads(cli('ingest-dataset', fixtures / 'sample_dataset.csv', '--key-column', 'id').stdout)['records_written'] == 2
    assert json.loads(cli('ingest-sql-export', fixtures / 'sample_sql_export.jsonl', '--query-key', 'demo-orders',
                          '--query-file', fixtures / 'sample_query.sql', '--record-key-column', 'order_id').stdout)['records_written'] == 2
    assert json.loads(cli('record-metric', '--metric-key', 'demo-count', '--value', '12', '--value-kind', 'numeric').stdout)['records_written'] == 1
    refusal = json.loads(cli('validate-query-contract', source / 'query_contracts/demo-movement.query-contract.json', expected=2).stdout)
    assert refusal['static_gate_passed'] is False and len(refusal['errors']) == 7
    status = json.loads(cli('status').stdout)
    assert status['quick_check'] == ['ok'] and status['foreign_key_violations'] == 0
    assert status['counts']['dataset_rows'] == status['counts']['sql_result_rows'] == 2
    assert status['counts']['metric_observations'] == 1
    assert json.loads(cli('backup', '--destination', backup).stdout)['quick_check'] == 'ok'
    backup_hash = digest(backup)
    cli('backup', '--destination', backup, expected=2)
    assert digest(backup) == backup_hash
    with closing(sqlite3.connect(backup.as_uri() + '?mode=ro', uri=True)) as copy:
        assert copy.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert copy.execute('SELECT COUNT(*) FROM dataset_rows').fetchone() == (2,)

    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    result = dict(status='PASS', package='program-data-hub', version='0.1.0',
        platform=sys.platform, python=platform.python_version(), sqlite=sqlite3.sqlite_version,
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=22, passed=22, failures=0, errors=0, skipped=0, test_ids=test_ids,
        cli_checks=['migrations', 'document_ingestion_and_retry', 'fts5', 'dataset_ingestion', 'export_ingestion',
                    'typed_metrics', 'static_contract_refusal', 'foreign_keys', 'backup_integrity_and_nonoverwrite'],
        dependencies=[], fresh_extraction=True, fresh_venv=True, source_bytes_unchanged=True,
        independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with report.open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print('HUB_QUALIFICATION ' + json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
