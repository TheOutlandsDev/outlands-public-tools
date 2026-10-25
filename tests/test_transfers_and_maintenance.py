"""Disposable transfer and pure lifecycle-rule checks, without live services."""

import contextlib
from datetime import date
import hashlib
import io
import json
import os
import sqlite3
import unittest
from unittest.mock import patch
from test_public_additions import Fixture, load, ROOT

transfer = load("transfer", "tools/verified-transfers/transfer.py")
maintenance = load("maintenance", "tools/server-maintenance/maintenance.py")


def entry(name, data):
    return dict(path=name, size=len(data), sha256=hashlib.sha256(data).hexdigest())


class TransferFixture(Fixture):
    def manifest(self, rows):
        path = self.parent / "reviewed.json"
        path.write_text(
            json.dumps(dict(schema_version=1, inventory=rows)), encoding="utf-8"
        )
        return path

    def package(self, rows, destination=None):
        manifest = self.manifest(rows)
        pin = hashlib.sha256(manifest.read_bytes()).hexdigest()
        return transfer.package_source(
            self.root,
            manifest,
            destination or self.parent / "bundle",
            expected_manifest_sha=pin,
        )

    def backup(self):
        return transfer.backup(self.root, self.parent / "bundle", confirm_stopped=True)

    def resign(self, bundle, data):
        raw = (json.dumps(data, indent=2) + "\n").encode("utf-8")
        (bundle / transfer.MANIFEST).write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        (bundle / transfer.CHECKSUM).write_bytes(
            (digest + "  " + transfer.MANIFEST + "\n").encode("ascii")
        )
        return digest


class SourcePackageTests(TransferFixture):
    def test_only_reviewed_files_are_copied(self):
        path = self.write("src/demo.py", 'print("fictional")\n')
        self.write(".env", "fictional unselected setting")
        result = self.package([entry("src/demo.py", path.read_bytes())])
        self.assertEqual(result["format"], transfer.SOURCE_FORMAT)
        payload = self.parent / "bundle/payload"
        self.assertEqual((payload / "src/demo.py").read_bytes(), path.read_bytes())
        self.assertFalse((payload / ".env").exists())

    def test_existing_destination_not_modified(self):
        path = self.write("demo.py", "pass\n")
        destination = self.parent / "bundle"
        destination.mkdir()
        retained = destination / "retained.txt"
        retained.write_text("preserve", encoding="utf-8")
        with self.assertRaises(transfer.TransferError):
            self.package([entry("demo.py", path.read_bytes())], destination)
        self.assertEqual(retained.read_text(), "preserve")

    def test_changed_reviewed_source_fails_before_destination_creation(self):
        path = self.write("demo.py", "pass\n")
        row = entry("demo.py", path.read_bytes())
        path.write_text("changed", encoding="utf-8")
        with self.assertRaises(transfer.TransferError):
            self.package([row])
        self.assertFalse((self.parent / "bundle").exists())

    def test_private_source_paths_rejected(self):
        for name in (
            "runtime/demo.py",
            ".env",
            "keys/id_ed25519",
            "private/example.md",
            "state.sqlite3",
        ):
            with self.subTest(name=name), self.assertRaises(transfer.TransferError):
                transfer.validate_inventory([entry(name, b"")], source=True)

    def test_unknown_source_format_rejected(self):
        with self.assertRaises(transfer.TransferError):
            transfer.validate_inventory([entry("game.exe", b"")], source=True)

    def test_non_utf8_and_binary_source_content_rejected(self):
        for data in (b"\xff", b"hello\x00world"):
            path = self.root / "demo.txt"
            path.write_bytes(data)
            with (
                self.subTest(data=data),
                self.assertRaises((transfer.TransferError, UnicodeError)),
            ):
                self.package([entry("demo.txt", data)])
            self.assertFalse((self.parent / "bundle").exists())

    def test_review_manifest_duplicate_json_keys_rejected(self):
        path = self.parent / "reviewed.json"
        path.write_text(
            '{"schema_version":1,"schema_version":1,"inventory":[]}', encoding="utf-8"
        )
        pin = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(transfer.TransferError):
            transfer.package_source(
                self.root, path, self.parent / "bundle", expected_manifest_sha=pin
            )

    def test_source_manifest_pin_is_required_and_bound_to_exact_bytes(self):
        path = self.write("demo.py", "pass\n")
        manifest = self.manifest([entry("demo.py", path.read_bytes())])
        with self.assertRaises(transfer.TransferError):
            transfer.package_source(
                self.root, manifest, self.parent / "bundle", expected_manifest_sha=None
            )
        with self.assertRaises(transfer.TransferError):
            transfer.package_source(
                self.root,
                manifest,
                self.parent / "bundle",
                expected_manifest_sha="0" * 64,
            )
        self.assertFalse((self.parent / "bundle").exists())

    def test_source_files_are_not_changed(self):
        path = self.write("demo.py", "pass\n")
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        self.package([entry("demo.py", path.read_bytes())])
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_source_root_can_contain_unselected_git_metadata(self):
        path = self.write("demo.py", "pass\n")
        self.write(".git/config", "fictional")
        self.package([entry("demo.py", path.read_bytes())])
        self.assertFalse((self.parent / "bundle/payload/.git").exists())

    def test_missing_parent_not_created(self):
        path = self.write("demo.py", "pass\n")
        with self.assertRaises(transfer.TransferError):
            self.package(
                [entry("demo.py", path.read_bytes())], self.parent / "absent/bundle"
            )
        self.assertFalse((self.parent / "absent").exists())

    def test_nested_destination_rejected(self):
        path = self.write("demo.py", "pass\n")
        with self.assertRaises(transfer.TransferError):
            self.package([entry("demo.py", path.read_bytes())], self.root / "bundle")

    def test_explicit_source_file_limit(self):
        self.write("demo.txt", "abc")
        with (
            patch.object(transfer, "SOURCE_FILE_LIMIT", 2),
            self.assertRaises(transfer.TransferError),
        ):
            self.package([entry("demo.txt", b"abc")])

    def test_input_changed_during_creation_refuses_and_retains_partial(self):
        path = self.write("demo.py", "pass\n")
        row = entry("demo.py", path.read_bytes())
        original = transfer.new_destination

        def mutate(destination):
            result = original(destination)
            path.write_text("changed\n", encoding="utf-8")
            return result

        with (
            patch.object(transfer, "new_destination", side_effect=mutate),
            self.assertRaises(transfer.TransferError),
        ):
            self.package([row])
        self.assertTrue((self.parent / "bundle").is_dir())
        self.assertFalse((self.parent / "bundle" / transfer.MANIFEST).exists())


