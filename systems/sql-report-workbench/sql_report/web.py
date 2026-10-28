"""Local single-operator API; query/report saving and worker execution stay separate."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import re
import secrets
import threading
from urllib.parse import urlparse,parse_qs
from . import application as app,contracts as c,jobs,runtime as r

TOKEN=secrets.token_urlsafe(32)


class LocalServer(ThreadingHTTPServer):
    daemon_threads=False
    block_on_close=True


class Handler(BaseHTTPRequestHandler):
    def setup(self):super().setup();self.connection.settimeout(10)
    def log_message(self,*args):pass
    def allowed_host(self):return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def send(self,value,status=200,html=False):
        raw=value.encode('utf-8') if html else r.encode(value);self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; object-src 'none'; base-uri 'none'");self.end_headers();self.wfile.write(raw)
    def refusal(self,error):
        code=str(error) if isinstance(error,r.WorkbenchError) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',str(error)) else 'OPERATION_REFUSED';self.send(dict(error=code),400)
    def do_GET(self):
        if not self.allowed_host():self.send(dict(error='HOST_REFUSED'),403);return
        path=urlparse(self.path)
        if path.path=='/':self.send((r.SOURCE/'sql_report/ui.html').read_text(encoding='utf-8').replace('__SESSION_TOKEN__',TOKEN),html=True);return
        if self.headers.get('X-Outlands-Token')!=TOKEN:self.send(dict(error='SESSION_REQUIRED'),403);return
        try:
            q=parse_qs(path.query,max_num_fields=8)
            if any(len(value)!=1 for value in q.values()):raise ValueError('QUERY_INVALID')
            identifier=q.get('id',[''])[0]
            if path.path=='/api/datasets':value=app.datasets()
            elif path.path=='/api/dataset':value=app.dataset(identifier)
            elif path.path in ('/api/queries','/api/reports'):value=app.documents('query' if path.path.endswith('queries') else 'report')
            elif path.path in ('/api/query','/api/report'):value=app.document('query' if path.path.endswith('query') else 'report',identifier,int(q['version'][0]) if 'version' in q else None)
            elif path.path=='/api/history':value=app.history(q.get('kind',[''])[0],identifier)
            elif path.path=='/api/artifacts':value=app.artifacts()
            elif path.path=='/api/artifact':value=app.artifact(identifier)
            elif path.path=='/api/job':value=jobs.status(identifier)
            elif path.path=='/api/report-query':value=app.report_query(identifier,q.get('dataset',[''])[0])
            elif path.path=='/api/compare':value=app.compare(q.get('left',[''])[0],q.get('right',[''])[0])
            elif path.path=='/api/example':
                kind=q.get('kind',[''])[0]
                if kind not in ('dataset','query','report'):raise ValueError('KIND_INVALID')
                raw=r.read_bytes(r.SOURCE/('examples/sample-'+kind+('.xml' if kind=='report' else '.json')));value=dict(xml=raw.decode()) if kind=='report' else r.decode(raw)
            else:self.send(dict(error='NOT_FOUND'),404);return
            self.send(value)
        except Exception as error:self.refusal(error)
    def do_POST(self):
        if not self.allowed_host() or self.headers.get('X-Outlands-Token')!=TOKEN:self.send(dict(error='SESSION_REQUIRED'),403);return
        if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):self.send(dict(error='ORIGIN_REFUSED'),403);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if self.headers.get('Transfer-Encoding') or not 0<length<=r.MAX_INPUT:raise ValueError('BODY_LIMIT')
            raw=self.rfile.read(length)
            if len(raw)!=length:raise ValueError('BODY_INCOMPLETE')
            value=r.decode(raw);path=urlparse(self.path).path
            if path=='/api/import':result=app.import_dataset(raw)
            elif path=='/api/save-query':result=app.save_query(raw)
            elif path=='/api/save-report':result=app.save_report(raw)
            elif path=='/api/run':result=app.start_query(raw)
            elif path=='/api/validate-report':result=app.start_validation(raw)
            elif path=='/api/review':result=app.review(raw)
            elif path=='/api/cancel':c.fields(value,('job_id',));result=jobs.cancel(value['job_id'])
            elif path=='/api/export':c.fields(value,('artifact_id',));result=app.export(value['artifact_id'])
            elif path in ('/api/backup','/api/shutdown'):
                if value!={}:raise ValueError('BODY_INVALID')
                if path=='/api/backup':result=app.backup()
                else:result=dict(status='STOPPING');threading.Thread(target=self.server.shutdown,daemon=True).start()
            else:self.send(dict(error='NOT_FOUND'),404);return
            self.send(result)
        except Exception as error:self.refusal(error)


def serve(port=0):
    server=LocalServer(('127.0.0.1',int(port)),Handler);print(r.encode(dict(mode='LOOPBACK_SQL_REPORT_UI',url=f'http://127.0.0.1:{server.server_port}')).decode(),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
