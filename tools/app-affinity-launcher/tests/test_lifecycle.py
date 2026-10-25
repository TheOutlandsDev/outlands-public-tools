"""Original MIT failure sequencing tests. Every child here is a generated fake."""
import copy
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app_affinity import AffinityError, make_plan, launch
from helpers import FakeBackend, make_executable


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="affinity-lifecycle-")
        self.addCleanup(self.tmp.cleanup)
        self.exe = make_executable(self.tmp.name)
        self.plan = make_plan(self.exe, mask=5, backend=FakeBackend())

    def test_affinity_and_priority_verified_before_resume(self):
        backend = FakeBackend()
        result = launch(self.plan, backend=backend)
        actions = backend.events
        self.assertLess(actions.index("create"), actions.index("set_mask"))
        self.assertLess(actions.index("set_mask"), actions.index("get_mask"))
        self.assertLess(actions.index("get_mask"), actions.index("resume"))
        self.assertLess(actions.index("get_priority"), actions.index("resume"))
        self.assertEqual(actions.count("close"), 1)
        self.assertNotIn("terminate", actions)
        self.assertEqual(backend.child.mask, 5)
        self.assertIsInstance(result, dict)

    def test_launch_revalidates_current_cpu_allowance(self):
        backend = FakeBackend(available_mask=1)
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertNotIn("create", backend.events)

    def test_launch_rechecks_duplicates(self):
        backend = FakeBackend(pids=(777,))
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertNotIn("create", backend.events)

    def test_launch_rechecks_missing_executable(self):
        self.exe.unlink()
        backend = FakeBackend()
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertNotIn("create", backend.events)

    def test_launch_revalidates_local_drive_status(self):
        backend = FakeBackend(reject_paths=True)
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertIn("verify_local_paths", backend.events)
        self.assertNotIn("create", backend.events)

    def test_creation_failure_has_no_child_to_terminate(self):
        backend = FakeBackend(create_fails=True)
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertNotIn("terminate", backend.events)
        self.assertNotIn("close", backend.events)

    def test_affinity_set_failure_never_resumes_and_cleans_created_child(self):
        backend = FakeBackend(child_options={"failure": "set_mask"})
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertNotIn("resume", backend.events)
        self.assertEqual(backend.events.count("terminate"), 1)
        self.assertEqual(backend.events.count("close"), 1)

    def test_affinity_read_failure_never_resumes(self):
        backend = FakeBackend(child_options={"failure": "get_mask"})
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertNotIn("resume", backend.events)
        self.assertIn("terminate", backend.events)
        self.assertEqual(backend.events.count("close"), 1)

    def test_affinity_readback_mismatch_never_resumes(self):
        backend = FakeBackend(child_options={"read_mask": 1})
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertNotIn("resume", backend.events)
        self.assertIn("terminate", backend.events)

    def test_non_normal_priority_never_resumes(self):
        backend = FakeBackend(child_options={"priority": 0x80})
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertNotIn("resume", backend.events)
        self.assertIn("terminate", backend.events)

    def test_priority_read_failure_never_resumes(self):
        backend = FakeBackend(child_options={"failure": "get_priority"})
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertNotIn("resume", backend.events)
        self.assertIn("terminate", backend.events)

    def test_failed_or_unexpected_resume_count_cleans_owned_child(self):
        for count in (-1, 0, 2, 0xffffffff):
            backend = FakeBackend(child_options={"resume_count": count})
            with self.subTest(count=count), self.assertRaises(AffinityError):
                launch(self.plan, backend=backend)
            self.assertEqual(backend.events.count("resume"), 1)
            self.assertEqual(backend.events.count("terminate"), 1)
            self.assertEqual(backend.events.count("close"), 1)

    def test_resume_error_cleans_owned_child(self):
        backend = FakeBackend(child_options={"failure": "resume"})
        with self.assertRaises(AffinityError):
            launch(self.plan, backend=backend)
        self.assertIn("terminate", backend.events)
        self.assertEqual(backend.events.count("close"), 1)

    def test_failed_cleanup_surfaces_created_pid_and_status(self):
        backend = FakeBackend(child_options={"failure": "set_mask", "terminate_fails": True})
        with self.assertRaises(AffinityError) as caught:
            launch(self.plan, backend=backend)
        details = getattr(caught.exception, "details", None)
        self.assertIsInstance(details, dict)
        self.assertIn("4242", str(details))
        self.assertEqual(backend.events.count("close"), 1)

    def test_cleanup_receipt_preserves_original_native_error_code(self):
        backend = FakeBackend(child_options={"failure": "set_mask", "failure_details": {"native_error_code": 5}})
        with self.assertRaises(AffinityError) as caught:
            launch(self.plan, backend=backend)
        self.assertEqual(caught.exception.details.get("native_error_code"), 5)
        self.assertEqual(caught.exception.details.get("pid"), 4242)
        self.assertEqual(backend.events.count("close"), 1)

    def test_close_failure_does_not_erase_setup_cleanup_status(self):
        backend = FakeBackend(child_options={"failure": "set_mask", "close_fails": True,
                                             "failure_details": {"native_error_code": 5}})
        with self.assertRaises(AffinityError) as caught:
            launch(self.plan, backend=backend)
        details = caught.exception.details
        self.assertEqual(details.get("pid"), 4242)
        self.assertTrue(details.get("terminated_created_child"))
        self.assertTrue(details.get("cleanup_confirmed"))
        self.assertEqual(details.get("native_error_code"), 5)
        self.assertIn("close", str(details).lower())

    def test_native_child_close_attempts_both_handles(self):
        from app_affinity.windows import Child

        class Kernel:
            def __init__(self):
                self.calls = []

            def CloseHandle(self, handle):
                self.calls.append(handle)
                return handle != 22

        kernel = Kernel()
        child = Child(kernel, SimpleNamespace(hProcess=11, hThread=22, dwProcessId=4242))
        with patch("app_affinity.windows.ctypes.get_last_error", return_value=6, create=True):
            with self.assertRaises(AffinityError):
                child.close()
        self.assertEqual(kernel.calls, [22, 11])

    def test_wait_can_observe_exit_without_terminating(self):
        backend = FakeBackend(child_options={"completed": True, "exit_status": 7})
        result = launch(self.plan, wait_seconds=1, backend=backend)
        self.assertIn("wait", backend.events)
        self.assertIn("exit_code", backend.events)
        self.assertNotIn("terminate", backend.events)
        self.assertEqual(result["child_exit_code"], 7)

    def test_wait_timeout_leaves_resumed_child_running(self):
        backend = FakeBackend(child_options={"completed": False})
        result = launch(self.plan, wait_seconds=1, backend=backend)
        self.assertNotIn("terminate", backend.events)
        self.assertEqual(backend.events.count("close"), 1)
        self.assertIsInstance(result, dict)

    def test_wait_error_does_not_kill_resumed_child(self):
        backend = FakeBackend(child_options={"failure": "wait"})
        with self.assertRaises(AffinityError):
            launch(self.plan, wait_seconds=1, backend=backend)
        self.assertNotIn("terminate", backend.events)
        self.assertEqual(backend.events.count("close"), 1)

    def test_invalid_wait_never_creates_child(self):
        for value in (0, -1, True, float("nan"), float("inf"), 301):
            backend = FakeBackend()
            with self.subTest(value=value), self.assertRaises(AffinityError):
                launch(self.plan, wait_seconds=value, backend=backend)
            self.assertNotIn("create", backend.events)

    def test_plan_input_is_not_mutated(self):
        before = copy.deepcopy(self.plan)
        launch(self.plan, backend=FakeBackend())
        self.assertEqual(self.plan, before)
