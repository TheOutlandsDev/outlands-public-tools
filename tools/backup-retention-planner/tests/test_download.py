"""Copied-script CLI consumers using only invented UTC snapshot declarations."""

import ctypes
from datetime import datetime, timedelta
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
# All 2030 timestamps below are fixed fictional policy inputs, never a clock.
AS_OF = "2030-04-10T12:00:00Z"
FLAGS = dict.fromkeys(("filesystem_scanned", "backup_contents_verified", "metadata_verified",
                      "deletion_performed", "deletion_authorized", "network_probed"), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(identifier="sample_now", created_at=AS_OF, pinned=False):
    return dict(id=identifier, created_at=created_at, pinned=pinned)


def plan(snapshots=None, *, as_of=AS_OF, keep_latest=1, keep_days=0):
    return dict(schema_version=1, snapshot_kind="independent_full", as_of=as_of,
                policy=dict(keep_latest=keep_latest, keep_days=keep_days),
                snapshots=[snapshot()] if snapshots is None else snapshots)


def golden(rows, *, keep, review, future, nonfuture, latest, issues=()):
    return dict(schema_version=1, status="REVIEW_REQUIRED" if review or issues else "KEEP_ONLY_PLAN",
                scope="DECLARED_INDEPENDENT_FULL_METADATA_ONLY", **FLAGS,
                counts=dict(keep=keep, review=review, future=future, nonfuture=nonfuture, latest_protected=latest),
                snapshots=[dict(id=identifier, decision="REVIEW" if reasons == ["OUTSIDE_DECLARED_PROTECTIONS"] else "KEEP",
                                reasons=reasons) for identifier, reasons in rows], issues=list(issues))


def default_result():
    return golden([("sample_now", ["LATEST_COUNT"])], keep=1, review=0, future=0, nonfuture=1, latest=1)


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="retention-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied single script"
        self.runtime.mkdir()
        self.source = self.runtime / "retention_plan.py"
        self.source.write_bytes((ROOT / "retention_plan.py").read_bytes())
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
                          + "import retention_plan as tool\nevents = []\n" + textwrap.dedent(body)
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
            self.assertEqual(set(value), {"schema_version", "status", "scope", "counts", "snapshots", "issues", *FLAGS})
            self.assertTrue(all(value[key] is False for key in FLAGS))
            for row in value["snapshots"]:
                self.assertEqual(set(row), {"id", "decision", "reasons"})
            self.assertNotIn("2030-", done.stdout)
        return value

    def run_cli(self, source=None, **options):
        return self.process("--plan", source or self.fixture(), **options)

    def check(self, value, wanted, *, raw=None, script=None):
        source = self.fixture(value, raw=raw)
        self.assertEqual(self.run_cli(source, expected=int(wanted["status"] == "REVIEW_REQUIRED"), script=script), wanted)
        return wanted

    def symlink(self, path, target):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_RETENTION_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_keep_only_plan_has_exact_complete_result_and_no_files(self):
        self.check(plan(), default_result())
        self.assertEqual({path.name for path in self.work.iterdir()}, {self.runtime.name, "FICTIONAL_PRIVATE_PLAN_1.json"})

    def test_count_age_and_pin_are_a_union_with_fixed_reason_order(self):
        value = plan([snapshot("old_pinned", "2030-04-01T12:00:00Z", True), snapshot("new_pinned", AS_OF, True),
                      snapshot("boundary", "2030-04-03T12:00:00Z"), snapshot("outside", "2030-04-03T11:59:59Z")], keep_days=7)
        self.check(value, golden([("old_pinned", ["PINNED"]), ("new_pinned", ["PINNED", "LATEST_COUNT", "WITHIN_AGE_WINDOW"]),
                                  ("boundary", ["WITHIN_AGE_WINDOW"]), ("outside", ["OUTSIDE_DECLARED_PROTECTIONS"])],
                                 keep=3, review=1, future=0, nonfuture=4, latest=1))

    def test_latest_timestamp_ties_protect_every_tied_declaration(self):
        rows = [snapshot("tie_a", "2030-04-09T12:00:00Z"), snapshot("older", "2030-04-08T12:00:00Z"),
                snapshot("tie_b", "2030-04-09T12:00:00Z"), snapshot("tie_c", "2030-04-09T12:00:00Z")]
        wanted = golden([("tie_a", ["LATEST_COUNT"]), ("older", ["OUTSIDE_DECLARED_PROTECTIONS"]),
                         ("tie_b", ["LATEST_COUNT"]), ("tie_c", ["LATEST_COUNT"])],
                        keep=3, review=1, future=0, nonfuture=4, latest=3)
        for count in (1, 2, 3):
            self.check(plan(rows, keep_latest=count), wanted)

    def test_age_window_is_inclusive_to_second_and_zero_disables_it(self):
        rows = [snapshot("new"), snapshot("boundary", "2030-04-09T12:00:00Z"),
                snapshot("inside", "2030-04-09T12:00:01Z"), snapshot("outside", "2030-04-09T11:59:59Z")]
        self.check(plan(rows, keep_days=1), golden([("new", ["LATEST_COUNT", "WITHIN_AGE_WINDOW"]),
                   ("boundary", ["WITHIN_AGE_WINDOW"]), ("inside", ["WITHIN_AGE_WINDOW"]),
                   ("outside", ["OUTSIDE_DECLARED_PROTECTIONS"])], keep=3, review=1, future=0, nonfuture=4, latest=1))
        self.check(plan(rows, keep_days=0), golden([("new", ["LATEST_COUNT"])] +
                   [(name, ["OUTSIDE_DECLARED_PROTECTIONS"]) for name in ("boundary", "inside", "outside")],
                   keep=1, review=3, future=0, nonfuture=4, latest=1))

    def test_future_dates_never_displace_nonfuture_latest_or_age_baseline(self):
        self.check(plan([snapshot("future", "2030-04-11T12:00:00Z"), snapshot("present"),
                         snapshot("old_pin", "2030-04-01T12:00:00Z", True)], keep_days=7),
                   golden([("future", ["FUTURE_TIMESTAMP_UNVERIFIED"]), ("present", ["LATEST_COUNT", "WITHIN_AGE_WINDOW"]),
                           ("old_pin", ["PINNED"])], keep=3, review=0, future=1, nonfuture=2, latest=1,
                          issues=["FUTURE_TIMESTAMPS_PRESENT"]))

    def test_all_future_and_insufficient_count_keep_rows_but_require_review(self):
        self.check(plan([snapshot("future_pin", "2030-04-11T12:00:00Z", True), snapshot("future", "2030-04-12T12:00:00Z")],
                        keep_latest=2, keep_days=36500),
                   golden([("future_pin", ["PINNED", "FUTURE_TIMESTAMP_UNVERIFIED"]), ("future", ["FUTURE_TIMESTAMP_UNVERIFIED"])],
                          keep=2, review=0, future=2, nonfuture=0, latest=0,
                          issues=["FUTURE_TIMESTAMPS_PRESENT", "LATEST_COUNT_NOT_MET"]))
        self.check(plan(keep_latest=2), golden([("sample_now", ["LATEST_COUNT"])], keep=1, review=0,
                   future=0, nonfuture=1, latest=1, issues=["LATEST_COUNT_NOT_MET"]))

    def test_seeded_pairwise_rank_oracle_and_permutation_keep_declared_order(self):
        selected = random.Random(11039)
        review_instant = datetime.strptime(AS_OF, "%Y-%m-%dT%H:%M:%SZ")
        for iteration in range(6):
            rows = [snapshot("sample_" + str(index), (review_instant + timedelta(days=selected.randrange(-8, 3))).strftime("%Y-%m-%dT%H:%M:%SZ"),
                             bool(selected.randrange(4) == 0)) for index in range(9)]
            count, days = selected.randrange(1, 5), selected.choice((0, 2, 5))
            dated = [(row, datetime.strptime(row["created_at"], "%Y-%m-%dT%H:%M:%SZ")) for row in rows]
            eligible = [(row, instant) for row, instant in dated if instant <= review_instant]
            reasons, future, latest, review = {}, 0, 0, 0
            for row, instant in dated:
                why = ["PINNED"] if row["pinned"] else []
                if instant > review_instant:
                    why.append("FUTURE_TIMESTAMP_UNVERIFIED")
                    future += 1
                else:
                    # Independent pairwise rank, without selecting a sorted cutoff.
                    if sum(other > instant for candidate, other in eligible) < count:
                        why.append("LATEST_COUNT")
                        latest += 1
                    if days and (review_instant - instant).total_seconds() <= days*86400:
                        why.append("WITHIN_AGE_WINDOW")
                if not why:
                    review += 1
                reasons[row["id"]] = why or ["OUTSIDE_DECLARED_PROTECTIONS"]
            issues = (["FUTURE_TIMESTAMPS_PRESENT"] if future else []) + (["LATEST_COUNT_NOT_MET"] if len(eligible) < count else [])
            for order in (rows, selected.sample(rows, len(rows))):
                self.check(plan(order, keep_latest=count, keep_days=days),
                           golden([(row["id"], reasons[row["id"]]) for row in order], keep=len(rows)-review, review=review,
                                  future=future, nonfuture=len(eligible), latest=latest, issues=issues))

    def test_exact_root_and_policy_schemas_do_not_accept_unknown_backup_fields(self):
        for value in (None, [], {}, dict(plan(), schema_version=True), dict(plan(), schema_version=1.0),
                      dict(plan(), schema_version="1"), dict(plan(), credential="FICTIONAL_PRIVATE_VALUE")):
            self.run_cli(self.fixture(raw=json.dumps(value).encode()), expected=2, code="PLAN_SCHEMA_INVALID")
        for kind in ("incremental", "differential", None):
            self.run_cli(self.fixture(dict(plan(), snapshot_kind=kind)), expected=2, code="INDEPENDENT_FULL_DECLARATION_REQUIRED")
        for policy in ({}, [], dict(keep_latest=1), dict(keep_latest=1, keep_days=0, delete=True)):
            self.run_cli(self.fixture(dict(plan(), policy=policy)), expected=2, code="POLICY_SCHEMA_INVALID")

    def test_snapshot_schema_ids_duplicates_and_pinned_boolean_are_strict(self):
        for row in ({}, dict(snapshot(), path="FICTIONAL_PRIVATE_PATH"), dict(snapshot(), parent_id="other")):
            self.run_cli(self.fixture(plan([row])), expected=2, code="SNAPSHOT_SCHEMA_INVALID")
        for identifier in ("Upper", "1starts_number", "has space", "é", "a"*41, None):
            self.run_cli(self.fixture(plan([snapshot(identifier)])), expected=2, code="SNAPSHOT_ID_INVALID")
        for identifier in ("a", "a"*40):
            self.check(plan([snapshot(identifier)]), golden([(identifier, ["LATEST_COUNT"])], keep=1, review=0, future=0, nonfuture=1, latest=1))
        self.run_cli(self.fixture(plan([snapshot(), snapshot()])), expected=2, code="DUPLICATE_SNAPSHOT_ID")
        for pinned in (0, 1, "true", None):
            self.run_cli(self.fixture(plan([snapshot(pinned=pinned)])), expected=2, code="PIN_FLAG_INVALID")

    def test_timestamp_canonical_utc_and_24_hour_rollover_are_rejected(self):
        for value in ("2030-04-10T24:00:00Z", "2030-04-10T25:00:00Z", "2030-04-10T12:00:60Z",
                      "2030-02-29T12:00:00Z", "2030-04-10T12:00:00+00:00", "2030-04-10T12:00:00.0Z",
                      "2030-04-10T12:00:00z", "2030-04-10T12:00:00", None):
            with self.subTest(timestamp=value):
                self.run_cli(self.fixture(plan(as_of=value)), expected=2, code="TIMESTAMP_INVALID")
                self.run_cli(self.fixture(plan([snapshot(created_at=value)])), expected=2, code="TIMESTAMP_INVALID")

    def test_valid_calendar_extremes_and_leap_dates_are_supported(self):
        for instant in ("0001-01-01T00:00:00Z", "2000-02-29T23:59:59Z", "9999-12-31T23:59:59Z"):
            self.check(plan([snapshot(created_at=instant)], as_of=instant), default_result())

    def test_policy_maximum_days_and_count_types_bounds_are_enforced(self):
        for field, value in (("keep_latest", 0), ("keep_latest", 257), ("keep_latest", True), ("keep_latest", 1.0),
                             ("keep_latest", "1"), ("keep_days", -1), ("keep_days", 36501), ("keep_days", False),
                             ("keep_days", 1.0), ("keep_days", "7")):
            value_plan = plan()
            value_plan["policy"][field] = value
            self.run_cli(self.fixture(value_plan), expected=2, code="POLICY_VALUE_INVALID")
        instant = datetime.strptime(AS_OF, "%Y-%m-%dT%H:%M:%SZ") - timedelta(days=36500)
        rows = [snapshot(), snapshot("maximum_boundary", instant.strftime("%Y-%m-%dT%H:%M:%SZ")),
                snapshot("outside_maximum", (instant-timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ"))]
        self.check(plan(rows, keep_days=36500), golden([("sample_now", ["LATEST_COUNT", "WITHIN_AGE_WINDOW"]),
                   ("maximum_boundary", ["WITHIN_AGE_WINDOW"]), ("outside_maximum", ["OUTSIDE_DECLARED_PROTECTIONS"])],
                   keep=2, review=1, future=0, nonfuture=3, latest=1))
        self.check(plan(keep_latest=256), golden([("sample_now", ["LATEST_COUNT"])], keep=1, review=0,
                   future=0, nonfuture=1, latest=1, issues=["LATEST_COUNT_NOT_MET"]))

    def test_snapshot_count_256_exact_and_one_extra_are_bounded(self):
        rows = [snapshot("sample_" + str(index)) for index in range(256)]
        self.check(plan(rows, keep_latest=256), golden([(row["id"], ["LATEST_COUNT"]) for row in rows],
                   keep=256, review=0, future=0, nonfuture=256, latest=256))
        for rows in ([], rows + [snapshot("extra")]):
            self.run_cli(self.fixture(plan(rows)), expected=2, code="PLAN_SCHEMA_INVALID")

    def test_input_64_kib_exact_utf8_bom_and_one_extra_byte(self):
        raw = b"\xef\xbb\xbf" + json.dumps(plan()).encode()
        exact = raw + b" "*(65536-len(raw))
        self.check(plan(), default_result(), raw=exact)
        self.run_cli(self.fixture(raw=exact+b" "), expected=2, code="INPUT_SIZE_LIMIT")

    def test_duplicate_json_keys_nonfinite_encoding_and_malformed_input_are_fixed(self):
        raw = json.dumps(plan()).encode()
        for duplicate in (raw[:-1]+b',"as_of":"2030-04-10T12:00:00Z"}',
                          raw.replace(b'"keep_days": 0', b'"keep_days": 0,"keep_days":0'),
                          raw.replace(b'"pinned": false', b'"pinned": false,"pinned":false')):
            self.run_cli(self.fixture(raw=duplicate), expected=2, code="DUPLICATE_JSON_KEY")
        for constant in (b"NaN", b"Infinity", b"-Infinity"):
            self.run_cli(self.fixture(raw=raw.replace(b'"keep_days": 0', b'"keep_days": '+constant)),
                         expected=2, code="NONSTANDARD_JSON")
        for value in (b"\xff", b"{", b"", b"{} {}"):
            self.run_cli(self.fixture(raw=value), expected=2, code="INPUT_OR_PLAN_FAILED")

    def test_help_version_explicit_arguments_and_path_errors_have_no_private_echo(self):
        self.assertIn("--plan", self.process("--help", json_output=False))
        self.assertEqual(self.process("--version", json_output=False), "backup-retention-planner 0.1.0\n")
        for args in ((), ("--plan",), ("--pl", "FICTIONAL_PRIVATE_ARGUMENT"), ("--unknown", "FICTIONAL_PRIVATE_ARGUMENT")):
            self.process(*args, expected=2, code="ARGUMENTS_INVALID")
        self.run_cli(self.work / "FICTIONAL_PRIVATE_MISSING.json", expected=2, code="INPUT_OR_PLAN_FAILED")
        self.run_cli(self.runtime, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        for path in (self.work / "CON.json", self.work / "file:stream", self.work / ".." / "escape.json"):
            self.run_cli(path, expected=2, code="INPUT_PATH_INVALID")
        source = self.fixture()
        self.assertEqual(self.run_cli(source.name), default_result())

    def test_only_selected_plan_is_read_without_clock_network_or_backup_actions(self):
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
                raise AssertionError('Clock, network, process or storage enumeration attempted')
            class SuppliedClockOnly(tool.datetime):
                now = staticmethod(forbidden)
                utcnow = staticmethod(forbidden)
                today = staticmethod(forbidden)
            tool.datetime = SuppliedClockOnly
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
            """.replace("INPUT_VALUE", repr(str(source))), prelude="import time, socket, urllib.request, subprocess, runpy\n",
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
                return (ancestors + ('controlled observed change',), leaf) if len(events) == 2 else (ancestors, leaf)
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
    def test_native_windows_named_stream_is_not_part_of_selected_plan(self):
        source = self.fixture()
        stream = str(source) + ":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b"FICTIONAL_PRIVATE_NAMED_STREAM")
        self.assertEqual(self.run_cli(source), default_result())
        self.run_cli(stream, expected=2, code="INPUT_PATH_INVALID")
        # Baseline behavior: Windows absolute normalization accepts these aliases.
        # This observation is not a lexical-refusal safeguard or race guarantee.
        for suffix in (".", " "):
            self.assertEqual(self.run_cli(str(source) + suffix), default_result())
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
        substitute = ("\\??\\" + str(target)).encode("utf-16-le")
        printable = str(target).encode("utf-16-le")
        payload = substitute + b"\x00\x00" + printable + b"\x00\x00"
        data = struct.pack("<LHHHHHH", 0xA0000003, 8 + len(payload), 0,
                           0, len(substitute), len(substitute) + 2, len(printable)) + payload
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
