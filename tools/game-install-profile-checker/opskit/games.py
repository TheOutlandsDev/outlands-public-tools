"""Read and check TOML game-install profiles within a selected local tree."""

from __future__ import annotations

import stat
import sys
import tomllib
from pathlib import Path
from typing import Any

from .common import OpsKitError


SUPPORTED_ENGINES = {"steamcmd", "standalone", "spt"}
SUPPORTED_PLATFORMS = {"any", "windows", "linux"}
_MAX_PROFILES = 256
_MAX_PROFILE_BYTES = 64 * 1024
_MAX_FIELD_ITEMS = 256
_WINDOWS_DEVICES = {
    "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
    *(f"{kind}{number}" for kind in ("COM", "LPT") for number in "123456789¹²³"),
}


def _state(root: Path, relative: Path) -> int | None:
    """Inspect each component without following a link or reparse point."""
    path = root
    for part in relative.parts or ("",):
        path = path / part
        try:
            info = path.lstat()
        except (FileNotFoundError, NotADirectoryError):
            return None
        except OSError:
            raise OpsKitError("A selected path could not be inspected.") from None
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise OpsKitError("Links and reparse points are refused.")
    return info.st_mode


def _local_absolute(path: Path) -> tuple[Path, int | None]:
    try:
        absolute = path.absolute()
    except OSError:
        raise OpsKitError("A selected path could not be inspected.") from None
    if (
        not absolute.is_absolute() or ".." in absolute.parts
        or absolute.drive.startswith("\\\\") or absolute.anchor == "//"
    ):
        raise OpsKitError("An ordinary local path is required.")
    anchor = Path(absolute.anchor)
    return absolute, _state(anchor, absolute.relative_to(anchor))


def _home(path: Path) -> Path:
    absolute, mode = _local_absolute(path)
    if mode is None or not stat.S_ISDIR(mode):
        raise OpsKitError("The selected home must be an existing directory.")
    return absolute


def _relative_under(path: Path, root: Path) -> Path:
    if ".." in path.parts:
        raise OpsKitError("The profile directory must be inside the selected home.")
    try:
        return path.relative_to(root)
    except ValueError:
        raise OpsKitError("The profile directory must be inside the selected home.") from None


def profiles_directory(home: Path, override: Path | None = None) -> Path:
    root = _home(home)
    directory = override if override is not None else Path("config", "game-profiles")
    if not directory.is_absolute():
        if directory.anchor:
            raise OpsKitError("The profile directory must be inside the selected home.")
        directory = root / directory
    relative = _relative_under(directory, root)
    if relative.parts and Path(*_portable_parts(relative.as_posix())) != relative:
        raise OpsKitError("An ordinary local profile directory is required.")
    _state(root, relative)
    return directory


def _portable_parts(value: object) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or len(value) > 1_024 or not value.isprintable():
        raise OpsKitError("Expected a portable relative path.")
    parts = value.replace("\\", "/").split("/")
    if any(
        part in ("", ".", "..") or part[0] in ("~", "$", "%")
        or part[-1] in (" ", ".")
        or any(character in part for character in ':*?"<>|')
        or part.split(".", 1)[0].rstrip().upper() in _WINDOWS_DEVICES
        for part in parts
    ):
        raise OpsKitError("Expected a portable relative path.")
    return tuple(parts)


def _label(value: object) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 160 and bool(value.strip()) and value.isprintable()


def _load_profile(directory: Path, path: Path) -> dict[str, Any]:
    relative = Path(*_portable_parts(path.name))
    mode = _state(directory, relative)
    if mode is None or not stat.S_ISREG(mode):
        raise OpsKitError("A profile entry is not an ordinary file.")
    try:
        with path.open("rb") as handle:
            content = handle.read(_MAX_PROFILE_BYTES + 1)
        if len(content) > _MAX_PROFILE_BYTES:
            raise OpsKitError("A profile exceeds the size limit.")
        profile = tomllib.loads(content.decode("utf-8"))
    except (OSError, ValueError, RecursionError):
        raise OpsKitError("A profile could not be read as valid TOML.") from None
    profile["_file"] = relative
    profile.setdefault("name", path.stem)
    profile.setdefault("enabled", False)
    profile.setdefault("platform", "any")
    if (
        not _label(profile["name"])
        or ("game" in profile and not _label(profile["game"]))
        or type(profile["enabled"]) is not bool
    ):
        raise OpsKitError("A profile has an invalid name, game, or enabled field.")
    return profile


def load_profiles(directory: Path) -> tuple[list[dict[str, Any]], list[str]]:
    directory, mode = _local_absolute(directory)
    if mode is None:
        return [], ["The profile directory does not exist."]
    if not stat.S_ISDIR(mode):
        raise OpsKitError("The selected profile path must be a directory.")
    paths = []
    try:
        for path in directory.iterdir():
            if path.suffix.casefold() == ".toml":
                if len(paths) == _MAX_PROFILES:
                    raise OpsKitError("The profile directory exceeds the profile limit.")
                paths.append(path)
    except OSError:
        raise OpsKitError("The selected profile directory could not be read.") from None

    profiles: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for path in sorted(paths, key=lambda item: (item.name.casefold(), item.name)):
        try:
            profile = _load_profile(directory, path)
        except OpsKitError as exc:
            warnings.append(str(exc))
            continue
        name = profile["name"].casefold()
        if name in seen:
            warnings.append("A duplicate game profile name was ignored.")
            continue
        seen.add(name)
        profiles.append(profile)
    return profiles, warnings


