"""Canonical legacy-schema acceptance; never execute selected schema SQL."""
from contextlib import contextmanager
from functools import lru_cache
import sqlite3

MAX_OBJECTS=16
MAX_SQL=8192
PROGRESS_CALLS=100000


def configure(con,readonly=False):
    if sqlite3.sqlite_version_info<(3,33,0):raise ValueError('SQLITE_RUNTIME_UNSUPPORTED')
    if hasattr(con,'enable_load_extension'):con.enable_load_extension(False)
    if hasattr(con,'setconfig') and hasattr(sqlite3,'SQLITE_DBCONFIG_DEFENSIVE'):
        con.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE,True)
    con.execute('PRAGMA trusted_schema=OFF')
    con.execute('PRAGMA foreign_keys=ON')
    if con.execute('PRAGMA trusted_schema').fetchone()[0]!=0:raise ValueError('SQLITE_CONFIGURATION_FAILED')
    if con.execute('PRAGMA foreign_keys').fetchone()[0]!=1:raise ValueError('SQLITE_CONFIGURATION_FAILED')
    if readonly:con.execute('PRAGMA query_only=ON')


def declared(con):
    rows=con.execute('SELECT type,substr(name,1,257),substr(tbl_name,1,257),substr(sql,1,8193),length(name),length(tbl_name),length(sql) FROM main.sqlite_schema LIMIT 17').fetchall()
    if len(rows)>MAX_OBJECTS:raise ValueError('STORE_SCHEMA_MISMATCH')
    result=[]
    for kind,name,table,sql,nlength,tlength,slength in rows:
        if nlength>256 or tlength>256 or slength is not None and slength>MAX_SQL:raise ValueError('STORE_SCHEMA_MISMATCH')
        result.append((kind,name,table,sql))
    return tuple(sorted(result))


def metadata(con,tables):
    output=[]
    for table in tables:
        quoted='"'+table.replace('"','""')+'"'
        for pragma in ('table_xinfo','foreign_key_list','index_list'):
            rows=con.execute('PRAGMA main.'+pragma+'('+quoted+')').fetchmany(33)
            if len(rows)>32:raise ValueError('STORE_SCHEMA_MISMATCH')
            output.append((table,pragma,tuple(sorted(tuple(row) for row in rows))))
        for row in con.execute('PRAGMA main.index_list('+quoted+')'):
            index='"'+row[1].replace('"','""')+'"'
            rows=con.execute('PRAGMA main.index_xinfo('+index+')').fetchmany(33)
            if len(rows)>32:raise ValueError('STORE_SCHEMA_MISMATCH')
            output.append((table,row[1],tuple(tuple(item) for item in rows)))
    return tuple(output)


@lru_cache(maxsize=1)
def reference(trusted_sql):
    con=sqlite3.connect(':memory:')
    try:
        configure(con)
        con.executescript(trusted_sql)
        objects=declared(con)
        tables=tuple(sorted(row[1] for row in objects if row[0]=='table'))
        return objects,tables,metadata(con,tables)
    finally:con.close()


@contextmanager
def validation_budget(con):
    calls=[0]
    def progress():
        calls[0]+=1
        return int(calls[0]>PROGRESS_CALLS)
    con.set_progress_handler(progress,1000)
    try:yield
    finally:con.set_progress_handler(None,0)


def validate(con,trusted_sql):
    expected,tables,expected_metadata=reference(trusted_sql)
    with validation_budget(con):
        if con.execute('PRAGMA main.user_version').fetchone()[0]!=0 or con.execute('PRAGMA main.application_id').fetchone()[0]!=0:
            raise ValueError('STORE_SCHEMA_VERSION')
        actual=declared(con)
        if actual!=expected:raise ValueError('STORE_SCHEMA_MISMATCH')
        if metadata(con,tables)!=expected_metadata:raise ValueError('STORE_SCHEMA_MISMATCH')
        if con.execute('PRAGMA main.foreign_key_check').fetchone() is not None:raise ValueError('STORE_FOREIGN_KEY_VIOLATION')
