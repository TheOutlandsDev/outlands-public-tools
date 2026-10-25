"""Fictional locks only; no package download, artifact, resolver or installer."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/dependency-lock-diff/lock_diff.py"
spec = importlib.util.spec_from_file_location("fictional_lock_diff", SCRIPT)
diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diff)
HASH_A = hashlib.sha256(b"Fictional artifact A").hexdigest()
HASH_B = hashlib.sha256(b"Fictional artifact B").hexdigest()


def pin(name="sample-package", version="1.0", digest=HASH_A):
    return f"{name}=={version} \\\n    --hash=sha256:{digest}\n".encode()


def lock(records, *, comments=False):
    return (b"# Fictional metadata only\n\n" if comments else b"") + b"".join(
        pin(*row) for row in sorted(records)
    )


class Fixture(unittest.TestCase):
    def setUp(self):
        base = Path(
            os.environ.get("OUTLANDS_TEST_TEMP", tempfile.gettempdir())
        ).resolve()
        self.temporary = tempfile.TemporaryDirectory(dir=base)
        self.parent = Path(self.temporary.name)

        def cleanup():
            target = self.parent.resolve()
            if target == base or not target.is_relative_to(base):
                raise RuntimeError("UNEXPECTED_CLEANUP_TARGET")
            self.temporary.cleanup()

        self.addCleanup(cleanup)

    def file(self, data=None, name="fictional.lock"):
        path = self.parent / name
        path.write_bytes(pin() if data is None else data)
        return path

    def rejected(self, data, code=None):
        with self.assertRaises(diff.DiffError) as caught:
            diff.parse_lock(data)
        if code:
            self.assertEqual(str(caught.exception), code)

    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = diff.main(list(map(str, args)))
        return code, out.getvalue(), err.getvalue()


class ParserTests(Fixture):
    def test_exact_byte_bound_can_hold_a_valid_lock(self):
        value = pin()
        remaining = diff.MAX_LOCK_BYTES - len(value)
        while remaining:
            width = min(512, remaining)
            if width == 1:
                value += b"\n"
            else:
                value += b"#" + b"x" * (width - 2) + b"\n"
            remaining -= width
        self.assertEqual(len(value), diff.MAX_LOCK_BYTES)
        self.assertEqual(len(diff.parse_lock(value)), 1)

    def test_parses_sorted_canonical_records_and_normalizes_hash_case(self):
        value = pin("sample-alpha", "1.0", HASH_A.upper()) + pin(
            "sample-beta", "2!1.0rc2.post3.dev4+local.5", HASH_B
        )
        parsed = diff.parse_lock(value)
        self.assertEqual(list(parsed), ["sample-alpha", "sample-beta"])
        self.assertEqual(parsed["sample-alpha"], dict(version="1.0", sha256=HASH_A))

    def test_only_nonempty_bounded_bytes_are_accepted(self):
        for value in (None, "fictional", bytearray(pin()), b"", b"x" * (1048576 + 1)):
            self.rejected(value, "INPUT_SIZE_LIMIT")
        for value in (b"\n", b"# Fictional comments only\n"):
            self.rejected(value, "EMPTY_LOCK")

    def test_bom_line_endings_and_comments_match_existing_grammar(self):
        for ending in (b"\n", b"\r\n", b"\r"):
            value = b"\xef\xbb\xbf# Fictional comment\n\n" + pin()
            self.assertEqual(
                diff.parse_lock(value.replace(b"\n", ending)), diff.parse_lock(pin())
            )

    def test_bad_encoding_and_control_characters_are_refused(self):
        self.rejected(b"\xff", "LOCK_ENCODING_INVALID")
        for char in (b"\x00", b"\t", b"\x1b", b"\x0b"):
            self.rejected(
                b"# Fictional" + char + b"\n" + pin(), "LOCK_CONTROL_CHARACTER"
            )

    def test_names_must_be_canonical_and_bounded(self):
        for name in (
            "Sample-Package",
            "sample_package",
            "sample.package",
            "sample--package",
        ):
            self.rejected(pin(name), "PACKAGE_NAME_NONCANONICAL")
        for name in ("-sample", "sample-", "a" * 201):
            self.rejected(pin(name), "PACKAGE_NAME_INVALID")
        for name in ("a", "a" * 200, "sample-123"):
            self.assertIn(name, diff.parse_lock(pin(name)))

    def test_supported_version_subset_preserves_text(self):
        for version in (
            "1",
            "1.0",
            "1.0.0",
            "1.0a1",
            "1.0b2",
            "1.0rc3",
            "1.0.post1",
            "1.0.dev2",
            "2!1.0rc2.post3.dev4+local.5",
            "1" * 128,
        ):
            self.assertEqual(
                diff.parse_lock(pin(version=version))["sample-package"]["version"],
                version,
            )

    def test_unsupported_versions_and_general_requirements_are_refused(self):
        for version in ("v1.0", "1.*", "1.0RC1", "1.0;marker", "fictional", "1" * 129):
            self.rejected(pin(version=version), "VERSION_UNSUPPORTED")
        for value in (
            b"sample>=1.0\n",
            b"sample[extra]==1.0\n",
            b"--index-url https://example.com/simple\n",
            b"-r fictional.lock\n",
            b"sample @ https://example.com/fictional.whl\n",
            b"sample==1.0 ; python_version > '3'\n",
        ):
            self.rejected(value, "LOCK_LINE_INVALID")

    def test_hash_line_is_exact_and_immediately_adjacent(self):
        header = pin().splitlines()[0] + b"\n"
        for trailer in (
            b"",
            b"\n",
            b"# Fictional comment\n",
            b"   --hash=sha256:" + HASH_A.encode() + b"\n",
            b"    --hash=sha256:" + b"a" * 63 + b"\n",
            b"    --hash=sha512:" + HASH_A.encode() + b"\n",
        ):
            self.rejected(header + trailer, "ADJACENT_SHA256_REQUIRED")

    def test_orphan_extra_hash_and_unknown_active_lines_fail(self):
        for value in (
            pin() + pin().splitlines()[1] + b"\n",
            pin() + b"fictional-private-canary\n",
            pin().splitlines()[1] + b"\n",
        ):
            self.rejected(value, "LOCK_LINE_INVALID")

    def test_duplicates_and_unsorted_packages_fail(self):
        self.rejected(pin() + pin(), "DUPLICATE_PACKAGE")
        self.rejected(pin("sample-z") + pin("sample-a"), "PACKAGE_ORDER_INVALID")

    def test_line_count_and_length_bounds(self):
        self.rejected(b"#" + b"x" * 512 + b"\n" + pin(), "LOCK_STRUCTURE_LIMIT")
        self.rejected(b"\n" * 6000 + pin(), "LOCK_STRUCTURE_LIMIT")
        self.assertEqual(len(diff.parse_lock(b"#" + b"x" * 511 + b"\n" + pin())), 1)

    def test_package_count_maximum_and_overflow(self):
        value = b"".join(pin(f"sample-{i:04}") for i in range(2000))
        self.assertEqual(len(diff.parse_lock(value)), 2000)
        self.rejected(value + pin("sample-2000"), "LOCK_PACKAGE_LIMIT")


class ComparisonTests(Fixture):
    def test_ignored_comments_are_not_copied_into_results(self):
        result = diff.compare_locks(pin(), b"# fictional-private-canary\n" + pin())
        self.assertEqual(result["status"], "MATCHING_LOCK_RECORDS")
        self.assertNotIn("fictional-private-canary", diff.render_report(result))
        self.assertNotEqual(
            result["input_sha256"]["before"], result["input_sha256"]["after"]
        )

    def test_matching_records_preserve_input_hashes_and_false_flags(self):
        result = diff.compare_locks(pin(), pin())
        self.assertEqual(result["status"], "MATCHING_LOCK_RECORDS")
        self.assertEqual(
            result["counts"],
            dict(
                before=1,
                after=1,
                only_in_before=0,
                only_in_after=0,
                version_text_changed=0,
                hash_only_changed=0,
                unchanged=1,
            ),
        )
        self.assertTrue(all(result[key] is False for key in diff._flags()))
        self.assertEqual(
            result["input_sha256"]["before"], hashlib.sha256(pin()).hexdigest()
        )

    def test_comments_bom_line_endings_and_hash_case_do_not_change_records(self):
        before = pin()
        after = b"\xef\xbb\xbf# Fictional comment\r\n" + pin(
            digest=HASH_A.upper()
        ).replace(b"\n", b"\r\n")
        result = diff.compare_locks(before, after)
        self.assertEqual(result["status"], "MATCHING_LOCK_RECORDS")
        self.assertNotEqual(
            result["input_sha256"]["before"], result["input_sha256"]["after"]
        )

    def test_only_in_before_and_after_do_not_claim_installed_changes(self):
        result = diff.compare_locks(pin("sample-old"), pin("sample-new", digest=HASH_B))
        self.assertEqual(result["counts"]["only_in_before"], 1)
        self.assertEqual(result["counts"]["only_in_after"], 1)
        for row in result["rows"]:
            self.assertIsNone(row["version_text_changed"])
            self.assertIsNone(row["hash_changed"])
        self.assertFalse(result["environment_inspected"])

    def test_version_change_can_coexist_with_hash_change(self):
        for digest, expected in ((HASH_A, False), (HASH_B, True)):
            result = diff.compare_locks(pin(), pin(version="2.0", digest=digest))
            row = result["rows"][0]
            self.assertEqual(row["classification"], "VERSION_TEXT_CHANGED")
            self.assertIs(row["version_text_changed"], True)
            self.assertIs(row["hash_changed"], expected)
            self.assertEqual(result["counts"]["hash_only_changed"], 0)

    def test_hash_only_change_keeps_version_text(self):
        result = diff.compare_locks(pin(), pin(digest=HASH_B))
        row = result["rows"][0]
        self.assertEqual(row["classification"], "HASH_ONLY_CHANGED")
        self.assertIs(row["version_text_changed"], False)
        self.assertIs(row["hash_changed"], True)

    def test_semantically_similar_versions_are_still_text_changes_without_ranking(self):
        for version in ("1", "1.0.0", "0.9", "9.0", "1.0rc1", "2!1.0"):
            result = diff.compare_locks(pin(), pin(version=version))
            self.assertEqual(
                result["rows"][0]["classification"], "VERSION_TEXT_CHANGED"
            )
            self.assertFalse(result["upgrade_direction_inferred"])

    def test_mixed_changes_counts_and_deterministic_name_order(self):
        a = lock(
            [
                ("sample-a", "1", HASH_A),
                ("sample-b", "1", HASH_A),
                ("sample-c", "1", HASH_A),
                ("sample-z", "1", HASH_A),
            ]
        )
        b = lock(
            [
                ("sample-a", "2", HASH_B),
                ("sample-b", "1", HASH_B),
                ("sample-d", "1", HASH_A),
                ("sample-z", "1", HASH_A),
            ]
        )
        result = diff.compare_locks(a, b)
        self.assertEqual(
            result["counts"],
            dict(
                before=4,
                after=4,
                only_in_before=1,
                only_in_after=1,
                version_text_changed=1,
                hash_only_changed=1,
                unchanged=1,
            ),
        )
        self.assertEqual(
            [row["name"] for row in result["rows"]],
            ["sample-a", "sample-b", "sample-c", "sample-d", "sample-z"],
        )

    def test_reverse_comparison_swaps_records_and_presence_counts(self):
        a = pin("sample-a") + pin("sample-z")
        b = pin("sample-b") + pin("sample-z", version="2")
        left, right = diff.compare_locks(a, b), diff.compare_locks(b, a)
        self.assertEqual(
            left["counts"]["only_in_before"], right["counts"]["only_in_after"]
        )
        for one, two in zip(left["rows"], right["rows"]):
            self.assertEqual(one["before"], two["after"])
            self.assertEqual(one["after"], two["before"])

    def test_maximum_size_comparison_stays_bounded(self):
        a = b"".join(pin(f"sample-a-{i:04}") for i in range(2000))
        b = b"".join(pin(f"sample-b-{i:04}") for i in range(2000))
        result = diff.compare_locks(a, b)
        self.assertEqual(len(result["rows"]), 4000)
        self.assertLess(len(diff.render_report(result)), diff.MAX_OUTPUT_BYTES)


class ReferenceTests(Fixture):
    @staticmethod
    def legacy_validator():
        root = ROOT / "tools/dependency-lock-tools"
        spec = importlib.util.spec_from_file_location(
            "lock_common", root / "lock_common.py"
        )
        common = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(common)
        with patch.dict(sys.modules, {"lock_common": common}):
            spec = importlib.util.spec_from_file_location(
                "public_legacy_validator", root / "verify_locks.py"
            )
            verifier = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(verifier)
        return common, verifier

    def test_100_seeded_valid_locks_match_existing_public_validator(self):
        _, verifier = self.legacy_validator()
        rng = random.Random(1801)
        for _ in range(100):
            records = [
                (
                    f"sample-{i:03}",
                    rng.choice(("1", "1.0rc1", "2!1.0+local.2")),
                    rng.choice((HASH_A, HASH_B)),
                )
                for i in range(rng.randrange(1, 40))
            ]
            value = lock(records, comments=bool(rng.randrange(2)))
            if rng.randrange(2):
                value = value.replace(b"\n", b"\r\n")
            if rng.randrange(2):
                value = b"\xef\xbb\xbf" + value
            self.assertEqual(len(diff.parse_lock(value)), verifier.validate_lock(value))

    def test_20_malformed_variants_are_rejected_by_both_parsers(self):
        common, verifier = self.legacy_validator()
        values = [
            b"",
            b"\xff",
            b"# only fictional comments\n",
            b"--index-url https://example.com/simple\n",
            pin() + pin(),
            pin("sample-z") + pin("sample-a"),
            pin("Sample"),
            pin("sample_name"),
            pin(version="v1.0"),
            pin(version="1.*"),
            pin(version="1.0RC1"),
            pin(digest="x" * 64),
            pin(digest="a" * 63),
            pin().splitlines()[0] + b"\n",
            pin().splitlines()[1] + b"\n",
            pin().replace(b"    --hash", b"\t--hash"),
            pin() + b"unexpected\n",
            b"sample>=1\n",
            b"sample[extra]==1\n",
            b"sample @ https://example.com/fictional.whl\n",
        ]
        self.assertEqual(len(values), 20)
        for value in values:
            with self.assertRaises(common.LockError):
                verifier.validate_lock(value)
            with self.assertRaises(diff.DiffError):
                diff.parse_lock(value)

    def test_300_seeded_comparisons_match_independent_list_search(self):
        rng = random.Random(1802)
        for _ in range(300):
            sides = []
            for side in range(2):
                records = [
                    (
                        f"sample-{i:02}",
                        rng.choice(("1", "1.0", "2.0", "1.0rc1")),
                        rng.choice((HASH_A, HASH_B)),
                    )
                    for i in range(12)
                    if rng.randrange(3)
                ]
                sides.append(records or [("sample-fallback", "1", HASH_A)])
            result = diff.compare_locks(lock(sides[0]), lock(sides[1]))
            for row in result["rows"]:
                a = next((r for r in sides[0] if r[0] == row["name"]), None)
                b = next((r for r in sides[1] if r[0] == row["name"]), None)
                expected = (
                    "ONLY_IN_AFTER"
                    if a is None
                    else "ONLY_IN_BEFORE"
                    if b is None
                    else "VERSION_TEXT_CHANGED"
                    if a[1] != b[1]
                    else "HASH_ONLY_CHANGED"
                    if a[2] != b[2]
                    else "UNCHANGED"
                )
                self.assertEqual(row["classification"], expected)


class ReaderAndCliTests(Fixture):
    def test_reads_exactly_selected_files_without_scan_or_mutation(self):
        a, b = self.file(name="before.lock"), self.file(name="after.lock")
        before = {p.name: p.read_bytes() for p in self.parent.iterdir()}
        opened = []
        original = diff._read_bytes

        def track(path, limit):
            opened.append(path)
            return original(path, limit)

        with (
            patch.object(diff, "_read_bytes", side_effect=track),
            patch.object(os, "scandir", side_effect=AssertionError("NO_SCAN")),
            patch.object(socket, "socket", side_effect=AssertionError("NO_NETWORK")),
        ):
            self.assertEqual(
                diff.read_and_compare(a, b)["status"], "MATCHING_LOCK_RECORDS"
            )
        self.assertEqual(opened, [a, b])
        self.assertEqual(
            {p.name: p.read_bytes() for p in self.parent.iterdir()}, before
        )

    def test_pure_compare_has_no_file_clock_process_or_network_access(self):
        with contextlib.ExitStack() as stack:
            for name in (
                "builtins.open",
                "os.open",
                "os.scandir",
                "os.system",
                "socket.socket",
                "subprocess.Popen",
                "time.time",
                "pathlib.Path.stat",
                "pathlib.Path.unlink",
            ):
                stack.enter_context(
                    patch(name, side_effect=AssertionError("NO_SIDE_EFFECT"))
                )
            self.assertEqual(
                diff.compare_locks(pin(), pin())["status"], "MATCHING_LOCK_RECORDS"
            )

    def test_oversized_file_refused_before_open(self):
        path = self.file(b"x" * 1048577)
        with patch.object(os, "open", side_effect=AssertionError("NO_OPEN")):
            code, out, _ = self.invoke("--before", path, "--after", path)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["code"], "INPUT_BYTE_LIMIT")

    def test_ambiguous_paths_refused_before_metadata(self):
        for name in (
            "../fictional",
            "//fictional-host/share/fictional.lock",
            "C:fictional",
            "nul",
            "fictional. ",
            "fictional:stream",
        ):
            with patch.object(Path, "lstat", side_effect=AssertionError("NO_STAT")):
                self.assertEqual(self.invoke("--before", name, "--after", name)[0], 2)

    def test_missing_and_native_error_details_are_suppressed(self):
        path = self.parent / "fictional-private-canary.lock"
        code, out, err = self.invoke("--before", path, "--after", path)
        self.assertEqual(code, 2)
        self.assertNotIn(str(path), out + err)
        self.assertNotIn("fictional-private-canary", out + err)
        try:
            diff.read_and_compare(path, path)
        except diff.DiffError as error:
            self.assertNotIn(str(path), "".join(traceback.format_exception(error)))
            self.assertTrue(error.__suppress_context__)
        else:
            self.fail("EXPECTED_ERROR")

    def test_directory_and_hardlinks_are_refused(self):
        self.assertEqual(
            self.invoke("--before", self.parent, "--after", self.parent)[0], 2
        )
        path = self.file()
        try:
            os.link(path, self.parent / "fictional-linked.lock")
        except OSError:
            self.skipTest("Native hardlink creation unavailable")
        self.assertEqual(self.invoke("--before", path, "--after", path)[0], 2)

    def test_symlink_input_and_linked_ancestor_are_refused(self):
        path = self.file()
        leaf = self.parent / "fictional-link.lock"
        folder = self.parent / "fictional-folder-link"
        try:
            leaf.symlink_to(path)
            folder.symlink_to(self.parent, target_is_directory=True)
        except OSError:
            self.skipTest("Native symlink creation unavailable")
        self.assertEqual(self.invoke("--before", leaf, "--after", path)[0], 2)
        self.assertEqual(
            self.invoke("--before", folder / path.name, "--after", path)[0], 2
        )

    def test_reparse_and_missing_identity_are_refused_synthetically(self):
        path = self.file()
        real = path.lstat()
        for changes in (dict(st_ino=0), dict(st_file_attributes=0x400)):
            fake = SimpleNamespace(
                **{
                    key: getattr(real, key)
                    for key in dir(real)
                    if key.startswith("st_")
                }
            )
            for key, value in changes.items():
                setattr(fake, key, value)
            with patch.object(Path, "lstat", return_value=fake):
                self.assertEqual(self.invoke("--before", path, "--after", path)[0], 2)

    def test_descriptor_and_cross_snapshot_changes_are_refused(self):
        path = self.file()
        real = path.lstat()
        fake = SimpleNamespace(
            **{key: getattr(real, key) for key in dir(real) if key.startswith("st_")}
        )
        fake.st_ino += 1
        with patch.object(os, "fstat", return_value=fake):
            self.assertEqual(self.invoke("--before", path, "--after", path)[0], 2)
        with patch.object(diff, "_fingerprint", return_value=("fictional-change",)):
            code, out, _ = self.invoke("--before", path, "--after", path)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["code"], "INPUT_CHANGED")

    def test_output_bound_refuses_before_partial_comparison(self):
        path = self.file()
        with patch.object(diff, "MAX_OUTPUT_BYTES", 10):
            code, out, err = self.invoke("--before", path, "--after", path)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["code"], "OUTPUT_BYTE_LIMIT")
        self.assertNotIn('"rows"', out)
        self.assertEqual(err, "")

    def test_exit_codes_and_unknown_arguments_do_not_echo_inputs(self):
        a, b = self.file(name="before.lock"), self.file(pin(version="2"), "after.lock")
        self.assertEqual(self.invoke("--before", a, "--after", a)[0], 0)
        self.assertEqual(self.invoke("--before", a, "--after", b)[0], 1)
        for args in (
            (),
            ("--before", a),
            ("--bef", a, "--after", b),
            ("--unknown", "fictional-private-canary"),
        ):
            code, out, err = self.invoke(*args)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out)["code"], "ARGUMENTS_INVALID")
            self.assertNotIn("fictional-private-canary", out + err)

    def test_invalid_lock_content_and_comments_are_not_echoed_in_errors(self):
        path = self.file(b"fictional-private-canary\n")
        code, out, err = self.invoke("--before", path, "--after", path)
        self.assertEqual(code, 2)
        self.assertNotIn("fictional-private-canary", out + err)

    def test_interrupt_is_fixed_exit_130(self):
        with patch.object(diff, "read_and_compare", side_effect=KeyboardInterrupt):
            code, out, err = self.invoke(
                "--before", "fictional.lock", "--after", "fictional.lock"
            )
        self.assertEqual(code, 130)
        self.assertEqual(json.loads(out)["code"], "INTERRUPTED")
        self.assertEqual(err, "")

    def test_single_script_standalone_copy_works_and_preserves_inputs(self):
        path = self.file()
        script = self.parent / "lock_diff.py"
        shutil.copyfile(SCRIPT, script)
        before = path.read_bytes()
        done = subprocess.run(
            [
                sys.executable,
                "-B",
                str(script),
                "--before",
                str(path),
                "--after",
                str(path),
            ],
            cwd=self.parent,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["status"], "MATCHING_LOCK_RECORDS")
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(done.stderr, "")

    def test_shipped_examples_match_documented_counts(self):
        folder = SCRIPT.parent / "examples"
        result = diff.read_and_compare(folder / "before.lock", folder / "after.lock")
        self.assertEqual(
            result["counts"],
            dict(
                before=4,
                after=4,
                only_in_before=1,
                only_in_after=1,
                version_text_changed=1,
                hash_only_changed=1,
                unchanged=1,
            ),
        )
        result = diff.read_and_compare(
            folder / "before.lock", folder / "hash-only.lock"
        )
        self.assertEqual(result["counts"]["hash_only_changed"], 1)
        self.assertEqual(result["counts"]["unchanged"], 3)
        self.assertEqual(
            diff.read_and_compare(folder / "before.lock", folder / "equivalent.lock")[
                "status"
            ],
            "MATCHING_LOCK_RECORDS",
        )


if __name__ == "__main__":
    unittest.main()
