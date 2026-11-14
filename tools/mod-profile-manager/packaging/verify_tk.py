"""Attest the pinned interpreter's actual withdrawn Tk widgets and Tcl/Tk resources. MIT."""
if not __debug__:
    raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ENVIRONMENT = ("TCL_LIBRARY", "TK_LIBRARY", "TCLLIBPATH")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def script_path(name):
    parts = name.split("/")
    if name.startswith(("python/tcl/", "python/Lib/tkinter/")):
        return True
    if len(parts) > 3 and parts[:2] == ["python", "lib"] and parts[2].startswith(("tcl", "tk", "itcl", "Tcl", "Tk")):
        return True
    return len(parts) > 4 and parts[:2] == ["python", "lib"] and parts[2].startswith("python3.") and parts[3] == "tkinter"


def scripts(dist):
    rows = []
    for directory, folders, files in os.walk(dist / "python", followlinks=False):
        base = Path(directory)
        for name in folders:
            path = base / name
            assert not path.is_symlink(), "LINKED_PYTHON_RESOURCE_DIRECTORY"
        for name in files:
            path = base / name
            relative = path.relative_to(dist).as_posix()
            if not script_path(relative):
                continue
            assert not path.is_symlink() and path.is_file(), "LINKED_TK_RESOURCE"
            raw = path.read_bytes()
            assert len(raw) < 128 * 1024 * 1024, "TK_RESOURCE_BYTE_LIMIT"
            rows.append(dict(path=relative, bytes=len(raw), sha256=sha(raw)))
    rows.sort(key=lambda row: row["path"])
    assert rows and len(rows) < 40000 and len(rows) == len({row["path"] for row in rows}), "TK_RESOURCE_SELECTION_DIFFERS"
    return dict(policy="tk-script-files-v1", digest_encoding="json-sorted-path-bytes-sha256-v1", files=len(rows),
                bytes=sum(row["bytes"] for row in rows), sha256=sha(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("ascii")))


def loaded_windows(path):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
    kernel.GetModuleFileNameW.restype = ctypes.c_uint
    handle = kernel.GetModuleHandleW(path.name)
    assert handle, "PINNED_TK_BINARY_NOT_LOADED"
    output = ctypes.create_unicode_buffer(32768)
    length = kernel.GetModuleFileNameW(handle, output, len(output))
    assert 0 < length < len(output), "LOADED_TK_BINARY_PATH_UNAVAILABLE"
    return Path(output.value).resolve(strict=True)


def loaded_linux():
    paths = set()
    for line in Path("/proc/self/maps").read_text(encoding="utf-8").splitlines():
        fields = line.split(None, 5)
        if len(fields) != 6 or not fields[5].startswith("/"):
            continue
        raw = re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[5])
        if raw.endswith(" (deleted)") or not Path(raw).is_file():
            continue
        paths.add(Path(raw).resolve(strict=True))
    return paths


def library_binding(root, name, dist, components):
    library = str(root.tk.call("info", "library") if name == "tcl" else root.tk.getvar("tk_library"))
    expected = next(row for row in components if row["role"] == name)
    if library.startswith("//zipfs:/"):
        mounts = root.tk.call("zipfs", "mount")
        mounts = list(mounts if isinstance(mounts, tuple) else root.tk.splitlist(mounts))
        assert len(mounts) % 2 == 0, "TK_ZIPFS_MOUNT_SHAPE"
        matches = [(str(mounts[index]).rstrip("/"), str(mounts[index + 1])) for index in range(0, len(mounts), 2)
                   if library.startswith(str(mounts[index]).rstrip("/") + "/")]
        assert len(matches) == 1, "TK_ZIPFS_LIBRARY_NOT_BOUND"
        mount, backing = matches[0]
        assert Path(backing).resolve(strict=True) == (dist / expected["path"]).resolve(strict=True), "TK_ZIPFS_BACKING_BINARY_DIFFERS"
        suffix = library[len(mount) + 1:]
        assert suffix and ".." not in suffix.split("/") and re.fullmatch(r"[A-Za-z0-9_./-]+", suffix), "TK_ZIPFS_LIBRARY_SIGNATURE"
        entry = "init.tcl" if name == "tcl" else "tk.tcl"
        assert int(root.tk.call("file", "exists", library + "/" + entry)) == 1, "TK_ZIPFS_ENTRY_MISSING"
        return dict(kind="zipfs", library="zipfs:" + name + "/" + suffix, backing_component=expected["path"],
                    backing_sha256=expected["sha256"], entry=entry)
    path = Path(library).resolve(strict=True)
    relative = path.relative_to(dist).as_posix()
    assert script_path(relative + "/fixture") and path.is_dir() and not Path(library).is_symlink(), "TK_DIRECTORY_LIBRARY_NOT_BOUND"
    entry = "init.tcl" if name == "tcl" else "tk.tcl"
    assert (path / entry).is_file(), "TK_DIRECTORY_ENTRY_MISSING"
    return dict(kind="directory", library=relative, entry=entry, pinned_script_tree=True)