def _supported(value: object, allowed: set[str]) -> str | None:
    normalized = value.casefold() if isinstance(value, str) else None
    return normalized if normalized in allowed else None


def list_profiles(directory: Path) -> tuple[dict[str, Any], list[str]]:
    profiles, warnings = load_profiles(directory)
    return {
        "profiles_directory": directory.name,
        "count": len(profiles),
        "profiles": [
            {
                "name": profile["name"],
                "game": profile.get("game"),
                "engine": _supported(profile.get("engine"), SUPPORTED_ENGINES),
                "platform": _supported(profile.get("platform"), SUPPORTED_PLATFORMS),
                "enabled": profile["enabled"],
                "file": profile["_file"].as_posix(),
            }
            for profile in profiles
        ],
        "read_only": True,
    }, warnings


def _result(name: str, status: str, message: str, **details: Any) -> dict[str, Any]:
    return {"name": name, "status": status, "message": message, "details": details}


def _path_check(
    checks: list[dict[str, Any]], root: Path, base: Path, name: str, value: object,
    kind: str, missing: str,
) -> Path | None:
    try:
        relative = base.joinpath(*_portable_parts(value))
        mode = _state(root, relative)
    except OpsKitError:
        checks.append(_result(name, "fail", "The declared path is invalid or unsafe."))
        return None
    exists = mode is not None and (
        stat.S_ISDIR(mode) if kind == "directory"
        else stat.S_ISREG(mode) if kind == "file"
        else stat.S_ISREG(mode) or stat.S_ISDIR(mode)
    )
    checks.append(
        _result(name, "pass" if exists else missing,
                "Path is present." if exists else "Path is missing or has the wrong type.",
                path=relative.as_posix())
    )
    return relative


def _path_array(
    checks: list[dict[str, Any]], root: Path, base: Path, name: str, item_name: str,
    value: object, kind: str, missing: str,
) -> None:
    if not isinstance(value, list) or len(value) > _MAX_FIELD_ITEMS:
        checks.append(_result(name, "fail", "Expected a bounded array of paths."))
        return
    for index, item in enumerate(value):
        _path_check(checks, root, base, f"{item_name}_{index}", item, kind, missing)


def check_profile(profile: dict[str, Any], home: Path) -> dict[str, Any]:
    root = _home(home)
    checks: list[dict[str, Any]] = []
    name = profile.get("name", "unnamed")
    game = profile.get("game")
    engine = _supported(profile.get("engine"), SUPPORTED_ENGINES)
    target = _supported(profile.get("platform", "any"), SUPPORTED_PLATFORMS)
    enabled = profile.get("enabled", False)
    if not _label(name) or (game is not None and not _label(game)) or type(enabled) is not bool:
        raise OpsKitError("A profile has an invalid name, game, or enabled field.")

    host = "windows" if sys.platform == "win32" else sys.platform
    applicable = target in {"any", host}
    active = enabled and applicable
    missing = "fail" if active else "skip"
    checks.extend((
        _result("enabled", "pass" if enabled else "skip", "Profile state checked."),
        _result("engine", "pass" if engine else "fail",
                "Engine is supported." if engine else "Expected a supported engine."),
        _result("platform", "pass" if target else "fail",
                "Target platform is supported." if target else "Expected a supported target platform."),
        _result("host_platform", "pass" if applicable else "skip", "Host applicability checked."),
    ))
    install = _path_check(checks, root, Path(), "install_dir", profile.get("install_dir"), "directory", missing)
    if install is not None:
        _path_check(checks, root, install, "executable", profile.get("executable"), "file", missing)
        _path_array(checks, root, install, "required_files", "required_file",
                    profile.get("required_files", []), "file", missing)
        _path_array(checks, root, install, "save_paths", "save_path",
                    profile.get("save_paths", []), "either", "warn" if active else "skip")

    ports = profile.get("ports", [])
    if not isinstance(ports, list) or len(ports) > _MAX_FIELD_ITEMS:
        checks.append(_result("ports", "fail", "Expected a bounded array of port numbers."))
    else:
        valid = [port for port in ports if type(port) is int and 1 <= port <= 65_535]
        valid_ports = len(valid) == len(ports) == len(set(valid))
        checks.append(_result("ports", "pass" if valid_ports else "fail",
                              "Declared ports must be unique integers from 1 through 65535.",
                              configured_ports=valid))
    running = profile.get("expect_running", False)
    if type(running) is not bool:
        checks.append(_result("listening_ports", "fail", "Runtime expectation must be a boolean."))
    elif running:
        checks.append(_result("listening_ports", "skip", "Runtime evidence is unavailable in this file check."))

    status = "pass" if active else "skip"
    if any(check["status"] == "fail" for check in checks):
        status = "fail"
    elif active and any(check["status"] == "warn" for check in checks):
        status = "warn"
    return {
        "name": name,
        "game": game,
        "engine": engine,
        "status": status,
        "enabled": enabled,
        "applicable": applicable,
        "checks": checks,
    }


def check_profiles(
    directory: Path, home: Path, *, selected_name: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    root = _home(home)
    directory = profiles_directory(root, directory)
    profiles, warnings = load_profiles(directory)
    if selected_name is not None:
        profiles = [profile for profile in profiles if profile["name"].casefold() == selected_name.casefold()]
        if not profiles:
            raise OpsKitError("The selected profile was not found.")
    results = [check_profile(profile, root) for profile in profiles]
    return {
        "profiles_directory": directory.relative_to(root).as_posix(),
        "count": len(results),
        "status": "fail" if warnings or not results or any(item["status"] == "fail" for item in results) else "pass",
        "profiles": results,
        "read_only": True,
    }, warnings
