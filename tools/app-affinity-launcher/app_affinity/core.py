"""Original MIT launch policy. Importing it starts nothing and changes no process."""
from __future__ import annotations

import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


class AffinityError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = {} if details is None else details


def parse_cores(text):
    if not isinstance(text, str) or not text or len(text) > 256:
        raise AffinityError("Cores must be a comma-separated list of logical processor numbers.")
    pieces = text.split(",")
    if any(not re.fullmatch(r"(?:0|[1-9][0-9]?)", item.strip()) for item in pieces):
        raise AffinityError("Use individual zero-based logical processor numbers, without ranges.")
    result = tuple(int(item.strip()) for item in pieces)
    mask_from_cores(result)
    return tuple(sorted(result))


def parse_mask(text):
    if not isinstance(text, str) or not re.fullmatch(r"0[xX][0-9a-fA-F]{1,16}", text):
        raise AffinityError("Mask must be an explicit hexadecimal value such as 0x1 or 0x5.")
    value = int(text, 16)
    if value == 0:
        raise AffinityError("An affinity mask cannot be zero.")
    return value


def mask_from_cores(cores):
    if not isinstance(cores, (tuple, list)) or not 1 <= len(cores) <= 64:
        raise AffinityError("Select between one and 64 distinct logical processor numbers.")
    seen = set()
    mask = 0
    for number in cores:
        if type(number) is not int or not 0 <= number <= 63 or number in seen:
            raise AffinityError("Logical processor numbers must be distinct integers from 0 through 63.")
        seen.add(number)
        mask |= 1 << number
    return mask


def validate_mask(mask, available_mask, pointer_bits=64):
    if type(pointer_bits) is not int or pointer_bits not in (32, 64):
        raise AffinityError("Unsupported native pointer width.")
    maximum = (1 << pointer_bits) - 1
    if type(available_mask) is not int or not 0 < available_mask <= maximum:
        raise AffinityError("The available processor mask could not be established.")
    if type(mask) is not int or not 0 < mask <= maximum or mask & ~available_mask:
        raise AffinityError("Requested mask must be nonzero and fit within this process's available processors.",
                            {"available_mask": hex(available_mask), "pointer_bits": pointer_bits})
    return mask


def _text(value, label):
    if not isinstance(value, str) or "\0" in value:
        raise AffinityError(f"{label} must be text without a NUL character.")
    try:
        value.encode("utf-16-le")
    except UnicodeError:
        raise AffinityError(f"{label} contains unsupported Unicode.") from None
    return value


def _local_path(value, directory=False, backend=None):
    try:
        raw = _text(os.fspath(value), "Path")
        if not raw or len(raw) > 32000 or any(ord(c) < 32 for c in raw):
            raise AffinityError("Provide an absolute local path without control characters.")
        path = Path(raw)
        if not path.is_absolute():
            raise AffinityError("Executable and working-directory paths must be absolute.")
        if os.name == "nt":
            if raw.startswith(("\\\\", "//")) or not re.fullmatch(r"[A-Za-z]:", path.drive):
                raise AffinityError("Only local drive paths are supported; UNC/device paths are refused.")
            if any(character in raw[2:] for character in ':<>"|?*'):
                raise AffinityError("Windows path contains an unsupported or ambiguous character.")
            if any(part in (".", "..") or part.endswith((".", " ")) for part in re.split(r"[\\/]", raw[3:]) if part):
                raise AffinityError("Windows path components must not be dot segments or end in a dot/space.")
        path = Path(os.path.abspath(raw))
        if backend is not None and hasattr(backend, "verify_local_paths"):
            backend.verify_local_paths(str(path), str(path))
        for candidate in (path, *path.parents):
            info = candidate.stat(follow_symlinks=False)
            if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
                raise AffinityError("Linked executable or working-directory paths/parents are unsupported.")
            if getattr(info, "st_file_attributes", 0) & 0x400:
                raise AffinityError("Reparse-point executable or directory paths are unsupported.")
        info = path.stat(follow_symlinks=False)
        if directory:
            if not stat.S_ISDIR(info.st_mode):
                raise AffinityError("Working directory must be an existing directory.")
        elif not stat.S_ISREG(info.st_mode) or path.suffix.lower() != ".exe":
            raise AffinityError("Executable must be an existing regular .exe file.")
        return str(path)
    except (OSError, ValueError, TypeError):
        raise AffinityError("Executable or working directory is unavailable or unsupported.") from None


def _backend(backend):
    if backend is not None:
        return backend
    from .windows import WindowsBackend
    return WindowsBackend()


