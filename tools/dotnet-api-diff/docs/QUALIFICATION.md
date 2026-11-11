# Standalone release qualification

.NET Public API Diff 0.1.0 is distributed as a source ZIP. Native qualification
begins from fresh extracted source, not a checkout with old build products.
Release `VALIDATION.json` records actual SDK/interpreter versions, lane
outcomes, counts and skips. A planned matrix is not proof of passing tests.

## Required lanes

| Platform | Pinned SDK | Target |
| --- | --- | --- |
| Windows x64 | 10.0.404 | .NET 10 LTS / default `net10.0` |
| Ubuntu x64 | 10.0.404 | .NET 10 LTS / default `net10.0` |
| Windows x64 | 11.0.100 | Explicit `net11.0` |
| Ubuntu x64 | 11.0.100 | Explicit `net11.0` |

Eight additional Windows/Ubuntu helper lanes use Python 3.12, 3.13, 3.14 and
3.15.2. They run source gates, compare generated source ZIP/build-manifest
bytes and verify optimized-Python refusal in `sdk.py`, `build.py` and
`qualify.py`. They do not build .NET. Helpers use the standard library and
refuse `-O`, `-OO` and `PYTHONOPTIMIZE`; Python is not a built CLI dependency.

Official SDK archive URLs/SHA-512 are pinned in [SDKS.json](SDKS.json).
The SDK helper checks the digest before extraction/execution, bounds downloads
at 512 MiB and records actual bytes; these are not official expected lengths.
Qualification checks the retained archive count/digest. Hashing archive bytes
does not attest the extracted SDK tree, host or later execution. Source ZIP
integrity uses SHA-256 separately. SDKs, generated DLLs, external binaries,
actual assemblies/reports, originals and raw diagnostics are not bundled.

## Checks and interpretation

The source gate verifies the allowlist/manifest, hashes, sizes, syntax/data,
local links, absence of package references and selected privacy indicators.
It cannot prove perfect secret detection, exclusive authorship or complete
security clearance. Packaging requires reviewed source committed in Git and
compares selected bytes with `HEAD`.

Each native lane verifies/extracts the ZIP, runs the source gate and restores/
builds the harness project, whose references build the CLI and both fictional
libraries: **all four projects** must use the selected framework. .NET 11
requires `-p:TargetFramework=net11.0` on both restore and build. NuGet feeds
remain cleared; matching reference packs must already exist in the SDK.
Missing packs fail. No NuGet implementation packages are used. Warnings are
errors, and generated outputs stay in the private workspace.

The native harness covers supported metadata/signature forms, six golden
declaration differences, equal comparisons, exclusions, malformed/limited
generated inputs, CLI statuses, fresh reports, preserved inputs and supported
path refusals. The fixture initializer marker must remain absent. Real
copied-app subprocess checks exercise built app files with the matching
runtime. Fictional fixture DLLs are generated during testing, not distributed.
`Inspector.cs`, report format and both fixture API sources remain unchanged.
`Program.cs` changes only to check output-leaf metadata before creation and
refuse observed existing leaves, including dangling symbolic links. The
existing native cases retain that output-preservation requirement. This
precheck does not remove check/create races or provide atomic containment.

The authored walkthrough expects one added, two removed and three changed
declarations, **exit 1**. Equal supported declarations return `0`; input/output/
coverage errors return `2`. Expected difference status must not be mislabeled
as a failed test or converted into equality. Any platform/privilege skips must
remain explicit; skipped assertions are not passes. Hosted qualification
requires native link-refusal coverage rather than accepting unavailable-link
privilege as evidence.

This qualifies only authored supported metadata cases. The preserved
[format/exclusions](FORMAT.md) and [metadata-reader trust boundary](PROVENANCE.md)
still apply. Input assembly code is not loaded, but metadata processing is
not a security sandbox: hostile metadata can crash/hang the reader. No case
count establishes arbitrary-DLL safety, binary/runtime/game compatibility,
semantic-versioning correctness or permission to publish API reports.

## Reproduce with private outputs

From the reviewed committed repository module:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
```

The new output's parent must exist. This source packaging command creates the
ZIP, build manifest and checksum file; it does not build .NET. The SDK helper
uses `--version` and `--out`, producing an archive, `sdk-receipt.json` and
`runtime/dotnet[.exe]` beneath its new private output directory.

The qualification inputs select existing artifact and SDK-output directories:

```text
python -B packaging/qualify.py --packages ABSOLUTE_ARTIFACT_DIRECTORY --sdk ABSOLUTE_SDK_DIRECTORY --framework net10.0 --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

`--packages` contains the source ZIP and `build-manifest.json`; `--sdk` contains
the provisioner's archive/receipt/runtime. Workspace/report must not exist;
their parents must exist. Use matching SDK 11.0.100 and `--framework net11.0`
for the other target. Manual Windows/Ubuntu commands and the fictional
walkthrough are in [USAGE.md](../USAGE.md).

User-owned portable prerequisites do not inherently require administrator
access. Respect policy and required OS libraries; do not bypass restrictions.
Helpers apply process-only global-tools `PATH`, ASP.NET certificate, telemetry
and build-server opt-outs; use the same settings before manual SDK commands.
Network is needed for explicit prerequisite downloading, not by the built CLI.

Publish sanitized structured validation. Keep raw logs, generated binaries,
SDKs, machine/account details and actual inputs/reports private. Exact actual
counts come from release `VALIDATION.json`. The original .NET 8 result in
[VALIDATION.md](VALIDATION.md)—52 assertions with one privilege skip, or 53
when that fixture runs—is historical evidence, separate from this release's
fresh Windows/Ubuntu .NET 10/11 matrix.