def display_provider(windowing_system):
    required = os.environ.get("OUTLANDS_PROFILE_XVFB_REQUIRED") == "1"
    if sys.platform == "win32":
        assert windowing_system == "win32" and not required, "NATIVE_WINDOWS_DISPLAY_REQUIRED"
        return dict(kind="native_windows", required=False, display_value_recorded=False, hostile_process_attestation_claimed=False)
    assert windowing_system == "x11" and os.environ.get("DISPLAY"), "ACTUAL_X11_DISPLAY_REQUIRED"
    if not required:
        return dict(kind="existing_x11_display", required=False, display_value_recorded=False, hostile_process_attestation_claimed=False)
    recipe = dict(schema=1, command="xvfb-run -a", executables=["Xvfb", "xauth", "xvfb-run"], packages=["xvfb", "xauth"],
                  package_query="dpkg-query --show --showformat=${Version} PACKAGE", selection="fixed_ubuntu_usr_bin")
    binaries = []
    for name in recipe["executables"]:
        path = Path("/usr/bin") / name
        assert path.is_file(), "REQUIRED_XVFB_PROVIDER_MISSING"
        raw = path.read_bytes()
        binaries.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
    versions = []
    for package in recipe["packages"]:
        done = subprocess.run(["/usr/bin/dpkg-query", "--show", "--showformat=${Version}", package],
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=10, check=False)
        version = done.stdout.decode("ascii").strip()
        assert done.returncode == 0 and done.stderr == b"" and re.fullmatch(r"[A-Za-z0-9.+:~_-]{1,160}", version), "XVFB_PACKAGE_IDENTITY_UNAVAILABLE"
        versions.append(dict(name=package, version=version))
    for row in binaries:
        raw = (Path("/usr/bin") / row["name"]).read_bytes()
        assert len(raw) == row["bytes"] and sha(raw) == row["sha256"], "XVFB_PROVIDER_CHANGED"
    return dict(kind="xvfb-run", required=True, command="xvfb-run -a", binaries=binaries, packages=versions,
                recipe_sha256=sha(json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode("ascii")),
                fixed_system_paths_verified=True, ownership_basis="explicit_ci_xvfb_run_invocation",
                display_value_recorded=False, hostile_process_attestation_claimed=False)


