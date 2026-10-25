#!/usr/bin/env python3
"""Create a new private fictional presence fixture without executing its files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

REPOSITORY = Path(__file__).resolve().parents[3]
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit
    for prefix in ("com", "lpt")
    for digit in "123456789\u00b9\u00b2\u00b3"
}


class FixtureError(ValueError):
    pass


def refuse(code):
    raise FixtureError(code)


def ordinary_directory(path):
    info = path.lstat()
    if (
        stat.S_ISLNK(info.st_mode)
        or getattr(info, "st_file_attributes", 0) & 0x400
        or not stat.S_ISDIR(info.st_mode)
    ):
        refuse("ORDINARY_DIRECTORY_REQUIRED")
    return info


def directory_identity(info):
    if not info.st_ino:
        refuse("DESTINATION_BOUNDARY_UNVERIFIED")
    return info.st_dev, info.st_ino


def destination_path(value):
    raw = Path(value)
    if (
        not raw.is_absolute()
        or ".." in raw.parts
        or raw.drive.startswith("\\\\")
        or raw.anchor == "//"
    ):
        refuse("ABSOLUTE_LOCAL_DESTINATION_REQUIRED")
    path = Path(os.path.abspath(raw))
    if path.parent == path or path.is_relative_to(REPOSITORY):
        refuse("EXTERNAL_DESTINATION_REQUIRED")
    for part in raw.parts:
        if part == raw.anchor:
            continue
        if (
            part.endswith((".", " "))
            or part.split(".")[0].casefold() in RESERVED
            or any(
                ord(char) < 32 or ord(char) == 127 or char in '\\:<>"|?*'
                for char in part
            )
        ):
            refuse("PORTABLE_DESTINATION_REQUIRED")
    repository_id = directory_identity(ordinary_directory(REPOSITORY))
    for ancestor in reversed([path.parent, *path.parent.parents]):
        info = ordinary_directory(ancestor)
        if directory_identity(info) == repository_id:
            refuse("EXTERNAL_DESTINATION_REQUIRED")
    return path


def write_new(path, raw, *, executable=False):
    ordinary_directory(path.parent)
    mode = 0o700 if executable else 0o600
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    with os.fdopen(os.open(path, flags, mode), "wb") as stream:
        if executable and os.name != "nt":
            os.fchmod(stream.fileno(), mode)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def create_fixture(destination):
    target = destination_path(destination)
    target.mkdir(mode=0o700)
    for name in ("inputs", "programs", "workspace"):
        ordinary_directory(target)
        (target / name).mkdir(mode=0o700)
    write_new(
        target / "inputs/fictional.txt",
        b"Fictional prerequisite input. No user records.\n",
    )
    if os.name == "nt":
        program = "fictional-tool.cmd"
        raw = b"@echo off\r\nrem Fictional presence fixture; do not execute.\r\nexit /b 73\r\n"
    else:
        program = "fictional-tool"
        raw = b"#!/bin/sh\n# Fictional presence fixture; do not execute.\nexit 73\n"
    write_new(target / "programs" / program, raw, executable=True)
    return {
        "status": "CREATED",
        "files_created": 2,
        "child_directories_created": 3,
        "fixture_executed": False,
    }


class Parser(argparse.ArgumentParser):
    def error(self, message):
        refuse("INVALID_ARGUMENTS")


def main(argv=None):
    parser = Parser(prog="make_fixture.py", description=__doc__)
    parser.add_argument(
        "--destination",
        required=True,
        help="New absolute external fixture directory; parent must exist",
    )
    try:
        args = parser.parse_args(argv)
        result = create_fixture(args.destination)
        print(json.dumps(result, sort_keys=True))
        return 0
    except FixtureError as error:
        print(
            json.dumps(
                {"status": "ERROR", "code": str(error), "fixture_executed": False}
            )
        )
        return 2
    except (OSError, ValueError, TypeError, UnicodeError):
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "code": "FIXTURE_REFUSED_OR_FAILED",
                    "fixture_executed": False,
                }
            )
        )
        return 2
    except KeyboardInterrupt:
        print(
            json.dumps(
                {"status": "ERROR", "code": "INTERRUPTED", "fixture_executed": False}
            )
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
