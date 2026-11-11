# Standalone download qualification

Public Release Audit 0.1.0 is a reviewed **source-only** release. Qualification
starts with freshly extracted source and clean environments. Actual versions,
counts, outcomes and exact skips belong to release `VALIDATION.json`; intended
coverage is not a passing result.

## Required scope

Eight lanes cover Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each creates a new venv without pip or installed distributions and imports
adjacent `release_audit.py`/`audit_windows.py` from the selected extraction.
Only standard-library code is needed, without network/model/account access.
Interpreters/OS prerequisites are separately supplied/licensed.

The baseline has **19 shared `AuditTests` bodies plus 40 I/O methods**. Method-
AST comparison preserves the original 19 bodies/assertions; minimal standalone
scaffolding avoids unrelated imports. Module-only discovery must not omit the
19. Another 26 copied-runtime process consumers exercise real CLI behavior,
complete summaries/reports/manifests, bounds and output preservation. That
selects 85 methods per lane, 680 across eight lanes; actual outcomes are separate.

Zero/missing discovery, wholly skipped modules, failures and unexpected skips
cannot qualify. Hosted Windows requires applicable native hardlink/symlink/
junction fixtures; relevant POSIX cases remain mandatory. Exact platform/
short-alias-absence skips must match method/reason contracts. Native privilege
failure cannot qualify strict hosted coverage. Do not weaken hash/assertion
guards or bypass device policy to force a pass.

## Source, outputs and evidence boundaries

The source gate checks exact selected inventory/manifest, hashes, sizes,
Python/structured-data syntax, module-local links and selected privacy markers.
It does not establish perfect secret detection, exclusive authorship or complete
rights/security clearance. No real export/marker/report, original private
implementation, interpreter/dependency binary or raw log is bundled.

All eight lanes independently rebuild committed reviewed source and compare
both ZIP and build-manifest bytes. Sorted members and synthetic fixed archive
metadata support deterministic identity. Both helpers refuse `-O`, `-OO` and
`PYTHONOPTIMIZE` before assertion guards can be disabled.

Coverage includes detector/filename/example exceptions, private literal markers,
stable input/control reads, bounds, inventories, manifest validation/mismatch,
outside-root outputs, existing-file refusal, short writes, late failures and
interruption. Dangling report and manifest links require explicit fixtures;
a refusal is insufficient if it creates the missing target before failing.
Any confined Windows output-guard correction needs exact reviewed diff and
before/after evidence on the same unchanged fixtures. Four diagnostic
executions (two baseline/two corrected) remain separate from the eight-lane
matrix; actual proof must distinguish expected baseline failure from passing
corrected source. This is not race or hostile-filesystem immunity.

Detector, CLI/POSIX behavior, report schemas/formatting and manifest contract
remain the preservation boundary. Lane runtime hashes identify the reviewed
release throughout a run; they do not assume Windows backend equality with an
older baseline. Historical [WINDOWS.md](WINDOWS.md) evidence stays separate
from fresh qualification and any reviewed output-guard fix.

Reports omit snippets but retain filenames, hashes and line numbers; they remain
private. `NO_PATTERN_FINDINGS` is not anonymity, ownership, semantic IP or
software-behavior clearance. Scanner/manual release review must use exact
selected bytes and independent evidence; the changed scanner cannot serve as
its own sole release authority.

## Reproduce privately

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new with existing parents and use the same reviewed
commit. Qualification input directories must exist; workspace/report must be
new absolute paths with existing parents outside source. Keep generated work
and receipts in an external [private workspace](PRIVATE-WORKSPACE.md).

Consumer runs may omit `--reference-build`, honestly recording `identical_zip`
and `identical_build_manifest` false, without independent Git-source rebuild
proof. All eight hosted lanes require both true. Anonymous hashes/source
comparisons and fresh consumer execution provide separate evidence.
[USAGE.md](../USAGE.md) supplies fictional complete JSON/exit comparisons and
input/control/report/runtime preservation checks.

User-owned Python/venvs do not inherently need administrator access. Respect
policy and OS prerequisites without bypasses. Keep actual exports, markers,
reports/manifests, paths, interpreter trees, captures and raw logs private.
Publish only designated reviewed assets and sanitized actual results.

## Limits that remain

Bounds are 20,000 encountered entries, 2 MiB/file and 64 MiB total. JSON controls
are bounded to 16 MiB; Windows encoded outputs to 64 MiB each. These are not
total CPU/memory/regex/deadline quotas. Root `.git` is excluded; unknown/binary/
archive/linked/private/runtime material requires review. History/tags/assets,
metadata/archive interiors, external links and software behavior are not
scanned. Streams, ACLs and topology are outside scope.

Private marker matching is literal/case-insensitive, not semantic detection.
False positives and missed secrets/identifiers remain possible. A replaceable
content/manifest pair can agree without authenticity or independent approval.
Retained partial or complete-looking output never proves command success.
There is no automatic cleanup/rollback or atomic multi-output transaction.
Trusted quiescent local paths and sampled checks retain race windows, without
a sandbox, universal deadline, live/provider or power-loss guarantee.
Permissions depend on parent ACLs and OS/Python; confidentiality is not audited.
