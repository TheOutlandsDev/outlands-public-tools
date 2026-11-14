"""Independent copied Steven consumers and invented loopback HTTP replies; no model inference. MIT."""
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("steven/__init__.py", "steven/__main__.py", "steven/core.py", "steven/cli.py",
           "main.py", "chatbot.py", "stephen.py")
POSIX_ID = "test_download.Download.test_native_posix_special_inputs_and_private_save_mode"
POSIX_REASON = "Native POSIX special-file and private-mode fixtures"
WINDOWS_ID = "test_download.Download.test_native_windows_junction_session_routes"
WINDOWS_REASON = "Native Windows junction fixtures"
FILE_LINK_ID = "test_download.Download.test_native_session_file_symlinks"
PARENT_LINK_ID = "test_download.Download.test_native_session_parent_symlinks"
LINK_REASON = "Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS = {(POSIX_ID, POSIX_REASON)}
REQUIRED_POSIX_SKIPS = {(WINDOWS_ID, WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS = {(FILE_LINK_ID, LINK_REASON), (PARENT_LINK_ID, LINK_REASON)}
MODEL = "fixture:tiny"
NL = "\r\n" if os.name == "nt" else "\n"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def session(messages=(), model=MODEL):
    return dict(schema=1, model=model, messages=list(messages))


def message(role, content):
    return dict(role=role, content=content)


def reply(content="Fictional reply"):
    return dict(body=dict(model=MODEL, done=True, message=message("assistant", content)))


@contextmanager
def fixture(responses=()):
    """Independent, bounded temporary HTTP peer; never Ollama or model inference."""
    requests = []
    pending = list(responses)
    failures = []
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *unused):
            pass
        def handle_one(self):
            self.connection.settimeout(3)
            length = int(self.headers.get("Content-Length", "0"))
            assert 0 <= length <= 1024*1024
            body = self.rfile.read(length)
            assert len(body) == length and len(requests) < 128
            requests.append(dict(method=self.command, path=self.path, body=body, headers=dict(self.headers)))
            row = pending.pop(0) if pending else dict(status=500, body="FICTIONAL_PRIVATE_UNEXPECTED_REQUEST")
            time.sleep(row.get("delay", 0))
            if "raw_http" in row:
                self.connection.sendall(row["raw_http"])
            else:
                payload = row.get("body", b"")
                if isinstance(payload, (dict, list)):
                    payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                elif isinstance(payload, str):
                    payload = payload.encode("utf-8")
                self.send_response(row.get("status", 200))
                self.send_header("Content-Type", "application/json")
                self.send_header("Connection", "close")
                if row.get("length", True):
                    self.send_header("Content-Length", str(row.get("declared_length", len(payload))))
                for key, value in row.get("headers", {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(payload)
            self.close_connection = True
        def do_GET(self):
            try:
                self.handle_one()
            except OSError:
                self.close_connection = True
            except BaseException as error:
                failures.append(type(error).__name__)
                self.close_connection = True
        do_POST = do_GET
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = False
    thread = threading.Thread(target=server.serve_forever, kwargs=dict(poll_interval=0.01))
    thread.start()
    endpoint = "http://127.0.0.1:" + str(server.server_port)
    assert server.server_address[0] == "127.0.0.1" and server.server_port != 11434
    try:
        yield endpoint, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=4)
        assert not thread.is_alive() and not failures, failures


BOOTSTRAP = r'''
import builtins,importlib.metadata,json,os,runpy,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();entry=sys.argv[2];port=int(sys.argv[3]);mode=sys.argv[4];args=sys.argv[5:]
sys.path.insert(0,str(base))
for stream in (sys.stdin,sys.stdout,sys.stderr):stream.reconfigure(encoding='utf-8')
def audit(event,values):
 if event in ('socket.connect','socket.getaddrinfo'):
  target=values[1] if event=='socket.connect' else values[:2]
  assert port and target[0]=='127.0.0.1' and target[1]==port,'NON_FIXTURE_NETWORK_REFUSED'
 if event.startswith('subprocess.') or event in ('os.system','os.startfile','webbrowser.open'):
  raise AssertionError('UNEXPECTED_PROCESS_OR_ACTION')
sys.addaudithook(audit)
import steven,steven.cli,steven.core
assert steven.__version__=='1.0.0'
for module,name in ((steven,'__init__'),(steven.cli,'cli'),(steven.core,'core')):
 assert Path(module.__file__).resolve()==base/'steven'/(name+'.py')
assert steven.cli.Conversation is steven.core.Conversation and steven.cli.OllamaClient is steven.core.OllamaClient
assert steven.cli.load_session is steven.core.load_session and steven.cli.save_session is steven.core.save_session
assert steven.ChatError is steven.core.ChatError and steven.safe_text is steven.core.safe_text
if mode=='affinity':
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',version=steven.__version__,runtime_files=7)));raise SystemExit(0)
if mode=='ascii':sys.stdout.reconfigure(encoding='ascii',errors='strict')
elif mode=='interrupt':
 count=0
 def interrupted(prompt):
  global count
  count+=1
  if count==1:return 'Fictional interrupt question'
  raise KeyboardInterrupt
 builtins.input=interrupted
elif mode=='save_failure':
 def failed_fsync(unused):raise OSError('FICTIONAL_PRIVATE_SAVE_FAILURE')
 os.fsync=failed_fsync
elif mode!='normal':raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
sys.argv=[entry,*args]
if entry=='module':runpy.run_module('steven',run_name='__main__')
else:runpy.run_path(str(base/entry),run_name='__main__')
'''


class Download(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.python_binary = Path(sys._base_executable).resolve()
        cls.python_pin = sha(cls.python_binary.read_bytes())
        cls.python_bytes = cls.python_binary.stat().st_size
        cls.python_version = ".".join(map(str, sys.version_info[:3]))
        if cls.python_pin != os.environ["OUTLANDS_TEST_PYTHON_SHA256"] or cls.python_version != os.environ["OUTLANDS_TEST_PYTHON_VERSION"]:
            raise AssertionError("EXPECTED_PYTHON_BINARY_OR_VERSION_DIFFERS")
    @classmethod
    def tearDownClass(cls):
        if sha(cls.python_binary.read_bytes()) != cls.python_pin or cls.python_binary.stat().st_size != cls.python_bytes:
            raise AssertionError("PYTHON_BINARY_CHANGED")
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="chat-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.copy = self.work/"copied runtime"
        self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT/name).read_bytes()
            target = self.copy/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            self.pins[name] = sha(raw)
        self.env = {key:value for key,value in os.environ.items() if not key.upper().startswith(("PYTHON","PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHON_COLORS="0",NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
    def runtime_preserved(self):
        self.assertEqual({p.relative_to(self.copy).as_posix() for p in self.copy.rglob("*") if p.is_file()},set(RUNTIME))
        self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME},self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")),[])
    def snapshot(self):
        rows = {}
        def visit(folder):
            for path in folder.iterdir():
                info = path.lstat()
                key = path.relative_to(self.work).as_posix()
                if path.is_symlink() or getattr(path,"is_junction",lambda:False)():
                    rows[key] = ("LINK",os.readlink(path))
                elif stat.S_ISDIR(info.st_mode):
                    rows[key] = ("DIRECTORY",)
                    visit(path)
                elif stat.S_ISREG(info.st_mode):
                    rows[key] = (sha(path.read_bytes()),info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_ino,info.st_nlink)
                else:
                    rows[key] = ("SPECIAL",info.st_mode)
        visit(self.work)
        return rows
    def invoke(self,args=(),*,endpoint=None,stdin="",entry="module",code=0,mode="normal",allow=(),env=None):
        port = int(endpoint.rsplit(":",1)[1]) if endpoint is not None else 0
        before = self.snapshot()
        result = subprocess.run([sys.executable,"-I","-B","-W","error","-c",BOOTSTRAP,str(self.copy),entry,str(port),mode,*map(str,args)],
            cwd=self.work,env=self.env if env is None else env,input=stdin.encode("utf-8"),
            capture_output=True,timeout=20)
        self.assertEqual(result.returncode,code,result.stderr.decode("utf-8",errors="replace")[:2000])
        output = (result.stdout+result.stderr).decode("utf-8")
        self.assertNotIn("Traceback",output)
        self.assertNotIn("FICTIONAL_PRIVATE",output)
        self.assertNotIn(str(self.work),result.stderr.decode("utf-8"))
        after = self.snapshot()
        self.assertEqual(before,{key:after.get(key) for key in before})
        self.assertTrue(after.keys()-before.keys() <= {Path(p).relative_to(self.work).as_posix() for p in allow})
        self.runtime_preserved()
        return result.stdout.decode("utf-8"),result.stderr.decode("utf-8")
    def ask(self,endpoint,prompt="Fictional question",**options):
        args=["ask","--connect","--endpoint",endpoint,"--model",MODEL,"--prompt",prompt]
        args.extend(options.pop("extra",()))
        return self.invoke(args,endpoint=endpoint,**options)
    def chat(self,endpoint,stdin="",**options):
        args=["chat","--connect","--endpoint",endpoint,"--model",MODEL]
        args.extend(options.pop("extra",()))
        return self.invoke(args,endpoint=endpoint,stdin=stdin,**options)
    def previous(self,messages=(),*,name="fictional-input.json",model=MODEL,raw=None):
        path = self.work/name
        path.write_bytes(json.dumps(session(messages,model),ensure_ascii=False).encode("utf-8") if raw is None else raw)
        return path
    def saved(self,path,messages):
        raw = path.read_bytes()
        expected = session(messages)
        self.assertEqual(json.loads(raw),expected)
        self.assertEqual(raw,(json.dumps(expected,ensure_ascii=False,allow_nan=False,indent=2)+"\n").encode("utf-8"))
    def request(self,row,messages,limit=256):
        self.assertEqual((row["method"],row["path"]),("POST","/api/chat"))
        self.assertEqual(json.loads(row["body"]),dict(model=MODEL,messages=messages,stream=False,options=dict(num_predict=limit)))
        headers = {key.lower():value for key,value in row["headers"].items()}
        self.assertEqual(headers["accept"],"application/json")
        self.assertEqual(headers["content-type"],"application/json")
        self.assertNotIn("authorization",headers)
    def symlink(self,path,target,directory=False):
        try:
            path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            if os.name=="nt" and getattr(error,"winerror",None)==1314 and os.environ.get("OUTLANDS_STEVEN_REQUIRE_LINKS")!="1":
                self.skipTest(LINK_REASON)
            raise

    def test_copied_package_affinity_without_original_imports(self):
        out,err=self.invoke(mode="affinity")
        self.assertEqual(json.loads(out),dict(status="COPIED_RUNTIME_AFFINITY",version="1.0.0",runtime_files=7));self.assertEqual(err,"")
    def test_help_no_arguments_and_subcommand_help_are_offline(self):
        for args in ((),("--help",),("ask","--help"),("models","--help"),("chat","--help")):
            out,err=self.invoke(args);self.assertIn("--connect",out);self.assertEqual(err,"")
    def test_demo_and_three_legacy_entrypoints_are_deterministic_and_offline(self):
        values=[]
        for entry in ("module","main.py","chatbot.py","stephen.py"):
            out,err=self.invoke(["--demo"],entry=entry);value=json.loads(out);self.assertIs(value["simulated"],True);self.assertIs(value["modelInferenceVerified"],False);self.assertIn("Fictional",value["description"]);self.assertEqual(len(value["exchange"]),2);self.assertEqual(err,"");values.append(value)
        self.assertTrue(all(value==values[0] for value in values))
        for args in (["--demo","--connect"],["--demo","models"]):self.invoke(args,code=2)
    def test_connect_gate_precedes_requests_and_session_reads_or_saves(self):
        target=self.work/"not-created.json"
        with fixture() as (endpoint,requests):
            for command in ("ask","chat","models"):
                args=[command,"--endpoint",endpoint]
                if command!="models":args+=["--model",MODEL,"--session",self.work/"FICTIONAL_PRIVATE_MISSING.json","--save",target]
                if command=="ask":args+=["--prompt","FICTIONAL_PRIVATE_PROMPT"]
                out,err=self.invoke(args,endpoint=endpoint,code=2);self.assertEqual(out,"");self.assertIn("--connect",err)
            self.assertEqual(requests,[])
        self.assertFalse(target.exists())
    def test_tags_get_sorted_deduplicated_cloud_filtered_and_empty_list(self):
        with fixture([dict(body=dict(models=[dict(name="z:tiny"),dict(name=MODEL),dict(name=MODEL),dict(name="x:cloud")])),dict(body=dict(models=[]))]) as (endpoint,requests):
            out,err=self.invoke(["models","--connect","--endpoint",endpoint],endpoint=endpoint);self.assertEqual(out,MODEL+NL+"z:tiny"+NL);self.assertEqual(err,"")
            self.assertEqual(self.invoke(["models","--connect","--endpoint",endpoint],endpoint=endpoint),("",""));self.assertEqual([(row["method"],row["path"],row["body"]) for row in requests],[("GET","/api/tags",b""),("GET","/api/tags",b"")])
    def test_ask_posts_exact_plain_text_nonstreaming_request(self):
        with fixture([reply("Fictional answer")]) as (endpoint,requests):
            out,err=self.ask(endpoint,extra=["--max-output-tokens","17"]);self.assertEqual((out,err),("Fictional answer"+NL,""));self.assertEqual(len(requests),1);self.request(requests[0],[message("user","Fictional question")],17)
    def test_common_options_on_either_side_and_unicode_round_trip(self):
        with fixture([reply("Fictional café 🧪"),reply("Fictional café 🧪")]) as (endpoint,requests):
            for args in (["--connect","--endpoint",endpoint,"--max-output-tokens","1","ask","--model",MODEL,"--prompt","Fictional café 🧪"],["ask","--connect","--endpoint",endpoint,"--max-output-tokens","1","--model",MODEL,"--prompt","Fictional café 🧪"]):
                out,err=self.invoke(args,endpoint=endpoint);self.assertEqual((out,err),("Fictional café 🧪"+NL,""))
            for row in requests:self.request(row,[message("user","Fictional café 🧪")],1)
    def test_endpoint_grammar_and_cloud_model_refusal_precede_network(self):
        for endpoint in ("https://127.0.0.1:1","http://192.0.2.1","http://127.0.0.2","http://127.1","http://2130706433","http://127.0.0.1:0","http://127.0.0.1:65536","http://127.0.0.1:","http://user:secret@127.0.0.1","http://127.0.0.1/base","http://127.0.0.1?x","http://127.0.0.1#x","http://LOCALHOST:1","http://[::1%25lo]:1"):
            out,err=self.invoke(["models","--connect","--endpoint",endpoint],code=2);self.assertEqual(out,"");self.assertIn("loopback",err)
        with fixture() as (endpoint,requests):
            for model in ("fixture:cloud","fixture-cloud","../FICTIONAL_PRIVATE_MODEL","bad model"):
                self.invoke(["ask","--connect","--endpoint",endpoint,"--model",model,"--prompt","Fictional"],endpoint=endpoint,code=2)
            self.assertEqual(requests,[])
        with fixture([dict(body=dict(models=[]))]) as (endpoint,requests):
            self.invoke(["models","--connect","--endpoint",endpoint.replace("127.0.0.1","localhost")+"/"],endpoint=endpoint);self.assertEqual(len(requests),1)
    def test_proxy_environment_is_ignored_and_redirect_is_not_followed(self):
        with fixture() as (trap,redirected),fixture([reply(),dict(status=302,headers={"Location":trap+"/private"},body="FICTIONAL_PRIVATE_REDIRECT")]) as (endpoint,requests):
            env=dict(self.env,HTTP_PROXY=trap,HTTPS_PROXY=trap,ALL_PROXY=trap,http_proxy=trap,NO_PROXY="",no_proxy="")
            self.ask(endpoint,env=env);self.ask(endpoint,env=env,code=2);self.assertEqual(len(requests),2);self.assertEqual(redirected,[])
    def test_completion_plain_text_and_model_list_shapes_fail_safely(self):
        values=[dict(done=False,message=message("assistant","Fictional")),dict(done=True,message=message("user","Fictional")),dict(done=True,message=dict(role="assistant",content="Fictional",tool_calls=[{}])),dict(done=True,message=message("assistant"," ")),dict(error="FICTIONAL_PRIVATE_BACKEND"),[],dict(models="bad")]
        with fixture([dict(body=value) for value in values]) as (endpoint,requests):
            for index in range(len(values)):
                if index==len(values)-1:self.invoke(["models","--connect","--endpoint",endpoint],endpoint=endpoint,code=2)
                else:self.ask(endpoint,code=2)
            self.assertEqual(len(requests),len(values))
    def test_strict_json_duplicate_keys_nonfinite_utf8_and_surrogates(self):
        values=[b'{"done":true,',b'{"done":true,"done":false}',b'{"x":NaN}',b'{"x":Infinity}',b"\xff",b'{"done":true,"message":{"role":"assistant","content":"\\ud800"}}']
        with fixture([dict(body=value) for value in values]) as (endpoint,requests):
            for unused in values:self.ask(endpoint,code=2)
            self.assertEqual(len(requests),len(values))
    def test_http_errors_malformed_status_and_truncated_body_hide_upstream_data(self):
        rows=[dict(status=500,body="FICTIONAL_PRIVATE_SERVER_BODY"),dict(body=b'{}',declared_length=40),dict(raw_http=b"THIS IS NOT HTTP\r\n\r\nFICTIONAL_PRIVATE_RAW")]
        with fixture(rows) as (endpoint,requests):
            for unused in rows:self.ask(endpoint,code=2)
            self.assertEqual(len(requests),3)
    def test_http_response_byte_bounds_with_and_without_declared_length(self):
        rows=[dict(body=b"x",declared_length=1048577),dict(body=b"x"*1048577,length=False),dict(body=b"{}",declared_length="invalid")]
        with fixture(rows) as (endpoint,requests):
            for unused in rows:self.ask(endpoint,code=2)
            self.assertEqual(len(requests),3)
    def test_timeout_is_generic_and_does_not_save_a_failed_exchange(self):
        target=self.work/"not-created.json"
        with fixture([dict(**reply(),delay=1.2)]) as (endpoint,requests):
            self.ask(endpoint,extra=["--timeout","1","--save",target],code=2);self.assertEqual(len(requests),1)
        self.assertFalse(target.exists())
    def test_terminal_controls_ascii_rendering_and_shell_text_never_execute(self):
        marker=self.work/"must-never-exist.txt"
        text="\x1b[2J\r\0\u202eFictional café 🧪 python -c 'open("+repr(str(marker))+",\"w\").write(\"bad\")'"
        with fixture([reply(text),reply("Fictional café 🧪")]) as (endpoint,requests):
            out,err=self.ask(endpoint);self.assertEqual(err,"")
            for value in ("\x1b","\r","\0","\u202e"):self.assertNotIn(value,out.replace(NL,"\n"))
            self.assertIn("\\u001b",out);self.assertIn("must-never-exist.txt",out)
            out,err=self.ask(endpoint,mode="ascii");self.assertEqual(err,"");self.assertIn("caf\\xe9",out);self.assertIn("\\U0001f9ea",out)
        self.assertFalse(marker.exists())
    def test_interactive_context_sends_only_successful_complete_pairs(self):
        with fixture([reply("Fictional first"),reply("Fictional second")]) as (endpoint,requests):
            out,err=self.chat(endpoint,"Fictional one\nFictional two\n/exit\n");self.assertEqual(err,"");self.assertIn("Fictional second",out);self.assertEqual(len(requests),2)
            self.request(requests[1],[message("user","Fictional one"),message("assistant","Fictional first"),message("user","Fictional two")])
    def test_context_budget_trims_whole_pairs_and_retains_initial_system(self):
        system=message("system","Fictional system")
        old=[system,message("user","a"*300),message("assistant","b"*300),message("user","c"*300),message("assistant","d"*300)]
        previous=self.previous(old)
        target=self.work/"trimmed.json"
        with fixture([reply("Fictional reply")]) as (endpoint,requests):
            self.ask(endpoint,extra=["--session",previous,"--context-chars","1024","--save",target],allow=[target]);expected=old[:1]+old[3:]+[message("user","Fictional question")];self.request(requests[0],expected)
        self.saved(target,expected+[message("assistant","Fictional reply")])
    def test_failed_interactive_turn_does_not_commit_or_erase_previous_history(self):
        target=self.work/"recovered-turns.json"
        with fixture([reply("Fictional first"),dict(status=500,body="FICTIONAL_PRIVATE_ERROR"),reply("Fictional third")]) as (endpoint,requests):
            out,err=self.chat(endpoint,"Fictional one\nFictional failed\nFictional three\nquit\n",extra=["--save",target],allow=[target]);self.assertIn("Error:",err);self.assertIn("Saved",err);self.assertIn("Fictional third",out)
            self.request(requests[2],[message("user","Fictional one"),message("assistant","Fictional first"),message("user","Fictional three")])
        self.saved(target,[message("user","Fictional one"),message("assistant","Fictional first"),message("user","Fictional three"),message("assistant","Fictional third")])
    def test_newest_exchange_over_budget_is_rejected_without_partial_save(self):
        previous=self.previous([message("system","Fictional system")])
        target=self.work/"not-created.json"
        with fixture([reply("x"*1024)]) as (endpoint,requests):
            self.ask(endpoint,extra=["--session",previous,"--context-chars","1024","--save",target],code=2);self.assertEqual(len(requests),1)
        self.assertFalse(target.exists())
    def test_invalid_prompt_and_numeric_limits_are_refused_before_contact(self):
        with fixture() as (endpoint,requests):
            for extra in (["--timeout","nan"],["--timeout","0"],["--timeout","301"],["--max-output-tokens","0"],["--max-output-tokens","4097"],["--context-chars","1023"],["--context-chars","65537"]):
                self.ask(endpoint,extra=extra,code=2)
            for prompt in (" ","x"*8193):self.ask(endpoint,prompt=prompt,code=2)
            self.assertEqual(requests,[])
    def test_interactive_help_clear_reset_and_quit_aliases_never_contact_backend(self):
        previous=self.previous([message("system","Fictional system"),message("user","Earlier"),message("assistant","Earlier reply")])
        with fixture([reply("Fictional fresh")]) as (endpoint,requests):
            out,err=self.chat(endpoint,"/help\n/clear\n/reset\nFictional fresh\n/quit\n",extra=["--session",previous]);self.assertEqual(err,"");self.assertIn("no file was changed",out);self.request(requests[0],[message("system","Fictional system"),message("user","Fictional fresh")])
        with fixture() as (endpoint,requests):
            for text in ("/exit\n","/quit\n","exit\n","quit\n","\n/help\n"):
                self.chat(endpoint,text)
            self.assertEqual(requests,[])
    def test_normal_eof_saves_once_but_empty_eof_and_interrupt_do_not_save(self):
        target=self.work/"eof.json"
        with fixture([reply("Fictional EOF")]) as (endpoint,requests):
            self.chat(endpoint,"Fictional EOF\n",extra=["--save",target],allow=[target]);self.assertEqual(len(requests),1)
        self.saved(target,[message("user","Fictional EOF"),message("assistant","Fictional EOF")])
        empty=self.work/"empty.json"
        with fixture() as (endpoint,requests):
            self.chat(endpoint,"",extra=["--save",empty]);self.assertEqual(requests,[])
        self.assertFalse(empty.exists())
        interrupted=self.work/"interrupted.json"
        with fixture([reply()]) as (endpoint,requests):
            out,err=self.chat(endpoint,mode="interrupt",extra=["--save",interrupted],code=130);self.assertIn("Cancelled",err);self.assertEqual(len(requests),1)
        self.assertFalse(interrupted.exists())
    def test_session_resume_exact_model_match_and_fresh_save_preserve_original(self):
        history=[message("user","Fictional earlier"),message("assistant","Fictional answer")]
        previous=self.previous(history);target=self.work/"continued.json"
        with fixture([reply("Fictional continued")]) as (endpoint,requests):
            self.ask(endpoint,extra=["--session",previous,"--save",target],allow=[target]);self.request(requests[0],history+[message("user","Fictional question")])
        self.saved(target,history+[message("user","Fictional question"),message("assistant","Fictional continued")])
        mismatch=self.previous(model="other:tiny",name="mismatch.json")
        with fixture() as (endpoint,requests):
            self.ask(endpoint,extra=["--session",mismatch],code=2);self.assertEqual(requests,[])
    def test_session_schema_role_sequence_encoding_and_size_are_strict(self):
        invalid=[b'{}',b'{"schema":true,"model":"fixture:tiny","messages":[]}',b'{"schema":1,"schema":1,"model":"fixture:tiny","messages":[]}',b'{"schema":NaN}',b"\xff",b" "*1048577,
            json.dumps(session([message("user","unfinished")])).encode(),json.dumps(session([message("assistant","wrong first")])).encode(),json.dumps(session([message("user","x"),message("assistant","y"),message("system","late")])).encode(),json.dumps(session([dict(role="user",content="x",extra="FICTIONAL_PRIVATE")])).encode()]
        with fixture() as (endpoint,requests):
            for raw in invalid:
                previous=self.previous(raw=raw);self.ask(endpoint,extra=["--session",previous],code=2)
            self.assertEqual(requests,[])
    def test_fresh_save_existing_targets_missing_parents_and_partial_write_refusal(self):
        existing=self.previous(name="existing.json");missing=self.work/"missing-parent"/"new.json"
        partial=self.work/"partial.json"
        with fixture([reply(),reply(),reply(),reply(),reply()]) as (endpoint,requests):
            for target in (existing,self.work,missing):self.ask(endpoint,extra=["--save",target],code=2)
            self.ask(endpoint,extra=["--save",partial],mode="save_failure",code=2,allow=[partial]);self.assertTrue(partial.is_file());self.ask(endpoint,extra=["--save",partial],code=2);self.assertEqual(len(requests),5)
    def test_hardlink_session_aliases_keep_bytes_and_refuse_existing_save(self):
        previous=self.previous();alias=self.work/"hardlinked.json";os.link(previous,alias);self.assertTrue(alias.samefile(previous))
        with fixture([reply(),reply()]) as (endpoint,requests):
            self.ask(endpoint,extra=["--session",alias]);self.ask(endpoint,extra=["--save",alias],code=2);self.assertEqual(len(requests),2)
    def test_native_session_file_symlinks(self):
        previous=self.previous();linked=self.work/"linked.json";self.symlink(linked,previous)
        with fixture([reply()]) as (endpoint,requests):
            self.ask(endpoint,extra=["--session",linked],code=2);self.assertEqual(requests,[])
            self.ask(endpoint,extra=["--save",linked],code=2);self.assertEqual(len(requests),1)
    def test_native_session_parent_symlinks(self):
        previous=self.previous();linked=self.work/"linked-parent";self.symlink(linked,self.work,directory=True)
        with fixture([reply()]) as (endpoint,requests):
            self.ask(endpoint,extra=["--session",linked/previous.name],code=2);self.assertEqual(requests,[])
            self.ask(endpoint,extra=["--save",linked/"not-created.json"],code=2);self.assertEqual(len(requests),1)
    @unittest.skipUnless(os.name=="nt",WINDOWS_REASON)
    def test_native_windows_junction_session_routes(self):
        previous=self.previous();linked=self.work/"junction"
        done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(linked),str(self.work)],capture_output=True,timeout=10)
        self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:linked.rmdir() if linked.exists() else None)
        with fixture([reply()]) as (endpoint,requests):
            self.ask(endpoint,extra=["--session",linked/previous.name],code=2);self.assertEqual(requests,[])
            self.ask(endpoint,extra=["--save",linked/"not-created.json"],code=2);self.assertEqual(len(requests),1)
    @unittest.skipUnless(os.name!="nt",POSIX_REASON)
    def test_native_posix_special_inputs_and_private_save_mode(self):
        fifo=self.work/"fictional.fifo";os.mkfifo(fifo)
        sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.work/"fictional.sock"));self.addCleanup(sock.close)
        target=self.work/"private.json"
        with fixture([reply()]) as (endpoint,requests):
            for path in (fifo,self.work/"fictional.sock"):self.ask(endpoint,extra=["--session",path],code=2)
            self.assertEqual(requests,[]);self.ask(endpoint,extra=["--save",target],allow=[target]);self.assertEqual(len(requests),1)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode)&0o077,0)


if __name__ == "__main__":
    unittest.main()
