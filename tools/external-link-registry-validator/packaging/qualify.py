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
PACKAGE = 'external-link-registry-validator'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_original_offline.ExternalLinkRegistryOriginalTests.test_external_sidebar_registry_matches_approved_matrix_and_is_sorted',
    'test_original_offline.ExternalLinkRegistryOriginalTests.test_external_sidebar_registry_contains_no_embedded_session_credentials',
}
FOCUSED_TESTS = {
    'test_cli.ExternalLinkRegistryCLITests.test_accepts_fictional_registry_without_changing_input',
    'test_cli.ExternalLinkRegistryCLITests.test_rejects_exact_duplicate_and_out_of_order_labels',
    'test_cli.ExternalLinkRegistryCLITests.test_rejects_malformed_urls_without_disclosing_input',
    'test_cli.ExternalLinkRegistryCLITests.test_rejects_userinfo_and_encoded_session_fields_without_disclosing_input',
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
assert not loader.errors, loader.errors
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
    script = source / 'external_link_registry.py'
    cli = [sys.executable, '-I', '-B', '-S', '-W', 'error', script]
    examples = source / 'examples'
    registry = examples / 'registry.json'
    marker = 'fictional-private-marker'
    hidden = (marker, str(workspace), str(source), 'Traceback')
    samples = {}

    def sample(name, data):
        path = workspace / f'fictional-{name}.json'
        path.write_bytes(data)
        samples[path] = digest(path)
        return path

    def rows(name, entries):
        return sample(name, (json.dumps(entries, ensure_ascii=True) + '\n').encode('ascii'))

    def entry(label, href='https://fixture.invalid/start'):
        return {'label': label, 'href': href}

    def validate(path, *, expected=0):
        return run([*cli, '--input', path], expected=expected)

    def check_report(result, count):
        assert not result.stderr
        assert all(value not in result.stdout for value in hidden)
        report = json.loads(result.stdout)
        assert report == {'status': 'valid', 'count': count}
        assert type(report['count']) is int

    def refused(path, *, secrets=()):
        result = validate(path, expected=2)
        assert not result.stdout and result.stderr.strip()
        assert all(value not in result.stderr for value in (*hidden, path.name, *secrets))

    help_text = run([*cli, '--help'])
    assert not help_text.stderr and '--input' in help_text.stdout

    fixture = json.loads(registry.read_bytes())
    assert len(fixture) == 25
    assert all(set(row) == {'label', 'href'} for row in fixture)
    baseline = validate(registry)
    check_report(baseline, 25)
    assert validate(registry).stdout == baseline.stdout
    invalid = examples / 'invalid.json'
    refused(invalid, secrets=tuple(
        value
        for row in json.loads(invalid.read_bytes())
        for value in row.values()
    ))

    ordered = [entry('alpha'), entry('ALPHA'), entry('Bravo')]
    check_report(validate(rows('casefold-order', ordered)), len(ordered))
    refused(rows('unordered-labels', [ordered[2], *ordered[:2]]))
    refused(rows('duplicate-labels', [ordered[0], ordered[0]]))

    bad_destinations = (
        'https:///no-host',
        'ftp://fixture.invalid/start',
        'https://[::1',
        'https://fixture.invalid:99999/start',
        'https://fixture.invalid:bad/start',
        'https://fixture.invalid/white space',
        'https://fixture.invalid/line\nbreak',
    )
    for index, href in enumerate(bad_destinations):
        refused(rows(f'malformed-destination-{index}', [entry(marker, href)]), secrets=(href,))
    check_report(validate(rows('explicit-port', [entry('Fictional Port', 'http://fixture.invalid:8080/start')])), 1)

    for index, authority in enumerate(('@', f'{marker}:secret@', f':{marker}@')):
        href = f'https://{authority}fixture.invalid/start'
        refused(rows(f'embedded-userinfo-{index}', [entry(marker, href)]), secrets=(href,))

    for index, key in enumerate(('%53eSsIoNiD', 's%65ssion', '%54IcKeT', 'AcCeSs%5FToKeN', '%74OKeN')):
        href = f'https://fixture.invalid/start?{key}='
        refused(rows(f'encoded-blank-query-{index}', [entry(marker, href)]), secrets=(href, key))
    check_report(validate(rows('ordinary-query', [entry('Fictional Query', 'https://fixture.invalid/start?view=')])), 1)

    invalid_shapes = (
        [],
        {'entries': [entry(marker)]},
        [None],
        [{'label': marker}],
        [{'label': marker, 'href': 'https://fixture.invalid/start', 'extra': True}],
        [entry(marker, 42)],
    )
    for index, value in enumerate(invalid_shapes):
        refused(rows(f'bad-shape-{index}', value))
    limit_rows = [entry(f'Fictional Entry {index:04}') for index in range(1024)]
    check_report(validate(rows('entry-count-limit', limit_rows)), 1024)
    refused(rows('above-entry-count-limit', [*limit_rows, entry('Fictional Entry 1024')]))

    refused(sample('private-malformed-json', f'[{marker}'.encode('ascii')))
    refused(sample('invalid-utf8', b'"\xff"'))
    refused(workspace / f'{marker}-missing.json')
    directory = workspace / f'{marker}-directory'
    directory.mkdir()
    refused(directory)
    limit = 256 * 1024
    valid_payload = registry.read_bytes()
    check_report(validate(sample('file-size-limit', b' ' * (limit - len(valid_payload)) + valid_payload)), 25)
    refused(sample('over-file-size-limit', b' ' * (limit + 1 - len(valid_payload)) + valid_payload))

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
    audited = run([sys.executable, '-I', '-B', '-W', 'error', '-c', audit, script, registry])
    assert audited.stdout == baseline.stdout and not audited.stderr
    assert all(digest(path) == before for path, before in samples.items())

    return [
        'registry_help',
        'fictional_registry_acceptance',
        'deterministic_fixed_shape_report',
        'fixture_sensitive_key_refusal',
        'casefold_label_order',
        'exact_duplicate_labels',
        'malformed_destination_rejection',
        'embedded_userinfo_refusal',
        'encoded_casefolded_blank_query_keys',
        'strict_registry_shape_and_count',
        'bounded_regular_file_input',
        'opaque_diagnostics',
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
           if not name.upper().startswith(('PYTHON', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1')

    def run(args, *, cwd=workspace, expected=0):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                capture_output=True, encoding='utf-8', timeout=90)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    test_ids = run_tests(run, source, workspace)
    cli_checks = check_offline_cli(run, source, workspace)
    run([sys.executable, '-I', '-B', source / 'source_check.py'])
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} == names
    assert {name: digest(source / name) for name in names} == before_source
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
    print('EXTERNAL_LINKS_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
