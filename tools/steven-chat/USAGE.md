# Steven Chat 1.0.0 — executable fictional walkthrough

This guide exercises the copied client against authored responses from a bounded
temporary HTTP fixture bound only to an ephemeral `127.0.0.1` port. It installs,
downloads or starts no Ollama or model, performs no inference and uses no real
conversation. The fixture is independent of `steven.core`, `steven.cli` and the
original test helper. It verifies requests instead of reusing client logic as
an oracle. A temporary local socket is used; this is not a no-network test.

## Prepare an owned workspace

Verify release checksums, extract the source ZIP into a fresh owned directory,
and select Python 3.12–3.15. Formal guide proof uses a fresh no-pip Python 3.15.2
environment and only the seven copied runtime files. No third-party package or
administrator access is needed. Keep the `steven` directory with its three alias
scripts; run the driver below with the module folder as its first argument.

Save the single Python block below as `fictional_steven_walkthrough.py` outside
source. Choose an existing absolute private parent outside both source and the
copied runtime; each run creates a unique child and retains its fictional files.
Use assertion-enabled Python, never `-O`. The parent must be a real owned folder,
not a symlink/junction. Example paths are invented placeholders to replace:

```powershell
$module = (Resolve-Path .).Path
$privateWork = 'D:\Private-Review'
python -I -B fictional_steven_walkthrough.py "$module" "$privateWork"
```

```sh
module="$PWD"
privateWork='/owned/private-review'
python3 -I -B fictional_steven_walkthrough.py "$module" "$privateWork"
```

Point `$module` at a separate copy containing only `main.py`, `chatbot.py`,
`stephen.py`, `steven/__init__.py`, `steven/__main__.py`, `steven/cli.py` and
`steven/core.py`; the driver checks that exact inventory. Formal verification
copies them byte-for-byte before executing this exact block. The selected Python
runs the CLI with `-E -s -B -X utf8`; the driver uses isolated `-I -B` mode.

## Read the expectations before running

Four offline demos (package plus aliases) match the complete fictional JSON.
The fixture then checks a deduplicated/filtered model listing and exact POST
bodies, including model, all selected messages, `stream: false` and `num_predict`.
Fresh session readback compares exact bytes, schema, model and complete history.
Resume preserves the input. Context pressure discards whole old pairs while
keeping the initial system message; the newest oversized exchange is refused.

Interactive clear retains the system message and only the following successful
turn; a failed turn is absent from its later retry request and checkpoint.
EOF without a successful turn makes no session file. Terminal control/bidi text
is printed as inert escapes while its session remains plaintext. Generated
code-like text is printed as data and never executed.

Refusals distinguish ordering: no `--connect`, invalid endpoint/model/options or
invalid session/prompt cause no request. HTTP errors, malformed/incomplete/oversized
responses and redirects are observed against queued fixture responses; redirect
refusal must produce no second request. An existing save or missing save parent
is refused after a valid answer has already been requested and printed. Those
cases must retain existing files, rather than pretending no request occurred.

The script stops and joins its fixture, records only fictional selected request
fields in `REQUESTS.json`, and writes `GUIDE-MANIFEST.json` with independent
SHA-256/byte counts for its thirteen payload files. It rechecks six unchanged
input files, six exact saved sessions, the request ledger, copied source and the
complete fourteen-file workspace. No model response is run as code. Assertions
fail on unexpected output, request, file, mutated source or missing refusal.

