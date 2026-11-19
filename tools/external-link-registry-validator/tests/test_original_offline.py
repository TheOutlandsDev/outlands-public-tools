"""Retain the two original registry cases with a fictional matrix."""

import json
from pathlib import Path
import unittest
from urllib.parse import parse_qsl, urlsplit

from external_link_registry import ExternalLink, validate_external_links


REGISTRY = Path(__file__).resolve().parents[1] / "examples" / "registry.json"
EXPECTED_LABELS = [f"Fictional Resource {number:02d}" for number in range(1, 26)]


EXTERNAL_SIDEBAR_LINKS = tuple(ExternalLink(**item) for item in json.loads(REGISTRY.read_bytes()))


class ExternalLinkRegistryOriginalTests(unittest.TestCase):
    def setUp(self) -> None:
        validate_external_links(EXTERNAL_SIDEBAR_LINKS)

    def test_external_sidebar_registry_matches_approved_matrix_and_is_sorted(self) -> None:
        labels = [link.label for link in EXTERNAL_SIDEBAR_LINKS]
        assert labels == EXPECTED_LABELS
        assert labels == sorted(labels, key=str.casefold)
        assert len(labels) == 25

    def test_external_sidebar_registry_contains_no_embedded_session_credentials(self) -> None:
        forbidden = {"ticket", "token", "access_token", "session", "sessionid"}
        for link in EXTERNAL_SIDEBAR_LINKS:
            parsed = urlsplit(link.href)
            assert parsed.scheme in {"http", "https"}
            assert parsed.netloc
            assert parsed.username is None
            assert parsed.password is None
            query_keys = {
                key.casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
            }
            assert query_keys.isdisjoint(forbidden)
