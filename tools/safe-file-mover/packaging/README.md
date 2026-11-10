# Reproduce the standalone wheel qualification

Use a separately supplied Python 3.12.7–3.15 in a fresh build venv. Install
`build-requirements.txt` in that environment. These are build-only dependencies;
the wheel declares no runtime dependencies. Run from the tool directory:

```text
python -m pip install -r packaging/build-requirements.txt
python -B packaging/build_wheel.py --out NEW_ABSOLUTE_OUTPUT_DIRECTORY
python -B packaging/qualify_wheel.py --wheel ABSOLUTE_WHEEL_PATH --work-root EXISTING_PRIVATE_LOCAL_SCRATCH --report NEW_ABSOLUTE_REPORT_PATH
```

The builder stages only seven allowlisted Python modules, `pyproject.toml`,
`LICENSE` and `USAGE.md`, normalizes text to LF and fixes archive timestamps.
It rejects unexpected wheel members. No source-tree build, cache or local state
is collected. The wheel contains seven modules and six distribution metadata/
license members. `USAGE.md` is embedded as distribution metadata and also
published separately. Repeat the build with a new output directory and compare
SHA-256 bytes. CI additionally compares builds across every OS/Python lane.

The qualifier creates a unique private workspace under the supplied scratch
directory and retains it for review. It creates a new pip-enabled venv, installs
the given wheel with `--no-index --no-deps`, copies only tests/the runner, and
runs from that fixture directory with isolated Python imports. Import location
must be inside the venv and match the installed distribution; no package source
is available beside the copied tests. Five tests invoke the installed console
entry point for metadata/help, mutation-free preview, move/history/recover/
restore, verified purge and changed-destination purge refusal. All 116 original
engine/CLI methods run against the installed package as well.

Set `OUTLANDS_MOVER_REQUIRE_NATIVE_FEATURES=1` for acceptance on Windows. Missing
native hardlink/symlink/junction support fails those fixtures; skipped named-
stream execution also fails qualification. An unprivileged local run may report
skips, which must not be claimed as full Windows acceptance. CI supplies native
features and a non-junction temporary parent without changing user policy.

Reports contain only platform/Python/version, wheel digest, import proof and test
counts/skip reasons. Raw console output and generated journals may contain local
paths; retain them privately. Reports and passing fixtures do not certify GUI,
live SMB, hostile concurrency, power loss or production backup behavior.
