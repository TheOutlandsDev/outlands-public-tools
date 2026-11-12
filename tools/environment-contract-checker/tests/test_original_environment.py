"""Fictional metadata-only prerequisite checks; no real host inventory."""

import contextlib
import copy
import io
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import hashlib
import atexit
import importlib.util
import shutil
import tempfile

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE
RUNTIME_NAMES = ("environment_check.py", "environment_windows.py", "examples/make_fixture.py")
_RUNTIME_SOURCE_BYTES = {name: (HERE / name).read_bytes() for name in RUNTIME_NAMES}
_RUNTIME_EXPECTED_SHA256 = {name: hashlib.sha256(data).hexdigest() for name, data in _RUNTIME_SOURCE_BYTES.items()}
_RUNTIME_MIRROR_ROOT = None
_RUNTIME_MIRROR_PARENT = None
RUNTIME_MIRROR_VERIFIED = False
RUNTIME_MIRROR_SHA256 = {}
RUNTIME_MIRROR_CREATION_COUNT = 0
ROOT_BINDING_EVENTS = []
ACTUAL_CLI_CASES = ("test_actual_cli_pass_and_missing_requirement_statuses", "test_actual_cli_unverified_observation_and_external_report")
REPORT_ROOT_CASE = "test_report_inside_source_or_selected_root_is_refused"


def _fixture_parent():
    parent = Path(os.environ.get("OUTLANDS_TEST_TEMP", tempfile.gettempdir()))
    if not parent.is_absolute() or not parent.is_dir() or parent.resolve(strict=True) != parent:
        raise AssertionError("FIXTURE_PARENT_MUST_BE_ABSOLUTE_ORDINARY_DIRECTORY")
    for part in (parent, *parent.parents):
        if part.is_symlink() or getattr(part.lstat(), "st_file_attributes", 0) & 0x400:
            raise AssertionError("FIXTURE_PARENT_MUST_NOT_BE_LINKED")
    return parent


def _cleanup_runtime_mirror():
    target, parent = _RUNTIME_MIRROR_ROOT, _RUNTIME_MIRROR_PARENT
    if target is None:
        return
    if (not target.is_absolute() or target.parent != parent or target == parent
            or not target.name.startswith("environment-runtime-mirror-")):
        raise AssertionError("UNEXPECTED_RUNTIME_MIRROR_CLEANUP_TARGET")
    if not target.exists():
        return
    if target.resolve(strict=True) != target or target.is_symlink() or getattr(target.lstat(), "st_file_attributes", 0) & 0x400:
        raise AssertionError("LINKED_RUNTIME_MIRROR_CLEANUP_TARGET")
    shutil.rmtree(target)


atexit.register(_cleanup_runtime_mirror)


def verify_runtime_mirror():
    """Verify three exact-byte test-only runtime files without changing ROOT."""
    global _RUNTIME_MIRROR_ROOT, _RUNTIME_MIRROR_PARENT
    global RUNTIME_MIRROR_VERIFIED, RUNTIME_MIRROR_SHA256, RUNTIME_MIRROR_CREATION_COUNT
    RUNTIME_MIRROR_VERIFIED = False
    if any((HERE / name).read_bytes() != data for name, data in _RUNTIME_SOURCE_BYTES.items()):
        raise AssertionError("ACTUAL_RUNTIME_SOURCE_CHANGED")
    if _RUNTIME_MIRROR_ROOT is None:
        parent = _fixture_parent()
        target = Path(tempfile.mkdtemp(prefix="environment-runtime-mirror-", dir=parent))
        if target.parent != parent or target.resolve(strict=True) != target:
            raise AssertionError("UNEXPECTED_RUNTIME_MIRROR_TARGET")
        _RUNTIME_MIRROR_ROOT, _RUNTIME_MIRROR_PARENT = target, parent
        directory = target / "tools/environment-contract-checker"
        directory.mkdir(parents=True)
        for name, data in _RUNTIME_SOURCE_BYTES.items():
            (directory / name).parent.mkdir(parents=True, exist_ok=True)
            with (directory / name).open("xb") as handle:
                handle.write(data)
        RUNTIME_MIRROR_CREATION_COUNT += 1
    directory = _RUNTIME_MIRROR_ROOT / "tools/environment-contract-checker"
    if any((directory / name).read_bytes() != data or (HERE / name).read_bytes() != data
           for name, data in _RUNTIME_SOURCE_BYTES.items()):
        raise AssertionError("RUNTIME_MIRROR_BYTES_CHANGED")
    RUNTIME_MIRROR_SHA256 = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in RUNTIME_NAMES}
    if RUNTIME_MIRROR_SHA256 != _RUNTIME_EXPECTED_SHA256 or RUNTIME_MIRROR_CREATION_COUNT != 1:
        raise AssertionError("RUNTIME_MIRROR_HASH_OR_COUNT_CHANGED")
    RUNTIME_MIRROR_VERIFIED = True
    return dict(RUNTIME_MIRROR_SHA256)


