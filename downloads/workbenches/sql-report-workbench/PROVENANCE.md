# SQL Report Workbench package provenance

Package version 0.1.1; underlying application declares 0.1.0. The complete
application tree is copied byte for byte from public source `f67b3c5e686595336d243d44e85bc2b3ccc76b0d`, under
`systems/sql-report-workbench`. The application's SOURCE-MANIFEST.json remains unchanged and
continues to check the application/ subfolder. No database, backup, session marker,
raw test output, browser/runtime binary or installed dependency is a package input.

Only START-HERE.md and this outer provenance guide are added around application/.
The generated PACKAGE-MANIFEST.json records each member's length/hash plus source
and packaging revisions. The release matrix and SHA256SUMS.txt pin the ZIP bytes.
Hashes establish consistency, not author identity, signatures or encryption.

## What acceptance runs

Each fresh ZIP is verified before extraction into a new path containing spaces.
Its original source manifest is checked, followed by the existing standard-library
suite, a new fictional demo instance, an independent result/export check, a separate
CLI reopen and refusal of an existing demo path without byte changes. SQL aggregates
are recalculated in Python; developer exports must preserve the original five source
files from revision 1. Every private export member is hash-checked.

Windows and Ubuntu with Python 3.12/3.13 also install hash-locked development-only
browser dependencies and run the application's existing actual Chromium suite from
the extracted ZIP. Browser routes refuse external requests. All four platform
packages must have identical bytes before a new focused release can publish.
Exact observed outcomes belong to that source/package revision's CI receipt;
these instructions are expected behavior, not a claim that the current machine passed.

## Rebuild

Check out the public packaging revision from release-matrix.json with Git history.
Run `python -B downloads/workbenches/build.py --output ABSOLUTE_NEW_OUTPUT`, then
`python -B downloads/workbenches/accept.py --packages ABSOLUTE_OUTPUT --workspace
ABSOLUTE_NEW_PRIVATE_WORKSPACE` as one line. Existing output/private paths are
refused. Add `--browser` only in a prepared development environment. Raw logs,
private instances and generated reports remain in the private acceptance workspace;
only the sanitized acceptance.json numeric receipt is suitable for deliberate review.

## Limits

This is a single-user local application using original fictional inputs. It is not
an installation on a clean operating system, a production or employer integration,
a multi-user service, a complete restore or power-loss qualification, an OS sandbox,
or universal privacy/rights clearance for later caller data. Keep real content out
of public screenshots/issues. Original software was developed with AI assistance;
upstream source origins, attribution and runtime limits remain in application/docs/.
