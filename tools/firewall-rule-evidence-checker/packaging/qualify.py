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
PACKAGE = 'firewall-rule-evidence-checker'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_original_offline.FirewallOriginalTests.test_port_ranges_expand_for_firewall_comparison',
    'test_original_offline.FirewallOriginalTests.test_exact_private_firewall_contract_is_allowed',
    'test_original_offline.FirewallOriginalTests.test_firewall_contract_rejects_broad_or_wrong_scope',
}
FOCUSED_TESTS = {
    'test_safeguards.FirewallSafeguardTests.test_mixed_or_lookalike_profiles_fail_closed',
    'test_safeguards.FirewallSafeguardTests.test_extra_ports_or_wildcard_fail_closed',
    'test_safeguards.FirewallSafeguardTests.test_extra_interfaces_and_addresses_fail_closed',
    'test_safeguards.FirewallSafeguardTests.test_cli_omits_saved_rule_details_from_all_outcomes',
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
    script = source / 'firewall_evidence.py'
    cli = [sys.executable, '-I', '-B', '-S', '-W', 'error', script]
    examples = source / 'examples'
    allowed_path = examples / 'allowed.json'
    allowed = json.loads(allowed_path.read_bytes())
    marker = 'fictional-private-marker'
    sensitive = (
        marker,
        str(workspace),
        str(source),
        allowed['service']['firewall_rule'],
        allowed['interface_alias'],
        allowed['local_ipv4'],
        'Traceback',
    )
    samples = {}

    def sample(name, data):
        path = workspace / f'fictional-{name}.json'
        path.write_bytes(data)
        samples[path] = digest(path)
        return path

    def saved(name, payload):
        return sample(name, (json.dumps(payload, ensure_ascii=True) + '\n').encode('ascii'))

    def assess(path, status):
        result = run([*cli, '--input', path], expected=0 if status == 'allowed' else 1)
        assert not result.stderr
        assert all(item not in result.stdout for item in (*sensitive, path.name))
        assert json.loads(result.stdout) == {'status': status}
        return result.stdout

    def refused(path):
        result = run([*cli, '--input', path], expected=2)
        assert not result.stdout and result.stderr.strip()
        assert all(item not in result.stderr for item in (*sensitive, path.name))

    def change_rule(name, **changes):
        case = json.loads(allowed_path.read_bytes())
        rule, = [rule for rule in case['policy']['rules']
                 if rule['display_name'] == case['service']['firewall_rule']]
        rule.update(changes)
        return saved(name, case)

    help_text = run([*cli, '--help'])
    assert not help_text.stderr and '--input' in help_text.stdout

    baseline = assess(allowed_path, 'allowed')
    assert assess(allowed_path, 'allowed') == baseline
    assess(examples / 'mismatch.json', 'mismatch')
    assess(examples / 'missing.json', 'missing')

    for index, profile in enumerate(('Private, Public', 'NotPrivate', 'Public')):
        assess(change_rule(f'profile-{index}', profile=profile), 'mismatch')

    expected = set(allowed['service']['ports'])
    extra_port = next(value for value in range(1, 65536) if value not in expected)
    assess(change_rule('excess-port', local_ports=[*sorted(expected), extra_port]), 'mismatch')
    assess(change_rule('wildcard-port', local_ports=[*sorted(expected), 'Any']), 'mismatch')

    assess(change_rule('excess-interface', interface_aliases=[allowed['interface_alias'], marker]), 'mismatch')
    other_ip = next(ip for ip in ('192.0.2.80', '192.0.2.81') if ip != allowed['local_ipv4'])
    assess(change_rule('excess-local-address', local_addresses=[allowed['local_ipv4'], other_ip]), 'mismatch')

    duplicate = json.loads(allowed_path.read_bytes())
    matching, = [rule for rule in duplicate['policy']['rules']
                 if rule['display_name'] == duplicate['service']['firewall_rule']]
    duplicate['policy']['rules'].append(matching.copy())
    assess(saved('ambiguous-matching-rule', duplicate), 'mismatch')
    assess(change_rule('malformed-rule-protocol', protocol={marker: []}), 'mismatch')
    assess(change_rule('malformed-rule-enabled', enabled=[marker]), 'mismatch')

    for index, value in enumerate((None, [marker], {'policy': [marker]}, {'service': marker})):
        refused(saved(f'invalid-snapshot-shape-{index}', value))
    refused(sample('invalid-json', f'[{marker}'.encode('ascii')))
    refused(sample('invalid-utf8', b'"\xff"'))
    refused(workspace / f'{marker}-unavailable.json')
    directory = workspace / f'{marker}-directory'
    directory.mkdir()
    refused(directory)
    limit = 256 * 1024
    valid_payload = allowed_path.read_bytes()
    assess(sample('exact-file-size', b' ' * (limit - len(valid_payload)) + valid_payload), 'allowed')
    refused(sample('excess-file-size', b' ' * (limit + 1 - len(valid_payload)) + valid_payload))

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
    audited = run([sys.executable, '-I', '-B', '-W', 'error', '-c', audit, script, allowed_path])
    assert audited.stdout == baseline and not audited.stderr
    assert all(digest(path) == original for path, original in samples.items())

    return [
        'checker_help',
        'fictional_saved_policy_allowed',
        'declared_mismatch_status',
        'missing_rule_status',
        'deterministic_status_only',
        'exact_private_profile',
        'exact_ports_and_wildcard_refusal',
        'exact_interface_and_address',
        'unique_matching_rule',
        'invalid_saved_shape',
        'bounded_ordinary_file',
        'neutral_output_all_outcomes',
        'offline_no_probe_guard',
        'offline_no_write_guard',
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
    print('FIREWALL_EVIDENCE_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
