from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable

from .models import IncidentCandidate


class CacStorage:
    def __init__(
        self, path: Path, *, clean_samples: int, retention_days: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock
        self.path = path
        self.clean_samples = clean_samples
        self.retention_days = retention_days
        path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _now(self) -> datetime:
        return datetime.now(UTC) if self._clock is None else self._clock()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")
        except sqlite3.Error:
            connection.close()
            raise
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS snapshots(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_snapshots_captured
                    ON snapshots(captured_at);
                CREATE TABLE IF NOT EXISTS incidents(
                    fingerprint TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    code TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    state TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    occurrence_count INTEGER NOT NULL,
                    clean_count INTEGER NOT NULL DEFAULT 0,
                    evidence_json TEXT NOT NULL,
                    acknowledged_at TEXT,
                    resolved_at TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_incidents_state
                    ON incidents(state, severity, last_seen);
                CREATE TABLE IF NOT EXISTS actions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    target TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                INSERT OR REPLACE INTO metadata(key, value)
                    VALUES('schema_version', '1');
                """
            )

    def save_snapshot(
        self,
        snapshot: dict[str, Any],
        incidents: Iterable[IncidentCandidate],
    ) -> None:
        now = str(snapshot["generated"])
        candidates = list(incidents)
        active = {candidate.fingerprint for candidate in candidates}
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO snapshots(captured_at, overall_status, payload_json)
                VALUES(?, ?, ?)
                """,
                (
                    now,
                    str(snapshot["overall_status"]),
                    json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False),
                ),
            )
            for candidate in candidates:
                connection.execute(
                    """
                    INSERT INTO incidents(
                        fingerprint, source, code, severity, state, summary,
                        first_seen, last_seen, occurrence_count, clean_count,
                        evidence_json
                    ) VALUES(?, ?, ?, ?, 'active', ?, ?, ?, 1, 0, ?)
                    ON CONFLICT(fingerprint) DO UPDATE SET
                        severity=excluded.severity,
                        state='active',
                        last_seen=excluded.last_seen,
                        occurrence_count=incidents.occurrence_count + 1,
                        clean_count=0,
                        evidence_json=excluded.evidence_json,
                        resolved_at=NULL,
                        acknowledged_at=CASE
                            WHEN incidents.state='resolved' THEN NULL
                            ELSE incidents.acknowledged_at
                        END
                    """,
                    (
                        candidate.fingerprint,
                        candidate.source,
                        candidate.code,
                        candidate.severity,
                        candidate.summary,
                        now,
                        now,
                        json.dumps(candidate.evidence, ensure_ascii=False),
                    ),
                )
            open_rows = connection.execute(
                """
                SELECT fingerprint, clean_count
                FROM incidents
                WHERE state IN ('active', 'monitoring')
                """
            ).fetchall()
            for row in open_rows:
                fingerprint = str(row["fingerprint"])
                if fingerprint in active:
                    continue
                clean_count = int(row["clean_count"]) + 1
                if clean_count >= self.clean_samples:
                    connection.execute(
                        """
                        UPDATE incidents
                        SET state='resolved', clean_count=?, resolved_at=?
                        WHERE fingerprint=?
                        """,
                        (clean_count, now, fingerprint),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE incidents
                        SET state='monitoring', clean_count=?
                        WHERE fingerprint=?
                        """,
                        (clean_count, fingerprint),
                    )
            cutoff = (
                self._now() - timedelta(days=self.retention_days)
            ).isoformat(timespec="seconds")
            connection.execute(
                "DELETE FROM snapshots WHERE captured_at < ?",
                (cutoff,),
            )

    def latest_snapshot(self) -> dict[str, Any] | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM snapshots
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(str(row["payload_json"]))
        except (TypeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def incidents(self, *, include_resolved: bool = True) -> list[dict[str, Any]]:
        where = "" if include_resolved else "WHERE state != 'resolved'"
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                f"""
                SELECT fingerprint, source, code, severity, state, summary,
                       first_seen, last_seen, occurrence_count, clean_count,
                       evidence_json, acknowledged_at, resolved_at
                FROM incidents
                {where}
                ORDER BY
                    CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
                    CASE state WHEN 'active' THEN 0 WHEN 'monitoring' THEN 1 ELSE 2 END,
                    last_seen DESC
                LIMIT 1000
                """
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["evidence"] = json.loads(item.pop("evidence_json"))
            result.append(item)
        return result

    def acknowledge_incident(self, fingerprint: str, *, actor: str = "local-admin") -> bool:
        """Acknowledge operator noise without deleting current evidence."""
        now = self._now().isoformat(timespec="seconds")
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE incidents SET acknowledged_at=? WHERE fingerprint=? AND state IN ('active', 'monitoring')",
                (now, fingerprint),
            )
            changed = cursor.rowcount == 1
        if changed:
            self.record_action(actor=actor, target=fingerprint, action="acknowledge_incident", status="completed", details={"preserved_evidence": True})
        return changed

    def clear_resolved_incidents(self, *, actor: str = "local-admin") -> int:
        """Delete resolved history only; active and monitoring rows are preserved."""
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute("DELETE FROM incidents WHERE state='resolved'")
            count = max(0, cursor.rowcount)
        self.record_action(actor=actor, target="resolved_incidents", action="clear_resolved_incidents", status="completed", details={"deleted_rows": count})
        return count
    def record_action(
        self,
        *,
        actor: str,
        target: str,
        action: str,
        status: str,
        details: dict[str, Any],
    ) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO actions(
                    created_at, actor, target, action, status, details_json
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    self._now().isoformat(timespec="seconds"),
                    actor,
                    target,
                    action,
                    status,
                    json.dumps(details, ensure_ascii=False),
                ),
            )

    def integrity_check(self) -> str:
        with closing(self._connect()) as connection, connection:
            return str(connection.execute("PRAGMA integrity_check").fetchone()[0])
