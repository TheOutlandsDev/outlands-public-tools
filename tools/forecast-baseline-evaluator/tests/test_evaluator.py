"""Fictional series only; independent arithmetic and prefix visibility checks."""
from dataclasses import FrozenInstanceError
from fractions import Fraction
import hashlib
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import evaluator
from evaluator import Score, forecast, rolling_score
from ingestion import Batch, Issue, MAX_PERIOD, Point, ReferenceError, ingest_csv, ingest_jsonl
from demo import main, run_demo


def batch(*values, start=0, series="sample"):
    return ingest_jsonl("\n".join(json.dumps(dict(series=series, period=start+i, value=value))
                                 for i, value in enumerate(values)))


class ForecastTests(unittest.TestCase):
    def test_last_value_repeats_and_advances_periods(self):
        result = forecast(batch(2, 5, 9, start=10), horizon=3)
        self.assertEqual(result, tuple(Point("sample", period, 9) for period in (13, 14, 15)))

    def test_mean_uses_only_observed_trailing_window_and_stays_fixed(self):
        result = forecast(batch(99, 2, 8), method="mean", window=2, horizon=3)
        self.assertEqual([p.value for p in result], [5, 5, 5])

    def test_mean_whole_history_and_single_value_windows(self):
        self.assertEqual(forecast(batch(1, 2, 9), method="mean", window=3)[0].value, 4)
        self.assertEqual(forecast(batch(1, 2, 9), method="mean", window=1)[0].value, 9)

    def test_seasonal_repeats_last_complete_observed_cycle(self):
        result = forecast(batch(99, 1, 4, 7), method="seasonal", season=3, horizon=8)
        self.assertEqual([p.value for p in result], [1, 4, 7, 1, 4, 7, 1, 4])

    def test_season_one_matches_last(self):
        source = batch(-3, 2)
        self.assertEqual(forecast(source, method="seasonal", season=1), forecast(source))

    def test_maximum_horizon_and_period_boundary(self):
        result = forecast(batch(1, start=MAX_PERIOD-32), horizon=32)
        self.assertEqual((len(result), result[-1].period), (32, MAX_PERIOD))
        with self.assertRaisesRegex(ReferenceError, "FORECAST_PERIOD_LIMIT"):
            forecast(batch(1, start=MAX_PERIOD), horizon=1)

    def test_horizon_requires_bounded_non_boolean_integer(self):
        for value in (0, 33, -1, True, 1.0, "1", None):
            with self.subTest(value=value), self.assertRaisesRegex(ReferenceError, "FORECAST_PARAMETER_INVALID"):
                forecast(batch(1), horizon=value)

    def test_window_and_season_parameters_are_always_validated(self):
        for name in ("window", "season"):
            for value in (0, 257, True, 1.0, "2", None):
                with self.subTest(name=name, value=value), self.assertRaisesRegex(ReferenceError, "FORECAST_PARAMETER_INVALID"):
                    forecast(batch(1), **{name: value})

    def test_unknown_or_non_string_method_has_fixed_error(self):
        for value in ("FICTIONAL_DO_NOT_ECHO", "LAST", None, [], True):
            with self.subTest(kind=type(value).__name__), self.assertRaises(ReferenceError) as caught:
                forecast(batch(1), method=value)
            self.assertEqual(str(caught.exception), "FORECAST_METHOD_INVALID")

    def test_method_specific_insufficient_history_is_refused(self):
        for options in (dict(method="mean", window=3), dict(method="seasonal", season=3)):
            with self.assertRaisesRegex(ReferenceError, "FORECAST_HISTORY_REQUIRED"):
                forecast(batch(1, 2), **options)

    def test_empty_or_partial_batch_is_never_consumed(self):
        partial = ingest_jsonl('{"series":"sample","period":0,"value":1}\nnull')
        for source in (ingest_jsonl(""), partial, Batch((Point("sample", 0, 1),), (Issue(2, "ROW_SCHEMA_INVALID"),), 0)):
            with self.assertRaisesRegex(ReferenceError, "BATCH_REVIEW_REQUIRED"):
                forecast(source)

    def test_conflict_blocks_prediction_even_with_valid_retained_records(self):
        source = ingest_jsonl('{"series":"sample","period":0,"value":1}\n{"series":"sample","period":0,"value":2}')
        self.assertEqual(len(source.records), 1)
        with self.assertRaisesRegex(ReferenceError, "BATCH_REVIEW_REQUIRED"):
            forecast(source)

    def test_identical_duplicates_are_accepted_via_clean_gate(self):
        source = ingest_csv("series,period,value\nsample,0,2\nsample,0,2")
        self.assertEqual(source.duplicates, 1)
        self.assertEqual(forecast(source)[0], Point("sample", 1, 2))

    def test_gaps_mixed_series_reversed_and_duplicate_periods_are_refused(self):
        for points in ((Point("sample", 0, 1), Point("sample", 2, 2)),
                       (Point("sample", 0, 1), Point("other", 1, 2)),
                       (Point("sample", 1, 1), Point("sample", 0, 2)),
                       (Point("sample", 0, 1), Point("sample", 0, 1))):
            with self.subTest(points=points), self.assertRaisesRegex(ReferenceError, "FORECAST_ORDER_OR_GAP"):
                forecast(Batch(points, (), 0))

    def test_input_requires_batch_and_bounded_canonical_containers(self):
        point = Point("sample", 0, 1)
        for source in (None, (point,), [point], Batch([point], (), 0), Batch((point,), [], 0),
                       Batch((point,), (), True), Batch((point,), (), -1), Batch((point,)*257, (), 0), Batch((point,), (), 256)):
            with self.subTest(kind=type(source).__name__), self.assertRaisesRegex(ReferenceError, "FORECAST_BATCH_INVALID"):
                forecast(source)

    def test_points_and_mutated_numeric_fields_are_revalidated(self):
        with self.assertRaisesRegex(ReferenceError, "FORECAST_POINT_INVALID"):
            forecast(Batch((dict(series="sample", period=0, value=1),), (), 0))
        for value in (float("nan"), float("inf"), True, 1000000001):
            point = Point("sample", 0, 1)
            object.__setattr__(point, "value", value)
            with self.assertRaisesRegex(ReferenceError, "VALUE_INVALID"):
                forecast(Batch((point,), (), 0))

    def test_boundary_values_are_finite_with_canonical_zero(self):
        for value in (-1000000000, 1000000000, -0.0):
            for method in ("last", "mean", "seasonal"):
                predicted = forecast(batch(value), method=method, window=1)
                self.assertTrue(math.isfinite(predicted[0].value))
                self.assertEqual(predicted[0].value, value)
                if value == 0:
                    self.assertEqual(math.copysign(1, predicted[0].value), 1)

    def test_maximum_history_is_supported_without_truncation(self):
        source = batch(*range(256))
        self.assertEqual(forecast(source, method="mean", window=256)[0].value, 127.5)
        self.assertEqual(forecast(source, method="seasonal", season=256)[0].value, 0)

    def test_input_preservation_and_immutable_output(self):
        source = batch(1, 2, 3)
        before = repr(source)
        output = forecast(source)
        self.assertEqual(repr(source), before)
        self.assertIsInstance(output, tuple)
        with self.assertRaises(FrozenInstanceError):
            output[0].value = 99


