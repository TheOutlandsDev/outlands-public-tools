"""Actual copied-pair CLI consumers over invented candidate/current trees only."""
import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT=Path(__file__).resolve().parents[1]
RUNTIMES=("preflight.py", "preflight_windows.py")
RECOVERY=[
    "Confirm a maintenance window and application-consistent stopped state independently.",
    "Make and verify a private backup; retain its manifest digest separately.",
    "Review this plan and recheck both trees before applying changes with another tool.",
    "Verify the resulting candidate version before starting the application.",
    "If recovery is needed, restore the verified backup to a new directory and review it before switching.",
]


def sha(data): return hashlib.sha256(data).hexdigest()


def content(data): return dict(size=len(data), sha256=sha(data))


def encoded(value): return (json.dumps(value, ensure_ascii=True)+"\n").encode("utf-8")


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent=Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP") or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp=tempfile.TemporaryDirectory(prefix="preflight-cli-",dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)
        self.runtime=self.work/"copied-runtime"; self.runtime.mkdir()
        self.runtime_bytes={name:(ROOT/name).read_bytes() for name in RUNTIMES}
        for name,data in self.runtime_bytes.items(): (self.runtime/name).write_bytes(data)
        self.source=self.runtime/"preflight.py"
        self.candidate=self.work/"candidate"; self.candidate.mkdir()
        self.current=self.work/"current"; self.current.mkdir()
        self.controls=self.work/"controls"; self.controls.mkdir()
        self.reports=self.work/"reports"; self.reports.mkdir()
        self.payloads={"docs/readme.txt":b"Fictional release notes\n", "bin/component.py":b"raise RuntimeError('FICTIONAL_PAYLOAD_EXECUTED')\n", "data/empty.bin":b""}
        self.current_bytes={"docs/readme.txt":self.payloads["docs/readme.txt"],"bin/component.py":b"Fictional previous component\n"}
        for root,values in ((self.candidate,self.payloads),(self.current,self.current_bytes)):
            for name,data in values.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        extra=self.current/"unselected";extra.mkdir();(extra/"private.py").write_bytes(b"raise RuntimeError('FICTIONAL_UNSELECTED_EXECUTED')\n")
        self.manifest=self.controls/"manifest.json"
        self.manifest.write_bytes(encoded(dict(schema_version=1,inventory=[dict(path=name,**content(data)) for name,data in self.payloads.items()])))
        self.pin=sha(self.manifest.read_bytes())
        self.spec=self.controls/"launcher.json"
        self.spec.write_bytes(encoded(dict(schema_version=1,executable="bin/component.py",working_directory=".",arguments=["--fictional","FICTIONAL_PRIVATE_ARGUMENT"])))
        self.spec_pin=sha(self.spec.read_bytes())
        self.environment=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1")
        for key in ("PYTHONPATH","PYTHONHOME","PYTHONSAFEPATH","PYTHONSTARTUP"): self.environment.pop(key,None)
        self.serial=0

    def metadata(self,value=None,raw=None):
        self.serial+=1; path=self.controls/("control-"+str(self.serial)+".json")
        path.write_bytes(encoded(value) if raw is None else raw)
        return path,sha(path.read_bytes())

    def wrapper(self,body,postlude="",prelude=""):
        self.serial+=1;script=self.work/("controlled-child-"+str(self.serial)+".py")
        script.write_text("import sys,os\nfrom pathlib import Path\nimport importlib.metadata\n"
            "assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())\n"
            "sys.path.insert(0,"+repr(str(self.runtime))+")\n"+textwrap.dedent(prelude)+
            "import preflight as tool\nif os.name=='nt': tool._windows()\nevents=[]\n"+textwrap.dedent(body)+
            "\nstatus=tool.main(sys.argv[1:])\n"+textwrap.dedent(postlude)+"\nraise SystemExit(status)\n",encoding="utf-8",newline="\n")
        return script

    def process(self,*arguments,expected=0,code=None,script=None,report=None,new_report=False,json_output=True):
        tree={p.relative_to(self.work).as_posix() for p in self.work.rglob("*")}
        retained={}
        for path in self.work.rglob("*"):
            if not path.is_symlink() and not path.is_junction():
                info=path.lstat()
                if stat.S_ISREG(info.st_mode): retained[path]=(sha(path.read_bytes()),info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_ino,info.st_nlink)
        done=subprocess.run([sys.executable,"-B","-s","-X","utf8",str(script or self.source),*map(str,arguments)],cwd=self.work,env=self.environment,
                            stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding="utf-8",errors="strict",timeout=90)
        self.assertEqual(done.returncode,expected,done.stdout+done.stderr)
        self.assertEqual(done.stderr,"")
        wanted=tree|({report.relative_to(self.work).as_posix()} if new_report else set())
        self.assertEqual({p.relative_to(self.work).as_posix() for p in self.work.rglob("*")},wanted)
        for path,before in retained.items():
            info=path.lstat();self.assertEqual((sha(path.read_bytes()),info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_ino,info.st_nlink),before)
        self.assertEqual({p.name for p in self.runtime.iterdir()},set(RUNTIMES))
        self.assertTrue(all((self.runtime/name).read_bytes()==data for name,data in self.runtime_bytes.items()))
        self.assertFalse(list(self.work.rglob("*.pyc")))
        self.assertNotIn(str(self.work),done.stdout.replace("\\\\","\\"))
        self.assertNotIn("FICTIONAL_PRIVATE",done.stdout)
        self.assertNotIn("component.py",done.stdout)
        if not json_output:return done.stdout
        self.assertEqual(len(done.stdout.splitlines()),1)
        value=json.loads(done.stdout)
        if expected:
            self.assertEqual(value,dict(status="ERROR",code=code,execution_performed=False))
        else:
            self.assertEqual(value["status"],"VERIFIED");self.assertIs(value["execution_performed"],False)
            self.assertNotIn("files",value);self.assertNotIn("recovery",value)
        return value

    def run_cli(self,operation="verify",*,candidate=None,current=None,manifest=None,pin=None,spec=None,spec_pin=None,report=None,**options):
        args=[operation,"--candidate",candidate or self.candidate,"--manifest",manifest or self.manifest,"--manifest-sha",self.pin if pin is None else pin]
        if operation=="plan":args += ["--current",current or self.current]
        if operation=="launcher-check":args += ["--spec",spec or self.spec,"--spec-sha",self.spec_pin if spec_pin is None else spec_pin]
        if report is not None:args += ["--report",report]
        return self.process(*args,report=report,**options)

    def verify_summary(self,pin=None):
        return dict(status="VERIFIED",schema_version=1,operation="verify",execution_performed=False,manifest_sha256=pin or self.pin,files_verified=3)

    def launcher_summary(self,pin=None,spec_pin=None,count=2):
        return dict(status="VERIFIED",schema_version=1,operation="launcher-check",execution_performed=False,manifest_sha256=pin or self.pin,
                    launch_spec_sha256=spec_pin or self.spec_pin,argument_count=count,executable_listed_and_verified=True,working_directory_exists=True,runtime_acceptance="NOT_TESTED")

    def plan_body(self,current=None):
        current=self.current_bytes if current is None else current
        rows=[];counts={}
        for name in sorted(self.payloads):
            previous=current.get(name)
            action="ADD" if previous is None else "UNCHANGED" if previous==self.payloads[name] else "REPLACE"
            counts[action]=counts.get(action,0)+1
            rows.append(dict(path=name,action=action,expected=content(self.payloads[name]),current=None if previous is None else content(previous)))
        return dict(schema_version=1,operation="plan",execution_performed=False,manifest_sha256=self.pin,counts=counts,files=rows,
                    unlisted_current_files="NOT_INSPECTED_OR_SELECTED",recovery=RECOVERY)

    def plan_summary(self,current=None):
        return dict(status="VERIFIED",**{key:value for key,value in self.plan_body(current).items() if key not in ("files","recovery")})

    def symlink(self,path,target):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:path.symlink_to(target,target_is_directory=target.is_dir())
        except OSError as error:
            if os.name=="nt" and getattr(error,"winerror",None)==1314 and os.environ.get("OUTLANDS_PREFLIGHT_REQUIRE_LINKS")!="1":self.skipTest("Native symlink privilege unavailable")
            raise AssertionError("Native symlink fixture creation failed") from error
        self.addCleanup(path.unlink)

    def test_verify_has_exact_summary_and_exclusive_complete_report(self):
        report=self.reports/"verify.json"
        self.assertEqual(self.run_cli(report=report,new_report=True),self.verify_summary())
        self.assertEqual(report.read_bytes(),(json.dumps({k:v for k,v in self.verify_summary().items() if k!="status"},indent=2,ensure_ascii=True)+"\n").encode())
        self.run_cli(report=report,expected=2,code="PREFLIGHT_REFUSED_OR_FAILED")

    def test_plan_full_report_classifies_add_replace_unchanged_without_selecting_unlisted_current(self):
        report=self.reports/"plan.json"
        self.assertEqual(self.run_cli("plan",report=report,new_report=True),self.plan_summary())
        self.assertEqual(json.loads(report.read_bytes()),self.plan_body())
        self.assertEqual([r["action"] for r in self.plan_body()["files"]],["REPLACE","ADD","UNCHANGED"])

    def test_launcher_full_summary_report_and_arguments_never_execute_payload(self):
        report=self.reports/"launcher.json"
        self.assertEqual(self.run_cli("launcher-check",report=report,new_report=True),self.launcher_summary())
        self.assertEqual(json.loads(report.read_bytes()),{k:v for k,v in self.launcher_summary().items() if k!="status"})
        self.assertNotIn("FICTIONAL_PRIVATE_ARGUMENT",report.read_text())

    def test_standalone_and_collection_layouts_have_exact_different_source_boundaries(self):
        self.run_cli(report=self.runtime/"forbidden.json",expected=2,code="REPORT_MUST_BE_EXTERNAL")
        outside=self.reports/"standalone-sibling.json"
        self.assertEqual(self.run_cli(report=outside,new_report=True),self.verify_summary())
        collection=self.work/"collection";directory=collection/"tools"/"release-preflight";directory.mkdir(parents=True)
        for name,data in self.runtime_bytes.items():(directory/name).write_bytes(data)
        docs=collection/"docs";docs.mkdir()
        self.run_cli(report=docs/"forbidden.json",script=directory/"preflight.py",expected=2,code="REPORT_MUST_BE_EXTERNAL")
        sibling=self.reports/"collection-external.json"
        self.assertEqual(self.run_cli(report=sibling,new_report=True,script=directory/"preflight.py"),self.verify_summary())

    def test_external_pin_format_and_mismatch_are_checked_before_json_decode(self):
        script=self.wrapper("def forbidden(*args,**kwargs): raise AssertionError('Untrusted JSON decoded')\ntool.json.loads=forbidden\n")
        for pin in ("", "A"*64,"not-a-sha256"):
            self.run_cli(pin=pin,expected=2,code="EXTERNAL_SHA256_PIN_REQUIRED",script=script)
        self.run_cli(pin="0"*64,expected=2,code="PIN_MISMATCH",script=script)
        self.run_cli("launcher-check",spec_pin="0"*64,expected=2,code="PIN_MISMATCH")

    def test_exact_raw_metadata_pin_allows_semantic_equivalence_without_authorship_claim(self):
        value=json.loads(self.manifest.read_bytes());path,pin=self.metadata(raw=b"\xef\xbb\xbf"+json.dumps(value,sort_keys=True).encode()+b"\r\n")
        self.assertNotEqual(pin,self.pin)
        self.assertEqual(self.run_cli(manifest=path,pin=pin),self.verify_summary(pin))
        self.run_cli(manifest=path,pin=self.pin,expected=2,code="PIN_MISMATCH")

    def test_candidate_inventory_is_exact_and_file_content_size_and_hash_are_pinned(self):
        extra=self.candidate/"extra.bin";extra.write_bytes(b"invented")
        self.run_cli(expected=2,code="UNLISTED_FILE");extra.unlink()
        empty=self.candidate/"empty-dir";empty.mkdir();self.run_cli(expected=2,code="UNLISTED_DIRECTORY");empty.rmdir()
        selected=self.candidate/"docs/readme.txt";raw=selected.read_bytes();selected.write_bytes(b"x"*len(raw))
        self.run_cli(expected=2,code="CANDIDATE_MISMATCH");selected.write_bytes(raw+b"x")
        self.run_cli(expected=2,code="CANDIDATE_MISMATCH");selected.unlink()
        self.run_cli(expected=2,code="CANDIDATE_MISMATCH")

    def test_manifest_schema_paths_case_collisions_and_resource_declarations_are_strict(self):
        row=dict(path="bin/component.py",**content(self.payloads["bin/component.py"]))
        samples=[(None,"INVALID_MANIFEST"),({"schema_version":True,"inventory":[row]},"INVALID_MANIFEST"),
                 ({"schema_version":1,"inventory":[]},"INVALID_MANIFEST"),({"schema_version":1,"inventory":[dict(row,private=1)]},"INVALID_MANIFEST_ENTRY")]
        for name,code in [("../escape","INVALID_RELATIVE_PATH"),("con.txt","INVALID_RELATIVE_PATH"),("x:stream","INVALID_RELATIVE_PATH"),("e\u0301.txt","NONCANONICAL_PATH")]:
            samples.append((dict(schema_version=1,inventory=[dict(row,path=name)]),code))
        samples += [(dict(schema_version=1,inventory=[dict(row,path="x"),dict(row,path="X")]),"DUPLICATE_PATH"),
                    (dict(schema_version=1,inventory=[dict(row,path="Bin/a"),dict(row,path="bin/b")]),"CASE_COLLISION"),
                    (dict(schema_version=1,inventory=[dict(row,path="x"),dict(row,path="x/y")]),"FILE_DIRECTORY_COLLISION"),
                    (dict(schema_version=1,inventory=[dict(row,size=True)]),"INVALID_MANIFEST_ENTRY"),
                    (dict(schema_version=1,inventory=[dict(row,size=268435457)]),"INVALID_MANIFEST_ENTRY"),
                    (dict(schema_version=1,inventory=[dict(row,path="f"+str(i),size=268435456) for i in range(5)]),"TOTAL_SIZE_LIMIT"),
                    (dict(schema_version=1,inventory=[dict(row,path="f"+str(i)) for i in range(4097)]),"INVALID_MANIFEST")]
        for value,code in samples:
            path,pin=self.metadata(value);self.run_cli(manifest=path,pin=pin,expected=2,code=code)

    def test_manifest_and_spec_exact_one_mib_bom_bounds_and_strict_json(self):
        for role,original in (("manifest",self.manifest),("spec",self.spec)):
            raw=b"\xef\xbb\xbf"+original.read_bytes();exact=raw+b" "*(1048576-len(raw))
            path,pin=self.metadata(raw=exact)
            options=dict(manifest=path,pin=pin) if role=="manifest" else dict(spec=path,spec_pin=pin)
            operation="verify" if role=="manifest" else "launcher-check"
            wanted=self.verify_summary(pin) if role=="manifest" else self.launcher_summary(spec_pin=pin)
            self.assertEqual(self.run_cli(operation,**options),wanted)
            path,pin=self.metadata(raw=exact+b" ");options=dict(manifest=path,pin=pin) if role=="manifest" else dict(spec=path,spec_pin=pin)
            self.run_cli(operation,**options,expected=2,code="FILE_SIZE_LIMIT")
        for raw,code in [(b'{"x":1,"x":2}',"DUPLICATE_JSON_KEY"),(b'{"x":NaN}',"NONSTANDARD_JSON"),(b"\xff","PREFLIGHT_REFUSED_OR_FAILED"),(b"{","PREFLIGHT_REFUSED_OR_FAILED")]:
            path,pin=self.metadata(raw=raw);self.run_cli(manifest=path,pin=pin,expected=2,code=code)

    def test_launcher_spec_is_bounded_structural_data_with_external_control(self):
        original=json.loads(self.spec.read_bytes())
        for changes,code in [({"schema_version":True},"INVALID_LAUNCH_SPEC"),({"environment":{}},"INVALID_LAUNCH_SPEC"),
                             ({"executable":"missing.bin"},"EXECUTABLE_NOT_IN_MANIFEST"),({"working_directory":"missing"},"PREFLIGHT_REFUSED_OR_FAILED"),
                             ({"arguments":["x"]*65},"INVALID_ARGUMENT_VECTOR"),({"arguments":["x"*2049]},"INVALID_ARGUMENT_VECTOR"),
                             ({"arguments":["x"*2048]*4+["x"]},"INVALID_ARGUMENT_VECTOR"),({"arguments":["bad\nargument"]},"INVALID_ARGUMENT_VECTOR")]:
            path,pin=self.metadata(dict(original,**changes));self.run_cli("launcher-check",spec=path,spec_pin=pin,expected=2,code=code)
        for arguments in (["x"*2048]*4,[""]*64):
            path,pin=self.metadata(dict(original,arguments=arguments,working_directory="bin"))
            self.assertEqual(self.run_cli("launcher-check",spec=path,spec_pin=pin),self.launcher_summary(spec_pin=pin,count=len(arguments)))
        inside=self.candidate/"inside-manifest.json";inside.write_bytes(self.manifest.read_bytes())
        self.run_cli(manifest=inside,expected=2,code="MANIFEST_MUST_BE_EXTERNAL")

    def test_plan_nested_roots_conflicts_and_missing_selected_directories_are_not_created(self):
        self.run_cli("plan",current=self.candidate,expected=2,code="NESTED_INPUT_ROOTS")
        self.run_cli("plan",current=self.work,expected=2,code="NESTED_INPUT_ROOTS")
        selected=self.current/"docs/readme.txt";selected.unlink();selected.mkdir()
        self.run_cli("plan",expected=2,code="FILE_TYPE_UNSUPPORTED");selected.rmdir()
        (self.current/"docs").rmdir()
        current=dict(self.current_bytes);current.pop("docs/readme.txt")
        self.assertEqual(self.run_cli("plan"),self.plan_summary(current))
        self.assertFalse((self.current/"docs").exists())

    def test_existing_file_directory_and_control_as_report_are_never_replaced(self):
        report=self.reports/"retained.json";report.write_bytes(b"Fictional prior report\n")
        for path in (report,self.reports,self.manifest,self.spec):
            self.run_cli(report=path,expected=2,code="PREFLIGHT_REFUSED_OR_FAILED")

    def test_report_must_be_outside_candidate_current_source_with_existing_parent(self):
        for path in (self.candidate/"report.json",self.runtime/"report.json"):
            self.run_cli(report=path,expected=2,code="REPORT_MUST_BE_EXTERNAL")
        self.run_cli("plan",report=self.current/"report.json",expected=2,code="REPORT_MUST_BE_EXTERNAL")
        self.run_cli(report=self.reports/"missing"/"report.json",expected=2,code="REPORT_PARENT_REQUIRED")

    def test_help_is_static_and_unknown_arguments_have_fixed_private_output(self):
        self.assertIn("verify",self.process("--help",json_output=False))
        for arguments in ((),("--version",),("FICTIONAL_PRIVATE_COMMAND",),("verify","--candidate","FICTIONAL_PRIVATE_PATH")):
            self.process(*arguments,expected=2,code="INVALID_ARGUMENTS")

    def test_no_network_execution_or_unselected_current_read_occurs(self):
        script=self.wrapper("""
            original_hash=tool.hash_file
            def checked_hash(path,*args,**kwargs):
                assert 'unselected' not in Path(path).parts,'Unlisted current file inspected'
                return original_hash(path,*args,**kwargs)
            def forbidden(*args,**kwargs):raise AssertionError('Network, process or input execution attempted')
            tool.hash_file=checked_hash
            socket.socket=forbidden
            socket.getaddrinfo=forbidden
            urllib.request.urlopen=forbidden
            subprocess.Popen=forbidden
            runpy.run_path=forbidden
            os.system=forbidden
            os.execv=forbidden
            """,prelude="import socket,urllib.request,subprocess,runpy\n")
        self.assertEqual(self.run_cli("plan",script=script),self.plan_summary())
        self.assertEqual(self.run_cli("launcher-check",script=script),self.launcher_summary())

    def test_short_zero_flush_and_readback_failures_never_false_pass_or_cleanup_reports(self):
        for mode in ("short","zero","flush","readback"):
            report=self.reports/(mode+".json")
            script=self.wrapper("""
                original_write,original_sync=os.write,os.fsync
                def written(fd,block):
                    events.append(fd)
                    return 0 if MODE=='zero' else original_write(fd,block[:3] if MODE=='short' else block)
                def synced(fd):
                    if MODE=='flush':raise OSError('FICTIONAL_PRIVATE_FLUSH')
                    return original_sync(fd)
                os.write,os.fsync=written,synced
                if MODE=='readback':
                    if os.name=='nt':
                        def failed(*args,**kwargs):raise tool.PreflightError('REPORT_VERIFY_FAILED')
                        tool._windows().read_bounded=failed
                    else:
                        original_hash=tool.hash_file
                        def failed(path,*args,**kwargs):
                            if Path(path)==Path(REPORT_VALUE):return dict(size=0,sha256='0'*64)
                            return original_hash(path,*args,**kwargs)
                        tool.hash_file=failed
                """.replace("MODE",repr(mode)).replace("REPORT_VALUE",repr(str(report))),postlude="""
                assert events
                for fd in events:
                    try:os.fstat(fd)
                    except OSError as error:assert error.errno==9
                    else:raise AssertionError('Report descriptor remained open')
                """)
            code={"zero":"OUTPUT_IO_ERROR","flush":"PREFLIGHT_REFUSED_OR_FAILED","readback":"REPORT_VERIFY_FAILED"}.get(mode)
            observed=self.run_cli("plan",script=script,report=report,new_report=True,expected=0 if mode=="short" else 2,code=code)
            if mode=="short":self.assertEqual(observed,self.plan_summary())
            if mode=="zero":self.assertEqual(report.read_bytes(),b"")
            else:self.assertEqual(json.loads(report.read_bytes()),self.plan_body())
            self.run_cli("plan",report=report,expected=2,code="PREFLIGHT_REFUSED_OR_FAILED")

    def test_controlled_read_failure_and_observed_identity_change_are_fixed(self):
        for mode in ("read","identity"):
            script=self.wrapper("""
                original_open,original_identity=os.open,tool.identity
                descriptors=[]
                def opened(*args,**kwargs):
                    fd=original_open(*args,**kwargs);descriptors.append(fd);return fd
                os.open=opened
                if MODE=='read':
                    def failed(*args,**kwargs):raise OSError('FICTIONAL_PRIVATE_READ')
                    os.read=failed
                else:
                    def changed(info):
                        value=original_identity(info);events.append(True)
                        return (value[0],value[1]+1,*value[2:]) if len(events)==2 else value
                    tool.identity=changed
                """.replace("MODE",repr(mode)),postlude="""
                assert descriptors
                for fd in descriptors:
                    try:os.fstat(fd)
                    except OSError as error:assert error.errno==9
                    else:raise AssertionError('Input descriptor remained open')
                """)
            self.run_cli(script=script,expected=2,code="PREFLIGHT_REFUSED_OR_FAILED" if mode=="read" else "INPUT_CHANGED")

    def test_seeded_authored_current_variants_and_manifest_permutations_match_plan_oracle(self):
        selected=random.Random(671)
        for iteration in range(6):
            current={}
            for name,data in self.payloads.items():
                target=self.current/name
                if target.exists():target.unlink()
                choice=selected.choice(("missing","same","different"))
                if choice!="missing":
                    target.parent.mkdir(parents=True,exist_ok=True);current[name]=data if choice=="same" else b"Fictional changed "+str(iteration).encode();target.write_bytes(current[name])
            value=json.loads(self.manifest.read_bytes());value["inventory"].reverse();self.manifest.write_bytes(encoded(value));self.pin=sha(self.manifest.read_bytes())
            report=self.reports/("oracle-"+str(iteration)+".json")
            self.assertEqual(self.run_cli("plan",report=report,new_report=True),self.plan_summary(current))
            self.assertEqual(json.loads(report.read_bytes()),self.plan_body(current))

    def test_native_hardlinked_input_and_report_are_refused_without_target_changes(self):
        selected=self.candidate/"bin/component.py";alias=self.work/"retained-hardlink.py"
        try:os.link(selected,alias)
        except OSError as error:raise AssertionError('Native hardlink fixture creation failed') from error
        self.run_cli(expected=2,code="HARDLINK_UNSUPPORTED");alias.unlink()
        retained=self.reports/"retained.json";retained.write_bytes(b"Fictional retained\n");report=self.reports/"hardlink.json"
        try:os.link(retained,report)
        except OSError as error:raise AssertionError('Native hardlink fixture creation failed') from error
        self.run_cli(report=report,expected=2,code="HARDLINK_UNSUPPORTED")

    def test_native_symlink_input_leaf_and_dangling_are_refused(self):
        alias=self.controls/"linked-manifest.json";self.symlink(alias,self.manifest)
        self.run_cli(manifest=alias,expected=2,code="LINK_OR_REPARSE_UNSUPPORTED")
        absent=self.controls/"absent.json";dangling=self.controls/"dangling.json";self.symlink(dangling,absent)
        self.run_cli(manifest=dangling,expected=2,code="LINK_OR_REPARSE_UNSUPPORTED");self.assertFalse(absent.exists())

    def test_native_symlink_input_parent_is_refused(self):
        alias=self.work/"linked-candidate";self.symlink(alias,self.candidate)
        self.run_cli(candidate=alias,expected=2,code="LINK_OR_REPARSE_UNSUPPORTED")

    def test_native_symlink_report_leaf_and_parent_are_refused(self):
        retained=self.reports/"retained.json";retained.write_bytes(b"Fictional retained\n")
        linked=self.reports/"linked.json";self.symlink(linked,retained)
        self.run_cli(report=linked,expected=2,code="LINK_OR_REPARSE_UNSUPPORTED")
        absent=self.reports/"absent.json";dangling=self.reports/"dangling.json";self.symlink(dangling,absent)
        self.run_cli(report=dangling,expected=2,code="LINK_OR_REPARSE_UNSUPPORTED");self.assertFalse(absent.exists())
        parent=self.work/"linked-reports";self.symlink(parent,self.reports)
        self.run_cli(report=parent/"new.json",expected=2,code="LINK_OR_REPARSE_UNSUPPORTED")

    @unittest.skipUnless(os.name=="nt","Native Windows junction fixture")
    def test_native_windows_junction_input_and_report_parents_are_refused(self):
        for role,target in (("candidate",self.candidate),("current",self.current),("report",self.reports)):
            alias=self.work/(role+"-junction");self.junction(alias,target)
            options=dict(candidate=alias) if role=="candidate" else dict(current=alias) if role=="current" else dict(report=alias/"new.json")
            self.run_cli("plan" if role=="current" else "verify",**options,expected=2,code="LINK_OR_REPARSE_UNSUPPORTED")

    @unittest.skipUnless(os.name=="nt","Native Windows alternate stream fixture")
    def test_native_windows_stream_and_original_suffix_aliases_are_refused(self):
        stream=str(self.manifest)+":fictional"
        with open(stream,"wb") as handle:handle.write(b"Fictional private stream")
        self.assertEqual(self.run_cli(),self.verify_summary())
        for spelling in (stream,str(self.manifest)+".",str(self.manifest)+" ",str(self.manifest.parent)+"."+os.sep+self.manifest.name,str(self.manifest.parent)+" "+os.sep+self.manifest.name):
            self.run_cli(manifest=spelling,expected=2,code="PATH_INVALID")
        for spelling in (str(self.candidate)+".",str(self.candidate)+" "):
            self.run_cli(candidate=spelling,expected=2,code="PATH_INVALID")
        self.run_cli(report=Path(str(self.reports)+".")/"new.json",expected=2,code="PATH_INVALID")
        with open(stream,"rb") as handle:self.assertEqual(handle.read(),b"Fictional private stream")

    @unittest.skipUnless(os.name!="nt","Native POSIX FIFO fixture")
    def test_native_posix_fifo_input_is_refused_before_open(self):
        fifo=self.controls/"fifo.json"
        try:os.mkfifo(fifo,0o600)
        except OSError as error:raise AssertionError('Native FIFO fixture creation failed') from error
        self.run_cli(manifest=fifo,expected=2,code="FILE_TYPE_UNSUPPORTED")

    @unittest.skipUnless(os.name=="nt","Native Windows interrupt fixture")
    def test_native_windows_interruption_is_fixed_and_releases_handles(self):
        script=self.wrapper("""
            def interrupted(*args,**kwargs):raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT')
            os.read=interrupted
            """,postlude="""
            import ctypes
            from ctypes import wintypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
            kernel.CreateFileW.restype=wintypes.HANDLE
            kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
            held=kernel.CreateFileW(MANIFEST,0x10000,0,None,3,0x80,None)
            if held==ctypes.c_void_p(-1).value:raise AssertionError('Input handles remained held after interruption') from ctypes.WinError(ctypes.get_last_error())
            assert kernel.CloseHandle(held)
            """.replace("MANIFEST",repr(str(self.manifest))))
        self.run_cli(script=script,expected=130,code="PREFLIGHT_INTERRUPTED")

    def junction(self, link, target):
        from ctypes import wintypes

        self.assertTrue(link.is_relative_to(self.work) and target.is_relative_to(self.work))
        link.mkdir()
        self.addCleanup(link.rmdir)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                                          wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                          ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        kernel.DeviceIoControl.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        substitute = ("\\??\\"+str(target)).encode("utf-16-le")
        printable = str(target).encode("utf-16-le")
        payload = substitute+b"\x00\x00"+printable+b"\x00\x00"
        data = struct.pack("<LHHHHHH", 0xA0000003, 8+len(payload), 0,
                           0, len(substitute), len(substitute)+2, len(printable))+payload
        held = kernel.CreateFileW(str(link), 0x40000000, 0, None, 3, 0x02200000, None)
        if held == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            buffer = ctypes.create_string_buffer(data)
            returned = wintypes.DWORD()
            if not kernel.DeviceIoControl(held, 0x000900A4, buffer, len(data), None, 0,
                                          ctypes.byref(returned), None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(held)
        self.assertTrue(link.is_junction())


if __name__ == "__main__":
    unittest.main()
