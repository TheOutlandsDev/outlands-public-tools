# Qualification contract — 0.1.0

This record defines the release gates. Accepted `VALIDATION.json`, attached to
the source release, records actual native outcomes for its reviewed commit.
Required selections are not assumed passes. The unchanged historical
[validation record](VALIDATION.md) describes an earlier source/platform scope.

## Source and interpreter identity

The source ZIP has 29 explicitly allowlisted source files plus
`SOURCE-MANIFEST.json`, 30 members. It includes original MIT implementation,
tests, authored docs/fixtures generator and qualification/build helpers, not
Python interpreters, module binaries, generated inputs/reports, real inventories,
raw logs or private methods. Build/checksum manifests bind the exact ZIP.
Hashes and unsigned manifests verify bytes, not authentic authorship or rights.

`PYTHON-LOCK.json` pins CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 and the
20261110 standalone archive recipe separately for Windows and Ubuntu. Preparation
verifies archive SHA-256, actual version and actual base executable SHA-256.
Each archive lane uses a new `venv --without-pip` with zero installed
distributions. No third-party Python packages or native module tools are needed.
No administrator permission or global interpreter/PATH change is required.
Runtime CLI/generator uses `-E -s -B`; independent probes/helpers use `-I -B`.

## Preserved and copied checks

All 38 original test methods remain: 21 module/CLI methods and 17 support methods.
The runtime/generator three files, original two test files and historical four
docs remain byte-identical to the reviewed baseline. The native harness selects
the original methods and binds actual interpreter/source identity; it neither
rewrites the protected tests nor replaces their assertions. Reported native
metrics are derived from those originals rather than copied-method totals.

Thirty additional copied-runtime methods use external copies, disposable owned
fixtures and the actual CLI. Each lane selects 68 methods; Windows/Ubuntu across
four versions select 544 in total. Actual passed, skipped, failed and errored
counts are separate. Platform-opposite FIFO/Windows-stream cases have finite
named skip reasons. A local privilege skip requires the exact actual Windows
symlink privilege error; hosted strict mode does not allow that skip. Hardlink
safeguards must execute. Skip-policy IDs must be selected and unique.

Coverage includes dependency closure/order, path/basename resolution and
ambiguity, duplicate declarations/selections/tokens, unresolved prerequisite
propagation, closed witnesses versus merely blocked dependants, unrelated
findings, optional declared inventories, unsupported syntax, empty scope,
literal compressed suffixes and deep/limited graphs. Safe I/O checks cover
distinct stable regular inputs, links/reparse routes/aliases/streams, fixed
errors, UTF-8/control/line/byte bounds, fresh output, unchanged inputs, HTML
escaping and report manifests. Copied checks do not substitute for originals.

## Executable guide and evidence limits

The [fictional walkthrough](../USAGE.md) is executed as its exact published
Python block in a fresh no-pip 3.15.2 environment using the actual copied
runtime. It supplies independent explicit whole-report expectations, verifies
source/input/report bytes and preserves working evidence separately from one
committed-head rerun. Its 38 cases include 23 completed reports and fourteen
controlled incomplete refusals plus fixture generation. It checks 46 payload
hashes, 50 input hash observations, 38 inputs and 107 exact input/report files.
Three default/details pairs keep observations identical after opt-in fields.

All checks use authored text. Scope flags remain false for module binary access,
module loading/decompression, kmod invocation, device access, real system
inventory, kernel ABI compatibility verification and runtime load verification.
Module suffixes are not decompressed, optional inventory is not a filesystem
scan, and selected-plan completeness does not establish inventory membership.
Unknown or ambiguous prerequisites stay blocked; witness paths are not an
enumeration of every cycle. Unsupported rows limit coverage. Empty scope is
not proof of system completeness or valid load behavior.

No native kmod parity, binary/ABI/vermagic/signature/builtin/alias analysis,
actual module loading, kernel/device test, bootability, hostile-writer sandbox,
atomic snapshot, transactional rollback or durable-output guarantee is claimed.
Failure can leave a partial fresh report directory; only a completed verified
manifest constitutes the report's byte-consistency evidence. Omitted names and
filenames are not anonymization. Keep real inventories/reports private.

## Reproduce the release gates

Use the pinned [Python preparation helper](../packaging/prepare_python.py),
[source builder](../packaging/build.py) and [archive qualifier](../packaging/qualify.py)
to prepare the exact interpreter and build/qualify in a new owned workspace.
The native adapter and copied-runtime suite record finite skips separately;
read the actual workflow results for the release commit. Public validation
contains sanitized counts, versions and byte identities, not raw logs, local
paths, machine identity or operational captures. CI success establishes these
bounded fictional-source checks only.
