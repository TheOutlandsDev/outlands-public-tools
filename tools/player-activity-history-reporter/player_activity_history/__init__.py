"""Build offline activity history reports from saved daily aggregates."""

from .history import ReportError, build_report

__all__ = ["ReportError", "build_report"]
