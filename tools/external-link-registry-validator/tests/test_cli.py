"""Exercise the standalone CLI with fictional saved input."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


SOURCE = Path(__file__).resolve().parents[1]
CLI = SOURCE / "external_link_registry.py"
REGISTRY = SOURCE / "examples" / "registry.json"
FICTIONAL_LABEL = "FICTIONAL-PRIVATE-LABEL"
FICTIONAL_SECRET = "FICTIONAL-PRIVATE-VALUE"
FICTIONAL_DESTINATION = "https://registry.example.invalid/resources"


class ExternalLinkRegistryCLITests(unittest.TestCase):
    def _run(self, data: bytes) -> subprocess.CompletedProcess[str]:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fictional-private-registry.json"
            source.write_bytes(data)
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-W", "error", str(CLI), "--input", str(source)],
                cwd=root,
                capture_output=True,
                encoding="utf-8",
                timeout=20,
                check=False,
            )
            self.assertEqual(source.read_bytes(), data)
            self.assertEqual(list(root.iterdir()), [source])
            self.assertNotIn(str(source), result.stdout + result.stderr)
            self.assertNotIn(source.name, result.stdout + result.stderr)
            return result

    def _assert_valid(self, data: bytes, count: int) -> None:
        result = self._run(data)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), {"status": "valid", "count": count})

    def _assert_rejected(self, rows: list[dict[str, str]]) -> None:
        result = self._run(json.dumps(rows).encode("utf-8"))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.strip())
        for marker in ("Traceback", FICTIONAL_LABEL, FICTIONAL_SECRET, "example.invalid"):
            self.assertNotIn(marker, result.stderr)
        for row in rows:
            self.assertNotIn(row["href"], result.stderr)
            self.assertNotIn(row["label"], result.stderr)

    def test_accepts_fictional_registry_without_changing_input(self) -> None:
        self._assert_valid(REGISTRY.read_bytes(), 25)
        # Stable casefold ordering and exact-label uniqueness are independent rules.
        distinct = [
            {"label": "fictional alias", "href": FICTIONAL_DESTINATION},
            {"label": "Fictional Alias", "href": FICTIONAL_DESTINATION},
            {"label": "Fictional Zebra", "href": FICTIONAL_DESTINATION},
        ]
        self._assert_valid(json.dumps(distinct).encode("utf-8"), 3)

    def test_rejects_exact_duplicate_and_out_of_order_labels(self) -> None:
        entry = {"label": FICTIONAL_LABEL, "href": FICTIONAL_DESTINATION}
        self._assert_rejected([entry, entry.copy()])
        later = {"label": "Fictional Zebra", "href": FICTIONAL_DESTINATION}
        earlier = {"label": "fictional alpha", "href": FICTIONAL_DESTINATION}
        self._assert_rejected([later, earlier])

    def test_rejects_malformed_urls_without_disclosing_input(self) -> None:
        for href in (
            "ftp://registry.example.invalid/resources",
            "https:///resources",
            "https://[2001:db8::1/resources",
            "https://registry.example.invalid:70000/resources",
            "https://registry.example.invalid:not-a-port/resources",
            "https://registry.example.invalid/fictional\nresource",
            "https://registry.exa\tmple.invalid/resources",
        ):
            with self.subTest(href=href):
                self._assert_rejected([{"label": FICTIONAL_LABEL, "href": href}])

    def test_rejects_userinfo_and_encoded_session_fields_without_disclosing_input(self) -> None:
        for href in (
            "https://@registry.example.invalid/resources",
            f"https://fictional-user:{FICTIONAL_SECRET}@registry.example.invalid/resources",
            f"{FICTIONAL_DESTINATION}?%54oKeN=",
            f"{FICTIONAL_DESTINATION}?%53eSsIoNiD={FICTIONAL_SECRET}",
        ):
            with self.subTest(href=href):
                self._assert_rejected([{"label": FICTIONAL_LABEL, "href": href}])