```python
"""Exercise authored demo/loopback fixtures only; no Ollama or model is installed."""
from collections import deque
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

if not __debug__:raise RuntimeError("ASSERTIONS_REQUIRED")
module=Path(sys.argv[1]).resolve(strict=True);parent=Path(sys.argv[2]).resolve(strict=True)
assert parent.is_dir() and not parent.is_relative_to(module) and not module.is_relative_to(parent)
assert not parent.is_symlink() and not getattr(parent,"is_junction",lambda:False)()
work=Path(tempfile.mkdtemp(prefix="fictional-steven-chat-",dir=parent)).resolve();assert work.parent==parent
runtime_names=("main.py","chatbot.py","stephen.py","steven/__init__.py","steven/__main__.py","steven/cli.py","steven/core.py")
def sha(raw):return hashlib.sha256(raw).hexdigest()
runtime={name:sha((module/name).read_bytes()) for name in runtime_names}
inputs=work/"inputs";outputs=work/"sessions";inputs.mkdir();outputs.mkdir()
model="fixture-local:tiny";system={"role":"system","content":"Fictional system instruction."}
history=[system,{"role":"user","content":"A"*600},{"role":"assistant","content":"B"*600},
         {"role":"user","content":"C"*500},{"role":"assistant","content":"D"*500}]
def session(messages):return dict(schema=1,model=model,messages=copy.deepcopy(messages))
def session_bytes(value):return (json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+"\n").encode()
fixtures={"context-input.json":session_bytes(session(history)),"system-input.json":session_bytes(session([system])),
          "duplicate-key.json":b'{"schema":1,"schema":1,"model":"fixture-local:tiny","messages":[]}',
          "incomplete.json":session_bytes(session([{"role":"user","content":"Incomplete fictional turn"}])),
          "invalid-utf8.json":b'\xff',"oversized.json":b' '*(1024*1024+1)}
for name,raw in fixtures.items():(inputs/name).write_bytes(raw)
input_hashes={name:sha(raw) for name,raw in fixtures.items()}
plans=deque();observations=[];fixture_errors=[];lock=threading.Lock()
def encoded(value):return json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.0"
    def log_message(self,*_args):pass
    def setup(self):
        super().setup();self.connection.settimeout(3)
    def serve(self):
        try:
            length=int(self.headers.get("Content-Length","0"));assert 0<=length<=32768
            raw=self.rfile.read(length);assert len(raw)==length
            record=dict(method=self.command,path=self.path,accept=self.headers.get("Accept"),
                        content_type=self.headers.get("Content-Type"),body_bytes=len(raw),body_sha256=sha(raw),
                        body=json.loads(raw) if raw else None)
            with lock:
                assert plans and len(observations)<64
                plan=plans.popleft();observations.append(record)
            self.send_response(plan["status"])
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(plan.get("declared_bytes",len(plan["raw"]))))
            if "location" in plan:self.send_header("Location",plan["location"])
            self.end_headers()
            self.wfile.write(plan["raw"]);self.wfile.flush()
        except (AssertionError,ValueError,OSError) as error:
            with lock:fixture_errors.append(type(error).__name__)
    do_GET=serve;do_POST=serve
class FixtureServer(ThreadingHTTPServer):
    allow_reuse_address=False
    daemon_threads=False
    block_on_close=True
    request_queue_size=4
server=FixtureServer(("127.0.0.1",0),Handler)
assert server.server_address[0]=="127.0.0.1"
thread=threading.Thread(target=server.serve_forever,kwargs={"poll_interval":0.02},daemon=True);thread.start()
endpoint="http://127.0.0.1:"+str(server.server_address[1])
outcomes=[];case_requests=[];saved={};refusals_before_http=0;refusals_after_http=0
def request(body=None):
    raw=b"" if body is None else encoded(body)
    return dict(method="GET" if body is None else "POST",path="/api/tags" if body is None else "/api/chat",
                accept="application/json",content_type="application/json",body_bytes=len(raw),body_sha256=sha(raw),body=body)
def body(messages,tokens=17):return dict(model=model,messages=copy.deepcopy(messages),stream=False,options=dict(num_predict=tokens))
def user(text):return dict(role="user",content=text)
def assistant(text):return dict(role="assistant",content=text)
def reply(text):return dict(status=200,raw=encoded(dict(done=True,message=dict(role="assistant",content=text))))
def args(prompt,*,session_path=None,save=None,tokens=17,context=16384,selected_model=model):
    value=["ask","--connect","--endpoint",endpoint,"--timeout","3","--model",selected_model,"--prompt",prompt,
           "--max-output-tokens",str(tokens),"--context-chars",str(context)]
    if session_path is not None:value += ["--session",session_path]
    if save is not None:value += ["--save",save]
    return value
def wire(text):return text.replace("\n",os.linesep).encode("utf-8")
def check(case,arguments,code,stdout,stderr="",*,requests=(),responses=(),stdin="",entry=None):
    global refusals_before_http,refusals_after_http
    before={p.relative_to(work).as_posix():sha(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    with lock:
        assert not plans
        offset=len(observations);plans.extend(responses)
    command=[sys.executable,"-E","-s","-B","-X","utf8",*([str(module/entry)] if entry else ["-m","steven"]),*map(str,arguments)]
    result=subprocess.run(command,cwd=module,input=stdin.encode(),capture_output=True,timeout=20)
    assert (result.returncode,result.stdout,result.stderr)==(code,wire(stdout),wire(stderr)),(case,result.returncode,result.stdout,result.stderr)
    with lock:
        actual=copy.deepcopy(observations[offset:]);assert not plans and not fixture_errors
    assert actual==list(requests),(case,actual,requests)
    assert before=={name:sha((work/name).read_bytes()) for name in before},case
    assert str(work).encode() not in result.stdout+result.stderr and str(module).encode() not in result.stdout+result.stderr
    outcomes.append(dict(case=case,exit_code=code));case_requests.append(dict(case=case,requests=actual))
    if code==2:
        if actual:refusals_after_http+=1
        else:refusals_before_http+=1
def readback(name,messages):
    path=outputs/name;expected=session(messages)
    assert path.is_file() and not path.is_symlink() and path.read_bytes()==session_bytes(expected)
    assert json.loads(path.read_bytes())==expected
    if os.name!="nt":assert path.stat().st_mode & 0o777==0o600
    saved[name]=dict(bytes=path.stat().st_size,sha256=sha(path.read_bytes()),messages=len(messages))
demo=dict(simulated=True,modelInferenceVerified=False,
    description="Fictional deterministic example; no model, server, session or network was opened.",
    exchange=[user("Help me organize a fictional study plan."),assistant("Demo fixture: list three topics, then choose one short study block.")])
demo_text=json.dumps(demo,indent=2)+"\n"
live_error="Error: Live commands require --connect. Use --demo for the offline example.\n"
backend_error="Error: Local backend request failed. Check its availability, installed model and timeout; redirects are refused.\n"
strict_error="Error: Response or session is not supported strict UTF-8 JSON.\n"
save_message="Saved the explicit fresh session file.\n"
banner="Steven / Stephen: local backend chat. /help, /clear, /exit. No automatic transcript saving.\n"
first=[user("First fictional question"),assistant("First fixture answer")]
second=first+[user("Second fictional question"),assistant("Second fixture answer")]
try:
    check("offline-package-demo",["--demo"],0,demo_text)
    check("offline-main-alias-demo",["--demo"],0,demo_text,entry="main.py")
    check("offline-chatbot-alias-demo",["--demo"],0,demo_text,entry="chatbot.py")
    check("offline-stephen-alias-demo",["--demo"],0,demo_text,entry="stephen.py")
    check("refuse-demo-connect-mix",["--demo","--connect"],2,"","Error: Use --demo by itself without a live command or --connect.\n")
    check("refuse-models-without-connect",["models","--endpoint",endpoint],2,"",live_error)
    check("refuse-ask-without-connect-no-save",["ask","--endpoint",endpoint,"--model",model,"--prompt","Fictional offline refusal","--save",outputs/"no-connect.json"],2,"",live_error)
    tags=dict(models=[dict(name=model),dict(name="fixture:cloud"),dict(name=model),dict(name="fixture-local:small")])
    check("fixture-model-list-deduplicates-and-filters-label",["models","--connect","--endpoint",endpoint,"--timeout","3"],0,"fixture-local:small\nfixture-local:tiny\n",
          requests=(request(),),responses=(dict(status=200,raw=encoded(tags)),))
    check("fixture-first-ask-fresh-save",args(first[0]["content"],save=outputs/"first.json"),0,first[1]["content"]+"\n",save_message,
          requests=(request(body(first[:1])),),responses=(reply(first[1]["content"]),));readback("first.json",first)
    check("fixture-resume-preserves-input-and-context",args(second[-2]["content"],session_path=outputs/"first.json",save=outputs/"second.json",tokens=19),0,second[-1]["content"]+"\n",save_message,
          requests=(request(body(second[:-1],19)),),responses=(reply(second[-1]["content"]),));readback("second.json",second)
    overwrite_prompt="Fictional overwrite refusal"
    check("fresh-save-refusal-occurs-after-fixture-reply",args(overwrite_prompt,session_path=outputs/"first.json",save=outputs/"first.json"),2,"Overwrite fixture reply\n","Error: Save target already exists; choose a new filename.\n",
          requests=(request(body(first+[user(overwrite_prompt)])),),responses=(reply("Overwrite fixture reply"),))
    check("refuse-session-model-mismatch-before-request",args("Fictional mismatch",session_path=outputs/"first.json",selected_model="other-local:tiny"),2,"","Error: Requested model differs from the session; choose the same model or start a new session.\n")
    trimmed=[system,user("Newest fictional question"),assistant("Trimmed fixture answer")]
    check("whole-old-pairs-trim-system-retained",args(trimmed[1]["content"],session_path=inputs/"context-input.json",save=outputs/"trimmed.json",context=1024),0,trimmed[2]["content"]+"\n",save_message,
          requests=(request(body(trimmed[:2])),),responses=(reply(trimmed[2]["content"]),));readback("trimmed.json",trimmed)
    chat_args=["chat","--connect","--endpoint",endpoint,"--timeout","3","--model",model,"--session",inputs/"system-input.json","--max-output-tokens","17"]
    interactive=[system,user("Second interactive question"),assistant("Second interactive answer")]
    check("interactive-clear-keeps-system-fresh-checkpoint",chat_args+["--save",outputs/"interactive.json"],0,
          banner+"You: Steven: First interactive answer\nYou: In-memory context cleared; no file was changed.\nYou: Steven: Second interactive answer\nYou: ",save_message,
          stdin="First interactive question\n/clear\nSecond interactive question\n/exit\n",
          requests=(request(body([system,user("First interactive question")])),request(body(interactive[:2]))),
          responses=(reply("First interactive answer"),reply("Second interactive answer")));readback("interactive.json",interactive)
    recovered=[system,user("Recovered fictional turn"),assistant("Recovered fixture answer")]
    check("interactive-failure-not-appended-before-retry",chat_args+["--save",outputs/"retry.json"],0,banner+"You: You: Steven: Recovered fixture answer\nYou: ",backend_error+save_message,
          stdin="Failed fictional turn\nRecovered fictional turn\n/exit\n",
          requests=(request(body([system,user("Failed fictional turn")])),request(body(recovered[:2]))),
          responses=(dict(status=500,raw=b'{"error":"fictional_private_backend_marker"}'),reply(recovered[2]["content"])));readback("retry.json",recovered)
    check("interactive-eof-without-success-does-not-save",chat_args+["--save",outputs/"eof.json"],0,banner+"You: ")
    controls="safe\x1b[31m\x00\u202e"
    check("terminal-controls-inert-session-remains-plaintext",args("Fictional terminal test",save=outputs/"terminal.json"),0,"safe\\u001b[31m\\u0000\\u202e\n",save_message,
          requests=(request(body([user("Fictional terminal test")])),),responses=(reply(controls),));readback("terminal.json",[user("Fictional terminal test"),assistant(controls)])
    code_text="__import__('pathlib').Path('FICTIONAL-CANDIDATE').write_text('never')"
    check("model-like-code-is-printed-not-executed",args("Fictional code-as-data test"),0,code_text+"\n",requests=(request(body([user("Fictional code-as-data test")])),),responses=(reply(code_text),))
    assert not (module/"FICTIONAL-CANDIDATE").exists() and not (work/"FICTIONAL-CANDIDATE").exists()
    check("http-error-body-not-disclosed-no-save",args("Fictional HTTP failure",save=outputs/"failed.json"),2,"",backend_error,
          requests=(request(body([user("Fictional HTTP failure")])),),responses=(dict(status=500,raw=b'{"error":"fictional_private_backend_marker"}'),))
    check("malformed-response-no-partial-save",args("Fictional malformed response",save=outputs/"malformed.json"),2,"",strict_error,
          requests=(request(body([user("Fictional malformed response")])),),responses=(dict(status=200,raw=b'not-json'),))
    check("incomplete-assistant-response-refused",args("Fictional incomplete response",save=outputs/"incomplete.json"),2,"","Error: Backend did not return a completed plain-text assistant response.\n",
          requests=(request(body([user("Fictional incomplete response")])),),responses=(dict(status=200,raw=encoded(dict(done=False,message=assistant("Unfinished fixture reply")))),))
    check("redirect-refused-without-second-request",args("Fictional redirect"),2,"",backend_error,
          requests=(request(body([user("Fictional redirect")])),),responses=(dict(status=302,raw=b'{}',location="/should-not-follow"),))
    check("declared-response-byte-bound-refused",args("Fictional response budget"),2,"","Error: Backend response exceeds the supported byte limit.\n",
          requests=(request(body([user("Fictional response budget")])),),responses=(dict(status=200,raw=b'',declared_bytes=1024*1024+1),))
    check("newest-oversized-exchange-not-saved",args("New",session_path=outputs/"first.json",save=outputs/"oversized-exchange.json",context=1024),2,"","Error: Newest turn and system message exceed the context limit; shorten them or start a new session.\n",
          requests=(request(body(first+[user("New")])),),responses=(reply("Z"*1025),))
    check("refuse-remote-endpoint-before-request",["models","--connect","--endpoint","http://example.invalid:11434"],2,"","Error: Endpoint must be an HTTP loopback origin using 127.0.0.1, localhost or [::1].\n")
    check("refuse-obvious-cloud-model-before-request",args("Fictional cloud-label refusal",selected_model="fixture:cloud"),2,"","Error: Cloud-labelled models are refused; choose a local model and disable backend cloud features.\n")
    check("refuse-nonfinite-timeout-before-request",["models","--connect","--endpoint",endpoint,"--timeout","nan"],2,"","Error: Timeout must be finite and between 1 and 300 seconds.\n")
    check("refuse-output-token-bound-before-request",args("Fictional token limit",tokens=4097),2,"","Error: Output token limit is outside its supported bounds.\n")
    check("refuse-context-bound-before-request",args("Fictional context limit",context=1023),2,"","Error: Context character limit is outside its supported bounds.\n")
    check("refuse-empty-prompt-before-request",args(""),2,"","Error: Prompt must contain 1-8192 characters.\n")
    check("refuse-prompt-length-before-request",args("X"*8193),2,"","Error: Prompt must contain 1-8192 characters.\n")
    check("refuse-session-duplicate-key-before-request",args("Fictional strict session",session_path=inputs/"duplicate-key.json"),2,"",strict_error)
    check("refuse-session-incomplete-turn-before-request",args("Fictional partial session",session_path=inputs/"incomplete.json"),2,"","Error: Session contains an incomplete turn.\n")
    check("refuse-session-invalid-utf8-before-request",args("Fictional encoding",session_path=inputs/"invalid-utf8.json"),2,"",strict_error)
    check("refuse-session-byte-bound-before-request",args("Fictional session budget",session_path=inputs/"oversized.json"),2,"","Error: Session must be a bounded regular UTF-8 JSON file.\n")
    check("missing-save-parent-refused-after-reply",args("Fictional missing save parent",save=work/"missing-parent/session.json"),2,"Missing-parent fixture reply\n","Error: The explicit session parent directory must already exist.\n",
          requests=(request(body([user("Fictional missing save parent")])),),responses=(reply("Missing-parent fixture reply"),))
    check("refuse-missing-session-before-request",args("Fictional missing session",session_path=inputs/"missing.json"),2,"","Error: Could not read the explicit session file.\n")
    check("refuse-directory-session-before-request",args("Fictional directory session",session_path=inputs),2,"","Error: Session must be a bounded regular UTF-8 JSON file.\n")
finally:
    server.shutdown();server.server_close();thread.join(timeout=3)
assert not thread.is_alive() and not plans and not fixture_errors
assert len(outcomes)==38 and len(observations)==18 and len(saved)==6
assert (refusals_before_http,refusals_after_http)==(17,8)
assert input_hashes=={name:sha((inputs/name).read_bytes()) for name in fixtures}
assert runtime=={name:sha((module/name).read_bytes()) for name in runtime_names}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
assert {p.relative_to(module).as_posix() for p in module.rglob("*") if p.is_file()}==set(runtime_names)
request_raw=(json.dumps(dict(schema=1,cases=case_requests),ensure_ascii=True,indent=2)+"\n").encode()
(work/"REQUESTS.json").write_bytes(request_raw)
expected_files={"inputs/"+name for name in fixtures}|{"sessions/"+name for name in saved}|{"REQUESTS.json"}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()}==expected_files
file_rows=[dict(path=name,bytes=(work/name).stat().st_size,sha256=sha((work/name).read_bytes())) for name in sorted(expected_files)]
manifest=dict(schema=1,files=file_rows)
(work/"GUIDE-MANIFEST.json").write_bytes((json.dumps(manifest,indent=2)+"\n").encode())
assert json.loads((work/"GUIDE-MANIFEST.json").read_bytes())==manifest
assert all(row["bytes"]==(work/row["path"]).stat().st_size and row["sha256"]==sha((work/row["path"]).read_bytes()) for row in file_rows)
assert len(file_rows)==13 and len(list(work.rglob("*.json")))==14 and not (work/"missing-parent").exists()
print(json.dumps(dict(outcomes=outcomes,cases=38,fixture_http_requests=18,fixture_get_requests=1,fixture_post_requests=17,
    request_cases_with_http=16,refusals_before_http=17,refusals_after_http=8,offline_demo_cases=4,session_readbacks=6,
    input_files_preserved=6,artifact_payload_hashes_checked=13,artifact_manifest_readbacks=1,expected_workspace_files=14,
    unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fixture_server_stopped=True,
    loopback_fixture_used=True,offline_demo_checked=True,actual_ollama_used=False,real_model_inference_verified=False,
    model_quality_verified=False,gpu_compatibility_verified=False,backend_cloud_isolation_verified=False,models_downloaded=False,
    ollama_servers_installed_or_started=False,real_conversations_used=False),sort_keys=True))
```

