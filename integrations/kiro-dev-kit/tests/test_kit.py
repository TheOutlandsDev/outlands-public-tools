import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kiro_kit", ROOT / "scripts" / "kiro_kit.py")
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "project with spaces"
        self.target.mkdir()

    def test_preview_has_no_writes(self):
        result = kit.install(self.target)
        self.assertEqual(result["action"], "preview")
        self.assertGreater(len(result["changes"]), 10)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_round_trip_and_idempotence(self):
        untouched = self.target / "project.txt"
        untouched.write_bytes(b"keep\x00exact\r\n")
        result = kit.install(self.target, apply=True)
        self.assertEqual(kit.install(self.target, apply=True)["action"], "unchanged")
        report = kit.verify(self.target)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["missing"], [])
        self.assertFalse(report["ready_for_managed_work"])
        self.assertEqual(report["managed_model_session"], "NOT_RUN")
        kit.restore(self.target, result["receipt"], apply=True)
        self.assertFalse((self.target / "AGENTS.md").exists())
        self.assertTrue((self.target / ".kiro-kit/.gitignore").is_file())
        self.assertEqual(untouched.read_bytes(), b"keep\x00exact\r\n")

    def test_conflict_requires_explicit_replace_and_restores_bytes(self):
        path = self.target / "AGENTS.md"
        original = b"Existing project rules\r\nDo not remove.\r\n"
        path.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "Existing files differ"):
            kit.install(self.target, apply=True)
        self.assertEqual(list(self.target.iterdir()), [path])
        result = kit.install(self.target, apply=True, replace=True)
        kit.restore(self.target, result["receipt"], apply=True)
        self.assertEqual(path.read_bytes(), original)

    def test_restore_preserves_edited_files_and_is_preflighted(self):
        result = kit.install(self.target, apply=True)
        path = self.target / ".kiro/steering/python.md"
        path.write_text("User refinement", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Installed file changed"):
            kit.restore(self.target, result["receipt"], apply=True)
        self.assertTrue((self.target / "AGENTS.md").exists())
        self.assertIn("Installed file drift", " ".join(kit.verify(self.target)["errors"]))

    def test_tampered_backup_is_rejected(self):
        (self.target / "AGENTS.md").write_text("original", encoding="utf-8")
        result = kit.install(self.target, apply=True, replace=True)
        receipt_path = self.target / result["receipt"]
        receipt = kit.read_json(receipt_path)
        entry = next(x for x in receipt["files"] if x["backup"])
        (receipt_path.parent / entry["backup"]).write_bytes(b"damaged")
        with self.assertRaisesRegex(ValueError, "Backup digest mismatch"):
            kit.restore(self.target, result["receipt"], apply=True)
        self.assertTrue((self.target / "AGENTS.md").exists())

    def test_interrupted_write_reverts_prior_files(self):
        original_write = kit.atomic_write
        failed = False

        def failing_write(path, data):
            nonlocal failed
            if path.name == "python.md" and not failed:
                failed = True
                raise OSError("simulated write failure")
            return original_write(path, data)

        with patch.object(kit, "atomic_write", side_effect=failing_write):
            with self.assertRaisesRegex(OSError, "simulated"):
                kit.install(self.target, apply=True)
        self.assertFalse((self.target / "AGENTS.md").exists())
        receipts = list((self.target / ".kiro-kit/state").glob("*/receipt.json"))
        self.assertEqual(kit.read_json(receipts[0])["status"], "failed_reverted")

    def test_path_escape_and_case_collision_rejected(self):
        for value in ["../outside", "/outside", "C:/outside", "a\\b", "a/../b", "a//b"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                kit.within(self.target, value)
        with self.assertRaisesRegex(ValueError, "Receipt must be"):
            kit.restore(self.target, "receipt.json")

    def test_reparse_target_rejected_without_following_it(self):
        fake = self.target / ".kiro"
        real_lstat = Path.lstat

        def lstat(path, *args, **kwargs):
            if path == fake:
                class Reparse:
                    st_mode = 0
                    st_file_attributes = 0x400
                return Reparse()
            return real_lstat(path, *args, **kwargs)

        with patch.object(Path, "lstat", lstat):
            with self.assertRaisesRegex(ValueError, "reparse"):
                kit.install(self.target, apply=True)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_template_tampering_is_rejected_before_write(self):
        with patch.object(kit, "read_json", return_value={"version": "1.2.0", "files": [
            {"target": "AGENTS.md", "sha256": "0" * 64}]}):
            with self.assertRaisesRegex(ValueError, "Template digest mismatch"):
                kit.install(self.target, apply=True)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_duplicate_inventory_target_is_rejected(self):
        manifest = kit.read_json(ROOT / "kit-manifest.json")
        manifest["files"].append({**manifest["files"][0], "target": manifest["files"][0]["target"].upper()})
        with patch.object(kit, "read_json", return_value=manifest):
            with self.assertRaisesRegex(ValueError, "Duplicate installation path"):
                kit.payloads()

    def test_only_available_model_ids_are_rendered(self):
        inventory = self.root / "models.json"
        inventory.write_text(json.dumps({"available_model_ids": ["example-approved-gpt"]}))
        with self.assertRaisesRegex(ValueError, "absent"):
            kit.install(self.target, apply=True, models_file=inventory, primary="unknown-model")
        self.assertEqual(list(self.target.iterdir()), [])
        kit.install(self.target, apply=True, models_file=inventory, primary="example-approved-gpt")
        report = kit.verify(self.target)
        self.assertEqual(set(report["configured_models"].values()), {"example-approved-gpt"})
        self.assertFalse(report["ready_for_managed_work"])

    def test_url_is_not_a_model_id(self):
        inventory = self.root / "models.json"
        inventory.write_text(json.dumps({"available_model_ids": ["https://example.invalid/model"]}))
        with self.assertRaisesRegex(ValueError, "Expected exact model IDs"):
            kit.install(self.target, models_file=inventory, primary="https://example.invalid/model")

    def test_shared_script_is_pinned_and_cannot_redirect_source(self):
        data = kit.payloads()
        self.assertEqual(data[".kiro/devkit/check_bedrock.py"], (ROOT / "scripts/check_bedrock.py").read_bytes())
        manifest = kit.read_json(ROOT / "kit-manifest.json")
        entry = next(x for x in manifest["files"] if x.get("source"))
        entry["source"] = "README.md"
        with patch.object(kit, "read_json", return_value=manifest):
            with self.assertRaisesRegex(ValueError, "Unapproved shared"):
                kit.payloads()

    def test_route_agent_drift_is_reported(self):
        kit.install(self.target, apply=True)
        p = self.target / ".kiro/agents/outlands-developer.json"
        config = kit.read_json(p)
        config["model"] = "another-model"
        p.write_bytes(kit.encoded(config))
        self.assertIn("Route and agent model differ", " ".join(kit.verify(self.target)["errors"]))

    def test_restore_preview_has_no_changes(self):
        result = kit.install(self.target, apply=True)
        before = (self.target / "AGENTS.md").read_bytes()
        self.assertEqual(kit.restore(self.target, result["receipt"])["action"], "restore_preview")
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), before)

    def test_reverse_installation_restores_previous_model_config(self):
        first = kit.install(self.target, apply=True)
        inventory = self.root / "models.json"
        inventory.write_text(json.dumps({"available_model_ids": ["example-approved-gpt"]}))
        second = kit.install(self.target, apply=True, replace=True, models_file=inventory, primary="example-approved-gpt")
        with self.assertRaisesRegex(ValueError, "Installed file changed"):
            kit.restore(self.target, first["receipt"], apply=True)
        kit.restore(self.target, second["receipt"], apply=True)
        self.assertEqual(kit.verify(self.target)["errors"], [])
        kit.restore(self.target, first["receipt"], apply=True)
        self.assertFalse((self.target / "AGENTS.md").exists())

    def test_bugfix_eval_fails_then_passes_and_rejects_test_changes(self):
        target = self.root / "eval"
        kit.prepare_eval(target)
        self.assertFalse(kit.score_eval(target)["code_checks_passed"])
        path = target / "orders.py"
        path.write_text(path.read_text().replace(" > quantity", " >= quantity"))
        self.assertTrue(kit.score_eval(target)["code_checks_passed"])
        (target / "tests/test_orders.py").write_text("# removed tests\n")
        result = kit.score_eval(target)
        self.assertFalse(result["code_checks_passed"])
        self.assertEqual(result["protected_files_changed"], ["tests/test_orders.py"])


if __name__ == "__main__":
    unittest.main()
