# Android Build Module Declaration Inspector

Review literal module-name declarations in **explicitly selected saved
`Android.bp` and `Android.mk` text files**. The inspector shows supported
declarations, repeated names, held/unsupported syntax, and whether a requested
name was observed in the selected supported scope. Python **3.12 or newer**,
standard library only, original [MIT source](LICENSE).

Useful when reviewing a small build-file change or checking selected declarations
against a list of expected names. It does not walk a source tree, build Android,
source Makefiles, resolve variables/includes or determine effective module
availability. Repeated names are review observations: namespaces, host/device
variants and other build context can legitimately reuse names.

## Install and try fictional examples

Clone or download [outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools)
and enter `tools/android-build-module-inspector`. Run `python --version`; use
`python3` if that is your Python 3.12+ command. No pip dependency, AOSP checkout,
Android SDK, administrator permission or device connection is required.

Choose an existing absolute private work directory outside the source checkout.
Every generated output directory must be new. The generator writes invented
build text only, which is never included, compiled or executed.

Windows PowerShell, after setting `$privateWork` to that existing directory:

```powershell
python -B examples/generate.py --output "$privateWork/build-demo"
python -B build_module_inspector.py --bp "$privateWork/build-demo/clean.bp" --mk "$privateWork/build-demo/clean.mk" --wanted "$privateWork/build-demo/wanted.txt" --output "$privateWork/build-clean-report"
python -B build_module_inspector.py --bp "$privateWork/build-demo/review.bp" --wanted "$privateWork/build-demo/wanted-unseen.txt" --output "$privateWork/build-review-report" --include-details
```

Linux shell, after setting `privateWork` to that existing absolute directory:

```sh
python3 -B examples/generate.py --output "$privateWork/build-demo"
python3 -B build_module_inspector.py --bp "$privateWork/build-demo/clean.bp" --mk "$privateWork/build-demo/clean.mk" --wanted "$privateWork/build-demo/wanted.txt" --output "$privateWork/build-clean-report"
python3 -B build_module_inspector.py --bp "$privateWork/build-demo/review.bp" --wanted "$privateWork/build-demo/wanted-unseen.txt" --output "$privateWork/build-review-report" --include-details
```

Expected results:

| Example | Exit | Result |
| --- | --- | --- |
| Clean BP + Make + wanted list | 0 | Three supported declarations, with each requested name observed once. |
| Review BP + wanted list | 1 | Three declaration records: two repeat a literal name and one has an unresolved name expression. The unseen request is held because scope is incomplete. |

Open `report.html` locally, or use `report.json` in your own tooling. A review
exit in the second example is intentional. See [examples](examples/README.md)
and the [precise format](docs/FORMAT.md) for the supported subset and caveats.

## Command and outputs

```text
python -B build_module_inspector.py --bp ABSOLUTE_BP --mk ABSOLUTE_MK --wanted ABSOLUTE_NAME_LIST --output NEW_ABSOLUTE_DIRECTORY
```

Supply at least one `--bp` or `--mk`. Repeat either option to inspect selected
sets. The filename does not select a parser: the explicit option does. `--wanted`
is optional; without it the report only inventories supported declarations and
review observations. Names are matched exactly, case-sensitively; `.so` suffixes,
directory names and aliases are never guessed or removed.

Each completed run writes exactly `report.json`, escaped static `report.html`
and `MANIFEST.json` containing SHA-256 hashes and lengths of those two reports.
The manifest is unsigned consistency evidence, not authenticity proof. HTML has
no scripts or external resources. Stdout prints fixed status/count fields;
errors use fixed codes rather than source values, filenames or exception text.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No implemented finding or coverage issue in selected supported text. |
| 1 | `REVIEW_REQUIRED` | Repeated names, unmatched requests, ambiguity or unsupported scope needs review. |
| 2 | `INCOMPLETE` | Invalid arguments/path/encoding, resource limit, changed snapshot or I/O failure. |

