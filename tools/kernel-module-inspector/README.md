# Kernel Module List & Dependency Inspector

Review explicitly supplied module dependency and load-list text. It reports
ambiguous declarations, unresolved references and closed cycle witnesses, then
gives a dependency-first order for the supported selected closure. Python 3.12
or newer, standard library only, original [MIT source](LICENSE).

The inspector never opens, decompresses or loads module binaries and never
invokes kmod or accesses devices. Ordering selected declarations is not kernel
ABI verification, load authorization or successful boot/runtime proof. Optional
inventory is caller-supplied text rather than an observed filesystem inventory.

## Download and fictional walkthrough

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/kernel-module-inspector-v0.1.0),
including its source ZIP, checksums, usage guide, public validation JSON and
build manifest. Verify hashes before extracting into a new owned directory.
The ZIP contains 29 reviewed source files plus their manifest, 30 members;
Python, module binaries, real inventories, generated reports and raw logs are
excluded. No pip package, administrator rights, native helper or device is
required. Keep the module intact, including `inspection_support.py`.

The [executable guide](USAGE.md) creates fictional dependency/load/inventory
files, checks graph resolution/order/witnesses and ambiguity, compares privacy
modes, independently verifies input/report hashes and exercises refusals. Use
an existing absolute private work directory outside the source tree, with fresh
fixture/report destinations. Never use these invented files as a deployment plan.

From this module folder, after setting your existing private directory:

