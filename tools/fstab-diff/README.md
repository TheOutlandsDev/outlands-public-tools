# Fstab Configuration Diff

Compare supported saved Linux or Android fstab text by exact decoded mount
target. Review field changes and relative order among unique common targets,
while duplicate targets remain ambiguous without an arbitrary match. Python
3.12 or newer, standard library only, original [MIT source](LICENSE).

The tool never mounts, probes filesystems, edits configs or connects devices.
Options remain ordered text rather than evaluated flags. Report observations
describe selected parsed records, not bootability, complete device state or
runtime-equivalent mount behavior. Unsupported rows remain visible coverage.

## Download and fictional walkthrough

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/fstab-diff-v0.1.0),
including its ZIP, checksums, usage guide, public validation JSON and build
manifest. Verify downloaded hashes before extracting to a new owned directory.
The ZIP contains 29 reviewed source files plus their manifest, 30 members;
Python, actual device configs, generated reports and raw logs are excluded.
No pip package, administrator permission, mount utility or device is required.
Keep the module intact, including `text_support.py`.

The [executable guide](USAGE.md) creates fictional before/after inputs, compares
both formats, checks duplicate/order/escape/numeric behavior, independently
verifies input/report hashes, compares privacy modes and exercises refusals.
Choose an existing absolute private work directory outside the source folder.
Every generated fixture/report directory must be new.

From this module folder, after setting your existing private directory:

PowerShell 5.1 or newer:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/fstab-demo"
python -E -s -B fstab_diff.py --before "$privateWork/fstab-demo/linux-before.fstab" --after "$privateWork/fstab-demo/linux-same.fstab" --format linux --output "$privateWork/fstab-linux-same-report"
python -E -s -B fstab_diff.py --before "$privateWork/fstab-demo/linux-before.fstab" --after "$privateWork/fstab-demo/linux-changed.fstab" --format linux --output "$privateWork/fstab-linux-change-report" --include-details
python -E -s -B fstab_diff.py --before "$privateWork/fstab-demo/android-before.fstab" --after "$privateWork/fstab-demo/android-changed.fstab" --format android --output "$privateWork/fstab-android-report"
```

POSIX shell, using `python3` if that is your selected Python command:

```sh
python3 -E -s -B examples/generate.py --output "$privateWork/fstab-demo"
python3 -E -s -B fstab_diff.py --before "$privateWork/fstab-demo/linux-before.fstab" --after "$privateWork/fstab-demo/linux-same.fstab" --format linux --output "$privateWork/fstab-linux-same-report"
python3 -E -s -B fstab_diff.py --before "$privateWork/fstab-demo/linux-before.fstab" --after "$privateWork/fstab-demo/linux-changed.fstab" --format linux --output "$privateWork/fstab-linux-change-report" --include-details
python3 -E -s -B fstab_diff.py --before "$privateWork/fstab-demo/android-before.fstab" --after "$privateWork/fstab-demo/android-changed.fstab" --format android --output "$privateWork/fstab-android-report"
```

The unchanged Linux example exits 0 despite comment differences. Linux changed
intentionally exits 1 for an option change, one added target and changed relative
order of the two unique common targets. Android changed exits 1 for its fifth
field, `fs_mgr_flags`. Read static local `report.html` or `report.json`.

## Explicit format and supported comparisons

```text
python -E -s -B fstab_diff.py --before ABSOLUTE_BEFORE --after ABSOLUTE_AFTER --format linux --output NEW_ABSOLUTE_DIRECTORY
```

Choose `--format linux` or `--format android`; formats are not guessed. Linux
accepts four through six fields, defaulting omitted dump/pass numbers to zero.
Those numbers are decimal 0–65535 with at most five digits; leading zeroes do
not change the value. Android requires exactly five fields, with the fifth
treated as `fs_mgr_flags`. No flag semantics, overrides or runtime equivalence
are evaluated. Comma order and duplicates remain text; empty/duplicate option
tokens produce findings even in identical inputs.

Fields split on ASCII space/tab before one-pass decoding of supported octal
space, tab and backslash escapes. A separate `#` field starts a trailing comment;
embedded `#` stays data. Unsupported escapes/field counts/numbers produce
coverage rather than silent equality. Quotes have no shell-quoting semantics.
See the unchanged [precise format contract](docs/FORMAT.md).

Unique decoded targets match exactly. A target repeated on either side forms
an ambiguous group: its rows are excluded from added/removed/change pairing and
order comparison. No first/last match is chosen. Changing a target becomes
removal/addition. Relative order compares only unique common parsed targets;
adding a different target alone is not reordering. Unsupported rows can coexist
with supported-record observations, so reported additions/removals do not prove
absence from a complete configuration. Empty/comment-only inputs can exit 0
without establishing completeness, valid mounts or a successful boot.

## Reports, privacy and exits

Completed runs create exactly `report.json`, escaped static `report.html` and
`MANIFEST.json`, with SHA-256/byte lengths covering both report payloads. Before
and after inputs have separate exact-byte hash/size records. Unsigned manifests
prove consistency, not origin, authenticity, runtime validity or redistribution
permission. HTML has no scripts or external resources. Stdout uses fixed
status/count/error fields rather than local paths or upstream exceptions.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No finding/coverage issue in selected supported records; scope may be empty. |
| 1 | `REVIEW_REQUIRED` | Value/order changes, ambiguity, option findings or incomplete coverage needs review. |
| 2 | `INCOMPLETE` | Arguments, input/path/encoding, bounds, changed snapshots or I/O prevented completion. |

Defaults omit decoded field values and local filenames, retaining opaque target
IDs, sides/line positions, changed-field labels, hashes, counts and findings.
`--include-details` adds decoded record fields, before/after values and ambiguous
target names. IDs depend on first-seen order and are not stable identifiers
across edits. Omission is not anonymization: hashes and structure can identify
inputs. Keep actual configs and identifying reports private, and review details
before sharing. See [private workspace guidance](docs/PRIVATE-WORKSPACE.md).

## Inputs, bounds and failure limits

Before/after must be distinct stable regular local files with absolute paths;
identical bytes in distinct copies are supported, while same-file/hardlink
aliases are refused. Links/reparse routes, traversal, UNC/device paths, Windows
alternate streams, non-UTF-8 and unsupported controls are refused. UTF-8 BOM,
LF and CRLF are supported. Field paths are text and are never probed or opened.

The CLI accepts exactly two selected files, at most 1 MiB each. Text has at most
20,000 split physical lines including a final empty line, 8,192 characters per
line, 4,000 rows per bounded collection and 8 MiB per JSON/HTML report. Bounds
fail incomplete rather than silently truncate. Use an existing owned report
parent and a new output directory. Inputs and earlier reports are not edited
or overwritten. A write failure can leave a partial new report; preserve/review
it and choose another new destination after fixing the cause.

Snapshot/path checks address ordinary changes, not an OS sandbox or atomic
snapshot against a hostile concurrent writer. Use trusted stable files/parents.
No recursive scan, network, shell/subprocess, privileged operation, mount,
filesystem probe or device access is implemented in the inspector.

## Qualification and feedback

The [qualification contract](docs/QUALIFICATION.md) requires exact pinned CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows/Ubuntu, preserving 33 original
methods and adding thirty copied-runtime methods. Eight lanes select 504 methods;
accepted passes and finite native skips are separate in release validation.
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
Do not submit actual configs/firmware, credentials, customer data, device
identifiers or unredacted reports. Inspected inputs retain their owners' rights.