The `outcomes` field must equal the following ordered list. Exit 0 means the
specified fictional behavior completed; exit 2 is an intentional refusal. Some
interactive retries finish with exit 0 after a recorded per-turn error.

```json
[
  {
    "case": "offline-package-demo",
    "exit_code": 0
  },
  {
    "case": "offline-main-alias-demo",
    "exit_code": 0
  },
  {
    "case": "offline-chatbot-alias-demo",
    "exit_code": 0
  },
  {
    "case": "offline-stephen-alias-demo",
    "exit_code": 0
  },
  {
    "case": "refuse-demo-connect-mix",
    "exit_code": 2
  },
  {
    "case": "refuse-models-without-connect",
    "exit_code": 2
  },
  {
    "case": "refuse-ask-without-connect-no-save",
    "exit_code": 2
  },
  {
    "case": "fixture-model-list-deduplicates-and-filters-label",
    "exit_code": 0
  },
  {
    "case": "fixture-first-ask-fresh-save",
    "exit_code": 0
  },
  {
    "case": "fixture-resume-preserves-input-and-context",
    "exit_code": 0
  },
  {
    "case": "fresh-save-refusal-occurs-after-fixture-reply",
    "exit_code": 2
  },
  {
    "case": "refuse-session-model-mismatch-before-request",
    "exit_code": 2
  },
  {
    "case": "whole-old-pairs-trim-system-retained",
    "exit_code": 0
  },
  {
    "case": "interactive-clear-keeps-system-fresh-checkpoint",
    "exit_code": 0
  },
  {
    "case": "interactive-failure-not-appended-before-retry",
    "exit_code": 0
  },
  {
    "case": "interactive-eof-without-success-does-not-save",
    "exit_code": 0
  },
  {
    "case": "terminal-controls-inert-session-remains-plaintext",
    "exit_code": 0
  },
  {
    "case": "model-like-code-is-printed-not-executed",
    "exit_code": 0
  },
  {
    "case": "http-error-body-not-disclosed-no-save",
    "exit_code": 2
  },
  {
    "case": "malformed-response-no-partial-save",
    "exit_code": 2
  },
  {
    "case": "incomplete-assistant-response-refused",
    "exit_code": 2
  },
  {
    "case": "redirect-refused-without-second-request",
    "exit_code": 2
  },
  {
    "case": "declared-response-byte-bound-refused",
    "exit_code": 2
  },
  {
    "case": "newest-oversized-exchange-not-saved",
    "exit_code": 2
  },
  {
    "case": "refuse-remote-endpoint-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-obvious-cloud-model-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-nonfinite-timeout-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-output-token-bound-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-context-bound-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-prompt-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-prompt-length-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-session-duplicate-key-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-session-incomplete-turn-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-session-invalid-utf8-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-session-byte-bound-before-request",
    "exit_code": 2
  },
  {
    "case": "missing-save-parent-refused-after-reply",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-session-before-request",
    "exit_code": 2
  },
  {
    "case": "refuse-directory-session-before-request",
    "exit_code": 2
  }
]
```

