"""Original MIT portable affinity and launch-plan policy tests."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from app_affinity import (AffinityError, parse_cores, parse_mask, mask_from_cores,
                          validate_mask, make_plan)
from helpers import FakeBackend, make_executable


class MaskTests(unittest.TestCase):
    def test_explicit_zero_based_core_ids(self):
        self.assertEqual(parse_cores("0,2,5"), (0, 2, 5))

    def test_single_core(self):
        self.assertEqual(parse_cores("0"), (0,))

    def test_empty_and_ambiguous_core_lists_refused(self):
        for value in ("", " ", ",", "0,", ",0", "1,,2", "0-3", "0;1", "0,0", "-1", "64", None, True):
            with self.subTest(value=value), self.assertRaises(AffinityError):
                parse_cores(value)

    def test_explicit_hex_masks(self):
        self.assertEqual(parse_mask("0x1"), 1)
        self.assertEqual(parse_mask("0xA5"), 165)

    def test_invalid_masks_refused(self):
        for value in ("", "0x0", "-1", "0x-1", "0xz", "0x1;echo", None, True, 1):
            with self.subTest(value=value), self.assertRaises(AffinityError):
                parse_mask(value)

    def test_core_bits_are_exact(self):
        self.assertEqual(mask_from_cores((0, 2, 5)), 0x25)

    def test_core_collection_bounds_and_types(self):
        for value in ((), (True,), (-1,), (64,), (0, 0), ("0",), None):
            with self.subTest(value=value), self.assertRaises(AffinityError):
                mask_from_cores(value)

    def test_subset_mask_accepted(self):
        self.assertEqual(validate_mask(0x21, 0xA5), 0x21)

    def test_unavailable_core_refused(self):
        with self.assertRaises(AffinityError):
            validate_mask(0x02, 0xA5)

    def test_mask_cannot_be_zero_negative_or_boolean(self):
        for value in (0, -1, True, 1.0, "1"):
            with self.subTest(value=value), self.assertRaises(AffinityError):
                validate_mask(value, 0xff)

    def test_pointer_width_bound(self):
        self.assertEqual(validate_mask(1 << 31, 0xffffffff, 32), 1 << 31)
        with self.assertRaises(AffinityError):
            validate_mask(1 << 32, (1 << 33) - 1, 32)
        self.assertEqual(validate_mask(1 << 63, (1 << 64) - 1, 64), 1 << 63)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="affinity-plan-")
        self.addCleanup(self.tmp.cleanup)
        self.exe = make_executable(self.tmp.name)

    def test_plan_does_not_create_a_child(self):
        backend = FakeBackend()
        result = make_plan(self.exe, cores=(0, 2), backend=backend)
        self.assertEqual(result["action"], "plan")
        self.assertFalse(result["launch_requested"])
        self.assertEqual(result["mask"], "0x5")
        self.assertEqual(result["cores"], [0, 2])
        self.assertNotIn("create", backend.events)

    def test_default_working_directory_is_executable_parent(self):
        result = make_plan(self.exe, mask=1, backend=FakeBackend())
        self.assertEqual(Path(result["cwd"]), self.exe.parent)

    def test_explicit_existing_working_directory(self):
        directory = self.exe.parent / "working folder"
        directory.mkdir()
        result = make_plan(self.exe, mask=1, cwd=directory, backend=FakeBackend())
        self.assertEqual(Path(result["cwd"]), directory)

    def test_missing_executable_refused_before_create(self):
        backend = FakeBackend()
        with self.assertRaises(AffinityError):
            make_plan(self.exe.parent / "missing.exe", mask=1, backend=backend)
        self.assertNotIn("create", backend.events)

    def test_non_exe_inputs_refused(self):
        for suffix in (".cmd", ".bat", ".lnk", ".com", ".txt"):
            path = self.exe.with_suffix(suffix)
            path.write_text("Generated refusal fixture", encoding="utf-8")
            with self.subTest(suffix=suffix), self.assertRaises(AffinityError):
                make_plan(path, mask=1, backend=FakeBackend())

    def test_directory_is_not_executable(self):
        path = self.exe.parent / "directory.exe"
        path.mkdir()
        with self.assertRaises(AffinityError):
            make_plan(path, mask=1, backend=FakeBackend())

    def test_relative_executable_refused(self):
        with self.assertRaises(AffinityError):
            make_plan("relative.exe", mask=1, backend=FakeBackend())

    def test_missing_working_directory_refused(self):
        with self.assertRaises(AffinityError):
            make_plan(self.exe, mask=1, cwd=self.exe.parent / "missing", backend=FakeBackend())

    def test_working_directory_cannot_be_file(self):
        with self.assertRaises(AffinityError):
            make_plan(self.exe, mask=1, cwd=self.exe, backend=FakeBackend())

    def test_cpu_selection_must_be_explicit_and_unambiguous(self):
        for kwargs in ({}, {"cores": (0,), "mask": 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(AffinityError):
                make_plan(self.exe, backend=FakeBackend(), **kwargs)

    def test_unavailable_mask_refused(self):
        with self.assertRaises(AffinityError):
            make_plan(self.exe, mask=2, backend=FakeBackend(available_mask=1))

    def test_multiple_processor_groups_refused(self):
        with self.assertRaises(AffinityError):
            make_plan(self.exe, mask=1, backend=FakeBackend(processor_groups=2))

    def test_backend_local_drive_check_is_required_when_available(self):
        backend = FakeBackend(reject_paths=True)
        with self.assertRaises(AffinityError):
            make_plan(self.exe, mask=1, backend=backend)
        self.assertIn("verify_local_paths", backend.events)
        self.assertNotIn("create", backend.events)

    @unittest.skipUnless(os.name == "nt", "Windows path spelling rules")
    def test_windows_dot_segments_are_refused_before_normalizing(self):
        nested = self.exe.parent / "nested"
        nested.mkdir()
        raw = str(nested) + "\\..\\" + self.exe.name
        with self.assertRaises(AffinityError):
            make_plan(raw, mask=1, backend=FakeBackend())

    @unittest.skipUnless(os.name == "nt", "Windows path spelling rules")
    def test_windows_trailing_dot_or_space_directory_alias_is_refused(self):
        directory = self.exe.parent / "working"
        directory.mkdir()
        for suffix in (".", " "):
            with self.subTest(suffix=suffix), self.assertRaises(AffinityError):
                make_plan(self.exe, mask=1, cwd=str(directory) + suffix, backend=FakeBackend())

    def test_duplicate_exact_path_refused(self):
        backend = FakeBackend(pids=(1234,))
        with self.assertRaises(AffinityError):
            make_plan(self.exe, mask=1, backend=backend)
        self.assertNotIn("create", backend.events)

    def test_explicit_duplicate_override_is_recorded(self):
        result = make_plan(self.exe, mask=1, allow_existing=True, backend=FakeBackend(pids=(1234,)))
        self.assertTrue(result["allow_existing"])
        self.assertEqual(result["duplicates"]["pids"], [1234])

    def test_incomplete_duplicate_visibility_is_recorded(self):
        result = make_plan(self.exe, mask=1, backend=FakeBackend(unqueryable=3, truncated=True))
        self.assertEqual(result["duplicates"]["unqueryable"], 3)
        self.assertTrue(result["duplicates"]["truncated"])

    def test_arguments_are_literal_and_input_list_is_copied(self):
        arguments = ["spaces here", 'embedded"quote', "tail\\", "&", "|", "$(fictional)", ""]
        result = make_plan(self.exe, mask=1, args=arguments, backend=FakeBackend())
        self.assertEqual(result["args"], arguments)
        self.assertIn("fictional app.exe", result["command_line"])
        arguments.append("external mutation")
        self.assertNotIn("external mutation", result["args"])
        json.dumps(result, allow_nan=False)

    def test_null_and_surrogate_arguments_refused(self):
        for value in ("bad\0argument", "\ud800", 2, True):
            with self.subTest(value=repr(value)), self.assertRaises(AffinityError):
                make_plan(self.exe, mask=1, args=[value], backend=FakeBackend())

    def test_utf16_command_line_limit(self):
        for argument in ("x" * 32767, "\U0001f600" * 17000):
            with self.subTest(kind=argument[:1]), self.assertRaises(AffinityError):
                make_plan(self.exe, mask=1, args=[argument], backend=FakeBackend())

    def test_linked_executable_is_refused(self):
        link = self.exe.parent / "linked.exe"
        try:
            link.symlink_to(self.exe)
        except OSError:
            self.skipTest("Account lacks symlink creation permission")
        with self.assertRaises(AffinityError):
            make_plan(link, mask=1, backend=FakeBackend())

    def test_linked_working_directory_is_refused(self):
        target = self.exe.parent / "real folder"
        target.mkdir()
        link = self.exe.parent / "linked folder"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("Account lacks symlink creation permission")
        with self.assertRaises(AffinityError):
            make_plan(self.exe, mask=1, cwd=link, backend=FakeBackend())
