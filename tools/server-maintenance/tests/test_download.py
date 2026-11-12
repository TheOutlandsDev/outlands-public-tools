"""Copied-runtime CLI consumers of fictional maintenance declarations; never server control."""
import calendar
import ctypes
from ctypes import wintypes
from datetime import date, timedelta
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import socket
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("maintenance.py", "maintenance_windows.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
ERROR = dict(status="ERROR", code="PLAN_INPUT_INVALID", execution_performed=False)
READY = dict(target_verified=True, new_instance=True, fresh_log_markers=True, probe_succeeded=True)
RESTART = ["notify", "request_save", "request_stop", "verify_stopped", "refresh_backup",
           "verify_backup_pin", "start", "verify_new_instance", "verify_fresh_readiness"]
PROBE = r'''
import importlib.metadata,json,os,socket,subprocess,sys
from pathlib import Path
assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(base))
import maintenance as m
assert Path(m.__file__).resolve()==base/'maintenance.py'
assert Path(m._windows().__file__).resolve()==base/'maintenance_windows.py'
kind=sys.argv[2]
if kind=='short':
 original=os.read
 def short(fd,amount):return original(fd,min(amount,3))
 os.read=short
elif kind=='early':
 values=iter((b'{}',b''))
 def early(*args):return next(values,b'')
 os.read=early
elif kind=='growth':
 original=os.read;events=[]
 def grow(fd,amount):
  block=original(fd,amount)
  if block and not events:
   with Path(sys.argv[5]).open('ab') as handle:handle.write(b' '*m.INPUT_LIMIT)
   events.append(True)
  return block
 os.read=grow
elif kind=='mutation':
 original=os.read;events=[]
 def mutate(fd,amount):
  block=original(fd,amount)
  if block and not events:
   path=Path(sys.argv[5]);data=path.read_bytes();changed=data.replace(b'"players": 0',b'"players": 1')
   assert changed!=data and len(changed)==len(data)
   stamp=path.stat().st_mtime_ns;path.write_bytes(changed);os.utime(path,ns=(stamp,stamp+1_000_000));events.append(True)
  return block
 os.read=mutate
elif kind=='read_failure':
 def failure(*args):raise OSError('FICTIONAL_PRIVATE_DETAIL')
 os.read=failure
elif kind=='interrupt':
 def interrupt(*args):raise KeyboardInterrupt
 os.read=interrupt
elif kind=='no_external':
 def refuse(*args,**kwargs):raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
 socket.socket=refuse;socket.create_connection=refuse;subprocess.Popen=refuse;os.system=refuse;os.scandir=refuse
elif kind=='calendar_without_inputs':
 def refuse(*args,**kwargs):raise AssertionError('CALENDAR_EXTERNAL_ACTION')
 m.load_request=refuse;socket.socket=refuse;subprocess.Popen=refuse;os.system=refuse
elif kind=='nul':
 assert m.main(['plan','--input','FICTIONAL\x00PRIVATE'])==2
 raise SystemExit(0)
elif kind=='library_interrupt':
 import errno
 path=Path(sys.argv[5]);before=path.read_bytes();observed=[]
 def interrupt(fd,amount):
  observed.append(fd)
  raise KeyboardInterrupt
 os.read=interrupt
 try:m.load_request(path)
 except KeyboardInterrupt:pass
 else:raise AssertionError('LIBRARY_INTERRUPT_MUST_PROPAGATE')
 assert len(observed)==1, 'INPUT_DESCRIPTOR_NOT_OBSERVED'
 try:os.fstat(observed[0])
 except OSError as error:assert error.errno==errno.EBADF, 'CLOSED_DESCRIPTOR_ERROR_DIFFERS'
 else:raise AssertionError('INTERRUPTED_INPUT_DESCRIPTOR_STILL_OPEN')
 assert path.read_bytes()==before
 print(json.dumps(dict(status='LIBRARY_INTERRUPT_PROPAGATED',execution_performed=False)))
 raise SystemExit(0)
elif kind=='posix_cli_interrupt':
 assert os.name!='nt'
 def interrupt(*args):raise KeyboardInterrupt
 os.read=interrupt
 try:m.main(sys.argv[3:])
 except KeyboardInterrupt:pass
 else:raise AssertionError('POSIX_CLI_INTERRUPT_MUST_PROPAGATE')
 print(json.dumps(dict(status='POSIX_INTERRUPT_PROPAGATED',execution_performed=False)))
 raise SystemExit(0)
elif kind=='loader_exponent':
 value=m.load_request(sys.argv[3]);assert value['x']==float('inf')
 print(json.dumps(dict(status='EXPONENT_LOADER_PRESERVED',execution_performed=False)))
 raise SystemExit(0)
elif kind=='oracle':
 from datetime import date,timedelta
 for row in json.loads(sys.argv[3]):
  y,mo,wd,off,anchor,followup,nxt=row
  actual=m.schedule_window(y,mo,wd,off)
  assert actual==dict(anchor=anchor,followup=followup,next_anchor=nxt,weekday=wd,time_of_day='operator_selected',timezone='operator_selected',execution_performed=False)
 print(json.dumps(dict(status='CALENDAR_ORACLE_MATCH',cases=len(json.loads(sys.argv[3])),execution_performed=False)))
 raise SystemExit(0)
else:raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
raise SystemExit(m.main(sys.argv[3:]))
'''


def request(**changes):
    value = dict(action="restart", state="running", players=0, observation_age_seconds=30,
                 maximum_age_seconds=300, cooldown_remaining_seconds=0, previous_attempt="completed",
                 target_verified=True, backup_verified=True)
    value.update(changes)
    return value


def result(status, action="restart", steps=()):
    return dict(status=status, action=action, steps=list(steps), execution_performed=False)


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="maintenance-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.copy = self.work / "copied runtime"
        self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            data = (ROOT / name).read_bytes()
            (self.copy / name).write_bytes(data)
            self.pins[name] = hashlib.sha256(data).hexdigest()
        self.source = self.work / "fictional request.json"
        self.write(request())
        self.addCleanup(self.runtime_preserved)

    def runtime_preserved(self):
        self.assertEqual({p.name for p in self.copy.iterdir()}, set(RUNTIME))
        self.assertEqual({n: hashlib.sha256((self.copy / n).read_bytes()).hexdigest() for n in RUNTIME}, self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])

    def write(self, value=None, raw=None, path=None):
        path = self.source if path is None else path
        path.write_bytes(json.dumps(request() if value is None else value, ensure_ascii=True).encode()
                         if raw is None else raw)
        return path

    def snapshot(self):
        rows = {}
        def visit(folder):
            for p in folder.iterdir():
                relative = p.relative_to(self.work).as_posix()
                if p.is_symlink() or getattr(p, "is_junction", lambda: False)():
                    rows[relative] = ("LINK",)
                elif p.is_dir():
                    rows[relative] = ("DIRECTORY",)
                    visit(p)
                else:
                    info = p.stat()
                    if stat.S_ISREG(info.st_mode):
                        rows[relative] = (hashlib.sha256(p.read_bytes()).hexdigest(), info.st_size,
                                          info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink)
                    else:
                        rows[relative] = ("SPECIAL", info.st_mode)
        visit(self.work)
        return rows

    def call(self, args=None, *, code=0, probe=None, wanted=None, preserve=True, json_output=True):
        args = ["plan", "--input", str(self.source)] if args is None else list(map(str, args))
        before = self.snapshot()
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        command = ([sys.executable, "-I", "-B", "-W", "error", "-c", PROBE, str(self.copy), probe]
                   if probe else [sys.executable, "-I", "-B", "-W", "error", str(self.copy / "maintenance.py")])
        done = subprocess.run([*command, *args], cwd=self.work, env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        self.assertEqual(done.returncode, code, (done.stdout + done.stderr).decode(errors="replace")[:2000])
        self.assertEqual(done.stderr, b"")
        for private in (str(self.work).encode(), b"FICTIONAL_PRIVATE", b"Traceback"):
            self.assertNotIn(private, done.stdout)
        if preserve:
            self.assertEqual(before, self.snapshot())
        self.runtime_preserved()
        if not json_output:
            return done.stdout
        self.assertEqual(len(done.stdout.splitlines()), 1)
        value = json.loads(done.stdout)
        self.assertIs(value["execution_performed"], False)
        if wanted is not None:
            self.assertEqual(value, wanted)
            sorted_output = probe not in {"nul", "library_interrupt", "posix_cli_interrupt", "loader_exponent", "oracle"} and code == 0
            self.assertEqual(done.stdout, json.dumps(wanted, sort_keys=sorted_output).encode() + NEWLINE)
        return value

    def reject(self, args=None, **options):
        return self.call(args, code=2, wanted=ERROR, **options)

    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and error.winerror == 1314:
                if os.environ.get("OUTLANDS_MAINTENANCE_REQUIRE_LINKS") == "1":
                    self.fail("APPLICABLE_NATIVE_SYMLINK_REQUIRED")
                self.skipTest("Native symlink privilege unavailable")
            raise

    def test_static_help_for_all_commands_is_private_and_side_effect_free(self):
        for args in (["--help"], ["calendar", "--help"], ["plan", "--help"], ["readiness", "--help"]):
            text = self.call(args, json_output=False)
            self.assertIn(b"maintenance.py", text)
            self.assertIn(b"--help", text)

    def test_unknown_version_commands_and_arguments_use_exact_fixed_errors(self):
        for args in ([], ["--version"], ["FICTIONAL_PRIVATE_COMMAND"], ["plan", "--input"],
                     ["calendar", "--year", "FICTIONAL_PRIVATE_YEAR"], ["readiness", "--unknown"]):
            self.reject(args)

    def test_calendar_example_has_exact_dates_and_operator_selected_time(self):
        self.call(["calendar", "--year", 2026, "--month", 12, "--weekday", 3, "--offset-days", 14],
                  wanted=dict(anchor="2026-12-03", followup="2026-12-17", next_anchor="2027-01-07",
                              weekday=3, time_of_day="operator_selected", timezone="operator_selected",
                              execution_performed=False), probe="calendar_without_inputs")

    def test_calendar_seeded_independent_date_oracle_matches_copied_library(self):
        rng = random.Random(731)
        rows = []
        for _ in range(160):
            year, month, weekday, offset = rng.randrange(1990, 2041), rng.randrange(1, 13), rng.randrange(7), rng.randrange(1, 20)
            days = [day for day in range(1, calendar.monthrange(year, month)[1]+1)
                    if date(year, month, day).weekday() == weekday]
            anchor = date(year, month, days[0])
            ny, nm = (year+1, 1) if month == 12 else (year, month+1)
            ndays = [day for day in range(1, calendar.monthrange(ny, nm)[1]+1)
                     if date(ny, nm, day).weekday() == weekday]
            next_anchor = date(ny, nm, ndays[0])
            self.assertLess(anchor + timedelta(days=offset), next_anchor)
            rows.append([year, month, weekday, offset, anchor.isoformat(),
                         (anchor+timedelta(days=offset)).isoformat(), next_anchor.isoformat()])
        self.call([json.dumps(rows)], probe="oracle",
                  wanted=dict(status="CALENDAR_ORACLE_MATCH", cases=160, execution_performed=False))

    def test_calendar_bounds_and_overlap_use_fixed_cli_failure(self):
        for year, month, weekday, offset in ((0, 1, 0, 1), (9999, 1, 0, 1), (2026, 0, 0, 1),
                (2026, 13, 0, 1), (2026, 1, -1, 1), (2026, 1, 7, 1), (2026, 1, 0, 0),
                (2026, 1, 0, 28), (2021, 2, 0, 28)):
            self.reject(["calendar", "--year", year, "--month", month, "--weekday", weekday, "--offset-days", offset])

    def test_running_restart_has_the_complete_ordered_checklist(self):
        self.call(wanted=result("PLAN_READY", steps=RESTART))

    def test_stopped_restart_has_only_backup_start_readiness_checklist(self):
        self.write(request(state="stopped"))
        self.call(wanted=result("PLAN_READY", steps=["verify_backup_pin", "start", "verify_new_instance", "verify_fresh_readiness"]))

    def test_start_and_stop_have_exact_no_action_and_action_results(self):
        cases = [(dict(action="start"), result("NO_ACTION", "start")),
                 (dict(action="start", state="stopped"), result("PLAN_READY", "start", ["start", "verify_new_instance", "verify_fresh_readiness"])),
                 (dict(action="stop", state="stopped"), result("NO_ACTION", "stop")),
                 (dict(action="stop"), result("PLAN_READY", "stop", ["notify", "request_save", "request_stop", "verify_stopped"]))]
        for changes, wanted in cases:
            self.write(request(**changes)); self.call(wanted=wanted)

    def test_backup_and_update_require_stopped_state_and_exact_steps(self):
        for action, steps in (("backup", ["snapshot_private_state", "verify_snapshot"]),
                              ("update", ["verify_backup_pin", "apply_reviewed_update", "verify_updated_files", "record_result"])):
            self.write(request(action=action)); self.call(wanted=result("STOP_REQUIRED", action))
            self.write(request(action=action, state="stopped")); self.call(wanted=result("PLAN_READY", action, steps))

    def test_lifecycle_blocking_precedence_remains_exact_without_execution(self):
        cases = [(dict(previous_attempt="incomplete", players=3), "REVIEW_PREVIOUS_ATTEMPT"),
                 (dict(previous_attempt="unknown"), "REVIEW_PREVIOUS_ATTEMPT"),
                 (dict(target_verified=False, state="unknown"), "TARGET_NOT_VERIFIED"),
                 (dict(state="unknown"), "STATE_NOT_ESTABLISHED"),
                 (dict(observation_age_seconds=None, players=None), "OBSERVATION_STALE_OR_MISSING"),
                 (dict(observation_age_seconds=301), "OBSERVATION_STALE_OR_MISSING"),
                 (dict(players=None), "PLAYER_COUNT_UNKNOWN"),
                 (dict(state="stopped", players=1, cooldown_remaining_seconds=10), "OBSERVATION_INCONSISTENT"),
                 (dict(cooldown_remaining_seconds=1, players=1), "COOLDOWN_PENDING"),
                 (dict(players=1), "PLAYERS_PRESENT"),
                 (dict(backup_verified=False), "VERIFIED_BACKUP_REQUIRED")]
        for changes, status in cases:
            self.write(request(**changes)); self.call(wanted=result(status))

    def test_plan_exact_field_set_enum_and_boolean_types_are_required(self):
        values = [request(extra=True), {k:v for k,v in request().items() if k!="state"},
                  request(action="launch"), request(state="pending"), request(previous_attempt="retry"),
                  request(action=1), request(state=None), request(previous_attempt=False),
                  request(target_verified=1), request(backup_verified="true")]
        for value in values:
            self.write(value); self.reject()

    def test_integer_bounds_and_boolean_integer_refusal_remain_strict(self):
        for field, low, high in (("players", 0, 100000), ("observation_age_seconds", 0, 86400),
                                ("maximum_age_seconds", 1, 3600), ("cooldown_remaining_seconds", 0, 86400)):
            for invalid in (True, low-1, high+1, 1.5, "1"):
                self.write(request(**{field:invalid})); self.reject()
        self.write(request(players=100000, observation_age_seconds=86400, maximum_age_seconds=3600,
                           cooldown_remaining_seconds=86400))
        self.call(wanted=result("OBSERVATION_STALE_OR_MISSING"))
        self.write(request(observation_age_seconds=300))
        self.call(wanted=result("PLAN_READY", steps=RESTART))

    def test_all_sixteen_readiness_combinations_are_declarations_only(self):
        names = sorted(READY)
        for bits in range(16):
            value = {name: bool(bits & (1 << index)) for index, name in enumerate(names)}
            self.write(value)
            missing = sorted(name for name in names if not value[name])
            self.call(["readiness", "--input", self.source],
                      wanted=dict(status="NOT_ESTABLISHED" if missing else "OBSERVATIONS_COMPLETE",
                                  missing=missing, execution_performed=False))

    def test_readiness_rejects_extra_missing_and_non_boolean_fields(self):
        values = [dict(READY, extra=True), {k:v for k,v in READY.items() if k!="new_instance"}]
        for invalid in (0, 1, "true", None, []):
            values.append(dict(READY, target_verified=invalid))
        for value in values:
            self.write(value); self.reject(["readiness", "--input", self.source])

    def test_exact_64_kib_plan_is_accepted_and_one_extra_byte_refused(self):
        base = json.dumps(request()).encode()
        self.write(raw=base+b" "*(65536-len(base)))
        self.assertEqual(self.source.stat().st_size, 65536)
        self.call(wanted=result("PLAN_READY", steps=RESTART))
        self.write(raw=self.source.read_bytes()+b" ")
        self.reject()

    def test_bom_whitespace_and_unicode_json_preserve_original_bytes(self):
        raw = b"\xef\xbb\xbf \r\n"+json.dumps(request(), ensure_ascii=True).encode()+b"\r\n\t"
        self.write(raw=raw); self.call(wanted=result("PLAN_READY", steps=RESTART))
        self.write(raw=b'\xef\xbb\xbf{"x":"\\u2603"}')
        self.reject()
        self.assertEqual(self.source.read_bytes(), b'\xef\xbb\xbf{"x":"\\u2603"}')

    def test_duplicate_constants_depth_and_exponent_planner_rules_are_fixed(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":{"y":1,"y":2}}', b'{"x":NaN}', b'{"x":Infinity}',
                    b'{"x":-Infinity}', b"["*2000+b"0"+b"]"*2000):
            self.write(raw=raw); self.reject()
        self.write(raw=b'{"x":1e999}')
        self.call([self.source], probe="loader_exponent",
                  wanted=dict(status="EXPONENT_LOADER_PRESERVED", execution_performed=False))
        self.reject()

    def test_empty_malformed_utf8_and_scalar_inputs_use_fixed_failure(self):
        for raw in (b"", b"{FICTIONAL_PRIVATE_DETAIL", b"\xffPRIVATE", b"null", b"[]", b"true", b"1", b'"fictional"'):
            self.write(raw=raw)
            for command in ("plan", "readiness"):
                self.reject([command, "--input", self.source])

    def test_input_filename_never_imports_or_executes_its_contents(self):
        alternate = self.work/"fictional.py"; self.write(path=alternate)
        self.call(["plan", "--input", alternate], wanted=result("PLAN_READY", steps=RESTART))
        alternate.write_bytes(b"raise RuntimeError('FICTIONAL_PRIVATE_EXECUTED')")
        self.reject(["plan", "--input", alternate])
        self.assertEqual({p.name for p in self.copy.iterdir()}, set(RUNTIME))

    def test_relative_and_spaced_input_paths_remain_supported(self):
        self.call(["plan", "--input", self.source.name], wanted=result("PLAN_READY", steps=RESTART))
        folder = self.work/"fictional input directory"; folder.mkdir()
        path = folder/"selected plan.data"; self.write(path=path)
        self.call(["plan", "--input", Path(folder.name)/path.name], wanted=result("PLAN_READY", steps=RESTART))

    def test_missing_directory_and_nonregular_inputs_never_create_files(self):
        for path in (self.work/"missing.json", self.work/"missing parent"/"plan.json", self.work):
            for command in ("plan", "readiness"):
                self.reject([command, "--input", path])

    def test_parent_traversal_and_nul_are_fixed_failures(self):
        for command in ("plan", "readiness"):
            self.reject([command, "--input", self.work/".." /self.work.name/self.source.name])
        self.call([], probe="nul", wanted=ERROR)

    def test_native_hardlinked_inputs_remain_supported_and_unchanged(self):
        alias = self.work/"fictional hardlink.json"
        os.link(self.source, alias)
        self.assertEqual(alias.stat().st_nlink, 2)
        for command, value, wanted in (("plan", request(), result("PLAN_READY", steps=RESTART)),
                                      ("readiness", READY, dict(status="OBSERVATIONS_COMPLETE", missing=[], execution_performed=False))):
            self.write(value)
            self.call([command, "--input", alias], wanted=wanted)
            self.assertEqual(alias.read_bytes(), self.source.read_bytes())

    def test_native_symlink_input_leaf_and_parent_are_refused(self):
        before = self.source.read_bytes()
        leaf = self.work/"fictional symlink.json"; self.symlink(leaf, self.source)
        target = self.work/"actual input directory"; target.mkdir()
        path = target/"request.json"; self.write(path=path)
        parent = self.work/"fictional directory link"; self.symlink(parent, target, True)
        for linked in (leaf, parent/path.name):
            self.reject(["plan", "--input", linked])
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(path.read_bytes(), before)

    @unittest.skipUnless(os.name=="nt", "Native Windows junction and stream fixture")
    def test_native_windows_junction_and_stream_spellings_refused(self):
        target = self.work/"actual input directory"; target.mkdir()
        path = target/"request.json"; self.write(path=path)
        junction = self.work/"fictional junction"
        done = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
                              capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(done.returncode, 0, "APPLICABLE_NATIVE_JUNCTION_REQUIRED")
        self.assertTrue(junction.is_junction())
        self.addCleanup(lambda: os.rmdir(junction) if junction.is_junction() else None)
        self.reject(["plan", "--input", junction/path.name])
        stream = Path(str(self.source)+":fictional")
        stream.write_bytes(b"FICTIONAL_NAMED_STREAM")
        for invalid in (str(stream), str(self.source)+".", str(self.source)+" "):
            self.reject(["plan", "--input", invalid])
        self.call(wanted=result("PLAN_READY", steps=RESTART))
        self.assertEqual(stream.read_bytes(), b"FICTIONAL_NAMED_STREAM")
        method = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
        method.argtypes, method.restype = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD], wintypes.DWORD
        buffer = ctypes.create_unicode_buffer(32768)
        size = method(str(path), buffer, len(buffer))
        self.assertGreater(size, 0, "SHORT_PATH_API_REQUIRED")
        self.assertLess(size, len(buffer), "SHORT_PATH_API_MUST_NOT_TRUNCATE")
        if buffer.value.casefold() != str(path).casefold():
            self.reject(["plan", "--input", buffer.value])

    @unittest.skipIf(os.name=="nt", "Native POSIX FIFO and socket fixture")
    def test_native_posix_fifo_and_socket_refused_before_read(self):
        fifo = self.work/"fictional fifo"; os.mkfifo(fifo)
        self.reject(["plan", "--input", fifo])
        path = self.work/"fictional socket"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as endpoint:
            endpoint.bind(str(path))
            self.reject(["readiness", "--input", path])

    def test_controlled_short_reads_complete_and_early_eof_is_refused(self):
        self.call(probe="short", wanted=result("PLAN_READY", steps=RESTART))
        self.reject(probe="early")

    def test_controlled_growth_and_same_size_mutation_are_refused(self):
        self.reject(probe="growth", preserve=False)
        self.assertEqual(self.source.stat().st_size, len(json.dumps(request()).encode())+65536)
        self.write()
        self.reject(probe="mutation", preserve=False)
        self.assertEqual(json.loads(self.source.read_bytes())["players"], 1)

    def test_controlled_read_error_and_external_action_sentinels_preserve_inputs(self):
        self.reject(probe="read_failure")
        renamed = self.work/"released.json"; self.source.rename(renamed); renamed.rename(self.source)
        self.call(probe="no_external", wanted=result("PLAN_READY", steps=RESTART))
        self.write(READY)
        self.call(["readiness", "--input", self.source], probe="no_external",
                  wanted=dict(status="OBSERVATIONS_COMPLETE", missing=[], execution_performed=False))

    def test_controlled_interruption_preserves_platform_contract_and_releases_handles(self):
        self.call(probe="library_interrupt",
                  wanted=dict(status="LIBRARY_INTERRUPT_PROPAGATED", execution_performed=False))
        if os.name=="nt":
            self.call(code=130, probe="interrupt",
                      wanted=dict(status="ERROR", code="PLAN_INTERRUPTED", execution_performed=False))
        else:
            self.call(probe="posix_cli_interrupt",
                      wanted=dict(status="POSIX_INTERRUPT_PROPAGATED", execution_performed=False))
        renamed = self.work/"released.json"; self.source.rename(renamed); renamed.rename(self.source)


if __name__ == "__main__":
    unittest.main()
