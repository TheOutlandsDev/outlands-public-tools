"""Read a caller-selected socket table and print its parsed records."""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

from .ports import parse_proc_net, parse_windows_netstat


MAX_INPUT_BYTES = 4 * 1024 * 1024
_FORMATS = ("windows-netstat", "linux-tcp", "linux-tcp6", "linux-udp", "linux-udp6")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "Invalid arguments. See --help for usage.\n")


def _regular_entry(info: os.stat_result) -> bool:
    return stat.S_ISREG(info.st_mode) and not (
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _read_input(path: Path) -> str:
    if path.drive.startswith("\\\\") or path.anchor == "//":
        raise ValueError("Expected a local file.")
    before = path.lstat()
    if not _regular_entry(before) or before.st_size > MAX_INPUT_BYTES:
        raise ValueError("Expected a bounded regular file.")
    if os.name == "posix":
        resolved = path.resolve(strict=True)
        if any(resolved.is_relative_to(directory) for directory in ("/dev", "/proc", "/sys")):
            raise ValueError("Expected a saved table.")
    flags = (
        os.O_RDONLY | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as source:
        opened = os.fstat(source.fileno())
        if not _regular_entry(opened) or not os.path.samestat(before, opened):
            raise ValueError("Input changed before it was opened.")
        data = source.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds the size limit.")
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    text = data.decode(encoding)
    if _CONTROL.search(text):
        raise ValueError("Expected a text table.")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser(prog="opskit", description="Parse a saved socket table.")
    commands = parser.add_subparsers(dest="command", required=True)
    ports = commands.add_parser("ports", help="Read a saved table from a local file.")
    ports.add_argument("--format", required=True, choices=_FORMATS)
    ports.add_argument("--input", required=True, type=Path)
    ports.add_argument("--include-connections", action="store_true")
    args = parser.parse_args(argv)

    try:
        content = _read_input(args.input)
    except (OSError, RuntimeError, ValueError):
        print("Could not read the supplied socket table file.", file=sys.stderr)
        return 2
    if args.format == "windows-netstat":
        rows = parse_windows_netstat(content, include_connections=args.include_connections)
    else:
        protocol = args.format.removeprefix("linux-")
        rows = parse_proc_net(content, protocol, include_connections=args.include_connections)
    print(json.dumps({"rows": rows}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
