"""Child-only SQLite authorization, heap/VM/deadline/row/result limits and fixed errors."""
import math
from pathlib import Path
import sqlite3
import time
from . import contracts as c,runtime as r

MAX_ROWS=200
MAX_RESULT=1024*1024
FUNCTIONS={'abs','avg','count','sum','total','min','max','round','lower','upper','length','substr','substring','trim','ltrim','rtrim','replace','coalesce','ifnull','nullif','typeof','like','glob','iif','group_concat','row_number','rank','dense_rank','lag','lead','first_value','last_value','nth_value'}


def execute(request):
    c.fields(request,('snapshot','snapshot_sha256','tables','sql','parameters','bindings','mode'));c.hash_value(request['snapshot_sha256']);c.sql(request['sql'])
    if request['mode'] not in ('query','inspect'):raise r.WorkbenchError('MODE_INVALID')
    if type(request['tables']) is not list or not 1<=len(request['tables'])<=8:raise r.WorkbenchError('TABLE_LIMIT')
    for name in request['tables']:c.identifier(name)
    definitions=request['parameters']
    c.query(r.encode(dict(format='outlands-sql-query-v1',query_id='worker-query',title='Worker query',sql=request['sql'],parameters=definitions)));bound=c.bindings(request['bindings'],definitions)
    path=Path(request['snapshot']);raw=r.read_bytes(path,32*1024*1024)
    if r.digest(raw)!=request['snapshot_sha256']:raise r.WorkbenchError('SNAPSHOT_HASH_MISMATCH')
    denied=False;budget=False;steps=0;deadline=time.monotonic()+2
    def authorize(action,first,second,database,source):
        nonlocal denied
        allowed=action in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_RECURSIVE) or action==sqlite3.SQLITE_READ and database in ('main',None) and first in request['tables'] or action==sqlite3.SQLITE_FUNCTION and (second or first or '').casefold() in FUNCTIONS
        if not allowed:denied=True
        return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY
    def progress():
        nonlocal budget,steps
        steps+=1000
        if steps>2000000 or time.monotonic()>deadline:budget=True;return 1
        return 0
    with r.io_errors(),r.guarded._store_scope(path):
        con=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True,timeout=.1)
        try:
            if hasattr(con,'enable_load_extension'):con.enable_load_extension(False)
            con.execute('PRAGMA query_only=ON');con.execute('PRAGMA trusted_schema=OFF');con.execute('PRAGMA temp_store=MEMORY')
            heap=con.execute('PRAGMA hard_heap_limit=67108864').fetchone()
            if not heap or not 0<heap[0]<=67108864:raise r.WorkbenchError('SQLITE_HEAP_GUARD_UNAVAILABLE')
            for category,value in ((sqlite3.SQLITE_LIMIT_LENGTH,32768),(sqlite3.SQLITE_LIMIT_SQL_LENGTH,18000),(sqlite3.SQLITE_LIMIT_COLUMN,32),(sqlite3.SQLITE_LIMIT_EXPR_DEPTH,64),(sqlite3.SQLITE_LIMIT_COMPOUND_SELECT,10),(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER,32),(sqlite3.SQLITE_LIMIT_FUNCTION_ARG,16),(sqlite3.SQLITE_LIMIT_ATTACHED,0),(sqlite3.SQLITE_LIMIT_VDBE_OP,20000)):con.setlimit(category,value)
            con.set_authorizer(authorize);con.set_progress_handler(progress,1000)
            if request['mode']=='inspect':
                statement=request['sql'].rstrip().rstrip(';').rstrip();cur=con.execute('SELECT * FROM ('+statement+') LIMIT 0',bound);columns=[column[0] for column in cur.description]
                plan=[list(row) for row in con.execute('EXPLAIN QUERY PLAN '+statement,bound).fetchmany(201)]
                result=dict(status='completed',columns=columns,rows=plan[:200],truncated=len(plan)>200,mode='inspect',query_executed=False,worker_executed=True)
            else:
                cur=con.execute(request['sql'],bound);columns=[column[0] for column in cur.description];rows=[list(row) for row in cur.fetchmany(MAX_ROWS+1)]
                result=dict(status='completed',columns=columns,rows=rows[:MAX_ROWS],truncated=len(rows)>MAX_ROWS,mode='query',query_executed=True,worker_executed=True)
            for name in result['columns']:c.text(name,256,empty=True,multiline=True)
            for row in result['rows']:
                for cell in row:
                    if type(cell) is bytes:raise r.WorkbenchError('BLOB_RESULT_UNSUPPORTED')
                    if type(cell) is str:c.text(cell,4000,empty=True,multiline=True)
                    elif type(cell) is float and not math.isfinite(cell):raise r.WorkbenchError('NONFINITE_RESULT')
            if len(r.encode(result))>MAX_RESULT:raise r.WorkbenchError('RESULT_LIMIT')
            return result
        except (sqlite3.Error,MemoryError):return dict(status='budget_exceeded' if budget else 'refused',reason='VM_OR_TIME_BUDGET' if budget else 'SQL_AUTHORIZATION_REFUSED' if denied else 'SQLITE_QUERY_REFUSED',worker_executed=True)
        finally:con.close()


def main():
    import sys
    try:result=execute(r.decode(sys.stdin.buffer.read(r.MAX_INPUT+1)))
    except r.WorkbenchError as error:result=dict(status='refused',reason=str(error),worker_executed=True)
    except Exception:result=dict(status='refused',reason='WORKER_REFUSED',worker_executed=True)
    sys.stdout.buffer.write(r.encode(result));sys.stdout.buffer.flush()
