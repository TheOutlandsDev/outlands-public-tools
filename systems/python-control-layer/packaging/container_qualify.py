"""Exercise the supplied Compose file from a fresh source archive on Linux."""
import argparse,hashlib,json,os,subprocess,sys,time,urllib.error,urllib.request,uuid,zipfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('packages','workspace','report'):p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();assert sys.platform=='linux' and not a.workspace.exists() and a.workspace.parent.is_dir() and not a.report.exists()
    build=json.loads((a.packages/'build-manifest.json').read_bytes());archive=a.packages/build['filename']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==build['sha256'] and archive.stat().st_size==build['bytes']
    a.workspace.mkdir();prefix='python-control-layer-0.1.0/'
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();assert len(names)==len(set(names))==build['files'] and z.testzip() is None
        assert all(n.startswith(prefix) and '..' not in n.split('/') and '\\' not in n and ':' not in n for n in names)
        z.extractall(a.workspace)
    source=(a.workspace/prefix).resolve();manifest=json.loads((source/'SOURCE-MANIFEST.json').read_bytes())
    assert len(manifest['files'])+1==len(names)
    for row in manifest['files']:assert hashlib.sha256((source/row['path']).read_bytes()).hexdigest()==row['sha256']
    project='control-validation-'+uuid.uuid4().hex[:12]
    env=dict(os.environ,APP_ENVIRONMENT='fictional-validation',APP_VERSION='0.1.0',LOG_LEVEL='INFO',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    base=['docker','compose','-p',project,'-f',str(source/'compose.yaml')]
    def command(args):
        r=subprocess.run(args,cwd=source,env=env,capture_output=True,timeout=900)
        with (a.workspace/'docker-private.log').open('ab') as f:f.write(r.stdout+r.stderr)
        assert r.returncode==0,'OWNED_CONTAINER_COMMAND_FAILED'
        return r.stdout.decode('utf-8')
    requests=[]
    try:
        version=command(['docker','version','--format','{{.Server.Version}}']).strip()
        compose_version=command(['docker','compose','version','--short']).strip()
        command(base+['build','--pull','control-api','tests'])
        output=command(base+['--profile','test','run','--rm','--no-deps','-T','-e','PYTEST_DISABLE_PLUGIN_AUTOLOAD=1','tests','python','-B','packaging/container_tests.py'])
        receipts=[]
        for line in output.splitlines():
            try:value=json.loads(line)
            except json.JSONDecodeError:continue
            if 'container_test_receipt' in value:receipts.append(value['container_test_receipt'])
        assert len(receipts)==1 and receipts[0]['status']=='PASS'
        command(base+['up','-d','--wait','--wait-timeout','60','control-api'])
        identifier=command(base+['ps','-q','control-api']).strip();assert identifier and '\n' not in identifier
        inspect=json.loads(command(['docker','inspect',identifier]))[0]
        assert inspect['Config']['User']=='10001:10001' and inspect['HostConfig']['ReadonlyRootfs'] is True
        bindings=inspect['NetworkSettings']['Ports']['8000/tcp'];assert bindings==[dict(HostIp='127.0.0.1',HostPort='8000')]
        assert inspect['State']['Health']['Status']=='healthy'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for method,path,status,body in [('GET','/health/live',200,{'status':'alive'}),('GET','/health/ready',200,{'status':'ready'}),('GET','/fictional-missing',404,{'detail':'Not Found'}),('POST','/health/ready',405,{'detail':'Method Not Allowed'})]:
            request=urllib.request.Request('http://127.0.0.1:8000'+path,method=method)
            try:response=opener.open(request,timeout=3)
            except urllib.error.HTTPError as error:response=error
            with response:assert response.status==status and json.load(response)==body
            requests.append(dict(method=method,path=path,status=status))
        command(base+['stop','-t','15','control-api'])
        stopped=json.loads(command(['docker','inspect',identifier]))[0]
        assert stopped['State']['Running'] is False and stopped['State']['ExitCode']==0
        logs=command(base+['logs','--no-color','control-api'])
        assert logs.count('application_started')==logs.count('application_stopped')==1
        value=dict(schema=1,status='PASS',package='python-control-layer',profile='Ubuntu-Docker-Compose',source_revision=build['source_revision'],zip_sha256=build['sha256'],zip_bytes=build['bytes'],source_files=len(manifest['files']),archive_members=len(names),docker_version=version,compose_version=compose_version,base_image='python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df',tests=receipts[0],actual_tcp_http=True,requests=requests,compose_healthcheck_healthy=True,runtime_user='10001:10001',runtime_read_only=True,published_on_loopback_only=True,graceful_shutdown=True,owned_container_exit_code=0,actual_database_operations_verified=False,external_dependency_readiness_verified=False,raw_logs_included=False)
    finally:
        command(base+['--profile','test','down','--remove-orphans'])
    a.report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(value))
if __name__=='__main__':main()
