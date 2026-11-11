"""Fresh consumer processes of two copied library files; no production CLI."""

import ctypes
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("helpers.py", "helpers_windows.py")


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class Download(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="helpers-consumer-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied library"
        self.runtime.mkdir()
        self.runtime_hashes = {}
        for name in RUNTIME:
            data = (ROOT / name).read_bytes()
            (self.runtime / name).write_bytes(data)
            self.runtime_hashes[name] = hashlib.sha256(data).hexdigest()
        self.input = self.work / "FICTIONAL_PRIVATE_INPUT.json"
        self.input.write_bytes(b'{"fictional":true}')
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def fixture(self, data, name=None):
        self.serial += 1
        path = self.work / (name or ("fictional-" + str(self.serial) + ".json"))
        path.write_bytes(data)
        return path

    def consumer(self, body, *arguments, prelude=""):
        self.serial += 1
        script = self.work / ("authored-consumer-" + str(self.serial) + ".py")
        header = """\
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
if not __debug__:
    raise RuntimeError('OPTIMIZED_CONSUMER_UNSUPPORTED')
assert sys.prefix != sys.base_prefix
assert not list(importlib.metadata.distributions())
library = Path(sys.argv[1])
path = Path(sys.argv[2])
args = sys.argv[3:]
sys.path.insert(0, str(library))
"""
        middle = """\
import helpers as h
assert Path(h.__file__).resolve() == library / 'helpers.py'
def refused(selected, **options):
    try:
        h.load_json_object(selected, **options)
    except h.HelperError as error:
        assert str(error) == 'JSON_OBJECT_LOAD_FAILED'
        assert error.__suppress_context__ is True
        return error
    raise AssertionError('Expected selected input refusal')
def redaction_error(value, code, **options):
    try:
        h.redact_structure(value, **options)
    except h.HelperError as error:
        assert str(error) == code
        return
    raise AssertionError('Expected structured redaction refusal')
"""
        script.write_text(header + textwrap.dedent(prelude) + middle + textwrap.dedent(body)
                          + "\nprint(json.dumps({'status':'PASS','copied_library_api':True}))\n",
                          encoding="utf-8", newline="\n")
        retained = {file: digest(file) for file in self.work.rglob("*")
                    if not file.is_symlink() and not file.is_junction() and stat.S_ISREG(file.lstat().st_mode)}
        inventory = {file.relative_to(self.work).as_posix() for file in self.work.rglob("*")}
        done = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8", str(script), str(self.runtime),
                               str(self.input), *map(str, arguments)], cwd=self.work, env=self.environment,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              encoding="utf-8", errors="strict", timeout=40)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(done.stderr, "")
        self.assertEqual(json.loads(done.stdout), dict(status="PASS", copied_library_api=True))
        self.assertEqual(len(done.stdout.splitlines()), 1)
        self.assertNotIn(str(self.work), done.stdout)
        self.assertNotIn("FICTIONAL_PRIVATE", done.stdout)
        for file, checksum in retained.items():
            self.assertEqual(digest(file), checksum)
        self.assertEqual(inventory, {file.relative_to(self.work).as_posix() for file in self.work.rglob("*")})
        self.assertEqual({file.name for file in self.runtime.iterdir()}, set(RUNTIME))
        self.assertEqual({name: digest(self.runtime / name) for name in RUNTIME}, self.runtime_hashes)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])

    def symlink(self, path, target, directory=False):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as failure:
            if (os.name == "nt" and getattr(failure, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_HELPERS_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_load_nested_bom_whitespace_and_ordinary_json_values(self):
        self.input.write_bytes(b'\xef\xbb\xbf{\r\n"nested":[1,true,null,{"label":"fictional"}],"unicode":"\\u03bb"\r\n}')
        self.consumer("assert h.load_json_object(path) == {'nested':[1,True,None,{'label':'fictional'}],'unicode':'\u03bb'}\n")

    def test_duplicate_object_keys_preserve_last_value_at_each_level(self):
        self.input.write_bytes(b'{"x":1,"x":2,"nested":{"key":"first","key":"last"}}')
        self.consumer("assert h.load_json_object(path) == {'x':2,'nested':{'key':'last'}}\n")

    def test_only_top_level_objects_are_accepted(self):
        paths = [self.fixture(data) for data in (b'[]', b'null', b'true', b'1', b'"fictional"')]
        self.consumer("for selected in args:\n    refused(selected)\n", *paths)

    def test_malformed_utf8_json_and_empty_inputs_have_fixed_private_errors(self):
        paths = [self.fixture(data) for data in (b'{FICTIONAL_PRIVATE_BODY', b'\xffFICTIONAL_PRIVATE_BODY', b'')]
        self.consumer("""
            for selected in args:
                error = refused(selected)
                assert 'FICTIONAL_PRIVATE' not in str(error)
                assert str(path.parent) not in str(error)
                assert error.__cause__ is None
            """, *paths)

    def test_nonstandard_constants_fail_while_exponent_overflow_is_preserved(self):
        paths = [self.fixture(('{"number":' + literal + '}').encode()) for literal in ('NaN', 'Infinity', '-Infinity')]
        overflow = self.fixture(b'{"positive":1e999,"negative":-1e999}')
        self.consumer("""
            for selected in args[:3]:
                refused(selected)
            values = h.load_json_object(args[3])
            assert math.isinf(values['positive']) and values['positive'] > 0
            assert math.isinf(values['negative']) and values['negative'] < 0
            """, *paths, overflow)

    def test_default_one_mib_boundary_accepts_exact_and_refuses_one_extra_byte(self):
        size = 1024 * 1024
        raw = b'{"x":"' + b'a' * (size - 8) + b'"}'
        exact, excess = self.fixture(raw), self.fixture(raw + b' ')
        self.assertEqual(exact.stat().st_size, size)
        self.consumer("assert len(h.load_json_object(args[0])['x']) == 1024*1024-8\nrefused(args[1])\n", exact, excess)

    def test_sixteen_mib_override_cap_accepts_exact_and_refuses_larger_input(self):
        size = 16 * 1024 * 1024
        raw = b'{"x":"' + b'a' * (size - 8) + b'"}'
        exact, excess = self.fixture(raw), self.fixture(raw + b' ')
        self.assertEqual(exact.stat().st_size, size)
        self.consumer("assert len(h.load_json_object(args[0],max_bytes=16*1024*1024)['x']) == 16*1024*1024-8\n"
                      "refused(args[1],max_bytes=16*1024*1024)\n", exact, excess)

    def test_invalid_limits_are_refused_before_path_conversion_or_io(self):
        self.consumer("""
            class ForbiddenPath:
                def __fspath__(self):
                    raise AssertionError('PATH_CONVERSION_BEFORE_LIMIT_VALIDATION')
            class IntegerSubclass(int):
                pass
            for limit in (True,False,0,-1,1.5,None,16*1024*1024+1,IntegerSubclass(2)):
                try:
                    h.load_json_object(ForbiddenPath(),max_bytes=limit)
                except h.HelperError as error:
                    assert str(error) == 'INVALID_LIMIT'
                else:
                    raise AssertionError('Invalid limit accepted')
            """)

    def test_exact_small_explicit_limit_and_pathlike_inputs(self):
        self.input.write_bytes(b'{}')
        self.consumer("assert h.load_json_object(path,max_bytes=2) == {}\n"
                      "assert h.load_json_object(str(path),max_bytes=2) == {}\nrefused(path,max_bytes=1)\n")

    def test_relative_paths_work_but_missing_directories_and_parent_traversal_fail(self):
        self.consumer("""
            assert h.load_json_object(path.name) == {'fictional':True}
            refused(path.parent/'FICTIONAL_PRIVATE_MISSING.json')
            refused(path.parent)
            refused(str(path.parent/'uncreated'/'..'/path.name))
            """)

    def test_import_and_calls_do_not_execute_named_payloads_or_contact_networks(self):
        payload = self.fixture(b"raise AssertionError('FICTIONAL_PAYLOAD_EXECUTED')\n", "fictional-payload.py")
        self.input.write_bytes(json.dumps(dict(command=payload.name, url="https://fictional.invalid/not-requested",
                                              message="FICTIONAL_PRIVATE_TEXT")).encode())
        self.consumer("""
            loaded = h.load_json_object(path)
            assert h.redact_structure(loaded) == loaded
            assert loaded['command'] == 'fictional-payload.py'
            """, prelude="""
            import socket, urllib.request, subprocess
            def forbidden(*args, **kwargs):
                raise AssertionError('UNREQUESTED_EXECUTION_OR_NETWORK')
            socket.socket = forbidden
            socket.create_connection = forbidden
            urllib.request.urlopen = forbidden
            subprocess.run = forbidden
            os.system = forbidden
            """)

    def test_documented_sensitive_keys_normalize_case_and_dash_underscore(self):
        self.consumer("""
            expected = {'password','api_key','authorization','secret','token','access_token','refresh_token','secret_key','private_key'}
            assert h.SENSITIVE_KEYS == frozenset(expected)
            variants = ['PASSWORD','Api-Key','AUTHORIZATION','Secret','token','Access-Token','refresh_token','Secret-Key','PRIVATE_KEY']
            source = {key:'FICTIONAL_PRIVATE_VALUE' for key in variants}
            result = h.redact_structure(source)
            assert result == {key:'<redacted>' for key in variants}
            assert set(result) == set(source)
            assert all(value == 'FICTIONAL_PRIVATE_VALUE' for value in source.values())
            """)

    def test_unknown_keys_identifying_metadata_and_free_text_are_retained(self):
        self.consumer("""
            source = {'user':'Fictional Person','email':'fictional@example.invalid',
                      'api key':'fictional unknown key',' token':'leading space retained',
                      'tokens':'plural retained','password_hint':'retained hint',
                      'message':'password=fictional remains ordinary free text'}
            result = h.redact_structure(source)
            assert result == source and result is not source
            """)

    def test_nested_redaction_copies_containers_without_mutating_or_aliasing_input(self):
        self.consumer("""
            shared = {'token':'fictional token','notes':['ordinary',{'password':'fictional password'}]}
            source = {'left':shared,'right':shared,'rows':[shared]}
            result = h.redact_structure(source)
            assert result['left']['token'] == '<redacted>'
            assert result['rows'][0]['notes'][1]['password'] == '<redacted>'
            assert result is not source and result['left'] is not shared
            assert result['left'] is not result['right']
            result['left']['notes'].append('new result item')
            assert len(shared['notes']) == len(result['right']['notes']) == 2
            assert shared['token'] == 'fictional token'
            """)

    def test_redactor_preserves_primitives_nonfinite_floats_and_negative_zero(self):
        self.consumer("""
            source = [None,True,False,123,'fictional',1.25,-0.0,float('inf'),float('-inf'),float('nan')]
            result = h.redact_structure(source)
            assert result[:6] == source[:6] and result is not source
            assert math.copysign(1.0,result[6]) == -1.0
            assert math.isinf(result[7]) and result[7] > 0
            assert math.isinf(result[8]) and result[8] < 0
            assert math.isnan(result[9])
            """)

    def test_invalid_redaction_depth_is_refused_before_value_inspection(self):
        self.consumer("""
            class IntegerSubclass(int):
                pass
            for depth in (True,False,0,-1,129,1.5,None,IntegerSubclass(2)):
                redaction_error(object(),'INVALID_DEPTH',max_depth=depth)
            """)

    def test_redaction_depth_cycles_and_sensitive_branch_behavior_are_bounded(self):
        self.consumer("""
            assert h.redact_structure([['leaf']],max_depth=2) == [['leaf']]
            redaction_error([['leaf']],'DEPTH_LIMIT',max_depth=1)
            value = 'leaf'
            for _ in range(32):
                value = [value]
            h.redact_structure(value)
            redaction_error([value],'DEPTH_LIMIT')
            cycle = []
            cycle.append(cycle)
            redaction_error(cycle,'DEPTH_LIMIT')
            mapping = {}
            mapping['ordinary'] = mapping
            redaction_error(mapping,'DEPTH_LIMIT')
            assert h.redact_structure({'password':cycle}) == {'password':'<redacted>'}
            """)

    def test_nonstring_keys_and_unsupported_values_have_specific_errors(self):
        self.consumer("""
            for value in ({1:'fictional'},{None:'fictional'}):
                redaction_error(value,'STRING_KEYS_REQUIRED')
            class IntegerSubclass(int):
                pass
            for value in ((),set(),b'fictional',object(),1+2j,IntegerSubclass(1)):
                redaction_error(value,'JSON_TYPES_REQUIRED')
            assert h.redact_structure({'secret':object()}) == {'secret':'<redacted>'}
            """)

    def test_load_then_redact_is_an_explicit_consumer_operation_with_input_preserved(self):
        self.input.write_bytes(b'{"token":"FICTIONAL_PRIVATE_TOKEN","nested":[{"api-key":"fictional"}],"message":"token=fictional text"}')
        self.consumer("""
            loaded = h.load_json_object(path)
            result = h.redact_structure(loaded)
            assert result == {'token':'<redacted>','nested':[{'api-key':'<redacted>'}],'message':'token=fictional text'}
            assert loaded['token'] == 'FICTIONAL_PRIVATE_TOKEN'
            assert loaded['nested'][0]['api-key'] == 'fictional'
            """)

    def test_native_hardlinked_ordinary_sources_load_without_mutation(self):
        linked = self.work / "hardlinked-fictional.json"
        os.link(self.input, linked)
        self.consumer("assert h.load_json_object(path) == h.load_json_object(args[0]) == {'fictional':True}\n", linked)
        self.assertEqual(digest(self.input), digest(linked))

    def test_native_symlink_leaf_inputs_are_refused(self):
        linked = self.work / "linked-fictional.json"
        self.symlink(linked, self.input)
        missing = self.work / "absent-fictional.json"
        dangling = self.work / "dangling-fictional.json"
        self.symlink(dangling, missing)
        self.consumer("refused(args[0])\nrefused(args[1])\n", linked, dangling)
        self.assertFalse(missing.exists())

    def test_native_symlink_parent_is_refused(self):
        target = self.work / "real parent"
        target.mkdir()
        selected = target / "fictional.json"
        selected.write_bytes(b'{"fictional":true}')
        link = self.work / "linked parent"
        self.symlink(link, target, directory=True)
        self.consumer("refused(args[0])\n", link / selected.name)

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_parent_is_refused(self):
        from ctypes import wintypes

        target = self.work / "real junction parent"
        target.mkdir()
        selected = target / "fictional.json"
        selected.write_bytes(b'{"fictional":true}')
        link = self.work / "junction parent"
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
        substitute = ("\\??\\" + str(target)).encode("utf-16-le")
        printable = str(target).encode("utf-16-le")
        payload = substitute + b"\x00\x00" + printable + b"\x00\x00"
        data = struct.pack("<LHHHHHH", 0xA0000003, 8 + len(payload), 0,
                           0, len(substitute), len(substitute) + 2, len(printable)) + payload
        handle = kernel.CreateFileW(str(link), 0x40000000, 0, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            buffer = ctypes.create_string_buffer(data)
            returned = wintypes.DWORD()
            if not kernel.DeviceIoControl(handle, 0x000900A4, buffer, len(data), None, 0,
                                          ctypes.byref(returned), None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(handle)
        self.assertTrue(link.is_junction())
        self.consumer("refused(args[0])\n", link / selected.name)

    @unittest.skipUnless(os.name == "nt", "Native Windows alternate stream fixture")
    def test_native_windows_alternate_stream_is_refused(self):
        stream = str(self.input) + ":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b'{"fictional_stream":true}')
        self.consumer("refused(args[0])\n", stream)
        with open(stream, "rb") as handle:
            self.assertEqual(handle.read(), b'{"fictional_stream":true}')

    @unittest.skipUnless(os.name != "nt", "Native POSIX special file fixture")
    def test_native_posix_fifo_and_short_socket_are_refused(self):
        fifo = self.work / "f"
        os.mkfifo(fifo, 0o600)
        endpoint = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(endpoint.close)
        original = Path.cwd()
        try:
            os.chdir(self.work)
            endpoint.bind("s")
        finally:
            os.chdir(original)
        # Binding a relative one-character path avoids the AF_UNIX address limit
        # even if the trusted fixture parent has a long fully spelled pathname.
        self.consumer("refused(args[0])\nrefused(args[1])\n", fifo, self.work / "s")

    def test_interruption_closes_read_descriptors_and_releases_source_handles(self):
        self.consumer("""
            real_open, real_close, real_read = os.open, os.close, os.read
            opened, closed = [], []
            def selected_open(*args, **kwargs):
                fd = real_open(*args, **kwargs)
                opened.append(fd)
                return fd
            def selected_close(fd):
                real_close(fd)
                closed.append(fd)
            def interrupted_read(*args):
                raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPTION')
            os.open, os.close, os.read = selected_open, selected_close, interrupted_read
            try:
                try:
                    h.load_json_object(path)
                except KeyboardInterrupt:
                    pass
                else:
                    raise AssertionError('Expected caller-visible interruption')
            finally:
                os.open, os.close, os.read = real_open, real_close, real_read
            assert opened and set(opened) <= set(closed)
            for fd in opened:
                try:
                    os.fstat(fd)
                except OSError:
                    pass
                else:
                    raise AssertionError('Read descriptor remained open')
            renamed = path.with_name('temporary-closure-probe.json')
            path.rename(renamed)
            renamed.rename(path)
            assert h.load_json_object(path) == {'fictional':True}
            """)


if __name__ == "__main__":
    unittest.main()
