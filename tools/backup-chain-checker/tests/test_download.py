"""Actual copied-script consumers of authored graph declarations, never backups."""

import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
FLAGS = dict.fromkeys(("filesystem_scanned", "backup_contents_read", "metadata_verified", "restore_performed",
                      "deletion_performed", "deletion_authorized", "commands_generated", "network_probed"), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def node(identifier="sample_full", *, parent=None, sequence=0, series="sample_series", kind=None):
    return dict(id=identifier, series_id=series, kind=kind or ("full" if parent is None else "incremental"),
                parent_id=parent, sequence=sequence)


def valid_nodes():
    return [node(), node("sample_first", parent="sample_full", sequence=1),
            node("sample_second", parent="sample_first", sequence=2)]


def plan(rows=None, *, target="sample_second"):
    return dict(schema_version=1, restore_point_id=target, snapshots=valid_nodes() if rows is None else rows)


def golden(rows, *, target="sample_second", series=1, cycles=0, target_issues=(), order=()):
    problems = sum(bool(issues) for identifier, issues in rows)
    return dict(schema_version=1, status="REVIEW_REQUIRED" if problems or target_issues else "DECLARED_CHAIN_CONSISTENT",
                scope="DECLARED_FULL_INCREMENTAL_METADATA_ONLY", **FLAGS,
                counts=dict(snapshots=len(rows), series=series, snapshots_with_issues=problems, cycle_members=cycles),
                snapshots=[dict(id=identifier, issues=issues) for identifier, issues in sorted(rows)],
                target=dict(id=target, status="REVIEW_REQUIRED" if target_issues else "DECLARED_CHAIN_CONSISTENT",
                            issues=list(target_issues), declared_order=list(order)))


def default_result():
    return golden([(row["id"], []) for row in valid_nodes()], order=["sample_full", "sample_first", "sample_second"])


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="chain-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied single script"
        self.runtime.mkdir()
        self.source = self.runtime / "chain_check.py"
        self.source.write_bytes((ROOT / "chain_check.py").read_bytes())
        self.runtime_hash = sha(self.source.read_bytes())
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def fixture(self, value=None, *, raw=None):
        self.serial += 1
        path = self.work / ("FICTIONAL_PRIVATE_PLAN_" + str(self.serial) + ".json")
        path.write_bytes(json.dumps(plan() if value is None else value).encode("utf-8") if raw is None else raw)
        return path

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import chain_check as tool\nevents = []\n" + textwrap.dedent(body)
                          + "\nstatus = tool.main(sys.argv[1:])\n" + textwrap.dedent(postlude)
                          + "\nraise SystemExit(status)\n", encoding="utf-8", newline="\n")
        return script

    def process(self, *arguments, expected=0, code=None, script=None, json_output=True):
        tree = {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")}
        retained = {}
        for path in self.work.rglob("*"):
            if not path.is_symlink() and not path.is_junction():
                info = path.lstat()
                if stat.S_ISREG(info.st_mode):
                    retained[path] = (sha(path.read_bytes()), info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink)
        done = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8", str(script or self.source), *map(str, arguments)],
                              cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60)
        self.assertEqual(done.returncode, expected, done.stdout[:2000] + done.stderr)
        self.assertEqual(done.stderr, "")
        self.assertEqual(tree, {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")})
        for path, before in retained.items():
            info = path.lstat()
            self.assertEqual((sha(path.read_bytes()), info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink), before)
        self.assertEqual(list(self.runtime.iterdir()), [self.source])
        self.assertEqual(sha(self.source.read_bytes()), self.runtime_hash)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
        self.assertNotIn(str(self.work), done.stdout.replace("\\\\", "\\"))
        self.assertNotIn("FICTIONAL_PRIVATE", done.stdout)
        if not json_output:
            return done.stdout
        self.assertEqual(len(done.stdout.splitlines()), 1)
        value = json.loads(done.stdout)
        if expected in (2, 130):
            self.assertEqual(value, dict(status="ERROR", code=code or "INTERRUPTED", **FLAGS))
        else:
            self.assertEqual(set(value), {"schema_version", "status", "scope", "counts", "snapshots", "target", *FLAGS})
            self.assertTrue(all(value[key] is False for key in FLAGS))
            for row in value["snapshots"]:
                self.assertEqual(set(row), {"id", "issues"})
            self.assertEqual(set(value["target"]), {"id", "status", "issues", "declared_order"})
        return value

    def run_cli(self, source=None, **options):
        return self.process("--plan", source or self.fixture(), **options)

    def check(self, value, wanted, *, raw=None, script=None):
        self.assertEqual(self.run_cli(self.fixture(value, raw=raw), expected=int(wanted["status"] == "REVIEW_REQUIRED"), script=script), wanted)
        return wanted

    def symlink(self, path, target):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_CHAIN_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_valid_full_and_incremental_chain_has_exact_result(self):
        self.check(plan(), default_result())
        self.assertEqual({path.name for path in self.work.iterdir()}, {self.runtime.name, "FICTIONAL_PRIVATE_PLAN_1.json"})

    def test_branches_gaps_multiple_full_roots_and_series_keep_only_selected_ancestry(self):
        rows = [node("root_a", sequence=10), node("root_b", sequence=100), node("branch_a", parent="root_a", sequence=40),
                node("branch_b", parent="root_a", sequence=50), node("other_root", series="other_series")]
        self.check(plan(rows, target="branch_b"), golden([(row["id"], []) for row in rows], target="branch_b", series=2,
                   order=["root_a", "branch_b"]))

    def test_missing_parent_null_incremental_and_bad_full_parent_have_fixed_local_issues(self):
        cases = [(node("sample", parent="absent", sequence=1), ["PARENT_NOT_FOUND"]),
                 (node("sample", kind="incremental"), ["INCREMENTAL_PARENT_NOT_SUPPLIED"]),
                 (node("sample", kind="full", parent="absent"), ["FULL_PARENT_NOT_NULL", "PARENT_NOT_FOUND"])]
        for declaration, issues in cases:
            self.check(plan([declaration], target="sample"), golden([("sample", issues)], target="sample", target_issues=["TARGET_CHAIN_BLOCKED"]))

    def test_cross_series_non_earlier_parents_and_sequence_reuse_are_ordered(self):
        self.check(plan([node("root"), node("child", parent="root", sequence=1, series="other_series")], target="child"),
                   golden([("root", []), ("child", ["PARENT_SERIES_MISMATCH"])], target="child", series=2, target_issues=["TARGET_CHAIN_BLOCKED"]))
        self.check(plan([node("root", sequence=3), node("child", parent="root", sequence=3)], target="child"),
                   golden([("root", ["SEQUENCE_REUSED_IN_SERIES"]), ("child", ["PARENT_SEQUENCE_NOT_EARLIER", "SEQUENCE_REUSED_IN_SERIES"])],
                          target="child", target_issues=["TARGET_CHAIN_BLOCKED"]))
        self.check(plan([node("root", sequence=5), node("child", parent="root", sequence=2)], target="child"),
                   golden([("root", []), ("child", ["PARENT_SEQUENCE_NOT_EARLIER"])], target="child", target_issues=["TARGET_CHAIN_BLOCKED"]))

    def test_self_reference_and_full_parent_cycles_report_all_fixed_issues(self):
        for kind, leading in (("full", ["FULL_PARENT_NOT_NULL"]), ("incremental", [])):
            self.check(plan([node("sample", kind=kind, parent="sample")], target="sample"),
                       golden([("sample", leading + ["PARENT_SELF_REFERENCE", "PARENT_SEQUENCE_NOT_EARLIER", "DEPENDENCY_CYCLE"])],
                              target="sample", cycles=1, target_issues=["TARGET_CHAIN_BLOCKED"]))
        self.check(plan([node("a", parent="b", kind="full"), node("b", parent="a", sequence=1)], target="b"),
                   golden([("a", ["FULL_PARENT_NOT_NULL", "PARENT_SEQUENCE_NOT_EARLIER", "DEPENDENCY_CYCLE"]), ("b", ["DEPENDENCY_CYCLE"])],
                          target="b", cycles=2, target_issues=["TARGET_CHAIN_BLOCKED"]))

    def test_cycle_members_exclude_descendants_but_block_their_ancestry(self):
        rows = [node("a", parent="b", sequence=1), node("b", parent="a", sequence=2),
                node("tail", parent="b", sequence=3), node("c", parent="c", sequence=4)]
        self.check(plan(rows, target="tail"), golden([("a", ["PARENT_SEQUENCE_NOT_EARLIER", "DEPENDENCY_CYCLE"]),
                   ("b", ["DEPENDENCY_CYCLE"]), ("tail", []), ("c", ["PARENT_SELF_REFERENCE", "PARENT_SEQUENCE_NOT_EARLIER", "DEPENDENCY_CYCLE"])],
                   target="tail", cycles=3, target_issues=["TARGET_CHAIN_BLOCKED"]))

    def test_unrelated_bad_branch_requires_review_without_erasing_clean_target_order(self):
        rows = valid_nodes() + [node("other_child", parent="other_missing", sequence=1, series="other_series")]
        self.check(plan(rows), golden([(row["id"], []) for row in valid_nodes()] + [("other_child", ["PARENT_NOT_FOUND"])],
                   series=2, order=["sample_full", "sample_first", "sample_second"]))

    def test_missing_target_and_bad_ancestor_never_return_partial_order(self):
        self.check(plan(target="absent"), golden([(row["id"], []) for row in valid_nodes()], target="absent", target_issues=["RESTORE_POINT_NOT_FOUND"]))
        self.check(plan([node("base", kind="incremental"), node("child", parent="base", sequence=1)], target="child"),
                   golden([("base", ["INCREMENTAL_PARENT_NOT_SUPPLIED"]), ("child", [])], target="child", target_issues=["TARGET_CHAIN_BLOCKED"]))

    def test_seeded_reachability_oracle_and_permutation_preserve_graph_results(self):
        selected = random.Random(15043)
        names = ["sample_a", "sample_b", "sample_c", "sample_d"]
        for iteration in range(8):
            rows = [node(name, parent=selected.choice([None] + names), sequence=selected.randrange(5),
                         series=selected.choice(("series_a", "series_b")), kind=selected.choice(("full", "incremental"))) for name in names]
            target = selected.choice(names + ["absent"])
            by_name = {row["id"]: row for row in rows}
            reach = {(left, right): by_name[left]["parent_id"] == right for left in names for right in names}
            # Independent transitive closure, not the runtime's parent-walk cycle search.
            for middle in names:
                for left in names:
                    for right in names:
                        reach[left, right] = reach[left, right] or (reach[left, middle] and reach[middle, right])
            cycles = {name for name in names if reach[name, name]}
            local = {}
            for row in rows:
                issues, parent = [], by_name.get(row["parent_id"])
                if row["kind"] == "full" and row["parent_id"] is not None:
                    issues.append("FULL_PARENT_NOT_NULL")
                if row["kind"] == "incremental" and row["parent_id"] is None:
                    issues.append("INCREMENTAL_PARENT_NOT_SUPPLIED")
                if row["parent_id"] is not None:
                    if parent is None:
                        issues.append("PARENT_NOT_FOUND")
                    else:
                        if parent["id"] == row["id"]:
                            issues.append("PARENT_SELF_REFERENCE")
                        if parent["series_id"] != row["series_id"]:
                            issues.append("PARENT_SERIES_MISMATCH")
                        if parent["sequence"] >= row["sequence"]:
                            issues.append("PARENT_SEQUENCE_NOT_EARLIER")
                if sum(other["series_id"] == row["series_id"] and other["sequence"] == row["sequence"] for other in rows) > 1:
                    issues.append("SEQUENCE_REUSED_IN_SERIES")
                if row["id"] in cycles:
                    issues.append("DEPENDENCY_CYCLE")
                local[row["id"]] = issues
            if target not in by_name:
                target_issues, order = ["RESTORE_POINT_NOT_FOUND"], []
            else:
                required = {target} | {name for name in names if reach[target, name]}
                target_issues = ["TARGET_CHAIN_BLOCKED"] if any(local[name] for name in required) else []
                # Valid single-parent ancestry is strictly sequence-ordered.
                order = [] if target_issues else sorted(required, key=lambda name: by_name[name]["sequence"])
            wanted = golden(list(local.items()), target=target, series=len({row["series_id"] for row in rows}),
                            cycles=len(cycles), target_issues=target_issues, order=order)
            for declarations in (rows, selected.sample(rows, len(rows))):
                self.check(plan(declarations, target=target), wanted)

    def test_root_and_snapshot_fields_are_exact_without_private_backup_fields(self):
        for value in (None, [], {}, dict(plan(), schema_version=True), dict(plan(), schema_version=1.0),
                      dict(plan(), schema_version="1"), dict(plan(), backup_path="FICTIONAL_PRIVATE_PATH")):
            self.run_cli(self.fixture(raw=json.dumps(value).encode()), expected=2, code="PLAN_SCHEMA_INVALID")
        for row in ({}, dict(node(), command="FICTIONAL_PRIVATE_COMMAND"), dict(node(), hashes=[])):
            self.run_cli(self.fixture(plan([row])), expected=2, code="SNAPSHOT_SCHEMA_INVALID")
        for kind in (None, "differential", "multi_parent", []):
            row = dict(node(), kind=kind)
            self.run_cli(self.fixture(plan([row])), expected=2, code="SNAPSHOT_KIND_INVALID")

    def test_identifiers_series_parent_and_duplicate_ids_are_strict(self):
        for field, code in (("id", "SNAPSHOT_ID_INVALID"), ("series_id", "SERIES_ID_INVALID"), ("parent_id", "PARENT_ID_INVALID")):
            for value in ("Upper", "has space", "1first", "é", "a"*41, 1, True, []):
                self.run_cli(self.fixture(plan([dict(node(), **{field: value})])), expected=2, code=code)
        for target in (None, "Upper", "a"*41):
            self.run_cli(self.fixture(plan(target=target)), expected=2, code="RESTORE_POINT_ID_INVALID")
        for identifier in ("a", "a"*40):
            self.check(plan([node(identifier)], target=identifier), golden([(identifier, [])], target=identifier, order=[identifier]))
        self.run_cli(self.fixture(plan([node(), node(sequence=1)])), expected=2, code="DUPLICATE_SNAPSHOT_ID")

    def test_sequence_requires_integer_with_inclusive_million_bound(self):
        for value in (True, False, 1.0, "1", -1, 1000001, None):
            self.run_cli(self.fixture(plan([node(sequence=value)])), expected=2, code="SEQUENCE_INVALID")
        rows = [node("minimum", sequence=0), node("maximum", sequence=1000000)]
        self.check(plan(rows, target="maximum"), golden([("minimum", []), ("maximum", [])], target="maximum", order=["maximum"]))

    def test_maximum_256_node_chain_and_one_extra_snapshot_are_bounded(self):
        names = ["sample_" + str(index).zfill(3) for index in range(256)]
        rows = [node(name, parent=None if index == 0 else names[index-1], sequence=index) for index, name in enumerate(names)]
        self.check(plan(rows, target=names[-1]), golden([(name, []) for name in names], target=names[-1], order=names))
        for declarations in ([], rows + [node("extra", sequence=256)]):
            self.run_cli(self.fixture(plan(declarations)), expected=2, code="PLAN_SCHEMA_INVALID")

    def test_input_64_kib_exact_bom_and_extra_byte(self):
        raw = b"\xef\xbb\xbf" + json.dumps(plan()).encode()
        exact = raw + b" "*(65536-len(raw))
        self.check(plan(), default_result(), raw=exact)
        self.run_cli(self.fixture(raw=exact+b" "), expected=2, code="INPUT_SIZE_LIMIT")

    def test_duplicate_json_keys_constants_encoding_and_malformed_data_are_fixed(self):
        raw = json.dumps(plan()).encode()
        for duplicate in (raw[:-1]+b',"restore_point_id":"again"}', raw.replace(b'"sequence": 0', b'"sequence":0,"sequence":0')):
            self.run_cli(self.fixture(raw=duplicate), expected=2, code="DUPLICATE_JSON_KEY")
        for constant in (b"NaN", b"Infinity", b"-Infinity"):
            self.run_cli(self.fixture(raw=raw.replace(b'"sequence": 0', b'"sequence":'+constant)), expected=2, code="NONSTANDARD_JSON")
        for value in (b"\xff", b"{", b"", b"{} {}"):
            self.run_cli(self.fixture(raw=value), expected=2, code="INPUT_OR_PLAN_FAILED")

    def test_help_version_arguments_and_original_path_spellings_have_fixed_errors(self):
        self.assertIn("--plan", self.process("--help", json_output=False))
        self.assertEqual(self.process("--version", json_output=False), "backup-chain-checker 0.1.0\n")
        for args in ((), ("--plan",), ("--pl", "FICTIONAL_PRIVATE_ARGUMENT"), ("--unknown", "FICTIONAL_PRIVATE_ARGUMENT")):
            self.process(*args, expected=2, code="ARGUMENTS_INVALID")
        self.run_cli(self.work / "FICTIONAL_PRIVATE_MISSING.json", expected=2, code="INPUT_OR_PLAN_FAILED")
        self.run_cli(self.runtime, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        for path in (self.work / "CON.json", self.work / "file:stream", self.work / ".." / "escape.json"):
            self.run_cli(path, expected=2, code="INPUT_PATH_INVALID")
        source = self.fixture()
        for spelling in (str(source)+".", str(source)+" "):
            self.run_cli(spelling, expected=2, code="INPUT_PATH_INVALID")
        self.assertEqual(self.run_cli(source.name), default_result())

    def test_only_selected_control_is_read_without_backup_clock_network_or_commands(self):
        source = self.fixture()
        (self.work / "fictional-backup.bin").write_bytes(b"FICTIONAL_PRIVATE_BACKUP_BODY_NEVER_READ")
        (self.work / "prior-capture.txt").write_bytes(b"Fictional prior capture must remain unchanged\n")
        script = self.wrapper("""
            selected = Path(INPUT_VALUE)
            original = os.open
            def opened(path, *args, **kwargs):
                assert Path(path) == selected, 'Unselected backup or file opened'
                events.append(True)
                return original(path, *args, **kwargs)
            def forbidden(*args, **kwargs):
                raise AssertionError('Clock, network, command or storage enumeration attempted')
            class NoClock(datetime.datetime):
                now = staticmethod(forbidden)
                utcnow = staticmethod(forbidden)
                today = staticmethod(forbidden)
            datetime.datetime = NoClock
            time.time = forbidden
            os.open = opened
            os.scandir = forbidden
            os.listdir = forbidden
            Path.open = forbidden
            socket.socket = forbidden
            socket.create_connection = forbidden
            urllib.request.urlopen = forbidden
            subprocess.Popen = forbidden
            runpy.run_path = forbidden
            os.system = forbidden
            """.replace("INPUT_VALUE", repr(str(source))), prelude="import datetime, time, socket, urllib.request, subprocess, runpy\n",
                              postlude="assert events == [True] and status == 0\n")
        self.assertEqual(self.run_cli(source, script=script), default_result())

    def test_native_hardlinked_plan_is_refused_and_target_preserved(self):
        source = self.fixture()
        alias = self.work / "owned-hardlink.json"
        os.link(source, alias)
        self.assertGreaterEqual(source.stat().st_nlink, 2)
        self.run_cli(source, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    def test_controlled_interrupt_and_short_read_release_input_handle(self):
        source = self.fixture()
        for mode in ("interrupt", "short"):
            script = self.wrapper("""
                original = os.fdopen
                descriptors = []
                class Controlled:
                    def __init__(self, stream):
                        self.stream = stream
                    def __enter__(self):
                        self.stream.__enter__()
                        return self
                    def __exit__(self, *args):
                        return self.stream.__exit__(*args)
                    def fileno(self):
                        return self.stream.fileno()
                    def read(self, maximum):
                        events.append(True)
                        if MODE == 'interrupt':
                            raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT')
                        return self.stream.read(maximum)[:-1]
                def opened(fd, *args, **kwargs):
                    descriptors.append(fd)
                    return Controlled(original(fd, *args, **kwargs))
                os.fdopen = opened
                """.replace("MODE", repr(mode)), postlude="""
                assert events == [True]
                for fd in descriptors:
                    try:
                        os.fstat(fd)
                    except OSError as error:
                        assert error.errno == 9
                    else:
                        raise AssertionError('Owned descriptor remained open')
                """)
            self.run_cli(source, script=script, expected=130 if mode == "interrupt" else 2,
                         code=None if mode == "interrupt" else "INPUT_CHANGED")

    def test_observed_identity_change_and_native_read_error_are_fixed(self):
        source = self.fixture()
        script = self.wrapper("""
            original = tool._snapshot
            def changed(path):
                events.append(True)
                ancestors, leaf = original(path)
                return (ancestors+('controlled observed change',), leaf) if len(events) == 2 else (ancestors, leaf)
            tool._snapshot = changed
            """, postlude="assert events == [True, True] and status == 2\n")
        self.run_cli(source, script=script, expected=2, code="INPUT_CHANGED")
        script = self.wrapper("""
            def denied(*args, **kwargs):
                events.append(True)
                raise OSError('FICTIONAL_PRIVATE_NATIVE_IO_DETAIL')
            os.open = denied
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(source, script=script, expected=2, code="INPUT_OR_PLAN_FAILED")

    def test_native_symlink_plan_leaf_and_dangling_are_refused(self):
        source = self.fixture()
        alias = self.work / "linked-plan.json"
        self.symlink(alias, source)
        self.run_cli(alias, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        absent = self.work / "owned-absent-target.json"
        dangling = self.work / "dangling-plan.json"
        self.symlink(dangling, absent)
        self.run_cli(dangling, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        self.assertFalse(absent.exists())

    def test_native_symlink_plan_parent_is_refused(self):
        source = self.fixture()
        target = self.work / "owned-plan-parent"
        target.mkdir()
        moved = target / "plan.json"
        source.rename(moved)
        alias = self.work / "linked-parent"
        self.symlink(alias, target)
        self.run_cli(alias / "plan.json", expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_plan_parent_is_refused(self):
        source = self.fixture()
        target = self.work / "owned-plan-parent"
        target.mkdir()
        moved = target / "plan.json"
        source.rename(moved)
        alias = self.work / "junction-parent"
        self.junction(alias, target)
        self.run_cli(alias / "plan.json", expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows alternate stream fixture")
    def test_native_windows_named_stream_and_original_suffix_aliases_are_refused(self):
        source = self.fixture()
        stream = str(source)+":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b"FICTIONAL_PRIVATE_NAMED_STREAM")
        self.assertEqual(self.run_cli(source), default_result())
        self.run_cli(stream, expected=2, code="INPUT_PATH_INVALID")
        for suffix in (".", " "):
            self.run_cli(str(source)+suffix, expected=2, code="INPUT_PATH_INVALID")
            self.run_cli(str(source.parent)+suffix+os.sep+source.name, expected=2, code="INPUT_PATH_INVALID")
        with open(stream, "rb") as handle:
            self.assertEqual(handle.read(), b"FICTIONAL_PRIVATE_NAMED_STREAM")

    @unittest.skipUnless(os.name == "nt", "Native Windows held writer fixture")
    def test_native_windows_exclusive_writer_causes_open_refusal_then_release(self):
        source = self.fixture()
        script = self.wrapper("""
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                          wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            held = kernel.CreateFileW(INPUT_VALUE, 0x40000000, 0, None, 3, 0x80, None)
            if held == ctypes.c_void_p(-1).value:
                raise AssertionError('Native held writer fixture creation failed') from ctypes.WinError(ctypes.get_last_error())
            events.append(True)
            """.replace("INPUT_VALUE", repr(str(source))),
                              postlude="assert kernel.CloseHandle(held)\nassert events == [True] and status == 2\n")
        self.run_cli(source, script=script, expected=2, code="INPUT_OR_PLAN_FAILED")
        self.assertEqual(self.run_cli(source), default_result())

    @unittest.skipUnless(os.name != "nt", "Native POSIX FIFO fixture")
    def test_native_posix_fifo_plan_is_refused_before_open(self):
        fifo = self.work / "owned-fifo.json"
        os.mkfifo(fifo, 0o600)
        self.run_cli(fifo, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    def junction(self, link, target):
        from ctypes import wintypes

        self.assertTrue(link.is_relative_to(self.work) and target.is_relative_to(self.work))
        link.mkdir()
        self.addCleanup(link.rmdir)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                                          wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                          ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        kernel.DeviceIoControl.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        substitute = ("\\??\\"+str(target)).encode("utf-16-le")
        printable = str(target).encode("utf-16-le")
        payload = substitute+b"\x00\x00"+printable+b"\x00\x00"
        data = struct.pack("<LHHHHHH", 0xA0000003, 8+len(payload), 0,
                           0, len(substitute), len(substitute)+2, len(printable))+payload
        held = kernel.CreateFileW(str(link), 0x40000000, 0, None, 3, 0x02200000, None)
        if held == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            buffer = ctypes.create_string_buffer(data)
            returned = wintypes.DWORD()
            if not kernel.DeviceIoControl(held, 0x000900A4, buffer, len(data), None, 0,
                                          ctypes.byref(returned), None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(held)
        self.assertTrue(link.is_junction())


if __name__ == "__main__":
    unittest.main()
