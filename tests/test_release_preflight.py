"""Disposable component-release checks; no installed server or game is used."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_public_additions import Fixture, load, ROOT

preflight = load("release_preflight", "tools/release-preflight/preflight.py")


class ReleaseFixture(Fixture):
    def setUp(self):
        super().setUp()
        self.candidate = self.root
        self.current = self.parent / "current"
        self.current.mkdir()

    def metadata(self, name="manifest.json", value=None, raw=None):
        path = self.parent / name
        if raw is None:
            raw = json.dumps(value).encode()
        path.write_bytes(raw)
        return path, hashlib.sha256(raw).hexdigest()

    def manifest(self, names=("bin/program.py",)):
        rows = []
        for name in names:
            path = self.candidate / name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(
                    b"raise RuntimeError('must never execute this fixture')\n"
                )
            data = path.read_bytes()
            rows.append(
                dict(path=name, size=len(data), sha256=hashlib.sha256(data).hexdigest())
            )
        return self.metadata(value=dict(schema_version=1, inventory=rows))

    def specification(self, **overrides):
        data = dict(
            schema_version=1,
            executable="bin/program.py",
            working_directory=".",
            arguments=["--demo"],
        )
        data.update(overrides)
        return self.metadata("launcher.json", data)

    def verify(self):
        manifest, pin = self.manifest()
        return preflight.verify(self.candidate, manifest, pin)


class ManifestAndCandidateTests(ReleaseFixture):
    def test_exact_candidate_passes_without_execution_or_mutation(self):
        manifest, pin = self.manifest()
        original = (self.candidate / "bin/program.py").read_bytes()
        root, rows = preflight.verify(self.candidate, manifest, pin)
        self.assertEqual(root, self.candidate)
        self.assertEqual(len(rows), 1)
        self.assertEqual((self.candidate / "bin/program.py").read_bytes(), original)

    def test_external_pin_required_and_exact(self):
        manifest, pin = self.manifest()
        for bad in (None, "", pin.upper(), "0" * 64):
            with self.subTest(pin=bad), self.assertRaises(preflight.PreflightError):
                preflight.verify(self.candidate, manifest, bad)

    def test_manifest_change_is_refused(self):
        manifest, pin = self.manifest()
        manifest.write_bytes(manifest.read_bytes() + b" ")
        with self.assertRaisesRegex(preflight.PreflightError, "PIN_MISMATCH"):
            preflight.verify(self.candidate, manifest, pin)

    def test_manifest_inside_candidate_is_refused(self):
        manifest, pin = self.manifest()
        inside = self.candidate / "manifest.json"
        inside.write_bytes(manifest.read_bytes())
        with self.assertRaisesRegex(preflight.PreflightError, "MUST_BE_EXTERNAL"):
            preflight.verify(self.candidate, inside, pin)

    def test_duplicate_json_keys_and_nonstandard_numbers_are_refused(self):
        for raw in (
            b'{"schema_version":1,"schema_version":1,"inventory":[]}',
            b'{"value":NaN}',
        ):
            path, pin = self.metadata(raw=raw)
            with self.subTest(raw=raw), self.assertRaises(preflight.PreflightError):
                preflight.pinned_json(path, pin)

    def test_invalid_inventory_contracts_are_refused(self):
        for value in (
            {},
            dict(schema_version=True, inventory=[]),
            dict(schema_version=1, inventory=[]),
            dict(schema_version=1, inventory=[], extra=1),
        ):
            with self.subTest(value=value), self.assertRaises(preflight.PreflightError):
                preflight.manifest_rows(value)

    def test_unsafe_cross_platform_paths_are_refused(self):
        for value in (
            "../x",
            "/x",
            "a//b",
            "a/./b",
            "a\\b",
            "a:b",
            "nul.txt",
            "COM1",
            "bad.",
            "bad ",
            "a\x00b",
            ".git/config",
            "e\u0301.txt",
            "a/" * 33 + "x",
        ):
            with self.subTest(value=value), self.assertRaises(preflight.PreflightError):
                preflight.relative_name(value)

    def test_duplicate_case_prefix_and_file_directory_collisions_are_refused(self):
        for names in (("a", "a"), ("Bin/a", "bin/b"), ("a", "a/b")):
            rows = [dict(path=name, size=0, sha256="0" * 64) for name in names]
            with self.subTest(names=names), self.assertRaises(preflight.PreflightError):
                preflight.manifest_rows(dict(schema_version=1, inventory=rows))

    def test_size_type_hash_and_count_limits_are_refused(self):
        valid = dict(path="x", size=0, sha256="0" * 64)
        for field, value in (
            ("size", True),
            ("size", -1),
            ("size", preflight.MAX_FILE + 1),
            ("sha256", "bad"),
        ):
            row = {**valid, field: value}
            with (
                self.subTest(field=field, value=value),
                self.assertRaises(preflight.PreflightError),
            ):
                preflight.manifest_rows(dict(schema_version=1, inventory=[row]))
        with (
            patch.object(preflight, "MAX_FILES", 1),
            self.assertRaises(preflight.PreflightError),
        ):
            preflight.manifest_rows(
                dict(schema_version=1, inventory=[valid, {**valid, "path": "y"}])
            )

    def test_extra_file_is_refused(self):
        manifest, pin = self.manifest()
        (self.candidate / "unlisted.txt").write_bytes(b"fictional")
        with self.assertRaisesRegex(preflight.PreflightError, "UNLISTED_FILE"):
            preflight.verify(self.candidate, manifest, pin)

    def test_extra_empty_directory_is_refused(self):
        manifest, pin = self.manifest()
        (self.candidate / "unlisted").mkdir()
        with self.assertRaisesRegex(preflight.PreflightError, "UNLISTED_DIRECTORY"):
            preflight.verify(self.candidate, manifest, pin)

    def test_missing_changed_and_wrong_size_files_are_refused(self):
        manifest, pin = self.manifest()
        path = self.candidate / "bin/program.py"
        original = path.read_bytes()
        for replacement in (b"z" * len(original), b"x", None):
            if replacement is None:
                path.unlink()
            else:
                path.write_bytes(replacement)
            with (
                self.subTest(replacement=replacement),
                self.assertRaises(preflight.PreflightError),
            ):
                preflight.verify(self.candidate, manifest, pin)

    def test_entry_and_metadata_limits_are_enforced(self):
        manifest, pin = self.manifest()
        with (
            patch.object(preflight, "MAX_ENTRIES", 1),
            self.assertRaises(preflight.PreflightError),
        ):
            preflight.verify(self.candidate, manifest, pin)
        with (
            patch.object(preflight, "MAX_METADATA", 1),
            self.assertRaises(preflight.PreflightError),
        ):
            preflight.pinned_json(manifest, pin)

    def test_changed_input_identity_is_refused(self):
        manifest, _ = self.manifest()
        actual_identity = preflight.identity
        counter = 0

        def changed(info):
            nonlocal counter
            counter += 1
            result = actual_identity(info)
            return (*result[:-1], result[-1] + 1) if counter == 3 else result

        with (
            patch.object(preflight, "identity", side_effect=changed),
            self.assertRaisesRegex(preflight.PreflightError, "INPUT_CHANGED"),
        ):
            preflight.hash_file(manifest)

    def test_candidate_symlink_is_refused(self):
        manifest, pin = self.manifest()
        target = self.candidate / "bin/program.py"
        link = self.candidate / "linked.py"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("Native symlink creation is unavailable")
        with self.assertRaises(preflight.PreflightError):
            preflight.verify(self.candidate, manifest, pin)

    def test_candidate_hardlink_is_refused(self):
        manifest, pin = self.manifest()
        try:
            os.link(self.candidate / "bin/program.py", self.parent / "linked.py")
        except OSError:
            self.skipTest("Native hardlink creation is unavailable")
        with self.assertRaisesRegex(preflight.PreflightError, "HARDLINK"):
            preflight.verify(self.candidate, manifest, pin)


class PlanAndLauncherTests(ReleaseFixture):
    def test_plan_classifies_add_replace_unchanged_and_preserves_inputs(self):
        manifest, pin = self.manifest(("add.txt", "replace.txt", "same.txt"))
        (self.current / "replace.txt").write_bytes(b"old version")
        same = (self.candidate / "same.txt").read_bytes()
        (self.current / "same.txt").write_bytes(same)
        private = self.current / "unlisted-private.txt"
        private.write_bytes(b"fictional unlisted data")
        before = {p.name: p.read_bytes() for p in self.current.iterdir()}
        result = preflight.update_plan(self.candidate, self.current, manifest, pin)
        self.assertEqual(result["counts"], dict(ADD=1, REPLACE=1, UNCHANGED=1))
        self.assertFalse(result["execution_performed"])
        self.assertEqual(
            {p.name: p.read_bytes() for p in self.current.iterdir()}, before
        )
        self.assertNotIn(private.name, json.dumps(result))

    def test_unlisted_current_data_is_never_opened(self):
        manifest, pin = self.manifest()
        private = self.current / "private.json"
        private.write_bytes(b"fictional")
        actual = preflight.hash_file

        def guarded(path, **kwargs):
            self.assertNotEqual(Path(path), private)
            return actual(path, **kwargs)

        with patch.object(preflight, "hash_file", side_effect=guarded):
            preflight.update_plan(self.candidate, self.current, manifest, pin)

    def test_current_path_file_directory_conflict_is_refused(self):
        manifest, pin = self.manifest()
        (self.current / "bin").write_bytes(b"blocking file")
        with self.assertRaises(preflight.PreflightError):
            preflight.update_plan(self.candidate, self.current, manifest, pin)

    def test_nested_roots_are_refused(self):
        manifest, pin = self.manifest()
        with self.assertRaisesRegex(preflight.PreflightError, "NESTED"):
            preflight.update_plan(self.candidate, self.parent, manifest, pin)

    def test_total_current_bytes_are_bounded(self):
        manifest, pin = self.manifest()
        (self.current / "bin").mkdir()
        (self.current / "bin/program.py").write_bytes(b"x" * 200)
        with (
            patch.object(preflight, "MAX_TOTAL", 100),
            self.assertRaises(preflight.PreflightError),
        ):
            preflight.update_plan(self.candidate, self.current, manifest, pin)

    def test_launcher_checks_structure_without_exposing_arguments(self):
        manifest, pin = self.manifest()
        secret = "fictional-private-argument"
        spec, spec_pin = self.specification(arguments=[secret])
        result = preflight.launcher_check(self.candidate, manifest, pin, spec, spec_pin)
        self.assertEqual(result["argument_count"], 1)
        self.assertTrue(result["executable_listed_and_verified"])
        self.assertNotIn(secret, json.dumps(result))
        self.assertFalse(result["execution_performed"])

    def test_launcher_unlisted_executable_and_missing_working_directory_refused(self):
        manifest, pin = self.manifest()
        for kwargs in (
            dict(executable="missing.py"),
            dict(working_directory="missing"),
            dict(working_directory="../outside"),
            dict(executable="../outside"),
        ):
            spec, spec_pin = self.specification(**kwargs)
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaises((preflight.PreflightError, OSError)),
            ):
                preflight.launcher_check(self.candidate, manifest, pin, spec, spec_pin)

    def test_launcher_bad_argument_vectors_refused(self):
        manifest, pin = self.manifest()
        for args in (
            "--demo",
            [1],
            ["line\nbreak"],
            ["x"] * 65,
            ["x" * 2049],
            ["x" * 2048] * 5,
        ):
            spec, spec_pin = self.specification(arguments=args)
            with (
                self.subTest(args_type=type(args).__name__),
                self.assertRaises(preflight.PreflightError),
            ):
                preflight.launcher_check(self.candidate, manifest, pin, spec, spec_pin)

    def test_launcher_unknown_fields_and_inside_spec_refused(self):
        manifest, pin = self.manifest()
        spec, spec_pin = self.specification(environment={"fictional": "value"})
        with self.assertRaises(preflight.PreflightError):
            preflight.launcher_check(self.candidate, manifest, pin, spec, spec_pin)
        inside = self.candidate / "launcher.json"
        inside.write_bytes(spec.read_bytes())
        with self.assertRaises(preflight.PreflightError):
            preflight.launcher_check(self.candidate, manifest, pin, inside, spec_pin)

    def test_report_requires_new_external_path(self):
        manifest, pin = self.manifest()
        result = preflight.update_plan(self.candidate, self.current, manifest, pin)
        for destination in (
            self.candidate / "report.json",
            self.current / "report.json",
            ROOT / "report.json",
        ):
            with (
                self.subTest(destination=destination.name),
                self.assertRaises(preflight.PreflightError),
            ):
                preflight.write_report(
                    destination, result, [self.candidate, self.current]
                )
        destination = self.parent / "report.json"
        preflight.write_report(destination, result, [self.candidate, self.current])
        before = destination.read_bytes()
        with self.assertRaises(FileExistsError):
            preflight.write_report(destination, result, [self.candidate, self.current])
        self.assertEqual(destination.read_bytes(), before)
        self.assertNotIn(str(self.parent), before.decode())

    def test_cli_errors_do_not_echo_paths_or_argument_values(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = preflight.main(
                [
                    "verify",
                    "--candidate",
                    str(self.candidate),
                    "--manifest",
                    "fictional-missing",
                    "--manifest-sha",
                    "not-a-pin",
                ]
            )
        self.assertEqual(code, 2)
        self.assertNotIn(str(self.parent), output.getvalue())
        self.assertNotIn("fictional-missing", output.getvalue())

    def test_actual_cli_reports_success_without_running_payload(self):
        manifest, pin = self.manifest()
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/release-preflight/preflight.py"),
                "verify",
                "--candidate",
                str(self.candidate),
                "--manifest",
                str(manifest),
                "--manifest-sha",
                pin,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["files_verified"], 1)
        self.assertFalse(json.loads(result.stdout)["execution_performed"])


if __name__ == "__main__":
    unittest.main()
