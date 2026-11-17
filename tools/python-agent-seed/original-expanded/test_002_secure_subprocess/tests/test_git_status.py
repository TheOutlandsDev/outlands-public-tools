from __future__ import annotations

import inspect
from pathlib import Path
from unittest import TestCase, mock

from starter import git_status
from starter.git_status import GitStatusError, git_status_short


class GitStatusEvalTests(TestCase):
    @mock.patch("starter.git_status.subprocess.run")
    def test_uses_explicit_args_and_cwd_for_path_input(self, run_mock: mock.Mock) -> None:
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = " M file.py\n"
        run_mock.return_value.stderr = ""

        result = git_status_short(Path("/repo"))

        self.assertEqual(result, " M file.py\n")
        args = run_mock.call_args.args[0]
        _, kwargs = run_mock.call_args
        self.assertEqual(args, ["git", "status", "--short"])
        self.assertEqual(kwargs["cwd"], Path("/repo"))
        self.assertEqual(kwargs["capture_output"], True)
        self.assertEqual(kwargs["text"], True)
        self.assertEqual(kwargs["check"], False)
        self.assertNotIn("shell", kwargs)

    @mock.patch("starter.git_status.subprocess.run")
    def test_accepts_str_input_and_returns_stdout(self, run_mock: mock.Mock) -> None:
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = "?? new_file.py\n"
        run_mock.return_value.stderr = ""

        result = git_status_short("/repo")

        self.assertEqual(result, "?? new_file.py\n")
        self.assertEqual(run_mock.call_args.kwargs["cwd"], Path("/repo"))

    @mock.patch("starter.git_status.subprocess.run")
    def test_raises_on_nonzero_exit_and_includes_stderr(self, run_mock: mock.Mock) -> None:
        run_mock.return_value.returncode = 128
        run_mock.return_value.stdout = ""
        run_mock.return_value.stderr = "fatal: not a git repository"

        with self.assertRaisesRegex(GitStatusError, "not a git repository"):
            git_status_short("/not-repo")

    @mock.patch("starter.git_status.subprocess.run")
    def test_raises_on_nonzero_exit_with_fallback_message(self, run_mock: mock.Mock) -> None:
        run_mock.return_value.returncode = 1
        run_mock.return_value.stdout = ""
        run_mock.return_value.stderr = ""

        with self.assertRaises(GitStatusError) as context:
            git_status_short("/repo")

        self.assertTrue(str(context.exception).strip())

    def test_source_does_not_use_shell_true_or_check_output(self) -> None:
        source = inspect.getsource(git_status)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("check_output", source)
