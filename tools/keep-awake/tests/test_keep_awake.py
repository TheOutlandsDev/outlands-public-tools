"""Synthetic helpers and simulated APIs only; never a native Windows/Tk test."""
import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import ctypes
import importlib.util
import io
import math
from pathlib import Path
import random
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("outlands_awake_under_test", ROOT / "keep_awake.py")
tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tool
SPEC.loader.exec_module(tool)

# Fail closed if a test accidentally attempts a real Windows DLL load.
def setUpModule():
    global native_guard
    native_guard = mock.patch.object(ctypes, "WinDLL", side_effect=AssertionError("NATIVE_API_FORBIDDEN"), create=True)
    native_guard.start()

def tearDownModule():
    native_guard.stop()

class HelpersTests(unittest.TestCase):
    def test_color_clamping_and_blending(self):
        self.assertEqual(tool.clamp(-2), 0)
        self.assertEqual(tool.clamp(2), 1)
        self.assertEqual(tool.mix("#000000", "#ffffff", .5), "#808080")
        self.assertEqual(tool.mix("#000000", "#ffffff", -1), "#000000")
        self.assertEqual(tool.mix("#000000", "#ffffff", 2), "#ffffff")

    def test_duration_text(self):
        self.assertEqual(tool.duration_text(3661.9), "01:01:01")
        self.assertEqual(tool.duration_text(-2), "00:00:00")

    def test_minutes_reject_negative_nonfinite_and_nonnumeric(self):
        for value in ("-1", "nan", "inf", "-inf", "fictional"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                tool.nonnegative_minutes(value)
        self.assertEqual(tool.nonnegative_minutes("2.5"), 2.5)
        self.assertEqual(tool.nonnegative_minutes("0"), 0)

    def test_minutes_conversion_cannot_overflow_deadline(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            tool.nonnegative_minutes("1e308")

    def test_monitor_bounds_are_data_only(self):
        monitor = tool.MonitorBounds(-1920, 0, 0, 1080)
        self.assertEqual((monitor.width, monitor.height), (1920, 1080))
        self.assertTrue(monitor.contains(-100, 500))
        self.assertFalse(monitor.contains(0, 500))
        self.assertEqual(monitor.geometry, "1920x1080+-1920+0")

    def test_synthetic_animation_graph_is_deterministic_and_bounded(self):
        def graph():
            app = tool.AwakeApp.__new__(tool.AwakeApp)
            app.rng = random.Random(123)
            app.nodes = app._build_neural_nodes(42)
            edges = app._build_neural_edges()
            return app.nodes, edges
        first, second = graph(), graph()
        self.assertEqual(first, second)
        nodes, edges = first
        self.assertEqual(len(nodes), 42)
        self.assertEqual(len({(e.source, e.target) for e in edges}), len(edges))
        for edge in edges:
            self.assertLess(nodes[edge.source].layer, nodes[edge.target].layer)
        for node in nodes:
            for elapsed in (0, 1, 100):
                self.assertTrue(0 <= tool.AwakeApp._node_activation(node, elapsed) <= 1)

class ArgumentTests(unittest.TestCase):
    def rejected(self, args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(tool, "StayAwake") as request:
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(tool.main(args), 2)
        request.assert_not_called()
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "Error: ARGUMENTS_INVALID\n")

    def test_unknown_argument_not_echoed(self):
        self.rejected(["--unknown", "PRIVATE-ARGUMENT-CANARY"])

    def test_missing_minutes_not_echoed(self):
        self.rejected(["--minutes"])

    def test_invalid_choice_not_echoed(self):
        self.rejected(["--theme", "PRIVATE-THEME-CANARY"])

    def test_invalid_number_not_echoed(self):
        self.rejected(["--fps", "PRIVATE-NUMBER-CANARY"])

    def test_help_uses_static_program_name(self):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["/private/PROGRAM-CANARY"]):
            with redirect_stdout(out), self.assertRaises(SystemExit) as stopped:
                tool.main(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn("usage: keep_awake.py", out.getvalue())
        self.assertNotIn("PROGRAM-CANARY", out.getvalue())

    def test_version_uses_static_program_name(self):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["/private/VERSION-CANARY"]):
            with redirect_stdout(out), self.assertRaises(SystemExit) as stopped:
                tool.main(["--version"])
        self.assertEqual(stopped.exception.code, 0)
        self.assertEqual(out.getvalue(), "keep_awake.py " + tool.VERSION + "\n")

    def test_nonwindows_self_test_cannot_attempt_native_api(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "platform", "linux"), mock.patch.object(tool, "self_test") as operation:
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(tool.main(["--self-test"]), 1)
        operation.assert_not_called()
        self.assertEqual(err.getvalue(), "Error: WINDOWS_REQUIRED\n")
        self.assertEqual(out.getvalue(), "")

    def test_compatibility_options_and_defaults_are_explicit(self):
        parsed = tool.build_parser().parse_args(["--minimized", "--pattern", "random", "--keep-display-on"])
        self.assertEqual(parsed.minutes, 0)
        self.assertTrue(parsed.minimized)
        self.assertTrue(parsed.keep_display_on)
        self.assertEqual(parsed.pattern, "random")

class FakeFunction:
    def __init__(self, values):
        self.values = iter(values)
        self.flags = []
    def __call__(self, flags):
        self.flags.append(flags)
        return next(self.values)

class PowerSimulationTests(unittest.TestCase):
    def power(self, values):
        stack = ExitStack()
        self.addCleanup(stack.close)
        function = FakeFunction(values)
        stack.enter_context(mock.patch.object(sys, "platform", "win32"))
        loader = stack.enter_context(mock.patch.object(ctypes, "WinDLL", return_value=SimpleNamespace(SetThreadExecutionState=function), create=True))
        stack.enter_context(mock.patch.object(ctypes, "get_last_error", return_value=123, create=True))
        stack.enter_context(mock.patch.object(ctypes, "WinError", side_effect=lambda code: OSError("MOCK_ERROR_" + str(code)), create=True))
        return function, loader

    def test_flags_refresh_and_restore_simulated(self):
        function, loader = self.power([1, 1, 1])
        with tool.StayAwake() as request:
            self.assertTrue(request.active)
            request.refresh()
        self.assertFalse(request.active)
        self.assertEqual(function.flags, [0x80000003, 0x80000003, 0x80000000])
        loader.assert_called_once_with("kernel32", use_last_error=True)

    def test_restore_inactive_is_noop_simulated(self):
        function, _ = self.power([])
        request = tool.StayAwake()
        request.restore()
        self.assertEqual(function.flags, [])

    def test_acquisition_failure_is_reported_simulated(self):
        function, _ = self.power([0])
        request = tool.StayAwake()
        with self.assertRaises(OSError):
            request.refresh()
        self.assertFalse(request.active)
        self.assertEqual(function.flags, [0x80000003])

    def test_body_exception_still_restores_simulated(self):
        function, _ = self.power([1, 1])
        with self.assertRaises(ValueError):
            with tool.StayAwake() as request:
                raise ValueError("fictional body failure")
        self.assertFalse(request.active)
        self.assertEqual(function.flags[-1], 0x80000000)

    def test_restore_failure_warns_and_keeps_active_flag_simulated(self):
        self.power([1, 0])
        err = io.StringIO()
        with redirect_stderr(err):
            with tool.StayAwake() as request:
                pass
        self.assertTrue(request.active)
        self.assertIn("restoration failed", err.getvalue())

    def test_main_restore_failure_has_failure_exit_status(self):
        self.power([1, 0])
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(tool, "run_console"), redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(tool.main(["--no-visual", "--minutes", "1"]), 1)
        self.assertIn("RESTORATION_NOT_CONFIRMED", err.getvalue())

    def test_main_interrupt_restores_simulated(self):
        function, _ = self.power([1, 1])
        with mock.patch.object(tool, "run_console", side_effect=KeyboardInterrupt), redirect_stdout(io.StringIO()):
            self.assertEqual(tool.main(["--no-visual"]), 0)
        self.assertEqual(function.flags[-1], 0x80000000)

    def test_main_runtime_failure_still_restores_simulated(self):
        function, _ = self.power([1, 1])
        with mock.patch.object(tool, "run_console", side_effect=RuntimeError("fictional")), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(tool.main(["--no-visual"]), 1)
        self.assertEqual(function.flags[-1], 0x80000000)

    def test_console_deadline_uses_fake_clock_without_real_sleep(self):
        request = mock.Mock()
        with mock.patch.object(tool.time, "monotonic", side_effect=[0, 0, 0, 61]), mock.patch.object(tool.time, "sleep") as sleep:
            with redirect_stdout(io.StringIO()):
                tool.run_console(request, 1)
        request.refresh.assert_called_once_with()
        sleep.assert_called_once_with(20.0)

class FakeTclError(Exception):
    pass

class VisualControlFlowTests(unittest.TestCase):
    def fake_tk(self, root=None, error=None):
        module = ModuleType("tkinter")
        module.TclError = FakeTclError
        module.Tk = mock.Mock(return_value=root, side_effect=error)
        return module
    def arguments(self):
        return tool.build_parser().parse_args([])

    def test_init_failure_destroys_fake_root(self):
        root = mock.Mock()
        with mock.patch.dict(sys.modules, {"tkinter": self.fake_tk(root)}), mock.patch.object(tool, "enable_dpi_awareness"), mock.patch.object(tool, "AwakeApp", side_effect=RuntimeError("fictional init")):
            with self.assertRaises(RuntimeError):
                tool.run_visual(mock.Mock(), self.arguments())
        root.destroy.assert_called_once_with()

    def test_normal_mainloop_exit_destroys_fake_root(self):
        root = mock.Mock()
        with mock.patch.dict(sys.modules, {"tkinter": self.fake_tk(root)}), mock.patch.object(tool, "enable_dpi_awareness"), mock.patch.object(tool, "AwakeApp"):
            tool.run_visual(mock.Mock(), self.arguments())
        root.mainloop.assert_called_once_with()
        root.destroy.assert_called_once_with()

    def test_tcl_error_is_generic_without_private_detail(self):
        with mock.patch.dict(sys.modules, {"tkinter": self.fake_tk(error=FakeTclError("PRIVATE-TCL-CANARY"))}), mock.patch.object(tool, "enable_dpi_awareness"):
            with self.assertRaisesRegex(RuntimeError, "^GUI_UNAVAILABLE_OR_FAILED$"):
                tool.run_visual(mock.Mock(), self.arguments())

    def test_close_is_idempotent_with_fake_widgets(self):
        app = tool.AwakeApp.__new__(tool.AwakeApp)
        app.running = True
        app.tk = SimpleNamespace(TclError=FakeTclError)
        app.root = mock.Mock()
        app.request = mock.Mock()
        app.after_id = "fictional-timer"
        self.assertEqual(app.close(), "break")
        self.assertEqual(app.close(), "break")
        app.request.restore.assert_called_once_with()
        app.root.after_cancel.assert_called_once_with("fictional-timer")
        app.root.destroy.assert_called_once_with()

if __name__ == "__main__":
    unittest.main()
