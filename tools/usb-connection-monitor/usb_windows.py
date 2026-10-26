"""Original MIT Windows read-only PnP adapter, isolated and bounded per query."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import threading
import time
from inspection_support import TextError, strict_json

MAX_DEVICES = 512
MAX_OUTPUT = 256 * 1024
QUERY_SECONDS = 5

# Fixed source, no string interpolation from selected devices or user input.
# A failed/incomplete query is unknown, never evidence of device absence.
SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$rows = @(PnpDevice\Get-PnpDevice -PresentOnly -ErrorAction Stop |
    Where-Object { $_.InstanceId -like 'USB\*' } |
    Select-Object -First 513)
if ($rows.Count -gt 512) { exit 21 }
$result = @($rows | ForEach-Object {
    $id = [string]$_.InstanceId
    $name = [string]$_.FriendlyName
    if ($id.Length -gt 512 -or $name.Length -gt 256) { exit 22 }
    @{ id = $id; name = $name }
})
ConvertTo-Json -InputObject $result -Depth 3 -Compress
'''


def valid_device_id(value):
    if not (type(value) is str and 5 <= len(value) <= 512 and value[:4].upper() == 'USB\\'
            and all(ord(char) >= 32 and ord(char) != 127 for char in value)):
        raise TextError('DEVICE_ID_INVALID')
    return value


def parse_snapshot(data):
    if type(data) is not bytes or len(data) > MAX_OUTPUT:
        raise TextError('QUERY_OUTPUT_LIMIT')
    try:
        value = strict_json(data, MAX_OUTPUT, 4000, 1024)
        if type(value) is not list or len(value) > MAX_DEVICES:
            raise TextError('QUERY_INVALID')
        seen = set()
        result = []
        for row in value:
            if type(row) is not dict or set(row) != {'id', 'name'}:
                raise TextError('QUERY_INVALID')
            identity = valid_device_id(row['id'])
            name = row['name']
            if type(name) is not str or len(name) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in name):
                raise TextError('QUERY_INVALID')
            if identity.casefold() in seen:
                raise TextError('QUERY_INVALID')
            seen.add(identity.casefold())
            result.append({'id': identity, 'name': name or 'Unnamed USB entry'})
        return sorted(result, key=lambda row: (row['name'].casefold(), row['id'].casefold()))
    except (TextError, ValueError, TypeError, KeyError):
        raise TextError('QUERY_INVALID') from None


def powershell_path():
    if os.name != 'nt':
        raise TextError('WINDOWS_REQUIRED')
    # Fixed Windows system location; never search PATH or load a user profile.
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    size = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
    if not size or size >= len(buffer):
        raise TextError('POWERSHELL_UNAVAILABLE')
    path = Path(buffer.value) / 'WindowsPowerShell/v1.0/powershell.exe'
    if not path.is_file():
        raise TextError('POWERSHELL_UNAVAILABLE')
    return path


def bounded_process(command, stop=None, timeout=QUERY_SECONDS, maximum=MAX_OUTPUT):
    """Private capture; never forward raw stdout/stderr or unbounded diagnostics."""
    stop = stop if stop is not None else threading.Event()
    if stop.is_set():
        raise TextError('CANCELLED')
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, shell=False,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    chunks = []
    overflow = threading.Event()
    failed = threading.Event()
    def read():
        total = 0
        try:
            while True:
                block = process.stdout.read(4096)
                if not block:
                    break
                total += len(block)
                if total > maximum:
                    overflow.set()
                    break
                chunks.append(block)
        except (OSError, ValueError):
            failed.set()
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    error = None
    try:
        while process.poll() is None:
            if stop.is_set():
                error = 'CANCELLED'
                break
            if overflow.is_set():
                error = 'QUERY_OUTPUT_LIMIT'
                break
            if time.monotonic() >= deadline:
                error = 'QUERY_TIMEOUT'
                break
            stop.wait(.025)
        if error is not None and process.poll() is None:
            process.kill()
        process.wait(timeout=2)
        reader.join(timeout=2)
        if reader.is_alive():
            error = error or 'QUERY_FAILED'
        if overflow.is_set():
            error = error or 'QUERY_OUTPUT_LIMIT'
        if failed.is_set() or process.returncode != 0:
            error = error or 'QUERY_FAILED'
        if error:
            raise TextError(error)
        return b''.join(chunks)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        process.stdout.close()
        reader.join(timeout=2)


def query_devices(stop=None):
    try:
        command = [str(powershell_path()), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', SCRIPT]
        return parse_snapshot(bounded_process(command, stop=stop))
    except TextError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise TextError('QUERY_FAILED') from None
