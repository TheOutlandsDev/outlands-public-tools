DROP INDEX ux_data_assets_content;

CREATE UNIQUE INDEX ux_data_assets_file_content
    ON data_assets(source_id, asset_type, content_sha256)
    WHERE content_sha256 IS NOT NULL
      AND asset_type IN ('document', 'dataset');

ALTER TABLE sql_executions ADD COLUMN snapshot_key TEXT;

UPDATE sql_executions
SET snapshot_key = execution_id
WHERE snapshot_key IS NULL;

CREATE UNIQUE INDEX ux_sql_executions_snapshot_key
    ON sql_executions(query_id, snapshot_key)
    WHERE snapshot_key IS NOT NULL;

PRAGMA user_version = 2;
