"""Actual copied checker-pair/generator CLI consumers over fictional metadata."""
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
RUNTIMES=("environment_check.py","environment_windows.py","examples/make_fixture.py")
DEFAULT=object()


def sha(data):return hashlib.sha256(data).hexdigest()


def encoded(value):return (json.dumps(value,ensure_ascii=True)+"\n").encode()


def requirement(identifier="document",kind="file",**fields):return dict(id=identifier,kind=kind,**fields)


def contract(rows=None):
    return dict(schema_version=1,requirements=rows if rows is not None else [requirement(path="inputs/fictional.txt"),
                requirement("workspace","directory",path="workspace"),requirement("tool","program",name="fictional-tool")])


def checked(identifier,kind,status="PRESENT",evidence=None):
    defaults=dict(file="REGULAR_FILE_METADATA",directory="DIRECTORY_METADATA",program="PROGRAM_CANDIDATE_METADATA",observation="OBSERVATION_NOT_SUPPLIED")
    return dict(id=identifier,kind=kind,status=status,evidence=evidence or defaults[kind])


def golden(rows):
    counts={key:sum(row["status"].lower()==key for row in rows) for key in ("present","missing","unknown","unsafe")}
    return dict(schema_version=1,status="ALL_PRESENT" if counts["present"]==len(rows) else "REVIEW_REQUIRED",scope="DECLARED_REQUIREMENTS_ONLY",
                target_contents_read=False,programs_executed=False,versions_verified=False,counts=counts,checks=rows)


def default_result():return golden([checked("document","file"),checked("workspace","directory"),checked("tool","program")])


