CREATE TABLE sources (
    source_id INTEGER PRIMARY KEY,
    source_key TEXT NOT NULL COLLATE NOCASE UNIQUE,
    display_name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (
        source_type IN ('document', 'dataset', 'sql_query', 'metric', 'other')
    ),
    authority_note TEXT,
    location_hint TEXT,
    config_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(config_json)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    )
) STRICT;

CREATE TABLE ingestion_runs (
    run_id TEXT PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    status TEXT NOT NULL CHECK (
        status IN ('running', 'succeeded', 'failed', 'partial')
    ),
    trigger_type TEXT NOT NULL DEFAULT 'manual' CHECK (
        trigger_type IN ('manual', 'scheduled', 'api', 'test')
    ),
    input_reference TEXT,
    input_sha256 TEXT CHECK (
        input_sha256 IS NULL OR length(input_sha256) = 64
    ),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    records_read INTEGER NOT NULL DEFAULT 0 CHECK (records_read >= 0),
    records_written INTEGER NOT NULL DEFAULT 0 CHECK (records_written >= 0),
    records_rejected INTEGER NOT NULL DEFAULT 0 CHECK (records_rejected >= 0),
    error_summary TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
) STRICT;

CREATE TABLE data_assets (
    asset_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id),
    asset_type TEXT NOT NULL CHECK (
        asset_type IN (
            'document',
            'dataset',
            'sql_result',
            'metric_batch',
            'other'
        )
    ),
    logical_name TEXT NOT NULL,
    source_uri TEXT,
    media_type TEXT,
    byte_size INTEGER CHECK (byte_size IS NULL OR byte_size >= 0),
    content_sha256 TEXT CHECK (
        content_sha256 IS NULL OR length(content_sha256) = 64
    ),
    source_modified_at TEXT,
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
) STRICT;

CREATE UNIQUE INDEX ux_data_assets_content
    ON data_assets(source_id, asset_type, content_sha256)
    WHERE content_sha256 IS NOT NULL;
CREATE INDEX ix_data_assets_run ON data_assets(run_id);
CREATE INDEX ix_data_assets_source_ingested
    ON data_assets(source_id, ingested_at DESC);

