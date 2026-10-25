"""Fictional confusion counts with an independent expanded-observation oracle."""

from collections import Counter
import contextlib
import copy
from fractions import Fraction
import io
import json
import os
from pathlib import Path
import random
import socket
import stat
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_public_additions import Fixture, load, ROOT


checker = load(
    "evaluation_metrics_calculator",
    "tools/evaluation-metrics-calculator/evaluation_metrics.py",
)


def counts(matrix, classes=None):
    return {
        "schema_version": 1,
        "classes": list(classes)
        if classes is not None
        else ["class_" + str(index) for index in range(len(matrix))],
        "counts": matrix,
    }


def changed_stat(info, **values):
    fields = {
        name: getattr(info, name)
        for name in dir(info)
        if name.startswith("st_") and not callable(getattr(info, name))
    }
    fields.update(values)
    return SimpleNamespace(**fields)


class MetricsFixture(Fixture):
    def metadata(self, value=None, *, raw=None, name="fictional-counts.json"):
        source = self.parent / name
        source.write_bytes(json.dumps(value).encode("utf-8") if raw is None else raw)
        return source

    def score(self, actual, numerator, denominator):
        if denominator:
            self.assertEqual(
                actual,
                {
                    "status": "DEFINED",
                    "numerator": numerator,
                    "denominator": denominator,
                },
            )
            self.assertIs(type(actual["numerator"]), int)
            self.assertIs(type(actual["denominator"]), int)
            self.assertEqual(
                Fraction(actual["numerator"], actual["denominator"]),
                Fraction(numerator, denominator),
            )
        else:
            self.assertEqual(
                actual, {"status": "UNDEFINED", "numerator": None, "denominator": 0}
            )
            self.assertIs(type(actual["denominator"]), int)

    def expanded_oracle(self, matrix, result):
        # Expand only small fictional matrices. This does not reuse matrix-sum
        # implementation logic or execute a model to obtain observations.
        observations = [
            (expected, predicted)
            for expected, row in enumerate(matrix)
            for predicted, repetitions in enumerate(row)
            for _ in range(repetitions)
        ]
        supports = Counter(expected for expected, _ in observations)
        predictions = Counter(predicted for _, predicted in observations)
        correct = Counter(
            expected for expected, predicted in observations if expected == predicted
        )
        false_positives = Counter(
            predicted for expected, predicted in observations if expected != predicted
        )
        false_negatives = Counter(
            expected for expected, predicted in observations if expected != predicted
        )
        self.assertEqual(result["counts"]["observations"], len(observations))
        self.score(result["accuracy"], sum(correct.values()), len(observations))
        undefined = 0
        for index, row in enumerate(result["classes"]):
            tp, fp, fn = correct[index], false_positives[index], false_negatives[index]
            self.assertEqual(
                (
                    row["support"],
                    row["true_positive"],
                    row["false_positive"],
                    row["false_negative"],
                ),
                (supports[index], tp, fp, fn),
            )
            self.score(row["precision"], tp, predictions[index])
            self.score(row["recall"], tp, supports[index])
            self.score(row["f1"], 2 * tp, 2 * tp + fp + fn)
            undefined += sum(
                row[name]["status"] == "UNDEFINED"
                for name in ("precision", "recall", "f1")
            )
        self.assertEqual(result["counts"]["undefined_metrics"], undefined)
        self.assertEqual(
            result["status"], "REVIEW_REQUIRED" if undefined else "METRICS_COMPUTED"
        )

    def invoke(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = checker.main(list(map(str, args)))
        return code, output.getvalue(), errors.getvalue()

    def reader_failure_traceback(self, source):
        try:
            checker.read_input_json(source)
        except checker.ContractError as error:
            self.assertTrue(error.__suppress_context__)
            return "".join(traceback.format_exception(error))
        self.fail("Expected a fixed input error")


class MetricsSchemaTests(MetricsFixture):
    def test_parse_deep_copies_classes_and_count_rows_without_mutation(self):
        data = counts([[3, 1], [2, 4]])
        before = copy.deepcopy(data)
        parsed = checker.parse_counts(data)
        self.assertEqual(parsed, data)
        self.assertIsNot(parsed, data)
        self.assertIsNot(parsed["classes"], data["classes"])
        self.assertIsNot(parsed["counts"], data["counts"])
        for actual, original in zip(parsed["counts"], data["counts"]):
            self.assertIsNot(actual, original)
        parsed["classes"][0] = "changed"
        parsed["counts"][0][0] = 1
        self.assertEqual(data, before)
        checker.calculate_metrics(data)
        self.assertEqual(data, before)

    def test_root_schema_is_exact_and_raw_records_models_or_outputs_are_not_inputs(
        self,
    ):
        valid = counts([[1]])
        invalid = [None, [], "fictional", {}]
        invalid.extend(
            {**valid, key: "fictional-sensitive-canary"}
            for key in (
                "model",
                "records",
                "predictions",
                "ground_truth",
                "api_url",
                "output",
            )
        )
        invalid.extend(
            {key: value for key, value in valid.items() if key != removed}
            for removed in valid
        )
        invalid.extend(
            {**valid, "schema_version": value} for value in (None, True, 1.0, "1", 0, 2)
        )
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(checker.ContractError):
                checker.parse_counts(data)

    def test_classes_are_unique_bounded_neutral_id_tokens(self):
        for classes in (None, {}, "fictional", (), [], ["a"] * 2):
            with (
                self.subTest(classes=classes),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_counts(
                    {"schema_version": 1, "classes": classes, "counts": [[1]]}
                )
        for identifier in (
            None,
            True,
            1,
            [],
            {},
            "",
            "A",
            "1class",
            "a b",
            "a/b",
            "a" * 41,
            "café",
        ):
            with (
                self.subTest(identifier=identifier),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_counts(counts([[1]], [identifier]))
        for identifier in ("a", "a" * 40, "fictional_class-1"):
            self.assertEqual(
                checker.parse_counts(counts([[1]], [identifier]))["classes"],
                [identifier],
            )

    def test_matrix_is_square_and_uses_plain_list_rows(self):
        invalid = (
            None,
            {},
            "fictional",
            (),
            [],
            [1],
            [(1,)],
            [[1, 2]],
            [[1], [2]],
            [[1, 0], [0]],
            [[1, 0], [0, 1], [0, 0]],
        )
        for matrix in invalid:
            with self.subTest(matrix=matrix), self.assertRaises(checker.ContractError):
                checker.parse_counts(
                    {"schema_version": 1, "classes": ["one"], "counts": matrix}
                )
        for matrix in ([[1, 0], [0]], [[1], [0, 1]]):
            with self.subTest(matrix=matrix), self.assertRaises(checker.ContractError):
                checker.parse_counts(counts(matrix, ["one", "two"]))

    def test_cells_are_exact_nonnegative_bounded_integers(self):
        for value in (None, True, False, 1.0, "1", [], {}, -1, 1000000001):
            with self.subTest(value=value), self.assertRaises(checker.ContractError):
                checker.parse_counts(counts([[value]]))
        self.assertEqual(
            checker.parse_counts(counts([[1000000000]]))["counts"], [[1000000000]]
        )
        with self.assertRaises(checker.ContractError):
            checker.parse_counts(counts([[0, 0], [0, 0]]))

    def test_class_and_total_count_limits_include_exact_maximum(self):
        maximum = [
            [1000000000 if row * 32 + column < 1000 else 0 for column in range(32)]
            for row in range(32)
        ]
        result = checker.calculate_metrics(counts(maximum))
        self.assertEqual(result["counts"]["classes"], 32)
        self.assertEqual(result["counts"]["observations"], 1000000000000)
        self.score(result["accuracy"], 31000000000, 1000000000000)
        over_total = copy.deepcopy(maximum)
        over_total[-1][-1] = 1
        with self.assertRaises(checker.ContractError):
            checker.parse_counts(counts(over_total))
        too_many = [
            [int(row == 0 and column == 0) for column in range(33)] for row in range(33)
        ]
        with self.assertRaises(checker.ContractError):
            checker.parse_counts(counts(too_many))


class MetricArithmeticTests(MetricsFixture):
    def test_asymmetric_expected_rows_predicted_columns_match_fraction_oracle(self):
        matrix = [[3, 1, 0], [2, 4, 1], [0, 2, 5]]
        result = checker.calculate_metrics(counts(matrix, ["alpha", "beta", "gamma"]))
        self.expanded_oracle(matrix, result)
        self.score(result["accuracy"], 12, 18)
        self.assertEqual([row["support"] for row in result["classes"]], [4, 7, 7])
        self.score(result["classes"][0]["precision"], 3, 5)
        self.score(result["classes"][0]["recall"], 3, 4)
        self.score(result["classes"][0]["f1"], 6, 9)

    def test_seeded_small_matrices_match_expanded_observation_oracle(self):
        generator = random.Random(314159)
        for size in range(1, 6):
            for iteration in range(10):
                matrix = [
                    [generator.randrange(5) for _ in range(size)] for _ in range(size)
                ]
                if not any(any(row) for row in matrix):
                    matrix[0][0] = 1
                with self.subTest(size=size, iteration=iteration):
                    self.expanded_oracle(
                        matrix, checker.calculate_metrics(counts(matrix))
                    )

    def test_transpose_swaps_precision_recall_and_false_positive_negative(self):
        matrix = [[3, 1, 0], [2, 4, 1], [0, 2, 5]]
        original = checker.calculate_metrics(counts(matrix))
        transposed = checker.calculate_metrics(
            counts([list(row) for row in zip(*matrix)])
        )
        self.assertEqual(original["accuracy"], transposed["accuracy"])
        for before, after in zip(original["classes"], transposed["classes"]):
            self.assertEqual(before["id"], after["id"])
            self.assertEqual(before["true_positive"], after["true_positive"])
            self.assertEqual(before["false_positive"], after["false_negative"])
            self.assertEqual(before["false_negative"], after["false_positive"])
            self.assertEqual(before["precision"], after["recall"])
            self.assertEqual(before["recall"], after["precision"])
            self.assertEqual(before["f1"], after["f1"])
            self.assertEqual(
                after["support"], before["true_positive"] + before["false_positive"]
            )

    def test_single_class_perfect_scores_remain_unreduced_raw_formulas(self):
        result = checker.calculate_metrics(counts([[7]]))
        self.assertEqual(result["status"], "METRICS_COMPUTED")
        self.score(result["accuracy"], 7, 7)
        self.score(result["classes"][0]["precision"], 7, 7)
        self.score(result["classes"][0]["recall"], 7, 7)
        self.score(result["classes"][0]["f1"], 14, 14)
        self.assertEqual(result["counts"]["undefined_metrics"], 0)

    def test_zero_true_positives_have_defined_zero_scores_without_quality_inference(
        self,
    ):
        matrix = [[0, 2], [3, 0]]
        result = checker.calculate_metrics(counts(matrix))
        self.expanded_oracle(matrix, result)
        self.score(result["accuracy"], 0, 5)
        self.score(result["classes"][0]["precision"], 0, 3)
        self.score(result["classes"][0]["recall"], 0, 2)
        self.score(result["classes"][0]["f1"], 0, 5)
        self.assertEqual(result["status"], "METRICS_COMPUTED")

    def test_no_predictions_means_undefined_precision_but_defined_recall_and_direct_f1(
        self,
    ):
        matrix = [[2, 0], [3, 0]]
        result = checker.calculate_metrics(counts(matrix))
        self.expanded_oracle(matrix, result)
        absent_predictions = result["classes"][1]
        self.score(absent_predictions["precision"], 0, 0)
        self.score(absent_predictions["recall"], 0, 3)
        self.score(absent_predictions["f1"], 0, 3)
        self.assertEqual(result["counts"]["undefined_metrics"], 1)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_no_expected_observations_means_undefined_recall_but_direct_f1_defined(
        self,
    ):
        matrix = [[2, 3], [0, 0]]
        result = checker.calculate_metrics(counts(matrix))
        self.expanded_oracle(matrix, result)
        absent_expected = result["classes"][1]
        self.score(absent_expected["precision"], 0, 3)
        self.score(absent_expected["recall"], 0, 0)
        self.score(absent_expected["f1"], 0, 3)
        self.assertEqual(result["counts"]["undefined_metrics"], 1)

    def test_entirely_absent_class_has_three_undefined_metrics(self):
        matrix = [[5, 0], [0, 0]]
        result = checker.calculate_metrics(counts(matrix))
        self.expanded_oracle(matrix, result)
        row = result["classes"][1]
        self.assertEqual(
            (
                row["support"],
                row["true_positive"],
                row["false_positive"],
                row["false_negative"],
            ),
            (0, 0, 0, 0),
        )
        for metric in ("precision", "recall", "f1"):
            self.score(row[metric], 0, 0)
        self.assertEqual(result["counts"]["undefined_metrics"], 3)
        self.score(result["accuracy"], 5, 5)

    def test_combined_undefined_cases_count_each_metric_independently(self):
        matrix = [[2, 0, 0], [3, 0, 0], [0, 0, 0]]
        result = checker.calculate_metrics(counts(matrix))
        self.expanded_oracle(matrix, result)
        self.assertEqual(
            result["counts"], {"classes": 3, "observations": 5, "undefined_metrics": 4}
        )


class MetricsPrivacyTests(MetricsFixture):
    def test_report_is_declared_order_fixed_metadata_without_matrix_or_extra_fields(
        self,
    ):
        data = counts([[3, 1], [2, 4]], ["zulu", "alpha"])
        result = checker.calculate_metrics(data)
        self.assertEqual(
            set(result),
            {
                "schema_version",
                "status",
                "scope",
                "orientation",
                "model_executed",
                "network_probed",
                "input_modified",
                "ground_truth_verified",
                "predictions_verified",
                "counts",
                "accuracy",
                "classes",
            },
        )
        self.assertEqual(result["scope"], "DECLARED_SINGLE_LABEL_CONFUSION_COUNTS_ONLY")
        self.assertEqual(result["orientation"], "EXPECTED_ROWS_PREDICTED_COLUMNS")
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual([row["id"] for row in result["classes"]], ["zulu", "alpha"])
        self.assertEqual(
            result["counts"], {"classes": 2, "observations": 10, "undefined_metrics": 0}
        )
        for row in result["classes"]:
            self.assertEqual(
                set(row),
                {
                    "id",
                    "support",
                    "true_positive",
                    "false_positive",
                    "false_negative",
                    "precision",
                    "recall",
                    "f1",
                },
            )
        for flag in (
            "model_executed",
            "network_probed",
            "input_modified",
            "ground_truth_verified",
            "predictions_verified",
        ):
            self.assertIs(result[flag], False)
        self.assertIsInstance(result["counts"], dict)
        raw = json.dumps(result)
        self.assertNotIn(json.dumps(data["counts"]), raw)
        self.assertNotIn(str(self.parent), raw)
        self.assertNotIn('"matrix"', raw)
        self.assertNotIn('"records"', raw)

    def test_calculation_has_no_model_network_process_clock_or_target_file_activity(
        self,
    ):
        data = counts([[3, 1], [2, 4]])
        before = copy.deepcopy(data)
        guards = (
            patch.object(socket, "socket", side_effect=AssertionError("No sockets")),
            patch.object(
                socket, "create_connection", side_effect=AssertionError("No connection")
            ),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("No DNS")),
            patch("subprocess.Popen", side_effect=AssertionError("No model execution")),
            patch("subprocess.run", side_effect=AssertionError("No model execution")),
            patch.object(os, "system", side_effect=AssertionError("No shell")),
            patch.object(os, "execv", side_effect=AssertionError("No exec")),
            patch("builtins.open", side_effect=AssertionError("No records read")),
            patch("io.open", side_effect=AssertionError("No records read")),
            patch.object(os, "open", side_effect=AssertionError("No records read")),
            patch.object(os, "stat", side_effect=AssertionError("No target metadata")),
            patch.object(os, "lstat", side_effect=AssertionError("No target metadata")),
            patch.object(os, "listdir", side_effect=AssertionError("No scanning")),
            patch.object(os, "scandir", side_effect=AssertionError("No scanning")),
            patch.object(os, "remove", side_effect=AssertionError("No deletion")),
            patch.object(os, "unlink", side_effect=AssertionError("No deletion")),
            patch.object(os, "rename", side_effect=AssertionError("No mutation")),
            patch.object(os, "replace", side_effect=AssertionError("No mutation")),
            patch.object(
                os, "getenv", side_effect=AssertionError("No environment lookup")
            ),
            patch.object(time, "time", side_effect=AssertionError("No clock")),
            patch.object(
                time, "localtime", side_effect=AssertionError("No local clock")
            ),
            patch.object(time, "gmtime", side_effect=AssertionError("No UTC clock")),
        )
        with contextlib.ExitStack() as stack:
            for guard in guards:
                stack.enter_context(guard)
            result = checker.calculate_metrics(data)
        self.assertEqual(result["status"], "METRICS_COMPUTED")
        self.assertEqual(data, before)


class GuardedInputTests(MetricsFixture):
    def test_utf8_bom_exact_byte_boundary_and_preserved_input(self):
        data = counts([[1]])
        raw = b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8")
        raw += b" " * (65536 - len(raw))
        source = self.metadata(raw=raw)
        self.assertEqual(checker.read_input_json(source), data)
        self.assertEqual(source.read_bytes(), raw)
        source.write_bytes(raw + b" ")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(source)

    def test_duplicate_json_keys_nonfinite_values_and_invalid_encoding(self):
        samples = [
            b'{"classes":[],"classes":[]}',
            b'{"counts":{"fictional":1,"fictional":2}}',
            b"{",
            b"\xff",
            b"{} trailing",
        ]
        samples.extend(
            b'{"fictional":' + value + b"}"
            for value in (b"NaN", b"Infinity", b"-Infinity")
        )
        for raw in samples:
            source = self.metadata(raw=raw)
            with self.subTest(raw=raw), self.assertRaises(checker.ContractError):
                checker.read_input_json(source)

    def test_missing_nonfile_root_and_unsafe_paths_are_refused(self):
        for path in (
            self.parent / "missing.json",
            self.root,
            Path(self.parent.anchor),
            str(self.parent / "fictional/../counts.json"),
            r"\\fictional-host\share\counts.json",
            "//fictional-host/share/counts.json",
            "Q:fictional-counts.json",
            "NUL",
            "CON",
        ):
            with self.subTest(path=str(path)), self.assertRaises(checker.ContractError):
                checker.read_input_json(path)

    def test_reader_does_not_enumerate_directories(self):
        source = self.metadata(counts([[1]]))
        with (
            patch.object(os, "listdir", side_effect=AssertionError("No inventory")),
            patch.object(os, "scandir", side_effect=AssertionError("No inventory")),
        ):
            self.assertEqual(checker.read_input_json(source), counts([[1]]))

    def test_unsafe_input_and_ancestor_metadata_are_refused_before_open(self):
        source = self.metadata(counts([[1]]))
        original = Path.lstat
        for selected, values in (
            (source, {"st_file_attributes": 0x400}),
            (source, {"st_nlink": 2}),
            (source, {"st_mode": stat.S_IFIFO | 0o600}),
            (source, {"st_ino": 0}),
            (self.parent, {"st_file_attributes": 0x400}),
            (self.parent, {"st_ino": 0}),
        ):

            def unsafe(path):
                info = original(path)
                return changed_stat(info, **values) if path == selected else info

            with self.subTest(selected=selected.name, values=values):
                with (
                    patch.object(Path, "lstat", unsafe),
                    patch.object(
                        os, "open", side_effect=AssertionError("Unsafe input opened")
                    ),
                ):
                    with self.assertRaises(checker.ContractError):
                        checker.read_input_json(source)

    def test_opened_and_post_read_metadata_changes_are_refused(self):
        source = self.metadata(counts([[1]]))
        original = os.fstat
        for after_only in (False, True):
            observations = 0

            def changed(descriptor):
                nonlocal observations
                observations += 1
                info = original(descriptor)
                return (
                    changed_stat(info, st_mtime_ns=info.st_mtime_ns + 1)
                    if not after_only or observations > 1
                    else info
                )

            with (
                self.subTest(after_only=after_only),
                patch.object(os, "fstat", changed),
                self.assertRaises(checker.ContractError),
            ):
                checker.read_input_json(source)

    def test_path_or_ancestor_replacement_after_read_is_refused(self):
        source = self.metadata(counts([[1]]))
        original = Path.lstat
        for selected in (source, self.parent):
            observations = 0

            def changed(path):
                nonlocal observations
                info = original(path)
                if path == selected:
                    observations += 1
                    if observations > 1:
                        return changed_stat(info, st_ino=info.st_ino + 1)
                return info

            with (
                self.subTest(selected=selected.name),
                patch.object(Path, "lstat", changed),
                self.assertRaises(checker.ContractError),
            ):
                checker.read_input_json(source)

    def test_missing_path_and_native_permission_tracebacks_hide_canaries(self):
        source = self.parent / "fictional-missing-path-canary.json"
        formatted = self.reader_failure_traceback(source)
        for value in (str(source), source.name, "FileNotFoundError"):
            self.assertNotIn(value, formatted)
        source = self.metadata(counts([[1]]), name="fictional-input-path-canary.json")
        message = "fictional-sensitive-native-canary"
        original = Path.lstat

        def denied(path):
            if path == source:
                raise PermissionError(13, message, str(source))
            return original(path)

        with patch.object(Path, "lstat", denied):
            formatted = self.reader_failure_traceback(source)
        for value in (str(source), source.name, message, "PermissionError"):
            self.assertNotIn(value, formatted)

    def test_unicode_json_and_recursion_tracebacks_hide_native_messages(self):
        source = self.metadata(counts([[1]]), name="fictional-decoder-path-canary.json")
        canary = "fictional-sensitive-decoder-canary"
        errors = (
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, canary),
            json.JSONDecodeError(canary, "{}", 0),
            RecursionError(canary),
        )
        for native_error in errors:
            with self.subTest(error_type=type(native_error).__name__):
                with patch.object(checker.json, "loads", side_effect=native_error):
                    formatted = self.reader_failure_traceback(source)
                for value in (
                    str(source),
                    source.name,
                    canary,
                    type(native_error).__name__,
                ):
                    self.assertNotIn(value, formatted)

    def test_native_symlink_input_is_refused(self):
        source = self.metadata(counts([[1]]))
        alias = self.parent / "fictional-alias.json"
        try:
            alias.symlink_to(source)
        except OSError:
            self.skipTest("Native symlink creation is unavailable")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(alias)

    def test_native_hardlink_input_is_refused(self):
        source = self.metadata(counts([[1]]))
        alias = self.parent / "fictional-alias.json"
        try:
            os.link(source, alias)
        except OSError:
            self.skipTest("Native hardlink creation is unavailable")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(source)


class MetricsCliTests(MetricsFixture):
    def test_cli_defined_and_undefined_exit_codes_preserve_input(self):
        for data, expected in ((counts([[1]]), 0), (counts([[5, 0], [0, 0]]), 1)):
            source = self.metadata(data)
            before = source.read_bytes()
            code, output, errors = self.invoke("--counts", source)
            self.assertEqual(code, expected, output + errors)
            self.assertEqual(errors, "")
            self.assertEqual(source.read_bytes(), before)
            self.assertNotIn(str(source), output)

    def test_cli_errors_have_fixed_schema_and_no_raw_values(self):
        canary = "fictional-sensitive-input-canary"
        source = self.metadata({**counts([[1]]), "private_value": canary})
        for args in (
            ("--counts", source),
            ("--counts", self.parent / "fictional-missing-path-canary.json"),
            ("--unknown", canary),
            ("--counts", source, "--report", self.parent / "must-not-create.json"),
        ):
            with self.subTest(args=args):
                code, output, errors = self.invoke(*args)
                self.assertEqual(code, 2, output + errors)
                result = json.loads(output)
                self.assertEqual(
                    set(result),
                    {
                        "status",
                        "code",
                        "model_executed",
                        "network_probed",
                        "input_modified",
                        "ground_truth_verified",
                        "predictions_verified",
                    },
                )
                self.assertEqual(result["status"], "ERROR")
                for flag in (
                    "model_executed",
                    "network_probed",
                    "input_modified",
                    "ground_truth_verified",
                    "predictions_verified",
                ):
                    self.assertIs(result[flag], False)
                for value in (
                    str(self.parent),
                    "fictional-missing-path-canary.json",
                    canary,
                    "Traceback",
                ):
                    self.assertNotIn(value, output + errors)
        self.assertFalse((self.parent / "must-not-create.json").exists())

    def test_abbreviated_flags_are_refused_before_input_reading(self):
        source = self.metadata(counts([[1]]))
        for argument in ("--count", "--cou"):
            with patch.object(
                checker,
                "read_input_json",
                side_effect=AssertionError("Unexpected input read"),
            ):
                code, output, errors = self.invoke(argument, source)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output)["status"], "ERROR")
            self.assertNotIn(str(source), output + errors)

    def test_interrupt_has_five_false_flags_and_exit_130(self):
        source = self.metadata(counts([[1]]))
        with patch.object(checker, "read_input_json", side_effect=KeyboardInterrupt):
            code, output, errors = self.invoke("--counts", source)
        self.assertEqual(code, 130)
        result = json.loads(output)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["code"], "INTERRUPTED")
        self.assertEqual(
            set(result),
            {
                "status",
                "code",
                "model_executed",
                "network_probed",
                "input_modified",
                "ground_truth_verified",
                "predictions_verified",
            },
        )
        for key, value in result.items():
            if key not in ("status", "code"):
                self.assertIs(value, False)
        self.assertEqual(errors, "")

    def test_help_and_version_are_static(self):
        for argument in ("--help", "--version"):
            output, errors = io.StringIO(), io.StringIO()
            with (
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(errors),
                self.assertRaises(SystemExit) as stopped,
            ):
                checker.main([argument])
            self.assertEqual(stopped.exception.code, 0)
            self.assertNotIn(str(ROOT), output.getvalue() + errors.getvalue())

    def test_actual_cli_is_stdout_only_and_preserves_fictional_fixture_files(self):
        source = self.metadata(counts([[3, 1], [2, 4]]))
        canary_file = self.write(
            "fictional-not-a-record-input.txt", "Fictional bytes remain unchanged.\n"
        )
        preserved = {path: path.read_bytes() for path in (source, canary_file)}
        names_before = {path.name for path in self.parent.iterdir()}
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/evaluation-metrics-calculator/evaluation_metrics.py"),
                "--counts",
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "METRICS_COMPUTED")
        self.score(result["accuracy"], 7, 10)
        self.assertEqual(process.stderr, "")
        for path, raw in preserved.items():
            self.assertEqual(path.read_bytes(), raw)
            self.assertNotIn(str(path), process.stdout)
        self.assertEqual({path.name for path in self.parent.iterdir()}, names_before)


if __name__ == "__main__":
    unittest.main()