## Review artifacts and limits

Expected totals are 38 cases: thirteen exit 0 and twenty-five exit 2. Eighteen
fixture requests comprise one GET and seventeen POSTs across sixteen cases.
Seventeen refusals occur before HTTP and eight after HTTP. Four offline demo
cases, six fresh session readbacks, six unchanged fixture inputs and thirteen
payload hashes are checked; the manifest makes fourteen workspace files. The
public release's accepted validation records actual guide execution separately
from archive matrix/native tests. Hashes show byte consistency, not authentic
origin, model behavior or a security verdict.

All artifacts here are fictional but sessions are still ordinary cleartext.
Do not reuse fixture contents as instructions from a model or point this driver
at real transcripts. No actual model, Ollama service, GPU, backend outbound route
or cloud-isolation property is exercised. A loopback URL and a non-cloud label
cannot establish any of those properties. The client's bounds and path checks
are not an OS sandbox, atomic stable read, hard I/O deadline or rollback guarantee.
Only fresh files are created; failed writes can leave partial new files. Windows
ACLs are inherited, and POSIX mode checks do not establish cross-platform secrecy.

For normal manual usage, review [README.md](README.md) and [SECURITY.md](SECURITY.md).
The existing [fictional session](examples/session.json) documents schema 1; its
historical example and dependency records are preserved rather than regenerated.
Real backend setup and model/license evaluation are separate, unverified work.