CREATE TABLE documents (
    document_id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL UNIQUE
        REFERENCES data_assets(asset_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    author TEXT,
    language TEXT,
    page_count INTEGER CHECK (page_count IS NULL OR page_count >= 0),
    extraction_status TEXT NOT NULL CHECK (
        extraction_status IN ('extracted', 'not_supported', 'failed', 'pending')
    ),
    extracted_text TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
) STRICT;

CREATE TABLE document_chunks (
    chunk_id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL
        REFERENCES documents(document_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    char_start INTEGER NOT NULL CHECK (char_start >= 0),
    char_end INTEGER NOT NULL CHECK (char_end >= char_start),
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    UNIQUE(document_id, chunk_index)
) STRICT;

CREATE INDEX ix_document_chunks_document
    ON document_chunks(document_id, chunk_index);

CREATE VIRTUAL TABLE document_chunks_fts USING fts5(
    content,
    content='document_chunks',
    content_rowid='chunk_id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER document_chunks_ai AFTER INSERT ON document_chunks BEGIN
    INSERT INTO document_chunks_fts(rowid, content)
    VALUES (new.chunk_id, new.content);
END;

CREATE TRIGGER document_chunks_ad AFTER DELETE ON document_chunks BEGIN
    INSERT INTO document_chunks_fts(document_chunks_fts, rowid, content)
    VALUES ('delete', old.chunk_id, old.content);
END;

CREATE TRIGGER document_chunks_au AFTER UPDATE ON document_chunks BEGIN
    INSERT INTO document_chunks_fts(document_chunks_fts, rowid, content)
    VALUES ('delete', old.chunk_id, old.content);
    INSERT INTO document_chunks_fts(rowid, content)
    VALUES (new.chunk_id, new.content);
END;

CREATE TABLE datasets (
    dataset_id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL UNIQUE
        REFERENCES data_assets(asset_id) ON DELETE CASCADE,
    data_format TEXT NOT NULL CHECK (
        data_format IN ('csv', 'json', 'jsonl', 'ndjson', 'other')
    ),
    row_count INTEGER NOT NULL DEFAULT 0 CHECK (row_count >= 0),
    column_count INTEGER NOT NULL DEFAULT 0 CHECK (column_count >= 0),
    schema_json TEXT NOT NULL DEFAULT '{"columns":[]}'
        CHECK (json_valid(schema_json)),
    key_column TEXT,
    observed_at_column TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
) STRICT;

CREATE TABLE dataset_rows (
    dataset_row_id INTEGER PRIMARY KEY,
    dataset_id INTEGER NOT NULL
        REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL CHECK (row_number >= 1),
    record_key TEXT,
    observed_at TEXT,
    row_json TEXT NOT NULL CHECK (json_valid(row_json)),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    UNIQUE(dataset_id, row_number)
) STRICT;

CREATE INDEX ix_dataset_rows_record_key
    ON dataset_rows(dataset_id, record_key);
CREATE INDEX ix_dataset_rows_observed_at
    ON dataset_rows(dataset_id, observed_at);

CREATE TABLE sql_queries (
    query_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    query_key TEXT NOT NULL COLLATE NOCASE,
    display_name TEXT NOT NULL,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_id, query_key)
) STRICT;

CREATE TABLE sql_query_versions (
    query_version_id INTEGER PRIMARY KEY,
    query_id INTEGER NOT NULL
        REFERENCES sql_queries(query_id) ON DELETE CASCADE,
    query_sha256 TEXT NOT NULL CHECK (length(query_sha256) = 64),
    query_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(query_id, query_sha256)
) STRICT;

CREATE TABLE sql_executions (
    execution_id TEXT PRIMARY KEY,
    query_id INTEGER NOT NULL REFERENCES sql_queries(query_id),
    query_version_id INTEGER REFERENCES sql_query_versions(query_version_id),
    run_id TEXT NOT NULL UNIQUE REFERENCES ingestion_runs(run_id),
    asset_id INTEGER NOT NULL UNIQUE REFERENCES data_assets(asset_id),
    server_name TEXT,
    database_name TEXT,
    execution_status TEXT NOT NULL CHECK (
        execution_status IN ('imported', 'succeeded', 'failed', 'partial')
    ),
    executed_at TEXT,
    imported_at TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0 CHECK (row_count >= 0),
    result_schema_json TEXT NOT NULL DEFAULT '{"columns":[]}'
        CHECK (json_valid(result_schema_json)),
    parameters_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(parameters_json)),
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
) STRICT;

CREATE INDEX ix_sql_executions_query_imported
    ON sql_executions(query_id, imported_at DESC);

CREATE TABLE sql_result_rows (
    sql_result_row_id INTEGER PRIMARY KEY,
    execution_id TEXT NOT NULL
        REFERENCES sql_executions(execution_id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL CHECK (row_number >= 1),
    record_key TEXT,
    row_json TEXT NOT NULL CHECK (json_valid(row_json)),
    row_sha256 TEXT NOT NULL CHECK (length(row_sha256) = 64),
    UNIQUE(execution_id, row_number)
) STRICT;

CREATE INDEX ix_sql_result_rows_record_key
    ON sql_result_rows(execution_id, record_key);

CREATE TABLE metric_definitions (
    metric_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    metric_key TEXT NOT NULL COLLATE NOCASE,
    display_name TEXT NOT NULL,
    description TEXT,
    unit TEXT,
    value_kind TEXT NOT NULL CHECK (
        value_kind IN ('numeric', 'text', 'boolean', 'json')
    ),
    dimensions_schema_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(dimensions_schema_json)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_id, metric_key)
) STRICT;

CREATE TABLE metric_observations (
    observation_id INTEGER PRIMARY KEY,
    metric_id INTEGER NOT NULL REFERENCES metric_definitions(metric_id),
    run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id),
    observed_at TEXT NOT NULL,
    value_number REAL,
    value_text TEXT,
    value_json TEXT CHECK (
        value_json IS NULL OR json_valid(value_json)
    ),
    dimensions_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(dimensions_json)),
    quality_status TEXT NOT NULL DEFAULT 'valid' CHECK (
        quality_status IN ('valid', 'suspect', 'invalid')
    ),
    dedupe_key TEXT NOT NULL UNIQUE CHECK (length(dedupe_key) = 64),
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    CHECK (
        (CASE WHEN value_number IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN value_text IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN value_json IS NOT NULL THEN 1 ELSE 0 END) = 1
    )
) STRICT;

