PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS groups(group_id TEXT PRIMARY KEY,split TEXT NOT NULL CHECK(split IN ('train','validation','test')));
CREATE TABLE IF NOT EXISTS sources(
 source_id TEXT PRIMARY KEY,path TEXT NOT NULL,sha256 TEXT NOT NULL,bytes INTEGER NOT NULL,
 collection TEXT NOT NULL,license_note TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS records(
 id TEXT PRIMARY KEY,content_hash TEXT NOT NULL UNIQUE,
 kind TEXT NOT NULL CHECK(kind IN ('example','document','evaluation')),
 title TEXT NOT NULL,domain TEXT NOT NULL CHECK(domain IN ('coding','devops','mixed','other')),
 language TEXT NOT NULL DEFAULT '',group_id TEXT NOT NULL REFERENCES groups(group_id),
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
 text TEXT NOT NULL,messages_json TEXT NOT NULL DEFAULT '[]',metadata_json TEXT NOT NULL DEFAULT '{}',
 flags_json TEXT NOT NULL DEFAULT '[]',quality_reviewed INTEGER NOT NULL DEFAULT 0,
 privacy_reviewed INTEGER NOT NULL DEFAULT 0,rights_reviewed INTEGER NOT NULL DEFAULT 0,
 context_reviewed INTEGER NOT NULL DEFAULT 0,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS provenance(record_id TEXT NOT NULL REFERENCES records(id),source_id TEXT NOT NULL REFERENCES sources(source_id),
 source_row INTEGER NOT NULL DEFAULT 0,source_key TEXT NOT NULL DEFAULT '',PRIMARY KEY(record_id,source_id,source_row));
CREATE TABLE IF NOT EXISTS group_links(left_group TEXT NOT NULL,right_group TEXT NOT NULL,PRIMARY KEY(left_group,right_group));
CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,record_id TEXT NOT NULL REFERENCES records(id),actor TEXT NOT NULL,
 status TEXT NOT NULL,note TEXT NOT NULL,checks_json TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,action TEXT NOT NULL,detail_json TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,record_id TEXT NOT NULL REFERENCES records(id),ordinal INTEGER NOT NULL,
 text TEXT NOT NULL,sha256 TEXT NOT NULL,UNIQUE(record_id,ordinal));
CREATE TABLE IF NOT EXISTS embeddings(chunk_id TEXT NOT NULL REFERENCES chunks(id),model TEXT NOT NULL,model_digest TEXT NOT NULL,
 dimensions INTEGER NOT NULL,vector_json TEXT NOT NULL,created_utc TEXT NOT NULL,PRIMARY KEY(chunk_id,model,model_digest));
CREATE INDEX IF NOT EXISTS records_filter ON records(status,domain,kind);
CREATE INDEX IF NOT EXISTS records_group ON records(group_id);
CREATE INDEX IF NOT EXISTS provenance_source_row ON provenance(source_id,source_row);
CREATE TABLE IF NOT EXISTS models(name TEXT NOT NULL,digest TEXT NOT NULL,details_json TEXT NOT NULL,observed_utc TEXT NOT NULL,PRIMARY KEY(name,digest));
CREATE TABLE IF NOT EXISTS benchmark_cases(id TEXT PRIMARY KEY,language TEXT NOT NULL,skill TEXT NOT NULL,
 prompt TEXT NOT NULL,rubric_json TEXT NOT NULL,suite_version TEXT NOT NULL,source_path TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS benchmark_runs(id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES benchmark_cases(id),
 model TEXT NOT NULL,model_digest TEXT NOT NULL,status TEXT NOT NULL,answer TEXT NOT NULL DEFAULT '',
 metrics_json TEXT NOT NULL DEFAULT '{}',request_json TEXT NOT NULL,error TEXT NOT NULL DEFAULT '',
 score REAL,scored_by TEXT,score_note TEXT,created_utc TEXT NOT NULL,finished_utc TEXT);
CREATE TABLE IF NOT EXISTS discussions(id TEXT PRIMARY KEY,task TEXT NOT NULL,status TEXT NOT NULL,
 config_json TEXT NOT NULL,final_answer TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT '',created_utc TEXT NOT NULL,finished_utc TEXT);
CREATE TABLE IF NOT EXISTS discussion_turns(id INTEGER PRIMARY KEY,discussion_id TEXT NOT NULL REFERENCES discussions(id),
 ordinal INTEGER NOT NULL,role TEXT NOT NULL,model TEXT NOT NULL,model_digest TEXT NOT NULL,
 input_json TEXT NOT NULL,answer TEXT NOT NULL,metrics_json TEXT NOT NULL,created_utc TEXT NOT NULL,
 UNIQUE(discussion_id,ordinal));
CREATE VIRTUAL TABLE IF NOT EXISTS record_fts USING fts5(title,text,content='records',content_rowid='rowid');
CREATE TRIGGER IF NOT EXISTS record_insert AFTER INSERT ON records BEGIN
 INSERT INTO record_fts(rowid,title,text) VALUES(new.rowid,new.title,new.text);
END;
CREATE TRIGGER IF NOT EXISTS record_delete AFTER DELETE ON records BEGIN
 INSERT INTO record_fts(record_fts,rowid,title,text) VALUES('delete',old.rowid,old.title,old.text);
END;
CREATE TRIGGER IF NOT EXISTS record_text_update AFTER UPDATE OF title,text ON records BEGIN
 INSERT INTO record_fts(record_fts,rowid,title,text) VALUES('delete',old.rowid,old.title,old.text);
 INSERT INTO record_fts(rowid,title,text) VALUES(new.rowid,new.title,new.text);
END;
