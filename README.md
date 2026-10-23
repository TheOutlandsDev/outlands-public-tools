# OUTLANDS | Engineering Utilities

Focused Python utilities for reviewing dependency locks and checking package source without running the selected package. Both tools use Python's standard library and require the documented POSIX file operations.

| Tool | Purpose | Documentation |
| --- | --- | --- |
| Dependency Lock Tools | Convert a supported pip JSON report to sorted name/version/SHA-256 requirements and validate that limited lock format offline. | [Usage, format and limits](tools/dependency-lock-tools/README.md) |
| Package Layout Checker | Check caller-declared files, optional Python syntax and case-insensitive literal markers without importing the selected package. | [Usage, examples and limits](tools/package-layout-checker/README.md) |

## Quick start

Use Python 3.12 on Linux/POSIX. No package installation is needed. Start with disposable fictional inputs and read the tool-specific limits.

```text
python tools/package-layout-checker/layout_check.py --root tools/package-layout-checker/examples/sample-package --manifest tools/package-layout-checker/examples/layout.json
```

To work with an existing report or lock, provide your own explicit private input/output paths:

```text
python tools/dependency-lock-tools/report_to_lock.py --report INPUT_REPORT_JSON --output NEW_LOCK_FILE
python tools/dependency-lock-tools/verify_locks.py LOCK_FILE
```

## Recorded validation

| Tool | Synthetic unittest methods | Runtime |
| --- | ---: | --- |
| Dependency Lock Tools | 32 passed | Python 3.12.7, Linux |
| Package Layout Checker | 33 passed | Python 3.12.14, Linux |

All 65 recorded methods passed with no skips, failures or errors. A separate fictional layout CLI run passed for two declared files; it is not counted as additional unittest cases. Validation used bounded, isolated child processes with network system calls denied. No real report, package artifact, business data or production environment was accepted by these tests.

## Scope

Lock validation checks syntax and hash pairing. Hashes come from the supplied report; the tools do not establish artifact origin, dependency resolution, installability, platform coverage or vulnerability status. Report URLs and source constraints are not carried into the generated format.

Layout checks cover only declared files. PASS does not enumerate extra files, prove an exact export list, find arbitrary secrets or establish application correctness. Syntax parsing is not execution. Neither tool is an anonymity mechanism, a universal filesystem sandbox or a complete snapshot. Windows is unsupported by these hardened editions.

Keep real reports, generated locks, private manifests, credentials, runtime outputs and identifying support material outside this repository. Use stable, trusted files and parents.

## Provenance and licensing

The owner reports personal work created with AI assistance; the adaptations, documentation and synthetic tests were also AI-assisted. Only the selected generic mechanisms and fictional examples are included. No required license or attribution notice was removed from the selected sources. This statement is not independent proof of exclusive authorship.

**No open-source license has been assigned.** This is a publicly viewable source showcase; general reuse permission is not granted by this README. See [LICENSING.md](LICENSING.md) before redistributing or incorporating code.
