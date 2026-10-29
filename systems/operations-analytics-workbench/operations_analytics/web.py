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
    def __init__(self,*args,**kwargs):
        self.operation_lock=threading.RLock();self.nonce=secrets.token_urlsafe(24)
        super().__init__(*args,**kwargs)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(10)
    def log_message(self,*args):pass
    def allowed_host(self):return len(self.headers.get_all('Host',[]))==1 and self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def send(self,value,status=200,html=False):
        raw=value.encode('utf-8') if html else runtime.encode(value)
        self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',f"default-src 'none'; script-src 'nonce-{self.server.nonce}'; style-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        with self.server.operation_lock:self.get_locked()
    def get_locked(self):
        if not self.allowed_host():self.send(dict(error='HOST_REFUSED'),403);return
        path=urlparse(self.path)
        if path.scheme or path.netloc or path.params or path.fragment:self.send(dict(error='TARGET_REFUSED'),400);return
        if path.path=='/' and not path.query:
            self.send((runtime.SOURCE/'operations_analytics/ui.html').read_text(encoding='utf-8').replace('__SESSION_TOKEN__',TOKEN).replace('<script>',f'<script nonce="{self.server.nonce}">'),html=True);return
        if self.headers.get_all('X-Outlands-Token',[])!=[TOKEN]:self.send(dict(error='SESSION_REQUIRED'),403);return
        try:
            query=parse_qs(path.query,max_num_fields=8,keep_blank_values=True)
            allowed={'/api/project':{'project','revision'},'/api/plan':{'project','revision'},'/api/compare':{'project','left','right'},'/api/history':{'project'},'/api/view':{'project'}}.get(path.path,set())
            if set(query)-allowed or any(len(v)!=1 for v in query.values()):raise ValueError('QUERY_INVALID')
            identifier=query.get('project',[''])[0]
            if path.path=='/api/view':result=dict(snapshot=app.show(identifier),plan=app.plan(identifier),history=app.history(identifier),projects=app.projects())
            elif path.path=='/api/projects':result=app.projects()
            elif path.path=='/api/project':result=app.show(identifier,int(query['revision'][0]) if 'revision' in query else None)
            elif path.path=='/api/plan':result=app.plan(identifier,int(query['revision'][0]) if 'revision' in query else None)
            elif path.path=='/api/compare':result=app.compare(identifier,int(query['left'][0]),int(query['right'][0]))
            elif path.path=='/api/history':result=app.history(identifier)
            elif path.path=='/api/example':result=runtime.decode(runtime.read_bytes(runtime.SOURCE/'examples/sample-scenario.json'))
            else:self.send(dict(error='NOT_FOUND'),404);return
            self.send(result)
        except Exception:self.send(dict(error='OPERATION_REFUSED'),400)
    def do_POST(self):
        with self.server.operation_lock:self.post_locked()
    def post_locked(self):
        if not self.allowed_host() or self.headers.get_all('X-Outlands-Token',[])!=[TOKEN]:self.send(dict(error='SESSION_REQUIRED'),403);return
        if len(self.headers.get_all('Origin',[]))>1 or self.headers.get('Origin') not in (None,f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            self.send(dict(error='ORIGIN_REFUSED'),403);return
        try:
            if len(self.headers.get_all('Content-Length',[]))!=1 or not self.headers['Content-Length'].isascii() or not self.headers['Content-Length'].isdecimal():raise ValueError('BODY_FRAMING')
            if len(self.headers.get_all('Content-Type',[]))>1 or self.headers.get('Content-Type','application/json').lower().split(';')[0].strip()!='application/json':raise ValueError('BODY_TYPE')
            target=urlparse(self.path)
            if target.scheme or target.netloc or target.params or target.fragment or target.query:raise ValueError('TARGET_INVALID')
            length=int(self.headers['Content-Length'])
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
                if type(value) is not dict or set(value)!={'project_id','expected'}:raise ValueError('BODY_INVALID')
                if app.show(value['project_id'])['revision_sha256']!=value['expected']:raise ValueError('REVISION_CONFLICT')
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