def attest(python_pin):
    assert sys.platform in ("win32", "linux"), "SUPPORTED_TK_PLATFORM_REQUIRED"
    assert all(name not in os.environ for name in FORBIDDEN_ENVIRONMENT), "INHERITED_TCL_TK_OVERRIDE_REFUSED"
    version = ".".join(map(str, sys.version_info[:3]))
    minor = ".".join(map(str, sys.version_info[:2]))
    executable = Path(sys._base_executable).resolve(strict=True)
    assert python_pin["python"] == version and python_pin["executable_sha256"] == sha(executable.read_bytes()), "TK_PYTHON_PIN_DIFFERS"
    assert python_pin["actual_interpreter_verified"] is True, "TK_PYTHON_ATTESTATION_REQUIRED"
    base = Path(sys.base_prefix).resolve(strict=True)
    dist = base.parent
    assert base.name == "python" and executable.is_relative_to(base), "PREPARED_PYTHON_PREFIX_REQUIRED"
    lock_raw = (ROOT / "GUI-LOCK.json").read_bytes()
    python_raw = (ROOT / "PYTHON-LOCK.json").read_bytes()
    lock = json.loads(lock_raw)
    python_lock = json.loads(python_raw)
    assert lock["schema"] == 1 and lock["python_lock_sha256"] == sha(python_raw), "TK_GUI_LOCK_DIFFERS"
    assert lock["source_build_release"] == python_lock["python_build_release"], "TK_BUILD_RELEASE_DIFFERS"
    expected = lock["runtime_packages"][sys.platform][minor]
    assert expected["python_version"] == version and expected["archive_sha256"] == python_lock["python_archives"][sys.platform][minor]["sha256"], "TK_RUNTIME_PACKAGE_DIFFERS"
    components = expected["components"]
    assert len(components) == 3 and {row["role"] for row in components} == {"tkinter", "tcl", "tk"}, "TK_COMPONENT_SELECTION_DIFFERS"
    for row in components:
        path = dist / row["path"]
        assert row["path"].startswith("python/") and path.resolve(strict=True).is_relative_to(base) and not path.is_symlink(), "TK_COMPONENT_PATH_DIFFERS"
        raw = path.read_bytes()
        assert len(raw) == row["bytes"] and sha(raw) == row["sha256"], "TK_COMPONENT_BYTES_DIFFER"
    script_tree = scripts(dist)
    assert script_tree == expected["script_tree"], "TK_SCRIPT_TREE_DIFFERS"
    tkinter_component = next(row for row in components if row["role"] == "tkinter")
    spec = importlib.util.find_spec("_tkinter")
    assert spec and Path(spec.origin).resolve(strict=True) == (dist / tkinter_component["path"]).resolve(strict=True), "TKINTER_MODULE_ORIGIN_DIFFERS"
    import _tkinter
    import tkinter as tk
    from tkinter import ttk
    assert Path(_tkinter.__file__).resolve(strict=True) == Path(spec.origin).resolve(strict=True), "LOADED_TKINTER_MODULE_DIFFERS"
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        frame = ttk.Frame(root)
        frame.pack()
        invoked = []
        button = ttk.Button(frame, command=lambda: invoked.append(True))
        button.invoke()
        tree = ttk.Treeview(frame)
        item = tree.insert("", "end", text="Fictional Tk attestation")
        assert str(tree.item(item, "text")) == "Fictional Tk attestation" and invoked == [True], "NATIVE_TK_WIDGET_PROBE_FAILED"
        root.update_idletasks()
        assert root.state() == "withdrawn", "WITHDRAWN_TK_REQUIRED"
        loaded = loaded_linux() if sys.platform == "linux" else None
        for row in components:
            path = (dist / row["path"]).resolve(strict=True)
            assert (loaded_windows(path) == path if sys.platform == "win32" else path in loaded), "ACTUAL_LOADED_TK_COMPONENT_DIFFERS"
        libraries = {name: library_binding(root, name, dist, components) for name in ("tcl", "tk")}
        windowing_system = str(root.tk.call("tk", "windowingsystem"))
        provider = display_provider(windowing_system)
        value = dict(schema=1, status="PASS", platform=sys.platform, python=version, executable_sha256=python_pin["executable_sha256"],
                     helper_sha256=sha(Path(__file__).read_bytes()), gui_lock_sha256=sha(lock_raw), python_lock_sha256=sha(python_raw),
                     build_release=lock["source_build_release"], archive_sha256=expected["archive_sha256"],
                     tcl_compile_version=_tkinter.TCL_VERSION, tk_compile_version=_tkinter.TK_VERSION,
                     tcl_patchlevel=str(root.tk.call("info", "patchlevel")), tk_patchlevel=str(root.tk.call("package", "require", "Tk")),
                     windowing_system=windowing_system, display_provider=provider, components=components, script_tree=script_tree,
                     libraries=libraries, actual_loaded_components_verified=True, prepared_python_prefix_verified=True,
                     native_withdrawn_widgets_checked=True, inherited_tcl_tk_overrides_absent=True,
                     display_value_recorded=False, global_environment_changed=False, binaries_bundled_in_source=False)
    finally:
        if root is not None:
            root.destroy()
    for row in components:
        raw = (dist / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and sha(raw) == row["sha256"], "TK_COMPONENT_CHANGED_DURING_ATTESTATION"
    assert scripts(dist) == script_tree and sha(executable.read_bytes()) == python_pin["executable_sha256"], "TK_RESOURCES_CHANGED_DURING_ATTESTATION"
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report = args.report
    assert report.is_absolute() and report.parent.is_dir() and not os.path.lexists(report), "NEW_TK_RECEIPT_REQUIRED"
    assert report.parent.resolve() == report.parent and not report.resolve().is_relative_to(ROOT.resolve()), "OWNED_EXTERNAL_TK_RECEIPT_REQUIRED"
    pin = dict(python=os.environ["OUTLANDS_TEST_PYTHON_VERSION"], executable_sha256=os.environ["OUTLANDS_TEST_PYTHON_SHA256"], actual_interpreter_verified=True)
    value = attest(pin)
    with report.open("x", encoding="utf-8", newline="\n") as out:
        out.write(json.dumps(value, indent=2) + "\n")
    print(json.dumps(dict(status=value["status"], python=value["python"], tcl_patchlevel=value["tcl_patchlevel"], tk_patchlevel=value["tk_patchlevel"], native_withdrawn_widgets_checked=True)))


if __name__ == "__main__":
    main()
