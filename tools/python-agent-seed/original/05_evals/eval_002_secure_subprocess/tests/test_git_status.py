from __future__ import annotations

from pathlib import Path
from unittest import TestCase, mock

from starter.git_status import GitStatusError, git_status_short


class GitStatusEvalTests(TestCase):
    @mock.patch("starter.git_status.subprocess.run")
    def test_uses_explicit_args_and_cwd(self, run_mock: mock.Mock) -> None:
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = " M file.py\n"
        run_mock.return_value.stderr = ""

        result = git_status_short(Path("/repo"))

        self.assertEqual(result, " M file.py\n")
        _, kwargs = run_mock.call_args
        self.assertEqual(kwargs["cwd"], Path("/repo"))
        self.assertEqual(kwargs["capture_output"], True)
        self.assertEqual(kwargs["text"], True)
        self.assertEqual(kwargs["check"], False)
        args = run_mock.call_args.args[0]
        self.assertEqual(args, ["git", "status", "--short"])
        self.assertNotIn("shell", kwargs)

    @mock.patch("starter.git_status.subprocess.run")
    def test_raises_on_nonzero_exit(self, run_mock: mock.Mock) -> None:
        run_mock.return_value.returncode = 128
        run_mock.return_value.stdout = ""
        run_mock.return_value.stderr = "not a git repository"

        with self.assertRaisesRegex(GitStatusError, "not a git repository"):
            git_status_short("/not-repo")
