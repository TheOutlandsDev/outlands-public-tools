from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest import mock

from safe_file_mover import cli
from safe_file_mover.core import MoveOperation, Progress


class CommandLineOutputTests(unittest.TestCase):
    def test_move_survives_unicode_path_on_legacy_redirected_stdout(self) -> None:
        engine = mock.Mock()

        def move(*args: object, progress: object, **kwargs: object) -> MoveOperation:
            self.assertTrue(callable(progress))
            progress(
                Progress(
                    phase="copying",
                    path=r"C:\valuable data\Project Ω\payload.bin",
                    bytes_done=7,
                    total_bytes=7,
                    items_done=1,
                    item_count=1,
                )
            )
            return MoveOperation(
                operation_id="operation-123",
                source=Path(r"C:\valuable data\Project Ω"),
                destination=Path(r"D:\archive\Project Ω"),
                recovery_copy=Path(r"C:\valuable data\.Project Ω.recovery"),
                status="backup_retained",
                total_bytes=7,
                item_count=1,
                keep_backup=True,
                last_error=None,
            )

        engine.move.side_effect = move
        raw_output = io.BytesIO()
        redirected_stdout = io.TextIOWrapper(
            raw_output,
            encoding="cp1252",
            errors="strict",
        )

        with (
            mock.patch.object(cli, "SafeMoveEngine", return_value=engine),
            mock.patch.object(sys, "platform", "win32"),
            mock.patch.object(sys, "stdout", redirected_stdout),
        ):
            exit_code = cli.main(["move", "source", "destination"])
            redirected_stdout.flush()
            rendered = raw_output.getvalue().decode("cp1252")

        self.assertEqual(exit_code, 0)
        self.assertIn(r"Project \u03a9", rendered)
        self.assertIn("backup_retained", rendered)

    def test_error_survives_unicode_message_on_legacy_redirected_stderr(self) -> None:
        engine = mock.Mock()
        engine.purge_backup.side_effect = ValueError("cannot purge Project Ω")
        raw_error = io.BytesIO()
        redirected_stderr = io.TextIOWrapper(
            raw_error,
            encoding="cp1252",
            errors="strict",
        )

        with (
            mock.patch.object(cli, "SafeMoveEngine", return_value=engine),
            mock.patch.object(sys, "platform", "win32"),
            mock.patch.object(sys, "stdout", io.StringIO()),
            mock.patch.object(sys, "stderr", redirected_stderr),
        ):
            exit_code = cli.main(["purge", "operation-123"])
            redirected_stderr.flush()
            rendered = raw_error.getvalue().decode("cp1252")

        self.assertEqual(exit_code, 2)
        self.assertIn(r"Project \u03a9", rendered)

    def test_missing_windowed_standard_streams_do_not_break_argument_errors(
        self,
    ) -> None:
        with (
            mock.patch.object(sys, "platform", "win32"),
            mock.patch.object(sys, "stdout", None),
            mock.patch.object(sys, "stderr", None),
        ):
            result = cli.main(["--definitely-not-a-real-option"])

        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
