# Android Build Copy-Map Inspector

Review literal `PRODUCT_COPY_FILES +=` declarations in explicitly selected saved
Make text. Index source/destination/optional-owner words, repeated declarations,
destination conflicts, NFC/casefold portability collisions and file/parent path
candidates without evaluating Make or touching payload paths. Python 3.12 or
newer, standard library only, original [MIT source](LICENSE).

Only whole leading root variables can use explicitly supplied literal JSON
substitutions. No partition defaults, environment lookup or nested expansion is
performed. Unresolved entries remain visible and are excluded from collision
pairing. Includes, conditions and other assignments produce coverage; literal
appends under conditions can still be indexed as candidates. No effective branch,
assignment result, source availability or payload right is inferred.

## Download and fictional walkthrough

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-copy-map-inspector-v0.1.0),
including its ZIP, checksums, usage guide, public validation JSON and build
manifest. Verify downloaded hashes before extracting to a new owned directory.
The ZIP has 29 reviewed source files plus their manifest, 30 members; Python,
actual configs/payloads, generated reports and raw validation logs are excluded.
No pip package, administrator permission, Make, Android tool or device is needed.
Keep the module intact, including `text_support.py`.

The [executable guide](USAGE.md) creates fictional Make/roots JSON, checks
declarations, unresolved entries and candidate conflicts, compares privacy modes,
independently hashes inputs/reports and exercises controlled refusals. Use an
existing absolute private work directory outside the source folder. Every
generated fixture/report directory must be new.

From this module folder, after setting your existing private directory:

PowerShell 5.1 or newer:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/copy-map-demo"
python -E -s -B copy_map_inspector.py --file "$privateWork/copy-map-demo/clean.mk" --output "$privateWork/copy-map-clean-report"
python -E -s -B copy_map_inspector.py --file "$privateWork/copy-map-demo/review.mk" --output "$privateWork/copy-map-review-report" --include-details
python -E -s -B copy_map_inspector.py --file "$privateWork/copy-map-demo/roots.mk" --roots "$privateWork/copy-map-demo/roots.json" --output "$privateWork/copy-map-roots-report"
```

POSIX shell, using `python3` if that is your selected Python command:

```sh
python3 -E -s -B examples/generate.py --output "$privateWork/copy-map-demo"
python3 -E -s -B copy_map_inspector.py --file "$privateWork/copy-map-demo/clean.mk" --output "$privateWork/copy-map-clean-report"
python3 -E -s -B copy_map_inspector.py --file "$privateWork/copy-map-demo/review.mk" --output "$privateWork/copy-map-review-report" --include-details
python3 -E -s -B copy_map_inspector.py --file "$privateWork/copy-map-demo/roots.mk" --roots "$privateWork/copy-map-demo/roots.json" --output "$privateWork/copy-map-roots-report"
```

The clean example exits 0 with two distinct resolved declarations from one joined
append. Review intentionally exits 1: five entries include unresolved paths and
three conflict pairs, plus an uninspected include. The explicit-roots example
exits 0 with one substituted entry. Without supplied roots it remains unresolved,
even if the same variable names are set in the environment. Read local static
`report.html` or machine-readable `report.json`.

## Literal scope and interpretation

```text
python -E -s -B copy_map_inspector.py --file ABSOLUTE_MAKE_TEXT --roots OPTIONAL_ABSOLUTE_ROOTS_JSON --output NEW_ABSOLUTE_DIRECTORY
```

Repeat `--file` for selected Make files; omit `--roots` when no substitutions are
intended. Supported logical lines are literal appends, with single terminal-
backslash joining and inline `#` comments. Interrupted/dangling continuations,
quoting/escaping and general Make expressions require review. No Make command,
include or conditional is evaluated. Other assignments do not hide later
supported literal appends.

Words are `source:destination[:owner]`. Paths are bounded portable relative text
using forward slashes; payload paths are never opened, copied, scanned or checked
for existence. Owner syntax is bounded, but ownership/licensing semantics are
not assessed. A whole leading `$(UPPERCASE_NAME)` may be replaced with one supplied
literal root, optionally followed by a suffix. Embedded/nested variables and
functions are not recursively expanded. Root values must themselves be supported
literal relative paths. See the unchanged [format contract](docs/FORMAT.md).

