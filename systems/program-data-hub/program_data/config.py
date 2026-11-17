"""Path and environment configuration for the data hub."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_RELATIVE_PATH = Path("data/runtime/program_data.sqlite3")
DATABASE_ENVIRONMENT_VARIABLE = "PROGRAM_DATA_DB"


def resolve_project_path(value: str | Path) -> Path:
    """Resolve a configured path, anchoring relative paths at the project root."""

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def get_database_path(override: str | Path | None = None) -> Path:
    """Return the database path from an override, environment, or default."""

    configured = override
    if configured is None:
        configured = os.environ.get(
            DATABASE_ENVIRONMENT_VARIABLE,
            str(DEFAULT_DATABASE_RELATIVE_PATH),
        )
    return resolve_project_path(configured)


def get_backup_directory() -> Path:
    """Return the managed backup directory."""

    return resolve_project_path("data/backups")
