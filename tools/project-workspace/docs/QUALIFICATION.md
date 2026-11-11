# Standalone download qualification

Project Workspace 0.1.0 is a reviewed **source-only** release. Qualification
begins with freshly extracted bytes and a clean interpreter environment.
Actual versions/counts/outcomes/skips belong to release `VALIDATION.json`;
intended coverage is not a passing result.

## Required scope

Eight lanes cover Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each uses a new venv **without pip or installed distributions**, adjacent
`workspace.py`/`workspace_windows.py` and authored disposable opaque inputs.
The CLI and helpers use only the standard library. No network/model/account
is needed; interpreters and OS prerequisites are separately supplied/licensed.

The original baseline contains **six shared `WorkspaceTests` bodies plus 40
safety methods**. Method-AST comparison preserves the original six bodies and
assertions; minimal standalone scaffolding imports no unrelated tools. Module-
only discovery must not omit the shared six. Another 26 copied-runtime process
consumers exercise actual CLI/JSON/results and complete file layouts/bytes,
not mocked successful return values. The release's exact selected IDs/counts
and results are recorded in its validation evidence.

Zero/missing discovery, wholly skipped modules, failures and unexpected skips
cannot qualify. Hosted Windows requires applicable native hardlink/symlink/
junction fixtures; relevant POSIX cases remain mandatory. Platform-only and
optional short-alias-absence skips must match exact method/reason contracts.
Unavailable native privilege cannot qualify strict hosted coverage. Do not
weaken a guard or bypass device policy to obtain a pass.

## Source, packaging and behavioral evidence

The source gate verifies the exact selected inventory/manifest, hashes, sizes,
Python/structured-data syntax, module-local document links and selected privacy
indicators. It does not establish perfect secret detection, exclusive authorship
or complete rights/security clearance. The ZIP includes no interpreter/dependency
binary, actual input/generated workspace, private template or raw diagnostic log.

All eight lanes independently rebuild committed reviewed source and compare
**both ZIP and build-manifest bytes**. Sorted members and fixed synthetic
archive metadata support deterministic identity. `build.py` and `qualify.py`
refuse `-O`, `-OO` and `PYTHONOPTIMIZE` before assertions can be disabled.

Behavioral coverage includes plan with/without source, no-write plan behavior,
source limits/opaque copies, complete summary/layout/metadata values, neutral
names, input/runtime preservation, existing-destination refusal, path/native
identity guards, short writes, late failures, readback and interruption cleanup.
Creation failures retain partial or complete-looking unconfirmed output.
Matching hashes/populated trees never replace the actual successful result.

The original POSIX bodies, folder/name rules, neutral template and
[WINDOWS.md](WINDOWS.md) remain preserved. Historical observations in that
contract are separate from fresh standalone source/download qualification.
Windows's native readback/exclusive-output scope must not be attributed to a
broader POSIX behavior than the retained implementation provides.

Windows qualification exposed a pre-fix output bug: the CRT could create a
dangling symlink's missing target despite the exclusive-open flags, before a
later native name check failed. The release backend checks the output leaf
with `lstat` and refuses every observed existing leaf before `os.open`.
The CLI, POSIX bodies, template and historical filesystem document remain
unchanged; the Windows backend has this reviewed output-leaf patch. Fixed
runtime pins and `runtime_unchanged` lane evidence refer to the selected
release bytes throughout a run, not pre-fix baseline equality.

A separate before/after probe must retain the failure against pre-fix source
and confirm the corrected backend passes the **same unchanged** dangling-output
fixture. Its two executions are separate from the eight 72-method release
lanes (576 selected methods). Original method IDs/assertions remain preserved;
the fixture and hash guards must not be weakened to obtain a passing result.
Actual probe/lane outcomes belong to release validation. This observed-leaf
check is not race immunity, atomic creation or a hostile-filesystem guarantee.

## Reproduce privately

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new with existing parents and use the same committed
source. Qualification input artifact directories must exist; workspace/report
must be new absolute paths with existing parents. Generated work and receipts
stay in an external [private workspace](PRIVATE-WORKSPACE.md), outside source.

A local/consumer run may omit `--reference-build`, honestly recording
`identical_zip` and `identical_build_manifest` false. It supplies no independent
Git-source rebuild proof. All eight hosted lanes require both true. Anonymous
download hashes/source checks and fresh consumer execution provide separate
evidence. [USAGE.md](../USAGE.md) supplies a fictional plan/create verification
driver with complete JSON/exit comparisons and input/runtime/output hashes.

User-owned Python/venvs do not inherently require administrator access. Respect
policy and OS requirements without bypasses. Keep actual inputs/workspaces,
paths, captures, interpreter trees and raw diagnostics private. Publish only
designated reviewed source assets and sanitized validation with actual skips.

## Limits that remain

The 16 MiB source bound is not a total CPU/memory/deadline quota. Planning reads
a selected source and reserves nothing; reads can affect OS access metadata.
Only unnamed opaque file data is copied, without streams, ACLs, ownership,
topology or timestamps. Copied bytes can remain private/identifying.

The early ignore file can be missing/incomplete and is not access control.
Permissions depend on parent ACLs and OS/Python; confidentiality is not audited.
There is no automatic recursive deletion, rollback or confirmed success after
failure. Sampled pathname/create/open checks retain race windows under trusted
quiescent local parents. No atomic transaction, hostile-filesystem sandbox,
universal I/O deadline, live/cloud/remote-provider, hardware/power-loss or
all-stream backup acceptance is claimed. See [PROVENANCE.md](PROVENANCE.md).
