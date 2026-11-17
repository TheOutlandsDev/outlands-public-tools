from __future__ import annotations

from unittest import TestCase

from starter.tagger import add_tag


class TaggerEvalTests(TestCase):
    def test_does_not_share_default_list(self) -> None:
        self.assertEqual(add_tag("a"), ["a"])
        self.assertEqual(add_tag("b"), ["b"])

    def test_does_not_mutate_caller_list(self) -> None:
        original = ["existing"]
        result = add_tag("new", original)
        self.assertEqual(result, ["existing", "new"])
        self.assertEqual(original, ["existing"])
