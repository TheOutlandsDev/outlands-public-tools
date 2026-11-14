# Android Property Configuration Diff

Compare supported saved Android `.prop` declarations by literal key/value.
Review added, removed and changed values while holding duplicate identities
without an arbitrary winner. Python 3.12 or newer, standard library only,
original [MIT source](LICENSE).

The tool never follows property imports, changes device properties, merges
effective state or evaluates precedence, permissions or runtime compatibility.
Only explicitly selected saved text is read. Unknown rows/imports limit absence
claims: unmatched keys are held when their opposite side has unidentified rows.

## Download and fictional walkthrough

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-property-diff-v0.1.0),
including source ZIP, checksums, usage guide, public validation JSON and build
manifest. Verify hashes before extracting to a new owned directory. The ZIP
contains 30 reviewed source files plus their manifest, 31 members; Python,
actual snapshots, binaries, generated reports and raw logs are excluded. No pip
package, administrator rights, Android SDK or device is required. Keep the
module intact, including `declaration_diff.py` and `inspection_support.py`.

The [executable guide](USAGE.md) generates fictional before/after files, compares
multi-file sets, checks literal/duplicate/uncertainty behavior, independently
verifies input/report hashes, compares privacy modes and exercises refusals.
Choose an existing absolute private directory outside source. Every fixture/report
destination must be fresh. Never deploy these invented property snapshots.

From this module folder, after setting your existing private work directory:

PowerShell 5.1 or newer:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/property-demo"
python -E -s -B property_diff.py --before "$privateWork/property-demo/before.prop" --after "$privateWork/property-demo/same.prop" --output "$privateWork/property-same-report"
python -E -s -B property_diff.py --before "$privateWork/property-demo/before.prop" --after "$privateWork/property-demo/changed.prop" --output "$privateWork/property-changed-report" --include-details
python -E -s -B property_diff.py --before "$privateWork/property-demo/before.prop" --after "$privateWork/property-demo/review.prop" --output "$privateWork/property-review-report"
```

POSIX shell, using `python3` if that is your selected Python command:

```sh
python3 -E -s -B examples/generate.py --output "$privateWork/property-demo"
python3 -E -s -B property_diff.py --before "$privateWork/property-demo/before.prop" --after "$privateWork/property-demo/same.prop" --output "$privateWork/property-same-report"
python3 -E -s -B property_diff.py --before "$privateWork/property-demo/before.prop" --after "$privateWork/property-demo/changed.prop" --output "$privateWork/property-changed-report" --include-details
python3 -E -s -B property_diff.py --before "$privateWork/property-demo/before.prop" --after "$privateWork/property-demo/review.prop" --output "$privateWork/property-review-report"
```

Same exits 0 despite comments, ASCII whitespace and declaration-order changes.
Changed intentionally exits 1 for one changed value and one added key. Review
exits 1 for held duplicate declarations and an unfollowed import. Repeat
`--before`/`--after` for selected sets, at most 32 files total. Read local static
HTML/JSON; no device property service is contacted.

## Literal grammar and conservative comparison

```text
python -E -s -B property_diff.py --before ABSOLUTE_BEFORE --after ABSOLUTE_AFTER --output NEW_ABSOLUTE_DIRECTORY
```

Support is limited to blank/full-line `#` comments and literal `key=value` lines.
Keys are 1–128 ASCII letters/digits/underscore/dot/hyphen, case-sensitive.
Split only at the first equals sign and trim surrounding ASCII spaces/tabs.
Empty values are valid declarations, distinct from absent keys. Inline `#`,
additional equals, quotes, backslashes and dollar expressions stay literal;
values are not unquoted/expanded/decoded and lines are not continued. Nonbreaking
space is not ASCII trim. See the exact [format contract](docs/FORMAT.md).

Index declarations across all selected files on each side. Unique literal keys
match and compare trimmed values exactly. Comment/order changes alone do not
change unique values. Key renames become removal/addition only where absence
can be assessed within the selected parsed scope. Duplicate keys on either side
or across files stay held with all record IDs, even for identical values; no
first/last winner or arbitrary pairing is chosen.