def make_plan(executable, cores=None, mask=None, cwd=None, args=(), allow_existing=False,
              no_window=False, backend=None):
    if type(allow_existing) is not bool or type(no_window) is not bool:
        raise AffinityError("Launch flags must be booleans.")
    if (cores is None) == (mask is None):
        raise AffinityError("Select either logical processors or a hexadecimal mask, but not both.")
    selected = mask_from_cores(parse_cores(cores) if isinstance(cores, str) else cores) if cores is not None else parse_mask(mask) if isinstance(mask, str) else mask
    if not isinstance(args, (list, tuple)) or len(args) > 256:
        raise AffinityError("Child arguments must be a list of at most 256 literal strings.")
    arguments = [_text(item, "Argument") for item in args]
    native = _backend(backend)
    executable = _local_path(executable, backend=native)
    working = _local_path(Path(executable).parent if cwd is None else cwd, directory=True, backend=native)
    command_line = subprocess.list2cmdline([executable, *arguments])
    if len(command_line.encode("utf-16-le")) // 2 + 1 > 32767:
        raise AffinityError("Windows command line exceeds 32767 UTF-16 code units including its terminator.")
    capabilities = native.capabilities()
    if type(capabilities.get("processor_groups")) is not int or capabilities["processor_groups"] != 1:
        raise AffinityError("Only single-processor-group systems are supported by this release.")
    selected = validate_mask(selected, capabilities["available_mask"], capabilities["pointer_bits"])
    duplicates = native.duplicates(executable)
    if duplicates["pids"] and not allow_existing:
        raise AffinityError("A visible process with this exact executable path is already running; --allow-existing is an explicit override.",
                            {"matching_pids": list(duplicates["pids"]), "visibility_incomplete": bool(duplicates["unqueryable"] or duplicates["truncated"])})
    return {"schema": 1, "action": "plan", "launch_requested": False,
            "executable": executable, "cwd": working, "args": arguments,
            "command_line": command_line, "mask": hex(selected),
            "cores": [i for i in range(capabilities["pointer_bits"]) if selected & (1 << i)],
            "available_mask": hex(capabilities["available_mask"]),
            "pointer_bits": capabilities["pointer_bits"], "processor_groups": capabilities["processor_groups"],
            "duplicates": duplicates, "allow_existing": allow_existing, "no_window": no_window,
            "limits": "Duplicate visibility is best effort and not atomic. A successful launch does not prove application readiness."}


def launch(plan, wait_seconds=None, backend=None):
    if wait_seconds is not None and (isinstance(wait_seconds, bool) or not isinstance(wait_seconds, (float, int))
                                     or not math.isfinite(wait_seconds) or not 0 < wait_seconds <= 300):
        raise AffinityError("Wait must be finite, greater than zero and at most 300 seconds.")
    if not isinstance(plan, dict) or type(plan.get("schema")) is not int or plan["schema"] != 1:
        raise AffinityError("Launch requires a supported plan.")
    native = _backend(backend)
    try:
        checked = make_plan(plan["executable"], mask=plan["mask"], cwd=plan["cwd"], args=plan["args"],
                            allow_existing=plan["allow_existing"], no_window=plan["no_window"], backend=native)
    except KeyError:
        raise AffinityError("Launch plan is missing required fields.") from None
    child = None
    resumed = False
    receipt = {**checked, "action": "launch", "launch_requested": True, "resumed": False,
               "wait_timed_out": False, "child_exit_code": None}
    try:
        child = native.create(checked)
        receipt["pid"] = child.pid
        child.set_mask(int(checked["mask"], 16))
        actual = child.get_mask()
        if actual != int(checked["mask"], 16):
            raise AffinityError("Child affinity readback did not match; its primary thread was not resumed.")
        receipt["mask_before_resume"] = hex(actual)
        priority = child.get_priority()
        if priority != 0x20:
            raise AffinityError("Child priority was not normal; its primary thread was not resumed.")
        receipt["priority_before_resume"] = "normal"
        if child.resume() != 1:
            raise AffinityError("Primary-thread resume returned an unexpected suspend count.")
        resumed = True
        receipt["resumed"] = True
        if wait_seconds is not None:
            if child.wait(wait_seconds):
                receipt["child_exit_code"] = child.exit_code()
            else:
                receipt["wait_timed_out"] = True
        return receipt
    except BaseException as error:
        if child is not None and not resumed:
            cleanup = {**(error.details if isinstance(error, AffinityError) else {}),
                       "pid": child.pid, "terminated_created_child": False, "cleanup_confirmed": False}
            try:
                child.terminate()
                cleanup["terminated_created_child"] = True
                cleanup["cleanup_confirmed"] = child.wait(5)
            except Exception:
                pass
            if isinstance(error, KeyboardInterrupt):
                raise AffinityError("Interrupted before launch completed; inspect created-child cleanup status.", cleanup) from None
            message = str(error) if isinstance(error, AffinityError) else "Native launch setup failed."
            raise AffinityError(message, cleanup) from None
        if isinstance(error, KeyboardInterrupt) and resumed:
            raise AffinityError("Wait interrupted; the already resumed application was left running.",
                                {"pid": child.pid, "resumed": True, "interrupted": True}) from None
        if isinstance(error, AffinityError) and resumed:
            raise AffinityError(str(error), {**error.details, "pid": child.pid, "resumed": True}) from None
        if isinstance(error, Exception) and not isinstance(error, AffinityError):
            raise AffinityError("Native launch operation failed.",
                                {"pid": child.pid, "resumed": True} if resumed else {}) from None
        raise
    finally:
        if child is not None:
            active_error = sys.exc_info()[1]
            try:
                child.close()
            except AffinityError as close_error:
                if isinstance(active_error, AffinityError):
                    active_error.details.update(close_error.details)
                elif active_error is None:
                    raise AffinityError(str(close_error), {**close_error.details, "pid": child.pid, "resumed": resumed}) from None