class StrictFixture(unittest.TestCase):
    def setUp(self):
        _fixture_parent()
        return super().setUp()

    def run(self, result=None):
        global ROOT
        verify_runtime_mirror()
        previous = ROOT
        use_mirror = self._testMethodName in ACTUAL_CLI_CASES
        ROOT = _RUNTIME_MIRROR_ROOT if use_mirror else checker.REPOSITORY
        if checker.REPOSITORY != fixture_maker.REPOSITORY:
            raise AssertionError("CORE_AND_GENERATOR_SCOPE_DIFFER")
        ROOT_BINDING_EVENTS.append(dict(test=self.id(), binding="owned_mirror" if use_mirror else "actual_repository",
                                       root_matches_repository=ROOT == checker.REPOSITORY))
        original_link, original_hardlink = Path.symlink_to, os.link
        def checked_link(path, target, target_is_directory=False):
            try:
                return original_link(path, target, target_is_directory=target_is_directory)
            except OSError as error:
                if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                        and os.environ.get("OUTLANDS_ENVIRONMENT_REQUIRE_LINKS") != "1"):
                    raise
                raise AssertionError("Required native symlink fixture creation failed") from error
        def checked_hardlink(*args, **kwargs):
            try:
                return original_hardlink(*args, **kwargs)
            except OSError as error:
                raise AssertionError("Required native hardlink fixture creation failed") from error
        try:
            with patch.object(Path, "symlink_to", new=checked_link), patch.object(os, "link", new=checked_hardlink):
                return super().run(result)
        finally:
            verify_runtime_mirror()
            ROOT = previous

    def skipTest(self, reason):
        if reason in ("Native symlink creation is unavailable", "Native directory symlink creation is unavailable", "Native hardlink creation is unavailable"):
            error = sys.exception()
            if (reason != "Native hardlink creation is unavailable" and os.name == "nt"
                    and isinstance(error, OSError) and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_ENVIRONMENT_REQUIRE_LINKS") != "1"):
                return super().skipTest(reason)
            raise AssertionError("Native link fixture creation failed") from error
        return super().skipTest(reason)


def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class Fixture(StrictFixture):
    def setUp(self):
        temp_parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(dir=temp_parent)
        def cleanup():
            target=Path(self.temporary.name).resolve()
            if target==temp_parent or not target.is_relative_to(temp_parent):raise RuntimeError('UNEXPECTED_CLEANUP_TARGET')
            self.temporary.cleanup()
        self.addCleanup(cleanup)
        self.parent=Path(self.temporary.name);self.root=self.parent/'export';self.root.mkdir()
    def write(self,name,text):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding='utf-8');return path


checker = load(
    "environment_contract_checker",
    "environment_check.py",
)
fixture_maker = load(
    "environment_contract_fictional_fixture",
    "examples/make_fixture.py",
)


ROOT = checker.REPOSITORY


def contract(*requirements):
    return {"schema_version": 1, "requirements": list(requirements)}


def requirement(identifier="fixture_file", kind="file", **fields):
    return {"id": identifier, "kind": kind, **fields}


def changed_stat(info, **values):
    fields = {
        name: getattr(info, name)
        for name in dir(info)
        if name.startswith("st_") and not callable(getattr(info, name))
    }
    fields.update(values)
    return SimpleNamespace(**fields)


def short_path_alias(path):
    import ctypes

    short_path = ctypes.windll.kernel32.GetShortPathNameW
    short_path.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint)
    short_path.restype = ctypes.c_uint
    buffer = ctypes.create_unicode_buffer(32768)
    count = short_path(str(path), buffer, len(buffer))
    if not count or count >= len(buffer):
        return None
    alias = Path(buffer.value)
    return alias if str(alias).casefold() != str(path).casefold() else None


_original_short_path_alias = short_path_alias
SHORT_NAME_OBSERVATIONS = []


def _strict_short_path_alias(path):
    alias = _original_short_path_alias(path)
    if alias is not None:
        return alias
    import ctypes
    query = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
    query.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint)
    query.restype = ctypes.c_uint
    buffer = ctypes.create_unicode_buffer(32768)
    count = query(str(path), buffer, len(buffer))
    same = bool(0 < count < len(buffer) and buffer.value.casefold() == str(path).casefold())
    SHORT_NAME_OBSERVATIONS.append(dict(api_return=count, successful_same_path=same))
    if not same:
        raise AssertionError("Native short-name discovery failed") from ctypes.WinError(ctypes.get_last_error())
    return None


short_path_alias = _strict_short_path_alias


class ContractFixture(Fixture):
    def setUp(self):
        super().setUp()
        self.program_dir = self.parent / "programs"
        self.program_dir.mkdir()

    def metadata(self, value, name="contract.json", raw=None):
        path = self.parent / name
        path.write_bytes(json.dumps(value).encode("utf-8") if raw is None else raw)
        return path

    def program(self, name="fictional-tool"):
        filename = name + ".cmd" if checker.WINDOWS else name
        path = self.program_dir / filename
        path.write_text(
            "@exit /b 97\n" if checker.WINDOWS else "#!/bin/sh\nexit 97\n",
            encoding="utf-8",
        )
        if not checker.WINDOWS:
            path.chmod(0o700)
        return path

    def one_file(self):
        path = self.write("inputs/fictional.txt", "Fictional private content canary")
        return path, contract(requirement(path="inputs/fictional.txt"))

    def by_id(self, report):
        return {item["id"]: item for item in report["checks"]}

    def invoke(self, *args):
        output = io.StringIO()
        error = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = checker.main(list(map(str, args)))
        return code, output.getvalue(), error.getvalue()


