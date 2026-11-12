"""Actual copied-script consumers of fictional aggregate counts, never model execution."""

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
FLAGS = dict.fromkeys(("model_executed", "network_probed", "input_modified", "ground_truth_verified", "predictions_verified"), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def counts(matrix=None, identifiers=None):
    matrix = [[8, 2], [1, 9]] if matrix is None else matrix
    return dict(schema_version=1, classes=identifiers if identifiers is not None else ["class_"+str(index) for index in range(len(matrix))], counts=matrix)


def ratio(numerator, denominator):
    return dict(status="DEFINED", numerator=numerator, denominator=denominator) if denominator else dict(status="UNDEFINED", numerator=None, denominator=0)


def metric(identifier, support, true_positive, false_positive, false_negative):
    return dict(id=identifier, support=support, true_positive=true_positive, false_positive=false_positive, false_negative=false_negative,
                precision=ratio(true_positive, true_positive+false_positive), recall=ratio(true_positive, true_positive+false_negative),
                f1=ratio(2*true_positive, 2*true_positive+false_positive+false_negative))


def golden(rows, observations, correct):
    undefined = sum(row[key]["status"] == "UNDEFINED" for row in rows for key in ("precision", "recall", "f1"))
    return dict(schema_version=1, status="REVIEW_REQUIRED" if undefined else "METRICS_COMPUTED",
                scope="DECLARED_SINGLE_LABEL_CONFUSION_COUNTS_ONLY", orientation="EXPECTED_ROWS_PREDICTED_COLUMNS", **FLAGS,
                counts=dict(classes=len(rows), observations=observations, undefined_metrics=undefined), accuracy=ratio(correct, observations), classes=rows)


def default_result():
    return golden([metric("class_0", 10, 8, 1, 2), metric("class_1", 10, 9, 2, 1)], 20, 17)


def expanded_oracle(matrix, identifiers):
    # Enumerate only small fictional observations; no row/column-sum implementation.
    observations = [(expected, predicted) for expected, row in enumerate(matrix) for predicted, repetitions in enumerate(row) for _ in range(repetitions)]
    rows = []
    for index, identifier in enumerate(identifiers):
        support = sum(expected == index for expected, predicted in observations)
        tp = sum(expected == predicted == index for expected, predicted in observations)
        fp = sum(predicted == index and expected != index for expected, predicted in observations)
        fn = sum(expected == index and predicted != index for expected, predicted in observations)
        rows.append(metric(identifier, support, tp, fp, fn))
    return golden(rows, len(observations), sum(expected == predicted for expected, predicted in observations))


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="metrics-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied single script"
        self.runtime.mkdir()
        self.source = self.runtime / "evaluation_metrics.py"
        self.source.write_bytes((ROOT / "evaluation_metrics.py").read_bytes())
        self.runtime_hash = sha(self.source.read_bytes())
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def fixture(self, value=None, *, raw=None):
        self.serial += 1
        path = self.work / ("FICTIONAL_PRIVATE_COUNTS_" + str(self.serial) + ".json")
        path.write_bytes(json.dumps(counts() if value is None else value).encode("utf-8") if raw is None else raw)
        return path

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import evaluation_metrics as tool\nevents = []\n" + textwrap.dedent(body)
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
            self.assertEqual(set(value), {"schema_version", "status", "scope", "orientation", "counts", "accuracy", "classes", *FLAGS})
            self.assertTrue(all(value[key] is False for key in FLAGS))
            for row in value["classes"]:
                self.assertEqual(set(row), {"id", "support", "true_positive", "false_positive", "false_negative", "precision", "recall", "f1"})
                for key in ("precision", "recall", "f1"):
                    self.assertEqual(set(row[key]), {"status", "numerator", "denominator"})
                    self.assertIs(type(row[key]["denominator"]), int)
                    self.assertTrue(row[key]["numerator"] is None or type(row[key]["numerator"]) is int)
        return value

    def run_cli(self, source=None, **options):
        return self.process("--counts", source or self.fixture(), **options)

    def check(self, value, wanted, *, raw=None, script=None):
        self.assertEqual(self.run_cli(self.fixture(value, raw=raw), expected=int(wanted["status"] == "REVIEW_REQUIRED"), script=script), wanted)
        return wanted

    def symlink(self, path, target):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_EVALUATION_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_asymmetric_orientation_has_complete_exact_json_and_no_result_files(self):
        self.check(counts(), default_result())
        self.assertEqual({path.name for path in self.work.iterdir()}, {self.runtime.name, "FICTIONAL_PRIVATE_COUNTS_1.json"})
        self.check(counts([[3, 1, 0], [2, 4, 1], [0, 2, 5]], ["alpha", "beta", "gamma"]), golden([
            metric("alpha", 4, 3, 2, 1), metric("beta", 7, 4, 3, 3), metric("gamma", 7, 5, 1, 2)], 18, 12))

    def test_perfect_single_and_multiple_classes_preserve_unreduced_integer_pairs(self):
        self.check(counts([[3]], ["only"]), golden([metric("only", 3, 3, 0, 0)], 3, 3))
        self.check(counts([[3, 0], [0, 2]], ["first", "second"]), golden([
            metric("first", 3, 3, 0, 0), metric("second", 2, 2, 0, 0)], 5, 5))
        result = self.run_cli(self.fixture(counts([[3]])))
        self.assertEqual(result["classes"][0]["f1"], dict(status="DEFINED", numerator=6, denominator=6))

    def test_zero_true_positives_can_be_defined_without_quality_threshold_or_review(self):
        self.check(counts([[0, 2], [3, 0]], ["a", "b"]), golden([
            metric("a", 2, 0, 3, 2), metric("b", 3, 0, 2, 3)], 5, 0))

    def test_no_predictions_has_undefined_precision_but_defined_recall_and_direct_f1(self):
        self.check(counts([[0, 1], [0, 1]], ["a", "b"]), golden([
            metric("a", 1, 0, 0, 1), metric("b", 1, 1, 1, 0)], 2, 1))

    def test_no_expected_observations_has_undefined_recall_but_defined_direct_f1(self):
        self.check(counts([[0, 0], [1, 1]], ["a", "b"]), golden([
            metric("a", 0, 0, 1, 0), metric("b", 2, 1, 0, 1)], 2, 1))

    def test_absent_classes_have_three_undefined_ratios_and_combined_count_is_per_metric(self):
        self.check(counts([[1, 0], [0, 0]], ["present", "absent"]), golden([
            metric("present", 1, 1, 0, 0), metric("absent", 0, 0, 0, 0)], 1, 1))
        self.check(counts([[0, 1, 0], [0, 0, 0], [0, 0, 0]], ["no_prediction", "no_support", "absent"]), golden([
            metric("no_prediction", 1, 0, 0, 1), metric("no_support", 0, 0, 1, 0), metric("absent", 0, 0, 0, 0)], 1, 0))

    def test_transposition_swaps_precision_recall_and_false_counts_without_changing_f1_accuracy(self):
        original = self.run_cli(self.fixture(counts()))
        transposed = self.run_cli(self.fixture(counts([[8, 1], [2, 9]])))
        self.assertEqual(transposed, golden([metric("class_0", 9, 8, 2, 1), metric("class_1", 11, 9, 1, 2)], 20, 17))
        self.assertEqual(original["accuracy"], transposed["accuracy"])
        for before, after in zip(original["classes"], transposed["classes"]):
            self.assertEqual(before["precision"], after["recall"])
            self.assertEqual(before["recall"], after["precision"])
            self.assertEqual(before["f1"], after["f1"])
            self.assertEqual((before["false_positive"], before["false_negative"]), (after["false_negative"], after["false_positive"]))

    def test_class_permutation_moves_both_matrix_axes_and_preserves_declared_result_order(self):
        matrix = [[3, 1, 0], [2, 4, 1], [0, 2, 5]]
        identifiers = ["zeta", "alpha", "middle"]
        self.check(counts(matrix, identifiers), expanded_oracle(matrix, identifiers))
        order = [2, 0, 1]
        permuted = [[matrix[row][column] for column in order] for row in order]
        names = [identifiers[index] for index in order]
        self.check(counts(permuted, names), expanded_oracle(permuted, names))

    def test_seeded_small_counts_match_independent_expanded_observation_complete_reports(self):
        selected = random.Random(8517)
        for size in range(1, 5):
            for iteration in range(4):
                matrix = [[selected.randrange(3) for _ in range(size)] for _ in range(size)]
                if not any(any(row) for row in matrix): matrix[0][0] = 1
                names = ["sample_"+str(index) for index in range(size)]
                self.check(counts(matrix, names), expanded_oracle(matrix, names))

    def test_scaling_preserves_raw_numerators_and_denominators_without_reduction_or_floats(self):
        self.check(counts([[16, 4], [2, 18]]), golden([
            metric("class_0", 20, 16, 2, 4), metric("class_1", 20, 18, 4, 2)], 40, 34))
        before, after = default_result(), self.run_cli(self.fixture(counts([[16, 4], [2, 18]])))
        for old, new in [(before["accuracy"], after["accuracy"])]+[(a[key], b[key]) for a, b in zip(before["classes"], after["classes"]) for key in ("precision", "recall", "f1")]:
            self.assertEqual(new, dict(status="DEFINED", numerator=old["numerator"]*2, denominator=old["denominator"]*2))

    def test_root_schema_class_ids_and_matrix_shapes_are_exact_without_corpus_or_model_inputs(self):
        for value in (None, [], {}, dict(counts(), schema_version=True), dict(counts(), model="FICTIONAL_PRIVATE_MODEL"), dict(counts(), classes=[]), dict(counts(), classes="sample")):
            self.run_cli(self.fixture(raw=json.dumps(value).encode()), expected=2, code="COUNTS_SCHEMA_INVALID")
        for value in (True, 1, "Upper", "1first", "has space", "é", "a"*41):
            self.run_cli(self.fixture(counts([[1]], [value])), expected=2, code="CLASS_ID_INVALID")
        self.run_cli(self.fixture(counts([[1, 0], [0, 1]], ["same", "same"])), expected=2, code="DUPLICATE_CLASS_ID")
        for matrix in ([], [1], [[1, 2]], [[1], [0]], [[1, 0], [0]]):
            self.run_cli(self.fixture(counts(matrix, ["only"])), expected=2, code="MATRIX_SHAPE_INVALID")
        for identifier in ("a", "a"*40):
            self.check(counts([[1]], [identifier]), golden([metric(identifier, 1, 1, 0, 0)], 1, 1))

    def test_cells_are_plain_nonnegative_bounded_integers_and_zero_total_is_invalid(self):
        for value in (None, True, False, 1.0, "1", [], {}, -1, 1000000001):
            self.run_cli(self.fixture(counts([[value]])), expected=2, code="CELL_COUNT_INVALID")
        self.check(counts([[1000000000]], ["only"]), golden([metric("only", 1000000000, 1000000000, 0, 0)], 1000000000, 1000000000))
        self.run_cli(self.fixture(counts([[0, 0], [0, 0]])), expected=2, code="TOTAL_COUNT_INVALID")

    def test_32_classes_and_exact_trillion_total_have_separate_overflow_refusals(self):
        matrix = [[1000000000 if row*32+column < 1000 else 0 for column in range(32)] for row in range(32)]
        rows = [metric("class_"+str(index), 32000000000 if index < 31 else 8000000000,
                       1000000000 if index < 31 else 0,
                       31000000000 if index < 8 or index == 31 else 30000000000,
                       31000000000 if index < 31 else 8000000000) for index in range(32)]
        self.check(counts(matrix), golden(rows, 1000000000000, 31000000000))
        matrix[-1][-1] = 1
        self.run_cli(self.fixture(counts(matrix)), expected=2, code="TOTAL_COUNT_INVALID")
        self.run_cli(self.fixture(counts([[1 if row == column == 0 else 0 for column in range(33)] for row in range(33)])), expected=2, code="COUNTS_SCHEMA_INVALID")

    def test_exact_64_kib_bom_json_duplicates_constants_encoding_and_extra_byte(self):
        raw = b"\xef\xbb\xbf"+json.dumps(counts()).encode()
        exact = raw+b" "*(65536-len(raw))
        self.assertEqual(self.run_cli(self.fixture(raw=exact)), default_result())
        self.run_cli(self.fixture(raw=exact+b" "), expected=2, code="INPUT_SIZE_LIMIT")
        for raw, code in [(b'{"private":1,"private":2}', "DUPLICATE_JSON_KEY"), (b'{"private":NaN}', "NONSTANDARD_JSON"),
                          (b'{"private":Infinity}', "NONSTANDARD_JSON"), (b'{"private":-Infinity}', "NONSTANDARD_JSON"),
                          (b"\xff", "INPUT_OR_COUNTS_FAILED"), (b"{", "INPUT_OR_COUNTS_FAILED"), (b"{} trailing", "INPUT_OR_COUNTS_FAILED")]:
            self.run_cli(self.fixture(raw=raw), expected=2, code=code)

    def test_five_false_flags_and_output_metadata_omit_raw_matrix_without_anonymity_claim(self):
        result = self.run_cli(self.fixture())
        self.assertEqual(result, default_result())
        self.assertEqual(set(result["counts"]), {"classes", "observations", "undefined_metrics"})
        first, second = result["classes"]
        reconstructed = [[first["true_positive"], first["false_negative"]], [first["false_positive"], second["true_positive"]]]
        self.assertEqual(reconstructed, [[8, 2], [1, 9]])
        self.run_cli(self.fixture(dict(counts(), corpus="FICTIONAL_PRIVATE_CORPUS")), expected=2, code="COUNTS_SCHEMA_INVALID")

    def test_help_version_arguments_paths_and_rejected_report_option_have_fixed_private_output(self):
        for argument in ("--help", "--version"):
            self.assertIn("evaluation-metrics-calculator", self.process(argument, json_output=False))
        for arguments in ((), ("--count", "FICTIONAL_PRIVATE_MISSING"), ("--cou", "FICTIONAL_PRIVATE_MISSING"),
                          ("--counts", "x", "--report", "FICTIONAL_PRIVATE_OUTPUT")):
            self.process(*arguments, expected=2, code="ARGUMENTS_INVALID")
        self.run_cli(self.work/"FICTIONAL_PRIVATE_MISSING.json", expected=2, code="INPUT_OR_COUNTS_FAILED")
        self.run_cli(self.runtime, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        for path in (self.work/"CON.json", self.work/"file:stream", self.work/".."/"escape.json"):
            self.run_cli(path, expected=2, code="INPUT_PATH_INVALID")
        source = self.fixture()
        self.assertEqual(self.run_cli(source.name), default_result())

    def test_only_selected_counts_are_read_without_model_network_process_clock_or_environment_activity(self):
        source = self.fixture()
        (self.work/"unrelated-corpus.txt").write_bytes(b"FICTIONAL_PRIVATE_CORPUS_NEVER_OPEN")
        (self.work/"prior-capture.txt").write_bytes(b"Fictional prior capture must remain unchanged\n")
        script = self.wrapper("""
            selected = Path(INPUT_VALUE)
            environment_before = dict(os.environ)
            original = os.open
            def opened(path, *args, **kwargs):
                assert Path(path) == selected, 'Unselected model, corpus or environment file opened'
                events.append(True)
                return original(path, *args, **kwargs)
            def forbidden(*args, **kwargs):
                raise AssertionError('Model, network, process, clock or environment activity attempted')
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
        self.run_cli(source, script=script, expected=2, code="INPUT_OR_COUNTS_FAILED")

    def test_native_symlink_input_leaf_and_dangling_are_refused(self):
        source = self.fixture()
        alias = self.work / "linked-counts.json"
        self.symlink(alias, source)
        self.run_cli(alias, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        absent = self.work / "owned-absent-target.json"
        dangling = self.work / "dangling-counts.json"
        self.symlink(dangling, absent)
        self.run_cli(dangling, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        self.assertFalse(absent.exists())

    def test_native_symlink_input_parent_is_refused(self):
        source = self.fixture()
        target = self.work / "owned-counts-parent"
        target.mkdir()
        moved = target / "counts.json"
        source.rename(moved)
        alias = self.work / "linked-parent"
        self.symlink(alias, target)
        self.run_cli(alias / "counts.json", expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_input_parent_is_refused(self):
        source = self.fixture()
        target = self.work / "owned-counts-parent"
        target.mkdir()
        moved = target / "counts.json"
        source.rename(moved)
        alias = self.work / "junction-parent"
        self.junction(alias, target)
        self.run_cli(alias / "counts.json", expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

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
        self.run_cli(source, script=script, expected=2, code="INPUT_OR_COUNTS_FAILED")
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
