CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE revisions(assessment_id TEXT NOT NULL,version INTEGER NOT NULL,sha256 TEXT NOT NULL UNIQUE,parent_sha256 TEXT,payload_json TEXT NOT NULL,PRIMARY KEY(assessment_id,version));
CREATE TRIGGER revision_no_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'append only'); END;
CREATE TRIGGER revision_no_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'append only'); END;
