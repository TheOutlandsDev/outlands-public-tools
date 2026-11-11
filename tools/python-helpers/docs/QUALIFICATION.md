# Standalone download qualification

Python Helpers 0.1.0 is a reviewed **source-only library** release, without a
CLI/installer. Qualification begins with fresh extracted bytes, not a checkout
with an existing environment. Actual versions/counts/outcomes/skips belong to
release `VALIDATION.json`; planned coverage is not a passing result.

## Required scope

Eight lanes cover Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each uses a new venv **without pip or installed distributions**, adjacent
`helpers.py`/`helpers_windows.py` and authored disposable JSON/structures. The
library and helpers use only the standard library; no network/model/account is
required. Interpreters/OS prerequisites are separate and retain their licenses.

The original baseline has **five shared helper test bodies plus 40 input
methods**. Method-AST comparison preserves the original five bodies/assertions;
minimal standalone scaffolding imports no unrelated tools. Discovery must retain
that baseline rather than testing only module-local input methods. Another 26
copied-library process consumers call real APIs from the selected two-file copy
and compare complete values/fixed errors, not mocked library return values.

Zero/missing discovery, wholly skipped groups, failures and unexpected skips
cannot qualify. Hosted Windows requires applicable native hardlink/symlink/
junction cases; relevant POSIX fixtures remain mandatory. Platform-only and
optional short-alias-absence skips need exact method/reason contracts. Unavailable
native privilege cannot qualify strict hosted coverage. Do not weaken a guard or
change device policy to force success.

## Checks and evidence boundaries

The source gate verifies exact selected inventory/manifest, hashes, sizes,
Python/structured-data syntax, module-local links and selected privacy indicators.
It does not prove perfect secret detection, exclusive authorship or complete
security clearance. The ZIP contains no interpreter/dependency binary, actual
JSON/results, original private helper or raw diagnostic log.

All eight lanes independently rebuild source from committed reviewed Git bytes
and compare **both ZIP and build-manifest bytes**. Sorted source members and
fixed synthetic archive metadata support deterministic identity. The two helpers,
`build.py` and `qualify.py`, refuse `-O`, `-OO` and `PYTHONOPTIMIZE` before
assertions can be disabled.

Existing regressions and copied API processes cover object/BOM/duplicate-key/
number semantics, exact byte-limit validation, fixed loader errors, known-key
normalization, independent structure copies, unknown/free-text preservation,
depth/type errors, source-byte preservation, native path/identity guards and
interruption cleanup. Exponent overflow and caller-supplied float behavior
remain unchanged; no new finite-number policy is inferred from passing fixtures.

The consumer records structured outcomes, but the API itself returns values or
raises `HelperError`; it has no CLI exit/report schema. Fixed displayed errors
do not anonymize traceback paths, retained exception contexts, decoded values or
logs. Known-key redaction is not privacy, secrecy or rights clearance. The
preserved [INPUT-CONTRACT.md](INPUT-CONTRACT.md) remains historical contract/
evidence; standalone fresh results are separate.

## Reproduce privately

From reviewed committed repository source, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Both package outputs must be new with existing parents and use the same committed
source. Qualification input artifact directories must exist; workspace/report
must be new absolute paths with existing parents. All generated work and receipts
stay in an external [private workspace](PRIVATE-WORKSPACE.md), not source.

A local/consumer run may omit `--reference-build`, honestly recording
`identical_zip` and `identical_build_manifest` false. It supplies no independent
Git-source rebuild proof. All eight hosted release lanes must record both true.
Separately hashing and testing an anonymous public download provides consumer
evidence with its own scope. See [USAGE.md](../USAGE.md) for explicit imports,
private fixtures, structured API outcomes and input/runtime hash checks.

User-owned Python/venvs do not inherently require administrator access. Respect
policy and required OS support without bypasses. Keep real inputs/results,
exceptions, paths, captures, interpreter trees and raw logs private. Publish
only reviewed source assets and sanitized validation with actual versions/skips.

## Limits that remain

Loader bytes are bounded (1 MiB default, explicit override at most 16 MiB),
and redaction has its preserved depth bound. These are not total CPU, memory,
JSON-depth, result-size or elapsed-time quotas. Loader input is object-only;
default duplicate-key/number behavior remains, not schema or finite-number
validation. Redaction preserves unknown/free-text/identifying data and floats.

Trusted quiescent ordinary local inputs remain required. Sampled native/path/
size/time checks have race windows; no atomic snapshot, hostile-filesystem
sandbox, universal I/O deadline, remote/live/provider or power-loss acceptance
is claimed. Read [INPUT-CONTRACT.md](INPUT-CONTRACT.md) and
[PROVENANCE.md](PROVENANCE.md) before making broader claims.
