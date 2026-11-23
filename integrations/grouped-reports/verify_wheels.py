"""Verify the pinned wheel assets and install them in isolated offline environments."""
from __future__ import annotations

import argparse
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

from build_wheels import (
    COLLECTION, HERE, ROOT, SOURCE_DIGEST, SOURCE_REVISION, VERSION,
    component_guide, digest, module_name, wheel_name,
)

TAG = f"grouped-reports-wheels-v{VERSION}"
EXIT_STATUS = {"PASS": 0, "REVIEW_REQUIRED": 1}
NO_EFFECT_FIELDS = (
    "database_opened", "network_requests_performed", "source_completeness_verified",
    "sql_executed", "target_changes_performed",
)
API_RUNNER = (
    "import importlib,json,sys; from pathlib import Path; "
    "operation=importlib.import_module(sys.argv[1]).check; "
    "print(json.dumps(operation(Path(sys.argv[2]).read_bytes()), sort_keys=True))"
)


def require(condition, error):
    if not condition:
        raise ValueError(error)


def check_assets(directory, guide):
    plan = json.loads((HERE / "release.json").read_text(encoding="utf-8"))
    wheels = {wheel_name(record["command"]) for record in guide["components"]} | {wheel_name(COLLECTION)}
    expected = wheels | {"MANIFEST.json", "SHA256SUMS.txt"}
    require(plan["tag"] == TAG and plan["version"] == VERSION and plan["source_revision"] == SOURCE_REVISION,
            "RELEASE_IDENTITY_MISMATCH")
    require(set(plan["assets"]) == expected, "RELEASE_MEMBERS_MISMATCH")
    require({item.name for item in directory.iterdir()} == expected, "ARTIFACT_MEMBERS_MISMATCH")
    for name, pin in plan["assets"].items():
        path = directory / name
        require(not path.is_symlink() and path.is_file() and path.stat().st_size < 1_000_000
                and digest(path.read_bytes()) == pin, f"ARTIFACT_INTEGRITY_MISMATCH: {name}")
    manifest = json.loads((directory / "MANIFEST.json").read_text(encoding="utf-8"))
    expected_manifest = {
        "format": "outlands-grouped-reports-wheel-v1",
        "version": VERSION,
        "source_revision": SOURCE_REVISION,
        "source_zip_sha256": SOURCE_DIGEST,
        "wheels": [{"filename": name, "sha256": plan["assets"][name]} for name in sorted(wheels)],
    }
    require(manifest == expected_manifest, "ARTIFACT_MANIFEST_MISMATCH")
    expected_lines = [f"{plan['assets'][name]}  {name}" for name in sorted(wheels)]
    require((directory / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines() == expected_lines,
            "ARTIFACT_CHECKSUMS_MISMATCH")
    return len(expected)


def audit_wheel(path, distribution, python, license_bytes, dependencies=()):
    package = module_name(distribution)
    info = f"{package}-{VERSION}.dist-info"
    prefix_set = {package, info}
    with zipfile.ZipFile(path) as archive:
        require(not archive.comment, f"WHEEL_COMMENT_REFUSED: {path.name}")
        members = archive.infolist()
        names = [member.filename for member in members]
        require(names == sorted(set(names)), f"WHEEL_MEMBER_ORDER_OR_DUPLICATES: {path.name}")
        for member in members:
            safe = PurePosixPath(member.filename)
            require(safe.parts and safe.parts[0] in prefix_set and not member.is_dir()
                    and not {"..", "."}.intersection(safe.parts) and "\\" not in member.filename
                    and safe.as_posix() == member.filename and not safe.is_absolute()
                    and member.date_time == (1980, 1, 1, 0, 0, 0)
                    and member.create_system == 3 and member.external_attr == 0o100644 << 16
                    and member.compress_type == zipfile.ZIP_STORED and not member.extra and not member.comment,
                    f"WHEEL_MEMBER_REFUSED: {member.filename}")
        metadata = BytesParser().parsebytes(archive.read(f"{info}/METADATA"))
        require(
            (metadata["Name"], metadata["Version"], metadata["Requires-Python"], metadata["License-Expression"])
            == (distribution, VERSION, python, "MIT")
            and metadata["License-File"] == "LICENSE"
            and metadata.get_all("Requires-Dist", []) == list(dependencies)
            and archive.read(f"{info}/licenses/LICENSE") == license_bytes,
            f"WHEEL_METADATA_MISMATCH: {path.name}",
        )
        record_name = f"{info}/RECORD"
        record = list(csv.reader(io.StringIO(archive.read(record_name).decode("ascii"))))
        require(len(record) == len(names) and {row[0] for row in record} == set(names),
                f"WHEEL_RECORD_COVERAGE_MISMATCH: {path.name}")
        for name, pin, length in record:
            if name == record_name:
                require((pin, length) == ("", ""), f"WHEEL_RECORD_SELF_HASH_REFUSED: {path.name}")
                continue
            raw = archive.read(name)
            content_hash = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode("ascii")
            require(pin == "sha256=" + content_hash and length == str(len(raw)),
                    f"WHEEL_RECORD_MISMATCH: {name}")


def run(command, workspace, expected=0):
    env = {key: value for key, value in os.environ.items() if not key.startswith(("PIP_", "PYTHON"))}
    env.update({
        "PIP_CONFIG_FILE": os.devnull, "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONNOUSERSITE": "1", "PYTHONUTF8": "1",
    })
    result = subprocess.run(
        [str(arg) for arg in command], cwd=workspace, text=True, encoding="utf-8",
        capture_output=True, env=env, check=False, timeout=120,
    )
    if result.returncode != expected:
        raise ValueError(
            f"UNEXPECTED_EXIT: {Path(command[0]).name}: expected {expected}, got {result.returncode}\n"
            f"{result.stderr}"
        )
    return result.stdout


def installed_command(scripts, name):
    return scripts / (name + ".exe" if os.name == "nt" else name)


def environment(workspace, name, wheel_dir, distribution):
    path = workspace / name
    run([sys.executable, "-I", "-m", "venv", path], workspace)
    scripts = path / ("Scripts" if os.name == "nt" else "bin")
    python = installed_command(scripts, "python")
    run([python, "-I", "-m", "pip", "install", "--no-index", "--find-links",
         wheel_dir, f"{distribution}=={VERSION}"], workspace)
    run([python, "-I", "-m", "pip", "check"], workspace)
    return python, scripts


def report_matches(report, sample, component, status, issue_codes):
    require(
        report["format"] == component["result_format"]
        and report["status"] == status
        and report["input_sha256"] == digest(sample.read_bytes())
        and sorted({issue["code"] for issue in report["issues"]}) == sorted(issue_codes)
        and set(report) == set(component["result_fields"])
        and all(report[field] is False for field in NO_EFFECT_FIELDS),
        f"EXAMPLE_CONTRACT_MISMATCH: {component['id']}/{sample.name}",
    )


def verify_examples(python, scripts, workspace, component):
    command = installed_command(scripts, component["command"])
    demo = installed_command(scripts, component["command"] + "-demo")
    module = component["python_api"].split(".check(", 1)[0]
    sample = ROOT / component["example_input"]
    status = component["example_status"]
    report = json.loads(run([command, "--input", sample], workspace, EXIT_STATUS[status]))
    report_matches(report, sample, component, status, component["example_issue_codes"])
    embedded = json.loads(run([demo], workspace, EXIT_STATUS[status]))
    api = json.loads(run([python, "-I", "-c", API_RUNNER, module, sample], workspace))
    require(report == api == embedded, f"CLI_API_DEMO_DRIFT: {component['id']}")

    if component["example_review_input"] is not None:
        review = ROOT / component["example_review_input"]
        report = json.loads(run([command, "--input", review], workspace, 1))
        report_matches(report, review, component, "REVIEW_REQUIRED", component["example_review_issue_codes"])


def verify(directory):
    directory = directory.resolve()
    guide = component_guide()
    asset_count = check_assets(directory, guide)
    components = guide["components"]
    for component in components:
        name = component["command"]
        license_path = ROOT / "tools" / component["id"] / "LICENSE"
        audit_wheel(directory / wheel_name(name), name, guide["python"], license_path.read_bytes())
    collection_license = ROOT / "tools/grouped-report-contract-checker/LICENSE"
    audit_wheel(directory / wheel_name(COLLECTION), COLLECTION, guide["python"], collection_license.read_bytes(),
                [component["package"] for component in components])

    with tempfile.TemporaryDirectory(prefix="outlands-grouped-wheel-acceptance-") as temporary:
        workspace = Path(temporary)
        for component in components:
            python, scripts = environment(workspace, component["id"], directory, component["command"])
            verify_examples(python, scripts, workspace, component)
            installed = json.loads(run([python, "-I", "-m", "pip", "list", "--format=json"], workspace))
            outlands = {item["name"] for item in installed if item["name"].startswith("outlands-")}
            require(outlands == {component["command"]}, f"STANDALONE_INSTALL_DRIFT: {component['id']}")

        python, scripts = environment(workspace, "collection", directory, COLLECTION)
        command = installed_command(scripts, guide["collection"]["command"])
        require(run([command], workspace).splitlines() == [item["command"] for item in components],
                "COLLECTION_COMMANDS_MISMATCH")
        for component in components:
            verify_examples(python, scripts, workspace, component)

    return {
        "status": "PASS",
        "assets": asset_count,
        "individual_offline_installs": {
            component["id"]: {"install": "PASS", "cli": "PASS", "python_api": "PASS",
                              "observed_example_status": component["example_status"]}
            for component in components
        },
        "collection_offline_install": "PASS",
        "pinned_digests_and_record": "PASS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheels", required=True, type=Path)
    print(json.dumps(verify(parser.parse_args().wheels), sort_keys=True))
