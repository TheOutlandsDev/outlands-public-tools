PRAGMA foreign_keys=ON;
CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE revisions(
 project_id TEXT NOT NULL, sequence INTEGER NOT NULL CHECK(sequence>0),
 revision_sha256 TEXT PRIMARY KEY, parent_sha256 TEXT, snapshot_json TEXT NOT NULL,
 created_utc TEXT NOT NULL, UNIQUE(project_id,sequence));
CREATE TABLE actions(
 action_id TEXT NOT NULL, row_version INTEGER NOT NULL CHECK(row_version>0),
 project_id TEXT NOT NULL, revision_sha256 TEXT NOT NULL REFERENCES revisions(revision_sha256),
 state_json TEXT NOT NULL, event_json TEXT NOT NULL, PRIMARY KEY(action_id,row_version));
CREATE INDEX actions_project ON actions(project_id,revision_sha256);
CREATE TRIGGER revisions_no_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
CREATE TRIGGER revisions_no_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
CREATE TRIGGER actions_no_update BEFORE UPDATE ON actions BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
CREATE TRIGGER actions_no_delete BEFORE DELETE ON actions BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
