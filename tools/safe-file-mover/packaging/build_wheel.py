"""Build a wheel from an explicit text-only allowlist in a fresh staging tree."""
import argparse
import base64
import csv
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("__init__.py", "__main__.py", "cli.py", "core.py", "gui.py",
           "journal.py", "windows_fs.py")
INPUTS = ("pyproject.toml", "LICENSE", "USAGE.md") + tuple(
    "safe_file_mover/" + name for name in MODULES
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.absolute()
    out.mkdir(parents=True, exist_ok=False)
    if {p.name for p in (ROOT / "safe_file_mover").glob("*.py")} != set(MODULES):
        raise RuntimeError("PACKAGE_ALLOWLIST_CHANGED")
    # LF normalization and a fixed ZIP timestamp make Windows/Linux builds comparable.
    with tempfile.TemporaryDirectory(prefix="mover-build-") as temporary:
        stage = Path(temporary)
        for name in INPUTS:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8"))
        env = dict(os.environ, SOURCE_DATE_EPOCH="315532800", PYTHONHASHSEED="0")
        subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation",
                        "--outdir", str(out), str(stage)], env=env, check=True)
    wheels = list(out.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("ONE_WHEEL_REQUIRED")
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        dist = "safe_file_mover-0.2.1.dist-info/"
        expected = {"safe_file_mover/" + name for name in MODULES} | {
            dist + name for name in ("METADATA", "WHEEL", "entry_points.txt",
                                     "top_level.txt", "RECORD", "licenses/LICENSE")
        }
        if names != expected:
            raise RuntimeError("WHEEL_MEMBER_ALLOWLIST_CHANGED")
        # Backends use host-specific metadata newlines and ZIP attributes.
        # All allowlisted members are UTF-8 text. Normalize them, regenerate
        # RECORD from the resulting bytes and use stored ZIP entries so zlib
        # versions cannot change the release hash across interpreters/hosts.
        members = {name: archive.read(name).decode("utf-8").replace("\r\n", "\n").encode("utf-8")
                   for name in names if name != dist + "RECORD"}
    order = sorted(members, key=lambda name: (name.startswith(dist), name))
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name in order:
        data = members[name]
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
        writer.writerow((name, "sha256=" + digest, len(data)))
    writer.writerow((dist + "RECORD", "", ""))
    members[dist + "RECORD"] = record.getvalue().encode("utf-8")
    canonical = io.BytesIO()
    with zipfile.ZipFile(canonical, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in order + [dist + "RECORD"]:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, members[name])
    wheel.write_bytes(canonical.getvalue())
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    (out / "SHA256SUMS.txt").write_text(digest + "  " + wheel.name + "\n", encoding="ascii", newline="\n")
    print("WHEEL_SHA256=" + digest)


if __name__ == "__main__":
    main()
