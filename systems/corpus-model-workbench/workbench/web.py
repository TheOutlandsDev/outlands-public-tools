"""Loopback-only UI. Mutations require a session token and same-origin requests."""
import json
import secrets
import threading
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from . import corpus
from . import models
from . import runtime

TOKEN=secrets.token_urlsafe(32)
JOBS={};LOCK=threading.Lock()
def launch_job(action):
    identifier=uuid.uuid4().hex
    with LOCK:
        if any(job['status']=='running' for job in JOBS.values()): raise ValueError('JOB_BUSY')
        while len(JOBS)>=32:JOBS.pop(next(iter(JOBS)))
        JOBS[identifier]=dict(status='running')
    def run():
        try:
            result=action()
            with LOCK: JOBS[identifier]=dict(status='complete',result=result)
        except Exception as error:
            with LOCK: JOBS[identifier]=dict(status='error',error='OPERATION_FAILED')
    threading.Thread(target=run,daemon=True).start()
    return dict(job_id=identifier,status='running')
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def allowed_host(self): return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def send(self,value,status=200,content_type='application/json'):
        payload=value.encode('utf-8') if isinstance(value,str) else corpus.encode(value).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type',content_type+'; charset=utf-8')
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        if not self.allowed_host(): self.send(dict(error='Invalid Host header'),403);return
        parsed=urlparse(self.path);query=parse_qs(parsed.query)
        if parsed.path.startswith('/api/') and self.headers.get('X-Outlands-Token')!=TOKEN:
            self.send(dict(error='Session token required'),403);return
        def item(key,default=''): return query.get(key,[default])[0]
        try:
            if parsed.path=='/':
                page=(corpus.APP/'ui.html').read_text(encoding='utf-8').replace('__SESSION_TOKEN__',TOKEN)
                if getattr(runtime._client,'fictional_demo',False):
                    page=page.replace('<body>','<body><p role="status">FICTIONAL MODEL DEMONSTRATION: no real inference or code execution.</p>')
                self.send(page,content_type='text/html')
            elif parsed.path=='/api/status': self.send(corpus.status())
            elif parsed.path=='/api/records': self.send(corpus.list_records(item('q'),item('domain'),item('kind'),item('status'),item('split'),int(item('limit','25')),int(item('offset','0'))))
            elif parsed.path=='/api/record': self.send(corpus.get_record(item('id')))
            elif parsed.path=='/api/model-overview': self.send(models.overview())
            elif parsed.path=='/api/discussion': self.send(models.get_discussion(item('id')))
            elif parsed.path=='/api/job':
                with LOCK: result=JOBS.get(item('id'),dict(status='unknown'))
                self.send(result)
            else: self.send(dict(error='Not found'),404)
        except Exception as error: self.send(dict(error='OPERATION_FAILED'),400)
    def do_POST(self):
        if not self.allowed_host() or self.headers.get('X-Outlands-Token')!=TOKEN:
            self.send(dict(error='Session token required'),403);return
        origin=self.headers.get('Origin')
        if origin and origin not in {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}:
            self.send(dict(error='Cross-origin request refused'),403);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=1024*1024: raise ValueError('Invalid request size')
            data=runtime.decode(self.rfile.read(length));path=urlparse(self.path).path
            if path=='/api/review': result=corpus.review_record(data['id'],data['decision'],data['actor'],data['note'],data['checks'])
            elif path=='/api/materialize': result=corpus.materialize(data['id'])
            elif path=='/api/export': result=launch_job(lambda:corpus.export_dataset(data['kind'],data.get('domain','')))
            elif path=='/api/backup': result=launch_job(corpus.backup)
            elif path=='/api/discover': result=launch_job(lambda:models.discover(data.get('url')))
            elif path=='/api/benchmark': result=launch_job(lambda:models.benchmark(data['models'],data.get('language',''),int(data.get('limit',0)),data.get('url')))
            elif path=='/api/discuss': result=launch_job(lambda:models.discuss(data['task'],data['planner'],data['coder'],data['reviewer'],int(data.get('rounds',2)),data.get('url')))
            elif path=='/api/score': result=models.score(data['id'],data['score'],data['actor'],data['note'])
            elif path=='/api/queue-discussion': result=models.queue_discussion(data['id'])
            elif path=='/api/embed': result=launch_job(lambda:corpus.embed_corpus(data['model'],data.get('url')))
            elif path=='/api/shutdown':
                with LOCK:
                    if any(job['status']=='running' for job in JOBS.values()): raise ValueError('A job is still running; wait for it to finish before stopping the UI.')
                result=dict(status='stopping')
                threading.Thread(target=self.server.shutdown,daemon=True).start()
            else: self.send(dict(error='Not found'),404);return
            self.send(result)
        except Exception as error: self.send(dict(error='OPERATION_FAILED'),400)
def serve(port=8765):
    server=ThreadingHTTPServer(('127.0.0.1',int(port)),Handler)
    print(corpus.encode(dict(mode='LOOPBACK_CORPUS_UI',url=f'http://127.0.0.1:{server.server_port}')),flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
