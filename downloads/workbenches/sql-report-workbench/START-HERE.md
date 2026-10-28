# SQL Report Workbench - start here

Run parameterized read-only SQL over an original neutral dataset; inspect report fields, compare saved revisions, review results and export checked private reports.

**Requirements:** CPython 3.12 or 3.13, its standard SQLite module, and a modern
browser on Windows x64 or Ubuntu x86_64. The application needs no pip packages,
account, hosted API or external database server. Browser test tools are separate.
This is downloadable source, not a bundled Python runtime or installed executable.

## One useful first run

1. Check this ZIP against SHA256SUMS.txt from the same release. Extract into a new
   folder. Keep START-HERE.md beside application/ and PACKAGE-MANIFEST.json.
2. Open a terminal in that extracted folder. Use a new private sibling path that
   does not exist; the commands below intentionally refuse an existing instance:

```text
python -B application/workbench.py --workspace ../fictional-sql-report-workbench-instance demo
python -B application/workbench.py --workspace ../fictional-sql-report-workbench-instance serve
```

Use `python3` where appropriate, after checking its version. Quote paths containing
spaces. Open the exact loopback URL printed by serve. Keep that URL private if it
contains an access token. Stop with Ctrl+C before another CLI command uses the
same instance. For another independent demo, choose a different new instance path.

Expect alpha = 8 and beta = 11; minimum 4 gives alpha = 5 and beta = 11. The revised query gives 9 and 12. One report validates; four artifacts and a seven-file private export are retained.

The demonstration stores private state outside the extracted source folder. It
uses only the included invented fixtures. Restart serve with the same workspace
to inspect persisted state. A saved database backup is not a complete-instance
restore: inbox files and separately exported files are outside that backup.

The same README and contract/validation documents are available offline inside `application/`.

## Inspect and reproduce

- [Application README, full workflow and limits](https://github.com/TheOutlandsDev/outlands-public-tools/blob/f67b3c5e686595336d243d44e85bc2b3ccc76b0d/systems/sql-report-workbench/README.md)
- [Runtime contracts](https://github.com/TheOutlandsDev/outlands-public-tools/blob/f67b3c5e686595336d243d44e85bc2b3ccc76b0d/systems/sql-report-workbench/docs/CONTRACT.md)
- [Existing application validation](https://github.com/TheOutlandsDev/outlands-public-tools/blob/f67b3c5e686595336d243d44e85bc2b3ccc76b0d/systems/sql-report-workbench/docs/VALIDATION.md)
- [Packaging provenance and acceptance](PROVENANCE.md)

```text
python -B application/release_source.py check
python -B -W error application/run_checks.py
```

These checks use temporary synthetic state. Native-link fixtures may be unavailable
on a restricted local account and must be reported as skips, not passes. Windows/
Ubuntu release CI requires applicable native link fixtures and separate real
Chromium workflows from the extracted ZIP.

**Download package 0.1.1 contains application source declaring 0.1.0.** This release
adds the outer handoff and verifies the fixed public source snapshot; it does not
rename or edit application runtime files. Earlier 0.1.0 source ZIPs remain unchanged.
Future user datasets, source, queries, notes, exports and backups stay private.
Approval/review is not publication clearance or universal secret detection.
