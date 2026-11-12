"""Download or verify only the reviewed binary dependency artifacts for this lane."""
if not __debug__:
    raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import struct
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {"python-docx": "1.2.0", "lxml": "6.1.3", "typing_extensions": "4.16.0"}
INSTALLER_VERSION = "26.3"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def selection():
    assert sys.version_info.major == 3 and sys.version_info.minor in (12, 13, 14, 15)
    assert sys.version_info.releaselevel == "final" and struct.calcsize("P") == 8
    assert platform.machine().lower() in ("amd64", "x86_64")
    system = "windows" if sys.platform == "win32" else "ubuntu"
    assert sys.platform in ("win32", "linux")
    metadata = json.loads((ROOT / "dependency-locks/DEPENDENCIES.json").read_text(encoding="utf-8"))
    assert metadata["schema"] == 1 and metadata["package"] == "document-builders"
    assert metadata["dependency_versions"] == VERSIONS
    assert metadata["wheel_payloads_bundled"] is False and metadata["source_builds_permitted"] is False
    key = system + "-cp3" + str(sys.version_info.minor)
    lane = metadata["lanes"][key]
    assert lane["platform"] == sys.platform and lane["architecture"] == "x86_64"
    assert lane["python_minor"] == "3." + str(sys.version_info.minor)
    installer = metadata["installer"]
    assert installer["project"] == "pip" and installer["version"] == INSTALLER_VERSION and installer["runtime_dependency"] is False
    artifacts = [*lane["wheels"], installer["artifact"]]
    assert len(artifacts) == len({x["filename"] for x in artifacts}) == 4
    assert {x["project"]: x["version"] for x in lane["wheels"]} == VERSIONS
    for item in (lane, installer):
        name = item["lock"]
        assert re.fullmatch(r"[a-z0-9_.-]+\.txt", name)
        assert sha((ROOT / "dependency-locks" / name).read_bytes()) == item["lock_sha256"]
    for item in artifacts:
        assert re.fullmatch(r"[A-Za-z0-9_.+-]+\.whl", item["filename"])
        assert re.fullmatch("[a-f0-9]{64}", item["sha256"])
        assert type(item["bytes"]) is int and 0 < item["bytes"] <= 25 * 1024 * 1024
        url = urllib.parse.urlsplit(item["url"])
        assert url.scheme == "https" and url.hostname == "files.pythonhosted.org"
        assert urllib.parse.unquote(url.path.rsplit("/", 1)[-1]) == item["filename"]
        assert not url.query and not url.fragment
    return key, lane, installer, artifacts

def check_wheelhouse(folder):
    key, lane, installer, artifacts = selection()
    assert folder.is_absolute() and folder.is_dir() and not folder.is_symlink()
    assert not getattr(folder, "is_junction", lambda: False)()
    assert {p.name for p in folder.iterdir()} == {x["filename"] for x in artifacts}
    for item in artifacts:
        path = folder / item["filename"]
        assert path.is_file() and not path.is_symlink() and path.stat().st_nlink == 1
        assert path.stat().st_size == item["bytes"] and sha(path.read_bytes()) == item["sha256"]
    return key, lane, installer, artifacts

def download(folder):
    key, lane, installer, artifacts = selection()
    assert folder.is_absolute() and folder.parent.is_dir() and not os.path.lexists(folder)
    assert not folder.resolve().is_relative_to(ROOT.resolve())
    folder.mkdir()
    for item in artifacts:
        request = urllib.request.Request(item["url"], headers={"User-Agent": "OUTLANDS-reviewed-dependency-download"})
        with urllib.request.urlopen(request, timeout=60) as response:
            final = urllib.parse.urlsplit(response.url)
            assert final.scheme == "https" and final.hostname == "files.pythonhosted.org"
            data = response.read(item["bytes"] + 1)
        assert len(data) == item["bytes"] and sha(data) == item["sha256"], "DEPENDENCY_ARTIFACT_DIFFERS"
        with (folder / item["filename"]).open("xb") as handle:
            handle.write(data)
    check_wheelhouse(folder)
    print(json.dumps(dict(status="PASS", lane=key, artifacts=4, bytes=sum(x["bytes"] for x in artifacts),
                          dependency_versions=VERSIONS, installer_version=INSTALLER_VERSION)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--download", type=Path, help="Create a new external wheelhouse from exact pinned HTTPS URLs")
    modes.add_argument("--wheelhouse", type=Path, help="Verify an existing exact four-wheel inventory")
    args = parser.parse_args()
    if args.download is not None:
        download(args.download)
    else:
        key, lane, installer, artifacts = check_wheelhouse(args.wheelhouse)
        print(json.dumps(dict(status="PASS", lane=key, artifacts=len(artifacts))))
