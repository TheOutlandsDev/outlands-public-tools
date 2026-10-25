"""Original MIT Windows tests using only newly generated disposable Python children."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from helpers import ROOT, cli, receipt

if os.environ.get("APP_AFFINITY_REQUIRE_NATIVE") == "1" and os.name != "nt":
    raise RuntimeError("APP_AFFINITY_REQUIRE_NATIVE requires Windows native fixture execution")


PROBE = r'''import ctypes
from ctypes import wintypes
import json, os, sys, time
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.GetCurrentProcess.restype = wintypes.HANDLE
k.GetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
k.GetProcessAffinityMask.restype = wintypes.BOOL
k.GetPriorityClass.argtypes = [wintypes.HANDLE]
k.GetPriorityClass.restype = wintypes.DWORD
mask, system = ctypes.c_size_t(), ctypes.c_size_t()
if not k.GetProcessAffinityMask(k.GetCurrentProcess(), ctypes.byref(mask), ctypes.byref(system)):
    raise ctypes.WinError(ctypes.get_last_error())
data = {"pid": os.getpid(), "mask": mask.value, "priority": k.GetPriorityClass(k.GetCurrentProcess()),
        "cwd": os.getcwd(), "args": sys.argv[3:]}
temporary = sys.argv[1] + ".tmp"
with open(temporary, "x", encoding="utf-8") as stream:
    json.dump(data, stream)
os.replace(temporary, sys.argv[1])
time.sleep(float(sys.argv[2]))
'''


def native_kernel():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
    kernel.GetProcessAffinityMask.restype = wintypes.BOOL
    kernel.GetActiveProcessorGroupCount.argtypes = []
    kernel.GetActiveProcessorGroupCount.restype = wintypes.WORD
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel


def current_mask(kernel):
    process, system = ctypes.c_size_t(), ctypes.c_size_t()
    if not kernel.GetProcessAffinityMask(kernel.GetCurrentProcess(), ctypes.byref(process), ctypes.byref(system)):
        raise ctypes.WinError(ctypes.get_last_error())
    return process.value


@unittest.skipUnless(os.name == "nt", "Native process-affinity proof requires Windows")
class NativeWindowsTests(unittest.TestCase):
    def setUp(self):
        self.kernel = native_kernel()
        self.assertEqual(self.kernel.GetActiveProcessorGroupCount(), 1,
                         "These native fixtures require the launcher's supported single-group platform")
        self.parent_mask = current_mask(self.kernel)
        self.bits = [i for i in range(ctypes.sizeof(ctypes.c_size_t) * 8) if self.parent_mask & (1 << i)]
        self.assertTrue(self.bits)
        self.tmp = tempfile.TemporaryDirectory(prefix="affinity native ")
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.probe = self.folder / "probe script.py"
        self.probe.write_text(PROBE, encoding="utf-8")

    def tearDown(self):
        self.assertEqual(current_mask(self.kernel), self.parent_mask, "The launcher changed its parent's affinity")

    def invoke(self, mask=None, arguments=(), cwd=None, delay=0, wait=10, allow=True):
        output = self.folder / ("probe-" + str(time.monotonic_ns()) + ".json")
        chosen = (1 << self.bits[0]) if mask is None else mask
        args = ["launch", "--exe", str(Path(sys.executable).absolute()), "--mask", hex(chosen), "--no-window"]
        if allow:
            args.append("--allow-existing")
        if cwd is not None:
            args += ["--cwd", str(cwd)]
        if wait is not None:
            args += ["--wait", str(wait)]
        args += ["--", str(self.probe), str(output), str(delay), *arguments]
        return cli(*args), output, chosen

    def test_single_core_applied_before_generated_child_reports(self):
        result, output, chosen = self.invoke(arguments=("fictional",))
        data = receipt(result)
        probe = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(data["resumed"])
        self.assertEqual(data["mask_before_resume"], hex(chosen))
        self.assertEqual(data["priority_before_resume"], "normal")
        self.assertEqual(data["child_exit_code"], 0)
        self.assertEqual(probe["mask"], chosen)
        self.assertEqual(probe["priority"], 0x20)
        self.assertEqual(probe["pid"], data["pid"])

    def test_multiple_allowed_cores_reach_generated_child(self):
        if len(self.bits) < 2:
            self.skipTest("Only one logical processor is available to this test process")
        mask = (1 << self.bits[0]) | (1 << self.bits[1])
        result, output, chosen = self.invoke(mask=mask)
        data = receipt(result)
        self.assertEqual(data["mask_before_resume"], hex(mask))
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["mask"], mask)

    def test_spaces_quotes_backslashes_and_shell_characters_are_literal(self):
        arguments = ("", "has spaces", 'embedded"quote', "endswith\\", 'space and quote"\\', "&", "|", ">", "$(fictional)", "%TEMP%", "fictional\U0001f600")
        result, output, chosen = self.invoke(arguments=arguments)
        receipt(result)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["args"], list(arguments))

    def test_explicit_working_directory_reaches_generated_child(self):
        directory = self.folder / "working folder \u03bb"
        directory.mkdir()
        result, output, chosen = self.invoke(cwd=directory)
        receipt(result)
        actual = json.loads(output.read_text(encoding="utf-8"))["cwd"]
        self.assertEqual(os.path.normcase(actual), os.path.normcase(str(directory)))

    def test_duplicate_executable_is_refused_before_creation(self):
        result, output, chosen = self.invoke(allow=False)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())
        self.assertNotIn("Traceback", result.stderr)

    def test_unavailable_mask_never_executes_generated_child(self):
        outside = next((1 << i for i in range(64) if not self.parent_mask & (1 << i)), 1 << 64)
        result, output, chosen = self.invoke(mask=outside)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_plan_only_creates_no_probe_output(self):
        output = self.folder / "must-not-exist.json"
        result = cli("plan", "--exe", str(Path(sys.executable).absolute()), "--mask", hex(1 << self.bits[0]),
                     "--allow-existing", "--", str(self.probe), str(output), "0")
        data = receipt(result)
        self.assertEqual(data["action"], "plan")
        self.assertFalse(data["launch_requested"])
        self.assertFalse(output.exists())

    def test_public_fixture_example_matches_native_receipt(self):
        output = self.folder / "public example receipt.json"
        mask = 1 << self.bits[0]
        result = cli("launch", "--exe", str(Path(sys.executable).absolute()), "--mask", hex(mask),
                     "--allow-existing", "--no-window", "--wait", "10", "--",
                     str(ROOT / "examples/fixture_child.py"), "--receipt", str(output),
                     "--label", "fictional public example")
        launched = receipt(result)
        proof = json.loads(output.read_text(encoding="utf-8"))
        self.assertIs(proof["fixture"], True)
        self.assertEqual(proof["mask"], hex(mask))
        self.assertEqual(proof["priority"], "0x20")
        self.assertEqual(proof["pid"], launched["pid"])
        self.assertEqual(proof["label"], "fictional public example")

    def test_wait_timeout_leaves_only_created_fixture_running(self):
        result, output, chosen = self.invoke(delay=4, wait=0.2)
        data = receipt(result)
        self.assertTrue(data["wait_timed_out"])
        deadline = time.monotonic() + 5
        while not output.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        probe = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(probe["pid"], data["pid"])
        self.assertNotEqual(probe["pid"], os.getpid())
        handle = self.kernel.OpenProcess(0x00100000 | 0x1000 | 0x0001, False, probe["pid"])
        self.assertTrue(handle, "Generated child unexpectedly stopped before timeout verification")
        try:
            name = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(name))
            self.assertTrue(self.kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)))
            self.assertEqual(os.path.normcase(name.value), os.path.normcase(str(Path(sys.executable).absolute())))
            self.assertEqual(self.kernel.WaitForSingleObject(handle, 0), 258)
        finally:
            # Exact retained handle, confirmed by our fixture receipt/output; never an image-name kill.
            self.kernel.TerminateProcess(handle, 0)
            self.kernel.WaitForSingleObject(handle, 5000)
            self.kernel.CloseHandle(handle)


if __name__ == "__main__":
    unittest.main()
