# Qualification contract — 0.1.0

This record defines release gates. Accepted `VALIDATION.json`, attached to the
source release, records actual outcomes for its reviewed commit. Required
selections are not assumed passes. The unchanged [historical validation](VALIDATION.md)
describes a separate earlier source/platform scope.

## Source and interpreter identity

The source ZIP contains 31 explicitly allowlisted source files plus
`SOURCE-MANIFEST.json`, 32 members: original MIT implementation/restricted XML
reader/support, tests, authored docs/generator and qualification/build helpers.
Python interpreters, actual device manifests, binaries, generated inputs/reports,
raw logs and private methods are excluded. Checksums/build manifest bind the
exact ZIP; unsigned hashes show consistency rather than authentic authorship.

`PYTHON-LOCK.json` pins CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 and the
20261110 standalone archive recipe separately for Windows and Ubuntu. Preparation
verifies archive SHA-256, actual version and actual base executable SHA-256.
Archive lanes use new `venv --without-pip` environments with zero distributions.
No third-party Python/native XML packages, Expat pin, Android SDK, administrator
permission or global interpreter/PATH modification are required. The original
bounded restricted reader remains unchanged. Runtime CLI/generator uses
`-E -s -B`; independent probes/helpers use `-I -B`.

## Preserved and copied checks

All 58 original methods remain: 27 VINTF/comparison/CLI, fourteen restricted-XML
and seventeen support methods. The four runtime/generator files, original three
test files and four historical docs remain baseline byte-identical. The native
harness selects originals and binds actual source/interpreter identity without
replacing their assertions. Metrics derive from those protected original tests.

Thirty additional copied-runtime methods use external source copies, disposable
owned fictional files and actual CLI execution. Each lane selects 88 methods;
Windows/Ubuntu across four versions select 704 total: 464 original and 240
copied selections. Actual passed/skipped/failed/errored counts stay separate.
Platform-opposite FIFO/Windows-stream skips are finite named cases. Local
privilege skips require the exact actual Windows symlink privilege error;
hosted strict mode permits no such skip. Hardlink safeguards must execute.
Every skip-policy ID must be selected and unique.

Coverage includes supported HIDL/AIDL index/comparison, equivalent forms,
identity/version removal-addition, transport/arch changes, ambiguity on either
side, selected fragment scope, type separation, unsupported modifiers/namespaces
and non-instance metadata. Restricted-reader checks cover balanced grammar,
one-pass references, comments/instruction handling, refusal of DTD/entity/CDATA,
malformed attributes/references/trees, depth/element/attribute/text bounds and
absence of native parser imports. Safe I/O checks cover distinct stable regular
inputs, links/reparse routes/aliases/streams, encoding/control/line/byte/count
budgets, fresh output, source immutability, HTML escaping and report manifests.
Copied methods supplement rather than replace original parser regressions.

## Exact executable guide and limits

The [fictional walkthrough](../USAGE.md) is executed as its exact published
Python block in fresh no-pip 3.15.2 using actual copied runtime. Explicit
whole-report expectations do not reuse the parser/matching implementation.
Working evidence is preserved separately from one committed-head rerun, with
twenty protected source hashes including the actual qualifier.

Its 51 cases include 25 completed reports, twenty-five controlled refusals and
fixture generation. It checks fifty report payload hashes, 39 input hash
observations, forty fixtures and 115 exact input/report files. Twenty default
reports/five details reports include four observation-equivalent privacy pairs.
Unknown/raw XML, comments and local filenames remain omitted with details;
omission is not anonymization because accepted fields/hashes/structure identify.

All eight scope flags remain false: native XML parser use, external resources,
device configuration merging, override application, compatibility-matrix
evaluation, runtime HAL service checks, device access and real device manifests.
No `assemble_vintf`/`checkvintf`, native HAL/device test, general XML conformance,
full schema validation, effective fragment/override merge, runtime/API-level
selection, bootability or complete system inventory is verified. Partial
supported results coexist with coverage; empty supported scope proves little.

Input/output checks are not an OS sandbox, atomic hostile-writer snapshot,
transactional rollback, hard I/O deadline or durable-output guarantee. Failed
writes can leave a partial fresh report; only a completed checked manifest
establishes report byte consistency. Use trusted stable inputs and owned parents.

## Reproduce the gates

Use the [pinned Python preparer](../packaging/prepare_python.py),
[source builder](../packaging/build.py) and [archive qualifier](../packaging/qualify.py)
in a new owned external workspace. The native adapter and copied suite report
finite skips separately; inspect actual workflow results for the release
commit. Public validation retains sanitized counts, versions and byte identities,
not machine paths, raw logs, real manifests or operational records. CI success
establishes bounded fictional-source checks, not deployment acceptance.
