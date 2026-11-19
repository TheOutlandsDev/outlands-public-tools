"""Validate the released source ZIP on a verified interpreter and a fresh test environment."""

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
PACKAGE = 'game-install-profile-checker'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_games.GameProfileTests.test_profile_list_and_check',
    'test_cli.CLITests.test_game_check_human_output_includes_profile_engine',
}
FOCUSED_TESTS = {
    'test_game_profile_safety.GameProfileSafetyTests.test_missing_installation_files_are_reported',
    'test_game_profile_safety.GameProfileSafetyTests.test_duplicate_names_are_warned_and_check_fails',
    'test_game_profile_safety.GameProfileSafetyTests.test_disabled_and_other_platform_profiles_skip_missing_files',
    'test_game_profile_safety.GameProfileSafetyTests.test_port_declarations_require_integer_range',
    'test_game_profile_safety.GameProfileSafetyTests.test_expect_running_stays_offline',
    'test_game_profile_safety.GameProfileSafetyTests.test_malformed_toml_diagnostics_are_generic',
    'test_game_profile_safety.GameProfileSafetyTests.test_declared_paths_cannot_escape_installation_root',
    'test_game_profile_safety.GameProfileSafetyTests.test_links_cannot_leave_selected_root',
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
    python = [sys.executable, "-B", "-S", "-W", "error"]
    cli = [*python, "-m", "opskit"]
    env = {"PYTHONPATH": str(source)}
    fixture = workspace / "fictional home"
    marker = "fictional-private-diagnostic-marker"

    def tree_bytes(root):
        return {path.relative_to(root).as_posix(): digest(path) if path.is_file() else None
                for path in root.rglob("*")}

    def valid(result):
        assert not result.stderr
        return json.loads(result.stdout)

    def invoke(home, *args, expected=0):
        return valid(run([*cli, "--home", home, "game", *args, "--json"], expected=expected, extra_env=env))

    def profile_path(home):
        return home / "config" / "game-profiles" / "demo.toml"

    def variant(name, **changes):
        home = workspace / name
        shutil.copytree(fixture, home)
        path = profile_path(home)
        config = path.read_text(encoding="utf-8")
        for key, value in changes.items():
            config, count = re.subn(fr"^{re.escape(key)}\s*=.*$", lambda _match: f"{key} = {value}",
                                    config, flags=re.MULTILINE)
            if not count:
                config = config.rstrip() + f"\n{key} = {value}\n"
        path.write_text(config, encoding="utf-8", newline="\n")
        return home

    def checks(report):
        assert report["data"]["count"] == 1
        profile, = report["data"]["profiles"]
        return {row["name"]: row["status"] for row in profile["checks"]}

    def failed(home):
        report = invoke(home, "check", "--all", expected=1)
        assert report["ok"] is False and report["data"]["status"] == "fail"
        return report

    run([*python, source / "examples" / "create_sample.py", fixture])
    before = tree_bytes(fixture)
    assert before["servers/demo/server.bin"]
    assert before["servers/demo/saves/fixture.marker"]
    listed = invoke(fixture, "list")
    assert listed["ok"] is True and listed["data"]["count"] == 1 and listed["data"]["read_only"] is True
    listed_profile, = listed["data"]["profiles"]
    assert listed_profile["name"] == "demo" and listed_profile["engine"] == "standalone"
    assert not listed["warnings"]
    report = invoke(fixture, "check", "--all")
    assert report["ok"] is True and report["data"]["status"] == "pass" and report["data"]["read_only"] is True
    outcomes = checks(report)
    for label in ("install_dir", "executable", "required_file_0", "save_path_0", "ports"):
        assert outcomes[label] == "pass", (label, outcomes)
    selected = invoke(fixture, "check", "--name", "DEMO")
    assert selected["data"]["count"] == 1
    assert selected["data"]["profiles"][0]["name"] == "demo"
    human = run([*cli, "--home", fixture, "game", "check", "--all"], extra_env=env)
    assert not human.stderr and "demo | Demo Server | standalone | enabled=true" in human.stdout
    assert "unknown engine" not in human.stdout

    missing = variant("missing-required-files")
    for name in ("server.bin", "required.txt"):
        (missing / "servers" / "demo" / name).unlink()
    failed_checks = checks(failed(missing))
    assert failed_checks["executable"] == failed_checks["required_file_0"] == "fail"
    missing_install = variant("missing-install", install_dir='"servers/absent"')
    assert checks(failed(missing_install))["install_dir"] == "fail"

    duplicate = variant("duplicate-profile")
    duplicate_path = profile_path(duplicate)
    config = duplicate_path.read_text(encoding="utf-8")
    renamed, count = re.subn(r'^name\s*=.*$', 'name = "DEMO"', config, flags=re.MULTILINE)
    assert count == 1
    duplicate_path.with_name("second.toml").write_text(renamed, encoding="utf-8")
    listed = invoke(duplicate, "list")
    assert listed["data"]["count"] == 1 and listed["warnings"]
    assert failed(duplicate)["warnings"]

    malformed = variant("malformed-profile")
    profile_path(malformed).with_name("broken.toml").write_text(f"[{marker}\n", encoding="utf-8")
    listed = invoke(malformed, "list")
    assert listed["data"]["count"] == 1 and listed["warnings"]
    combined = json.dumps(failed(malformed)["warnings"] + listed["warnings"])
    assert marker not in combined and str(workspace) not in combined

    disabled = variant("disabled-profile", enabled="false", executable='"absent.bin"')
    report = invoke(disabled, "check", "--all")
    assert report["ok"] is True and checks(report)["executable"] == "skip"
    disabled_profile, = report["data"]["profiles"]
    assert disabled_profile["enabled"] is False
    other_platform = '"linux"' if os.name == "nt" else '"windows"'
    other = variant("other-platform", platform=other_platform, executable='"absent.bin"')
    report = invoke(other, "check", "--all")
    assert report["ok"] is True
    outcomes = checks(report)
    assert outcomes["host_platform"] == outcomes["executable"] == "skip"

    invalid = variant("invalid-ports", ports="[27015, 0, 65536, 27015]")
    assert checks(failed(invalid))["ports"] == "fail"
    expected = variant("expected-running", expect_running="true")
    report = invoke(expected, "check", "--all")
    assert report["ok"] is True
    outcomes = checks(report)
    assert outcomes["ports"] == "pass" and outcomes["listening_ports"] == "skip"

    outside = workspace / "outside-evidence"
    outside.mkdir()
    sentinel = outside / "outside-marker.txt"
    sentinel.write_text("fictional outside data\n", encoding="utf-8")
    outside_hash = digest(sentinel)
    escaped = variant("relative-escape", required_files='["../../../outside-evidence/outside-marker.txt"]')
    assert checks(failed(escaped))["required_file_0"] == "fail"
    absolute = variant("absolute-escape", required_files=json.dumps([str(sentinel)]))
    assert checks(failed(absolute))["required_file_0"] == "fail"

    linked = variant("linked-install-path", required_files='["linked/outside-marker.txt"]')
    link = linked / "servers" / "demo" / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        # The native Windows runner can make junctions without symlink privilege.
        made = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                              shell=False, capture_output=True, timeout=20)
        assert made.returncode == 0 and link.is_junction(), "Unable to create an owned test junction"
    assert checks(failed(linked))["required_file_0"] == "fail"
    assert digest(sentinel) == outside_hash

    bad = run([*cli, "--home", workspace / marker, "game", "check", "--all", "--json"],
              expected=2, extra_env=env)
    assert not bad.stdout and bad.stderr
    assert all(item not in bad.stderr for item in (marker, str(workspace), "Traceback"))
    bad_option = run([*cli, "--home", fixture, "game", "check", f"--{marker}"],
                     expected=2, extra_env=env)
    assert not bad_option.stdout and bad_option.stderr
    assert all(item not in bad_option.stderr for item in (marker, str(workspace), "Traceback"))

    audit = """
import os
from pathlib import Path
import runpy
import sys

source = Path(sys.argv[1])
sys.path.insert(0, str(source))
sys.argv = ["opskit", *sys.argv[2:]]


def verify_offline(event, args):
    if event.startswith("socket.") or event in {
        "subprocess.Popen", "os.exec", "os.system", "os.spawn", "os.posix_spawn",
        "os.startfile", "os.startfile/2", "os.kill", "ctypes.dlopen",
    }:
        raise AssertionError("Profile checker attempted live collection or execution")
    if event == "open" and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError("Profile checker opened a file for writing")
    if event in {
        "os.chmod", "os.link", "os.mkdir", "os.remove", "os.rename", "os.rmdir",
        "os.symlink", "os.truncate", "os.utime", "shutil.copyfile", "shutil.rmtree",
        "tempfile.mkdtemp", "tempfile.mkstemp",
    }:
        raise AssertionError("Profile checker attempted a filesystem mutation")


sys.addaudithook(verify_offline)
import opskit
assert Path(opskit.__file__).resolve().parent == source / "opskit"
runpy.run_module("opskit", run_name="__main__", alter_sys=True)
"""
    before_expected = tree_bytes(expected)
    audited = [sys.executable, "-I", "-B", "-W", "error", "-c", audit, source, "--home", expected, "game"]
    audited_list = valid(run([*audited, "list", "--json"]))
    assert audited_list["ok"] is True and audited_list["data"]["count"] == 1
    audited_check = valid(run([*audited, "check", "--all", "--json"]))
    assert audited_check["ok"] is True and checks(audited_check)["listening_ports"] == "skip"
    assert tree_bytes(expected) == before_expected
    assert tree_bytes(fixture) == before
    assert digest(sentinel) == outside_hash

    return [
        "fictional_install_profile_listing",
        "selected_profile_and_human_engine",
        "missing_install_and_required_paths",
        "duplicate_profile_names_case_insensitive",
        "malformed_toml_diagnostics",
        "disabled_and_platform_mismatch",
        "declared_port_validation",
        "runtime_expectation_without_live_evidence",
        "traversal_and_absolute_profile_paths_refused",
        "linked_paths_refused",
        "opaque_cli_diagnostics",
        "offline_read_only_no_install_audit_guard",
        "extracted_source_and_inputs_unchanged",
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

    def run(args, *, cwd=workspace, expected=0, extra_env=None):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env | (extra_env or {}),
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
    print('GAME_INSTALL_PROFILE_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
