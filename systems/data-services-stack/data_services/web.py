"""Loopback-only, token-protected UI. No real transport or provider adapter route."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import secrets
import threading
from urllib.parse import urlsplit
from . import files
from .contracts import StackError,canonical,decode,integer
from .service import Stack
from .workbench import Workbench

MAX_BODY=262144
class LocalServer(ThreadingHTTPServer):
    daemon_threads=False
    block_on_close=True
    def __init__(self,address,controller):
        self.controller=controller;self.token=secrets.token_urlsafe(32);self.stopping=threading.Event()
        super().__init__(address,Handler)
    def get_request(self):
        connection,address=super().get_request();connection.settimeout(10);return connection,address
    def handle_error(self,request,address):
        # Native exception details, addresses and paths are not diagnostics.
        pass

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def host_ok(self):return self.headers.get_all('Host',[])==['127.0.0.1:'+str(self.server.server_port)]
    def send(self,value,status=200,*,html=False,nonce=None):
        raw=value if html else canonical(value)
        try:
            self.send_response(status);self.send_header('Content-Type',('text/html' if html else 'application/json')+'; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Content-Type-Options','nosniff')
            policy="default-src 'none'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
            if nonce:policy+="; script-src 'nonce-"+nonce+"'"
            self.send_header('Content-Security-Policy',policy);self.end_headers();self.wfile.write(raw)
        except (OSError,TimeoutError):self.close_connection=True
    def do_GET(self):
        if not self.host_ok():self.send(dict(code='HOST_REFUSED'),403);return
        if self.path!='/':self.send(dict(code='NOT_FOUND'),404);return
        try:
            nonce=secrets.token_urlsafe(24);raw=files.read(files.APPLICATION/'data_services/ui.html',262144).decode('utf-8').replace('__SESSION_TOKEN__',self.server.token).replace('__SCRIPT_NONCE__',nonce).encode('utf-8');self.send(raw,html=True,nonce=nonce)
        except Exception:self.send(dict(code='OPERATION_REFUSED'),400)
    def do_POST(self):
        if not self.host_ok() or self.headers.get_all('X-Outlands-Token',[])!=[self.server.token]:self.send(dict(code='SESSION_REQUIRED'),403);return
        if self.headers.get_all('Origin',[])!=['http://127.0.0.1:'+str(self.server.server_port)]:self.send(dict(code='ORIGIN_REFUSED'),403);return
        try:
            if self.headers.get_all('Content-Type',[])!=['application/json']:raise StackError('CONTENT_TYPE_REFUSED')
            lengths=self.headers.get_all('Content-Length',[])
            if len(lengths)!=1 or self.headers.get_all('Transfer-Encoding',[]):raise StackError('HTTP_FRAMING_REFUSED')
            try:length=int(lengths[0])
            except ValueError:raise StackError('HTTP_FRAMING_REFUSED') from None
            integer(length,2,MAX_BODY,'REQUEST_BYTE_LIMIT');raw=self.rfile.read(length)
            if len(raw)!=length:raise StackError('REQUEST_INCOMPLETE')
            if not self.path.startswith('/api/') or urlsplit(self.path).query or urlsplit(self.path).fragment:raise StackError('OPERATION_REFUSED')
            action=self.path.removeprefix('/api/');data=decode(raw,MAX_BODY)
            with self.server.controller.lock:
                if self.server.stopping.is_set():raise StackError('SERVER_STOPPING')
                result=self.server.controller.apply(action,data)
                if action=='shutdown':
                    self.server.stopping.set();threading.Thread(target=self.server.shutdown,daemon=True).start()
            self.send(dict(result=result))
        except StackError as error:self.send(dict(code=str(error)),400)
        except Exception:self.send(dict(code='OPERATION_REFUSED'),400)

def serve(root,reports,port=0):
    integer(port,0,65535,'PORT_INVALID')
    with Stack(root) as stack:
        controller=Workbench(stack,reports)
        try:
            server=LocalServer(('127.0.0.1',port),controller)
            try:
                print(canonical(dict(mode='FICTIONAL_DATA_SERVICES_UI',url='http://127.0.0.1:'+str(server.server_port),fake_transport_only=True)).decode(),flush=True)
                try:server.serve_forever()
                except KeyboardInterrupt:pass
            finally:server.stopping.set();server.server_close()
        finally:controller.close()
