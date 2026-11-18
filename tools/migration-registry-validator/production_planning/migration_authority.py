"""Fail-closed source authority for PostgreSQL and ClickHouse migrations."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


REGISTRY_RELATIVE_PATH = Path("data/platform/database_migration_registry_v1.json")
MAX_REGISTRY_BYTES = 256 * 1024
MAX_MIGRATION_BYTES = 2 * 1024 * 1024
DATABASE_IDS = frozenset({"postgresql", "clickhouse"})
EXECUTION_CLASSES = frozenset(
    {
        "BOOTSTRAP_SCHEMA",
        "ADDITIVE_SCHEMA",
        "CONTROLLED_DATA_SEED",
        "DESTRUCTIVE_CLEANUP",
        "VIEW_REPLACEMENT",
        "READ_ONLY_GRANT",
    }
)
ROLLBACK_CLASSES = frozenset({"BACKUP_RESTORE_REQUIRED", "REVOKE_GRANT"})


class MigrationAuthorityError(ValueError):
    """Raised when migration source authority is missing, ambiguous, or changed."""


@dataclass(frozen=True)
class MigrationRecord:
    migration_id: str
    database_id: str
    sequence: int
    path: Path
    sha256: str
    execution_class: str
    rollback_class: str


@dataclass(frozen=True)
class MigrationAuthority:
    contract_id: str
    contract_version: str
    status: str
    registry_path: Path
    records: tuple[MigrationRecord, ...]
    source_fingerprint: str

    def records_for(self, database_id: str) -> tuple[MigrationRecord, ...]:
        if database_id not in DATABASE_IDS:
            raise MigrationAuthorityError("database identifier is not registered")
        return tuple(
            record for record in self.records if record.database_id == database_id
        )


def project_root_from(module_path: Path | None = None) -> Path:
    """Resolve the project root without accepting an unbounded runtime path."""

    source = (module_path or Path(__file__)).resolve()
    for root in (source.parents[1], source.parents[2]):
        if (root / REGISTRY_RELATIVE_PATH).is_file():
            return root
    raise MigrationAuthorityError("migration registry project root is unavailable")


def default_registry_path(project_root: Path | None = None) -> Path:
    return (project_root or project_root_from()) / REGISTRY_RELATIVE_PATH


def _bounded_path(project_root: Path, relative_value: str) -> Path:
    relative_path = Path(relative_value)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise MigrationAuthorityError("migration path is outside the project root")
    resolved_root = project_root.resolve()
    resolved = (resolved_root / relative_path).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise MigrationAuthorityError("migration path escaped the project root") from exc
    if not resolved.is_file() or resolved.suffix.lower() != ".sql":
        raise MigrationAuthorityError("registered migration source is unavailable")
    if resolved.stat().st_size > MAX_MIGRATION_BYTES:
        raise MigrationAuthorityError("registered migration source is oversized")
    return resolved


def _load_payload(registry_path: Path) -> dict[str, Any]:
    if not registry_path.is_file() or registry_path.stat().st_size > MAX_REGISTRY_BYTES:
        raise MigrationAuthorityError("migration registry is unavailable or oversized")
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationAuthorityError("migration registry is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise MigrationAuthorityError("migration registry root is invalid")
    return payload


def _source_catalog(project_root: Path) -> set[str]:
    return {
        "database/create_tables.sql",
        *(
            path.relative_to(project_root).as_posix()
            for path in (project_root / "database/migrations").glob("*.sql")
        ),
        *(
            path.relative_to(project_root).as_posix()
            for path in (project_root / "postgres/init").glob("*.sql")
        ),
    }


def load_migration_authority(
    registry_path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> MigrationAuthority:
    """Validate and return migration source authority without database access."""

    resolved_root = (project_root or project_root_from()).resolve()
    resolved_registry = (registry_path or default_registry_path(resolved_root)).resolve()
    if resolved_registry != (resolved_root / REGISTRY_RELATIVE_PATH).resolve():
        raise MigrationAuthorityError("migration registry path is not authoritative")
    payload = _load_payload(resolved_registry)
    required = {
        "contract_id",
        "contract_version",
        "status",
        "technical_owner",
        "live_execution_authorized",
        "databases",
        "excluded_sql_files",
        "migrations",
    }
    if not required.issubset(payload):
        raise MigrationAuthorityError("migration registry is missing required fields")
    if payload["status"] != "SOURCE_AUTHORITY_NO_EXECUTION":
        raise MigrationAuthorityError("migration registry status permits execution")
    if payload["live_execution_authorized"] is not False:
        raise MigrationAuthorityError("migration registry unexpectedly authorizes execution")

    databases = payload["databases"]
    if not isinstance(databases, list) or len(databases) != 2:
        raise MigrationAuthorityError("database authority catalog is invalid")
    database_catalog = {
        item.get("database_id"): item
        for item in databases
        if isinstance(item, dict)
    }
    if set(database_catalog) != DATABASE_IDS:
        raise MigrationAuthorityError("database authority catalog is incomplete")

    raw_migrations = payload["migrations"]
    if not isinstance(raw_migrations, list) or not (1 <= len(raw_migrations) <= 64):
        raise MigrationAuthorityError("migration catalog size is invalid")
    records: list[MigrationRecord] = []
    migration_ids: set[str] = set()
    paths: set[str] = set()
    sequences: dict[str, list[int]] = {database_id: [] for database_id in DATABASE_IDS}
    fingerprint_parts: list[str] = []
    for raw in raw_migrations:
        if not isinstance(raw, dict):
            raise MigrationAuthorityError("migration entry is invalid")
        try:
            migration_id = raw["migration_id"]
            database_id = raw["database_id"]
            sequence = raw["sequence"]
            relative_path = raw["path"]
            expected_hash = raw["sha256"]
            execution_class = raw["execution_class"]
            rollback_class = raw["rollback_class"]
        except KeyError as exc:
            raise MigrationAuthorityError("migration entry is incomplete") from exc
        if (
            not isinstance(migration_id, str)
            or not migration_id.startswith(f"{database_id}-")
            or migration_id in migration_ids
        ):
            raise MigrationAuthorityError("migration identifier is invalid or duplicated")
        if database_id not in DATABASE_IDS:
            raise MigrationAuthorityError("migration database is not registered")
        if not isinstance(sequence, int) or sequence < 0:
            raise MigrationAuthorityError("migration sequence is invalid")
        if sequence in sequences[database_id]:
            raise MigrationAuthorityError("migration sequence is duplicated")
        if not isinstance(relative_path, str) or relative_path in paths:
            raise MigrationAuthorityError("migration path is invalid or duplicated")
        if execution_class not in EXECUTION_CLASSES:
            raise MigrationAuthorityError("migration execution class is invalid")
        if rollback_class not in ROLLBACK_CLASSES:
            raise MigrationAuthorityError("migration rollback class is invalid")
        source = _bounded_path(resolved_root, relative_path)
        actual_hash = sha256(source.read_bytes()).hexdigest()
        if expected_hash != actual_hash:
            raise MigrationAuthorityError(f"migration source hash drifted: {relative_path}")
        records.append(
            MigrationRecord(
                migration_id=migration_id,
                database_id=database_id,
                sequence=sequence,
                path=source,
                sha256=actual_hash,
                execution_class=execution_class,
                rollback_class=rollback_class,
            )
        )
        migration_ids.add(migration_id)
        paths.add(relative_path)
        sequences[database_id].append(sequence)
        fingerprint_parts.append(
            "|".join(
                (
                    migration_id,
                    database_id,
                    str(sequence),
                    relative_path,
                    actual_hash,
                    execution_class,
                    rollback_class,
                )
            )
        )

    if any(values != sorted(values) for values in sequences.values()):
        raise MigrationAuthorityError("migration order is not deterministic")
    if paths != _source_catalog(resolved_root):
        raise MigrationAuthorityError("migration registry does not cover the SQL source catalog")
    for database_id, database in database_catalog.items():
        if database.get("ledger_migration_id") not in migration_ids:
            raise MigrationAuthorityError(
                f"{database_id} migration ledger is not registered"
            )
    excluded = payload["excluded_sql_files"]
    if not isinstance(excluded, list) or not excluded:
        raise MigrationAuthorityError("excluded SQL source policy is missing")
    for item in excluded:
        if not isinstance(item, dict) or not item.get("reason"):
            raise MigrationAuthorityError("excluded SQL source entry is invalid")
        excluded_path = _bounded_path(resolved_root, item.get("path", ""))
        if excluded_path.relative_to(resolved_root).as_posix() in paths:
            raise MigrationAuthorityError("excluded SQL source is registered as a migration")

    return MigrationAuthority(
        contract_id=payload["contract_id"],
        contract_version=payload["contract_version"],
        status=payload["status"],
        registry_path=resolved_registry,
        records=tuple(records),
        source_fingerprint=sha256("\n".join(fingerprint_parts).encode("utf-8")).hexdigest(),
    )