def fixture_program():
    return ("fictional-tool.cmd",b"@echo off\r\nrem Fictional presence fixture; do not execute.\r\nexit /b 73\r\n") if os.name=="nt" else ("fictional-tool",b"#!/bin/sh\n# Fictional presence fixture; do not execute.\nexit 73\n")


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix,sys.base_prefix);self.assertEqual(list(importlib.metadata.distributions()),[])
        parent=Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT")or os.environ.get("OUTLANDS_TEST_TEMP")or os.environ.get("TEMP")or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute()and parent.is_dir())
        self.temp=tempfile.TemporaryDirectory(prefix="environment-cli-",dir=parent);self.addCleanup(self.temp.cleanup);self.work=Path(self.temp.name)
        self.runtime=self.work/"copied-runtime";self.runtime.mkdir();(self.runtime/"examples").mkdir()
        self.runtime_bytes={name:(ROOT/name).read_bytes()for name in RUNTIMES}
        for name,data in self.runtime_bytes.items():(self.runtime/name).write_bytes(data)
        self.source=self.runtime/"environment_check.py";self.generator=self.runtime/"examples/make_fixture.py"
        self.targets=self.work/"targets";self.targets.mkdir();(self.targets/"inputs").mkdir();(self.targets/"workspace").mkdir()
        self.target=self.targets/"inputs/fictional.txt";self.target.write_bytes(b"FICTIONAL_TARGET_BODY_NEVER_READ\n")
        self.programs=self.work/"programs";self.programs.mkdir();self.program=self.programs/("fictional-tool.cmd"if os.name=="nt"else"fictional-tool")
        self.program.write_bytes(b"FICTIONAL_PROGRAM_BODY_NEVER_EXECUTED\n")
        if os.name!="nt":self.program.chmod(0o700)
        self.controls=self.work/"controls";self.controls.mkdir();self.reports=self.work/"reports";self.reports.mkdir()
        self.control=self.controls/"contract.json";self.control.write_bytes(encoded(contract()))
        self.environment=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1")
        for key in("PYTHONPATH","PYTHONHOME","PYTHONSAFEPATH","PYTHONSTARTUP"):self.environment.pop(key,None)
        self.serial=0

    def metadata(self,value=None,raw=None):
        self.serial+=1;path=self.controls/("control-"+str(self.serial)+".json");path.write_bytes(encoded(value)if raw is None else raw);return path

    def wrapper(self,body,postlude="",generator=False,prelude=""):
        self.serial+=1;script=self.work/("controlled-child-"+str(self.serial)+".py")
        load=("import importlib.util\nspec=importlib.util.spec_from_file_location('copied_generator',"+repr(str(self.generator))+")\ntool=importlib.util.module_from_spec(spec)\nspec.loader.exec_module(tool)\n") if generator else ("sys.path.insert(0,"+repr(str(self.runtime))+")\nimport environment_check as tool\nif os.name=='nt':tool._windows()\n")
        script.write_text("import sys,os\nfrom pathlib import Path\nimport importlib.metadata\nassert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())\n"+
            textwrap.dedent(prelude)+load+"events=[]\n"+textwrap.dedent(body)+"\nstatus=tool.main(sys.argv[1:])\n"+textwrap.dedent(postlude)+"\nraise SystemExit(status)\n",encoding="utf-8",newline="\n")
        return script

    def process(self,*arguments,expected=0,code=None,script=None,generator=False,created=(),optional_created=(),json_output=True):
        tree={p.relative_to(self.work).as_posix()for p in self.work.rglob("*")};retained={}
        for path in self.work.rglob("*"):
            if not path.is_symlink()and not path.is_junction():
                info=path.lstat()
                if stat.S_ISREG(info.st_mode):retained[path]=(sha(path.read_bytes()),info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_ino,info.st_nlink)
        done=subprocess.run([sys.executable,"-B","-s","-X","utf8",str(script or(self.generator if generator else self.source)),*map(str,arguments)],
                            cwd=self.work,env=self.environment,stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding="utf-8",errors="strict",timeout=90)
        self.assertEqual(done.returncode,expected,done.stdout+done.stderr);self.assertEqual(done.stderr,"")
        actual={p.relative_to(self.work).as_posix()for p in self.work.rglob("*")}
        wanted=tree|{p.relative_to(self.work).as_posix()for p in created}
        optional={p.relative_to(self.work).as_posix()for p in optional_created}
        self.assertTrue(wanted<=actual<=wanted|optional)
        for path,before in retained.items():
            info=path.lstat();self.assertEqual((sha(path.read_bytes()),info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_ino,info.st_nlink),before)
        self.assertEqual({p.relative_to(self.runtime).as_posix()for p in self.runtime.rglob("*")},{*RUNTIMES,"examples"})
        self.assertTrue(all((self.runtime/name).read_bytes()==data for name,data in self.runtime_bytes.items()));self.assertFalse(list(self.work.rglob("*.pyc")))
        self.assertNotIn(str(self.work),done.stdout.replace("\\\\","\\"));self.assertNotIn("FICTIONAL_PRIVATE",done.stdout)
        if not json_output:return done.stdout
        self.assertEqual(len(done.stdout.splitlines()),1);value=json.loads(done.stdout)
        if generator:
            if expected:self.assertEqual(value,dict(status="ERROR",code=code,fixture_executed=False))
            else:self.assertEqual(value,dict(status="CREATED",files_created=2,child_directories_created=3,fixture_executed=False))
        elif expected in(2,130):
            if isinstance(code,set):
                self.assertIn(value.get("code"),code);self.assertEqual(set(value),{"status","code","target_contents_read","programs_executed"})
                self.assertEqual(value["status"],"ERROR");self.assertIs(value["target_contents_read"],False);self.assertIs(value["programs_executed"],False)
            else:self.assertEqual(value,dict(status="ERROR",code=code,target_contents_read=False,programs_executed=False))
        else:
            self.assertEqual(set(value),{"schema_version","status","scope","target_contents_read","programs_executed","versions_verified","counts","checks"})
            self.assertTrue(all(value[key]is False for key in("target_contents_read","programs_executed","versions_verified")))
        return value

    def run_cli(self,*,control=None,root=DEFAULT,program_dirs=DEFAULT,observations=None,report=None,**options):
        args=["--contract",control or self.control]
        if root is DEFAULT:root=self.targets
        if root is not None:args += ["--root",root]
        if program_dirs is DEFAULT:program_dirs=[self.programs]
        if program_dirs is not None:
            for directory in program_dirs:args += ["--program-dir",directory]
        if observations is not None:args += ["--observations",observations]
        if report is not None:args += ["--report",report]
        return self.process(*args,**options)

    def generate(self,destination,**options):return self.process("--destination",destination,generator=True,**options)

    def fixture_tree(self,destination,partial=False):
        name,_=fixture_program()
        return [destination,*(destination/p for p in("inputs","programs","workspace","inputs/fictional.txt")),*(()if partial else(destination/"programs"/name,))]

    def check(self,value,wanted,**options):
        self.assertEqual(self.run_cli(control=self.metadata(value),expected=0 if wanted["status"]=="ALL_PRESENT"else 1,**options),wanted)

    def symlink(self,path,target):
        self.assertTrue(path.is_relative_to(self.work)and target.is_relative_to(self.work))
        try:path.symlink_to(target,target_is_directory=target.is_dir())
        except OSError as error:
            if os.name=="nt"and getattr(error,"winerror",None)==1314 and os.environ.get("OUTLANDS_ENVIRONMENT_REQUIRE_LINKS")!="1":self.skipTest("Native symlink privilege unavailable")
            raise AssertionError('Native symlink fixture creation failed')from error
        self.addCleanup(path.unlink)

    def test_all_present_has_exact_json_and_new_verified_report_bytes(self):
        output=self.reports/"present.json"
        self.assertEqual(self.run_cli(report=output,created=[output]),default_result())
        self.assertEqual(output.read_bytes(),(json.dumps(default_result(),indent=2,ensure_ascii=True)+"\n").encode())

    def test_unselected_root_and_program_scope_are_unknown_not_missing(self):
        self.assertEqual(self.run_cli(root=None,program_dirs=[] ,expected=1),golden([checked("document","file","UNKNOWN","ROOT_NOT_SELECTED"),
            checked("workspace","directory","UNKNOWN","ROOT_NOT_SELECTED"),checked("tool","program","UNKNOWN","PROGRAM_SEARCH_NOT_SELECTED")]))
        self.run_cli(root=self.work/"missing-root",expected=2,code="ROOT_UNAVAILABLE_OR_UNSAFE")

    def test_explicit_missing_targets_and_program_directories_are_missing_not_unknown(self):
        value=contract([requirement(path="absent.txt"),requirement("folder","directory",path="absent-folder"),requirement("tool","program",name="fictional-tool")])
        output=self.reports/"missing.json";wanted=golden([checked("document","file","MISSING","NOT_FOUND"),checked("folder","directory","MISSING","NOT_FOUND"),checked("tool","program","MISSING","PROGRAM_NOT_FOUND")])
        self.check(value,wanted,program_dirs=[self.work/"missing-programs"],report=output,created=[output]);self.assertEqual(json.loads(output.read_bytes()),wanted)
        self.assertFalse((self.work/"missing-programs").exists())

    def test_operator_true_false_and_absent_remain_unknown_in_declaration_order(self):
        rows=[requirement("reported_true","observation"),requirement("reported_false","observation"),requirement("not_supplied","observation")]
        obs=self.metadata(dict(schema_version=1,observations=[dict(id="reported_false",satisfied=False),dict(id="reported_true",satisfied=True)]))
        self.check(contract(rows),golden([checked("reported_true","observation","UNKNOWN","OPERATOR_REPORTED_TRUE_UNVERIFIED"),
            checked("reported_false","observation","UNKNOWN","OPERATOR_REPORTED_FALSE_UNVERIFIED"),checked("not_supplied","observation","UNKNOWN","OBSERVATION_NOT_SUPPLIED")]),observations=obs)

    def test_only_explicit_program_directories_and_static_suffixes_are_used(self):
        self.environment["PATH"]=str(self.programs);self.environment["PATHEXT"]=".custom"
        value=contract([requirement("tool","program",name="fictional-tool")])
        self.check(value,golden([checked("tool","program","UNKNOWN","PROGRAM_SEARCH_NOT_SELECTED")]),program_dirs=[])
        empty=self.work/"empty-programs";empty.mkdir()
        self.check(value,golden([checked("tool","program","MISSING","PROGRAM_NOT_FOUND")]),program_dirs=[empty])
        custom=empty/"fictional-tool.custom";custom.write_bytes(b"FICTIONAL_PROGRAM_NEVER_RUN")
        if os.name!="nt":custom.chmod(0o700)
        self.check(value,golden([checked("tool","program","MISSING","PROGRAM_NOT_FOUND")]),program_dirs=[empty])

    def test_target_file_directory_type_mismatches_are_unknown_without_body_read(self):
        value=contract([requirement(path="workspace"),requirement("folder","directory",path="inputs/fictional.txt")])
        self.check(value,golden([checked("document","file","UNKNOWN","TARGET_TYPE_MISMATCH"),checked("folder","directory","UNKNOWN","TARGET_TYPE_MISMATCH")]))

    def test_contract_ids_shapes_paths_and_program_names_are_strict(self):
        for value in(None,[],{},dict(contract(),schema_version=True),dict(contract(),private="FICTIONAL_PRIVATE_VALUE")):
            self.run_cli(control=self.metadata(value),expected=2,code="CONTRACT_SCHEMA_INVALID")
        for row,code in [({},"REQUIREMENT_ID_INVALID"),(requirement("Upper",path="inputs/fictional.txt"),"REQUIREMENT_ID_INVALID"),
                         (requirement(kind="module"),"REQUIREMENT_KIND_INVALID"),(requirement(path="inputs/fictional.txt",execute=True),"REQUIREMENT_SCHEMA_INVALID"),
                         (requirement(path="../escape"),"REQUIREMENT_PATH_INVALID"),(requirement(path="con.txt"),"REQUIREMENT_PATH_INVALID"),
                         (requirement("tool","program",name="some/path"),"PROGRAM_NAME_INVALID")]:
            self.run_cli(control=self.metadata(contract([row])),expected=2,code=code)
        self.run_cli(control=self.metadata(contract([requirement(path="x"),requirement(path="y")])),expected=2,code="DUPLICATE_REQUIREMENT_ID")

    def test_observation_schema_ids_boolean_types_and_duplicates_are_strict(self):
        control=self.metadata(contract([requirement("review","observation")]))
        samples=[({},"OBSERVATIONS_SCHEMA_INVALID"),(dict(schema_version=True,observations=[]),"OBSERVATIONS_SCHEMA_INVALID"),
                 (dict(schema_version=1,observations=[dict(id="review",satisfied="true")]),"OBSERVATION_VALUE_INVALID"),
                 (dict(schema_version=1,observations=[dict(id="other",satisfied=True)]),"OBSERVATION_ID_NOT_DECLARED"),
                 (dict(schema_version=1,observations=[dict(id="review",satisfied=True),dict(id="review",satisfied=False)]),"DUPLICATE_OBSERVATION_ID"),
                 (dict(schema_version=1,observations=[dict(id="review",satisfied=True,hostname="FICTIONAL_PRIVATE_HOST")]),"OBSERVATION_SCHEMA_INVALID")]
        for value,code in samples:self.run_cli(control=control,observations=self.metadata(value),expected=2,code=code)

    def test_128_requirements_and_16_explicit_directories_have_exact_count_limits(self):
        rows=[requirement("file_"+str(index),path="inputs/fictional.txt")for index in range(128)]
        self.check(contract(rows),golden([checked(row["id"],"file")for row in rows]))
        for value in(contract([]),contract(rows+[requirement("extra",path="inputs/fictional.txt")])):
            self.run_cli(control=self.metadata(value),expected=2,code="CONTRACT_SCHEMA_INVALID")
        dirs=[self.work/("missing-"+str(index))for index in range(16)]
        value=contract([requirement("tool","program",name="fictional-tool")])
        self.check(value,golden([checked("tool","program","MISSING","PROGRAM_NOT_FOUND")]),program_dirs=dirs)
        self.run_cli(program_dirs=dirs+[self.work/"extra"],expected=2,code="PROGRAM_DIRECTORIES_INVALID")
        self.run_cli(program_dirs=[self.programs,self.programs],expected=2,code="DUPLICATE_PROGRAM_DIRECTORY")

    def test_each_control_exact_64_kib_bom_and_strict_json_errors(self):
        observed=contract([requirement("review","observation")]);control=self.metadata(observed)
        for role,value in(("contract",contract()),("observations",dict(schema_version=1,observations=[]))):
            raw=b"\xef\xbb\xbf"+encoded(value);exact=raw+b" "*(65536-len(raw));path=self.metadata(raw=exact)
            if role=="contract":self.assertEqual(self.run_cli(control=path),default_result())
            else:self.check(observed,golden([checked("review","observation","UNKNOWN","OBSERVATION_NOT_SUPPLIED")]),observations=path)
            path=self.metadata(raw=exact+b" ");options=dict(control=path)if role=="contract"else dict(control=control,observations=path)
            self.run_cli(**options,expected=2,code="INPUT_SIZE_LIMIT")
        for raw,code in[(b'{"x":1,"x":2}',"DUPLICATE_JSON_KEY"),(b'{"x":NaN}',"NONSTANDARD_JSON"),(b"\xff","INPUT_OR_REPORT_FAILED"),(b"{","INPUT_OR_REPORT_FAILED")]:
            self.run_cli(control=self.metadata(raw=raw),expected=2,code=code)

    def test_metadata_checks_never_open_targets_programs_or_network_or_enumerate(self):
        script=self.wrapper("""
            original_check=tool.check_contract
            def guarded(*args,**kwargs):
                def forbidden(*args,**kwargs):raise AssertionError('Target/program/body/network/enumeration activity attempted')
                with ExitStack()as stack:
                    for obj,name in[(os,'open'),(os,'scandir'),(os,'listdir'),(builtins,'open'),(Path,'open'),(socket,'socket'),(socket,'getaddrinfo'),(subprocess,'Popen'),(runpy,'run_path'),(tool,'_windows')]:
                        stack.enter_context(mock.patch.object(obj,name,side_effect=forbidden))
                    return original_check(*args,**kwargs)
            tool.check_contract=guarded
            """,prelude="import builtins,socket,subprocess,runpy\nfrom contextlib import ExitStack\nfrom unittest import mock\n")
        self.assertEqual(self.run_cli(script=script),default_result())

    def test_probe_and_between_probe_time_budget_exhaustion_remain_unknown(self):
        for mode in("count","time"):
            script=self.wrapper("tool.MAX_TARGET_PROBES=0\n"if mode=="count"else"calls=[]\ndef clock():\n    calls.append(True)\n    return 0 if len(calls)==1 else 6\ntool.time.monotonic=clock\n")
            self.assertEqual(self.run_cli(script=script,expected=1),golden([checked("document","file","UNKNOWN","PROBE_BUDGET_EXHAUSTED"),
                checked("workspace","directory","UNKNOWN","PROBE_BUDGET_EXHAUSTED"),checked("tool","program","UNKNOWN","PROBE_BUDGET_EXHAUSTED")]))

    def test_report_boundaries_cover_source_root_program_directories_and_missing_scope(self):
        for output in(self.runtime/"report.json",self.targets/"report.json",self.programs/"report.json"):
            self.run_cli(report=output,expected=2,code="REPORT_MUST_BE_EXTERNAL")
        missing=self.work/"missing-programs"
        self.run_cli(program_dirs=[missing],report=missing/"report.json",expected=2,code="REPORT_MUST_BE_EXTERNAL")
        output=self.reports/"missing-scope.json";wanted=golden([checked("document","file"),checked("workspace","directory"),checked("tool","program","MISSING","PROGRAM_NOT_FOUND")])
        self.assertEqual(self.run_cli(program_dirs=[missing],report=output,created=[output],expected=1),wanted)
        self.assertEqual(json.loads(output.read_bytes()),wanted);self.assertFalse(missing.exists())

    def test_existing_report_controls_and_missing_parent_never_overwrite_or_create_parents(self):
        output=self.reports/"prior.json";output.write_bytes(b"Fictional prior capture\n")
        for path in(output,self.control,self.reports):self.run_cli(report=path,expected=2,code="INPUT_OR_REPORT_FAILED")
        self.run_cli(report=self.reports/"missing"/"report.json",expected=2,code="REPORT_PARENT_UNAVAILABLE_OR_UNSAFE")

    def test_short_zero_flush_readback_failures_retain_unconfirmed_new_reports(self):
        for mode in("short","zero","flush","readback"):
            output=self.reports/(mode+".json")
            script=self.wrapper("""
                original_write,original_sync,original_read=os.write,os.fsync,tool._read_control_bytes
                def written(fd,block):
                    events.append(fd);return 0 if MODE=='zero'else original_write(fd,block[:3]if MODE=='short'else block)
                def synced(fd):
                    if MODE=='flush':raise OSError('FICTIONAL_PRIVATE_FLUSH')
                    return original_sync(fd)
                def readback(path,*args,**kwargs):
                    if MODE=='readback'and Path(path)==Path(OUTPUT_VALUE):return b'wrong'
                    return original_read(path,*args,**kwargs)
                os.write,os.fsync,tool._read_control_bytes=written,synced,readback
                """.replace("MODE",repr(mode)).replace("OUTPUT_VALUE",repr(str(output))),postlude="""
                assert events
                for fd in events:
                    try:os.fstat(fd)
                    except OSError as error:assert error.errno==9
                    else:raise AssertionError('Report descriptor remained open')
                """)
            code={"zero":"REPORT_WRITE_FAILED","flush":"INPUT_OR_REPORT_FAILED","readback":"REPORT_VERIFY_FAILED"}.get(mode)
            observed=self.run_cli(script=script,report=output,created=[output],expected=0 if mode=="short"else 2,code=code)
            if mode=="short":self.assertEqual(observed,default_result())
            if mode=="zero":self.assertEqual(output.read_bytes(),b"")
            else:self.assertEqual(json.loads(output.read_bytes()),default_result())
            self.run_cli(report=output,expected=2,code="INPUT_OR_REPORT_FAILED")

    def test_controlled_short_read_failure_and_input_change_release_descriptors(self):
        for mode in("short","read","identity"):
            script=self.wrapper("""
                from types import SimpleNamespace
                original_open,original_read,original_fstat=os.open,os.read,os.fstat
                descriptors=[]
                def opened(*args,**kwargs):
                    fd=original_open(*args,**kwargs);descriptors.append(fd);return fd
                def read(fd,amount):
                    if MODE=='read':raise OSError('FICTIONAL_PRIVATE_READ')
                    return original_read(fd,min(amount,3)if MODE=='short'else amount)
                def changed(fd):
                    info=original_fstat(fd);events.append(True)
                    fields={name:getattr(info,name)for name in dir(info)if name.startswith('st_')and not callable(getattr(info,name))}
                    fields['st_ino']+=1
                    return SimpleNamespace(**fields)
                os.open,os.read=opened,read
                if MODE=='identity':os.fstat=changed
                """.replace("MODE",repr(mode)),postlude="""
                assert descriptors
                for fd in descriptors:
                    try:os.fstat(fd)
                    except OSError as error:assert error.errno==9
                    else:raise AssertionError('Input descriptor remained open')
                """)
            code="INPUT_OR_REPORT_FAILED"if mode=="read"else"INPUT_CHANGED"
            observed=self.run_cli(script=script,expected=0 if mode=="short"else 2,code=code)
            if mode=="short":self.assertEqual(observed,default_result())

    def test_checker_help_version_and_generator_help_have_fixed_argument_errors(self):
        self.assertIn("0.1.0",self.process("--version",json_output=False));self.assertIn("--contract",self.process("--help",json_output=False))
        self.assertIn("--destination",self.process("--help",generator=True,json_output=False))
        self.process("--unknown","FICTIONAL_PRIVATE_DETAIL",expected=2,code="ARGUMENTS_INVALID")
        self.process("--version",generator=True,expected=2,code="INVALID_ARGUMENTS")

    def test_seeded_metadata_outcome_oracle_preserves_requirement_order(self):
        selected=random.Random(348)
        for iteration in range(8):
            definitions=[(requirement("present",path="inputs/fictional.txt"),checked("present","file")),
                (requirement("missing",path="absent"),checked("missing","file","MISSING","NOT_FOUND")),
                (requirement("wrong","directory",path="inputs/fictional.txt"),checked("wrong","directory","UNKNOWN","TARGET_TYPE_MISMATCH")),
                (requirement("reported","observation"),checked("reported","observation","UNKNOWN","OBSERVATION_NOT_SUPPLIED"))]
            selected.shuffle(definitions);self.check(contract([row for row,result in definitions]),golden([result for row,result in definitions]))

    def test_checker_standalone_and_collection_layouts_protect_exact_source_boundaries(self):
        output=self.reports/"standalone.json";self.assertEqual(self.run_cli(report=output,created=[output]),default_result())
        collection=self.work/"collection";directory=collection/"tools/environment-contract-checker";directory.mkdir(parents=True);(directory/"examples").mkdir()
        for name,data in self.runtime_bytes.items():(directory/name).write_bytes(data)
        docs=collection/"docs";docs.mkdir()
        self.run_cli(report=docs/"forbidden.json",script=directory/"environment_check.py",expected=2,code="REPORT_MUST_BE_EXTERNAL")
        self.run_cli(report=directory/"forbidden.json",script=directory/"environment_check.py",expected=2,code="REPORT_MUST_BE_EXTERNAL")
        output=self.reports/"collection.json";self.assertEqual(self.run_cli(report=output,script=directory/"environment_check.py",created=[output]),default_result())

    def test_generator_creates_exact_new_fixture_bytes_and_never_executes_program(self):
        destination=self.work/"generated";self.generate(destination,created=self.fixture_tree(destination))
        name,raw=fixture_program();self.assertEqual((destination/"inputs/fictional.txt").read_bytes(),b"Fictional prerequisite input. No user records.\n")
        self.assertEqual((destination/"programs"/name).read_bytes(),raw)
        if os.name!="nt":self.assertEqual((destination/"programs"/name).stat().st_mode&0o777,0o700)
        self.assertEqual(self.run_cli(root=destination,program_dirs=[destination/"programs"]),default_result())

    def test_generator_existing_destinations_both_source_layouts_and_portable_paths_are_preserved(self):
        for destination in(self.control,self.targets):self.generate(destination,expected=2,code="FIXTURE_REFUSED_OR_FAILED")
        self.generate(self.runtime/"forbidden",expected=2,code="EXTERNAL_DESTINATION_REQUIRED")
        collection=self.work/"collection";directory=collection/"tools/environment-contract-checker";directory.mkdir(parents=True);(directory/"examples").mkdir()
        for name,data in self.runtime_bytes.items():(directory/name).write_bytes(data)
        docs=collection/"docs";docs.mkdir()
        self.generate(docs/"forbidden",script=directory/"examples/make_fixture.py",expected=2,code="EXTERNAL_DESTINATION_REQUIRED")
        destination=self.work/"collection-generated";self.generate(destination,script=directory/"examples/make_fixture.py",created=self.fixture_tree(destination))

        self.generate("relative",expected=2,code="ABSOLUTE_LOCAL_DESTINATION_REQUIRED")
        self.generate(self.work/"missing"/"new",expected=2,code="FIXTURE_REFUSED_OR_FAILED")
        for spelling in(str(self.work/"new")+".",str(self.work/"new")+" "):
            self.generate(spelling,expected=2,code="PORTABLE_DESTINATION_REQUIRED")

    def test_generator_partial_new_output_is_retained_and_retry_never_replaces_it(self):
        destination=self.work/"partial-generated"
        script=self.wrapper("def failed(*args,**kwargs):raise OSError('FICTIONAL_PRIVATE_FLUSH')\nos.fsync=failed\n",generator=True)
        self.generate(destination,script=script,created=self.fixture_tree(destination,partial=True),expected=2,code="FIXTURE_REFUSED_OR_FAILED")
        self.assertEqual((destination/"inputs/fictional.txt").read_bytes(),b"Fictional prerequisite input. No user records.\n")
        self.generate(destination,expected=2,code="FIXTURE_REFUSED_OR_FAILED")

    def test_native_hardlinked_control_target_and_report_preserve_original_bytes(self):
        link=self.controls/"hardlink.json"
        try:os.link(self.control,link)
        except OSError as error:raise AssertionError('Native hardlink fixture creation failed')from error
        self.run_cli(expected=2,code="INPUT_UNAVAILABLE_OR_UNSAFE");link.unlink()
        targetlink=self.work/"retained-target"
        try:os.link(self.target,targetlink)
        except OSError as error:raise AssertionError('Native hardlink fixture creation failed')from error
        self.assertEqual(self.run_cli(expected=1),golden([checked("document","file","UNSAFE","LINK_COUNT_UNSUPPORTED"),checked("workspace","directory"),checked("tool","program")]))
        output=self.reports/"hardlink.json";retained=self.reports/"retained.json";retained.write_bytes(b"Fictional retained\n")
        try:os.link(retained,output)
        except OSError as error:raise AssertionError('Native hardlink fixture creation failed')from error
        self.run_cli(report=output,expected=2,code="INPUT_OR_REPORT_FAILED")

    def test_native_symlink_input_leaf_and_dangling_are_refused(self):
        link=self.controls/"linked.json";self.symlink(link,self.control);self.run_cli(control=link,expected=2,code="INPUT_UNAVAILABLE_OR_UNSAFE")
        absent=self.controls/"absent.json";dangling=self.controls/"dangling.json";self.symlink(dangling,absent)
        self.run_cli(control=dangling,expected=2,code="INPUT_UNAVAILABLE_OR_UNSAFE");self.assertFalse(absent.exists())
        moved=self.work/"retained-target";self.target.rename(moved);self.symlink(self.target,moved)
        self.assertEqual(self.run_cli(expected=1),golden([checked("document","file","UNSAFE","LINK_OR_REPARSE_UNSUPPORTED"),checked("workspace","directory"),checked("tool","program")]))

    def test_native_symlink_input_parent_is_refused(self):
        link=self.work/"linked-root";self.symlink(link,self.targets);self.run_cli(root=link,expected=2,code="ROOT_UNAVAILABLE_OR_UNSAFE")
        linked_programs=self.work/"linked-programs";self.symlink(linked_programs,self.programs)
        self.assertEqual(self.run_cli(program_dirs=[linked_programs],expected=1),golden([checked("document","file"),checked("workspace","directory"),checked("tool","program","UNSAFE","LINK_OR_REPARSE_UNSUPPORTED")]))

    def test_native_symlink_output_leaf_and_parent_preserve_reports_and_fixture(self):
        retained=self.reports/"retained.json";retained.write_bytes(b"Fictional retained\n")
        link=self.reports/"linked.json";self.symlink(link,retained);self.run_cli(report=link,expected=2,code="INPUT_OR_REPORT_FAILED")
        absent=self.reports/"absent.json";dangling=self.reports/"dangling.json";self.symlink(dangling,absent)
        # Distinct fixed guard stages may refuse; no new target may be created.
        self.run_cli(report=dangling,optional_created=[absent],expected=2,code={"INPUT_OR_REPORT_FAILED","OUTPUT_CHANGED"})
        self.assertFalse(absent.exists())
        parent=self.work/"linked-reports";self.symlink(parent,self.reports)
        self.run_cli(report=parent/"new.json",expected=2,code="REPORT_PARENT_UNAVAILABLE_OR_UNSAFE")
        self.generate(parent/"fixture",expected=2,code="ORDINARY_DIRECTORY_REQUIRED")

    @unittest.skipUnless(os.name=="nt","Native Windows junction fixture")
    def test_native_windows_junction_input_report_and_fixture_parents_are_refused(self):
        controls=self.work/"controls-junction";self.junction(controls,self.controls);self.run_cli(control=controls/self.control.name,expected=2,code="INPUT_UNAVAILABLE_OR_UNSAFE")
        targets=self.work/"targets-junction";self.junction(targets,self.targets);self.run_cli(root=targets,expected=2,code="ROOT_UNAVAILABLE_OR_UNSAFE")
        reports=self.work/"reports-junction";self.junction(reports,self.reports);self.run_cli(report=reports/"new.json",expected=2,code="REPORT_PARENT_UNAVAILABLE_OR_UNSAFE")
        self.generate(reports/"fixture",expected=2,code="ORDINARY_DIRECTORY_REQUIRED")

    @unittest.skipUnless(os.name=="nt","Native Windows alternate stream fixture")
    def test_native_windows_stream_and_control_suffix_forms_are_refused(self):
        stream=str(self.control)+":fictional"
        with open(stream,"wb")as handle:handle.write(b"Fictional private stream")
        self.assertEqual(self.run_cli(),default_result())
        for spelling in(stream,str(self.control)+".",str(self.control)+" ",str(self.control.parent)+"."+os.sep+self.control.name,str(self.control.parent)+" "+os.sep+self.control.name):
            self.run_cli(control=spelling,expected=2,code="PATH_INVALID")
        self.run_cli(report=stream,expected=2,code="STREAM_OR_URL_PATH_UNSUPPORTED")
        with open(stream,"rb")as handle:self.assertEqual(handle.read(),b"Fictional private stream")
        output=self.reports/"controlled-existing.json";output.write_bytes(b"Fictional retained report")
        script=self.wrapper("""
            from types import SimpleNamespace
            import stat
            original_lstat,original_open=Path.lstat,os.open
            selected=Path(OUTPUT_VALUE)
            def observed(path,*args,**kwargs):
                if path==selected:
                    events.append(True)
                    return SimpleNamespace(st_mode=stat.S_IFLNK|0o600,st_file_attributes=0x400)
                return original_lstat(path,*args,**kwargs)
            def opened(path,*args,**kwargs):
                if Path(path)==selected:raise AssertionError('Observed reparse report leaf reached CRT create')
                return original_open(path,*args,**kwargs)
            Path.lstat,os.open=observed,opened
            """.replace("OUTPUT_VALUE",repr(str(output))),postlude="assert events and status==2\n")
        self.run_cli(report=output,script=script,expected=2,code="INPUT_OR_REPORT_FAILED")

    @unittest.skipUnless(os.name!="nt","Native POSIX FIFO fixture")
    def test_native_posix_fifo_input_is_refused_before_open(self):
        fifo=self.controls/"fifo.json"
        try:os.mkfifo(fifo,0o600)
        except OSError as error:raise AssertionError('Native FIFO fixture creation failed')from error
        self.run_cli(control=fifo,expected=2,code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name=="nt","Native Windows interrupt fixture")
    def test_native_windows_interruption_is_fixed_and_releases_handles(self):
        script=self.wrapper("def interrupted(*args,**kwargs):raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT')\nos.read=interrupted\n")
        self.run_cli(script=script,expected=130,code="INPUT_OR_REPORT_INTERRUPTED")

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