CREATE INDEX ix_metric_observations_metric_time
    ON metric_observations(metric_id, observed_at DESC);

CREATE TABLE rejected_records (
    rejected_record_id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id),
    asset_id INTEGER REFERENCES data_assets(asset_id),
    record_number INTEGER,
    record_reference TEXT,
    raw_payload TEXT,
    reason_code TEXT NOT NULL,
    reason_detail TEXT NOT NULL,
    created_at TEXT NOT NULL
) STRICT;

CREATE INDEX ix_rejected_records_run ON rejected_records(run_id);

CREATE TABLE data_quality_issues (
    issue_id INTEGER PRIMARY KEY,
    run_id TEXT REFERENCES ingestion_runs(run_id),
    asset_id INTEGER REFERENCES data_assets(asset_id),
    severity TEXT NOT NULL CHECK (
        severity IN ('info', 'warning', 'error', 'critical')
    ),
    rule_code TEXT NOT NULL,
    record_reference TEXT,
    message TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(details_json)),
    status TEXT NOT NULL DEFAULT 'open' CHECK (
        status IN ('open', 'resolved', 'accepted')
    ),
    created_at TEXT NOT NULL,
    resolved_at TEXT
) STRICT;

CREATE INDEX ix_data_quality_issues_status
    ON data_quality_issues(status, severity);

CREATE TABLE lineage_edges (
    lineage_id INTEGER PRIMARY KEY,
    parent_asset_id INTEGER NOT NULL
        REFERENCES data_assets(asset_id) ON DELETE CASCADE,
    child_asset_id INTEGER NOT NULL
        REFERENCES data_assets(asset_id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL CHECK (
        relationship_type IN (
            'derived_from',
            'combined_from',
            'validated_against',
            'supersedes'
        )
    ),
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    CHECK (parent_asset_id <> child_asset_id),
    UNIQUE(parent_asset_id, child_asset_id, relationship_type)
) STRICT;

CREATE VIEW v_asset_catalog AS
SELECT
    a.asset_id,
    a.asset_type,
    a.logical_name,
    a.source_uri,
    a.media_type,
    a.byte_size,
    a.content_sha256,
    a.source_modified_at,
    a.observed_at,
    a.ingested_at,
    s.source_key,
    s.display_name AS source_name,
    s.source_type,
    r.run_id,
    r.status AS ingestion_status
FROM data_assets AS a
JOIN sources AS s ON s.source_id = a.source_id
JOIN ingestion_runs AS r ON r.run_id = a.run_id;

CREATE VIEW v_ingestion_run_summary AS
SELECT
    r.run_id,
    s.source_key,
    s.display_name AS source_name,
    s.source_type,
    r.status,
    r.trigger_type,
    r.input_reference,
    r.started_at,
    r.completed_at,
    r.records_read,
    r.records_written,
    r.records_rejected,
    r.error_summary,
    COUNT(DISTINCT a.asset_id) AS asset_count,
    COUNT(DISTINCT q.issue_id) AS quality_issue_count
FROM ingestion_runs AS r
JOIN sources AS s ON s.source_id = r.source_id
LEFT JOIN data_assets AS a ON a.run_id = r.run_id
LEFT JOIN data_quality_issues AS q ON q.run_id = r.run_id
GROUP BY
    r.run_id,
    s.source_key,
    s.display_name,
    s.source_type,
    r.status,
    r.trigger_type,
    r.input_reference,
    r.started_at,
    r.completed_at,
    r.records_read,
    r.records_written,
    r.records_rejected,
    r.error_summary;

CREATE VIEW v_latest_metric_observations AS
WITH ranked AS (
    SELECT
        o.*,
        row_number() OVER (
            PARTITION BY o.metric_id, o.dimensions_json
            ORDER BY o.observed_at DESC, o.observation_id DESC
        ) AS recency_rank
    FROM metric_observations AS o
)
SELECT
    r.observation_id,
    d.metric_key,
    d.display_name,
    d.unit,
    d.value_kind,
    r.observed_at,
    r.value_number,
    r.value_text,
    r.value_json,
    r.dimensions_json,
    r.quality_status,
    s.source_key
FROM ranked AS r
JOIN metric_definitions AS d ON d.metric_id = r.metric_id
JOIN sources AS s ON s.source_id = d.source_id
WHERE r.recency_rank = 1;

PRAGMA user_version = 1;
