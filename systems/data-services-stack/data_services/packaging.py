"""Deterministic source-only ZIPs from an explicit, verified public manifest."""
import io
from pathlib import PurePosixPath
import zipfile

from . import files
from .contracts import StackError, canonical, decode, digest

MANIFEST = "SOURCE-MANIFEST.json"


def source_files():
    root = files.APPLICATION
    manifest_raw = files.read(root / MANIFEST, 1048576)
    manifest = decode(manifest_raw)
    if (type(manifest) is not dict or set(manifest) != {"format", "files"}
            or manifest["format"] != "outlands-data-services-source-v1"
            or type(manifest["files"]) is not list or not 1 <= len(manifest["files"]) <= 64):
        raise StackError("SOURCE_MANIFEST_INVALID")
    output = {}
    folded = set()
    for row in manifest["files"]:
        if type(row) is not dict or set(row) != {"path", "size", "sha256"} or type(row["path"]) is not str:
            raise StackError("SOURCE_MANIFEST_INVALID")
        name = row["path"]
        path = PurePosixPath(name)
        if (path.is_absolute() or path.as_posix() != name or not path.parts
                or any(part in (".", "..") for part in path.parts) or "\\" in name or ":" in name
                or name == MANIFEST or name.casefold() in folded
                or type(row["size"]) is not int or not 0 <= row["size"] <= 2097152):
            raise StackError("SOURCE_MANIFEST_INVALID")
        raw = files.read(root.joinpath(*path.parts), row["size"])
        if len(raw) != row["size"] or digest(raw) != row["sha256"]:
            raise StackError("SOURCE_HASH_MISMATCH")
        output[name] = raw
        folded.add(name.casefold())
    output[MANIFEST] = manifest_raw
    return output


def source_check():
    selected = source_files()
    return dict(status="PASS", files=len(selected),
                source_manifest_sha256=digest(selected[MANIFEST]))


def package(destination):
    selected = source_files()
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(selected.items()):
            info = zipfile.ZipInfo("data-services-stack/" + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    raw = target.getvalue()
    files.write_new(files.selected(destination, output=True), raw)
    return dict(status="PACKAGED", files=len(selected), bytes=len(raw), sha256=digest(raw))