class ManifestValidationTests(unittest.TestCase):
    def test_traversal_absolute_stream_and_noncanonical_paths(self):
        for name in (
            "../escape",
            "/absolute",
            "a//b",
            "a/./b",
            "a\\b",
            "drive:name",
            "a\x00b",
            "trailing.",
            "nul.txt",
        ):
            with self.subTest(name=name), self.assertRaises(transfer.TransferError):
                transfer.validate_inventory([entry(name, b"")])

    def test_case_collisions_include_parent_directories(self):
        for paths in (["A/demo.txt", "a/other.txt"], ["one.txt", "ONE.txt"]):
            with self.subTest(paths=paths), self.assertRaises(transfer.TransferError):
                transfer.validate_inventory([entry(p, b"") for p in paths])

    def test_duplicate_and_file_directory_collisions(self):
        for paths in (["a.txt", "a.txt"], ["a", "a/b.txt"]):
            with self.subTest(paths=paths), self.assertRaises(transfer.TransferError):
                transfer.validate_inventory([entry(p, b"") for p in paths])

    def test_invalid_sizes_hashes_and_unexpected_fields(self):
        for row in (
            dict(path="a.txt", size=True, sha256="0" * 64),
            dict(path="a.txt", size=-1, sha256="0" * 64),
            dict(path="a.txt", size=0, sha256="invalid"),
            dict(path="a.txt", size=0, sha256="0" * 64, extra="value"),
        ):
            with self.subTest(row=row), self.assertRaises(transfer.TransferError):
                transfer.validate_inventory([row])

    def test_count_and_total_limits(self):
        with (
            patch.object(transfer, "MAX_FILES", 1),
            self.assertRaises(transfer.TransferError),
        ):
            transfer.validate_inventory([entry("a.txt", b""), entry("b.txt", b"")])
        with (
            patch.object(transfer, "MAX_TOTAL", 2),
            self.assertRaises(transfer.TransferError),
        ):
            transfer.validate_inventory([entry("a.txt", b"abc")])


