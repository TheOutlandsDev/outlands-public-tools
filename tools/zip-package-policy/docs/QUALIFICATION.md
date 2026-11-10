# Standalone source qualification

The unchanged baseline ran all 60 generated PowerShell harness cases on local
Windows with PowerShell 7.6.9. Version 0.1.0 adds focused source packaging and
fresh extracted-download qualification. The inspection script remains unchanged.
The existing test harness gains only child-process timeouts and hidden windows;
timeouts fail qualification rather than changing CLI behavior or weakening bounds.

## Selected runtimes

The 2026-11-10 official [PowerShell 7.6.10 LTS release](https://github.com/PowerShell/PowerShell/releases/tag/v7.6.10)
and [7.7.0 stable release](https://github.com/PowerShell/PowerShell/releases/tag/v7.7.0)
provide the exact Windows x64 / Linux x64 portable prerequisites recorded in
[RUNTIMES.json](RUNTIMES.json). Each asset's SHA-256 and length are verified before
it is extracted or executed. The release records take precedence over cached
documentation listing older patches. Python, PowerShell, .NET and their notices
are obtained separately and are not bundled in the source ZIP.

## Repeatable maintainer commands

Run from this source folder with Python 3.12-3.15. Every target is a new private
absolute directory outside the module. The runtime helper explicitly uses the
network; the inspector and fixture suites do not make network requests.

```text
python -B source_check.py
python -B packaging/build.py --out NEW_PACKAGE_DIRECTORY
python -B packaging/runtime.py --version 7.6.10 --out NEW_RUNTIME_DIRECTORY
python -B packaging/qualify.py --packages PACKAGE_DIRECTORY --runtime RUNTIME_DIRECTORY --workspace NEW_PRIVATE_DIRECTORY --report NEW_JSON_FILE
```

Commit reviewed source before building. The source gate has a fixed allowlist,
syntax/link/privacy checks and an exact SHA-256 manifest. The deterministic ZIP
uses committed Git blobs and fixed metadata, with no runtime or private payload.
Eight Windows/Ubuntu Python 3.12, 3.13, 3.14 and 3.15.2 helper lanes independently
run the source gate/build and compare exact ZIP bytes, not only filenames.

Four additional Windows/Ubuntu x64 lanes use the two selected PowerShell
releases. Each extracts a verified source ZIP into a new private workspace,
uses the hash-verified portable runtime, runs all 60 existing generated cases,
and creates a fresh Python venv without pip or installed distributions for nine
independent CLI methods. Those methods copy only the one runtime script and
invoke it as a separate PowerShell process. There are no mocked CLI results.

The nine methods verify the authored demo/report/hash readback; completed hash/
literal mismatch findings; preservation of existing reports and both input
aliases; traversal/case/NFC/special-entry refusal; no extraction/execution of an
authored script payload; actual filesystem symlink input/output-parent refusal;
native Windows junction-ancestor refusal; and help/malformed-input behavior.
Native symlinks are mandatory in hosted CI. The junction case is explicitly
Windows-only. A local non-admin account without symlink permission may record
two explicit skips; no policy or privilege change is made. Skips are not passes.

The release's VALIDATION.json records exact runtime/.NET/Python versions,
prerequisite digests, source revision, ZIP hash and every skip. Success requires
all four runtime and eight helper lanes. Failed logs and generated fixture
archives/policies/reports remain in private workspaces; sanitized receipts
contain no machine paths or actual user packages.

These tests establish only the recorded generated-fixture behavior. They do
not establish arbitrary archive safety, authenticity, all ZIP/CRC variants,
real application installation, hostile-race resistance, special-file safety,
OS sandboxing, native filesystem timing or hard RAM limits. Other architectures,
Windows PowerShell 5.1 and older runtime patches are not qualified here.
The separate 216-tool cumulative Python ledger is unchanged by this PowerShell
release. See the retained [original validation scope](VALIDATION.md).
