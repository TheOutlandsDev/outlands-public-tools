from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from starter.csv_summary import ScoreSummary, summarize_scores


class CsvSummaryEvalTests(TestCase):
    def test_summarizes_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scores.csv"
            path.write_text("name,score\nAda,10\nLinus,20\n", encoding="utf-8")
            self.assertEqual(summarize_scores(path), ScoreSummary(count=2, average=15.0, maximum=20))

    def test_ignores_blank_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scores.csv"
            path.write_text("name,score\nAda,10\n\nLinus,30\n", encoding="utf-8")
            self.assertEqual(summarize_scores(path).average, 20.0)

    def test_rejects_missing_score_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scores.csv"
            path.write_text("name\nAda\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                summarize_scores(path)

    def test_rejects_non_integer_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scores.csv"
            path.write_text("name,score\nAda,ten\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                summarize_scores(path)

    def test_rejects_no_valid_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scores.csv"
            path.write_text("name,score\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                summarize_scores(path)