Existing output is refused. Its parent must already exist. A failed write may
leave a new partial report directory; fix the cause and select a new output
name. The inspector never edits an input or silently replaces an earlier report.

## Scope and interpretation

- BP files support top-level `module_type { ... }` blocks and a literal direct
  `name: "value"` property. Comments/strings and nested braces/lists are handled
  by an original bounded tokenizer. A nested `target` property's `name` is not a
  module name. Other property contents are balanced and discarded, without
  asserting their complete syntax, property types or build meaning.
- Duplicate direct properties hold a declaration. Missing, invalid or dynamic
  names stay unresolved. Top-level assignments and unsupported syntax stop the
  remaining file with coverage; the tool does not skip ahead and guess modules.
  Namespace/package declarations and `soong_config_*` kinds produce explicit
  unevaluated-scope coverage.
- Make supports literal `LOCAL_MODULE := name` or `LOCAL_MODULE = name` between
  recognized `include $(CLEAR_VARS)` and `include $(BUILD_...)` markers. Those
  markers are text only and are never followed. Other recognized `LOCAL_*`
  assignments are counted/discarded, not interpreted. Duplicate, dynamic,
  continued, incomplete or unsupported name assignments are held.
- Unknown includes stay unfollowed. Conditional/define/export directives,
  recipes and unrecognized statements stop the remaining Make text with coverage.
  The tool does not determine a winning assignment, branch or build variant.
- A wanted name with no observed declaration is reported as
  `not_observed_selected_supported_scope` only when the selected parser scope has
  no unresolved identities or scope. Otherwise it is `held_incomplete_scope`.
  Neither state proves that a module is absent from an actual build. A supported
  literal declaration also does not prove build inclusion or a functioning module.

Read the [exact grammar/report schema](docs/FORMAT.md) before interpreting a
result. This deliberately limited inspector is not a Soong/Make replacement,
dependency resolver, build validator or Android compatibility test.

## Input handling and privacy

Inputs are explicit stable regular local files with absolute paths. Links,
reparse routes, Windows alternate streams, UNC/device paths, parent traversal,
special files and same-file/hardlink aliases are refused. The shared safeguards
detect ordinary snapshot changes; they are not an OS sandbox or an atomic
snapshot against a malicious concurrent filesystem owner. Use trusted files and
output parents you control. No network, subprocess, build, include following,
system scan or device operation is implemented in the inspector.

Limits: **32 input files total** including wanted text, **1 MiB per file**, **4 MiB
aggregate**, **20,000 physical lines** including final empty lines, and **8,192
characters per line**. Text is UTF-8 with optional BOM and LF/CRLF. Bare CR,
NUL and unsupported controls are refused. BP has 40,000 tokens, maximum nested
value depth 32, string length 1,024 and identifier length 256. Bounded report
collections have at most 4,000 entries. JSON/HTML reports are at most 8 MiB each.
Exceeding a bound is an incomplete run, not a silently truncated pass.

Default reports omit literal module names, module kinds, source paths and
unsupported source text. `--include-details` adds supported module names/kinds
and wanted names, never the discarded payload text or filenames. Source IDs,
hashes, line positions, counts and structure remain. This is **not
anonymization**: those observations can identify source material. Keep real
build files and identifying reports private, and review any output before sharing.

## Tests and suggestions

Run from this module folder:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

Tests use generated text and the actual Python CLI. They cover lexical traps,
nested names, duplicate/dynamic declarations, unsupported scope, wanted-name
holds, limits, private output and exclusive report creation. Shared safeguards
are repeated for standalone downloads. [Validation](docs/VALIDATION.md) separates
passes, platform/environment skips and real-build limitations.

Suggestions, bug reports, parser-format proposals and usability feedback are
welcome through the [issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Include OS, Python version, source commit, expected behavior and a minimal
fictional reproduction. Do not attach vendor build trees, proprietary files,
credentials or unredacted reports. See [CONTRIBUTING.md](CONTRIBUTING.md),
[SECURITY.md](SECURITY.md) and [provenance](docs/PROVENANCE.md).
