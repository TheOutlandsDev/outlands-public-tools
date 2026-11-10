# Dependency and extracted-package qualification

## Reproduction and change

The unchanged Windows Python 3.15.2 suite with the original pins ran 56 methods:
54 passed, two platform/privilege skips. A separate environment with
pypdfium2 5.15.2 and pypdf 7.0.0 reproduced the recorded 38 unsuccessful methods
(13 assertion failures and 25 errors), with two skips. The exact-version guard
refused pypdfium2 before geometry inspection. These are pin-contract refusals,
not evidence of 38 parser API regressions. The old environment is retained.

Version 0.2.0 updates the reviewed runtime pypdfium2 pin to 5.15.2 and test-only
pypdf to 7.0.1 (the current PyPI release when reviewed on 2026-11-10).
Seven other runtime versions remain unchanged. Inspection, geometry, worker,
input, output and privacy logic is unchanged. The exact-version guard remains.
No API adaptation was required by the authored fixture suite.

## Repeatable methods

Commit reviewed source before building:

```text
python -B source_check.py
python -B packaging/build.py --out NEW_ABSOLUTE_PACKAGE_DIRECTORY
python -B packaging/qualify.py --packages PACKAGE_DIRECTORY --workspace NEW_ABSOLUTE_LOCAL_DIRECTORY --report NEW_ABSOLUTE_JSON_FILE
```

The build has a fixed source-only allowlist, normalizes LF text, verifies every
member against the selected Git commit, and creates a deterministic ZIP with
the source manifest. No environment, generated PDF/report or dependency binary
is included. CI independently rebuilds and compares exact ZIP bytes per lane.

Each qualification extracts to a new private directory, validates all names,
sizes/hashes, creates a fresh venv, installs the complete runtime with
`--require-hashes --only-binary=:all:`, and runs actual CLI fixtures before
installing test-only pypdf from the dev lock. `pip check` and installed version
records are checked. A deliberate bad hash is refused in a separate dry run;
the installed set is untouched. The source gate and explicit PyPI advisory
check run separately from PDF inspection. The full suite runs with warnings
as errors from the extracted copy; imported source locations are checked.

The workflow uses Windows/Ubuntu x64 and CPython 3.12, 3.13, 3.14 and 3.15.2.
Native symlink refusal is mandatory in hosted CI; FIFO is POSIX-only. Local
Windows accounts lacking symlink permission report an explicit skip. Skips
are never counted as passes. The release's VALIDATION.json is the authoritative
eight-lane record with actual patch versions, dependency pins, counts and skips.

Tests cover real authored PDF rotations, origins, crop/media boundaries,
encryption refusal, malformed inputs, page/character/finding/byte limits,
worker timeout/protocol/output bounds, dependency/hash contracts, exclusive
outputs and geometry-only privacy. Fresh CLI tests additionally verify offline
audit denials, complete report hashes, textless review, incomplete failures and
input/output preservation. No original document or extracted text is published.

PyPI version records reported no listed advisories when reviewed. This is not
exhaustive vulnerability clearance. See the retained [initial validation](VALIDATION.md)
for historical visual fixture checks; no new rendering claim is made here.
The broader collection/bundle Python contracts and cumulative review counts
are not expanded by this single-tool qualification.
