"""Copied CLI and native primitives on owned fictional profiles only; no game or GUI acceptance. MIT."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("profile_manager.py","profile_engine.py","profile_fs.py","profile_gui.py",
           "inspection_support.py","examples/generate.py")
WINDOWS_ID = "test_download.Download.test_native_windows_streams_and_junction_routes"
WINDOWS_REASON = "Native Windows named-stream and junction fixtures"
POSIX_ID = "test_download.Download.test_native_posix_special_objects_and_case_collisions"
POSIX_REASON = "Native POSIX special-object and case-collision fixtures"
DIR_LINK_ID = "test_download.Download.test_native_symlink_source_and_linked_parent_routes"
FILE_LINK_ID = "test_download.Download.test_native_symlink_payload_and_workspace_routes"
LINK_REASON = "Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS = {(POSIX_ID,POSIX_REASON)}
REQUIRED_POSIX_SKIPS = {(WINDOWS_ID,WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS = {(DIR_LINK_ID,LINK_REASON),(FILE_LINK_ID,LINK_REASON)}
NL = b"\r\n" if os.name=="nt" else b"\n"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


CHILD = r'''
import builtins,ctypes,errno,importlib.metadata,importlib.util,json,os,runpy,sys
from pathlib import Path
from types import SimpleNamespace
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();root=Path(sys.argv[2]).resolve();mode=sys.argv[3];args=sys.argv[4:]
assert base.is_relative_to(root) and base!=root
sys.path.insert(0,str(base))
def owned(value):
 path=Path(value)
 assert path.is_absolute() and path.resolve().is_relative_to(root) and not path.resolve().is_relative_to(base),'UNOWNED_PROBE_PATH'
 return path
def audit(event,values):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open'):
  raise AssertionError('UNEXPECTED_NETWORK_OR_PROGRAM_ACTION')
sys.addaudithook(audit)
original_import=builtins.__import__
def guarded(name,*a,**kw):
 assert name.split('.')[0]!='tkinter','TK_NOT_PART_OF_CLI_PROOF'
 if mode=='help':assert name not in {'profile_engine','profile_gui'},'HELP_IMPORTED_APPLICATION_ENGINE'
 return original_import(name,*a,**kw)
builtins.__import__=guarded
import profile_manager as p
assert Path(p.__file__).resolve()==base/'profile_manager.py'
if mode=='help':
 sys.argv=[str(base/'profile_manager.py'),*args];raise SystemExit(p.main(args))
import profile_engine as e
import profile_fs as fs
import inspection_support as support
assert Path(e.__file__).resolve()==base/'profile_engine.py' and Path(fs.__file__).resolve()==base/'profile_fs.py'
assert Path(support.__file__).resolve()==base/'inspection_support.py' and e.fs is fs and e.ProfileError is fs.ProfileError
assert all(getattr(fs,name) is getattr(support,name) for name in ('canonical_directory','identity','linked','local_path','no_links','strict_json'))
if mode=='affinity':
 import profile_gui as gui
 assert Path(gui.__file__).resolve()==base/'profile_gui.py'
 spec=importlib.util.spec_from_file_location('copied_generator',base/'examples/generate.py')
 g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
 assert g.canonical_directory is support.canonical_directory and g.no_links is support.no_links
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=6,native_tk_widgets_checked=False),sort_keys=True));raise SystemExit(0)
if mode=='generate':
 owned(args[args.index('--output')+1])
 sys.argv=[str(base/'examples/generate.py'),*args];runpy.run_path(sys.argv[0],run_name='__main__');raise SystemExit(0)
if mode=='hold':
 workspace=owned(args[0]);ready=owned(args[1])
 with fs.lock_workspace(workspace):
  with ready.open('xb') as out:out.write(b'LOCKED')
  sys.stdin.buffer.read(1)
 raise SystemExit(0)
if mode in ('rename','rename-race'):
 source,destination=map(owned,args);assert source.is_dir() and not destination.exists()
 if mode=='rename-race':
  if os.name=='nt':
   original=fs.os.rename
   def raced(left,right):destination.mkdir();return original(left,right)
   fs.os.rename=raced
  else:
   native=getattr(fs.ctypes.CDLL(None,use_errno=True),'renameat2',None);assert native is not None,'NATIVE_NOREPLACE_REQUIRED'
   native.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];native.restype=ctypes.c_int
   def raced(*values):destination.mkdir();return native(*values)
   fs.ctypes.CDLL=lambda *a,**kw:SimpleNamespace(renameat2=raced)
  try:fs.rename_no_replace(source,destination)
  except (fs.ProfileError,OSError):pass
  else:raise AssertionError('NATIVE_RACE_OVERWROTE_DESTINATION')
  assert source.is_dir() and destination.is_dir() and not list(destination.iterdir())
  print(json.dumps(dict(status='NATIVE_RENAME_RACE_REFUSED'),sort_keys=True))
 else:
  fs.rename_no_replace(source,destination)
  try:fs.rename_no_replace(destination,owned(args[0]))
  except (fs.ProfileError,OSError):raise AssertionError('NATIVE_NEW_DESTINATION_REFUSED')
  assert source.is_dir() and not destination.exists()
  destination.mkdir()
  try:fs.rename_no_replace(source,destination)
  except fs.ProfileError as error:assert str(error)=='DESTINATION_EXISTS'
  else:raise AssertionError('EXISTING_DIRECTORY_REPLACED')
  print(json.dumps(dict(status='NATIVE_RENAME_NEW_ONLY'),sort_keys=True))
 raise SystemExit(0)
workspace=None
if '--workspace' in args:
 selected=Path(args[args.index('--workspace')+1])
 workspace=owned(selected if selected.is_absolute() else root/selected)
if mode.startswith('interrupt:'):
 phase=mode.split(':',1)[1];original=e.activate
 def interrupted(workspace,profile):
  def fault(observed):
   if observed==phase:raise KeyboardInterrupt
  return original(workspace,profile,fault_hook=fault)
 e.activate=interrupted
elif mode in ('partial-import','partial-activation','unexpected-stage'):
 if mode=='partial-import':
  original=fs.write_new;used=False
  def partial(path,data,*a,**kw):
   global used
   path=owned(path)
   if not used and path.is_relative_to(workspace/'operations') and 'payload' in path.parts:
    used=True;original(path,data[:max(1,len(data)//2)],*a,**kw);raise KeyboardInterrupt
   return original(path,data,*a,**kw)
  fs.write_new=partial
 else:
  original=e.activate
  def interrupted(workspace_value,profile):
   def fault(phase):
    if phase=='after_intent_written':
     state=fs.read_json(workspace/'state.json');stage=owned(workspace/'operations'/state['pending']/'stage')
     fs.fresh_directory(stage)
     if mode=='unexpected-stage':fs.write_new(stage/'unexpected.txt',b'fictional held data')
     else:
      source=owned(workspace/'profiles'/profile/'payload'/'README.txt')
      data=source.read_bytes();fs.write_new(stage/'README.txt',data[:max(1,len(data)//2)])
     raise KeyboardInterrupt
   return original(workspace_value,profile,fault_hook=fault)
  e.activate=interrupted
elif mode.startswith('limit:'):
 for name,value in json.loads(mode[6:]).items():
  assert name in {'MAX_FILES','MAX_DIRECTORIES','MAX_FILE_BYTES','MAX_TOTAL_BYTES','MAX_PATH','MAX_PROFILES','MAX_OPERATIONS','MAX_JSON'}
  if hasattr(fs,name):setattr(fs,name,value)
  if hasattr(e,name):setattr(e,name,value)
elif mode=='short-source-read':
 source=owned(args[args.index('--source')+1])/'README.txt';identity=source.stat();original=os.read
 def short(fd,length):
  info=os.fstat(fd)
  return b'' if (info.st_dev,info.st_ino)==(identity.st_dev,identity.st_ino) else original(fd,length)
 os.read=short
elif mode!='normal':raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
raise SystemExit(p.main(args))
'''


class Download(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.python_binary=Path(sys._base_executable).resolve()
        cls.python_pin=sha(cls.python_binary.read_bytes());cls.python_bytes=cls.python_binary.stat().st_size
        cls.python_version=".".join(map(str,sys.version_info[:3]))
        if cls.python_pin!=os.environ["OUTLANDS_TEST_PYTHON_SHA256"] or cls.python_version!=os.environ["OUTLANDS_TEST_PYTHON_VERSION"]:
            raise AssertionError("EXPECTED_PYTHON_BINARY_OR_VERSION_DIFFERS")
    @classmethod
    def tearDownClass(cls):
        if sha(cls.python_binary.read_bytes())!=cls.python_pin or cls.python_binary.stat().st_size!=cls.python_bytes:
            raise AssertionError("PYTHON_BINARY_CHANGED")
    def setUp(self):
        self.assertNotEqual(sys.prefix,sys.base_prefix);self.assertEqual(list(importlib.metadata.distributions()),[])
        parent=Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp=tempfile.TemporaryDirectory(prefix="profile-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();target=self.copy/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);self.pins[name]=sha(raw)
        self.sources=self.work/"fictional sources";self.workspace=self.work/"workspace"
        for name,color in (("orchard","orange"),("meadow","green")):
            self.write(self.sources/name/"README.txt",b"FICTIONAL_PRIVATE_CONTENT: inert authored fixture only\n")
            self.write(self.sources/name/"config/demo.ini",("[fictional]\ncolor="+color+"\n").encode())
        self.env={key:value for key,value in os.environ.items() if not key.upper().startswith(("PYTHON","PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHON_COLORS="0",NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
    def owned(self,path):
        path=Path(path);self.assertTrue(path.is_absolute() and path.resolve().is_relative_to(self.work) and not path.resolve().is_relative_to(self.copy));return path
    def write(self,path,raw):
        path=self.owned(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    def runtime_preserved(self):
        self.assertEqual({p.relative_to(self.copy).as_posix() for p in self.copy.rglob("*") if p.is_file()},set(RUNTIME))
        self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME},self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")),[])
    def tree(self,root):
        rows={}
        if not root.exists():return rows
        def visit(folder):
            for path in folder.iterdir():
                key=path.relative_to(root).as_posix();info=path.lstat()
                if path.is_symlink() or getattr(path,"is_junction",lambda:False)():rows[key]=("LINK",os.readlink(path))
                elif stat.S_ISDIR(info.st_mode):rows[key]=("DIRECTORY",);visit(path)
                elif stat.S_ISREG(info.st_mode):
                    digest="OWNED_LOCKED_BYTE_RANGE" if path==getattr(self,"locked_path",None) else sha(path.read_bytes())
                    rows[key]=(digest,info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_ino,info.st_nlink)
                else:rows[key]=("SPECIAL",info.st_mode)
        visit(root);return rows
    def catalog(self,root):
        return {name:row[:2] for name,row in self.tree(root).items()}
    def invoke(self,args=(),*,mode="normal",code=0,error=None,mutable=(),text=False):
        before=self.tree(self.work)
        result=subprocess.run([sys.executable,"-I","-B","-W","error","-c",CHILD,str(self.copy),str(self.work),mode,*map(str,args)],
            cwd=self.work,env=self.env,stdin=subprocess.DEVNULL,capture_output=True,timeout=60)
        self.assertEqual(result.returncode,code,result.stderr.decode(errors="replace")[:3000]);self.assertEqual(result.stderr,b"")
        for private in (str(self.work).encode(),b"FICTIONAL_PRIVATE",b"Traceback"):self.assertNotIn(private,result.stdout)
        after=self.tree(self.work)
        allowed=[self.owned(path).relative_to(self.work).as_posix() for path in mutable]
        affected={key for key in before.keys()|after.keys() if before.get(key)!=after.get(key)}
        self.assertTrue(all(any(key==root or key.startswith(root+"/") for root in allowed) for key in affected),"Unexpected application changes: "+repr(affected))
        self.runtime_preserved()
        if text:return result.stdout.decode("utf-8")
        value=json.loads(result.stdout)
        self.assertEqual(result.stdout,json.dumps(value,sort_keys=code!=130).encode()+NL)
        if error is not None:self.assertEqual(value,dict(status="INCOMPLETE",error=error))
        return value
    def cli(self,command,*extra,code=0,error=None,mode="normal",readonly=False):
        mutating=command in {"init","import-profile","activate","deactivate","recover"} and code in (0,130) and not readonly
        return self.invoke([command,"--workspace",self.workspace,*extra],mode=mode,code=code,error=error,mutable=[self.workspace] if mutating else [])
    def populated(self,tag="workspace",active=None):
        self.workspace=self.owned(self.work/tag)
        self.cli("init")
        for profile in ("orchard","meadow"):self.cli("import-profile","--profile",profile,"--source",self.sources/profile)
        if active:self.cli("activate","--profile",active)
    def state(self):
        return json.loads((self.workspace/"state.json").read_bytes())
    def pending_folder(self):
        value=self.state()["pending"];self.assertRegex(value,r"^[a-f0-9]{32}$");return self.owned(self.workspace/"operations"/value)
    def manifest(self,profile):
        value=json.loads((self.workspace/"profiles"/profile/"manifest.json").read_bytes())
        source=self.sources/profile
        self.assertEqual(value["directories"],["config"])
        expected=[dict(path=path.relative_to(source).as_posix(),bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for path in sorted(source.rglob("*"),key=lambda p:p.relative_to(source).as_posix()) if path.is_file()]
        self.assertEqual(value["files"],expected);self.assertEqual(value["total_bytes"],sum(row["bytes"] for row in expected))
        body={key:value[key] for key in ("schema_version","directories","files","total_bytes")}
        self.assertEqual(value["digest"],sha((json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode()))
        self.assertEqual(self.catalog(self.workspace/"profiles"/profile/"payload"),self.catalog(source));return value
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            if os.name=="nt" and getattr(error,"winerror",None)==1314 and os.environ.get("OUTLANDS_PROFILE_REQUIRE_LINKS")!="1":self.skipTest(LINK_REASON)
            raise

    def test_copied_affinity_and_help_import_no_engine_tk_or_state(self):
        self.assertEqual(self.invoke(mode="affinity"),dict(status="COPIED_RUNTIME_AFFINITY",runtime_files=6,native_tk_widgets_checked=False))
        for args in ((),("--help",),("activate","--help"),("gui","--help")):
            self.assertIn("usage:",self.invoke(args,mode="help",text=True))
        self.assertFalse(self.workspace.exists())
    def test_generator_exact_fictional_sources_and_exclusive_destination(self):
        target=self.owned(self.work/"generated")
        value=self.invoke(["--output",target],mode="generate",mutable=[target]);self.assertEqual(value,dict(status="FICTIONAL_EXAMPLES_CREATED",profiles=2,files=4))
        self.assertEqual((target/"orchard/config/demo.ini").read_bytes(),b"[fictional]\ncolor=orange\nmode=orchard\n")
        self.assertEqual((target/"meadow/config/demo.ini").read_bytes(),b"[fictional]\ncolor=green\nmode=meadow\n")
        self.assertEqual(len([p for p in target.rglob("*") if p.is_file()]),4)
        self.invoke(["--output",target],mode="generate",code=2,error="OUTPUT_EXISTS")
    def test_initialization_is_fresh_and_explicit_paths_and_arguments_are_fixed(self):
        value=self.cli("init");self.assertEqual(value,dict(status="OK",active_profile=None,pending=None,profiles=[],history=[]))
        self.assertEqual(set(p.name for p in self.workspace.iterdir()),{".lock","owner.json","state.json","profiles","operations"})
        self.cli("init",code=2,error="DESTINATION_EXISTS")
        for args,error in ((["init","--workspace","relative"],"LOCAL_ABSOLUTE_PATH_REQUIRED"),(["init","--workspace",self.work/"missing/new"],"IO_OR_INPUT_ERROR"),(["activate"],"ARGUMENTS_INVALID"),(["FICTIONAL_PRIVATE_UNKNOWN"],"ARGUMENTS_INVALID")):
            self.invoke(args,code=2,error=error)
    def test_imported_manifest_hashes_and_duplicate_profile_preserve_bytes(self):
        self.populated()
        for profile in ("orchard","meadow"):self.manifest(profile)
        self.cli("import-profile","--profile","orchard","--source",self.sources/"meadow",code=2,error="PROFILE_EXISTS")
        value=self.cli("status");self.assertEqual([row["id"] for row in value["profiles"]],["meadow","orchard"]);self.assertEqual(len(value["history"]),2)
    def test_generated_orchard_meadow_activation_switch_and_deactivation_retain_trees(self):
        target=self.owned(self.work/"generated")
        self.invoke(["--output",target],mode="generate",mutable=[target]);self.sources=target;self.populated()
        for profile in ("orchard","meadow"):
            result=self.cli("activate","--profile",profile);self.assertEqual(result["active_profile"],profile);self.assertEqual(self.catalog(self.workspace/"active"),self.catalog(self.sources/profile))
        switched=self.workspace/"operations"/result["operation"]/"previous";self.assertEqual(self.catalog(switched),self.catalog(self.sources/"orchard"))
        result=self.cli("deactivate");self.assertIsNone(result["active_profile"]);self.assertFalse((self.workspace/"active").exists());self.assertEqual(self.catalog(self.workspace/"operations"/result["operation"]/"previous"),self.catalog(self.sources/"meadow"))
    def test_readonly_status_list_plan_and_idempotent_transitions_create_no_operations(self):
        self.populated(active="orchard")
        before=self.tree(self.workspace);planned=self.cli("plan","--action","activate","--profile","meadow");self.assertTrue(planned["allowed"]);self.assertTrue(planned["previous_active_retained"])
        self.cli("status");self.cli("list");self.assertEqual(self.tree(self.workspace),before)
        self.assertEqual(self.cli("activate","--profile","orchard",readonly=True)["outcome"],"already_active")
        self.cli("deactivate");self.assertEqual(self.cli("deactivate",readonly=True)["outcome"],"already_disabled");self.assertEqual(self.cli("recover",readonly=True)["outcome"],"no_pending_operation")
    def test_advisory_plan_does_not_authorize_changed_profile_payload(self):
        self.populated();self.cli("plan","--action","activate","--profile","orchard")
        self.write(self.workspace/"profiles/orchard/payload/README.txt",b"fictional drift")
        self.cli("activate","--profile","orchard",code=2,error="TREE_MISMATCH");self.assertFalse((self.workspace/"active").exists())
    def test_changed_missing_and_unexpected_active_entries_require_review_without_moving(self):
        for kind in ("changed","missing","unexpected"):
            self.populated(kind,active="orchard");path=self.owned(self.workspace/"active/README.txt")
            if kind=="changed":self.write(path,b"fictional drift")
            elif kind=="missing":path.unlink()
            else:self.write(self.workspace/"active/unexpected.txt",b"fictional retained")
            value=self.cli("status",code=1);self.assertIn(dict(code="ACTIVE_TREE_MISMATCH"),value["issues"])
            for command in ("deactivate","recover"):self.cli(command,code=2,error="ACTIVE_TREE_MISMATCH")
    def test_unmanaged_active_directory_is_never_adopted_or_overwritten(self):
        self.populated();self.write(self.workspace/"active/held.txt",b"fictional unmanaged data")
        self.cli("activate","--profile","orchard",code=2,error="ACTIVE_TREE_MISMATCH");self.assertEqual(self.cli("status",code=1)["active_profile"],None)
    def test_strict_state_duplicate_keys_unknown_fields_and_invalid_tokens_are_held(self):
        self.populated();path=self.workspace/"state.json";original=path.read_bytes()
        rows=[b'{"schema_version":1,"schema_version":1,"active_profile":null,"pending":null}',b'{"schema_version":true,"active_profile":null,"pending":null}',b'{"schema_version":1,"active_profile":null,"pending":"../FICTIONAL_PRIVATE"}',b'{"schema_version":1,"active_profile":null,"pending":null,"extra":1}']
        for index,raw in enumerate(rows):
            self.write(path,raw);self.cli("status",code=2,error="DUPLICATE_JSON_KEY" if index==0 else "STATE_INVALID")
        self.write(path,original);self.cli("status")
    def test_manifest_hash_and_unknown_metadata_fields_are_not_repaired(self):
        self.populated();path=self.workspace/"profiles/orchard/manifest.json";original=path.read_bytes();value=json.loads(original)
        for altered in (dict(value,digest="0"*64),dict(value,extra="FICTIONAL_PRIVATE")):
            self.write(path,json.dumps(altered).encode());self.cli("activate","--profile","orchard",code=2,error="MANIFEST_INVALID")
        self.write(path,original);self.cli("activate","--profile","orchard")
    def test_actual_eight_mebibyte_file_limit_refuses_before_creating_operation(self):
        self.cli("init");self.write(self.sources/"orchard/README.txt",b"x"*(8*1024*1024+1))
        self.cli("import-profile","--profile","orchard","--source",self.sources/"orchard",code=2,error="FILE_BYTE_LIMIT");self.assertEqual(list((self.workspace/"operations").iterdir()),[])
    def test_controlled_collection_path_and_total_bounds_refuse_without_partial_import(self):
        self.cli("init")
        for limit,error in ((dict(MAX_FILES=1),"FILE_COUNT_LIMIT"),(dict(MAX_DIRECTORIES=0),"DIRECTORY_COUNT_LIMIT"),(dict(MAX_TOTAL_BYTES=1),"TREE_BYTE_LIMIT"),(dict(MAX_PATH=3),"RELATIVE_PATH_UNSUPPORTED"),(dict(MAX_PROFILES=0),"PROFILE_COUNT_LIMIT"),(dict(MAX_OPERATIONS=0),"OPERATION_COUNT_LIMIT")):
            self.cli("import-profile","--profile","orchard","--source",self.sources/"orchard",mode="limit:"+json.dumps(limit),code=2,error=error)
        self.assertEqual(list((self.workspace/"operations").iterdir()),[])
    def test_profile_identifiers_and_source_workspace_overlap_are_refused(self):
        self.cli("init")
        for profile in ("../escape","Uppercase","has space","a"*41):
            self.cli("import-profile","--profile",profile,"--source",self.sources/"orchard",code=2,error="PROFILE_NAME_INVALID")
        self.cli("import-profile","--profile","orchard","--source",self.workspace,code=2,error="SOURCE_WORKSPACE_OVERLAP")
        self.cli("import-profile","--profile","orchard","--source",self.sources/"orchard/README.txt",code=2,error="DIRECTORY_REQUIRED")
    def test_mandatory_hardlinked_source_is_refused_without_copying(self):
        self.cli("init");alias=self.owned(self.sources/"orchard/alias.txt");os.link(self.sources/"orchard/README.txt",alias);self.assertTrue(alias.samefile(self.sources/"orchard/README.txt"))
        self.cli("import-profile","--profile","orchard","--source",self.sources/"orchard",code=2,error="HARDLINK_UNSUPPORTED")
    def test_native_no_replace_rename_moves_only_to_new_destination(self):
        source=self.owned(self.work/"rename source");destination=self.owned(self.work/"rename target");self.write(source/"kept.txt",b"fictional retained")
        self.assertEqual(self.invoke([source,destination],mode="rename",mutable=[source,destination]),dict(status="NATIVE_RENAME_NEW_ONLY"));self.assertEqual((source/"kept.txt").read_bytes(),b"fictional retained");self.assertEqual(list(destination.iterdir()),[])
    def test_native_destination_creation_race_is_refused_without_replacing(self):
        source=self.owned(self.work/"race source");destination=self.owned(self.work/"race target");self.write(source/"kept.txt",b"fictional retained")
        self.assertEqual(self.invoke([source,destination],mode="rename-race",mutable=[destination]),dict(status="NATIVE_RENAME_RACE_REFUSED"));self.assertEqual((source/"kept.txt").read_bytes(),b"fictional retained");self.assertEqual(list(destination.iterdir()),[])
    def test_another_process_holds_nonblocking_workspace_lock(self):
        self.populated();ready=self.owned(self.work/"lock-ready")
        lock_path=self.owned(self.workspace/".lock");lock_bytes=lock_path.read_bytes()
        child=subprocess.Popen([sys.executable,"-I","-B","-W","error","-c",CHILD,str(self.copy),str(self.work),"hold",str(self.workspace),str(ready)],cwd=self.work,env=self.env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+10
            while not ready.exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(0.02)
            self.assertTrue(ready.exists(),"Independent lock holder did not become ready");self.locked_path=lock_path
            started=time.monotonic();self.cli("status",code=2,error="WORKSPACE_BUSY");self.assertLess(time.monotonic()-started,5)
        finally:
            try:out,err=child.communicate(b"release",timeout=10)
            except subprocess.TimeoutExpired:child.kill();out,err=child.communicate(timeout=10)
        if hasattr(self,"locked_path"):del self.locked_path
        self.assertEqual((child.returncode,out,err),(0,b"",b""));self.assertEqual(lock_path.read_bytes(),lock_bytes);self.cli("status")
    def test_interrupt_after_intent_aborts_absent_stage_and_preserves_previous_active(self):
        self.populated(active="orchard");self.cli("activate","--profile","meadow",mode="interrupt:after_intent_written",code=130)
        folder=self.pending_folder();self.assertFalse((folder/"stage").exists());self.cli("activate","--profile","orchard",code=2,error="RECOVERY_REQUIRED")
        self.assertEqual(self.cli("recover")["outcome"],"aborted_incomplete_stage");self.assertEqual(self.catalog(self.workspace/"active"),self.catalog(self.sources/"orchard"));self.assertTrue((folder/"intent.json").is_file())
    def test_interrupt_after_verified_stage_recovers_complete_candidate(self):
        self.populated(active="orchard");self.cli("activate","--profile","meadow",mode="interrupt:after_stage_verified",code=130)
        folder=self.pending_folder();self.assertEqual(self.catalog(folder/"stage"),self.catalog(self.sources/"meadow"));result=self.cli("recover");self.assertEqual(result["active_profile"],"meadow");self.assertEqual(self.catalog(folder/"previous"),self.catalog(self.sources/"orchard"))
    def test_interrupt_after_previous_active_and_state_boundaries_recovers_verified_trees(self):
        for phase in ("after_previous_retained","after_active_committed","after_state_saved"):
            self.populated(phase,active="orchard");self.cli("activate","--profile","meadow",mode="interrupt:"+phase,code=130)
            folder=self.pending_folder();result=self.cli("recover");self.assertEqual(result["active_profile"],"meadow");self.assertEqual(result["outcome"],"complete");self.assertEqual(self.catalog(self.workspace/"active"),self.catalog(self.sources/"meadow"));self.assertEqual(self.catalog(folder/"previous"),self.catalog(self.sources/"orchard"))
    def test_interrupted_import_retains_partial_payload_and_never_imports_it(self):
        self.cli("init");self.cli("import-profile","--profile","orchard","--source",self.sources/"orchard",mode="partial-import",code=130)
        folder=self.pending_folder();before=self.catalog(folder/"stage");result=self.cli("recover");self.assertEqual(result["outcome"],"aborted_incomplete_stage");self.assertEqual(self.catalog(folder/"stage"),before);self.assertFalse((self.workspace/"profiles/orchard").exists())
    def test_partial_activation_aborts_but_unexpected_stage_content_stays_held(self):
        for mode in ("partial-activation","unexpected-stage"):
            self.populated(mode,active="orchard");self.cli("activate","--profile","meadow",mode=mode,code=130);folder=self.pending_folder();before=self.catalog(folder/"stage")
            if mode=="partial-activation":self.assertEqual(self.cli("recover")["outcome"],"aborted_incomplete_stage")
            else:self.cli("recover",code=2,error="STAGE_DRIFT")
            self.assertEqual(self.catalog(folder/"stage"),before);self.assertEqual(self.catalog(self.workspace/"active"),self.catalog(self.sources/"orchard"))
    def test_recovery_holds_unexpected_destination_after_previous_tree_retention(self):
        self.populated(active="orchard");self.cli("activate","--profile","meadow",mode="interrupt:after_previous_retained",code=130)
        folder=self.pending_folder();self.write(self.workspace/"active/unexpected.txt",b"fictional held");self.cli("recover",code=2,error="RECOVERY_LAYOUT_CONFLICT");self.assertEqual(self.catalog(folder/"previous"),self.catalog(self.sources/"orchard"))
    def test_retained_pre_intent_folder_requires_review_without_blocking_valid_plan(self):
        self.populated();folder=self.owned(self.workspace/"operations"/("a"*32));folder.mkdir()
        value=self.cli("status",code=1);self.assertIsNone(value["pending"]);self.assertIn(dict(code="RETAINED_PREPARATION"),value["issues"])
        self.assertTrue(self.cli("plan","--action","activate","--profile","orchard")["allowed"]);self.cli("activate","--profile","orchard");self.assertTrue(folder.is_dir())
    def test_short_source_read_is_refused_and_payload_code_remains_inert(self):
        self.cli("init");self.cli("import-profile","--profile","orchard","--source",self.sources/"orchard",mode="short-source-read",code=2,error="INPUT_CHANGED")
        self.write(self.sources/"orchard/inert.py",b"raise AssertionError('Payload must never execute')\n")
        self.cli("import-profile","--profile","orchard","--source",self.sources/"orchard");self.cli("activate","--profile","orchard");self.assertEqual((self.workspace/"active/inert.py").read_bytes(),b"raise AssertionError('Payload must never execute')\n")
    def test_native_symlink_source_and_linked_parent_routes(self):
        self.cli("init");linked=self.owned(self.work/"source link");self.symlink(linked,self.sources/"orchard",directory=True)
        self.cli("import-profile","--profile","orchard","--source",linked,code=2,error="LINKED_PATH_REJECTED")
        parent=self.owned(self.work/"parent link");self.symlink(parent,self.sources,directory=True);self.cli("import-profile","--profile","orchard","--source",parent/"orchard",code=2,error="LINKED_PATH_REJECTED")
    def test_native_symlink_payload_and_workspace_routes(self):
        self.cli("init");linked=self.owned(self.sources/"orchard/linked.txt");self.symlink(linked,self.sources/"meadow/README.txt")
        self.cli("import-profile","--profile","orchard","--source",self.sources/"orchard",code=2,error="TREE_ENTRY_UNSUPPORTED")
        route=self.owned(self.work/"workspace link");self.symlink(route,self.workspace,directory=True);self.invoke(["status","--workspace",route],code=2,error="LINKED_PATH_REJECTED")
    @unittest.skipUnless(os.name=="nt",WINDOWS_REASON)
    def test_native_windows_streams_and_junction_routes(self):
        self.cli("init");self.write(Path(str(self.sources/"orchard/README.txt")+":fictional"),b"fictional stream")
        self.cli("import-profile","--profile","orchard","--source",self.sources/"orchard",code=2,error="NAMED_STREAM_UNSUPPORTED")
        route=self.owned(self.work/"junction")
        done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(route),str(self.sources)],capture_output=True,timeout=10)
        self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:route.rmdir() if route.exists() else None)
        self.cli("import-profile","--profile","orchard","--source",route/"meadow",code=2,error="LINKED_PATH_REJECTED")
    @unittest.skipUnless(os.name!="nt",POSIX_REASON)
    def test_native_posix_special_objects_and_case_collisions(self):
        self.cli("init");fifo=self.owned(self.sources/"orchard/fictional.fifo");os.mkfifo(fifo)
        sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.owned(self.sources/"meadow/fictional.sock")));self.addCleanup(sock.close)
        for name in ("orchard","meadow"):self.cli("import-profile","--profile",name,"--source",self.sources/name,code=2,error="TREE_ENTRY_UNSUPPORTED")
        source=self.owned(self.work/"case source");self.write(source/"Name.txt",b"one");self.write(source/"name.txt",b"two");self.assertFalse((source/"Name.txt").samefile(source/"name.txt"));self.cli("import-profile","--profile","case","--source",source,code=2,error="CASE_COLLISION")


if __name__=="__main__":
    unittest.main()
