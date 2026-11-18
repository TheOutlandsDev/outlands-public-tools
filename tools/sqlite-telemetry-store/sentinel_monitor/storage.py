from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .models import AlertEvent, SystemSnapshot


SCHEMA_VERSION = 1


@dataclass(slots=True, frozen=True)
class SessionDiagnostic:
    session_id: str
    previous_unclean: bool
    message: str


class SqliteStore:
    """Crash-resistant telemetry storage using SQLite WAL transactions."""

    def __init__(
        self,
        path: Path,
        *,
        enabled: bool = True,
        retention_days: int = 30,
    ) -> None:
        self.path = path
        self.enabled = enabled
        self.retention_days = max(1, int(retention_days))
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None
        self._session_id: str | None = None
        self._last_retention: datetime | None = None

        if self.enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(
                self.path,
                timeout=10,
                check_same_thread=False,
            )
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute("PRAGMA busy_timeout=10000")
            self._initialize_schema()

    @property
    def status(self) -> str:
        if not self.enabled:
            return "Disabled"
        return f"Active: SQLite WAL • {self.path.name}"

    def _initialize_schema(self) -> None:
        connection = self._require_connection()
        with connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    boot_time TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    last_sample_at TEXT,
                    ended_at TEXT,
                    clean_exit INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS samples (
                    sample_id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL UNIQUE,
                    cpu_percent REAL NOT NULL,
                    cpu_frequency_mhz REAL,
                    memory_percent REAL NOT NULL,
                    memory_used_bytes INTEGER NOT NULL,
                    memory_available_bytes INTEGER NOT NULL,
                    swap_percent REAL NOT NULL,
                    disk_read_bps REAL NOT NULL,
                    disk_write_bps REAL NOT NULL,
                    network_receive_bps REAL NOT NULL,
                    network_send_bps REAL NOT NULL,
                    uptime_seconds REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS disk_metrics (
                    sample_id INTEGER NOT NULL REFERENCES samples(sample_id) ON DELETE CASCADE,
                    device TEXT NOT NULL,
                    mountpoint TEXT NOT NULL,
                    label TEXT NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    used_bytes INTEGER NOT NULL,
                    free_bytes INTEGER NOT NULL,
                    percent REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS gpu_metrics (
                    sample_id INTEGER NOT NULL REFERENCES samples(sample_id) ON DELETE CASCADE,
                    gpu_index INTEGER NOT NULL,
                    uuid TEXT NOT NULL,
                    name TEXT NOT NULL,
                    serial TEXT NOT NULL,
                    pci_bus_id TEXT NOT NULL,
                    driver_version TEXT NOT NULL,
                    driver_model_current TEXT NOT NULL,
                    driver_model_pending TEXT NOT NULL,
                    temperature_c REAL,
                    utilization_percent REAL,
                    memory_utilization_percent REAL,
                    memory_used_mb REAL,
                    memory_total_mb REAL,
                    power_draw_w REAL,
                    power_limit_w REAL,
                    fan_percent REAL,
                    pstate TEXT NOT NULL,
                    graphics_clock_mhz REAL,
                    memory_clock_mhz REAL,
                    pcie_replays_since_reset INTEGER
                );

                CREATE TABLE IF NOT EXISTS sensor_metrics (
                    sample_id INTEGER NOT NULL REFERENCES samples(sample_id) ON DELETE CASCADE,
                    identifier TEXT NOT NULL,
                    hardware TEXT NOT NULL,
                    sensor_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    source TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS process_metrics (
                    sample_id INTEGER NOT NULL REFERENCES samples(sample_id) ON DELETE CASCADE,
                    pid INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    cpu_percent REAL NOT NULL,
                    memory_percent REAL NOT NULL,
                    memory_bytes INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    key TEXT NOT NULL,
                    label TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    unit TEXT NOT NULL,
                    message TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS hardware_events (
                    hardware_event_id INTEGER PRIMARY KEY,
                    channel TEXT NOT NULL,
                    record_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    event_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    UNIQUE(channel, record_id)
                );

                CREATE INDEX IF NOT EXISTS ix_samples_timestamp
                    ON samples(timestamp);
                CREATE INDEX IF NOT EXISTS ix_gpu_metrics_sample
                    ON gpu_metrics(sample_id, gpu_index);
                CREATE INDEX IF NOT EXISTS ix_sensor_metrics_lookup
                    ON sensor_metrics(hardware, name, sample_id);
                CREATE INDEX IF NOT EXISTS ix_hardware_events_timestamp
                    ON hardware_events(timestamp);
                CREATE INDEX IF NOT EXISTS ix_alerts_timestamp
                    ON alerts(timestamp);
                """
            )
            connection.execute(
                """
                INSERT INTO metadata(key, value) VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )

    def start_session(self, boot_time: datetime) -> SessionDiagnostic:
        if not self.enabled:
            return SessionDiagnostic("", False, "SQLite session tracking disabled")

        now = datetime.now().astimezone()
        session_id = str(uuid.uuid4())
        connection = self._require_connection()
        with self._lock, connection:
            previous = connection.execute(
                """
                SELECT session_id, boot_time, started_at, last_sample_at
                FROM sessions
                ORDER BY started_at DESC
                LIMIT 1
                """
            ).fetchone()
            previous_unclean = bool(previous)
            if previous:
                closed = connection.execute(
                    "SELECT clean_exit FROM sessions WHERE session_id=?",
                    (previous[0],),
                ).fetchone()
                previous_unclean = not bool(closed and closed[0])

            if previous_unclean and previous:
                same_boot = previous[1] == boot_time.isoformat()
                interruption = "application interruption" if same_boot else "system restart"
                last_sample = previous[3] or "no recorded sample"
                message = (
                    f"Previous Sentinel session did not close cleanly; possible "
                    f"{interruption}. Last sample: {last_sample}"
                )
            else:
                message = "Previous Sentinel session closed cleanly"

            connection.execute(
                """
                INSERT INTO sessions(session_id, boot_time, started_at, clean_exit)
                VALUES(?, ?, ?, 0)
                """,
                (session_id, boot_time.isoformat(), now.isoformat()),
            )
        self._session_id = session_id
        return SessionDiagnostic(session_id, previous_unclean, message)

    def log_snapshot(
        self,
        snapshot: SystemSnapshot,
        alerts: list[AlertEvent],
    ) -> None:
        if not self.enabled:
            return

        connection = self._require_connection()
        stamp = snapshot.timestamp.isoformat()
        with self._lock, connection:
            cursor = connection.execute(
                """
                INSERT INTO samples(
                    timestamp, cpu_percent, cpu_frequency_mhz, memory_percent,
                    memory_used_bytes, memory_available_bytes, swap_percent,
                    disk_read_bps, disk_write_bps, network_receive_bps,
                    network_send_bps, uptime_seconds
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stamp,
                    snapshot.cpu_percent,
                    snapshot.cpu_frequency_mhz,
                    snapshot.memory_percent,
                    snapshot.memory_used_bytes,
                    snapshot.memory_available_bytes,
                    snapshot.swap_percent,
                    snapshot.disk_read_bps,
                    snapshot.disk_write_bps,
                    snapshot.network_receive_bps,
                    snapshot.network_send_bps,
                    snapshot.uptime_seconds,
                ),
            )
            sample_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT INTO disk_metrics(
                    sample_id, device, mountpoint, label, total_bytes,
                    used_bytes, free_bytes, percent
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sample_id,
                        disk.device,
                        disk.mountpoint,
                        disk.label,
                        disk.total_bytes,
                        disk.used_bytes,
                        disk.free_bytes,
                        disk.percent,
                    )
                    for disk in snapshot.disks
                ],
            )
            connection.executemany(
                """
                INSERT INTO gpu_metrics(
                    sample_id, gpu_index, uuid, name, serial, pci_bus_id,
                    driver_version, driver_model_current, driver_model_pending,
                    temperature_c, utilization_percent, memory_utilization_percent,
                    memory_used_mb, memory_total_mb, power_draw_w, power_limit_w,
                    fan_percent, pstate, graphics_clock_mhz, memory_clock_mhz,
                    pcie_replays_since_reset
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sample_id,
                        gpu.index,
                        gpu.uuid,
                        gpu.name,
                        gpu.serial,
                        gpu.pci_bus_id,
                        gpu.driver_version,
                        gpu.driver_model_current,
                        gpu.driver_model_pending,
                        gpu.temperature_c,
                        gpu.utilization_percent,
                        gpu.memory_utilization_percent,
                        gpu.memory_used_mb,
                        gpu.memory_total_mb,
                        gpu.power_draw_w,
                        gpu.power_limit_w,
                        gpu.fan_percent,
                        gpu.pstate,
                        gpu.graphics_clock_mhz,
                        gpu.memory_clock_mhz,
                        gpu.pcie_replays_since_reset,
                    )
                    for gpu in snapshot.gpus
                ],
            )
            connection.executemany(
                """
                INSERT INTO sensor_metrics(
                    sample_id, identifier, hardware, sensor_type,
                    name, value, unit, source
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sample_id,
                        sensor.identifier,
                        sensor.hardware,
                        sensor.sensor_type,
                        sensor.name,
                        sensor.value,
                        sensor.unit,
                        sensor.source,
                    )
                    for sensor in snapshot.hardware_sensors
                ],
            )
            connection.executemany(
                """
                INSERT INTO process_metrics(
                    sample_id, pid, name, cpu_percent, memory_percent, memory_bytes
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sample_id,
                        process.pid,
                        process.name,
                        process.cpu_percent,
                        process.memory_percent,
                        process.memory_bytes,
                    )
                    for process in snapshot.processes
                ],
            )
            connection.executemany(
                """
                INSERT INTO alerts(
                    timestamp, severity, key, label, value,
                    threshold, unit, message
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        event.timestamp.isoformat(),
                        event.severity,
                        event.key,
                        event.label,
                        event.value,
                        event.threshold,
                        event.unit,
                        event.message,
                    )
                    for event in alerts
                ],
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO hardware_events(
                    channel, record_id, timestamp, category, severity,
                    provider, event_id, message
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        event.channel,
                        event.record_id,
                        event.timestamp.isoformat(),
                        event.category,
                        event.severity,
                        event.provider,
                        event.event_id,
                        event.message,
                    )
                    for event in snapshot.hardware_events
                ],
            )
            if self._session_id:
                connection.execute(
                    "UPDATE sessions SET last_sample_at=? WHERE session_id=?",
                    (stamp, self._session_id),
                )

        self._apply_retention(snapshot.timestamp)

    def _apply_retention(self, now: datetime) -> None:
        if self._last_retention and now - self._last_retention < timedelta(hours=6):
            return
        cutoff = (now - timedelta(days=self.retention_days)).isoformat()
        connection = self._require_connection()
        with self._lock, connection:
            connection.execute("DELETE FROM samples WHERE timestamp < ?", (cutoff,))
            connection.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff,))
            connection.execute("DELETE FROM hardware_events WHERE timestamp < ?", (cutoff,))
        self._last_retention = now

    def close(self, *, clean_exit: bool = True) -> None:
        connection = self._connection
        if connection is None:
            return
        with self._lock:
            if clean_exit and self._session_id:
                now = datetime.now().astimezone().isoformat()
                with connection:
                    connection.execute(
                        """
                        UPDATE sessions
                        SET ended_at=?, clean_exit=1
                        WHERE session_id=?
                        """,
                        (now, self._session_id),
                    )
            connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
            connection.close()
            self._connection = None

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("SQLite telemetry store is not open")
        return self._connection
