"""Portable Kiro project setup. Standard library only; never calls a model."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

KIT = Path(__file__).resolve().parents[1]
VERSION = "1.1.0"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def relative(value: str) -> Path:
    p = PurePosixPath(value)
    if (not value or "\\" in value or ":" in value or p.is_absolute()
            or any(x in ("", ".", "..") for x in value.split("/"))):
        raise ValueError(f"Unsafe relative path: {value!r}")
    return Path(*p.parts)


def no_links(path: Path) -> Path:
    """Reject symbolic links and Windows junctions in every existing component."""
    path = Path(os.path.abspath(path))
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Link/reparse point is not an installation target: {part}")
    return path


def within(root: Path, name: str) -> Path:
    root = no_links(root)
    result = no_links(root / relative(name))
    if not result.is_relative_to(root):
        raise ValueError("Path escaped the selected workspace")
    return result


def atomic_write(path: Path, content: bytes):
    no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(content)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def payloads(kit: Path = KIT) -> dict[str, bytes]:
    manifest = read_json(kit / "kit-manifest.json")
    if manifest["version"] != VERSION:
        raise ValueError("Kit and installer version differ")
    result = {}
    seen = set()
    for entry in manifest["files"]:
        name = entry["target"]
        relative(name)
        if name.casefold() in seen:
            raise ValueError("Duplicate installation path")
        seen.add(name.casefold())
        shared_source = entry.get("source")
        shared = {".kiro/devkit/check_bedrock.py": "scripts/check_bedrock.py",
                  ".kiro/devkit/pairing-plan.example.json": "pairing-plan.example.json"}
        if shared_source is not None:
            if shared.get(name) != shared_source:
                raise ValueError("Unapproved shared installation source")
            source = within(kit, shared_source)
        else:
            source = within(kit / "template", name)
        data = source.read_bytes()
        if digest(data) != entry["sha256"]:
            raise ValueError(f"Template digest mismatch: {name}")
        result[name] = data
    return result


def render(kit=KIT, models_file=None, primary=None, review=None, fast=None):
    result = payloads(kit)
    pins = {"developer": primary, "reviewer": review or primary,
            "investigator": fast or primary}
    if any(pins.values()):
        if not primary or models_file is None:
            raise ValueError("Model pinning needs --primary and --available-models")
        available = read_json(Path(models_file))["available_model_ids"]
        if (not isinstance(available, list) or not available
                or any(not isinstance(x, str) or not x or len(x) > 128
                       or any(c.isspace() for c in x) or "://" in x for x in available)):
            raise ValueError("Expected exact model IDs copied from the managed Kiro picker")
        for model in pins.values():
            if model not in available:
                raise ValueError(f"Model is absent from the supplied Kiro inventory: {model}")
    for role, model in pins.items():
        name = f".kiro/agents/outlands-{role}.json"
        config = json.loads(result[name])
        if model:
            config["model"] = model
        result[name] = encoded(config)
    routes = json.loads(result[".kiro/devkit/routes.json"])
    routes["model_pins"] = pins
    routes["selection"] = "explicit_inventory" if primary else "managed_kiro_default"
    result[".kiro/devkit/routes.json"] = encoded(routes)
    return result


def install(target: Path, *, apply=False, replace=False, kit=KIT, **models):
    target = no_links(target)
    if not target.is_dir():
        raise ValueError("Select an existing project directory")
    data = render(kit, **models)
    changes = []
    conflicts = []
    for name, content in data.items():
        path = within(target, name)
        if path.exists() and not path.is_file():
            raise ValueError(f"Installation path is not a file: {name}")
        previous = path.read_bytes() if path.exists() else None
        if previous == content:
            continue
        if previous is not None:
            conflicts.append(name)
        changes.append((name, content, previous))
    if not apply:
        return {"action": "preview", "version": VERSION,
                "changes": [x[0] for x in changes], "conflicts": conflicts}
    if conflicts and not replace:
        raise ValueError("Existing files differ; review preview and use --replace: " + ", ".join(conflicts))
    if not changes:
        return {"action": "unchanged", "version": VERSION, "files": len(data)}
    receipt_rel = f".kiro-kit/state/{uuid.uuid4().hex}/receipt.json"
    receipt_path = within(target, receipt_rel)
    # Retained with rollback receipts so original project bytes remain git-ignored.
    state_ignore = within(target, ".kiro-kit/state/.gitignore")
    if not state_ignore.exists():
        atomic_write(state_ignore, b"*\n")
    receipt = {"version": VERSION, "status": "installing", "files": []}
    # Capture original bytes and durable receipt before changing project files.
    for index, (name, content, previous) in enumerate(changes):
        backup = f"backups/{index}.bin" if previous is not None else None
        if backup:
            atomic_write(within(receipt_path.parent, backup), previous)
        receipt["files"].append({"target": name, "installed_sha256": digest(content),
                                 "backup": backup,
                                 "original_sha256": digest(previous) if previous is not None else None})
    atomic_write(receipt_path, encoded(receipt))
    applied = []
    try:
        for name, content, previous in changes:
            path = within(target, name)
            current = path.read_bytes() if path.exists() else None
            if current != previous:
                raise ValueError(f"File changed after preview: {name}")
            atomic_write(path, content)
            applied.append((name, previous))
        receipt["status"] = "installed"
        atomic_write(receipt_path, encoded(receipt))
    except Exception:
        for name, previous in reversed(applied):
            path = within(target, name)
            if previous is None:
                path.unlink()
            else:
                atomic_write(path, previous)
        receipt["status"] = "failed_reverted"
        atomic_write(receipt_path, encoded(receipt))
        raise
    return {"action": "installed", "version": VERSION, "files": len(data),
            "changed": len(changes), "receipt": receipt_rel,
            "managed_model_session": "NOT_RUN"}


def restore(target: Path, receipt_name: str, *, apply=False):
    target = no_links(target)
    rel = relative(receipt_name)
    if rel.parts[:2] != (".kiro-kit", "state") or rel.name != "receipt.json" or len(rel.parts) != 4:
        raise ValueError("Receipt must be inside this workspace's .kiro-kit/state directory")
    path = within(target, receipt_name)
    receipt = read_json(path)
    if receipt["status"] != "installed":
        raise ValueError("Receipt is not an active installation")
    operations = []
    seen = set()
    for entry in receipt["files"]:
        name = entry["target"]
        if name.casefold() in seen or not (name == "AGENTS.md" or name.startswith((".kiro/", ".kiro-kit/"))):
            raise ValueError("Receipt contains an invalid target")
        seen.add(name.casefold())
        dest = within(target, name)
        if not dest.is_file() or digest(dest.read_bytes()) != entry["installed_sha256"]:
            raise ValueError(f"Installed file changed; preserve it before restoring: {name}")
        backup = entry["backup"]
        original = None
        if backup:
            if not backup.startswith("backups/"):
                raise ValueError("Invalid backup path")
            original = within(path.parent, backup).read_bytes()
            if digest(original) != entry["original_sha256"]:
                raise ValueError(f"Backup digest mismatch: {name}")
        operations.append((dest, original))
    if not apply:
        return {"action": "restore_preview", "files": len(operations)}
    for dest, original in operations:
        if original is None:
            if dest != target / ".kiro-kit/.gitignore":
                dest.unlink()  # Keep the privacy marker with retained local state.
        else:
            atomic_write(dest, original)
    receipt["status"] = "restored"
    atomic_write(path, encoded(receipt))
    return {"action": "restored", "files": len(operations)}


def verify(target: Path, kit=KIT):
    expected = payloads(kit)
    missing = [x for x in expected if not within(target, x).is_file()]
    configs = {}
    errors = []
    for role in ("developer", "reviewer", "investigator"):
        name = f".kiro/agents/outlands-{role}.json"
        if name in missing:
            continue
        try:
            config = read_json(within(target, name))
            if config["name"] != f"outlands-{role}" or not config.get("resources"):
                raise ValueError("Agent name/resources are missing")
            configs[role] = config.get("model", "managed_kiro_default")
        except (ValueError, KeyError) as exc:
            errors.append(f"{role}: {exc}")
    routes_path = within(target, ".kiro/devkit/routes.json")
    if routes_path.is_file():
        routes = read_json(routes_path)
        for role, model in routes["model_pins"].items():
            if configs.get(role) != (model or "managed_kiro_default"):
                errors.append(f"Route and agent model differ: {role}")
    # Detect drift against every active receipt, including non-agent files.
    receipt_root = within(target, ".kiro-kit/state")
    if receipt_root.is_dir():
        active = []
        for p in receipt_root.glob("*/receipt.json"):
            no_links(p)
            rec = read_json(p)
            if rec["status"] == "installed":
                active.append((p.stat().st_mtime_ns, rec))
        latest = {}
        for _, rec in sorted(active, key=lambda item: item[0]):
            latest.update({e["target"]: e["installed_sha256"] for e in rec["files"]})
        for name, sha in latest.items():
            p = within(target, name)
            if p.is_file() and digest(p.read_bytes()) != sha:
                errors.append(f"Installed file drift: {name}")
    return {"version": VERSION, "configuration_files_present": not missing,
            "missing": missing, "errors": errors, "configured_models": configs,
            "managed_model_session": "NOT_RUN", "agent_behavior": "NOT_RUN",
            "ready_for_managed_work": False}


def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            timeout=90, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def fixture_checks(kit=KIT, python=sys.executable, node="node", javac="javac", java="java"):
    """Compile/run copied fixtures; source kit is unchanged. No network or model calls."""
    with tempfile.TemporaryDirectory(prefix="kiro-kit-check-") as tmp:
        root = Path(tmp)
        shutil.copytree(kit / "evals" / "fixtures", root / "fixtures")
        fixtures = root / "fixtures"
        results = {"python": run([python, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], fixtures / "python315"),
                   "node": run([node, "--test"], fixtures / "node")}
        jp = fixtures / "java"
        compile_result = run([javac, "-d", "classes", "src/Stock.java", "tests/StockTest.java"], jp)
        results["java_compile"] = compile_result
        results["java"] = run([java, "-cp", "classes", "StockTest"], jp) if compile_result["exit_code"] == 0 else {"exit_code": 1, "stderr": "Compilation failed"}
        source = fixtures / "python315" / "orders.py"
        source.write_text(source.read_text().replace(" >= quantity", " > quantity"), encoding="utf-8")
        negative = run([python, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], source.parent)
        results["python_bug_detected"] = {"exit_code": 0 if negative["exit_code"] != 0 and "FAIL:" in negative["stderr"] else 1,
                                           "observed_test_exit": negative["exit_code"]}
        nsource = fixtures / "node" / "pricing.mjs"
        nsource.write_text(nsource.read_text().replace("Math.floor", "Math.ceil"), encoding="utf-8")
        regression = run([node, "--test"], nsource.parent)
        results["node_regression_detected"] = {"exit_code": 0 if regression["exit_code"] != 0 and "AssertionError" in regression["stdout"] + regression["stderr"] else 1,
                                                "observed_test_exit": regression["exit_code"]}
        return {"fixture_checks": results, "passed": all(x["exit_code"] == 0 for x in results.values()),
                "model_calls": 0, "agent_behavior": "NOT_RUN"}


def prepare_eval(target: Path, kit=KIT):
    target = no_links(target)
    if target.exists():
        raise ValueError("Evaluation needs a new destination; existing directories are preserved")
    shutil.copytree(kit / "evals" / "fixtures" / "python315", target)
    source = target / "orders.py"
    source.write_text(source.read_text().replace(" >= quantity", " > quantity"), encoding="utf-8")
    tests = {p.relative_to(target).as_posix(): digest(p.read_bytes()) for p in target.rglob("*") if p.is_file() and p.name != "orders.py"}
    atomic_write(target / ".kiro-kit" / "eval-baseline.json", encoded({"files": tests, "allowed_changes": ["orders.py"]}))
    install(target, apply=True, kit=kit)
    return {"evaluation": "python_bugfix", "expected_initial_tests": "FAIL",
            "allowed_change": "orders.py", "managed_model_session": "NOT_RUN"}


def score_eval(target: Path, python=sys.executable):
    target = no_links(target)
    baseline = read_json(within(target, ".kiro-kit/eval-baseline.json"))
    changed = []
    for name, sha in baseline["files"].items():
        p = within(target, name)
        if not p.is_file() or digest(p.read_bytes()) != sha:
            changed.append(name)
    tests = run([python, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], target)
    # External oracle is independent of the evaluation workspace's test discovery.
    oracle = run([python, "-B", "-c", "from orders import can_fulfill; "
                  "assert can_fulfill(5,2,3) is True; assert can_fulfill(5,2,4) is False; "
                  "assert can_fulfill(5,5,1) is False; assert can_fulfill(5,2,0) is True"], target)
    return {"protected_files_changed": changed, "tests": tests, "oracle": oracle,
            "code_checks_passed": not changed and tests["exit_code"] == oracle["exit_code"] == 0,
            "model_provider_and_agent_behavior": "REQUIRES_SESSION_EVIDENCE"}


def main():
    if sys.version_info[:2] != (3, 15):
        print(json.dumps({"error": "Use the kit's Python 3.15 environment"}), file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("install")
    p.add_argument("--target", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--replace", action="store_true")
    p.add_argument("--available-models", type=Path)
    p.add_argument("--primary")
    p.add_argument("--review")
    p.add_argument("--fast")
    p = sub.add_parser("restore")
    p.add_argument("--target", type=Path, required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("verify")
    p.add_argument("--target", type=Path, required=True)
    p = sub.add_parser("check-fixtures")
    for name, default in (("python", sys.executable), ("node", "node"), ("javac", "javac"), ("java", "java")):
        p.add_argument("--" + name, default=default)
    for name in ("prepare-eval", "score-eval"):
        p = sub.add_parser(name)
        p.add_argument("--target", type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "install":
        args["models_file"] = args.pop("available_models")
    if command == "restore":
        args["receipt_name"] = args.pop("receipt")
    try:
        result = {"install": install, "restore": restore, "verify": verify,
                  "check-fixtures": fixture_checks, "prepare-eval": prepare_eval,
                  "score-eval": score_eval}[command](**args)
        print(json.dumps(result, indent=2))
        if (command == "verify" and (result["missing"] or result["errors"])) or (command == "check-fixtures" and not result["passed"]) or (command == "score-eval" and not result["code_checks_passed"]):
            return 1
        return 0
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
