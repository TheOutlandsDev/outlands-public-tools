# Package Layout Checker

Check caller-declared package files, optionally parse Python syntax and match
literal rules, without importing/executing source or changing package files.
The CLI writes JSON to stdout only. **PASS covers declared checks**, not an
exact export allowlist, privacy clearance or application correctness.

Download the **0.1.0 standalone source ZIP** from the
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/package-layout-checker-v0.1.0),
extract into a fresh folder and follow [USAGE.md](USAGE.md). Keep
`layout_check.py` and `layout_windows.py` adjacent. Use Python **3.12–3.15**;
qualification selects 3.15.2 for that minor. Only standard-library/OS APIs are
needed, without pip packages, network, model, account or installation. No
interpreter, dependency binary, actual project/manifest/result, private original
verifier or raw diagnostic log is bundled.

```text
python -B layout_check.py --root EXISTING_FICTIONAL_PACKAGE --manifest PRIVATE_LAYOUT_JSON
```

Both options are required. There is no project/data default, environment
expansion or report/output switch. Run from the extracted folder or select the
script by explicit path. Capturing stdout is a separate caller action.

## Declared manifest and results

```json
{"schema_version":1,"files":[{"path":"README.md"},{"path":"src/demo.py","python_syntax":true,"forbidden_literals":["FICTIONAL_DO_NOT_SHIP"]}]}
```

Each canonical relative `path` selects one file. Optional `python_syntax` uses
only the running interpreter's AST parser; optional `forbidden_literals` matches
case-insensitive literal text, not regex or semantic secrets. Presence-only
entries check metadata without reading bodies. Unlisted entries are not
enumerated or opened. Python syntax compatibility depends on the running parser.

| Outcome | Exit | Meaning |
| --- | ---: | --- |
| `PASS` | 0 | Every declared file/rule passed. |
| `FAIL` | 1 | One or more declared rows have finding codes. |
| `REJECTED` | 2 | Invalid control/arguments, unsupported platform or root/manifest access failure. |
| `REJECTED` / `INTERRUPTED` | 130 | Interrupted run; captured output may be incomplete. |

Completed reports contain `schema_version`, `status`, `checked_files`,
`failed_files` and ordered rows with `path`, `status`, `codes`. Rejections contain
only `status`/fixed `code`. Static help is separate. Missing, unsafe, unreadable,
invalid-text, syntax, literal and byte-limit failures are aggregated by file.
Source/literal values, parser excerpts, root/native paths and raw errors are
omitted, while relative filenames remain identifying. Protect actual manifests,
private literal rules, results, caller captures and library tracebacks.

## Bounds and safeguards

A manifest is at most **64 KiB**, with **1–100 files** and relative paths up to
512 characters. Selected files are at most **256 KiB** each. Content checks
reserve at most **2 MiB per run**, including reservations for reads that fail.
Each row permits at most **16 literals of 1–256 characters**. Duplicate JSON
keys, nonstandard non-finite constants, unknown fields, wrong rule types,
duplicate/case-colliding paths, absolute/traversing paths and unsafe characters
are rejected. These bounds are not total CPU/memory/AST/deadline quotas.

POSIX uses directory descriptors and required no-follow/directory/nonblocking
primitives. Windows uses the separate native reader with retained ancestor/file
handles, normalized names/identity checks, read-only sharing and noninheritable
binary descriptors. Supported ordinary single-link manifest/selected files are
required; observed symlink/reparse/special/multilink inputs are refused. Windows
also rejects unsupported volume/name/short-alias/stream forms. Use stable trusted
fully spelled local paths. The [Windows contract](docs/WINDOWS.md) preserves
its historical wording with a standalone review hyperlink.

Checks and sharing are sampled, not an immutable/atomic snapshot or hostile-
filesystem sandbox. Mount/drive rebinding, mapped views, live/network/virtual
providers, blocked I/O, power loss and ACL privacy remain outside acceptance.
Reads can affect access metadata; Python caches are separate. Nothing in this
checker scans unlisted files, proves absence of extra/private content, audits
dependencies, establishes ownership/licensing or authorizes a release.

## Walkthrough and qualification

[USAGE.md](USAGE.md) supplies isolated fictional packages and outside-package
manifests, complete clean/finding/rejection JSON/exit outcomes, nonexecution/
source-omission checks and input/manifest/tree/runtime hashes. Use an external
[private workspace](docs/PRIVATE-WORKSPACE.md). User-owned Python/venvs do not
inherently require administrator access; respect device policy without bypasses.

Eight fresh extracted-ZIP Windows/Ubuntu Python lanes select 64 existing methods
plus copied CLI consumers in no-pip/no-distribution venvs. The 33 original POSIX
methods intentionally skip on Windows and must run on supported Linux; strict
hosted Windows requires applicable native link/junction cases. Actual versions,
counts/outcomes/skips belong to release `VALIDATION.json`, not planned coverage.
See [qualification](docs/QUALIFICATION.md). Historical evidence remains separate.

Selected original source is [MIT licensed](LICENSE), with retained notices and
AI-assisted preparation without exclusive-authorship claims. See
[provenance](docs/PROVENANCE.md),
[collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md)
and the [earlier review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-19-PACKAGE-LAYOUT-WINDOWS.md).
[Report an issue](https://github.com/TheOutlandsDev/outlands-public-tools/issues)
with invented fixtures and complete outcomes. Do not attach actual package
contents, private rules/manifests, identifying paths or raw logs.
