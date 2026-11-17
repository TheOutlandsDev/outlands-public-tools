"""Real loopback HTTP and graceful shutdown of one owned child process."""
import argparse,json,os,subprocess,sys,time,urllib.error,urllib.request
from pathlib import Path

CHILD=r'''
import json,pathlib,socket,sys,threading,time
import uvicorn
root=pathlib.Path(sys.argv[1]);sock=socket.socket();sock.bind(('127.0.0.1',0))
server=uvicorn.Server(uvicorn.Config('app.main:app',host='127.0.0.1',port=0,proxy_headers=False,access_log=False))
def watch():
 while not (root/'stop').exists():time.sleep(.05)
 server.should_exit=True
threading.Thread(target=watch,daemon=True).start()
temp=root/'port.tmp';temp.write_text(json.dumps({'port':sock.getsockname()[1]}));temp.replace(root/'port.json')
server.run(sockets=[sock])
'''

def exercise(workspace):
    workspace=workspace.resolve();assert not workspace.exists() and workspace.parent.is_dir()
    workspace.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
    for name in ('APP_NAME','APP_ENVIRONMENT','APP_VERSION','LOG_LEVEL','CONTROL_DB_URL','DATA_ROOT','MANIFEST_ROOT','STAGING_ROOT','RESULTS_ROOT'):env.pop(name,None)
    env.update(APP_ENVIRONMENT='fictional-validation',LOG_LEVEL='INFO',CONTROL_DB_URL='unsupported://fictional')
    for name in ('DATA_ROOT','MANIFEST_ROOT','STAGING_ROOT','RESULTS_ROOT'):env[name]=str(workspace/name.lower())
    rawlog=workspace/'server-private.log'
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    with rawlog.open('xb') as log:
        child=subprocess.Popen([sys.executable,'-I','-B','-c',CHILD,str(workspace)],cwd=workspace,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
        observed=[];started=time.monotonic()
        try:
            while not (workspace/'port.json').exists():
                assert child.poll() is None and time.monotonic()-started<30,'OWNED_SERVER_NOT_STARTED'
                time.sleep(.05)
            port=json.loads((workspace/'port.json').read_text())['port'];assert type(port) is int and 0<port<65536
            origin='http://127.0.0.1:'+str(port)
            while True:
                try:
                    with opener.open(origin+'/health/live',timeout=1) as response:
                        assert response.status==200 and json.load(response)=={'status':'alive'}
                    break
                except (urllib.error.URLError,TimeoutError):
                    assert child.poll() is None and time.monotonic()-started<30,'OWNED_SERVER_NOT_READY'
                    time.sleep(.05)
            for method,path,status,body in [('GET','/health/live',200,{'status':'alive'}),('GET','/health/ready',200,{'status':'ready'}),('GET','/fictional-missing',404,{'detail':'Not Found'}),('POST','/health/ready',405,{'detail':'Method Not Allowed'})]:
                request=urllib.request.Request(origin+path,method=method)
                try:response=opener.open(request,timeout=3)
                except urllib.error.HTTPError as error:response=error
                with response:
                    assert response.status==status and json.load(response)==body
                    assert response.headers.get_content_type()=='application/json'
                observed.append(dict(method=method,path=path,status=status))
            (workspace/'stop').write_text('owned shutdown\n',encoding='ascii')
            assert child.wait(timeout=15)==0,'OWNED_SERVER_SHUTDOWN_FAILED'
        finally:
            if child.poll() is None:
                if not (workspace/'stop').exists():(workspace/'stop').write_text('owned cleanup\n',encoding='ascii')
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=5)
    text=rawlog.read_text(encoding='utf-8',errors='replace')
    assert text.count('application_started')==text.count('application_stopped')==1
    assert all(not (workspace/name.lower()).exists() for name in ('DATA_ROOT','MANIFEST_ROOT','STAGING_ROOT','RESULTS_ROOT'))
    return dict(status='PASS',profile='owned-loopback-Uvicorn-child',actual_tcp_http=True,bind='127.0.0.1',requests=observed,graceful_shutdown=True,owned_child_exit_code=0,external_dependency_readiness_verified=False,storage_directories_created=False,actual_database_operations_verified=False,raw_logs_included=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    assert not args.report.exists();value=exercise(args.workspace)
    args.report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(value))
