"""Literal-loopback, owned-thread local HTTP interface with strict request framing."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import secrets
import threading
from urllib.parse import urlsplit,parse_qs
from . import application as a

class LocalServer(ThreadingHTTPServer):
    daemon_threads=False
    block_on_close=True
    def __init__(self,address,controller):
        if address[0]!='127.0.0.1':raise a.Refused('LOOPBACK_REQUIRED')
        self.controller=controller;self.token=secrets.token_urlsafe(32);self.nonce=secrets.token_urlsafe(24)
        super().__init__(address,Handler)
class Handler(BaseHTTPRequestHandler):
    def setup(self):super().setup();self.connection.settimeout(10)
    def log_message(self,*args):pass
    def send(self,value,status=200,html=False):
        raw=value.encode('utf-8') if html else a.encode(value);self.send_response(status)
        for k,v in [('Content-Type','text/html; charset=utf-8' if html else 'application/json'),('Content-Length',str(len(raw))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('Referrer-Policy','no-referrer'),('Content-Security-Policy',f"default-src 'none'; script-src 'nonce-{self.server.nonce}'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")]:self.send_header(k,v)
        self.end_headers();self.wfile.write(raw)
    def target(self):
        if self.headers.get_all('Host',[])!=['127.0.0.1:'+str(self.server.server_port)]:raise a.Refused('HOST_REFUSED')
        p=urlsplit(self.path)
        if p.scheme or p.netloc or p.fragment or ';' in p.path:raise a.Refused('TARGET_REFUSED')
        return p
    def auth(self):
        if self.headers.get_all('X-Outlands-Token',[])!=[self.server.token]:raise a.Refused('SESSION_REQUIRED')
    def do_GET(self):
        try:
            p=self.target()
            if p.path=='/' and not p.query:
                html=(a.SOURCE/'dataset_workbench/ui.html').read_text(encoding='utf-8').replace('__SESSION_TOKEN__',self.server.token).replace('__SCRIPT_NONCE__',self.server.nonce);self.send(html,html=True);return
            self.auth();q=parse_qs(p.query,keep_blank_values=True,max_num_fields=8)
            if any(len(v)!=1 for v in q.values()):raise a.Refused('QUERY_INVALID')
            if p.path in {'/api/state','/api/refresh'}:
                if set(q)-{'query','status','split','offset','limit'}:raise a.Refused('QUERY_INVALID')
                args={k:v[0] for k,v in q.items()}
                for k in ('offset','limit'):
                    if k in args:args[k]=int(args[k])
                result=self.server.controller.state(**args,refresh=p.path=='/api/refresh')
            elif p.path=='/api/detail' and set(q)=={'id'}:result=self.server.controller.detail(q['id'][0])
            else:self.send({'error':'NOT_FOUND'},404);return
            self.send(result)
        except a.Refused as e:self.send({'error':str(e) if str(e) in {'HOST_REFUSED','SESSION_REQUIRED'} else 'OPERATION_REFUSED'},403 if str(e) in {'HOST_REFUSED','SESSION_REQUIRED'} else 400)
        except Exception:self.send({'error':'OPERATION_REFUSED'},400)
    def do_POST(self):
        try:
            p=self.target();self.auth()
            if self.headers.get_all('Origin',[])!=['http://127.0.0.1:'+str(self.server.server_port)]:raise a.Refused('ORIGIN_REFUSED')
            lengths=self.headers.get_all('Content-Length',[])
            if len(lengths)!=1 or not lengths[0].isascii() or not lengths[0].isdecimal() or not 0<int(lengths[0])<=a.MAX_BODY or self.headers.get_all('Transfer-Encoding',[]) or self.headers.get_all('Content-Type',[])!=['application/json'] or p.query:raise a.Refused('BODY_INVALID')
            raw=self.rfile.read(int(lengths[0]))
            if len(raw)!=int(lengths[0]):raise a.Refused('BODY_INVALID')
            value=a.decode(raw)
            if p.path=='/api/shutdown':
                a.fields(value,set());result={'status':'STOPPING'};threading.Thread(target=self.server.shutdown,daemon=True).start()
            elif p.path in {'/api/import','/api/review','/api/export','/api/backup'}:result=self.server.controller.mutate(p.path.removeprefix('/api/'),value)
            else:self.send({'error':'NOT_FOUND'},404);return
            self.send(result)
        except a.Refused as e:
            code=str(e) if str(e) in {'STALE_STATE_REFRESH_REQUIRED','OPERATION_UNCERTAIN_REFRESH_REQUIRED','FOUR_CHECKS_REQUIRED','NEW_REDACTED_RECORD_REQUIRED'} else 'OPERATION_REFUSED';self.send({'error':code},400)
        except Exception:self.send({'error':'OPERATION_REFUSED'},400)

def serve(controller,port=0):
    server=LocalServer(('127.0.0.1',port),controller);print(a.encode({'mode':'LOOPBACK_DATASET_REVIEW_UI','url':'http://127.0.0.1:'+str(server.server_port)}).decode(),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
