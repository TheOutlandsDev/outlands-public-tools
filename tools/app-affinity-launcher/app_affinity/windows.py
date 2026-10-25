"""Original MIT ctypes binding. No DLL or vendor implementation is bundled."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import time

from .core import AffinityError

DWORD_PTR = ctypes.c_size_t
CREATE_SUSPENDED = 0x00000004
NORMAL_PRIORITY_CLASS = 0x00000020
CREATE_NO_WINDOW = 0x08000000
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
                ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
                ("hStdError", wintypes.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", DWORD_PTR),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]


def _fail(operation):
    raise AffinityError(f"Windows {operation} failed.", {"native_error_code": ctypes.get_last_error()})


def _configure(kernel):
    signatures = {
        "GetCurrentProcess": ([], wintypes.HANDLE),
        "GetDriveTypeW": ([wintypes.LPCWSTR], wintypes.UINT),
        "GetActiveProcessorGroupCount": ([], wintypes.WORD),
        "GetProcessAffinityMask": ([wintypes.HANDLE, ctypes.POINTER(DWORD_PTR), ctypes.POINTER(DWORD_PTR)], wintypes.BOOL),
        "SetProcessAffinityMask": ([wintypes.HANDLE, DWORD_PTR], wintypes.BOOL),
        "GetPriorityClass": ([wintypes.HANDLE], wintypes.DWORD),
        "ResumeThread": ([wintypes.HANDLE], wintypes.DWORD),
        "WaitForSingleObject": ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
        "TerminateProcess": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        "GetExitCodeProcess": ([wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        "CreateToolhelp32Snapshot": ([wintypes.DWORD, wintypes.DWORD], wintypes.HANDLE),
        "Process32FirstW": ([wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)], wintypes.BOOL),
        "Process32NextW": ([wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)], wintypes.BOOL),
        "OpenProcess": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
        "QueryFullProcessImageNameW": ([wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
        "CreateProcessW": ([wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                            wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
                            ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)], wintypes.BOOL),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(kernel, name)
        function.argtypes = arguments
        function.restype = result


class WindowsBackend:
    def __init__(self):
        if os.name != "nt":
            raise AffinityError("Native planning and launching require Windows; use demo or portable fixture tests here.")
        if ctypes.sizeof(ctypes.c_void_p) != 8:
            raise AffinityError("This release requires a 64-bit Python interpreter on Windows.")
        try:
            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            _configure(self.kernel)
        except (OSError, AttributeError):
            raise AffinityError("Required Windows process APIs are unavailable.") from None

    def verify_local_paths(self, executable, cwd):
        for value in (executable, cwd):
            drive = os.path.splitdrive(value)[0]
            if not drive or self.kernel.GetDriveTypeW(drive + "\\") not in (2, 3, 5, 6):
                raise AffinityError("Executable and working directory must be on an available local drive; mapped network drives are refused.")

    def capabilities(self):
        groups = self.kernel.GetActiveProcessorGroupCount()
        if groups != 1:
            raise AffinityError("Only single-processor-group systems are supported by this release.")
        process_mask, system_mask = DWORD_PTR(), DWORD_PTR()
        if not self.kernel.GetProcessAffinityMask(self.kernel.GetCurrentProcess(), ctypes.byref(process_mask), ctypes.byref(system_mask)):
            _fail("GetProcessAffinityMask")
        if not process_mask.value or process_mask.value & ~system_mask.value:
            raise AffinityError("Windows did not report a usable current-process affinity mask.")
        return {"available_mask": process_mask.value, "system_mask": system_mask.value,
                "pointer_bits": 64, "processor_groups": groups}

    def duplicates(self, executable):
        target = os.path.normcase(os.path.abspath(executable))
        snapshot = self.kernel.CreateToolhelp32Snapshot(0x2, 0)
        if snapshot == ctypes.c_void_p(-1).value or not snapshot:
            _fail("CreateToolhelp32Snapshot")
        pids = []
        unqueryable = 0
        truncated = False
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(entry)
            present = self.kernel.Process32FirstW(snapshot, ctypes.byref(entry))
            if not present and ctypes.get_last_error() != 18:
                _fail("Process32FirstW")
            count = 0
            while present:
                count += 1
                if count > 16384:
                    truncated = True
                    break
                handle = self.kernel.OpenProcess(0x1000, False, entry.th32ProcessID)
                if not handle:
                    unqueryable += 1
                else:
                    try:
                        buffer = ctypes.create_unicode_buffer(32768)
                        size = wintypes.DWORD(len(buffer))
                        if self.kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                            if os.path.normcase(os.path.abspath(buffer.value)) == target:
                                pids.append(int(entry.th32ProcessID))
                        else:
                            unqueryable += 1
                    finally:
                        self.kernel.CloseHandle(handle)
                present = self.kernel.Process32NextW(snapshot, ctypes.byref(entry))
                if not present and ctypes.get_last_error() != 18:
                    _fail("Process32NextW")
        finally:
            self.kernel.CloseHandle(snapshot)
        return {"pids": sorted(set(pids)), "unqueryable": unqueryable, "truncated": truncated}

    def create(self, plan):
        startup = STARTUPINFOW()
        startup.cb = ctypes.sizeof(startup)
        info = PROCESS_INFORMATION()
        command = ctypes.create_unicode_buffer(plan["command_line"])
        flags = CREATE_SUSPENDED | NORMAL_PRIORITY_CLASS
        if plan["no_window"]:
            flags |= CREATE_NO_WINDOW
        if not self.kernel.CreateProcessW(plan["executable"], command, None, None, False,
                                          flags, None, plan["cwd"], ctypes.byref(startup), ctypes.byref(info)):
            _fail("CreateProcessW")
        return Child(self.kernel, info)


class Child:
    def __init__(self, kernel, info):
        self.kernel = kernel
        self.process = info.hProcess
        self.thread = info.hThread
        self.pid = int(info.dwProcessId)

    def set_mask(self, mask):
        if not self.kernel.SetProcessAffinityMask(self.process, mask):
            _fail("SetProcessAffinityMask")

    def get_mask(self):
        process_mask, system_mask = DWORD_PTR(), DWORD_PTR()
        if not self.kernel.GetProcessAffinityMask(self.process, ctypes.byref(process_mask), ctypes.byref(system_mask)):
            _fail("GetProcessAffinityMask(child)")
        return process_mask.value

    def get_priority(self):
        result = self.kernel.GetPriorityClass(self.process)
        if not result:
            _fail("GetPriorityClass")
        return int(result)

    def resume(self):
        result = self.kernel.ResumeThread(self.thread)
        if result == 0xffffffff:
            _fail("ResumeThread")
        return int(result)

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while True:
            remaining = max(0, deadline - time.monotonic())
            result = self.kernel.WaitForSingleObject(self.process, min(250, int(remaining * 1000 + 0.999)))
            if result == WAIT_OBJECT_0:
                return True
            if result != WAIT_TIMEOUT:
                _fail("WaitForSingleObject")
            if time.monotonic() >= deadline:
                return False

    def exit_code(self):
        code = wintypes.DWORD()
        if not self.kernel.GetExitCodeProcess(self.process, ctypes.byref(code)):
            _fail("GetExitCodeProcess")
        return int(code.value)

    def terminate(self):
        if not self.kernel.TerminateProcess(self.process, 125):
            _fail("TerminateProcess(created child)")

    def close(self):
        errors = []
        if self.thread:
            if not self.kernel.CloseHandle(self.thread):
                errors.append(ctypes.get_last_error())
            self.thread = None
        if self.process:
            if not self.kernel.CloseHandle(self.process):
                errors.append(ctypes.get_last_error())
            self.process = None
        if errors:
            raise AffinityError("One or more created-child handles could not be closed.",
                                {"pid": self.pid, "handle_close_errors": errors})
