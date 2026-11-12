"""Actual copied-script consumers of authored workflow declarations, never task execution."""

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
FLAGS = dict.fromkeys(("filesystem_scanned", "states_verified", "execution_performed", "execution_authorized",
                      "commands_generated", "plan_changed", "network_probed"), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def task(identifier="sample_prepare", requires=(), state="pending"):
    return dict(id=identifier, requires=list(requires), state=state)


def valid_tasks():
    return [task("sample_prepare", state="completed"), task("sample_check", ["sample_prepare"]),
            task("sample_package", ["sample_check", "sample_prepare"])]


def plan(rows=None):
    return dict(schema_version=1, tasks=valid_tasks() if rows is None else rows)


def golden(rows, *, edges, pending, active, completed, cycles=0, order=(), eligible=(), waiting=()):
    problems = sum(bool(issues) for identifier, issues in rows)
    return dict(schema_version=1, status="REVIEW_REQUIRED" if problems else "DECLARED_PLAN_CONSISTENT",
                scope="DECLARED_TASK_DEPENDENCIES_AND_STATES_ONLY", **FLAGS,
                counts=dict(tasks=len(rows), dependency_edges=edges, pending=pending, in_progress=active,
                            completed=completed, tasks_with_issues=problems, cycle_members=cycles),
                tasks=[dict(id=identifier, issues=issues) for identifier, issues in sorted(rows)],
                declared_order=list(order), eligible_next_ids=list(eligible), waiting_ids=list(waiting))


def default_result():
    return golden([(row["id"], []) for row in valid_tasks()], edges=3, pending=2, active=0, completed=1,
                  order=["sample_prepare", "sample_check", "sample_package"], eligible=["sample_check"], waiting=["sample_package"])


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied single script"
        self.runtime.mkdir()
        self.source = self.runtime / "workflow_check.py"
        self.source.write_bytes((ROOT / "workflow_check.py").read_bytes())
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
                          + "import workflow_check as tool\nevents = []\n" + textwrap.dedent(body)
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
            self.assertEqual(set(value), {"schema_version", "status", "scope", "counts", "tasks", "declared_order", "eligible_next_ids", "waiting_ids", *FLAGS})
            self.assertTrue(all(value[key] is False for key in FLAGS))
            for row in value["tasks"]:
                self.assertEqual(set(row), {"id", "issues"})
            if expected == 1:
                self.assertEqual([value[key] for key in ("declared_order", "eligible_next_ids", "waiting_ids")], [[], [], []])
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
                    and os.environ.get("OUTLANDS_WORKFLOW_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_valid_plan_has_exact_order_eligibility_and_waiting(self):
        self.check(plan(), default_result())
        self.assertEqual({path.name for path in self.work.iterdir()}, {self.runtime.name, "FICTIONAL_PRIVATE_PLAN_1.json"})

    def test_multiple_prerequisites_all_must_be_declared_completed(self):
        for state in ("completed", "pending"):
            rows = [task("root_a", state="completed"), task("root_b", state=state), task("join", ["root_a", "root_b"])]
            self.check(plan(rows), golden([(row["id"], []) for row in rows], edges=2,
                       pending=1 if state == "completed" else 2, active=0, completed=2 if state == "completed" else 1,
                       order=["root_a", "root_b", "join"], eligible=["join"] if state == "completed" else ["root_b"],
                       waiting=[] if state == "completed" else ["join"]))

    def test_completed_and_in_progress_tasks_are_never_eligible_again(self):
        rows = [task("a", state="completed"), task("b", ["a"], "in_progress"), task("c", ["a"], "completed"),
                task("d", ["a"]), task("e", ["b"])]
        self.check(plan(rows), golden([(row["id"], []) for row in rows], edges=4, pending=2, active=1, completed=2,
                   order=["a", "b", "c", "d", "e"], eligible=["d"], waiting=["e"]))
        self.check(plan([task("a", state="completed"), task("b", ["a"], "completed")]),
                   golden([("a", []), ("b", [])], edges=1, pending=0, active=0, completed=2, order=["a", "b"]))

    def test_invalid_completed_and_active_claims_withhold_every_list(self):
        rows = [task("a"), task("b", ["a"], "completed"), task("c", ["a"], "in_progress"), task("d")]
        self.check(plan(rows), golden([("a", []), ("b", ["COMPLETED_PREREQUISITES_UNSATISFIED"]),
                   ("c", ["ACTIVE_PREREQUISITES_UNSATISFIED"]), ("d", [])], edges=2, pending=2, active=1, completed=1))
        for state, code in (("completed", "COMPLETED_PREREQUISITES_UNSATISFIED"), ("in_progress", "ACTIVE_PREREQUISITES_UNSATISFIED")):
            self.check(plan([task("sample", ["absent"], state)]), golden([("sample", ["PREREQUISITE_NOT_FOUND", code])],
                       edges=1, pending=0, active=int(state == "in_progress"), completed=int(state == "completed")))

    def test_unrelated_missing_prerequisite_withholds_clean_branch_lists(self):
        rows = valid_tasks()+[task("other", ["absent"])]
        self.check(plan(rows), golden([(row["id"], []) for row in valid_tasks()]+[("other", ["PREREQUISITE_NOT_FOUND"])],
                   edges=4, pending=3, active=0, completed=1))

    def test_all_cycle_members_exclude_tails_and_include_multi_parent_edges(self):
        rows = [task("a", ["b", "root"]), task("b", ["a"]), task("tail", ["b"]), task("c", ["c"]), task("root", state="completed")]
        self.check(plan(rows), golden([("a", ["DEPENDENCY_CYCLE"]), ("b", ["DEPENDENCY_CYCLE"]),
                   ("tail", []), ("c", ["SELF_DEPENDENCY", "DEPENDENCY_CYCLE"]), ("root", [])],
                   edges=5, pending=4, active=0, completed=1, cycles=3))

    def test_multiple_local_issues_have_fixed_order(self):
        for state, code in (("completed", "COMPLETED_PREREQUISITES_UNSATISFIED"), ("in_progress", "ACTIVE_PREREQUISITES_UNSATISFIED")):
            self.check(plan([task("sample", ["sample", "absent"], state)]),
                       golden([("sample", ["PREREQUISITE_NOT_FOUND", "SELF_DEPENDENCY", "DEPENDENCY_CYCLE", code])],
                              edges=2, pending=0, active=int(state == "in_progress"), completed=int(state == "completed"), cycles=1))

    def test_invalid_ancestor_cannot_unlock_declared_completed_descendant(self):
        rows = [task("a"), task("b", ["a"], "completed"), task("c", ["b"]), task("d", state="completed")]
        self.check(plan(rows), golden([("a", []), ("b", ["COMPLETED_PREREQUISITES_UNSATISFIED"]), ("c", []), ("d", [])],
                   edges=2, pending=2, active=0, completed=2))

    def test_seeded_path_oracle_and_bruteforce_order_match_whole_reports(self):
        import itertools

        selected = random.Random(16046)
        names = ["sample_a", "sample_b", "sample_c", "sample_d"]
        for iteration in range(8):
            rows = []
            for index, name in enumerate(names):
                pool = names[:index] if iteration % 2 == 0 else names+["absent"]
                requires = selected.sample(pool, selected.randrange(min(3, len(pool))+1))
                state = "pending" if iteration % 2 == 0 else selected.choice(("pending", "in_progress", "completed"))
                rows.append(task(name, requires, state))
            def lookup(name):
                return next((row for row in rows if row["id"] == name), None)
            cycles = set()
            for start in names:
                # Independent path reachability, without the runtime's bitset closure.
                pending, seen = list(lookup(start)["requires"]), set()
                while pending:
                    current = pending.pop()
                    if current == start:
                        cycles.add(start)
                        break
                    row = lookup(current)
                    if row is not None and current not in seen:
                        seen.add(current)
                        pending.extend(row["requires"])
            local = []
            for row in rows:
                missing = any(lookup(name) is None for name in row["requires"])
                satisfied = all(lookup(name) is not None and lookup(name)["state"] == "completed" for name in row["requires"])
                issues = (["PREREQUISITE_NOT_FOUND"] if missing else [])
                issues += ["SELF_DEPENDENCY"] if row["id"] in row["requires"] else []
                issues += ["DEPENDENCY_CYCLE"] if row["id"] in cycles else []
                if row["state"] == "completed" and not satisfied:
                    issues.append("COMPLETED_PREREQUISITES_UNSATISFIED")
                if row["state"] == "in_progress" and not satisfied:
                    issues.append("ACTIVE_PREREQUISITES_UNSATISFIED")
                local.append((row["id"], issues))
            order, eligible, waiting = [], [], []
            if not any(issues for name, issues in local):
                candidates = [candidate for candidate in itertools.permutations(names)
                              if all(candidate.index(parent) < candidate.index(row["id"]) for row in rows for parent in row["requires"])]
                order = list(min(candidates))
                for row in sorted(rows, key=lambda value: value["id"]):
                    if row["state"] == "pending":
                        target = eligible if all(lookup(name)["state"] == "completed" for name in row["requires"]) else waiting
                        target.append(row["id"])
            self.check(plan(rows), golden(local, edges=sum(len(row["requires"]) for row in rows),
                       pending=sum(row["state"] == "pending" for row in rows), active=sum(row["state"] == "in_progress" for row in rows),
                       completed=sum(row["state"] == "completed" for row in rows), cycles=len(cycles), order=order, eligible=eligible, waiting=waiting))

    def test_root_task_fields_states_and_types_are_exact(self):
        for value in (None, [], {}, dict(plan(), schema_version=True), dict(plan(), schema_version=1.0), dict(plan(), command="FICTIONAL_PRIVATE_COMMAND")):
            self.run_cli(self.fixture(raw=json.dumps(value).encode()), expected=2, code="PLAN_SCHEMA_INVALID")
        for row in ({}, dict(task(), path="FICTIONAL_PRIVATE_PATH"), dict(task(), payload={})):
            self.run_cli(self.fixture(plan([row])), expected=2, code="TASK_SCHEMA_INVALID")
        for state in (None, True, "done", "Pending", []):
            self.run_cli(self.fixture(plan([task(state=state)])), expected=2, code="TASK_STATE_INVALID")

    def test_ids_duplicates_and_prerequisite_list_contract_are_strict(self):
        for value in (None, 1, True, [], "Upper", "1first", "has space", "é", "a"*41):
            self.run_cli(self.fixture(plan([task(value)])), expected=2, code="TASK_ID_INVALID")
            self.run_cli(self.fixture(plan([task("sample", [value])])), expected=2, code="PREREQUISITE_ID_INVALID")
        for identifier in ("a", "a"*40):
            self.check(plan([task(identifier)]), golden([(identifier, [])], edges=0, pending=1, active=0, completed=0, order=[identifier], eligible=[identifier]))
        self.run_cli(self.fixture(plan([task(), task()])), expected=2, code="DUPLICATE_TASK_ID")
        for requires in (None, {}, "sample"):
            self.run_cli(self.fixture(plan([dict(task(), requires=requires)])), expected=2, code="PREREQUISITES_INVALID")
        self.run_cli(self.fixture(plan([task("sample", ["a", "a"])])), expected=2, code="DUPLICATE_PREREQUISITE_ID")

    def test_128_tasks_and_32_prerequisites_exact_bounds(self):
        names = ["sample_"+str(index).zfill(3) for index in range(128)]
        rows = [task(name, [] if index == 0 else [names[index-1]]) for index, name in enumerate(names)]
        self.check(plan(rows), golden([(name, []) for name in names], edges=127, pending=128, active=0, completed=0,
                   order=names, eligible=names[:1], waiting=names[1:]))
        for declarations in ([], rows+[task("extra")]):
            self.run_cli(self.fixture(plan(declarations)), expected=2, code="PLAN_SCHEMA_INVALID")
        roots = ["root_"+str(index).zfill(2) for index in range(32)]
        rows = [task(name, state="completed") for name in roots]+[task("join", roots)]
        self.check(plan(rows), golden([(row["id"], []) for row in rows], edges=32, pending=1, active=0, completed=32,
                   order=roots+["join"], eligible=["join"]))
        self.run_cli(self.fixture(plan([task("join", roots+["extra"])])), expected=2, code="PREREQUISITES_INVALID")

    def test_input_64_kib_exact_bom_and_extra_byte(self):
        raw = b"\xef\xbb\xbf"+json.dumps(plan()).encode()
        exact = raw+b" "*(65536-len(raw))
        self.check(plan(), default_result(), raw=exact)
        self.run_cli(self.fixture(raw=exact+b" "), expected=2, code="INPUT_SIZE_LIMIT")

    def test_duplicate_json_constants_encoding_and_malformed_data_are_fixed(self):
        raw = json.dumps(plan()).encode()
        for duplicate in (raw[:-1]+b',"tasks":[]}', raw.replace(b'"state": "pending"', b'"state":"pending","state":"pending"')):
            self.run_cli(self.fixture(raw=duplicate), expected=2, code="DUPLICATE_JSON_KEY")
        for constant in (b"NaN", b"Infinity", b"-Infinity"):
            self.run_cli(self.fixture(raw=raw.replace(b'"schema_version": 1', b'"schema_version":'+constant)), expected=2, code="NONSTANDARD_JSON")
        for value in (b"\xff", b"{", b"", b"{} {}"):
            self.run_cli(self.fixture(raw=value), expected=2, code="INPUT_OR_PLAN_FAILED")

    def test_task_and_prerequisite_permutations_preserve_complete_results(self):
        rows = [task("a", state="completed"), task("b", state="completed"), task("c", ["a", "b"]), task("d", ["a"]), task("e", ["a"], "in_progress")]
        wanted = golden([(row["id"], []) for row in rows], edges=4, pending=2, active=1, completed=2,
                        order=["a", "b", "c", "d", "e"], eligible=["c", "d"])
        selected = random.Random(12832)
        for iteration in range(5):
            declarations = [dict(row, requires=selected.sample(row["requires"], len(row["requires"]))) for row in selected.sample(rows, len(rows))]
            self.check(plan(declarations), wanted)

    def test_help_version_arguments_and_original_path_spellings_have_fixed_errors(self):
        self.assertIn("--plan", self.process("--help", json_output=False))
        self.assertEqual(self.process("--version", json_output=False), "workflow-plan-checker 0.1.0\n")
        for args in ((), ("--plan",), ("--pl", "FICTIONAL_PRIVATE_ARGUMENT"), ("--unknown", "FICTIONAL_PRIVATE_ARGUMENT")):
            self.process(*args, expected=2, code="ARGUMENTS_INVALID")
        self.run_cli(self.work/"FICTIONAL_PRIVATE_MISSING.json", expected=2, code="INPUT_OR_PLAN_FAILED")
        self.run_cli(self.runtime, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        for path in (self.work/"CON.json", self.work/"file:stream", self.work/".."/"escape.json"):
            self.run_cli(path, expected=2, code="INPUT_PATH_INVALID")
        source = self.fixture()
        for spelling in (str(source)+".", str(source)+" "):
            self.run_cli(spelling, expected=2, code="INPUT_PATH_INVALID")
        self.assertEqual(self.run_cli(source.name), default_result())

    def test_only_selected_control_is_read_without_clock_network_or_commands(self):
        source = self.fixture()
        (self.work/"unrelated-command.txt").write_bytes(b"FICTIONAL_PRIVATE_COMMAND_NEVER_EXECUTED")
        (self.work/"prior-capture.txt").write_bytes(b"Fictional prior capture must remain unchanged\n")
        script = self.wrapper("""
            selected = Path(INPUT_VALUE)
            original = os.open
            def opened(path, *args, **kwargs):
                assert Path(path) == selected, 'Unselected file opened'
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