Unknown lines/keys/imports create explicit coverage and unidentified-row locations.
Import targets are never opened. An unmatched key is held if the opposite side
contains any unidentified row/import, avoiding unsupported added/removed claims.
Unique supported matched changes remain visible with unrelated coverage. A
complete comparison therefore can contain both supported changes and held keys.
Empty/comment snapshots can exit 0 for limited empty scope, not completeness.

No `ro.`/`ctl.`/`persist.` runtime behavior, Android property validation/service,
reserved-key permissions, partition/source/import precedence, effective overrides,
actual device state or runtime compatibility is evaluated. Values and import
targets are text and are never executed or applied.

## Reports, privacy and exits

Completed runs create exactly `report.json`, escaped static `report.html` and
`MANIFEST.json`, hashing/length-checking both report payloads. Each selected
before/after file has a separate exact-byte input hash/size record. Unsigned
hashes prove consistency, not authorship, ownership, completeness or runtime
correctness. HTML has no scripts/external resources. Stdout has fixed codes/counts.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No supported finding/coverage issue; scope may be empty. |
| 1 | `REVIEW_REQUIRED` | Changes, duplicate ambiguity or uninspected coverage needs review. |
| 2 | `INCOMPLETE` | Arguments, input/path/encoding, budgets or I/O prevented completion. |

Defaults omit literal keys/values and local filenames, retaining opaque record
IDs, sides/sources/line positions, supported flags, changed-field labels, counts,
hashes and hold/coverage reasons. `--include-details` adds declared identities
and supported `fields.value`. Raw lines/import targets/local paths remain omitted.
IDs are report-local and depend on input order, not persistent identities.
Omission is not anonymization: hashes/structure and details can identify inputs.
Keep actual snapshots/reports private and review details before sharing. Read
[private workspace guidance](docs/PRIVATE-WORKSPACE.md).

## Inputs, budgets and failure limits

Select distinct stable regular local files with absolute paths. Duplicate/hardlink
identities across both sides, links/reparse routes, traversal, UNC/device paths
and Windows alternate streams are refused. Inputs are read-only and not replaced.
Use an existing owned output parent and new report directory. Failed writes may
leave a partial new folder: preserve/review it, fix the cause and choose another
new output. Earlier reports are not overwritten.

Budgets are 32 files total, 1 MiB each, 4 MiB aggregate, 20,000 split physical
lines including final empty line, 8,192 characters/line, 4,000 rows per bounded
collection and 8 MiB each for JSON/HTML. Strict UTF-8 supports optional BOM and
LF/CRLF; controls, bare CR, NUL and invalid encoding are refused. Bounds fail
incomplete rather than silently truncate. There is no XML/parser dependency
or event-JSON input format in this tool.

Stable-input checks and cooperative budgets are not an OS sandbox, atomic
snapshot against hostile mutation, hard I/O deadline or durable-output guarantee.
No recursive scan, subprocess/shell, network, import following, property change,
ADB or device action occurs in the inspector. Tests/guide launch only this
Python code on disposable authored text.

## Qualification and feedback

The [qualification contract](docs/QUALIFICATION.md) requires pinned CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows/Ubuntu, preserving 38 original
methods plus thirty copied-runtime methods. Eight lanes select 544 methods;
actual passes and finite native skips stay separate in release validation.
Fresh environments have no pip and zero installed distributions. Runtime,
generator, originals and four historical docs remain unchanged; the shared
comparison helper is included locally for standalone use. The unchanged
[historical validation](docs/VALIDATION.md) remains a separate earlier record.

From this module folder:

```text
python -E -s -B source_check.py
python -E -s -B -W error -m unittest discover -s tests -v
```

See [provenance](docs/PROVENANCE.md), [contributing](CONTRIBUTING.md) and
[security](SECURITY.md). Minimal fictional bug/suggestion reproductions are
welcome via the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Do not attach real configs, credentials, customer data or unredacted reports.
Inspected inputs retain their owners' rights/licenses.
