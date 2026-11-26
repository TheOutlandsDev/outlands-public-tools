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
PACKAGE = 'assistant-conversation-history-store'
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
    'tests/test_assistant_conversation_store.py::DatabaseTests::test_chat_and_tool_history_round_trip',
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
    script = source / 'assistant_conversation_store.py'
    probe = workspace / 'cli-probe'
    probe.mkdir()

    def invoke(path, *, expected=0):
        result = run(
            [python, '-I', '-B', '-W', 'error', script, 'demo', '--database', path],
            cwd=probe, expected=expected,
        )
        if expected:
            assert not result.stdout and 'Traceback' not in result.stderr and str(path) not in result.stderr
            return result.stderr
        assert not result.stderr
        return json.loads(result.stdout)

    path = probe / 'history.sqlite3'
    outcome = invoke(path)
    chat = outcome['chat']
    before = outcome['before_trim']
    after = outcome['after_trim']
    other = outcome['other_chat']
    other_messages = outcome['other_messages']
    assert chat['title'] == before[0]['content'] == 'Sketch a sample report'
    assert chat['model'] == other['model'] == 'fictional-model'
    assert [row['role'] for row in before] == ['user', 'assistant', 'tool']
    assert [row['id'] for row in before] == sorted({row['id'] for row in before})
    assert all(row['chat_id'] == chat['id'] for row in before)
    assert before[1]['tool_calls'] == [
        {'function': {'name': 'preview_note', 'arguments': {'section': 'summary'}}},
    ]
    assert before[2]['tool_name'] == 'preview_note'
    assert json.loads(before[2]['content']) == {'ok': True}
    assert after == before[:2]
    assert len(other_messages) == 1
    assert other_messages[0]['chat_id'] == other['id'] and other['id'] != chat['id']

    code = """
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

source, saved, disposable = map(Path, sys.argv[1:])
sys.path.insert(0, str(source))
from assistant_conversation_store import ChatDatabase

with closing(sqlite3.connect(saved)) as conn:
    assert conn.execute('PRAGMA journal_mode').fetchone() == ('wal',)
    assert conn.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
    assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    chats = conn.execute('SELECT id, title FROM chats').fetchall()
    assert sorted(title for _, title in chats) == ['Independent conversation', 'Sketch a sample report']
    rows = conn.execute('SELECT role, tool_calls_json FROM messages ORDER BY id').fetchall()
    assert [role for role, _ in rows] == ['user', 'assistant', 'user']
    assert json.loads(rows[1][1])[0]['function']['name'] == 'preview_note'

db = ChatDatabase(disposable)
first = db.create_chat('example-model')
other = db.create_chat('example-model', 'Unrelated title')
mark = db.add_message(first.id, 'user', '\\n[Attached local file: fictional.txt]\\nExample body')
assert db.get_chat(first.id).title == 'Local file conversation'
calls = [{'function': {'name': 'demo_tool', 'arguments': {'value': 'café'}}}]
db.add_message(first.id, 'assistant', tool_calls=calls)
db.add_message(first.id, 'tool', 'fictional result', tool_name='demo_tool')
db.add_message(other.id, 'user', 'Second chat')
reopened = ChatDatabase(disposable)
assert reopened.list_messages(first.id)[1].as_ollama() == {
    'role': 'assistant', 'content': '', 'tool_calls': calls,
}
assert reopened.list_messages(first.id)[2].as_ollama() == {
    'role': 'tool', 'content': 'fictional result', 'tool_name': 'demo_tool',
}
reopened.rename_chat(other.id, '  Renamed   example  ')
assert [chat.id for chat in reopened.list_chats('  Renamed  ')] == [other.id]
reopened.clear_messages_after(first.id, mark)
assert [message.id for message in reopened.list_messages(first.id)] == [mark]
assert len(reopened.list_messages(other.id)) == 1
reopened.delete_chat(first.id)
assert reopened.get_chat(first.id) is None and not reopened.list_messages(first.id)
assert len(reopened.list_messages(other.id)) == 1
print('preserved SQLite behavior')
"""
    result = run([python, '-I', '-B', '-W', 'error', '-c', code, source, path, probe / 'library.sqlite3'],
                 cwd=probe)
    assert result.stdout.strip() == 'preserved SQLite behavior' and not result.stderr

    original = digest(path)
    assert 'already exists' in invoke(path, expected=2)
    assert digest(path) == original
    secondary = probe / 'reserved.sqlite3'
    sidecar = secondary.with_name(secondary.name + '-wal')
    sidecar.write_bytes(b'fictional existing bytes')
    assert 'already exists' in invoke(secondary, expected=2)
    assert not secondary.exists() and sidecar.read_bytes() == b'fictional existing bytes'
    missing = probe / 'nonexistent' / 'history.sqlite3'
    assert 'Could not create' in invoke(missing, expected=2)
    assert not missing.parent.exists()
    help_text = run([python, '-I', '-B', '-W', 'error', script, 'demo', '--help'], cwd=probe)
    assert '--database' in help_text.stdout and not help_text.stderr
    return [
        'fresh_demo_database_round_trip_and_reopen',
        'message_order_and_tool_call_json',
        'automatic_titles_and_title_search',
        'trim_stays_in_one_conversation',
        'deletion_cascades_without_touching_other_conversations',
        'explicit_path_and_existing_database_or_sidecar_refused',
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
    print('ASSISTANT_CONVERSATION_HISTORY_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