PowerShell 5.1 or newer:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/module-demo"
python -E -s -B module_inspector.py --deps "$privateWork/module-demo/clean.dep" --load-list "$privateWork/module-demo/clean.load" --available "$privateWork/module-demo/available.txt" --output "$privateWork/module-clean-report"
python -E -s -B module_inspector.py --deps "$privateWork/module-demo/review.dep" --load-list "$privateWork/module-demo/review.load" --output "$privateWork/module-review-report" --include-details
```

POSIX shell, using `python3` if that is your selected Python command:

```sh
python3 -E -s -B examples/generate.py --output "$privateWork/module-demo"
python3 -E -s -B module_inspector.py --deps "$privateWork/module-demo/clean.dep" --load-list "$privateWork/module-demo/clean.load" --available "$privateWork/module-demo/available.txt" --output "$privateWork/module-clean-report"
python3 -E -s -B module_inspector.py --deps "$privateWork/module-demo/review.dep" --load-list "$privateWork/module-demo/review.load" --output "$privateWork/module-review-report" --include-details
```

Clean exits 0: selected feature has a three-module prerequisite closure. Those
prerequisites need not also appear in the load list. Review intentionally exits
1 for a declared cycle, unresolved dependency, repeated selection and unknown
selected name. Read the static local `report.html` or structured `report.json`.

## Literal metadata and selected graph scope

```text
python -E -s -B module_inspector.py --deps ABSOLUTE_DEPENDENCY_TEXT --load-list ABSOLUTE_SELECTION_TEXT --output NEW_ABSOLUTE_DIRECTORY
```

Dependency rows use the documented `relative/module.ko: relative/other.ko ...`
subset, with one load selection per line. Optional `--available` supplies a
separate text inventory of full relative module paths, not a directory. Missing
membership means only not listed in that supplied file. No declared module path
is opened. Literal `.ko`, `.ko.gz`, `.ko.xz` and `.ko.zst` suffixes are supported
without decompression. Unsupported syntax becomes visible coverage.

Load selections resolve by exact declared path first, then an unambiguous
literal basename or suffix-stripped basename. Duplicate declarations and
ambiguous aliases remain held; no arbitrary candidate wins. Dependency references
require exact paths. Duplicate dependency tokens produce a finding and are
normalized before graph ordering; duplicate load selections do not duplicate
the selected closure. Unknown/ambiguous prerequisites block their consumers and
dependants. Iterative traversal supports deep bounded graphs.

Closed DFS back-edge witnesses identify actual declared cycles; a dependant
blocked by a cycle is not automatically a cycle member. Witnesses do not enumerate
every possible cycle. Kahn ordering includes only unique declarations in the
resolved selected roots' known dependency closure. Unrelated findings still make
the whole report require review. `selected_plan_complete_within_metadata` concerns
only that supported selected closure; it does not establish inventory membership,
ABI compatibility or runtime success. It can be true while status is review.

Empty/comment-only inputs may exit 0 with an empty scope. No builtin modules,
modprobe aliases/config, environment search, dash/underscore equivalence, soft
dependencies, symbol/vermagic/signature checks or recovery availability are
inferred. Human-readable `modules.dep` is not a stable kmod API; this documented
limited grammar does not replace native kmod inspection. See [FORMAT.md](docs/FORMAT.md).

## Reports, privacy and exits

Completed runs create exactly `report.json`, escaped static `report.html` and
`MANIFEST.json`. The unsigned manifest records SHA-256 and byte lengths for both
report payloads. Selected dependency/load/inventory text has separate exact-byte
hash/size records. Hashes establish consistency, not author authenticity,
ownership, actual binary availability or runtime compatibility. HTML contains
no scripts or external resources. Stdout uses fixed statuses/counts/error codes.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No supported finding/coverage issue; scope may be empty. |
| 1 | `REVIEW_REQUIRED` | Ambiguity, graph/inventory findings or incomplete coverage needs review. |
| 2 | `INCOMPLETE` | Arguments, input/path/encoding, bounds, changing files or I/O prevented completion. |

Defaults omit declared names/paths and local input filenames, retaining opaque
IDs, positions, graph structure, resolution codes, counts and hashes. Opt-in
`--include-details` adds accepted declared module/dependency paths and selected
names; unsupported raw rows remain omitted. IDs follow declaration order and
are not persistent identities. Omission is not anonymization: hashes/structure
may identify inputs. Keep actual metadata and identifying reports private;
review details before sharing. See [private workspace guidance](docs/PRIVATE-WORKSPACE.md).

## Inputs, bounds and failure limits

Select two required files and optionally one inventory file. They must be distinct
stable regular local identities using absolute paths. Same-file/hardlink aliases,
links/reparse routes, traversal, UNC/device paths and Windows alternate streams
are refused. Strict UTF-8, optional BOM and LF/CRLF are supported; unsupported
controls/encodings are refused. Input bytes are never edited or executed.

Each selected file is at most 1 MiB; common aggregate/count ceilings are 4 MiB
and 32 files, while this CLI exposes at most three inputs. Text has at most
20,000 split physical lines including a final empty line, 8,192 characters per
line and supported paths at most 512 characters. Graph caps are 2,000 accepted
declarations, 4,000 dependency tokens before normalization and 8,000 IDs across
cycle witnesses. Common collections cap at 4,000 rows; JSON/HTML each at 8 MiB.
Bounds fail incomplete rather than silently truncate.

Use an existing owned parent and a fresh output directory. Existing reports and
inputs are not overwritten. A write failure can leave a partial new folder:
preserve/review it and use another new destination after fixing the cause.
Path/snapshot checks address ordinary changes, not an OS sandbox or atomic
snapshot against hostile concurrent mutation. No recursive scan, network,
shell/subprocess, privileged operation, binary access or module loading occurs
in the inspector. Tests/guide launch only this Python code on fictional files.

## Qualification and feedback

The [qualification contract](docs/QUALIFICATION.md) requires pinned CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows/Ubuntu, preserving 38 original
methods and adding thirty copied-runtime methods. Eight lanes select 544 methods;
actual passes and finite native skips remain separate in release validation.
Fresh application environments have no pip and zero installed distributions.
The unchanged [historical validation](docs/VALIDATION.md) is a separate earlier
record, including sibling-tool statements that do not apply to this runtime.

From this module folder:

```text
python -E -s -B source_check.py
python -E -s -B -W error -m unittest discover -s tests -v
```

See [provenance](docs/PROVENANCE.md), [contributing](CONTRIBUTING.md) and
[security](SECURITY.md). Minimal fictional bug/suggestion reproductions are
welcome via the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Do not attach real inventories/module binaries, device identifiers, credentials,
customer data or unredacted reports. Inspected inputs retain their own rights.