Only fully resolved pairs are compared. Exact source/destination/owner repetition
is `DUPLICATE_DECLARED_COPY`; a different source or owner at the same destination
is `DECLARED_DESTINATION_CONFLICT`. NFC normalization followed by Unicode casefold
finds portability candidates, and a slash-boundary prefix finds file/parent
candidates. These text comparisons do not prove a collision on any actual
filesystem or evaluated build. Conflict pairs and deduplicated finding locations
can have different counts. Empty/comment-only or empty-append input can exit 0;
that proves neither build completeness nor source availability.

## Reports, privacy and exits

Completed runs create exactly `report.json`, escaped static `report.html` and
`MANIFEST.json`, whose SHA-256/byte lengths cover both report payloads. Make
inputs have opaque IDs, sizes and hashes. A supplied roots file has its own
`roots_input` hash/size record. Unsigned hashes/manifests prove consistency, not
authenticity, payload rights or complete build results. HTML uses no scripts or
external resources; stdout uses fixed status/count/error fields.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No finding/coverage issue in selected supported declarations; scope can be empty. |
| 1 | `REVIEW_REQUIRED` | Candidate conflicts or unsupported/unresolved selected scope needs review. |
| 2 | `INCOMPLETE` | Arguments, input/path/schema, bounds, changed snapshots or I/O prevented completion. |

Defaults omit declared/resolved source/destination/owner values and local input
filenames. `--include-details` adds those selected fields, including unresolved
declared text and null unresolved paths. Opaque IDs, hashes, line positions,
root/owner counts and conflict structure remain identifying: omission is not
anonymization. Keep real Make/roots files and identifying reports private. See
[private workspace guidance](docs/PRIVATE-WORKSPACE.md).

## Input roles, bounds and failure limits

Use stable regular local files with absolute paths and owned output parents.
Links/reparse routes, traversal, UNC/device paths, Windows alternate streams,
non-UTF-8 and unsupported controls are refused. UTF-8 BOM, LF and CRLF are
supported for Make text. The report parent must exist and the output must be new.
A write error can leave a partial new directory; preserve/review it and select
another new destination after fixing the cause.

The `--file` Make-input set has at most 32 files, 1 MiB each, 4 MiB aggregate and
duplicate same-file/hardlink refusal within that set. Make text has at most
20,000 split physical lines including the final empty line, 8,192 characters per
physical/joined logical line, 4,000 entries/conflicts per bounded collection and
8 MiB per JSON/HTML output. Dense conflict pairs can hit the bound and fail
instead of producing a truncated pass.

The optional `--roots` file is snapshotted separately: at most 64 KiB, exact
schema-version-1 object, at most sixteen roots, JSON depth eight, 1,000 nodes,
256-character keys and 1,024-character strings. Duplicate keys, floating numbers,
unsupported controls and invalid root names/values fail. It is outside the Make
set's count/aggregate/duplicate checks; no cross-role alias refusal is claimed.

Inputs are opened read-only and earlier reports are not overwritten. Ordinary
snapshot/path checks are not an OS sandbox or atomic snapshot against a hostile
concurrent writer. Use trusted files and parents. No recursive scan, network,
shell/subprocess, privileged operation, Make evaluation or payload access is
implemented in the inspector.

## Qualification and feedback

The [qualification contract](docs/QUALIFICATION.md) requires exact pinned CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows/Ubuntu, preserving all 35 original
methods and adding thirty copied-runtime methods. Eight lanes select 520 methods;
accepted passes and exact native skips are separate in release validation.
Fresh application environments have no pip and zero installed distributions.
The unchanged [historical validation](docs/VALIDATION.md) remains a distinct earlier record.

From this module folder:

```text
python -E -s -B source_check.py
python -E -s -B -W error -m unittest discover -s tests -v
```

See [provenance](docs/PROVENANCE.md), [contributing](CONTRIBUTING.md) and
[security](SECURITY.md). Minimal fictional reproductions and usability ideas are
welcome through the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Do not submit actual vendor configs, firmware/payloads, credentials, customer
data, identifiers or unredacted reports. Inputs retain their owners' rights;
inspection grants no permission to redistribute them.
