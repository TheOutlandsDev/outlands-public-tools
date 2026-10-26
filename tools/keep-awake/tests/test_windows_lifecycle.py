"""Portable failure fixtures; opt-in native Windows requests and transparent Tk.

OUTLANDS_AWAKE_NATIVE=1 permits short real power requests and Tk windows.
No files, network, power plans, user input or persisted configuration are used.
"""
from contextlib import redirect_stderr, redirect_stdout
import ctypes
import importlib.util
import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "keep_awake.py"
SPEC = importlib.util.spec_from_file_location("outlands_awake_lifecycle", SOURCE)
tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tool
SPEC.loader.exec_module(tool)
CONTINUOUS = 0x80000000
REQUIRED = 0x80000003
NATIVE = sys.platform == "win32" and os.environ.get("OUTLANDS_AWAKE_NATIVE") == "1"


def captured_main(args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        status = tool.main(args)
    return status, out.getvalue(), err.getvalue()


class PortableLifecycleTests(unittest.TestCase):
    def setUp(self):
        guard = mock.patch.object(ctypes, "WinDLL", side_effect=AssertionError("NATIVE_FORBIDDEN"), create=True)
        guard.start()
        self.addCleanup(guard.stop)
        # Load argparse's lazy formatter dependencies under the real platform.
        # A later simulated sys.platform must not make Linux import _winapi.
        tool.build_parser()

    def power(self, values):
        function = mock.Mock(side_effect=values)
        patcher = mock.patch.object(ctypes, "WinDLL", return_value=SimpleNamespace(SetThreadExecutionState=function), create=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        platform = mock.patch.object(sys, "platform", "win32")
        platform.start()
        self.addCleanup(platform.stop)
        return function

    def test_power_failures_have_fixed_categories_without_last_error_lookup(self):
        self.power([0])
        with mock.patch.object(ctypes, "get_last_error", side_effect=AssertionError("UNSPECIFIED_LAST_ERROR"), create=True):
            self.assertEqual(captured_main(["--no-visual"])[2], "Error: POWER_REQUEST_FAILED\n")

    def test_clear_failure_is_generic_and_active_remains_true(self):
        self.power([1, 0])
        request = tool.StayAwake()
        request.refresh()
        with self.assertRaisesRegex(OSError, "^POWER_REQUEST_CLEAR_FAILED$"):
            request.restore()
        self.assertTrue(request.active)

    def test_wrong_thread_cannot_refresh_or_clear_an_owned_request(self):
        function = self.power([1, 1])
        request = tool.StayAwake()
        request.refresh()
        errors = []
        def other_thread():
            for operation in (request.refresh, request.restore):
                try:
                    operation()
                except RuntimeError as error:
                    errors.append(str(error))
        worker = threading.Thread(target=other_thread)
        worker.start()
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, ["REQUEST_THREAD_MISMATCH"] * 2)
        self.assertEqual(function.call_count, 1)
        request.restore()

    def test_arbitrary_runtime_error_details_are_not_printed(self):
        self.power([1, 1])
        with mock.patch.object(tool, "run_console", side_effect=ValueError("FICTIONAL_PRIVATE_DETAIL")):
            status, out, err = captured_main(["--no-visual"])
        self.assertEqual(status, 1)
        self.assertEqual(err, "Error: RUNTIME_FAILED\n")
        self.assertNotIn("FICTIONAL_PRIVATE_DETAIL", out + err)

    def test_arbitrary_self_test_error_details_are_not_printed(self):
        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(tool, "self_test", side_effect=RuntimeError("FICTIONAL_PRIVATE_DETAIL")):
            status, out, err = captured_main(["--self-test"])
        self.assertEqual((status, out, err), (1, "", "Self-test failed: RUNTIME_FAILED\n"))

    def test_interrupted_self_test_does_not_claim_success(self):
        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(tool, "self_test", side_effect=KeyboardInterrupt):
            self.assertEqual(captured_main(["--self-test"]), (1, "", "Error: SELF_TEST_INTERRUPTED\n"))

    def test_self_test_checks_are_not_assert_statements(self):
        with mock.patch.object(tool, "clamp", return_value=7):
            with self.assertRaisesRegex(RuntimeError, "^SELF_TEST_FAILED$"):
                tool.self_test()

    def test_optimized_self_test_still_rejects_a_false_check(self):
        code = "import runpy,sys; m=runpy.run_path(sys.argv[1]); m['self_test'].__globals__['clamp']=lambda value:7; m['self_test']()"
        result = subprocess.run([sys.executable, "-B", "-O", "-c", code, str(SOURCE)], capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"SELF_TEST_FAILED", result.stderr)

    def test_nonwindows_console_visual_and_smoke_stop_before_native_calls(self):
        with mock.patch.object(sys, "platform", "linux"):
            for args in (["--no-visual"], [], ["--ui-smoke-test"]):
                with self.subTest(args=args):
                    self.assertEqual(captured_main(args), (1, "", "Error: WINDOWS_REQUIRED\n"))

    def test_callback_exception_closes_fake_application_and_propagates_category(self):
        root = mock.Mock()
        app = SimpleNamespace(failure_code=None, close=mock.Mock())
        root.mainloop.side_effect = lambda: root.report_callback_exception(RuntimeError, RuntimeError("FICTIONAL_CALLBACK_DETAIL"), None)
        with mock.patch.object(tool, "AwakeApp", return_value=app):
            with self.assertRaisesRegex(RuntimeError, "^GUI_CALLBACK_FAILED$"):
                tool._run_visual_app(root, mock.Mock(), tool.build_parser().parse_args([]))
        self.assertEqual(app.close.call_count, 2)

    def test_callback_during_constructor_destroys_root_and_cannot_report_success(self):
        root = mock.Mock()
        def construct(*args, **kwargs):
            root.report_callback_exception(RuntimeError, RuntimeError("FICTIONAL_CALLBACK_DETAIL"), None)
            return SimpleNamespace(failure_code=None, close=mock.Mock())
        with mock.patch.object(tool, "AwakeApp", side_effect=construct):
            with self.assertRaisesRegex(RuntimeError, "^GUI_CALLBACK_FAILED$"):
                tool._run_visual_app(root, mock.Mock(), tool.build_parser().parse_args([]))
        root.destroy.assert_called_once_with()
        root.mainloop.assert_not_called()

    def test_gui_refresh_failure_closes_without_modal_or_native_error_text(self):
        app = tool.AwakeApp.__new__(tool.AwakeApp)
        app.close = mock.Mock()
        app._fatal_power_error(OSError("FICTIONAL_NATIVE_DETAIL"))
        self.assertEqual(app.failure_code, "POWER_REQUEST_FAILED")
        app.close.assert_called_once_with()

    def test_gui_clear_failure_survives_later_successful_cleanup(self):
        app = tool.AwakeApp.__new__(tool.AwakeApp)
        app.running, app.failure_code = True, None
        app.root, app.request = mock.Mock(), mock.Mock()
        app.tk = SimpleNamespace(TclError=type("FictionalTclError", (Exception,), {}))
        app.after_id = "fictional-timer"
        app.request.restore.side_effect = OSError("FICTIONAL_NATIVE_DETAIL")
        out = io.StringIO()
        with redirect_stderr(out):
            app.close()
        self.assertEqual(app.failure_code, "RESTORATION_NOT_CONFIRMED")
        self.assertNotIn("FICTIONAL_NATIVE_DETAIL", out.getvalue())
        root = mock.Mock()
        with mock.patch.object(tool, "AwakeApp", return_value=app):
            with self.assertRaisesRegex(RuntimeError, "^RESTORATION_NOT_CONFIRMED$"):
                tool._run_visual_app(root, mock.Mock(), tool.build_parser().parse_args([]))

    def test_smoke_failure_cannot_be_removed_by_optimization(self):
        root = mock.Mock()
        root.overrideredirect.return_value = False
        app = SimpleNamespace(fullscreen=False, failure_code=None, set_fullscreen=mock.Mock(),
                              _animate_aurora=mock.Mock(), _animate_network=mock.Mock(),
                              canvas=mock.Mock(), close=mock.Mock())
        app.canvas.find_all.return_value = ()
        args = tool.build_parser().parse_args(["--ui-smoke-test"])
        with mock.patch.object(tool, "AwakeApp", return_value=app):
            with self.assertRaisesRegex(RuntimeError, "^UI_SMOKE_FAILED$"):
                tool._run_visual_app(root, mock.Mock(), args)


class NativeWindowsFixture(unittest.TestCase):
    def setUp(self):
        raw = ctypes.WinDLL("kernel32", use_last_error=True).SetThreadExecutionState
        raw.argtypes, raw.restype = [ctypes.c_uint], ctypes.c_uint
        self.raw = raw
        previous = raw(CONTINUOUS)
        self.assertNotEqual(previous, 0)
        self.addCleanup(raw, previous)

    def observe(self, request):
        original = request._set_state
        calls = []
        def native_call(flags):
            result = original(flags)
            calls.append((flags, result))
            return result
        request._set_state = native_call
        self.addCleanup(request.restore)
        return calls

    def assert_cleared(self):
        self.assertEqual(self.raw(CONTINUOUS), CONTINUOUS)


@unittest.skipUnless(NATIVE, "Requires explicit OUTLANDS_AWAKE_NATIVE=1 on Windows")
class NativeWindowsPowerTests(NativeWindowsFixture):
    def test_native_acquire_refresh_clear_and_independent_previous_state(self):
        request = tool.StayAwake()
        calls = self.observe(request)
        request.refresh()
        self.assertEqual(self.raw(REQUIRED), REQUIRED)
        request.refresh()
        request.restore()
        self.assertFalse(request.active)
        self.assertEqual([f for f, _ in calls], [REQUIRED, REQUIRED, CONTINUOUS])
        self.assertTrue(all(result != 0 for _, result in calls))
        self.assert_cleared()

    def test_native_body_exception_clears_same_thread_request(self):
        request = tool.StayAwake()
        calls = self.observe(request)
        with self.assertRaisesRegex(ValueError, "FICTIONAL_BODY_FAILURE"):
            with request:
                raise ValueError("FICTIONAL_BODY_FAILURE")
        self.assertFalse(request.active)
        self.assertEqual(calls[-1][0], CONTINUOUS)
        self.assert_cleared()

    def test_native_bounded_console_clears_without_importing_tk(self):
        request = tool.StayAwake()
        self.observe(request)
        with mock.patch.object(tool, "StayAwake", return_value=request):
            status, _, err = captured_main(["--no-visual", "--minutes", "0.002"])
        self.assertEqual((status, err), (0, ""))
        self.assertFalse(request.active)
        self.assert_cleared()

    def test_native_request_clears_after_python_sigint(self):
        request = tool.StayAwake()
        calls = self.observe(request)
        def interrupt(*args):
            self.assertTrue(request.active)
            signal.raise_signal(signal.SIGINT)
        with mock.patch.object(tool, "StayAwake", return_value=request), mock.patch.object(tool, "run_console", side_effect=interrupt):
            status, out, err = captured_main(["--no-visual"])
        self.assertEqual((status, err), (0, ""))
        self.assertIn("Stop requested.", out)
        self.assertEqual(calls[-1][0], CONTINUOUS)
        self.assert_cleared()

    def test_native_request_clears_after_injected_runtime_failure(self):
        request = tool.StayAwake()
        self.observe(request)
        with mock.patch.object(tool, "StayAwake", return_value=request), mock.patch.object(tool, "run_console", side_effect=RuntimeError("FICTIONAL_RUNTIME_DETAIL")):
            self.assertEqual(captured_main(["--no-visual"])[2], "Error: RUNTIME_FAILED\n")
        self.assertFalse(request.active)
        self.assert_cleared()

    def test_native_monitor_enumeration_returns_positive_bounds(self):
        monitors = tool.enumerate_monitors()
        self.assertTrue(monitors)
        self.assertTrue(all(m.width > 0 and m.height > 0 for m in monitors))
        self.assertEqual(monitors, tuple(sorted(monitors, key=lambda m: (m.left, m.top))))
        self.assert_cleared()

    def test_native_self_test_acquires_and_clears(self):
        status, out, err = captured_main(["--self-test"])
        self.assertEqual((status, err), (0, ""))
        self.assertIn("native request acquire/clear calls succeeded", out)
        self.assert_cleared()


@unittest.skipUnless(NATIVE, "Requires explicit OUTLANDS_AWAKE_NATIVE=1 on Windows")
class NativeWindowsTkTests(NativeWindowsFixture):
    def visual(self, action, args=None):
        import tkinter as tk
        roots, apps = [], []
        factory = tk.Tk
        base = tool.AwakeApp
        request = tool.StayAwake()
        calls = self.observe(request)
        def hidden_root():
            root = factory()
            root.attributes("-alpha", 0.0)
            root.after(2000, root.quit)
            roots.append(root)
            return root
        class ControlledApp(base):
            def __init__(self, root, *items, **kwargs):
                super().__init__(root, *items, **kwargs)
                apps.append(self)
                root.after(30, lambda: action(self))
        with mock.patch.object(tk, "Tk", side_effect=hidden_root), mock.patch.object(tool, "StayAwake", return_value=request), mock.patch.object(tool, "AwakeApp", ControlledApp):
            result = captured_main(args or ["--quality", "low", "--fps", "10"])
        self.assertFalse(request.active)
        self.assertEqual(calls[-1][0], CONTINUOUS)
        self.assertTrue(all(value != 0 for _, value in calls))
        for root in roots:
            with self.assertRaises(tk.TclError):
                root.winfo_exists()
        self.assert_cleared()
        return result, apps

    def test_native_tk_registered_window_close_clears_and_destroys(self):
        def window_close(app):
            app.root.tk.call(app.root.protocol("WM_DELETE_WINDOW"))
        result, apps = self.visual(window_close)
        self.assertEqual((result[0], result[2]), (0, ""))
        self.assertFalse(apps[0].running)

    def test_native_tk_deadline_clears_and_destroys(self):
        result, apps = self.visual(lambda app: None, ["--quality", "low", "--fps", "10", "--minutes", "0.003"])
        self.assertEqual((result[0], result[2]), (0, ""))
        self.assertFalse(apps[0].running)

    def test_native_tk_callback_failure_returns_failure_without_traceback(self):
        def broken_callback(app):
            raise ValueError("FICTIONAL_CALLBACK_DETAIL")
        result, apps = self.visual(broken_callback)
        self.assertEqual((result[0], result[2]), (1, "Error: GUI_CALLBACK_FAILED\n"))
        self.assertNotIn("FICTIONAL_CALLBACK_DETAIL", result[1] + result[2])
        self.assertFalse(apps[0].running)

    def test_native_tk_refresh_failure_is_fixed_and_nonmodal(self):
        def fail_refresh(app):
            app.request.refresh = mock.Mock(side_effect=OSError("FICTIONAL_NATIVE_DETAIL"))
            app.next_awake_refresh = 0
        result, apps = self.visual(fail_refresh)
        self.assertEqual((result[0], result[2]), (1, "Error: POWER_REQUEST_FAILED\n"))
        self.assertFalse(apps[0].running)

    def test_native_tk_external_mainloop_quit_still_cleans_up(self):
        result, _ = self.visual(lambda app: app.root.quit())
        self.assertEqual((result[0], result[2]), (0, ""))

    def test_native_tk_clear_failure_on_loop_quit_is_not_hidden_by_retry(self):
        def fail_first_clear(app):
            original = app.request.restore
            remaining = [True]
            def restore():
                if remaining.pop() if remaining else False:
                    raise OSError("FICTIONAL_CLEAR_DETAIL")
                original()
            app.request.restore = restore
            app.root.quit()
        result, _ = self.visual(fail_first_clear)
        self.assertEqual(result[0], 1)
        self.assertIn("Error: RESTORATION_NOT_CONFIRMED\n", result[2])
        self.assertNotIn("FICTIONAL_CLEAR_DETAIL", result[1] + result[2])

    def test_native_tk_startup_failure_destroys_root_and_clears_request(self):
        import tkinter as tk
        factory, roots = tk.Tk, []
        def hidden_root():
            root = factory()
            root.withdraw()
            roots.append(root)
            return root
        with mock.patch.object(tk, "Tk", side_effect=hidden_root), mock.patch.object(tool, "AwakeApp", side_effect=RuntimeError("FICTIONAL_STARTUP_DETAIL")):
            result = captured_main([])
        self.assertEqual((result[0], result[2]), (1, "Error: RUNTIME_FAILED\n"))
        with self.assertRaises(tk.TclError):
            roots[0].winfo_exists()
        self.assert_cleared()

    def test_native_tk_smoke_runs_real_frames_and_clears(self):
        status, out, err = captured_main(["--ui-smoke-test", "--quality", "low", "--fps", "10"])
        self.assertEqual((status, err), (0, ""))
        self.assertIn("UI smoke test passed:", out)
        self.assert_cleared()


if __name__ == "__main__":
    unittest.main()
