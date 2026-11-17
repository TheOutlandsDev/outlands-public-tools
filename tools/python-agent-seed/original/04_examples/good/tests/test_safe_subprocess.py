from __future__ import annotations

import sys
from unittest import TestCase

from agent_seed_examples.safe_subprocess import run_command


class SafeSubprocessTests(TestCase):
    def test_runs_explicit_argument_list(self) -> None:
        result = run_command([sys.executable, "-c", "print('ok')"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_requires_non_empty_args(self) -> None:
        with self.assertRaises(ValueError):
            run_command([])
