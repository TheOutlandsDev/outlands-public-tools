#!/usr/bin/env python3
"""Verify this fixed public source inventory; no private-store inspection."""

import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parent
CONTRACT_SHA256 = "5c81fb4c74aa7126fc7c4e81b30aca138353c8e79ac6edcd5b9d488e72f0439d"
FILES = {
    ".gitattributes",
    ".gitignore",
    "LICENSE",
    "THIRD-PARTY-NOTICES.txt",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "workbench.py",
    "workbench_core.py",
    "workbench_gui.py",
    "record_contract.py",
    "source_check.py",
    "docs/FORMAT.md",
    "docs/PROVENANCE.md",
    "docs/VALIDATION.md",
    "examples/README.md",
    "examples/records.json",
    "tests/test_core.py",
    "tests/test_gui.py",
}


def check():
    actual = {}
    stack = [ROOT]
    entries = 0
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as iterator:
            for item in iterator:
                entries += 1
                if entries > 64:
                    raise ValueError("SOURCE_ENTRY_LIMIT")
                path = Path(item.path)
                info = path.lstat()
                if (
                    stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400
                ):
                    raise ValueError("SOURCE_LINK_REFUSED")
                if stat.S_ISDIR(info.st_mode):
                    stack.append(path)
                    continue
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_size > 512 * 1024
                ):
                    raise ValueError("SOURCE_NODE_REFUSED")
                name = path.relative_to(ROOT).as_posix()
                if name not in FILES | {"SOURCE-MANIFEST.json"}:
                    raise ValueError("UNLISTED_SOURCE_FILE")
                raw = path.read_bytes()
                raw.decode("utf-8")
                if b"\0" in raw:
                    raise ValueError("SOURCE_BINARY_REFUSED")
                actual[name] = dict(
                    path=name, size=len(raw), sha256=hashlib.sha256(raw).hexdigest()
                )
    if set(actual) != FILES | {"SOURCE-MANIFEST.json"}:
        raise ValueError("SOURCE_FILE_SET_MISMATCH")
    if sum(row["size"] for row in actual.values()) > 4 * 1024 * 1024:
        raise ValueError("SOURCE_TOTAL_LIMIT")
    manifest = json.loads((ROOT / "SOURCE-MANIFEST.json").read_text(encoding="utf-8"))
    if set(manifest) != {
        "schema_version",
        "component_version",
        "public_contract_sha256",
        "inventory",
    }:
        raise ValueError("MANIFEST_SCHEMA_INVALID")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["component_version"] != "0.1.0"
        or manifest["public_contract_sha256"] != CONTRACT_SHA256
    ):
        raise ValueError("MANIFEST_SCHEMA_INVALID")
    expected = [actual[name] for name in sorted(FILES)]
    if (
        manifest["inventory"] != expected
        or actual["record_contract.py"]["sha256"] != CONTRACT_SHA256
    ):
        raise ValueError("SOURCE_HASH_MISMATCH")
    return dict(status="PASS", files=len(FILES), scope="FIXED_PUBLIC_SOURCE_ONLY")


if __name__ == "__main__":
    try:
        result = check()
        code = 0
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        result = dict(status="FAIL", code="SOURCE_GATE_FAILED")
        code = 1
    print(json.dumps(result, sort_keys=True))
    sys.exit(code)