class EvaluationTests(unittest.TestCase):
    def test_last_metrics_match_independent_exact_fraction_oracle(self):
        values = (2, 6, 3, 12, -1)
        errors = [Fraction(values[i-1]-values[i]) for i in range(1, len(values))]
        expected_mae = float(sum(map(abs, errors))/len(errors))
        expected_rmse = math.sqrt(float(sum(e*e for e in errors)/len(errors)))
        score = rolling_score(batch(*values), min_history=1)
        self.assertEqual(score.count, 4)
        self.assertEqual(score.mae, expected_mae)
        self.assertEqual(score.rmse, expected_rmse)

    def test_mean_scores_observed_prefix_window_at_each_step(self):
        score = rolling_score(batch(1, 3, 7, 11), min_history=2, method="mean", window=2)
        self.assertEqual(score, Score(2, 5.5, math.sqrt(30.5)))

    def test_seasonal_perfect_pattern_has_zero_error(self):
        self.assertEqual(rolling_score(batch(2, 4, 2, 4, 2, 4), min_history=2, method="seasonal", season=2), Score(4, 0, 0))

    def test_every_prediction_sees_only_its_earlier_prefix(self):
        source = batch(2, 7, 3, 8, 4)
        with mock.patch.object(evaluator, "_predict", wraps=evaluator._predict) as spy:
            rolling_score(source, min_history=2, method="mean", window=2)
        self.assertEqual(spy.call_count, 3)
        for index, call in enumerate(spy.call_args_list, 2):
            self.assertEqual(call.args[0], source.records[:index])
            self.assertEqual(call.args[0][-1].period, index-1)

    def test_future_tail_changes_do_not_change_an_earlier_prediction(self):
        results = []
        for source in (batch(2, 4, 8, 16), batch(2, 4, -99, 999)):
            captured = []
            original = evaluator._predict
            def capture(*args):
                predicted = original(*args)
                captured.append(predicted)
                return predicted
            with mock.patch.object(evaluator, "_predict", side_effect=capture):
                rolling_score(source, min_history=2, method="mean", window=2)
            results.append(captured[0])
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0].value, 3)

    def test_minimum_history_is_explicit_bounded_and_not_boolean(self):
        for value in (0, 257, True, 1.0, "1", None):
            with self.subTest(value=value), self.assertRaisesRegex(ReferenceError, "FORECAST_PARAMETER_INVALID"):
                rolling_score(batch(1, 2), min_history=value)

    def test_no_holdout_is_refused_instead_of_fabricating_zero_error(self):
        for minimum in (2, 3, 256):
            with self.assertRaisesRegex(ReferenceError, "EVALUATION_HISTORY_REQUIRED"):
                rolling_score(batch(1, 2), min_history=minimum)

    def test_method_history_shortfall_is_not_silently_adjusted(self):
        for options in (dict(method="mean", window=3), dict(method="seasonal", season=3)):
            with self.assertRaisesRegex(ReferenceError, "FORECAST_HISTORY_REQUIRED"):
                rolling_score(batch(1, 2, 3, 4), min_history=2, **options)

    def test_partial_and_gapped_batches_cannot_be_scored(self):
        with self.assertRaisesRegex(ReferenceError, "BATCH_REVIEW_REQUIRED"):
            rolling_score(ingest_jsonl("null"), min_history=1)
        with self.assertRaisesRegex(ReferenceError, "FORECAST_ORDER_OR_GAP"):
            rolling_score(Batch((Point("sample", 0, 1), Point("sample", 2, 2)), (), 0), min_history=1)

    def test_extreme_error_is_finite_and_not_clipped(self):
        self.assertEqual(rolling_score(batch(-1000000000, 1000000000), min_history=1), Score(1, 2000000000, 2000000000))

    def test_last_allowed_period_and_maximum_fold_count(self):
        self.assertEqual(rolling_score(batch(1, 2, start=MAX_PERIOD-1), min_history=1), Score(1, 1, 1))
        self.assertEqual(rolling_score(batch(*range(256)), min_history=1).count, 255)

    def test_scores_are_immutable_and_source_is_preserved(self):
        source = batch(1, 3, 2)
        before = repr(source)
        score = rolling_score(source, min_history=1)
        self.assertEqual(repr(source), before)
        with self.assertRaises(FrozenInstanceError):
            score.mae = 0


