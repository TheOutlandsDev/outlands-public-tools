# Dependency Lock Tools 0.1.0

Offline conversion of an explicitly supplied pip JSON report into a sorted,
hash-pinned lock, and strict validation of that lock format. Windows and Ubuntu,
regular CPython 3.12–3.15; standard library only. Supply Python separately.
No administrator session, activation script, package installation or cloud
account is needed to run the two scripts. Managed execution controls still apply.

## Download and verify

Download `dependency-lock-tools-0.1.0.zip`, `SHA256SUMS.txt`, `USAGE.md`,
`VALIDATION.json` and `build-manifest.json` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/dependency-lock-tools-v0.1.0).
The checksum file covers every other attached asset. Compare the exact ZIP
filename/digest before extracting into a fresh local folder.

PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 .\dependency-lock-tools-0.1.0.zip
Get-Content .\SHA256SUMS.txt
```

Ubuntu, from a directory containing the downloaded assets:

```sh
sha256sum --check SHA256SUMS.txt
```

Checksums establish matching bytes, not independent publisher identity.
Keep all four runtime files together: `lock_common.py`, `lock_windows.py`,
`report_to_lock.py`, `verify_locks.py`. The ZIP also contains documentation,
tests, build/qualification methods, source manifest and MIT notice. No runtime,
dependency binary, actual report, lock, private configuration or credential.

## First use with fictional data

From the extracted tool directory, check `python --version` (or `python3` on
Ubuntu), then `python -B report_to_lock.py --help` and
`python -B verify_locks.py --help`. Use a trusted private scratch directory
outside the extracted app. Its output parent must already exist.

Create a fictional `report.json` there with these contents:

```json
{"version":"1","install":[{"metadata":{"name":"Demo_Package","version":"1.2.3"},"download_info":{"archive_info":{"hashes":{"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}}}]}
```

The all-`a` digest is deliberately fake. This exercise produces a syntax example;
do not use its lock to install packages. Run these commands with absolute private
paths substituted for the uppercase placeholders:

```text
python -B report_to_lock.py --report ABSOLUTE_PRIVATE_REPORT_JSON --output ABSOLUTE_NEW_PRIVATE_LOCK_FILE
python -B verify_locks.py ABSOLUTE_PRIVATE_LOCK_FILE
```

Use `python3` instead on Ubuntu if that selects the intended interpreter.
Conversion returns counts-only JSON with `result: LOCK_WRITTEN` and one package.
Validation returns `result: PASS`, one lock and one package record. Inspect the
lock: `Demo_Package` becomes `demo-package`, the version stays `1.2.3`, and the
report-supplied hash is retained. Other report metadata and URLs are omitted.

Repeat conversion with the same output: it must reject with status 2 and
`OUTPUT_EXISTS`, preserving both existing lock and report. Choose a different
new filename to convert again. Malformed report/hash/version data, duplicate
conflicts, unsupported active directives, unsafe links and bounds violations
are refused. Help uses no input; invalid arguments return a fixed error without
echoing supplied values. Handled errors are fixed-code JSON with status 2.

## Real report handling and limits

Use only reports and paths you are authorized to inspect. The converter does
not invoke pip, resolve dependencies, download packages or install anything.
It trusts the report's artifact hash declarations. Validation checks this narrow
lock syntax and adjacent name/version/hash pairing, not actual artifact bytes,
provenance, compatibility, advisory status or complete environment coverage.
Review actual artifact identity, trusted source and environment requirements
separately before any installation workflow.

Existing outputs are never overwritten and missing parents are not created.
POSIX requests mode 0600 and preserves no-follow/directory-relative checks.
Windows refuses reparse paths, multi-link inputs, ambiguous names and observed
identity/name changes through retained native handles. Windows output inherits
the selected parent's ACL; no mode-0600 equivalent or ACL confidentiality check
is supplied. Native error categories can differ from POSIX while preserving
the same refusal and unchanged-data guarantees.

An output failure can leave a new partial or unconfirmed file. Inspect it and
choose a fresh name; do not treat it as successful or delete original inputs
to suppress a refusal. Windows does not clean up by deleting a pathname. Keep
trusted, stable local parents and quiescent input files. Neither backend is a
hostile-filesystem sandbox, immutable snapshot or power-loss durability proof.

Reports and locks can identify private projects through package names, versions
and hashes. They are not anonymized. Keep them and diagnostic tracebacks private.
See [the full format/bounds](README.md), [Windows contract](docs/WINDOWS.md) and
[qualification method](docs/PYTHON315.md).

## Qualification

The release's VALIDATION.json records eight actual Windows/Ubuntu × Python
3.12, 3.13, 3.14 and 3.15.2 lanes, exact patch versions, ZIP hash and counts.
Each uses a new dependency-free venv and imports from a fresh extraction outside
the checkout. All 81 methods run, including five copied-runtime CLI tests with
socket/process actions denied inside each child. CI requires native Windows
hardlinks, symlinks and junctions. Opposite-platform cases and unavailable
alternate short-name spellings are explicit skips, never passes.

No original report or real package install is tested. Network/virtual storage,
hostile concurrent mutation, Windows ACL privacy, free-threaded Python, other
architectures and hardware/power-loss behavior remain unqualified.