class DataHandoffTests(TransferFixture):
    def test_backup_verify_restore_round_trip(self):
        original = self.write("config/settings.json", '{"fictional":true}')
        self.write("state/empty.bin", "")
        result = self.backup()
        bundle = self.parent / "bundle"
        pin = result["manifest_sha256"]
        self.assertEqual(transfer.verify(bundle, expected_manifest_sha=pin), result)
        transfer.restore(
            bundle,
            self.parent / "restored",
            expected_manifest_sha=pin,
            confirm_stopped=True,
        )
        self.assertEqual(
            (self.parent / "restored/config/settings.json").read_bytes(),
            original.read_bytes(),
        )
        self.assertEqual((self.parent / "restored/state/empty.bin").read_bytes(), b"")

    def test_stopped_assertion_required_for_backup_and_restore(self):
        self.write("data.bin", "fictional")
        with self.assertRaises(transfer.TransferError):
            transfer.backup(self.root, self.parent / "bundle")
        result = self.backup()
        with self.assertRaises(transfer.TransferError):
            transfer.restore(
                self.parent / "bundle",
                self.parent / "restore",
                expected_manifest_sha=result["manifest_sha256"],
            )

    def test_restore_requires_actual_trusted_pin(self):
        self.write("data.bin", "fictional")
        self.backup()
        with self.assertRaises(transfer.TransferError):
            transfer.restore(
                self.parent / "bundle",
                self.parent / "restore",
                expected_manifest_sha=None,
                confirm_stopped=True,
            )
        self.assertFalse((self.parent / "restore").exists())

    def test_existing_restore_target_preserved(self):
        self.write("data.bin", "fictional")
        result = self.backup()
        destination = self.parent / "restore"
        destination.mkdir()
        with self.assertRaises(transfer.TransferError):
            transfer.restore(
                self.parent / "bundle",
                destination,
                expected_manifest_sha=result["manifest_sha256"],
                confirm_stopped=True,
            )
        self.assertEqual(list(destination.iterdir()), [])

    def test_tampered_payload_fails_before_restore_writes(self):
        self.write("data.bin", "fictional")
        result = self.backup()
        bundle = self.parent / "bundle"
        (bundle / "payload/data.bin").write_bytes(b"changed")
        with self.assertRaises(transfer.TransferError):
            transfer.restore(
                bundle,
                self.parent / "restore",
                expected_manifest_sha=result["manifest_sha256"],
                confirm_stopped=True,
            )
        self.assertFalse((self.parent / "restore").exists())

    def test_extra_root_and_payload_files_refused(self):
        self.write("data.bin", "fictional")
        self.backup()
        bundle = self.parent / "bundle"
        extra = bundle / "extra.txt"
        extra.write_text("extra", encoding="utf-8")
        with self.assertRaises(transfer.TransferError):
            transfer.verify(bundle)
        extra.unlink()
        (bundle / "payload/extra.txt").write_text("extra", encoding="utf-8")
        with self.assertRaises(transfer.TransferError):
            transfer.verify(bundle)

    def test_missing_payload_file_refused(self):
        self.write("data.bin", "fictional")
        self.backup()
        bundle = self.parent / "bundle"
        (bundle / "payload/data.bin").unlink()
        with self.assertRaises(transfer.TransferError):
            transfer.verify(bundle)

    def test_checksum_corruption_refused(self):
        self.write("data.bin", "fictional")
        self.backup()
        bundle = self.parent / "bundle"
        (bundle / transfer.CHECKSUM).write_text("invalid", encoding="ascii")
        with self.assertRaises(transfer.TransferError):
            transfer.verify(bundle)

    def test_internal_checksum_is_not_a_substitute_for_external_pin(self):
        self.write("data.bin", "fictional")
        result = self.backup()
        bundle = self.parent / "bundle"
        changed = b"resigned fictional bytes"
        (bundle / "payload/data.bin").write_bytes(changed)
        data = json.loads((bundle / transfer.MANIFEST).read_text())
        data["inventory"] = [entry("data.bin", changed)]
        self.resign(bundle, data)
        transfer.verify(bundle)
        with self.assertRaises(transfer.TransferError):
            transfer.verify(bundle, expected_manifest_sha=result["manifest_sha256"])

    def test_unknown_format_and_metadata_keys_refused(self):
        self.write("data.bin", "fictional")
        self.backup()
        bundle = self.parent / "bundle"
        data = json.loads((bundle / transfer.MANIFEST).read_text())
        data["format"] = "unknown"
        self.resign(bundle, data)
        with self.assertRaises(transfer.TransferError):
            transfer.verify(bundle)

    def test_source_package_cannot_be_used_as_data_restore(self):
        path = self.write("demo.py", "pass\n")
        result = self.package([entry("demo.py", path.read_bytes())])
        with self.assertRaises(transfer.TransferError):
            transfer.restore(
                self.parent / "bundle",
                self.parent / "restore",
                expected_manifest_sha=result["manifest_sha256"],
                confirm_stopped=True,
            )

    def test_database_sidecars_refused_without_parsing_records(self):
        self.write("data.sqlite3", "fictional")
        self.write("data.sqlite3-wal", "")
        with self.assertRaises(transfer.TransferError):
            self.backup()
        self.assertFalse((self.parent / "bundle").exists())

    def test_clean_closed_sqlite_copied_as_opaque_bytes(self):
        source = self.root / "example.sqlite3"
        with sqlite3.connect(source) as connection:
            connection.execute("CREATE TABLE demo (value TEXT)")
            connection.execute("INSERT INTO demo VALUES (?)", ("fictional",))
        connection.close()
        before = source.read_bytes()
        result = self.backup()
        transfer.restore(
            self.parent / "bundle",
            self.parent / "restore",
            expected_manifest_sha=result["manifest_sha256"],
            confirm_stopped=True,
        )
        self.assertEqual((self.parent / "restore/example.sqlite3").read_bytes(), before)

    def test_control_directory_not_traversed(self):
        self.write(".git/config", "fictional")
        with self.assertRaises(transfer.TransferError):
            self.backup()

    def test_empty_snapshot_refused(self):
        with self.assertRaises(transfer.TransferError):
            self.backup()

    def test_state_outputs_forbidden_in_repository(self):
        with self.assertRaises(transfer.TransferError):
            transfer.selected_path(ROOT / "runtime", output=True)

    def test_cli_error_omits_private_paths(self):
        output = io.StringIO()
        path = self.parent / "missing"
        with contextlib.redirect_stdout(output):
            code = transfer.main(["verify", "--bundle", str(path)])
        self.assertEqual(code, 2)
        self.assertNotIn(str(path), output.getvalue())

    def test_verification_does_not_modify_bundle(self):
        self.write("data.bin", "fictional")
        self.backup()
        bundle = self.parent / "bundle"
        before = {
            p.relative_to(bundle).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in bundle.rglob("*")
            if p.is_file()
        }
        transfer.verify(bundle)
        after = {
            p.relative_to(bundle).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in bundle.rglob("*")
            if p.is_file()
        }
        self.assertEqual(after, before)

    def test_hardlinks_refused(self):
        original = self.write("data.bin", "fictional")
        try:
            os.link(original, self.parent / "alias.bin")
        except OSError:
            self.skipTest("Native hardlink creation unavailable")
        with self.assertRaises(transfer.TransferError):
            self.backup()

    def test_symlinks_refused(self):
        target = self.parent / "target.bin"
        target.write_bytes(b"fictional")
        try:
            os.symlink(target, self.root / "linked.bin")
        except OSError:
            self.skipTest("Native symlink creation unavailable")
        with self.assertRaises(transfer.TransferError):
            self.backup()


