"""Actual copied-script consumers of fictional assessment records, never target testing."""

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
FLAGS = dict.fromkeys(("execution_performed", "network_probed", "records_modified", "authorization_verified", "isolation_verified", "outcomes_verified"), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def submission(identifier="sample_original", series="sample_series", revision=2):
    return dict(id=identifier, series_id=series, revision=revision)


def finding(identifier="sample_finding", original="sample_original", state="closure_claimed", selected="sample_retest"):
    return dict(id=identifier, submission_id=original, state=state, selected_retest_id=selected)


def retest(identifier="sample_retest", owner="sample_finding", replacement="sample_replacement", outcome="not_observed"):
    return dict(id=identifier, finding_id=owner, submission_id=replacement, outcome=outcome)


def records(submissions=None, findings=None, retests=None):
    return dict(schema_version=1, submissions=[submission(), submission("sample_replacement", revision=10)] if submissions is None else submissions,
                findings=[finding()] if findings is None else findings, retests=[retest()] if retests is None else retests)


def checked(identifier, kind, status="PASS", evidence=None):
    defaults = dict(submission="SUBMISSION_DECLARATION_VALID", finding="CLOSURE_CLAIM_CONSISTENT", retest="RETEST_RELATIONSHIPS_CONSISTENT")
    return dict(id=identifier, kind=kind, status=status, evidence=evidence or defaults[kind])


def golden(rows):
    counts = {key: sum(row["status"] == status for row in rows) for key, status in (("passed", "PASS"), ("failed", "FAIL"), ("blocked", "BLOCKED"))}
    counts.update({plural: sum(row["kind"] == kind for row in rows) for plural, kind in (("submissions", "submission"), ("findings", "finding"), ("retests", "retest"))})
    return dict(schema_version=1, status="REVIEW_REQUIRED" if counts["failed"] or counts["blocked"] else "DECLARED_RECORDS_CONSISTENT",
                scope="DECLARED_ASSESSMENT_RECORDS_ONLY", **FLAGS, counts=counts, checks=rows)


def default_rows():
    return [checked("sample_original", "submission"), checked("sample_replacement", "submission"),
            checked("sample_finding", "finding"), checked("sample_retest", "retest")]


def default_result():
    return golden(default_rows())


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="assessment-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied single script"
        self.runtime.mkdir()
        self.source = self.runtime / "assessment_check.py"
        self.source.write_bytes((ROOT / "assessment_check.py").read_bytes())
        self.runtime_hash = sha(self.source.read_bytes())
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def fixture(self, value=None, *, raw=None):
        self.serial += 1
        path = self.work / ("FICTIONAL_PRIVATE_PLAN_" + str(self.serial) + ".json")
        path.write_bytes(json.dumps(records() if value is None else value).encode("utf-8") if raw is None else raw)
        return path

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import assessment_check as tool\nevents = []\n" + textwrap.dedent(body)
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
            self.assertEqual(set(value), {"schema_version", "status", "scope", "counts", "checks", *FLAGS})
            self.assertTrue(all(value[key] is False for key in FLAGS))
            for row in value["checks"]:
                self.assertEqual(set(row), {"id", "kind", "status", "evidence"})
        return value

    def run_cli(self, source=None, **options):
        return self.process("--records", source or self.fixture(), **options)

    def check(self, value, wanted, *, raw=None, script=None):
        self.assertEqual(self.run_cli(self.fixture(value, raw=raw), expected=int(wanted["status"] == "REVIEW_REQUIRED"), script=script), wanted)
        return wanted

    def symlink(self, path, target):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_ASSESSMENT_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_complete_consistent_records_json_and_no_result_files(self):
        self.check(records(), default_result())
        self.assertEqual({path.name for path in self.work.iterdir()}, {self.runtime.name, "FICTIONAL_PRIVATE_PLAN_1.json"})
        self.check(records([submission()], [], []), golden([checked("sample_original", "submission")]))

    def test_open_null_selection_accepts_historical_outcomes_without_closure(self):
        for outcome in ("not_run", "still_present", "not_observed", "inconclusive"):
            self.check(records(findings=[finding(state="open", selected=None)], retests=[retest(outcome=outcome)]), golden([
                *default_rows()[:2], checked("sample_finding", "finding", evidence="OPEN_RECORD_CONSISTENT"), checked("sample_retest", "retest")]))
        self.check(records(findings=[finding(state="open")]), golden([
            *default_rows()[:2], checked("sample_finding", "finding", "FAIL", "OPEN_HAS_SELECTED_RETEST"), checked("sample_retest", "retest")]))

    def test_pending_outcome_matrix_requires_explicit_not_run(self):
        for outcome in ("not_run", "still_present", "not_observed", "inconclusive"):
            state, evidence = ("PASS", "PENDING_RECORD_CONSISTENT") if outcome == "not_run" else ("FAIL", "PENDING_OUTCOME_INCONSISTENT")
            self.check(records(findings=[finding(state="retest_pending")], retests=[retest(outcome=outcome)]), golden([
                *default_rows()[:2], checked("sample_finding", "finding", state, evidence), checked("sample_retest", "retest")]))

    def test_closure_outcome_matrix_requires_explicit_not_observed(self):
        for outcome in ("not_run", "still_present", "not_observed", "inconclusive"):
            state, evidence = ("PASS", "CLOSURE_CLAIM_CONSISTENT") if outcome == "not_observed" else ("FAIL", "CLOSURE_OUTCOME_NOT_SUPPORTING")
            self.check(records(retests=[retest(outcome=outcome)]), golden([
                *default_rows()[:2], checked("sample_finding", "finding", state, evidence), checked("sample_retest", "retest")]))

    def test_missing_selection_and_typed_reference_failures_are_blocked_with_precedence(self):
        for selected, evidence in [(None, "SELECTED_RETEST_NOT_SUPPLIED"), ("missing", "SELECTED_RETEST_NOT_DECLARED"), ("sample_original", "SELECTED_RETEST_NOT_DECLARED")]:
            self.check(records(findings=[finding(selected=selected)]), golden([
                *default_rows()[:2], checked("sample_finding", "finding", "BLOCKED", evidence), checked("sample_retest", "retest")]))
        self.check(records(findings=[finding(original="missing")], retests=[retest(replacement="also_missing")]), golden([
            *default_rows()[:2], checked("sample_finding", "finding", "BLOCKED", "ORIGINAL_SUBMISSION_NOT_DECLARED"),
            checked("sample_retest", "retest", "BLOCKED", "ORIGINAL_SUBMISSION_NOT_DECLARED")]))
        self.check(records(findings=[finding(state="open", selected=None)], retests=[retest(owner="missing", replacement="also_missing")]), golden([
            *default_rows()[:2], checked("sample_finding", "finding", evidence="OPEN_RECORD_CONSISTENT"),
            checked("sample_retest", "retest", "BLOCKED", "FINDING_NOT_DECLARED")]))
        self.check(records(retests=[retest(replacement="sample_finding")]), golden([
            *default_rows()[:2], checked("sample_finding", "finding", "BLOCKED", "SELECTED_RETEST_INVALID"),
            checked("sample_retest", "retest", "BLOCKED", "REPLACEMENT_SUBMISSION_NOT_DECLARED")]))

    def test_selected_retest_must_belong_to_the_same_finding(self):
        self.check(records(findings=[finding(), finding("other_finding", state="open", selected=None)], retests=[retest(owner="other_finding")]), golden([
            *default_rows()[:2], checked("sample_finding", "finding", "FAIL", "SELECTED_RETEST_FINDING_MISMATCH"),
            checked("other_finding", "finding", evidence="OPEN_RECORD_CONSISTENT"), checked("sample_retest", "retest")]))

    def test_invalid_relationship_blocks_before_stale_revision_and_outcome(self):
        for replacement, evidence in [(submission("sample_replacement", series="other_series", revision=10), "SERIES_MISMATCH"),
                                      (submission("sample_replacement", revision=1), "REPLACEMENT_NOT_LATER")]:
            schema = records([submission(), replacement, submission("latest", revision=20)], retests=[retest(outcome="still_present")])
            self.check(schema, golden([checked(row["id"], "submission") for row in schema["submissions"]]+[
                checked("sample_finding", "finding", "BLOCKED", "SELECTED_RETEST_INVALID"), checked("sample_retest", "retest", "FAIL", evidence)]))
        self.check(records(retests=[retest(replacement="sample_original")]), golden([
            *default_rows()[:2], checked("sample_finding", "finding", "BLOCKED", "SELECTED_RETEST_INVALID"),
            checked("sample_retest", "retest", "FAIL", "REPLACEMENT_NOT_LATER")]))

    def test_latest_is_numeric_within_original_series_not_array_or_global_order(self):
        submissions = [submission("unrelated", series="other_series", revision=999), submission("sample_replacement", revision=10), submission()]
        self.check(records(submissions), golden([checked(row["id"], "submission") for row in submissions]+default_rows()[2:]))
        submissions.append(submission("newest", revision=20))
        for rows in (submissions, submissions[::-1]):
            self.check(records(rows, retests=[retest(outcome="still_present")]), golden([
                *[checked(row["id"], "submission") for row in rows],
                checked("sample_finding", "finding", "FAIL", "SELECTED_SUBMISSION_NOT_LATEST_DECLARED"), checked("sample_retest", "retest")]))

    def test_unselected_bad_historical_retests_still_require_review(self):
        submissions = [submission(), submission("sample_replacement", revision=10), submission("old", revision=1)]
        self.check(records(submissions, retests=[retest(), retest("history", replacement="old", outcome="not_run")]), golden([
            *[checked(row["id"], "submission") for row in submissions], checked("sample_finding", "finding"),
            checked("sample_retest", "retest"), checked("history", "retest", "FAIL", "REPLACEMENT_NOT_LATER")]))

    def test_seeded_independent_outcome_and_latest_oracle_preserves_permuted_order(self):
        selected = random.Random(429)
        allowed = {("retest_pending", "not_run"), ("closure_claimed", "not_observed")}
        for iteration in range(8):
            submissions, findings, retests, expected = [], [], [], {}
            for index in range(4):
                prefix = "s"+str(index)
                revisions = [2, 10, 100]
                for revision in revisions:
                    row = submission(prefix+"r"+str(revision), series=prefix, revision=revision)
                    submissions.append(row)
                    expected[row["id"]] = checked(row["id"], "submission")
                chosen = selected.choice(revisions[1:])
                state = selected.choice(("open", "retest_pending", "closure_claimed"))
                outcome = selected.choice(("not_run", "still_present", "not_observed", "inconclusive"))
                owner, summary = prefix+"f", prefix+"t"
                findings.append(finding(owner, original=prefix+"r2", state=state, selected=None if state == "open" else summary))
                retests.append(retest(summary, owner=owner, replacement=prefix+"r"+str(chosen), outcome=outcome))
                if state == "open":
                    status, evidence = "PASS", "OPEN_RECORD_CONSISTENT"
                elif any(value > chosen for value in revisions):
                    status, evidence = "FAIL", "SELECTED_SUBMISSION_NOT_LATEST_DECLARED"
                elif (state, outcome) in allowed:
                    status, evidence = "PASS", "PENDING_RECORD_CONSISTENT" if state == "retest_pending" else "CLOSURE_CLAIM_CONSISTENT"
                else:
                    status, evidence = "FAIL", "PENDING_OUTCOME_INCONSISTENT" if state == "retest_pending" else "CLOSURE_OUTCOME_NOT_SUPPORTING"
                expected[owner] = checked(owner, "finding", status, evidence)
                expected[summary] = checked(summary, "retest")
            for reverse in (False, True):
                ordered = [rows[::-1] if reverse else rows for rows in (submissions, findings, retests)]
                self.check(records(*ordered), golden([expected[row["id"]] for rows in ordered for row in rows]))

    def test_schema_tokens_revisions_states_outcomes_and_duplicate_pairs_are_strict(self):
        for value in (None, [], {}, dict(records(), schema_version=True), dict(records(), narrative="FICTIONAL_PRIVATE_VALUE")):
            self.run_cli(self.fixture(raw=json.dumps(value).encode()), expected=2, code="RECORDS_SCHEMA_INVALID")
        samples = [
            (records([dict(submission(), private="FICTIONAL_PRIVATE_VALUE")]), "SUBMISSION_SCHEMA_INVALID"),
            (records(findings=[dict(finding(), extra=1)]), "FINDING_SCHEMA_INVALID"),
            (records(retests=[dict(retest(), extra=1)]), "RETEST_SCHEMA_INVALID"),
            (records([submission("Upper")]), "RECORD_TOKEN_INVALID"),
            (records(findings=[finding(original=True)]), "RECORD_TOKEN_INVALID"),
            (records(retests=[retest(owner=None)]), "RECORD_TOKEN_INVALID"),
            (records(findings=[finding(state="Closed")]), "FINDING_STATE_INVALID"),
            (records(retests=[retest(outcome="passed")]), "RETEST_OUTCOME_INVALID"),
            (records(findings=[finding("sample_original")]), "DUPLICATE_RECORD_ID"),
            (records([submission(), submission("second", revision=2)]), "DUPLICATE_SERIES_REVISION"),
            (records(retests=[retest(), retest("second")]), "DUPLICATE_RETEST_PAIR"),
        ]
        samples += [(records([submission(revision=value)]), "REVISION_INVALID") for value in (True, 1.0, "2", 0, 1000000001)]
        for value, code in samples:
            self.run_cli(self.fixture(value), expected=2, code=code)
        for revision in (1, 1000000000):
            self.check(records([submission(revision=revision)], [], []), golden([checked("sample_original", "submission")]))

    def test_128_per_collection_and_256_total_bounds_are_independent(self):
        submissions = [submission("s"+str(index), series="s"+str(index), revision=1) for index in range(128)]
        findings = [finding("f"+str(index), original="s"+str(index), state="open", selected=None) for index in range(128)]
        self.check(records(submissions, findings, []), golden([checked(row["id"], "submission") for row in submissions]+[
            checked(row["id"], "finding", evidence="OPEN_RECORD_CONSISTENT") for row in findings]))
        retests = [retest("r"+str(index), owner="sample_finding", replacement="replacement_"+str(index), outcome="not_run") for index in range(128)]
        schema = records([submission()], [finding(state="open", selected=None)], retests)
        self.check(schema, golden([checked("sample_original", "submission"), checked("sample_finding", "finding", evidence="OPEN_RECORD_CONSISTENT")]+[
            checked(row["id"], "retest", "BLOCKED", "REPLACEMENT_SUBMISSION_NOT_DECLARED") for row in retests]))
        for value in (records([], [], []), records(submissions+[submission("extra")], [], []),
                      records([submission()], findings+[finding("extra", state="open", selected=None)], []),
                      records([submission()], [], retests+[retest("extra")]), records(submissions, findings, [retest()])):
            self.run_cli(self.fixture(value), expected=2, code="RECORD_COUNT_INVALID")

    def test_input_64_kib_bom_duplicate_json_constants_and_invalid_encoding(self):
        raw = b"\xef\xbb\xbf"+json.dumps(records()).encode()
        exact = raw+b" "*(65536-len(raw))
        self.assertEqual(self.run_cli(self.fixture(raw=exact)), default_result())
        self.run_cli(self.fixture(raw=exact+b" "), expected=2, code="INPUT_SIZE_LIMIT")
        for raw, code in [(b'{"private":1,"private":2}', "DUPLICATE_JSON_KEY"), (b'{"private":NaN}', "NONSTANDARD_JSON"),
                          (b'{"private":Infinity}', "NONSTANDARD_JSON"), (b'{"private":-Infinity}', "NONSTANDARD_JSON"),
                          (b"\xff", "INPUT_OR_RECORDS_FAILED"), (b"{", "INPUT_OR_RECORDS_FAILED"), (b"{} trailing", "INPUT_OR_RECORDS_FAILED")]:
            self.run_cli(self.fixture(raw=raw), expected=2, code=code)

    def test_six_false_flags_and_id_only_metadata_omit_raw_record_values(self):
        submissions = [submission("own_b", series="fictional_private_series", revision=100), submission("own_a", series="fictional_private_series", revision=2)]
        value = records(submissions, [finding("own_f", original="own_a", selected="own_t")], [retest("own_t", owner="own_f", replacement="own_b")])
        self.check(value, golden([checked("own_b", "submission"), checked("own_a", "submission"), checked("own_f", "finding"), checked("own_t", "retest")]))

    def test_help_version_arguments_and_path_errors_have_fixed_private_json(self):
        for argument in ("--help", "--version"):
            self.assertIn("assessment-record-checker", self.process(argument, json_output=False))
        for arguments in ((), ("--rec", "FICTIONAL_PRIVATE_MISSING"), ("--record", "FICTIONAL_PRIVATE_MISSING"),
                          ("--records", "x", "--report", "FICTIONAL_PRIVATE_OUTPUT")):
            self.process(*arguments, expected=2, code="ARGUMENTS_INVALID")
        self.run_cli(self.work/"FICTIONAL_PRIVATE_MISSING.json", expected=2, code="INPUT_OR_RECORDS_FAILED")
        self.run_cli(self.runtime, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        for path in (self.work/"CON.json", self.work/"file:stream", self.work/".."/"escape.json"):
            self.run_cli(path, expected=2, code="INPUT_PATH_INVALID")
        source = self.fixture()
        self.assertEqual(self.run_cli(source.name), default_result())

    def test_only_selected_ledger_is_read_without_target_network_process_clock_or_environment_activity(self):
        source = self.fixture()
        (self.work/"unrelated-evidence.txt").write_bytes(b"FICTIONAL_PRIVATE_ATTACHMENT_NEVER_OPEN")
        (self.work/"prior-capture.txt").write_bytes(b"Fictional prior capture must remain unchanged\n")
        script = self.wrapper("""
            selected = Path(INPUT_VALUE)
            environment_before = dict(os.environ)
            original = os.open
            def opened(path, *args, **kwargs):
                assert Path(path) == selected, 'Unselected evidence, target or environment file opened'
                events.append(True)
                return original(path, *args, **kwargs)
            def forbidden(*args, **kwargs):
                raise AssertionError('Target, network, process, clock or environment activity attempted')
            os.open = opened
            os.scandir = forbidden
            os.listdir = forbidden
            os.putenv = forbidden
            os.unsetenv = forbidden
            Path.open = forbidden
            socket.socket = forbidden
            socket.create_connection = forbidden
            socket.getaddrinfo = forbidden
            socket.gethostbyname = forbidden
            urllib.request.urlopen = forbidden
            subprocess.Popen = forbidden
            runpy.run_path = forbidden
            os.system = forbidden
            os.execv = forbidden
            time.time = forbidden
            time.monotonic = forbidden
            """.replace("INPUT_VALUE", repr(str(source))), prelude="import socket, urllib.request, subprocess, runpy, time\n",
                              postlude="assert events == [True] and status == 0\nassert dict(os.environ) == environment_before\n")
        self.assertEqual(self.run_cli(source, script=script), default_result())

    def test_series_namespace_is_separate_but_entity_references_remain_typed(self):
        value = records([submission("sample_original", series="sample_finding"), submission("sample_replacement", series="sample_finding", revision=10)])
        self.check(value, default_result())
        value = records(findings=[finding(original="sample_retest")])
        self.check(value, golden([*default_rows()[:2], checked("sample_finding", "finding", "BLOCKED", "ORIGINAL_SUBMISSION_NOT_DECLARED"),
                                  checked("sample_retest", "retest", "BLOCKED", "ORIGINAL_SUBMISSION_NOT_DECLARED")]))

    def test_native_hardlinked_input_is_refused_and_target_preserved(self):
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
        self.run_cli(source, script=script, expected=2, code="INPUT_OR_RECORDS_FAILED")

    def test_native_symlink_input_leaf_and_dangling_are_refused(self):
        source = self.fixture()
        alias = self.work / "linked-plan.json"
        self.symlink(alias, source)
        self.run_cli(alias, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        absent = self.work / "owned-absent-target.json"
        dangling = self.work / "dangling-plan.json"
        self.symlink(dangling, absent)
        self.run_cli(dangling, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        self.assertFalse(absent.exists())

    def test_native_symlink_input_parent_is_refused(self):
        source = self.fixture()
        target = self.work / "owned-plan-parent"
        target.mkdir()
        moved = target / "plan.json"
        source.rename(moved)
        alias = self.work / "linked-parent"
        self.symlink(alias, target)
        self.run_cli(alias / "plan.json", expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_input_parent_is_refused(self):
        source = self.fixture()
        target = self.work / "owned-plan-parent"
        target.mkdir()
        moved = target / "plan.json"
        source.rename(moved)
        alias = self.work / "junction-parent"
        self.junction(alias, target)
        self.run_cli(alias / "plan.json", expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows alternate stream fixture")
    def test_native_windows_named_stream_is_not_part_of_selected_input(self):
        source = self.fixture()
        stream = str(source)+":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b"FICTIONAL_PRIVATE_NAMED_STREAM")
        self.assertEqual(self.run_cli(source), default_result())
        self.run_cli(stream, expected=2, code="INPUT_PATH_INVALID")
        # Observed retained normalization, not a blanket lexical-refusal guard.
        for spelling in (str(source)+".", str(source)+" ", str(source.parent)+"."+os.sep+source.name):
            self.assertEqual(self.run_cli(spelling), default_result())
        self.run_cli(str(source.parent)+" "+os.sep+source.name, expected=2, code="INPUT_PATH_INVALID")
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
        self.run_cli(source, script=script, expected=2, code="INPUT_OR_RECORDS_FAILED")
        self.assertEqual(self.run_cli(source), default_result())

    @unittest.skipUnless(os.name != "nt", "Native POSIX FIFO fixture")
    def test_native_posix_fifo_input_is_refused_before_open(self):
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
