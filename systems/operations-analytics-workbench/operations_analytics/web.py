"""Local single-operator UI; authenticated API reads/writes and fixed errors."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import secrets
from urllib.parse import urlparse,parse_qs
import threading
from . import application as app,runtime

TOKEN=secrets.token_urlsafe(32)


class LocalServer(ThreadingHTTPServer):
    daemon_threads=False
    block_on_close=True


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(10)
    def log_message(self,*args):pass
    def allowed_host(self):return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def send(self,value,status=200,html=False):
        raw=value.encode('utf-8') if html else runtime.encode(value)
        self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if not self.allowed_host():self.send(dict(error='HOST_REFUSED'),403);return
        path=urlparse(self.path)
        if path.path=='/':
            self.send((runtime.SOURCE/'operations_analytics/ui.html').read_text(encoding='utf-8').replace('__SESSION_TOKEN__',TOKEN),html=True);return
        if self.headers.get('X-Outlands-Token')!=TOKEN:self.send(dict(error='SESSION_REQUIRED'),403);return
        try:
            query=parse_qs(path.query,max_num_fields=8);identifier=query.get('project',[''])[0]
            if path.path=='/api/projects':result=app.projects()
            elif path.path=='/api/project':result=app.show(identifier,int(query['revision'][0]) if 'revision' in query else None)
            elif path.path=='/api/plan':result=app.plan(identifier,int(query['revision'][0]) if 'revision' in query else None)
            elif path.path=='/api/compare':result=app.compare(identifier,int(query['left'][0]),int(query['right'][0]))
            elif path.path=='/api/history':result=app.history(identifier)
            elif path.path=='/api/example':result=runtime.decode(runtime.read_bytes(runtime.SOURCE/'examples/sample-scenario.json'))
            else:self.send(dict(error='NOT_FOUND'),404);return
            self.send(result)
        except Exception:self.send(dict(error='OPERATION_REFUSED'),400)
    def do_POST(self):
        if not self.allowed_host() or self.headers.get('X-Outlands-Token')!=TOKEN:self.send(dict(error='SESSION_REQUIRED'),403);return
        if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            self.send(dict(error='ORIGIN_REFUSED'),403);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if self.headers.get('Transfer-Encoding') or not 0<length<=runtime.MAX_INPUT:raise ValueError('BODY_LIMIT')
            raw=self.rfile.read(length)
            if len(raw)!=length:raise ValueError('BODY_INCOMPLETE')
            value=runtime.decode(raw)
            path=urlparse(self.path).path
            if path=='/api/save':
                if type(value) is not dict or set(value)!={'scenario','expected'}:raise ValueError('BODY_INVALID')
                result=app.save(runtime.encode(value['scenario']),value['expected'])
            elif path=='/api/review':result=app.review(raw)
            elif path=='/api/ingest':
                if type(value) is not dict or set(value)!={'project_id','file','expected'}:raise ValueError('BODY_INVALID')
                result=app.ingest(value['project_id'],value['file'],value['expected'])
            elif path=='/api/attach-planning':
                if type(value) is not dict or set(value)!={'project_id','directory','expected'}:raise ValueError('BODY_INVALID')
                result=app.attach_planning(value['project_id'],value['directory'],value['expected'])
            elif path=='/api/export':
                if type(value) is not dict or set(value)!={'project_id'}:raise ValueError('BODY_INVALID')
                result=app.export(value['project_id'])
            elif path=='/api/backup':
                if value!={}:raise ValueError('BODY_INVALID')
                result=app.backup()
            elif path=='/api/shutdown':
                if value!={}:raise ValueError('BODY_INVALID')
                result=dict(status='STOPPING');threading.Thread(target=self.server.shutdown,daemon=True).start()
            else:self.send(dict(error='NOT_FOUND'),404);return
            self.send(result)
        except Exception:self.send(dict(error='OPERATION_REFUSED'),400)


def serve(port=0):
    server=LocalServer(('127.0.0.1',int(port)),Handler)
    print(runtime.encode(dict(mode='LOOPBACK_ANALYTICS_UI',url=f'http://127.0.0.1:{server.server_port}')).decode(),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
