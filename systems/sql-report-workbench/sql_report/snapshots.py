"""Materialize only bounded caller-declared tables; original databases are not imported."""
import sqlite3
import uuid
from . import runtime as r

MAX_SNAPSHOT=32*1024*1024


def create(data,data_sha):
    relative='snapshots/'+uuid.uuid4().hex+'.sqlite3';path=r.local_path(relative,False);r.write_new(path,b'')
    with r.io_errors(),r.guarded._store_scope(path,initial=True):
        con=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True)
        try:
            con.execute('BEGIN IMMEDIATE')
            for table in data['tables']:
                columns=','.join('"'+column['name']+'" '+{'integer':'INTEGER','real':'REAL','text':'TEXT'}[column['type']]+('' if column['nullable'] else ' NOT NULL') for column in table['columns'])
                con.execute('CREATE TABLE "'+table['name']+'" ('+columns+')')
                con.executemany('INSERT INTO "'+table['name']+'" VALUES('+','.join('?' for _ in table['columns'])+')',table['rows'])
            if con.execute('PRAGMA page_count').fetchone()[0]*con.execute('PRAGMA page_size').fetchone()[0]>MAX_SNAPSHOT:raise r.WorkbenchError('SNAPSHOT_LIMIT')
            con.commit()
        except BaseException:con.rollback();raise
        finally:con.close()
    return relative,r.digest(r.read_bytes(path,MAX_SNAPSHOT))


def request(data,relative,file_sha):
    path=r.local_path(relative);raw=r.read_bytes(path,MAX_SNAPSHOT)
    if r.digest(raw)!=file_sha:raise r.WorkbenchError('SNAPSHOT_HASH_MISMATCH')
    return dict(snapshot=str(path),snapshot_sha256=file_sha,tables=[table['name'] for table in data['tables']])
