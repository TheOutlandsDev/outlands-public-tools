# Release qualification

Hash Journal 0.2.0 is distributed as a source ZIP. Native qualification starts
from a fresh extraction, rather than a working tree with existing build
products. The release's `VALIDATION.json` records actual lane outcomes and
discovered/passed/failed/skipped totals. Read it with the source version and
published artifact hashes; planned coverage is not evidence of a passing run.

## Supported lanes

| Operating system and architecture | Pinned SDK | Application target |
| --- | --- | --- |
| Windows x64 | 10.0.404 | .NET 10 LTS / `net10.0` (default) |
| Ubuntu x64 | 10.0.404 | .NET 10 LTS / `net10.0` (default) |
| Windows x64 | 11.0.100 | .NET 11 / `net11.0` (explicit override) |
| Ubuntu x64 | 11.0.100 | .NET 11 / `net11.0` (explicit override) |

Eight additional helper lanes cover Windows and Ubuntu with each of Python
3.12, 3.13, 3.14 and 3.15. They run the source gate, generate and byte-compare
source ZIP/build-manifest outputs, and check optimized-Python refusal in
`sdk.py`, `build.py` and `qualify.py`. These helper lanes do not build .NET.
The helpers use only Python's standard library. They refuse `-O`, `-OO` and
`PYTHONOPTIMIZE`; Python is not required by a built CLI.

SDK **10.0.404** and **11.0.100** are selected from official archives. Platform
URLs and SHA-512 digests are pinned in [SDKS.json](SDKS.json), and the SDK helper
verifies the downloaded archive before extraction/execution. Source-ZIP
integrity uses SHA-256 separately. SHA-512 is the SDK archive identity check;
the provisioner limits downloads to 512 MiB and records actual byte counts,
rather than treating metadata as an expected byte length. Qualification checks
the retained archive against that recorded count and the pinned SHA-512.
No SDK/runtime, dependency binary, generated app, real journal, original
private project or raw diagnostic log is bundled.

## What the checks establish

The source gate checks the reviewed allowlist, file sizes and SHA-256 manifest,
Python syntax, JSON/XML, local Markdown links, package-reference absence and
selected privacy indicators. It is an inventory/consistency gate, not proof
of perfect secret detection, exclusive authorship or complete security review.

Each native lane extracts fresh source and restores/builds using the selected
SDK with `NuGet.Config`, which clears feeds. There are no NuGet packages, and
the required reference packs must already exist in that SDK. Missing packs
must fail. Warnings are treated as errors. For .NET 11, restore and build both
use `-p:TargetFramework=net11.0`, including the native test project.

The native generated-fixture harness checks unchanged version 1 rules, golden
hashes, exact text/Unicode, tampering, reordering, expected heads/counts,
valid-prefix truncation, JSONL/UTF-8 parsing, size limits, bounded file I/O,
input preservation, fresh outputs, CLI metadata/errors and supported
link/special-file refusals. Copied-app checks exercise the actual built CLI
with its matching .NET runtime, rather than substituting an in-process call.
Test data is fictional and disposable. Platform/permission skips remain
visible and are never counted as passes.

Qualification includes the fictional create → append → anchored-verify
workflow. It preserves the one-record input and verifies the new two-record
output against the independently calculated head/count. That is evidence for
the stated bounded workflow, not long-term retention or event authenticity.

## Reproduce safely

Use a normal supported Python and an external
[private workspace](PRIVATE-WORKSPACE.md). Maintainers generate the qualified
source artifact from the reviewed repository checkout after committing its
source and manifest. Every selected file must match committed `HEAD`; this
packaging step requires Git and does not run from a standalone extraction:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
```

The output directory must not exist, and its parent must exist. The command
creates the source ZIP, `build-manifest.json` and `SHA256SUMS.txt`. Packaging
requires no .NET build. A release user can instead use the downloaded source
ZIP and its matching published build manifest.

The SDK helper accepts `--version` and `--out`. Its new output directory
contains the downloaded archive, `sdk-receipt.json` and extracted
`runtime/dotnet[.exe]`; its parent must already exist.

The qualification helper's `--packages` selects the artifact **directory**
containing the source ZIP and `build-manifest.json`. `--sdk` selects that SDK
helper output **directory**. Both input directories must already exist.
Select `net10.0` with SDK 10.0.404 or `net11.0` with SDK 11.0.100. Supply a new
private workspace directory and a report filename that do not exist; their
parent directories must already exist:

```text
python packaging/qualify.py --packages ABSOLUTE_ARTIFACT_DIRECTORY --sdk ABSOLUTE_SDK_DIRECTORY --framework net10.0 --workspace ABSOLUTE_PRIVATE_WORKSPACE --report ABSOLUTE_PRIVATE_REPORT_JSON
```

Replace the placeholders with explicit paths and select your normal Python
3.12–3.15 executable. Use another fresh workspace/report for another lane.
Run `packaging/qualify.py --help` for available option details. Manual build,
native-test and anchored-walkthrough commands are in [USAGE.md](../USAGE.md).
Before manual SDK use, set `DOTNET_ADD_GLOBAL_TOOLS_TO_PATH=false` in the
process environment to prevent first-run user-`PATH` changes. The SDK and
qualification helpers already apply this setting, disable telemetry and
control build servers in their child process environment only. They do not
persist these opt-outs as user or machine settings.

Portable SDK extraction and user-owned test work do not inherently need
administrator access. Respect device policy, and leave unsupported system
prerequisites or restricted link fixtures visible in reports. Do not bypass
restrictions to make a lane pass. Initial downloads can need network access;
the built CLI itself needs no network, Python, model or account.

Publish the sanitized structured validation summary. Keep raw diagnostics,
private paths, machine/account details, builds and test workspaces outside the
release. Exact actual totals come from the release `VALIDATION.json`.

## Historical evidence and limits

The 0.1.0 local result was **73 discovered, 69 passed, four skipped, zero
failed** on Windows using SDK 9.0.310 targeting .NET 8. Its two link cases
lacked permission; the Unix mode and FIFO cases were platform skips. This
historical result remains in [VALIDATION.md](VALIDATION.md), separately from
0.2.0's four SDK/runtime and eight helper-lane results. Do not reuse its totals
as current release qualification.

No case count establishes a hostile-filesystem sandbox, atomic snapshot,
concurrency-stress acceptance, immutable journal store, external anchor
service, factual-event audit or operational recovery guarantee. Size/time and
observed-link checks have race windows. A failed fresh output can be partial.
A valid prefix remains internally valid without independently retained
head/count values. A matching head does not prove authorship, truth or time.
See [FORMAT.md](FORMAT.md) and [SECURITY.md](../SECURITY.md).
