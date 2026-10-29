"""HTTP coherence, pinned reports, strict framing and actual server lifecycle."""
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import test_workbench as original
from operations_analytics import application as app,runtime,web

class BrowserBoundary(original.Fixture):
    def setUp(self):
        super().setUp();self.load();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(5)
    def request(self,path,method='GET',value=None,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            con.request(method,path,body=runtime.encode(value) if value is not None else None,headers=headers or {'X-Outlands-Token':web.TOKEN});res=con.getresponse();return res.status,res.read(),dict(res.getheaders())
        finally:con.close()
    def test_coherent_view_matches_revision_plan_and_history(self):
        status,raw,_=self.request('/api/view?project=sample-operations');value=json.loads(raw);self.assertEqual(status,200);self.assertEqual(value['snapshot']['revision_sha256'],value['plan']['revision_sha256']);self.assertEqual(value['history']['revisions'][-1]['revision_sha256'],value['plan']['revision_sha256'])
    def test_export_requires_current_pin_and_never_writes_on_refusal(self):
        before=list((self.root/'reports').iterdir())
        for body in ({'project_id':'sample-operations'},{'project_id':'sample-operations','expected':'0'*64}):self.assertEqual(self.request('/api/export','POST',body)[0],400)
        self.assertEqual(before,list((self.root/'reports').iterdir()));head=app.show('sample-operations')['revision_sha256'];self.assertEqual(self.request('/api/export','POST',dict(project_id='sample-operations',expected=head))[0],200)
    def test_duplicate_query_fields_and_unknown_arguments_refused(self):
        for path in ('/api/view?project=sample-operations&project=sample-operations','/api/view?project=sample-operations&unknown=fictional','/api/projects?project=sample-operations'):
            self.assertEqual(self.request(path)[0],400)
    def test_present_non_json_body_type_and_post_query_refused(self):
        self.assertEqual(self.request('/api/backup','POST',{},dict(**{'X-Outlands-Token':web.TOKEN,'Content-Type':'text/plain'}))[0],400);self.assertEqual(self.request('/api/backup?ignored=1','POST',{})[0],400);self.assertEqual(list((self.root/'backups').iterdir()),[])
    def wire(self,lines):
        con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            con.putrequest('POST','/api/backup',skip_host=True);con.putheader('Host','127.0.0.1:'+str(self.server.server_port));con.putheader('X-Outlands-Token',web.TOKEN)
            for key,value in lines:con.putheader(key,value)
            con.endheaders(b'{}');res=con.getresponse();return res.status,res.read()
        finally:con.close()
    def test_duplicate_length_and_transfer_encoding_refused(self):
        self.assertEqual(self.wire([('Content-Length','2'),('Content-Length','2')])[0],400);self.assertEqual(self.wire([('Content-Length','2'),('Transfer-Encoding','chunked')])[0],400)
    def test_duplicate_host_token_origin_refused(self):
        for key,value in [('Host','127.0.0.1:'+str(self.server.server_port)),('X-Outlands-Token',web.TOKEN)]:self.assertEqual(self.wire([('Content-Length','2'),(key,value)])[0],403)
        self.assertEqual(self.wire([('Content-Length','2'),('Origin','http://127.0.0.1:'+str(self.server.server_port)),('Origin','http://127.0.0.1:'+str(self.server.server_port))])[0],403)
    def test_nonce_policy_matches_only_script_and_blocks_external_connections(self):
        status,raw,headers=self.request('/');self.assertEqual(status,200);nonce=re.search(rb'<script nonce="([^"]+)"',raw).group(1).decode();self.assertIn("script-src 'nonce-"+nonce+"'",headers['Content-Security-Policy']);self.assertIn("connect-src 'self'",headers['Content-Security-Policy']);self.assertNotIn("script-src 'self' 'unsafe-inline'",headers['Content-Security-Policy'])
    def test_full_http_operations_are_serialized(self):
        entered=threading.Event();release=threading.Event();second=threading.Event();real=app.show;outputs=[]
        def held(*args):entered.set();self.assertTrue(release.wait(5));return real(*args)
        def call(path,event=None):
            if event:event.set()
            outputs.append(self.request(path)[0])
        with patch.object(app,'show',side_effect=held):
            first=threading.Thread(target=call,args=('/api/view?project=sample-operations',));first.start();self.assertTrue(entered.wait(5));later=threading.Thread(target=call,args=('/api/projects',second));later.start();self.assertTrue(second.wait(5));time.sleep(.05);self.assertEqual(outputs,[]);release.set();first.join(5);later.join(5)
        self.assertEqual(outputs,[200,200])

class ServerProcess(unittest.TestCase):
    def test_actual_serve_shutdown_releases_lock_and_reopens(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as temporary:
            root=Path(temporary)/'instance';cli=Path(__file__).resolve().parents[1]/'workbench.py';cmd=[sys.executable,'-B',str(cli),'--workspace',str(root)]
            subprocess.run(cmd+['demo'],check=True,capture_output=True,timeout=30)
            process=subprocess.Popen(cmd+['serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
            try:
                url=json.loads(process.stdout.readline())['url'];port=int(url.rsplit(':',1)[1]);con=http.client.HTTPConnection('127.0.0.1',port,timeout=5);con.request('GET','/');response=con.getresponse();html=response.read();con.close();token=re.search(rb"const token='([^']+)'",html).group(1).decode();con=http.client.HTTPConnection('127.0.0.1',port,timeout=5);con.request('POST','/api/shutdown',body=b'{}',headers={'X-Outlands-Token':token,'Content-Type':'application/json','Origin':url});response=con.getresponse();self.assertEqual(response.status,200);response.read();con.close();output,error=process.communicate(timeout=15);self.assertEqual(process.returncode,0);self.assertEqual(error,'');self.assertFalse((root/'.session-lock').exists());self.assertEqual(subprocess.run(cmd+['list'],capture_output=True,timeout=15).returncode,0)
            finally:
                if process.poll() is None:process.kill();process.communicate(timeout=10)

if __name__=='__main__':unittest.main()

class NativeJunction(original.Fixture):
    @unittest.skipUnless(os.name=='nt','Windows-only junction')
    def test_native_junction_input_parent_refused(self):
        target=self.root/'inbox/fictional-junction';source=self.root/'inbox';result=subprocess.run(['cmd','/d','/c','mklink','/J',str(target),str(source)],capture_output=True,timeout=10)
        if result.returncode:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native junction fixture required')
            self.skipTest('Native junction fixture unavailable on this filesystem')
        self.addCleanup(lambda:os.rmdir(target))
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(target/'sample-scenario.json')
