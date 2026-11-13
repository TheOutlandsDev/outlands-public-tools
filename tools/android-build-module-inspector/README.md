# Android Build Module Declaration Inspector

Review literal module-name declarations in explicitly selected saved `Android.bp`
and `Android.mk` text. The inspector reports supported declarations, repeated
names, held identities and incomplete scope. An optional wanted-name list checks
what was observed in that selected supported text. Python 3.12 or newer, standard
library only, original [MIT source](LICENSE).

Repeated names are observations, not confirmed build collisions. Namespaces,
host/device variants and other context can legitimately reuse names. An unseen
name does not prove absence from an effective build. The inspector never walks
a source tree, runs Make/Soong, follows includes, evaluates expressions, builds
Android or accesses devices.

## Download and fictional walkthrough

Download the source ZIP, checksums, [usage guide](USAGE.md), validation JSON and
build manifest from the [0.1.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-build-module-inspector-v0.1.0).
Verify the downloaded hashes before extracting into a new owned directory.
The ZIP contains 29 reviewed source files and their manifest, 30 members. Python,
build trees, Android tools, generated reports and raw validation logs are excluded.
No pip package, AOSP checkout, SDK, administrator permission or device is needed.

The [executable guide](USAGE.md) creates fictional saved BP/Make/wanted text,
checks clean and review results, independently hashes inputs/reports, and verifies
controlled refusals. Use an existing absolute private work directory outside the
source folder. Every generated output directory must be new.

For a short trial, run from this module folder after setting `privateWork` to that
existing directory. Use your selected Python 3.12–3.15 interpreter.