class MaintenanceTests(unittest.TestCase):
    def request(self, **changes):
        value = dict(
            action="restart",
            state="running",
            players=0,
            observation_age_seconds=0,
            maximum_age_seconds=60,
            cooldown_remaining_seconds=0,
            previous_attempt="completed",
            target_verified=True,
            backup_verified=True,
        )
        value.update(changes)
        return value

    def test_restart_has_ordered_save_stop_backup_start_checks(self):
        result = maintenance.maintenance_plan(self.request())
        steps = result["steps"]
        self.assertEqual(result["status"], "PLAN_READY")
        self.assertFalse(result["execution_performed"])
        self.assertLess(steps.index("verify_stopped"), steps.index("refresh_backup"))
        self.assertLess(steps.index("verify_backup_pin"), steps.index("start"))

    def test_unknown_players_block_plan(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(players=None))["status"],
            "PLAYER_COUNT_UNKNOWN",
        )

    def test_present_players_defer_plan(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(players=1))["status"],
            "PLAYERS_PRESENT",
        )

    def test_stale_or_missing_observation_blocks_plan(self):
        for age in (None, 61):
            self.assertEqual(
                maintenance.maintenance_plan(self.request(observation_age_seconds=age))[
                    "status"
                ],
                "OBSERVATION_STALE_OR_MISSING",
            )

    def test_incomplete_attempt_requires_review(self):
        for status in ("incomplete", "unknown"):
            self.assertEqual(
                maintenance.maintenance_plan(self.request(previous_attempt=status))[
                    "status"
                ],
                "REVIEW_PREVIOUS_ATTEMPT",
            )

    def test_unverified_target_and_unknown_state_block(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(target_verified=False))["status"],
            "TARGET_NOT_VERIFIED",
        )
        self.assertEqual(
            maintenance.maintenance_plan(self.request(state="unknown"))["status"],
            "STATE_NOT_ESTABLISHED",
        )

    def test_cooldown_defers_plan(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(cooldown_remaining_seconds=1))[
                "status"
            ],
            "COOLDOWN_PENDING",
        )

    def test_updates_and_backups_need_stopped_state(self):
        for action in ("update", "backup"):
            self.assertEqual(
                maintenance.maintenance_plan(self.request(action=action))["status"],
                "STOP_REQUIRED",
            )

    def test_update_and_restart_need_verified_backup(self):
        for action in ("update", "restart"):
            self.assertEqual(
                maintenance.maintenance_plan(
                    self.request(action=action, state="stopped", backup_verified=False)
                )["status"],
                "VERIFIED_BACKUP_REQUIRED",
            )

    def test_contradictory_stopped_players_refused(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(state="stopped", players=1))[
                "status"
            ],
            "OBSERVATION_INCONSISTENT",
        )

    def test_boolean_integer_and_unknown_fields_rejected(self):
        for changes in (
            {"players": False},
            {"maximum_age_seconds": 0},
            {"extra": True},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(maintenance.PlanError),
            ):
                maintenance.maintenance_plan(self.request(**changes))

    def test_start_running_and_stop_stopped_are_no_actions(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(action="start"))["status"],
            "NO_ACTION",
        )
        self.assertEqual(
            maintenance.maintenance_plan(self.request(action="stop", state="stopped"))[
                "status"
            ],
            "NO_ACTION",
        )

    def test_readiness_needs_all_observations(self):
        value = dict(
            target_verified=True,
            new_instance=True,
            fresh_log_markers=True,
            probe_succeeded=True,
        )
        self.assertEqual(
            maintenance.readiness_rule(value)["status"], "OBSERVATIONS_COMPLETE"
        )
        value["new_instance"] = False
        self.assertEqual(maintenance.readiness_rule(value)["status"], "NOT_ESTABLISHED")

    def test_first_weekday_handles_leap_month_and_year_boundary(self):
        self.assertEqual(maintenance.first_weekday(2024, 2, 3), date(2024, 2, 1))
        result = maintenance.schedule_window(2026, 12, 3, 14)
        self.assertEqual(result["anchor"], "2026-12-03")
        self.assertEqual(result["next_anchor"], "2027-01-07")

    def test_overlapping_offsets_and_bad_dates_rejected(self):
        for args in ((2026, 13, 3, 14), (2026, 2, 3, 0), (2026, 2, 8, 14)):
            with self.subTest(args=args), self.assertRaises(maintenance.PlanError):
                maintenance.schedule_window(*args)
        with self.assertRaises(maintenance.PlanError):
            maintenance.schedule_window(2021, 2, 0, 28)


if __name__ == "__main__":
    unittest.main()
