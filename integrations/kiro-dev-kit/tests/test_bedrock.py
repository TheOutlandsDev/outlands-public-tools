import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_bedrock", ROOT / "scripts/check_bedrock.py")
pairing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pairing)


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "pairing-plan.example.json").read_text())

    def complete(self):
        self.plan["kiro"] = {"approved_model_ids": ["example-approved-gpt"], "selected_model_id": "example-approved-gpt"}
        self.plan["bedrock"].update(enabled=True, region="us-east-1", model_id="us.openai.gpt-6-sol", auth_method="aws-profile", profile_name="example-profile")

    def test_empty_template_is_pending_not_ready(self):
        result = pairing.check_plan(self.plan)
        self.assertFalse(result["plan_complete"])
        self.assertFalse(result["ready_for_live_work"])
        self.assertEqual(result["network_requests"], 0)

    def test_complete_plan_still_does_not_certify_access(self):
        self.complete()
        result = pairing.check_plan(self.plan)
        self.assertTrue(result["plan_complete"])
        self.assertFalse(result["ready_for_live_work"])
        self.assertEqual(result["direct_bedrock"]["credentials"], "NOT_READ")
        self.assertEqual(result["kiro"]["model_access"], "NOT_VERIFIED")
        self.assertEqual(result["direct_bedrock"]["derived_base_url"], "https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1")

    def test_kiro_selection_does_not_require_direct_aws_credentials(self):
        self.plan["kiro"] = {"approved_model_ids": ["example-approved-gpt"], "selected_model_id": "example-approved-gpt"}
        result = pairing.check_plan(self.plan)
        self.assertTrue(result["plan_complete"])
        self.assertFalse(result["direct_bedrock"]["requested"])
        self.assertFalse(result["ready_for_live_work"])

    def test_model_must_be_in_supplied_kiro_inventory(self):
        self.plan["kiro"]["selected_model_id"] = "unknown"
        with self.assertRaises(ValueError):
            pairing.check_plan(self.plan)

    def test_endpoint_model_identifiers_cannot_be_interchanged(self):
        self.complete()
        for endpoint, model in [("runtime", "openai.gpt-6-sol"), ("mantle", "us.openai.gpt-6-sol")]:
            with self.subTest(endpoint=endpoint):
                self.plan["bedrock"].update(endpoint=endpoint, model_id=model)
                with self.assertRaises(ValueError):
                    pairing.check_plan(self.plan)

    def test_known_mantle_region_mismatch_is_incomplete(self):
        self.complete()
        self.plan["bedrock"].update(endpoint="mantle", model_id="openai.gpt-6-sol", region="us-west-2")
        result = pairing.check_plan(self.plan)
        self.assertFalse(result["plan_complete"])
        self.assertIn("DOCUMENTED_MANTLE_REGION_MISMATCH", result["issues"])

    def test_mantle_url_and_unknown_access(self):
        self.complete()
        self.plan["bedrock"].update(endpoint="mantle", model_id="openai.gpt-6-sol")
        result = pairing.check_plan(self.plan)
        self.assertEqual(result["direct_bedrock"]["derived_base_url"], "https://bedrock-mantle.us-east-1.api.aws/openai/v1")
        self.assertEqual(result["direct_bedrock"]["region_model_availability"], "NOT_VERIFIED")

    def test_missing_profile_is_reported_without_reading_credentials(self):
        self.complete()
        self.plan["bedrock"]["profile_name"] = None
        result = pairing.check_plan(self.plan)
        self.assertIn("BEDROCK_PROFILE_NAME_REQUIRED", result["issues"])

    def test_credentials_or_custom_urls_are_not_accepted_in_plan(self):
        for field in ("api_key", "secret_access_key", "base_url"):
            with self.subTest(field=field):
                plan = copy.deepcopy(self.plan)
                plan["bedrock"][field] = "private-sentinel-value"
                with self.assertRaises(ValueError):
                    pairing.check_plan(plan)

    def test_profile_name_is_not_printed(self):
        self.complete()
        self.plan["bedrock"]["profile_name"] = "private-profile-sentinel"
        self.assertNotIn("private-profile-sentinel", json.dumps(pairing.check_plan(self.plan)))

    def test_strict_field_types_and_region_format(self):
        for key, value in [("enabled", "true"), ("region", "https://example.invalid"), ("profile_name", "name with spaces")]:
            with self.subTest(key=key):
                plan = copy.deepcopy(self.plan)
                plan["bedrock"][key] = value
                with self.assertRaises(ValueError):
                    pairing.check_plan(plan)

    def test_duplicate_json_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "plan.json"
            p.write_text('{"schema_version":1,"schema_version":1}')
            with self.assertRaises(ValueError):
                pairing.load_plan(p)

    def test_cli_errors_do_not_expose_private_values_or_path(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "private-path-sentinel.json"
            self.plan["bedrock"]["api_key"] = "private-secret-sentinel"
            p.write_text(json.dumps(self.plan))
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/check_bedrock.py"), "--plan", str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("private-secret-sentinel", result.stdout + result.stderr)
            self.assertNotIn("private-path-sentinel", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
