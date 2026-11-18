import json
from pathlib import Path
import shutil

import pytest

from production_planning.migration_authority import (
    MigrationAuthorityError,
    load_migration_authority,
)


ROOT = Path(__file__).resolve().parents[1]


def _copy_authority_tree(destination: Path) -> Path:
    root = destination / "project"
    (root / "data/platform").mkdir(parents=True)
    (root / "database").mkdir(parents=True)
    shutil.copy2(
        ROOT / "data/platform/database_migration_registry_v1.json",
        root / "data/platform/database_migration_registry_v1.json",
    )
    shutil.copy2(ROOT / "database/create_tables.sql", root / "database/create_tables.sql")
    shutil.copy2(ROOT / "database/load_test_data.sql", root / "database/load_test_data.sql")
    shutil.copytree(ROOT / "database/migrations", root / "database/migrations")
    shutil.copytree(ROOT / "postgres/init", root / "postgres/init")
    return root


def test_migration_authority_covers_both_databases_without_execution() -> None:
    authority = load_migration_authority(project_root=ROOT)

    assert authority.status == "SOURCE_AUTHORITY_NO_EXECUTION"
    assert len(authority.records) == 26
    assert [record.sequence for record in authority.records_for("postgresql")] == list(
        range(1, 18)
    )
    assert [record.sequence for record in authority.records_for("clickhouse")] == [
        0,
        5,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
    ]
    assert len(authority.source_fingerprint) == 64


def test_destructive_history_is_explicit_and_requires_backup_restore() -> None:
    authority = load_migration_authority(project_root=ROOT)
    destructive = [
        record for record in authority.records if record.execution_class == "DESTRUCTIVE_CLEANUP"
    ]

    assert [record.migration_id for record in destructive] == [
        "clickhouse-008-demo-retention"
    ]
    assert destructive[0].rollback_class == "BACKUP_RESTORE_REQUIRED"


def test_ledgers_do_not_grant_application_migration_writes() -> None:
    postgres_ledger = (ROOT / "postgres/init/010_demo_migration_ledger.sql").read_text(
        encoding="utf-8"
    )
    clickhouse_ledger = (
        ROOT / "database/migrations/012_demo_migration_ledger.sql"
    ).read_text(encoding="utf-8")

    assert "GRANT SELECT ON demo_migration_ledger TO demo_reader" in postgres_ledger
    assert "GRANT INSERT" not in postgres_ledger
    assert "GRANT UPDATE" not in postgres_ledger
    assert "GRANT DELETE" not in postgres_ledger
    assert "ENGINE = MergeTree" in clickhouse_ledger
    assert "ReplacingMergeTree" not in clickhouse_ledger


def test_migration_source_hash_drift_fails_closed(tmp_path: Path) -> None:
    root = _copy_authority_tree(tmp_path)
    source = root / "postgres/init/003_demo_operator_events.sql"
    source.write_text(source.read_text(encoding="utf-8") + "\n-- drift\n", encoding="utf-8")

    with pytest.raises(MigrationAuthorityError, match="source hash drifted"):
        load_migration_authority(project_root=root)


def test_unregistered_sql_source_fails_closed(tmp_path: Path) -> None:
    root = _copy_authority_tree(tmp_path)
    (root / "database/migrations/013_unregistered.sql").write_text(
        "SELECT 1;\n", encoding="utf-8"
    )

    with pytest.raises(MigrationAuthorityError, match="does not cover"):
        load_migration_authority(project_root=root)


def test_execution_authorization_cannot_be_enabled_in_registry(tmp_path: Path) -> None:
    root = _copy_authority_tree(tmp_path)
    registry = root / "data/platform/database_migration_registry_v1.json"
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["live_execution_authorized"] = True
    registry.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(MigrationAuthorityError, match="authorizes execution"):
        load_migration_authority(project_root=root)
