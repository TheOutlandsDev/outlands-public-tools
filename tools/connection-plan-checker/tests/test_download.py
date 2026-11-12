"""Actual copied-script consumers of authored connection declarations, never network probes."""

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


ROOT = Path(__file__).resolve().parents[1]
FLAGS = dict.fromkeys(("network_probed", "programs_executed", "runtime_verified", "availability_verified"), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def binding(identifier="sample_a", *, transport="tcp", address="127.0.0.1", port=49152):
    return dict(id=identifier, transport=transport, address=address, port=port)


def distinct_bindings():
    return [binding(), binding("sample_b", transport="udp"), binding("sample_c", address="::1"), binding("sample_d", port=49153)]


def plan(rows=None):
    return dict(schema_version=1, bindings=distinct_bindings() if rows is None else rows)


def golden(identifiers, groups=()):
    repeated = {identifier for group in groups for identifier in group}
    return dict(schema_version=1, status="DECLARED_CONFLICTS" if groups else "NO_DECLARED_CONFLICTS",
                scope="DECLARED_LOOPBACK_BINDINGS_ONLY", **FLAGS,
                counts=dict(bindings=len(identifiers), conflict_groups=len(groups), conflicting_bindings=len(repeated)),
                checks=[dict(id=identifier, status="CONFLICT" if identifier in repeated else "DISTINCT",
                             evidence="REPEATED_DECLARED_BINDING" if identifier in repeated else "UNIQUE_DECLARED_BINDING")
                        for identifier in identifiers], conflict_groups=[dict(ids=list(group)) for group in groups])


def default_result():
    return golden([row["id"] for row in distinct_bindings()])


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="connection-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied single script"
        self.runtime.mkdir()
        self.source = self.runtime / "connection_check.py"
        self.source.write_bytes((ROOT / "connection_check.py").read_bytes())
        self.runtime_hash = sha(self.source.read_bytes())
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def fixture(self, value=None, *, raw=None):
        self.serial += 1
        path = self.work / ("FICTIONAL_PRIVATE_PLAN_" + str(self.serial) + ".json")
        path.write_bytes(json.dumps(plan() if value is None else value).encode("utf-8") if raw is None else raw)
        return path

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import connection_check as tool\nevents = []\n" + textwrap.dedent(body)
                          + "\nstatus = tool.main(sys.argv[1:])\n" + textwrap.dedent(postlude)
                          + "\nraise SystemExit(status)\n", encoding="utf-8", newline="\n")
        return script

    def process(self, *arguments, expected=0, code=None, script=None, json_output=True):
        tree = {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")}
        retained = {}
        for path in self.work.rglob("*"):
            if not path.is_symlink() and not path.is_junction():
                info = path.lstat()
                if stat.S_ISREG(info.st_mode):
                    retained[path] = (sha(path.read_bytes()), info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink)
        done = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8", str(script or self.source), *map(str, arguments)],
                              cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60)
        self.assertEqual(done.returncode, expected, done.stdout[:2000] + done.stderr)
        self.assertEqual(done.stderr, "")
        self.assertEqual(tree, {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")})
        for path, before in retained.items():
            info = path.lstat()
            self.assertEqual((sha(path.read_bytes()), info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink), before)
        self.assertEqual(list(self.runtime.iterdir()), [self.source])
        self.assertEqual(sha(self.source.read_bytes()), self.runtime_hash)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
        self.assertNotIn(str(self.work), done.stdout.replace("\\\\", "\\"))
        self.assertNotIn("FICTIONAL_PRIVATE", done.stdout)
        if not json_output:
            return done.stdout
        self.assertEqual(len(done.stdout.splitlines()), 1)
        value = json.loads(done.stdout)
        if expected in (2, 130):
            self.assertEqual(value, dict(status="ERROR", code=code or "INTERRUPTED", **FLAGS))
        else:
            self.assertEqual(set(value), {"schema_version", "status", "scope", "counts", "checks", "conflict_groups", *FLAGS})
            self.assertTrue(all(value[key] is False for key in FLAGS))
            for row in value["checks"]:
                self.assertEqual(set(row), {"id", "status", "evidence"})
            for group in value["conflict_groups"]:
                self.assertEqual(set(group), {"ids"})
        return value

    def run_cli(self, source=None, **options):
        return self.process("--plan", source or self.fixture(), **options)

    def check(self, value, wanted, *, raw=None, script=None):
        self.assertEqual(self.run_cli(self.fixture(value, raw=raw), expected=int(wanted["status"] == "DECLARED_CONFLICTS"), script=script), wanted)
        return wanted

    def symlink(self, path, target):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_CONNECTION_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_distinct_plan_has_complete_json_and_creates_no_result_files(self):
        self.check(plan(), default_result())
        self.assertEqual({path.name for path in self.work.iterdir()}, {self.runtime.name, "FICTIONAL_PRIVATE_PLAN_1.json"})

    def test_every_repeated_tcp_and_udp_member_is_a_declared_conflict(self):
        for transport in ("tcp", "udp"):
            rows = [binding(name, transport=transport) for name in ("sample_z", "sample_a", "sample_m")]
            self.check(plan(rows), golden([row["id"] for row in rows], [["sample_z", "sample_a", "sample_m"]]))

    def test_transport_address_and_port_each_separate_declared_tuples(self):
        rows = [binding("tcp_v4"), binding("udp_v4", transport="udp"), binding("tcp_v6", address="::1"),
                binding("udp_v6", transport="udp", address="::1"), binding("other_port", port=49153)]
        self.check(plan(rows), golden([row["id"] for row in rows]))

    def test_group_first_appearance_members_and_checks_keep_declaration_order(self):
        rows = [binding("group_z_first", port=49153), binding("group_a_first", transport="udp"),
                binding("group_a_second", transport="udp"), binding("distinct", address="::1"), binding("group_z_second", port=49153)]
        self.check(plan(rows), golden([row["id"] for row in rows],
                   [["group_z_first", "group_z_second"], ["group_a_first", "group_a_second"]]))

    def test_permutations_preserve_membership_and_follow_new_first_appearance(self):
        rows = [binding("a"), binding("b", transport="udp", address="::1", port=49153), binding("c"),
                binding("d", transport="udp", address="::1", port=49153), binding("e", address="::1")]
        self.check(plan(rows), golden(["a", "b", "c", "d", "e"], [["a", "c"], ["b", "d"]]))
        self.check(plan([rows[index] for index in (3, 2, 1, 4, 0)]), golden(["d", "c", "b", "e", "a"], [["d", "b"], ["c", "a"]]))

    def test_seeded_pairwise_equality_oracle_checks_complete_reports(self):
        selected = random.Random(941)
        for iteration in range(10):
            rows = [binding("sample_"+str(index), transport=selected.choice(("tcp", "udp")), address=selected.choice(("127.0.0.1", "::1")),
                            port=selected.choice((49152, 49153, 65535))) for index in range(12)]
            claimed, groups = set(), []
            # Independent pairwise field equality and list search, without tuple-key indexing.
            for index, row in enumerate(rows):
                if index in claimed:
                    continue
                members = [other for other, candidate in enumerate(rows)
                           if candidate["transport"] == row["transport"] and candidate["address"] == row["address"] and candidate["port"] == row["port"]]
                if len(members) > 1:
                    claimed.update(members)
                    groups.append([rows[other]["id"] for other in members])
            self.check(plan(rows), golden([row["id"] for row in rows], groups))

    def test_root_and_binding_fields_are_exact_without_private_configuration(self):
        for value in (None, [], {}, dict(plan(), schema_version=True), dict(plan(), schema_version=1.0),
                      dict(plan(), schema_version="1"), dict(plan(), command="FICTIONAL_PRIVATE_COMMAND")):
            self.run_cli(self.fixture(raw=json.dumps(value).encode()), expected=2, code="PLAN_SCHEMA_INVALID")
        for row in ({}, dict(binding(), credential="FICTIONAL_PRIVATE_VALUE"), dict(binding(), process_id=123)):
            self.run_cli(self.fixture(plan([row])), expected=2, code="BINDING_SCHEMA_INVALID")

    def test_binding_ids_are_bounded_strings_and_globally_unique(self):
        for value in (None, 1, True, [], "Upper", "1first", "has space", "é", "a"*41):
            self.run_cli(self.fixture(plan([binding(value)])), expected=2, code="BINDING_ID_INVALID")
        for identifier in ("a", "a"*40):
            self.check(plan([binding(identifier)]), golden([identifier]))
        self.run_cli(self.fixture(plan([binding(), binding(transport="udp")])), expected=2, code="DUPLICATE_BINDING_ID")

    def test_transport_accepts_only_exact_tcp_or_udp(self):
        for value in (None, True, 1, [], "TCP", "udp ", "http"):
            self.run_cli(self.fixture(plan([binding(transport=value)])), expected=2, code="TRANSPORT_INVALID")

    def test_only_two_exact_loopback_literals_are_accepted_without_resolution(self):
        for value in (None, 1, [], "localhost", "127.0.0.01", "127.0.0.2", "0.0.0.0", "::", "0:0:0:0:0:0:0:1",
                      "::ffff:127.0.0.1", "10.0.0.1", "::1 "):
            self.run_cli(self.fixture(plan([binding(address=value)])), expected=2, code="LOOPBACK_LITERAL_REQUIRED")

    def test_ports_have_inclusive_integer_boundaries_without_boolean_coercion(self):
        self.check(plan([binding("minimum", port=1), binding("maximum", port=65535)]), golden(["minimum", "maximum"]))
        for value in (None, True, False, 1.0, "49152", 0, -1, 65536):
            self.run_cli(self.fixture(plan([binding(port=value)])), expected=2, code="PORT_INVALID")

    def test_128_bindings_are_accepted_and_zero_or_extra_are_refused(self):
        rows = [binding("sample_"+str(index).zfill(3)) for index in range(128)]
        identifiers = [row["id"] for row in rows]
        self.check(plan(rows), golden(identifiers, [identifiers]))
        for declarations in ([], rows+[binding("extra")]):
            self.run_cli(self.fixture(plan(declarations)), expected=2, code="PLAN_SCHEMA_INVALID")

    def test_input_64_kib_exact_bom_and_extra_byte(self):
        raw = b"\xef\xbb\xbf"+json.dumps(plan()).encode()
        exact = raw+b" "*(65536-len(raw))
        self.check(plan(), default_result(), raw=exact)
        self.run_cli(self.fixture(raw=exact+b" "), expected=2, code="INPUT_SIZE_LIMIT")

    def test_duplicate_json_constants_encoding_and_malformed_data_are_fixed(self):
        raw = json.dumps(plan()).encode()
        for duplicate in (raw[:-1]+b',"bindings":[]}', raw.replace(b'"port": 49152', b'"port":49152,"port":49152')):
            self.run_cli(self.fixture(raw=duplicate), expected=2, code="DUPLICATE_JSON_KEY")
        for constant in (b"NaN", b"Infinity", b"-Infinity"):
            self.run_cli(self.fixture(raw=raw.replace(b'"port": 49152', b'"port":'+constant)), expected=2, code="NONSTANDARD_JSON")
        for value in (b"\xff", b"{", b"", b"{} {}"):
            self.run_cli(self.fixture(raw=value), expected=2, code="INPUT_OR_PLAN_FAILED")

    def test_four_false_flags_and_private_tuple_values_are_not_output_fields(self):
        rows = [binding("first"), binding("second")]
        value = self.check(plan(rows), golden(["first", "second"], [["first", "second"]]))
        raw = json.dumps(value)
        for literal in ('"transport"', '"address"', '"port"', '"tcp"', '"udp"', '127.0.0.1', '::1', '49152'):
            self.assertNotIn(literal, raw)
        self.assertEqual({key: value[key] for key in FLAGS}, FLAGS)

    def test_help_version_arguments_and_path_errors_have_fixed_private_output(self):
        self.assertIn("--plan", self.process("--help", json_output=False))
        self.assertEqual(self.process("--version", json_output=False), "connection-plan-checker 0.1.0\n")
        for args in ((), ("--plan",), ("--pl", "FICTIONAL_PRIVATE_ARGUMENT"), ("--unknown", "FICTIONAL_PRIVATE_ARGUMENT")):
            self.process(*args, expected=2, code="ARGUMENTS_INVALID")
        self.run_cli(self.work/"FICTIONAL_PRIVATE_MISSING.json", expected=2, code="INPUT_OR_PLAN_FAILED")
        self.run_cli(self.runtime, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        for path in (self.work/"CON.json", self.work/"file:stream", self.work/".."/"escape.json"):
            self.run_cli(path, expected=2, code="INPUT_PATH_INVALID")
        source = self.fixture()
        self.assertEqual(self.run_cli(source.name), default_result())

    def test_only_selected_plan_is_read_without_sockets_dns_processes_or_changes(self):
        source = self.fixture()
        (self.work/"unrelated-configuration.txt").write_bytes(b"FICTIONAL_PRIVATE_CONFIG_NEVER_OPEN")
        (self.work/"prior-capture.txt").write_bytes(b"Fictional prior capture must remain unchanged\n")
        script = self.wrapper("""
            selected = Path(INPUT_VALUE)
            environment_before = dict(os.environ)
            original = os.open
            def opened(path, *args, **kwargs):
                assert Path(path) == selected, 'Unselected configuration or environment file opened'
                events.append(True)
                return original(path, *args, **kwargs)
            def forbidden(*args, **kwargs):
                raise AssertionError('Socket, DNS, command, environment change or enumeration attempted')
            os.open = opened
            os.scandir = forbidden
            os.listdir = forbidden
            os.putenv = forbidden
            os.unsetenv = forbidden
            Path.open = forbidden
            socket.socket = forbidden
            socket.create_connection = forbidden
            socket.getaddrinfo = forbidden
            socket.gethostbyname = forbidden
            urllib.request.urlopen = forbidden
            subprocess.Popen = forbidden
            runpy.run_path = forbidden
            os.system = forbidden
            os.execv = forbidden
            """.replace("INPUT_VALUE", repr(str(source))), prelude="import socket, urllib.request, subprocess, runpy\n",
                              postlude="assert events == [True] and status == 0\nassert dict(os.environ) == environment_before\n")
        self.assertEqual(self.run_cli(source, script=script), default_result())

    def test_native_hardlinked_plan_is_refused_and_target_preserved(self):
        source = self.fixture()
        alias = self.work / "owned-hardlink.json"
        os.link(source, alias)
        self.assertGreaterEqual(source.stat().st_nlink, 2)
        self.run_cli(source, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    def test_controlled_interrupt_and_short_read_release_input_handle(self):
        source = self.fixture()
        for mode in ("interrupt", "short"):
            script = self.wrapper("""
                original = os.fdopen
                descriptors = []
                class Controlled:
                    def __init__(self, stream):
                        self.stream = stream
                    def __enter__(self):
                        self.stream.__enter__()
                        return self
                    def __exit__(self, *args):
                        return self.stream.__exit__(*args)
                    def fileno(self):
                        return self.stream.fileno()
                    def read(self, maximum):
                        events.append(True)
                        if MODE == 'interrupt':
                            raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT')
                        return self.stream.read(maximum)[:-1]
                def opened(fd, *args, **kwargs):
                    descriptors.append(fd)
                    return Controlled(original(fd, *args, **kwargs))
                os.fdopen = opened
                """.replace("MODE", repr(mode)), postlude="""
                assert events == [True]
                for fd in descriptors:
                    try:
                        os.fstat(fd)
                    except OSError as error:
                        assert error.errno == 9
                    else:
                        raise AssertionError('Owned descriptor remained open')
                """)
            self.run_cli(source, script=script, expected=130 if mode == "interrupt" else 2,
                         code=None if mode == "interrupt" else "INPUT_CHANGED")

    def test_observed_identity_change_and_native_read_error_are_fixed(self):
        source = self.fixture()
        script = self.wrapper("""
            original = tool._snapshot
            def changed(path):
                events.append(True)
                ancestors, leaf = original(path)
                return (ancestors+('controlled observed change',), leaf) if len(events) == 2 else (ancestors, leaf)
            tool._snapshot = changed
            """, postlude="assert events == [True, True] and status == 2\n")
        self.run_cli(source, script=script, expected=2, code="INPUT_CHANGED")
        script = self.wrapper("""
            def denied(*args, **kwargs):
                events.append(True)
                raise OSError('FICTIONAL_PRIVATE_NATIVE_IO_DETAIL')
            os.open = denied
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(source, script=script, expected=2, code="INPUT_OR_PLAN_FAILED")

    def test_native_symlink_plan_leaf_and_dangling_are_refused(self):
        source = self.fixture()
        alias = self.work / "linked-plan.json"
        self.symlink(alias, source)
        self.run_cli(alias, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        absent = self.work / "owned-absent-target.json"
        dangling = self.work / "dangling-plan.json"
        self.symlink(dangling, absent)
        self.run_cli(dangling, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        self.assertFalse(absent.exists())

    def test_native_symlink_plan_parent_is_refused(self):
        source = self.fixture()
        target = self.work / "owned-plan-parent"
        target.mkdir()
        moved = target / "plan.json"
        source.rename(moved)
        alias = self.work / "linked-parent"
        self.symlink(alias, target)
        self.run_cli(alias / "plan.json", expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_plan_parent_is_refused(self):
        source = self.fixture()
        target = self.work / "owned-plan-parent"
        target.mkdir()
        moved = target / "plan.json"
        source.rename(moved)
        alias = self.work / "junction-parent"
        self.junction(alias, target)
        self.run_cli(alias / "plan.json", expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows alternate stream fixture")
    def test_native_windows_named_stream_is_not_part_of_selected_plan(self):
        source = self.fixture()
        stream = str(source)+":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b"FICTIONAL_PRIVATE_NAMED_STREAM")
        self.assertEqual(self.run_cli(source), default_result())
        self.run_cli(stream, expected=2, code="INPUT_PATH_INVALID")
        # Observed retained normalization, not a blanket lexical-refusal guard.
        for spelling in (str(source)+".", str(source)+" ", str(source.parent)+"."+os.sep+source.name):
            self.assertEqual(self.run_cli(spelling), default_result())
        self.run_cli(str(source.parent)+" "+os.sep+source.name, expected=2, code="INPUT_PATH_INVALID")
        with open(stream, "rb") as handle:
            self.assertEqual(handle.read(), b"FICTIONAL_PRIVATE_NAMED_STREAM")

    @unittest.skipUnless(os.name == "nt", "Native Windows held writer fixture")
    def test_native_windows_exclusive_writer_causes_open_refusal_then_release(self):
        source = self.fixture()
        script = self.wrapper("""
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                          wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            held = kernel.CreateFileW(INPUT_VALUE, 0x40000000, 0, None, 3, 0x80, None)
            if held == ctypes.c_void_p(-1).value:
                raise AssertionError('Native held writer fixture creation failed') from ctypes.WinError(ctypes.get_last_error())
            events.append(True)
            """.replace("INPUT_VALUE", repr(str(source))),
                              postlude="assert kernel.CloseHandle(held)\nassert events == [True] and status == 2\n")
        self.run_cli(source, script=script, expected=2, code="INPUT_OR_PLAN_FAILED")
        self.assertEqual(self.run_cli(source), default_result())

    @unittest.skipUnless(os.name != "nt", "Native POSIX FIFO fixture")
    def test_native_posix_fifo_plan_is_refused_before_open(self):
        fifo = self.work / "owned-fifo.json"
        os.mkfifo(fifo, 0o600)
        self.run_cli(fifo, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

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
