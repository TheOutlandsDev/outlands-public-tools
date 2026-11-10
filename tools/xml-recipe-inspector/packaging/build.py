"""Build a deterministic source ZIP from an exact reviewed text allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
FILES = (".gitattributes", ".gitignore", "LICENSE", "README.md", "README.txt", "USAGE.md", "VERSION",
         "xml_recipe_inspector.py", "xml_windows.py",
         "docs/WINDOWS.md", "docs/PYTHON315.md", "tests/test_xml_recipe_inspector.py",
         "tests/test_xml_windows.py", "tests/test_download_cli.py", "packaging/build.py", "packaging/qualify.py")


def build(out):
    assert out.is_absolute() and not out.exists() and not out.is_relative_to(ROOT)
    assert (ROOT / "VERSION").read_text().strip() == VERSION
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    members = {}
    for name in FILES:
        path = ROOT / name
        assert not path.is_symlink()
        data = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
        expected = subprocess.check_output(["git", "show", "HEAD:tools/xml-recipe-inspector/" + name], cwd=ROOT)
        assert data == expected, "COMMIT_REVIEWED_SOURCE_BEFORE_BUILD"
        assert b"\x00" not in data and len(data) <= 1024 * 1024
        members[name] = data
    manifest = dict(schema=1, package="xml-recipe-inspector", version=VERSION,
                    files=[dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                           for name, data in sorted(members.items())])
    members["SOURCE-MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    out.mkdir()
    filename = "xml-recipe-inspector-" + VERSION + ".zip"
    archive = out / filename
    prefix = "xml-recipe-inspector-" + VERSION + "/"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED) as target:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(prefix + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            target.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    receipt = dict(schema=1, package="xml-recipe-inspector", version=VERSION, source_revision=revision,
                   filename=filename, bytes=archive.stat().st_size, files=len(members), sha256=digest)
    (out / "build-manifest.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "SHA256SUMS.txt").write_text(digest + "  " + filename + "\n", encoding="ascii", newline="\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    build(parser.parse_args().out)
