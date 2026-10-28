"""Fresh bounded SQLite stores with fixed schema and independent logical readback."""
from contextlib import closing
from functools import lru_cache
import sqlite3
from . import contracts as c,runtime as r,engine

SCHEMA='''CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE records(record_id INTEGER PRIMARY KEY,key_json TEXT NOT NULL UNIQUE,data_json TEXT NOT NULL,sha256 TEXT NOT NULL);
CREATE TABLE sources(path TEXT PRIMARY KEY,format TEXT NOT NULL,bytes INTEGER NOT NULL,sha256 TEXT NOT NULL);
CREATE TABLE provenance(record_id INTEGER NOT NULL REFERENCES records(record_id),source TEXT NOT NULL REFERENCES sources(path),first_line INTEGER NOT NULL,last_line INTEGER NOT NULL,source_sha256 TEXT NOT NULL,PRIMARY KEY(source,first_line,last_line));
CREATE TABLE rejected(source TEXT NOT NULL REFERENCES sources(path),first_line INTEGER NOT NULL,last_line INTEGER NOT NULL,source_sha256 TEXT NOT NULL,code TEXT NOT NULL,PRIMARY KEY(source,first_line,last_line));'''

@lru_cache(maxsize=1)
def expected_schema():
    with closing(sqlite3.connect(':memory:')) as con:
        con.executescript(SCHEMA);return con.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name').fetchall()
def validate(con):
    con.execute('PRAGMA trusted_schema=OFF');con.execute('PRAGMA foreign_keys=ON')
    if hasattr(con,'enable_load_extension'):con.enable_load_extension(False)
    rows=con.execute('SELECT type,substr(name,1,257),substr(tbl_name,1,257),substr(sql,1,16385) FROM sqlite_schema ORDER BY type,name LIMIT 129').fetchall()
    if rows!=expected_schema() or con.execute('PRAGMA user_version').fetchone()[0]!=0:c.fail('DESTINATION_SCHEMA_REFUSED')
def expected_rows(plan,plan_pin):
    meta=sorted([('format','outlands-private-import-store-v1'),('contract_json',r.encode(plan['contract']).decode()),('fingerprint',plan['fingerprint']),('plan_sha256',plan_pin)])
    records=[];provenance=[]
    for number,row in enumerate(plan['records'],1):
        records.append((number,r.encode(row['key']).decode(),r.encode(row['data']).decode(),row['sha256']))
        for item in row['provenance']:provenance.append((number,item['source'],item['first_line'],item['last_line'],item['source_sha256']))
    sources=[(s['path'],s['format'],s['bytes'],s['sha256']) for s in plan['sources']]
    rejected=[(s['source'],s['first_line'],s['last_line'],s['source_sha256'],s['code']) for s in plan['rejected']]
    return dict(meta=meta,records=records,sources=sorted(sources),provenance=sorted(provenance,key=lambda row:(row[1],row[2],row[3])),rejected=sorted(rejected))
def readback(con,plan,pin):
    validate(con);expected=expected_rows(plan,pin)
    queries=dict(meta='SELECT key,value FROM meta ORDER BY key',records='SELECT record_id,key_json,data_json,sha256 FROM records ORDER BY record_id',sources='SELECT path,format,bytes,sha256 FROM sources ORDER BY path',provenance='SELECT record_id,source,first_line,last_line,source_sha256 FROM provenance ORDER BY source,first_line,last_line',rejected='SELECT source,first_line,last_line,source_sha256,code FROM rejected ORDER BY source,first_line,last_line')
    for name,query in queries.items():
        if con.execute(query+' LIMIT 1001').fetchall()!=expected[name]:c.fail('DESTINATION_CONTENT_MISMATCH')
    if con.execute('PRAGMA foreign_key_check').fetchone() is not None:c.fail('DESTINATION_FOREIGN_KEY_MISMATCH')
def create(job_id,plan_result):
    plan=engine.read_plan(plan_result,current=True);directory=r.local_path('stores/'+job_id,False);r.mkdir(directory);path=directory/'data.sqlite3';r.write_new(path,b'');expected=expected_rows(plan,plan_result['plan_sha256'])
    with r.io_errors(),r.guarded._store_scope(path,initial=True):
        with closing(sqlite3.connect(path)) as con:
            con.execute('PRAGMA foreign_keys=ON');con.execute('PRAGMA trusted_schema=OFF');con.executescript('BEGIN IMMEDIATE;\n'+SCHEMA)
            try:
                for table,count in (('meta',2),('records',4),('sources',4),('provenance',5),('rejected',5)):con.executemany('INSERT INTO '+table+' VALUES('+','.join('?' for _ in range(count))+')',expected[table])
                readback(con,plan,plan_result['plan_sha256'])
                if con.execute('PRAGMA page_count').fetchone()[0]*con.execute('PRAGMA page_size').fetchone()[0]>c.MAX_OUTPUT_STORE:c.fail('DESTINATION_SIZE_LIMIT')
                con.commit()
            except BaseException:con.rollback();raise
    raw=r.read_bytes(path,c.MAX_OUTPUT_STORE);engine.read_plan(plan_result,current=True)
    result=dict(import_id=job_id,target='stores/'+job_id,plan_id=plan_result['plan_id'],plan_sha256=plan_result['plan_sha256'],fingerprint=plan['fingerprint'],database_sha256=r.digest(raw),database_bytes=len(raw),record_count=len(plan['records']),provenance_count=len(expected['provenance']),rejected_count=len(expected['rejected']))
    verify_database(path,result,plan);r.write_new(directory/'READY.json',r.encode(result));return result
def verify_database(path,result,plan):
    raw=r.read_bytes(path,c.MAX_OUTPUT_STORE)
    if r.digest(raw)!=result['database_sha256'] or len(raw)!=result['database_bytes']:c.fail('DESTINATION_HASH_MISMATCH')
    with r.io_errors(),r.guarded._store_scope(path):
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as con:
            readback(con,plan,result['plan_sha256'])
def verify(result,plan_result):
    c.identifier(result['import_id']);directory=r.local_path('stores/'+result['import_id']);plan=engine.read_plan(plan_result)
    if r.decode(r.read_bytes(directory/'READY.json'))!=result:c.fail('DESTINATION_MARKER_MISMATCH')
    verify_database(directory/'data.sqlite3',result,plan)
    return plan
