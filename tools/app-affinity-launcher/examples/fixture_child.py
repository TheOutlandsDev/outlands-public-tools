"""Original MIT disposable child; writes only the explicitly selected fresh file."""
import argparse
import ctypes
from ctypes import wintypes
import json
import math
import os
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--label", default="fictional example")
    parser.add_argument("--sleep", type=float, default=0)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This disposable native fixture requires Windows.")
    if not math.isfinite(args.sleep) or not 0 <= args.sleep <= 30:
        parser.error("Sleep must be between zero and thirty seconds.")
    output = Path(args.receipt)
    if not output.is_absolute() or not output.parent.is_dir():
        parser.error("Use an absolute fresh filename in an existing private directory.")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
    kernel.GetProcessAffinityMask.restype = wintypes.BOOL
    kernel.GetPriorityClass.argtypes = [wintypes.HANDLE]
    kernel.GetPriorityClass.restype = wintypes.DWORD
    process = kernel.GetCurrentProcess()
    selected = ctypes.c_size_t()
    system = ctypes.c_size_t()
    if not kernel.GetProcessAffinityMask(process, ctypes.byref(selected), ctypes.byref(system)):
        raise ctypes.WinError(ctypes.get_last_error())
    priority = kernel.GetPriorityClass(process)
    if not priority:
        raise ctypes.WinError(ctypes.get_last_error())
    value = {"fixture": True, "pid": os.getpid(), "mask": hex(selected.value),
             "system_mask": hex(system.value), "priority": hex(priority),
             "cwd": os.getcwd(), "args": sys.argv[1:], "label": args.label}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write("\n")
    time.sleep(args.sleep)


if __name__ == "__main__":
    main()
