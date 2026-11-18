from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "sample_interval_seconds": 2.0,
    "history_minutes": 15,
    "sqlite_logging": True,
    "sqlite_filename": "sentinel.db",
    "csv_logging": False,
    "log_retention_days": 30,
    "diagnostics_poll_seconds": 30,
    "diagnostic_auto_clear_samples": 5,
    "audible_alerts": False,
    "top_process_count": 12,
    "alert_sustain_samples": 3,
    "alert_repeat_minutes": 15,
    "thresholds": {
        "cpu_usage_percent": {"warning": 85, "critical": 95},
        "memory_usage_percent": {"warning": 85, "critical": 95},
        "disk_usage_percent": {"warning": 85, "critical": 95},
        "cpu_temperature_c": {"warning": 75, "critical": 85},
        "gpu_temperature_c": {"warning": 80, "critical": 88},
        "storage_temperature_c": {"warning": 65, "critical": 75},
    },
}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return deepcopy(DEFAULT_CONFIG)
    with path.open("r", encoding="utf-8") as handle:
        user_config = json.load(handle)
    config = _merge(DEFAULT_CONFIG, user_config)
    interval = float(config["sample_interval_seconds"])
    if not 0.5 <= interval <= 60:
        raise ValueError("sample_interval_seconds must be between 0.5 and 60")
    if int(config["history_minutes"]) < 1:
        raise ValueError("history_minutes must be at least 1")
    filename = str(config["sqlite_filename"])
    if Path(filename).name != filename or not filename.lower().endswith(".db"):
        raise ValueError("sqlite_filename must be a local .db filename")
    retention_days = int(config["log_retention_days"])
    if not 1 <= retention_days <= 3650:
        raise ValueError("log_retention_days must be between 1 and 3650")
    diagnostics_interval = float(config["diagnostics_poll_seconds"])
    if not 10 <= diagnostics_interval <= 300:
        raise ValueError(
            "diagnostics_poll_seconds must be between 10 and 300"
        )
    auto_clear_samples = int(config["diagnostic_auto_clear_samples"])
    if not 1 <= auto_clear_samples <= 120:
        raise ValueError(
            "diagnostic_auto_clear_samples must be between 1 and 120"
        )
    return config