PowerShell 5.1 or newer:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/build-demo"
python -E -s -B build_module_inspector.py --bp "$privateWork/build-demo/clean.bp" --mk "$privateWork/build-demo/clean.mk" --wanted "$privateWork/build-demo/wanted.txt" --output "$privateWork/build-clean-report"
python -E -s -B build_module_inspector.py --bp "$privateWork/build-demo/review.bp" --wanted "$privateWork/build-demo/wanted-unseen.txt" --output "$privateWork/build-review-report" --include-details
```

POSIX shell:

```sh
python3 -E -s -B examples/generate.py --output "$privateWork/build-demo"
python3 -E -s -B build_module_inspector.py --bp "$privateWork/build-demo/clean.bp" --mk "$privateWork/build-demo/clean.mk" --wanted "$privateWork/build-demo/wanted.txt" --output "$privateWork/build-clean-report"
python3 -E -s -B build_module_inspector.py --bp "$privateWork/build-demo/review.bp" --wanted "$privateWork/build-demo/wanted-unseen.txt" --output "$privateWork/build-review-report" --include-details
```

The clean case exits 0 with three declarations and three requests observed once.
The review case intentionally exits 1: two declarations repeat one literal name,
a third has unresolved identity, and the unseen request is held for incomplete
scope. Open static `report.html` locally or read `report.json`.

## Command and output

```text
python -E -s -B build_module_inspector.py --bp ABSOLUTE_BP --mk ABSOLUTE_MK --wanted ABSOLUTE_NAME_LIST --output NEW_ABSOLUTE_DIRECTORY
```

Supply at least one `--bp` or `--mk`; either can repeat. The explicit option selects
the parser, regardless of filename. `--wanted` is optional. Names match exactly,
case-sensitively; suffixes, aliases and directory names are never guessed.

Completed runs write exactly `report.json`, escaped static `report.html` and
`MANIFEST.json`. The manifest records SHA-256 and lengths of both report payloads.
Input-source hashes describe selected text bytes, not a build, binary or device.
Unsigned manifests are consistency evidence, not authenticity proof. HTML uses no
scripts or external resources. Stdout contains fixed status/count fields; errors
use fixed codes rather than source values, filenames or upstream exception text.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No implemented finding or coverage issue in the selected supported text. |
| 1 | `REVIEW_REQUIRED` | Repeated declarations, unmatched requests, held identity or incomplete scope needs review. |
| 2 | `INCOMPLETE` | Arguments, input/path/encoding, bounds, changed snapshots or I/O prevented completion. |

Existing outputs are refused and the output parent must already exist. A failed
write can leave a new partial directory; correct the cause and select a new name.
Inputs and earlier reports are never edited or silently replaced.

## Supported interpretation

BP supports top-level `module_type { ... }` blocks with a direct literal
`name: "value"`. A bounded tokenizer handles comments, strings and balanced nested
braces/lists. Nested `name` properties are not module names. Other property values
are discarded without validating their full grammar, types or build meaning.
Duplicate direct properties hold a declaration. Missing, invalid or dynamic names
remain unresolved. Unsupported top-level text stops the rest of that file with
coverage; namespace/package declarations and dynamic module kinds are explicitly
unevaluated. The parser does not skip ahead and guess later declarations.

Make supports one literal `LOCAL_MODULE := name` or `LOCAL_MODULE = name` between
recognized `include $(CLEAR_VARS)` and `include $(BUILD_...)` text markers. Those
markers are never followed. Other recognized `LOCAL_*` assignments are counted
and discarded. Duplicate, dynamic, continued or incomplete module assignments
are held. Unknown includes remain unfollowed; directives, recipes and unsupported
statements stop the remaining text. No winning assignment or branch is selected.

Wanted states distinguish `observed_once`, `observed_multiple`, `observed_held`,
`held_incomplete_scope` and `not_observed_selected_supported_scope`. The last
state applies only when selected build-parser scope has no unresolved identity
or scope; duplicate wanted rows are separate coverage. Neither an unseen name
nor a supported literal declaration establishes effective build availability.
Read the unchanged [precise grammar/schema](docs/FORMAT.md).

## Inputs and privacy

Use explicit stable regular local files with absolute paths and owned output
parents. Links/reparse routes, UNC/device paths, Windows alternate streams,
parent traversal, special files and same-file/hardlink aliases are refused.
Snapshot/path checks address ordinary changes; they are not an OS sandbox or an
atomic snapshot against a hostile concurrent filesystem owner. No network or
subprocess operation is implemented by the inspector.

Limits are 32 total inputs including wanted text, 1 MiB each, 4 MiB aggregate,
20,000 physical lines including the final empty line, and 8,192 characters per
line. UTF-8 with optional BOM and LF/CRLF is accepted; bare CR, NUL and unsupported
controls are refused. BP allows 40,000 tokens, nested value depth 32, strings of
1,024 characters and identifiers of 256. Report collections have at most 4,000
entries; JSON/HTML payloads are at most 8 MiB each. A bound produces an incomplete
run rather than a silently truncated pass.

Defaults omit literal names/kinds, source paths and discarded source text.
`--include-details` adds supported names/kinds and wanted names; it never adds
discarded values, raw unsupported expressions or filenames. Source IDs, hashes,
line positions, counts and structure remain. Omission is not anonymization:
these observations can identify material. Keep real build files and identifying
reports private and review outputs before sharing.

## Qualification and feedback

The [qualification contract](docs/QUALIFICATION.md) requires exact pinned CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows and Ubuntu, preserving all 56
original tests and adding 30 copied-runtime checks. Eight lanes select 688 methods
in total; accepted passes and exact native skips are reported separately in the
release validation asset. Fresh environments have no pip and zero installed
distributions. The unchanged [historical validation](docs/VALIDATION.md) remains
a distinct earlier record.

From this module folder, the source gate and complete suite remain available:

```text
python -E -s -B source_check.py
python -E -s -B -W error -m unittest discover -s tests -v
```

See [provenance](docs/PROVENANCE.md), [contributing](CONTRIBUTING.md) and
[security](SECURITY.md). Suggestions and minimal fictional reproductions are
welcome through the [issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Do not attach proprietary build trees, credentials, vendor declarations or
unredacted identifying reports.