class IntegrationTests(unittest.TestCase):
    def test_snapshot_is_byte_identical_to_public_ingestion_core(self):
        public = ROOT.parent/"record-ingestion"/"ingestion.py"
        self.assertEqual((ROOT/"ingestion.py").read_bytes(), public.read_bytes())

    def test_csv_and_jsonl_produce_identical_forecasts_and_scores(self):
        a = ingest_csv("series,period,value\n SAMPLE ,0,2\nsample,1,4\nsample,2,6")
        b = batch(2, 4, 6)
        self.assertEqual(forecast(a, method="mean", window=2), forecast(b, method="mean", window=2))
        self.assertEqual(rolling_score(a, min_history=1), rolling_score(b, min_history=1))

    def test_demo_never_opens_data_files_network_or_processes(self):
        with mock.patch("builtins.open", side_effect=AssertionError("FILE_OPENED")), mock.patch.object(socket, "socket", side_effect=AssertionError("NETWORK")), mock.patch.object(subprocess, "run", side_effect=AssertionError("PROCESS")), mock.patch.object(os, "system", side_effect=AssertionError("SHELL")):
            result = run_demo()
        self.assertEqual(result, run_demo())
        self.assertEqual(result["conflict_gate"], "BATCH_REVIEW_REQUIRED")
        self.assertEqual(result["methods"]["seasonal"]["score"], dict(count=4, mae=0, rmse=0))

    def test_actual_demo_cli_creates_no_files_and_preserves_source(self):
        def hashes():
            return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob("*.py")}
        before = hashes()
        with tempfile.TemporaryDirectory(prefix="fictional-forecast-", dir=os.environ.get("OUTLANDS_TEST_TEMP")) as folder:
            result = subprocess.run([sys.executable, "-B", str(ROOT/"demo.py"), "--demo"], cwd=folder, capture_output=True, text=True, timeout=20)
            self.assertEqual((result.returncode, result.stderr), (0, ""))
            self.assertEqual(json.loads(result.stdout), run_demo())
            self.assertEqual(list(Path(folder).iterdir()), [])
        self.assertEqual(hashes(), before)

    def test_static_help_and_no_arguments_omit_workstation_paths(self):
        for arguments in ([], ["--help"]):
            result = subprocess.run([sys.executable, "-B", str(ROOT/"demo.py"), *arguments], capture_output=True, text=True, timeout=20)
            self.assertEqual((result.returncode, result.stderr), (0, ""))
            self.assertIn("forecast-baseline-evaluator", result.stdout)
            self.assertNotIn(str(ROOT), result.stdout)

    def test_invalid_arguments_do_not_echo_values_or_native_errors(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT/"demo.py"), "--unknown", "FICTIONAL_DO_NOT_ECHO"], capture_output=True, text=True, timeout=20)
        self.assertEqual((result.returncode, result.stderr), (2, ""))
        self.assertEqual(json.loads(result.stdout), dict(status="ERROR", code="ARGUMENTS_INVALID"))

    def test_interruption_has_a_fixed_code(self):
        output = io.StringIO()
        with mock.patch("demo.run_demo", side_effect=KeyboardInterrupt), mock.patch("sys.stdout", output):
            status = main(["--demo"])
        self.assertEqual(status, 130)
        self.assertEqual(json.loads(output.getvalue()), dict(status="ERROR", code="INTERRUPTED"))


if __name__ == "__main__":
    unittest.main()
