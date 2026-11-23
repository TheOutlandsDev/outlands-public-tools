"""Build ordinary Python wheels from the pinned public Grouped Reports source ZIP."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERSION = "1.0.0"
SOURCE_REVISION = "9a6c94affad04b2634fe7f3a7af0f204eb28313d"
SOURCE_DIGEST = "11c6c5d39a120ee5f8dc0c9b8c41142dcc30a866ab08d4d75fa8a68bdbfdb2c6"
SHARED = ("toolkit.py", "native_windows.py", "decision_core.py", "group_core.py")
DISTRIBUTION_PREFIX = "outlands-"
COLLECTION = "outlands-grouped-reports-collection"
LOCAL_IMPORT = re.compile(
    r"^([ \t]*)import (toolkit|native_windows|decision_core|group_core)( as [a-z]+)?$",
    flags=re.MULTILINE,
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("ascii")


def component_guide():
    return json.loads((HERE / "components.json").read_text(encoding="utf-8"))


def source_members(source_zip):
    prefix = f"outlands-grouped-reports-4-{VERSION}/"
    if source_zip is None:
        spec = importlib.util.spec_from_file_location(
            "grouped_reports_source", ROOT / "downloads/grouped-reports-4/build.py"
        )
        source_builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(source_builder)
        plan = source_builder.plan()
        if plan["source_revision"] != SOURCE_REVISION:
            raise ValueError("GROUPED_REPORTS_SOURCE_REVISION_CHANGED")
        raw = source_builder.archive_bytes(
            plan, source_builder.payload(plan, source_builder.source_files(plan))
        )
    else:
        # The reviewed ZIP is about 200 KiB. Bound even an untrusted local input.
        with source_zip.open("rb") as handle:
            raw = handle.read(1_000_001)
    if len(raw) > 1_000_000 or digest(raw) != SOURCE_DIGEST:
        raise ValueError("GROUPED_REPORTS_SOURCE_ZIP_DIGEST_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return {
            name.removeprefix(prefix): archive.read(name)
            for name in archive.namelist()
            if name.startswith(prefix)
        }


def module_name(distribution):
    return distribution.replace("-", "_")


def wheel_name(distribution):
    return f"{module_name(distribution)}-{VERSION}-py3-none-any.whl"


def isolated_source(raw):
    text = raw.decode("utf-8")
    rewritten = LOCAL_IMPORT.sub(
        lambda match: f"{match[1]}from . import {match[2]}{match[3] or ''}", text
    )
    return rewritten.encode("utf-8")


def zip_bytes(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def build_wheel(distribution, summary, description, members, scripts, license_bytes,
                requires_python, dependencies=()):
    info = f"{module_name(distribution)}-{VERSION}.dist-info"
    metadata = [
        "Metadata-Version: 2.4",
        f"Name: {distribution}",
        f"Version: {VERSION}",
        f"Summary: {summary}",
        f"Requires-Python: {requires_python}",
        "License-Expression: MIT",
        "License-File: LICENSE",
        "Description-Content-Type: text/markdown",
    ]
    metadata.extend(f"Requires-Dist: {dependency}" for dependency in dependencies)
    contents = {
        **members,
        f"{info}/METADATA": ("\n".join(metadata) + "\n\n" + description).encode("utf-8"),
        f"{info}/WHEEL": b"Wheel-Version: 1.0\nGenerator: outlands-grouped-reports\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{info}/entry_points.txt": (
            "[console_scripts]\n" + "".join(f"{key} = {value}\n" for key, value in scripts.items())
        ).encode("ascii"),
        f"{info}/licenses/LICENSE": license_bytes,
    }
    rows = io.StringIO(newline="")
    record = csv.writer(rows, lineterminator="\n")
    for name, raw in sorted(contents.items()):
        encoded_hash = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=")
        record.writerow((name, "sha256=" + encoded_hash.decode("ascii"), len(raw)))
    record.writerow((f"{info}/RECORD", "", ""))
    contents[f"{info}/RECORD"] = rows.getvalue().encode("ascii")
    return zip_bytes(contents)


def demo_source(entry):
    return (
        '"""Run the bundled fictional example using the installed Python API."""\n'
        "import json\n"
        "from importlib.resources import files\n\n"
        f"from . import {entry}\n\n\n"
        "def main():\n"
        '    raw = files(__package__).joinpath("examples", "input.json").read_bytes()\n'
        f"    report = {entry}.check(raw)\n"
        "    print(json.dumps(report, sort_keys=True))\n"
        '    return 0 if report["status"] == "PASS" else 1\n'
    ).encode("ascii")


def build_component(component, source, requires_python):
    tool = component["id"]
    entry = component["source_entry"].removesuffix(".py")
    distribution = DISTRIBUTION_PREFIX + tool
    package = module_name(distribution)
    prefix = f"tools/{tool}/"
    license_bytes = source[prefix + "LICENSE"]
    names = (*SHARED, entry + ".py")
    members = {
        f"{package}/__init__.py": b'"""OUTLANDS offline grouped report checks."""\n',
        f"{package}/demo.py": demo_source(entry),
        **{f"{package}/{name}": isolated_source(source[prefix + name]) for name in names},
    }
    examples = (component["example_input"], component["example_review_input"])
    for path in filter(None, examples):
        members[f"{package}/examples/{Path(path).name}"] = source[path]
    for name in ("ORIGINS.md", "IO-SAFETY.md"):
        members[f"{package}/{name}"] = source[prefix + name]
    description = (
        f"# Installed {tool}\n\n"
        f"Command: `{component['command']} --input FILE`. "
        f"Python API: `{component['python_api']}`. "
        f"The offline fictional demo is `{component['command']}-demo`. "
        f"Use the repository component guide for expected status and limits.\n\n"
        + source[prefix + "README.md"].decode("utf-8")
    )
    return build_wheel(
        distribution, component["purpose"], description, members,
        {component["command"]: f"{package}.{entry}:main",
         f"{component['command']}-demo": f"{package}.demo:main"},
        license_bytes, requires_python,
    )


def build_collection(guide, source):
    package = module_name(COLLECTION)
    commands = tuple(component["command"] for component in guide["components"])
    catalog = (
        '"""List the command entry points in the installed collection."""\n'
        f"COMMANDS = {commands!r}\n\n\n"
        "def main():\n"
        '    print("\\n".join(COMMANDS))\n'
    ).encode("ascii")
    license_bytes = source["tools/grouped-report-contract-checker/LICENSE"]
    return build_wheel(
        COLLECTION, "Exact-version collection of four offline grouped report tools.",
        "# OUTLANDS Grouped Reports\n\nRun `outlands-grouped-reports` to list the tools.\n",
        {f"{package}/__init__.py": b'"""OUTLANDS Grouped Reports collection."""\n',
         f"{package}/catalog.py": catalog},
        {guide["collection"]["command"]: f"{package}.catalog:main"},
        license_bytes, guide["python"],
        [component["package"] for component in guide["components"]],
    )


def build(output, source_zip=None):
    output = output.resolve()
    if not output.is_dir() or output.is_relative_to(ROOT) or any(output.iterdir()):
        raise ValueError("OUTPUT_MUST_BE_EMPTY_DIRECTORY_OUTSIDE_REPOSITORY")
    source = source_members(source_zip)
    guide = component_guide()
    wheels = {
        wheel_name(component["command"]): build_component(component, source, guide["python"])
        for component in guide["components"]
    }
    wheels[wheel_name(COLLECTION)] = build_collection(guide, source)
    manifest = {
        "format": "outlands-grouped-reports-wheel-v1",
        "version": VERSION,
        "source_revision": SOURCE_REVISION,
        "source_zip_sha256": SOURCE_DIGEST,
        "wheels": [
            {"filename": name, "sha256": digest(raw)}
            for name, raw in sorted(wheels.items())
        ],
    }
    checksums = "".join(f"{row['sha256']}  {row['filename']}\n" for row in manifest["wheels"])
    assets = {**wheels, "MANIFEST.json": encoded(manifest), "SHA256SUMS.txt": checksums.encode("ascii")}
    for name, raw in sorted(assets.items()):
        with (output / name).open("xb") as handle:
            handle.write(raw)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-zip", type=Path, help="Use the verified public source ZIP instead of Git history")
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.source_zip), sort_keys=True))
