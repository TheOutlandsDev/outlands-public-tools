"""Single-operator loopback management UI with per-process request token."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import re
import secrets
import threading
from urllib.parse import urlparse,parse_qs
from . import application as app,runtime as r

TOKEN=secrets.token_urlsafe(32)
class LocalServer(ThreadingHTTPServer):
    daemon_threads=False
    block_on_close=True
class Handler(BaseHTTPRequestHandler):
    def setup(self):super().setup();self.connection.settimeout(10)
    def log_message(self,*args):pass
    def allowed_host(self):return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def send(self,value,status=200,html=False):
        raw=value.encode('utf-8') if html else r.encode(value)
        try:
            self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; object-src 'none'; base-uri 'none'");self.end_headers();self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
    def refusal(self,error):
        code=str(error) if isinstance(error,r.WorkbenchError) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',str(error)) else 'OPERATION_REFUSED';self.send(dict(error=code),400)
    def do_GET(self):
        if not self.allowed_host():self.send(dict(error='HOST_REFUSED'),403);return
        path=urlparse(self.path)
        if path.path=='/':self.send((r.SOURCE/'assessment/ui.html').read_text(encoding='utf-8').replace('__SESSION_TOKEN__',TOKEN),html=True);return
        if self.headers.get('X-Outlands-Token')!=TOKEN:self.send(dict(error='SESSION_REQUIRED'),403);return
        try:
            q=parse_qs(path.query,max_num_fields=6)
            if any(len(v)!=1 for v in q.values()):raise ValueError('QUERY_INVALID')
            identifier=q.get('id',[''])[0]
            if path.path=='/api/list':value=app.assessments()
            elif path.path=='/api/show':value=app.assessment(identifier,int(q['version'][0]) if 'version' in q else None)
            elif path.path=='/api/history':value=app.history(identifier)
            elif path.path=='/api/compare':value=app.compare(identifier,int(q['left'][0]),int(q['right'][0]))
            elif path.path=='/api/example':value=r.decode(r.read_bytes(r.SOURCE/'examples/sample-assessment.json'))
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
            if path=='/api/create':result=app.create(raw)
            elif path=='/api/act':result=app.act(raw)
            elif path=='/api/export':result=app.export(raw)
            elif path in ('/api/backup','/api/shutdown'):
                if value!={}:raise ValueError('BODY_INVALID')
                if path=='/api/backup':result=app.backup()
                else:result=dict(status='STOPPING');threading.Thread(target=self.server.shutdown,daemon=True).start()
            else:self.send(dict(error='NOT_FOUND'),404);return
            self.send(result)
        except Exception as error:self.refusal(error)

def serve(port=0):
    server=LocalServer(('127.0.0.1',int(port)),Handler);print(r.encode(dict(mode='LOOPBACK_ASSESSMENT_UI',url=f'http://127.0.0.1:{server.server_port}')).decode(),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
