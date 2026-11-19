"""Normalize saved player telemetry snapshots using an explicit server mapping."""

from .normalizer import SnapshotError, normalize_snapshot

__all__ = ["SnapshotError", "normalize_snapshot"]