class ContractSchemaTests(ContractFixture):
    def test_exact_metadata_contract_passes_without_mutating_input(self):
        self.write("inputs/fictional.txt", "Fictional contents")
        (self.root / "workspace").mkdir()
        self.program()
        data = contract(
            requirement("document", path="inputs/fictional.txt"),
            requirement("workspace", "directory", path="workspace"),
            requirement("compiler", "program", name="fictional-tool"),
        )
        before = copy.deepcopy(data)
        result = checker.check_contract(
            data, root=self.root, program_dirs=[self.program_dir]
        )
        self.assertEqual(result["status"], "ALL_PRESENT")
        self.assertEqual([row["status"] for row in result["checks"]], ["PRESENT"] * 3)
        self.assertEqual(data, before)

    def test_top_level_contract_shape_and_schema_are_strict(self):
        for data in (
            None,
            [],
            {},
            {"schema_version": True, "requirements": []},
            {"schema_version": 2, "requirements": []},
            {"schema_version": 1, "requirements": "not-a-list"},
            {"schema_version": 1, "requirements": []},
            {"schema_version": 1, "requirements": [], "credentials": "fictional"},
        ):
            with self.subTest(data=data), self.assertRaises(checker.ContractError):
                checker.parse_contract(data)

    def test_requirement_ids_are_unique_bounded_neutral_tokens(self):
        invalid = ("", "A", "a/b", "a b", "a@b", "a\n", "-first", "x" * 41)
        for identifier in invalid:
            with (
                self.subTest(identifier=identifier),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_contract(
                    contract(requirement(identifier, path="fixture.txt"))
                )
        duplicate = requirement("same", path="fixture.txt")
        with self.assertRaises(checker.ContractError):
            checker.parse_contract(contract(duplicate, duplicate.copy()))

    def test_unknown_requirement_kinds_and_fields_are_refused(self):
        rows = (
            {"id": "sample", "kind": "command", "command": "fictional"},
            {"id": "sample", "kind": []},
            {"id": "sample", "kind": {}},
            requirement("sample", path="fixture.txt", required=True),
            requirement("sample", "program", name="fictional", arguments=[]),
            requirement("sample", "observation", value="fictional-version"),
            requirement("sample"),
        )
        for row in rows:
            with self.subTest(row=row), self.assertRaises(checker.ContractError):
                checker.parse_contract(contract(row))

    def test_path_type_traversal_canonicalization_and_reserved_names_are_refused(self):
        paths = (
            None,
            True,
            12,
            "",
            ".",
            "..",
            "../outside.txt",
            "/absolute.txt",
            "a//b",
            "a/./b",
            "a/../b",
            "a\\b",
            "a:b",
            "NUL.txt",
            "con",
            "COM1.bin",
            "ends.",
            "ends ",
            "bad\x00name",
            "e\u0301.txt",
            "x" * 241,
            "/".join(["x"] * 33),
        )
        for path in paths:
            with self.subTest(path=path), self.assertRaises(checker.ContractError):
                checker.parse_contract(contract(requirement(path=path)))

    def test_program_names_are_basenames_without_shell_or_path_syntax(self):
        for name in (
            None,
            True,
            "",
            "../tool",
            "/tool",
            "a\\tool",
            "a/tool",
            "a:tool",
            "tool name",
            "tool\n",
            "-tool",
            "x" * 65,
            "NUL.exe",
        ):
            with self.subTest(name=name), self.assertRaises(checker.ContractError):
                checker.parse_contract(
                    contract(requirement("tool", "program", name=name))
                )

    def test_requirement_count_is_bounded(self):
        data = contract(
            *(
                requirement("item_" + str(index), path="fixture.txt")
                for index in range(checker.MAX_REQUIREMENTS + 1)
            )
        )
        with self.assertRaises(checker.ContractError):
            checker.parse_contract(data)

    def test_duplicate_json_keys_nonstandard_numbers_and_non_utf8_are_refused(self):
        for raw in (
            b'{"schema_version":1,"schema_version":1,"requirements":[]}',
            b'{"number":NaN}',
            b"\xff\xfe",
        ):
            path = self.metadata({}, raw=raw)
            with (
                self.subTest(raw=raw),
                self.assertRaises((checker.ContractError, ValueError, UnicodeError)),
            ):
                checker.read_input_json(path)

    def test_metadata_input_byte_limit_is_enforced(self):
        path = self.metadata({}, raw=b" " * (checker.MAX_INPUT_BYTES + 1))
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(path)


class PresenceAndPrivacyTests(ContractFixture):
    def test_missing_target_is_missing_and_omitted_root_is_unknown(self):
        data = contract(requirement(path="absent.txt"))
        missing = checker.check_contract(data, root=self.root)
        unknown = checker.check_contract(data)
        self.assertEqual(missing["checks"][0]["status"], "MISSING")
        self.assertEqual(unknown["checks"][0]["status"], "UNKNOWN")
        self.assertEqual(missing["status"], "REVIEW_REQUIRED")

    def test_wrong_target_type_is_unknown(self):
        self.write("a-file", "fictional")
        (self.root / "a-directory").mkdir()
        data = contract(
            requirement("expected_file", path="a-directory"),
            requirement("expected_directory", "directory", path="a-file"),
        )
        result = checker.check_contract(data, root=self.root)
        self.assertEqual(
            [x["status"] for x in result["checks"]], ["UNKNOWN", "UNKNOWN"]
        )

    def test_targets_are_not_opened_and_directories_are_not_enumerated(self):
        target, data = self.one_file()
        program = self.program()
        data["requirements"].append(
            requirement("compiler", "program", name="fictional-tool")
        )
        original_open = os.open

        def guarded_open(path, *args, **kwargs):
            self.assertNotIn(
                Path(path), {target, program}, "Selected target file was opened"
            )
            return original_open(path, *args, **kwargs)

        with (
            patch.object(checker.os, "open", side_effect=guarded_open),
            patch(
                "builtins.open",
                side_effect=AssertionError("Target contents must not be read"),
            ),
            patch(
                "io.open",
                side_effect=AssertionError("Target contents must not be read"),
            ),
            patch.object(
                checker.os,
                "scandir",
                side_effect=AssertionError("No directory inventory"),
            ),
            patch.object(
                checker.os,
                "listdir",
                side_effect=AssertionError("No directory inventory"),
            ),
        ):
            result = checker.check_contract(
                data, root=self.root, program_dirs=[self.program_dir]
            )
        self.assertEqual(result["status"], "ALL_PRESENT")

    def test_no_process_network_shell_or_selected_module_execution(self):
        target = self.write(
            "never_import.py", "raise AssertionError('Selected fixture was executed')\n"
        )
        self.program()
        data = contract(
            requirement("fixture", path=target.name),
            requirement("compiler", "program", name="fictional-tool"),
        )
        with (
            patch(
                "subprocess.Popen", side_effect=AssertionError("No process")
            ) as popen,
            patch("subprocess.run", side_effect=AssertionError("No process")) as run,
            patch.object(
                socket, "socket", side_effect=AssertionError("No socket")
            ) as network,
            patch.object(os, "system", side_effect=AssertionError("No shell")) as shell,
            patch.object(os, "execv", side_effect=AssertionError("No exec")) as execute,
        ):
            report = checker.check_contract(
                data, root=self.root, program_dirs=[self.program_dir]
            )
            for operation in (popen, run, network, shell, execute):
                operation.assert_not_called()
        self.assertEqual(report["status"], "ALL_PRESENT")

    def test_default_program_discovery_does_not_search_path_or_cwd(self):
        self.program()
        data = contract(requirement("compiler", "program", name="fictional-tool"))
        previous = Path.cwd()
        try:
            os.chdir(self.program_dir)
            with patch.dict(
                os.environ, {"PATH": str(self.program_dir), "PATHEXT": ".CMD"}
            ):
                report = checker.check_contract(data)
        finally:
            os.chdir(previous)
        self.assertEqual(report["checks"][0]["status"], "UNKNOWN")

    def test_explicit_program_selection_finds_fixture_and_missing_name(self):
        self.program()
        data = contract(
            requirement("compiler", "program", name="fictional-tool"),
            requirement("missing", "program", name="fictional-absent"),
        )
        report = checker.check_contract(data, program_dirs=[self.program_dir])
        self.assertEqual(
            [x["status"] for x in report["checks"]], ["PRESENT", "MISSING"]
        )

    def test_program_directory_limit_is_enforced(self):
        data = contract(requirement("compiler", "program", name="fictional-tool"))
        with self.assertRaises(checker.ContractError):
            checker.check_contract(
                data,
                program_dirs=[
                    self.parent / ("programs_" + str(index))
                    for index in range(checker.MAX_PROGRAM_DIRS + 1)
                ],
            )

    def test_windows_program_extensions_are_fixed_and_ignore_pathext(self):
        data = contract(requirement("compiler", "program", name="fictional-tool"))
        (self.program_dir / "fictional-tool.shadow").write_text(
            "Fictional", encoding="utf-8"
        )
        with (
            patch.object(checker, "WINDOWS", True),
            patch.dict(os.environ, {"PATHEXT": ".SHADOW"}),
        ):
            result = checker.check_contract(data, program_dirs=[self.program_dir])
            self.assertEqual(result["checks"][0]["status"], "MISSING")
            (self.program_dir / "fictional-tool.cmd").write_text(
                "@exit /b 97\n", encoding="utf-8"
            )
            result = checker.check_contract(data, program_dirs=[self.program_dir])
        self.assertEqual(result["checks"][0]["status"], "PRESENT")

    @unittest.skipIf(os.name == "nt", "POSIX execute-access semantics")
    def test_posix_program_without_execute_access_is_unknown(self):
        path = self.program()
        path.chmod(0o600)
        result = checker.check_contract(
            contract(requirement("compiler", "program", name="fictional-tool")),
            program_dirs=[self.program_dir],
        )
        self.assertEqual(result["checks"][0]["status"], "UNKNOWN")

    def test_permission_error_is_not_reported_as_missing(self):
        target, data = self.one_file()
        original = Path.lstat

        def denied(path, *args, **kwargs):
            if path == target:
                raise PermissionError("Fictional private path canary")
            return original(path, *args, **kwargs)

        with patch.object(Path, "lstat", denied):
            report = checker.check_contract(data, root=self.root)
        self.assertEqual(report["checks"][0]["status"], "UNKNOWN")
        self.assertNotIn("Fictional private path canary", json.dumps(report))

    def test_observed_metadata_change_is_unknown(self):
        target, data = self.one_file()
        original = Path.lstat
        seen = 0

        def changing(path, *args, **kwargs):
            nonlocal seen
            info = original(path, *args, **kwargs)
            if path == target:
                seen += 1
                if seen > 1:
                    return changed_stat(info, st_size=info.st_size + 1)
            return info

        with patch.object(Path, "lstat", changing):
            report = checker.check_contract(data, root=self.root)
        self.assertEqual(report["checks"][0]["status"], "UNKNOWN")

    def test_windows_reparse_attribute_is_refused_without_following(self):
        target, data = self.one_file()
        original = Path.lstat

        def reparse(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            return (
                changed_stat(info, st_file_attributes=0x400) if path == target else info
            )

        with patch.object(Path, "lstat", reparse):
            report = checker.check_contract(data, root=self.root)
        self.assertEqual(report["checks"][0]["status"], "UNSAFE")

    def test_hardlink_metadata_is_refused(self):
        target, data = self.one_file()
        original = Path.lstat

        def linked(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            return changed_stat(info, st_nlink=2) if path == target else info

        with patch.object(Path, "lstat", linked):
            report = checker.check_contract(data, root=self.root)
        self.assertEqual(report["checks"][0]["status"], "UNSAFE")

    def test_native_target_symlink_is_refused(self):
        target = self.parent / "outside.txt"
        target.write_text("Fictional outside file", encoding="utf-8")
        alias = self.root / "alias.txt"
        try:
            alias.symlink_to(target)
        except OSError:
            self.skipTest("Native symlink creation is unavailable")
        report = checker.check_contract(
            contract(requirement(path=alias.name)), root=self.root
        )
        self.assertEqual(report["checks"][0]["status"], "UNSAFE")

    def test_native_ancestor_symlink_is_refused(self):
        target = self.parent / "outside"
        target.mkdir()
        (target / "file.txt").write_text("Fictional outside file", encoding="utf-8")
        alias = self.root / "alias"
        try:
            alias.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("Native directory symlink creation is unavailable")
        report = checker.check_contract(
            contract(requirement(path="alias/file.txt")), root=self.root
        )
        self.assertEqual(report["checks"][0]["status"], "UNSAFE")

    def test_native_hardlinked_target_is_refused(self):
        target, data = self.one_file()
        try:
            os.link(target, self.parent / "alias.txt")
        except OSError:
            self.skipTest("Native hardlink creation is unavailable")
        report = checker.check_contract(data, root=self.root)
        self.assertEqual(report["checks"][0]["status"], "UNSAFE")

    def test_probe_budget_exhaustion_is_unknown(self):
        self.write("one.txt", "Fictional")
        self.write("two.txt", "Fictional")
        data = contract(
            requirement("one", path="one.txt"), requirement("two", path="two.txt")
        )
        with patch.object(checker, "MAX_TARGET_PROBES", 1):
            report = checker.check_contract(data, root=self.root)
        self.assertIn("UNKNOWN", [x["status"] for x in report["checks"]])
        self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_elapsed_probe_budget_is_unknown(self):
        _, data = self.one_file()
        ticks = iter((0.0, checker.MAX_CHECK_SECONDS + 1.0))
        with patch.object(checker.time, "monotonic", side_effect=lambda: next(ticks)):
            report = checker.check_contract(data, root=self.root)
        self.assertEqual(report["checks"][0]["status"], "UNKNOWN")
        self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_special_target_node_is_unsafe_without_opening(self):
        target, data = self.one_file()
        original = Path.lstat

        def special_info(path):
            info = original(path)
            return (
                changed_stat(info, st_mode=stat.S_IFIFO | 0o600)
                if path == target
                else info
            )

        with (
            patch.object(Path, "lstat", special_info),
            patch.object(
                checker.os, "open", side_effect=AssertionError("Target opened")
            ),
        ):
            report = checker.check_contract(data, root=self.root)
        self.assertEqual(report["checks"][0]["status"], "UNSAFE")

    def test_counts_include_each_status_and_require_review(self):
        self.write("present.txt", "Fictional")
        unsafe = self.write("unsafe.txt", "Fictional")
        data = contract(
            requirement("present", path="present.txt"),
            requirement("missing", path="missing.txt"),
            requirement("manual", "observation"),
            requirement("unsafe", path="unsafe.txt"),
        )
        original = Path.lstat

        def hardlink_info(path):
            info = original(path)
            return changed_stat(info, st_nlink=2) if path == unsafe else info

        with patch.object(Path, "lstat", hardlink_info):
            report = checker.check_contract(data, root=self.root)
        self.assertEqual(
            report["counts"], {"present": 1, "missing": 1, "unknown": 1, "unsafe": 1}
        )
        self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_selected_root_must_be_existing_nonroot_ordinary_directory(self):
        target, data = self.one_file()
        for root in (target, self.parent / "absent", Path(self.root.anchor)):
            with (
                self.subTest(root_kind=root.name),
                self.assertRaises(checker.ContractError),
            ):
                checker.check_contract(data, root=root)

    def test_report_has_ids_and_fixed_metadata_without_input_values(self):
        target, data = self.one_file()
        program = self.program()
        data["requirements"].append(
            requirement("compiler", "program", name="fictional-tool")
        )
        report = checker.check_contract(
            data, root=self.root, program_dirs=[self.program_dir]
        )
        raw = json.dumps(report)
        for value in (
            str(self.parent),
            str(self.root),
            target.name,
            program.name,
            "fictional-tool",
            "Fictional private content canary",
        ):
            self.assertNotIn(value, raw)
        self.assertEqual(
            {row["id"] for row in report["checks"]}, {"fixture_file", "compiler"}
        )
        for row in report["checks"]:
            self.assertEqual(set(row), {"id", "kind", "status", "evidence"})
        self.assertIs(report["target_contents_read"], False)
        self.assertIs(report["programs_executed"], False)


class ObservationAndOutputTests(ContractFixture):
    def test_operator_assertions_remain_unknown_and_unverified(self):
        data = contract(requirement("platform_review", "observation"))
        for supplied in (True, False):
            observations = {
                "schema_version": 1,
                "observations": [{"id": "platform_review", "satisfied": supplied}],
            }
            report = checker.check_contract(data, observations=observations)
            row = report["checks"][0]
            self.assertEqual(row["status"], "UNKNOWN")
            self.assertIn("UNVERIFIED", row["evidence"])
            self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_missing_operator_assertion_is_unknown(self):
        report = checker.check_contract(
            contract(requirement("platform_review", "observation"))
        )
        self.assertEqual(report["checks"][0]["status"], "UNKNOWN")

    def test_observations_accept_only_exact_boolean_declarations(self):
        rows = [requirement("platform_review", "observation")]
        values = (
            {"schema_version": True, "observations": []},
            {"schema_version": 1, "observations": "fictional"},
            {
                "schema_version": 1,
                "observations": [{"id": "unknown", "satisfied": True}],
            },
            {
                "schema_version": 1,
                "observations": [
                    {"id": "platform_review", "satisfied": "fictional-version"}
                ],
            },
            {
                "schema_version": 1,
                "observations": [{"id": "platform_review", "satisfied": 1}],
            },
            {
                "schema_version": 1,
                "observations": [
                    {"id": "platform_review", "satisfied": True, "value": "fictional"}
                ],
            },
            {
                "schema_version": 1,
                "observations": [{"id": "platform_review", "satisfied": True}] * 2,
            },
        )
        for value in values:
            with self.subTest(value=value), self.assertRaises(checker.ContractError):
                checker.parse_observations(value, rows)

    def test_report_write_is_external_new_only_and_input_preserving(self):
        target, data = self.one_file()
        result = checker.check_contract(data, root=self.root)
        output = self.parent / "report.json"
        before = target.read_bytes()
        checker.write_report(output, result, protected_roots=[self.root])
        saved = output.read_bytes()
        self.assertEqual(json.loads(saved), result)
        with self.assertRaises((OSError, checker.ContractError)):
            checker.write_report(output, result, protected_roots=[self.root])
        self.assertEqual(output.read_bytes(), saved)
        self.assertEqual(target.read_bytes(), before)

    def test_report_inside_source_or_selected_root_is_refused(self):
        _, data = self.one_file()
        report = checker.check_contract(data, root=self.root)
        for path in (
            self.root / "must-not-write.json",
            ROOT / "environment-contract-report-must-not-exist.json",
        ):
            with self.subTest(path=path.name):
                self.assertFalse(path.exists())
                with self.assertRaises(checker.ContractError):
                    checker.write_report(path, report, protected_roots=[self.root])
                self.assertFalse(path.exists())

    def test_report_parent_alias_identity_cannot_bypass_protected_root(self):
        _, data = self.one_file()
        result = checker.check_contract(data, root=self.root)
        alias = self.parent / "alternate-spelling"
        alias.mkdir()
        nested = alias / "nested"
        nested.mkdir()
        original = Path.lstat
        protected = self.root.lstat()

        def alias_info(path):
            info = original(path)
            return (
                changed_stat(info, st_dev=protected.st_dev, st_ino=protected.st_ino)
                if path == alias
                else info
            )

        for parent in (alias, nested):
            output = parent / "must-not-write.json"
            with self.subTest(parent=parent.name):
                with (
                    patch.object(Path, "lstat", alias_info),
                    patch.object(
                        checker.os,
                        "open",
                        side_effect=AssertionError("Alias output opened"),
                    ),
                ):
                    with self.assertRaises(checker.ContractError):
                        checker.write_report(
                            output, result, protected_roots=[self.root]
                        )
                self.assertFalse(output.exists())

    @unittest.skipUnless(os.name == "nt", "Native Windows short-path alias")
    def test_native_windows_short_path_cannot_bypass_report_boundary(self):
        _, data = self.one_file()
        result = checker.check_contract(data, root=self.root)
        alias = short_path_alias(self.root)
        if alias is None:
            self.skipTest("Filesystem did not supply an alternate short spelling")
        output = alias / "short-alias-must-not-write.json"
        with self.assertRaises(checker.ContractError):
            checker.write_report(output, result, protected_roots=[self.root])
        self.assertFalse((self.root / output.name).exists())

    def test_report_parent_with_unavailable_identity_is_refused(self):
        _, data = self.one_file()
        result = checker.check_contract(data, root=self.root)
        output_parent = self.parent / "unidentified-output"
        output_parent.mkdir()
        output = output_parent / "report.json"
        original = Path.lstat

        def unidentified_info(path):
            info = original(path)
            return changed_stat(info, st_ino=0) if path == output_parent else info

        with patch.object(Path, "lstat", unidentified_info):
            with self.assertRaises(checker.ContractError):
                checker.write_report(output, result, protected_roots=[self.root])
        self.assertFalse(output.exists())

    def test_report_writer_rejects_injected_data_and_inconsistent_status(self):
        _, data = self.one_file()
        report = checker.check_contract(data, root=self.root)
        variants = []
        injected = copy.deepcopy(report)
        injected["private_value"] = "fictional-sensitive-value-canary"
        variants.append(injected)
        injected = copy.deepcopy(report)
        injected["checks"][0]["path"] = "fictional/private.txt"
        variants.append(injected)
        injected = copy.deepcopy(report)
        injected["checks"][0]["evidence"] = "fictional-sensitive-value-canary"
        variants.append(injected)
        inconsistent = copy.deepcopy(report)
        inconsistent["counts"]["present"] = True
        variants.append(inconsistent)
        inconsistent = copy.deepcopy(report)
        inconsistent["status"] = "REVIEW_REQUIRED"
        variants.append(inconsistent)
        for index, value in enumerate(variants):
            output = self.parent / ("invalid-report-" + str(index) + ".json")
            with self.subTest(index=index), self.assertRaises(checker.ContractError):
                checker.write_report(output, value, protected_roots=[self.root])
            self.assertFalse(output.exists())

    def test_missing_output_parent_is_not_created(self):
        _, data = self.one_file()
        output = self.parent / "missing-parent/report.json"
        with self.assertRaises((OSError, checker.ContractError)):
            checker.write_report(
                output,
                checker.check_contract(data, root=self.root),
                protected_roots=[self.root],
            )
        self.assertFalse(output.parent.exists())

    def test_hardlinked_input_metadata_is_rejected_before_open(self):
        source = self.metadata(contract(requirement("manual", "observation")))
        original = Path.lstat

        def hardlink_info(path):
            info = original(path)
            return changed_stat(info, st_nlink=2) if path == source else info

        with (
            patch.object(Path, "lstat", hardlink_info),
            patch.object(
                checker.os, "open", side_effect=AssertionError("Unsafe input opened")
            ),
        ):
            with self.assertRaises(checker.ContractError):
                checker.read_input_json(source)

    def test_reparse_root_and_report_parent_are_refused(self):
        _, data = self.one_file()
        report = checker.check_contract(data, root=self.root)
        output_parent = self.parent / "output"
        output_parent.mkdir()
        output = output_parent / "report.json"
        original = Path.lstat

        def mark_reparse(selected):
            def reparse_info(path):
                info = original(path)
                return (
                    changed_stat(info, st_file_attributes=0x400)
                    if path == selected
                    else info
                )

            return reparse_info

        with patch.object(Path, "lstat", mark_reparse(self.root)):
            with self.assertRaises(checker.ContractError):
                checker.check_contract(data, root=self.root)
        with patch.object(Path, "lstat", mark_reparse(output_parent)):
            with self.assertRaises(checker.ContractError):
                checker.write_report(output, report, protected_roots=[self.root])
        self.assertFalse(output.exists())

    def test_cli_controlled_errors_never_echo_paths_or_values(self):
        private_value = "fictional-sensitive-argument-canary"
        invalid = self.metadata(
            {"schema_version": 1, "requirements": [], "credentials": private_value}
        )
        for args in (
            ("--contract", invalid),
            ("--contract", self.parent / "missing-private-input.json"),
            ("--unknown", private_value),
        ):
            code, output, error = self.invoke(*args)
            self.assertEqual(code, 2)
            for value in (
                private_value,
                str(self.parent),
                "missing-private-input.json",
            ):
                self.assertNotIn(value, output + error)
            self.assertNotIn("Traceback", output + error)

    def test_static_help_and_version_do_not_reveal_source_path(self):
        for option in ("--help", "--version"):
            output = io.StringIO()
            error = io.StringIO()
            with (
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(error),
                self.assertRaises(SystemExit) as stopped,
            ):
                checker.main([option])
            self.assertEqual(stopped.exception.code, 0)
            self.assertNotIn(str(ROOT), output.getvalue() + error.getvalue())

    def test_actual_cli_pass_and_missing_requirement_statuses(self):
        target, data = self.one_file()
        input_path = self.metadata(data)
        command = [
            sys.executable,
            "-B",
            str(ROOT / "tools/environment-contract-checker/environment_check.py"),
            "--contract",
            str(input_path),
            "--root",
            str(self.root),
        ]
        process = subprocess.run(command, capture_output=True, text=True, timeout=20)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertEqual(json.loads(process.stdout)["status"], "ALL_PRESENT")
        self.assertNotIn(str(self.parent), process.stdout + process.stderr)
        target.unlink()
        process = subprocess.run(command, capture_output=True, text=True, timeout=20)
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        self.assertEqual(json.loads(process.stdout)["status"], "REVIEW_REQUIRED")

    def test_actual_cli_unverified_observation_and_external_report(self):
        target, data = self.one_file()
        data["requirements"].append(requirement("manual_review", "observation"))
        source = self.metadata(data)
        observations = self.metadata(
            {
                "schema_version": 1,
                "observations": [{"id": "manual_review", "satisfied": True}],
            },
            name="observations.json",
        )
        output = self.parent / "fictional-result.json"
        preserved = {path: path.read_bytes() for path in (target, source, observations)}
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/environment-contract-checker/environment_check.py"),
                "--contract",
                str(source),
                "--root",
                str(self.root),
                "--observations",
                str(observations),
                "--report",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        report = json.loads(process.stdout)
        self.assertEqual(report, json.loads(output.read_text(encoding="utf-8")))
        self.assertEqual(self.by_id(report)["manual_review"]["status"], "UNKNOWN")
        self.assertEqual(
            self.by_id(report)["manual_review"]["evidence"],
            "OPERATOR_REPORTED_TRUE_UNVERIFIED",
        )
        self.assertNotIn(str(self.parent), process.stdout + process.stderr)
        self.assertIs(report["versions_verified"], False)
        for path, before in preserved.items():
            self.assertEqual(path.read_bytes(), before)


class FictionalFixtureGeneratorTests(Fixture):
    def test_new_external_fixture_contains_only_declared_fictional_files(self):
        destination = self.parent / "fictional-generated"
        with (
            patch("subprocess.Popen", side_effect=AssertionError("No process")),
            patch("subprocess.run", side_effect=AssertionError("No process")),
            patch.object(socket, "socket", side_effect=AssertionError("No socket")),
            patch.object(os, "system", side_effect=AssertionError("No shell")),
            patch.object(os, "execv", side_effect=AssertionError("No execution")),
        ):
            result = fixture_maker.create_fixture(destination)
        program = "fictional-tool.cmd" if os.name == "nt" else "fictional-tool"
        self.assertEqual(
            {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
            },
            {
                "inputs",
                "programs",
                "workspace",
                "inputs/fictional.txt",
                "programs/" + program,
            },
        )
        self.assertEqual(
            (destination / "inputs/fictional.txt").read_bytes(),
            b"Fictional prerequisite input. No user records.\n",
        )
        program_bytes = (destination / "programs" / program).read_bytes()
        self.assertIn(b"Fictional presence fixture; do not execute.", program_bytes)
        self.assertEqual(
            result,
            {
                "status": "CREATED",
                "files_created": 2,
                "child_directories_created": 3,
                "fixture_executed": False,
            },
        )
        self.assertNotIn(str(self.parent), json.dumps(result))
        report = checker.check_contract(
            contract(
                requirement("input", path="inputs/fictional.txt"),
                requirement("workspace", "directory", path="workspace"),
                requirement("program", "program", name="fictional-tool"),
            ),
            root=destination,
            program_dirs=[destination / "programs"],
        )
        self.assertEqual(report["status"], "ALL_PRESENT")

    def test_existing_destination_is_not_overwritten_or_extended(self):
        destination = self.parent / "fictional-existing"
        destination.mkdir()
        marker = destination / "preserved.txt"
        marker.write_bytes(b"Fictional preserved bytes\n")
        with self.assertRaises((OSError, fixture_maker.FixtureError)):
            fixture_maker.create_fixture(destination)
        self.assertEqual(marker.read_bytes(), b"Fictional preserved bytes\n")
        self.assertEqual({path.name for path in destination.iterdir()}, {marker.name})

    def test_repository_parent_is_refused_before_creating_destination(self):
        destination = ROOT / "environment-fixture-must-not-create"
        self.assertFalse(destination.exists())
        with patch.object(
            Path, "mkdir", side_effect=AssertionError("Repository write")
        ):
            with self.assertRaises(fixture_maker.FixtureError):
                fixture_maker.create_fixture(destination)
        self.assertFalse(destination.exists())

    def test_repository_alias_parent_is_refused_before_creating_destination(self):
        alias = self.parent / "repository-alias"
        alias.mkdir()
        nested = alias / "nested"
        nested.mkdir()
        protected = ROOT.lstat()
        original = Path.lstat

        def alias_info(path):
            info = original(path)
            return (
                changed_stat(info, st_dev=protected.st_dev, st_ino=protected.st_ino)
                if path == alias
                else info
            )

        for parent in (alias, nested):
            destination = parent / "must-not-create"
            with self.subTest(parent=parent.name):
                with (
                    patch.object(Path, "lstat", alias_info),
                    patch.object(
                        Path, "mkdir", side_effect=AssertionError("Alias write")
                    ),
                ):
                    with self.assertRaises(fixture_maker.FixtureError):
                        fixture_maker.create_fixture(destination)
                self.assertFalse(destination.exists())

    @unittest.skipUnless(os.name == "nt", "Native Windows short-path alias")
    def test_native_windows_repository_alias_is_refused_before_creation(self):
        alias = short_path_alias(ROOT)
        if alias is None:
            self.skipTest("Filesystem did not supply an alternate short spelling")
        destination = alias / "short-alias-fixture-must-not-create"
        with patch.object(Path, "mkdir", side_effect=AssertionError("Alias write")):
            with self.assertRaises(fixture_maker.FixtureError):
                fixture_maker.create_fixture(destination)
        self.assertFalse((ROOT / destination.name).exists())

    def test_unavailable_parent_identity_is_refused_before_creation(self):
        destination = self.parent / "unknown-identity-fixture"
        original = Path.lstat

        def unidentified_info(path):
            info = original(path)
            return changed_stat(info, st_ino=0) if path == self.parent else info

        with (
            patch.object(Path, "lstat", unidentified_info),
            patch.object(
                Path, "mkdir", side_effect=AssertionError("Unverified boundary write")
            ),
        ):
            with self.assertRaises(fixture_maker.FixtureError):
                fixture_maker.create_fixture(destination)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
