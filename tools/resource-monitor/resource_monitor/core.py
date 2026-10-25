"""Original bounded sampling/serialization logic. No packet or process inspection."""
from __future__ import annotations

from collections import deque
from copy import deepcopy
import csv
from datetime import datetime, timezone
import io
import json
import math
import os
from pathlib import Path
import stat
import threading
import time

MAX_HISTORY = 600
MAX_EXPORT_BYTES = 1024 * 1024


class MonitorError(Exception):
    """A generic, safe message with no upstream paths or data."""


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise MonitorError(f"{label} must be an integer between {low} and {high}.")
    return value


def interval_seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not .2 <= value <= 60:
        raise MonitorError("Interval must be finite and between 0.2 and 60 seconds.")
    return float(value)


def percent(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
        return None
    return round(float(value), 2)


def byte_count(value):
    return value if type(value) is int and 0 <= value <= (1 << 63) - 1 else None


class LiveProvider:
    """Read only aggregate CPU, memory and network byte counters via psutil."""
    mode = "live"

    def __init__(self):
        try:
            import psutil
        except ImportError:
            raise MonitorError("Live sampling needs the separately installed psutil dependency; see requirements-live.txt.") from None
        self.psutil = psutil

    def read(self):
        result = {}
        try:
            result["cpu_percent"] = self.psutil.cpu_percent(interval=None)
        except Exception:
            result["cpu_percent"] = None
        try:
            memory = self.psutil.virtual_memory()
            result["memory"] = {"percent": memory.percent, "used_bytes": memory.used, "total_bytes": memory.total}
        except Exception:
            result["memory"] = None
        try:
            network = self.psutil.net_io_counters(pernic=False, nowrap=False)
            result["network"] = None if network is None else {"received_bytes": network.bytes_recv, "sent_bytes": network.bytes_sent}
        except Exception:
            result["network"] = None
        return result


class DemoProvider:
    """Deterministic fictional counters; no machine/system API calls."""
    mode = "demo"

    def __init__(self):
        self.tick = 0

    def read(self):
        tick = self.tick
        self.tick += 1
        total = 16 * 1024 ** 3
        memory = 42 + (tick % 12) * .35
        return {"cpu_percent": [18.4, 24.6, 31.2, 27.8, 21.3, 16.5, 22.4, 34.1][tick % 8],
                "memory": {"percent": memory, "used_bytes": int(total * memory / 100), "total_bytes": total},
                "network": {"received_bytes": 40000000 + tick * 184320, "sent_bytes": 12000000 + tick * 32768}}


class Collector:
    def __init__(self, provider, clock=time.monotonic, utc_now=None):
        if getattr(provider, "mode", None) not in ("demo", "live"):
            raise MonitorError("Unsupported sampling mode.")
        self.provider = provider
        self.clock = clock
        self.utc_now = utc_now or (lambda: datetime.now(timezone.utc))
        self.sequence = 0
        self.started = None
        self.previous = None

    def collect(self):
        now = self.clock()
        if type(now) not in (float, int) or not math.isfinite(now):
            raise MonitorError("Sampling clock is unavailable.")
        if self.started is None:
            self.started = now
        try:
            raw = self.provider.read()
            if not isinstance(raw, dict):
                raw = {}
        except Exception:
            raw = {}
        issues = []
        cpu = percent(raw.get("cpu_percent"))
        if self.sequence == 0:
            cpu = None
            issues.append("cpu_warming_up")
        elif cpu is None:
            issues.append("cpu_unavailable")
        memory_raw = raw.get("memory")
        memory = {"percent": None, "used_bytes": None, "total_bytes": None}
        if isinstance(memory_raw, dict):
            memory = {"percent": percent(memory_raw.get("percent")),
                      "used_bytes": byte_count(memory_raw.get("used_bytes")),
                      "total_bytes": byte_count(memory_raw.get("total_bytes"))}
            if memory["total_bytes"] == 0 or (memory["used_bytes"] is not None and memory["total_bytes"] is not None and memory["used_bytes"] > memory["total_bytes"]):
                memory = {"percent": None, "used_bytes": None, "total_bytes": None}
        if any(value is None for value in memory.values()):
            issues.append("memory_unavailable")
        network_raw = raw.get("network")
        network = {"received_bytes": None, "sent_bytes": None, "received_bps": None, "sent_bps": None, "counter_reset": False}
        if isinstance(network_raw, dict):
            network["received_bytes"] = byte_count(network_raw.get("received_bytes"))
            network["sent_bytes"] = byte_count(network_raw.get("sent_bytes"))
        if network["received_bytes"] is None or network["sent_bytes"] is None:
            issues.append("network_unavailable")
            self.previous = None
        else:
            if self.previous is not None:
                before_time, received, sent = self.previous
                elapsed = now - before_time
                if network["received_bytes"] < received or network["sent_bytes"] < sent:
                    network["counter_reset"] = True
                    issues.append("network_counter_reset")
                elif elapsed > 0:
                    received_rate = (network["received_bytes"] - received) / elapsed
                    sent_rate = (network["sent_bytes"] - sent) / elapsed
                    if math.isfinite(received_rate) and math.isfinite(sent_rate):
                        network["received_bps"] = round(received_rate, 2)
                        network["sent_bps"] = round(sent_rate, 2)
                    else:
                        issues.append("network_rate_unavailable")
                else:
                    issues.append("clock_not_advanced")
            self.previous = (now, network["received_bytes"], network["sent_bytes"])
        self.sequence += 1
        return {"schema": 1, "mode": self.provider.mode, "sequence": self.sequence,
                "timestamp": self.utc_now().isoformat(timespec="milliseconds"),
                "elapsed_seconds": round(max(0, now - self.started), 3), "cpu_percent": cpu,
                "memory": memory, "network": network, "issues": issues}


class Store:
    def __init__(self, mode, capacity=120, interval=1):
        if mode not in ("demo", "live"):
            raise MonitorError("Unsupported sampling mode.")
        self.mode = mode
        self.capacity = integer(capacity, 1, MAX_HISTORY, "History capacity")
        self.interval = interval_seconds(interval)
        self.samples = deque(maxlen=capacity)
        self.lock = threading.Lock()
        self.sampling_error = False

    def add(self, sample):
        # JSON validation rejects unsupported numbers and proves the public shape is serializable.
        data = json.loads(json.dumps(sample, allow_nan=False))
        with self.lock:
            self.samples.append(data)
            self.sampling_error = False

    def mark_sampling_error(self):
        with self.lock:
            self.sampling_error = True

    def snapshot(self, limit=None):
        if limit is not None:
            integer(limit, 1, self.capacity, "History limit")
        with self.lock:
            samples = list(self.samples)
            if limit is not None:
                samples = samples[-limit:]
            return {"schema": 1, "mode": self.mode, "capacity": self.capacity,
                    "interval_seconds": self.interval, "sampling_error": self.sampling_error, "samples": deepcopy(samples)}

    def latest(self):
        values = self.snapshot(1)["samples"]
        return values[0] if values else None


def export_json(snapshot):
    try:
        value = (json.dumps(snapshot, allow_nan=False, ensure_ascii=True, indent=2) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise MonitorError("Snapshot could not be serialized.") from None
    if len(value) > MAX_EXPORT_BYTES:
        raise MonitorError("Snapshot exceeds the supported export size.")
    return value


def export_csv(snapshot):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["sequence", "timestamp", "mode", "cpu_percent", "memory_percent", "memory_used_bytes", "memory_total_bytes", "received_bytes", "sent_bytes", "received_bytes_per_second", "sent_bytes_per_second", "counter_reset", "issues"])
    for row in snapshot["samples"]:
        memory, network = row["memory"], row["network"]
        writer.writerow([row["sequence"], row["timestamp"], row["mode"], row["cpu_percent"], memory["percent"], memory["used_bytes"], memory["total_bytes"], network["received_bytes"], network["sent_bytes"], network["received_bps"], network["sent_bps"], network["counter_reset"], ";".join(row["issues"])])
    value = stream.getvalue().encode("utf-8")
    if len(value) > MAX_EXPORT_BYTES:
        raise MonitorError("Snapshot exceeds the supported export size.")
    return value


def save_fresh(path, value):
    """Explicit local export only; no overwrite or automatic parent creation."""
    try:
        target = Path(path)
        if not target.is_absolute():
            raise MonitorError("Use an explicit absolute export path in a private directory.")
        target = target.absolute()
        if ".." in target.parts:
            raise MonitorError("Use an explicit trusted export path without parent traversal.")
        for component in (target.parent, *target.parent.parents):
            info = component.lstat()
            if component.is_symlink() or getattr(component, "is_junction", lambda: False)() or getattr(info, "st_file_attributes", 0) & 0x400:
                raise MonitorError("Linked export parents are unsupported.")
        if not target.parent.is_dir():
            raise MonitorError("Export parent must already exist.")
        if target.is_symlink() or getattr(target, "is_junction", lambda: False)():
            raise MonitorError("Linked export targets are unsupported.")
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0), 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(value)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError:
        raise MonitorError("Export target already exists; choose a new filename.") from None
    except (OSError, ValueError, TypeError):
        raise MonitorError("Could not write the explicit fresh export. A failed write can leave a partial new file.") from None
