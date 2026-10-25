# OUTLANDS | Source Inventory

A small standard-library utility that writes a CSV of relative filenames, sizes, modification times and SHA-256 hashes for an explicitly chosen folder. A JSON summary records counts, exclusions and report hashes. Add `--tree` for a readable, quoted UTF-8 folder tree. File contents are read for hashing but are not copied into the reports.

Use a narrow, trusted folder whose contents and parent directories will stay unchanged during the scan. Keep the output parent trusted and unchanged too. This tool is not an atomic filesystem snapshot, a sandbox for hostile concurrent writers, a credential detector, an anonymization tool or a full-system audit.

## Use

Use Python 3.12 or 3.13. No third-party runtime dependency or installation is needed. The original Linux reference run used Python 3.12.7, followed by a bounded three-file Windows walkthrough. The folder-tree extension adds generated Windows/Linux fixtures, with platform outcomes recorded separately in [validation](docs/VALIDATION.md). See the earlier [walkthrough record](../../docs/V0.1.0-WALKTHROUGH.md).

Create an absolute `$privateWork` with the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md). Inside that external workspace, create a fictional `example-input` folder and a separate existing `example-reports` folder, then run:

```text
python source_inventory.py --root "$privateWork/example-input" --output-dir "$privateWork/example-reports" --label demo
```

Both folders must already exist, their paths must not contain symlink/reparse components, and the output folder must be outside the input tree. There is no implicit project root. The filesystem root is rejected. Labels use one to 48 lowercase letters/digits, hyphens or underscores and must start with a letter or digit.

Each successful run creates a fresh timestamp/label/random-suffix directory containing `files.csv` and `summary.json`. Existing run directories and report files are never overwritten or appended. New directories request mode 0700 and report files request mode 0600; effective permission semantics depend on the operating system. A failed output write can leave a new partial run directory; an error result does not certify its reports. Ordinary CLI output gives the run directory name without absolute input/output paths.

Exit status 0 means `COMPLETE_WITH_EXCLUSIONS` for the selected regular-file scope. Exit status 2 means `INCOMPLETE` and a fixed error code; an unreadable directory or file does not silently become a successful complete inventory. This result does not certify every entry below the root.

## Folder tree export

Use the same explicitly selected input and external report parent:

```text
python source_inventory.py --root "$privateWork/example-input" --output-dir "$privateWork/example-reports" --label tree-demo --tree
python source_inventory.py --root "$privateWork/example-input" --output-dir "$privateWork/example-reports" --label limited-tree --tree --tree-depth 2 --exclude-dir scratch --exclude-dir generated
```

`--tree` adds `tree.txt` to the fresh report directory. The default CSV and JSON
outputs remain available. Without `--tree`, the program still writes exactly
the original two reports. `--tree-depth` requires `--tree` and accepts 1–64
(default 16). Repeat `--exclude-dir` up to 64 times to add case-insensitive
directory **basenames** to the default exclusions; it does not remove defaults.
Additional exclusions also work without tree export.

The tree uses the **same collection and hashing pass** as the inventory. It
includes selected regular files and observed, nonexcluded directories, including
empty directories. Excluded files/directories, links and unsupported entries are
not rendered; their existing skip counts remain in `summary.json`. The root is
shown as `.` without its absolute path or real root name. Names are quoted and
control/bidirectional formatting characters are escaped to avoid forged lines
or terminal escapes. Ordinary Unicode names remain readable.

Directories appear before files, with deterministic case-folded/exact ordering.
Display depth limits do not reduce hashing: deeper selected files still appear
in `files.csv`. A visible omission marker and `tree.hidden_by_depth`/
`tree.display_complete` record the incomplete display. The tree summary also
records entry/directory counts, display depth and SHA-256 of exact UTF-8 bytes.
The tree is bounded to 1 MiB; exceeding this bound fails before any report is
created. Errors never silently produce a certified complete tree.

These are observed names, not a frozen filesystem snapshot. A directory can
change after observation. Filename metadata can identify private work even
without absolute paths or copied file contents. Keep real exports private.
Try the [fictional example generator](examples/README.md) before real inputs.

## Bounds and exclusions

Defaults are 1,000 selected files, 8 MiB per file, 64 MiB total selected bytes and 10,000 visited directory entries. You can lower the byte/file bounds:

```text
python source_inventory.py --root "$privateWork/example-input" --output-dir "$privateWork/example-reports" --label limited --max-files 100 --max-file-bytes 1048576 --max-total-bytes 8388608
```

Hard ceilings are 10,000 files, 64 MiB per file and 256 MiB total. The entry ceiling is fixed. Metadata is checked before hashing; captured reads are also bounded and checked against observed size/identity/timestamps. Detected growth, replacement or metadata change fails the run. These checks do not freeze the whole directory tree or detect every possible change.

Default exclusions cover common version-control, credential-store, dependency, cache/build, data, model, backup, log and prior-inventory directories, plus environment-like filenames, common key/database/log/archive suffixes and selected credential filenames. Exact directory/suffix lists and skip counts are in the summary. This is a conservative convenience filter, not a complete sensitive-file policy. Ordinary configuration, filenames or content outside those patterns can still contain private information. Choose and review the input scope yourself.

File and directory symlinks/reparse points are skipped rather than followed; unsupported nonregular entries are skipped and counted. Open descriptors are checked to be regular files. Where available, no-follow and nonblocking open flags reduce leaf-link/FIFO risks. Parent-directory operations still have time-of-check/time-of-use windows. Trusted, quiescent input and output parents are required; hostile concurrent replacement is outside the supported boundary.

## Reports and spreadsheet handling

CSV rows are sorted by relative path using a case-folded key and an exact secondary key. Repeated CSV bytes are deterministic for unchanged selected files and timestamps; run names and summary timestamps vary.

CSV quoting alone does not prevent spreadsheet formula evaluation. Potential formula-prefix, leading-tab/newline and apostrophe path cells receive an extra leading apostrophe, and `path_escaped` is `true`. To recover the exact relative path, remove one leading apostrophe only when that flag is true. Other paths have `path_escaped=false`. Unicode and embedded newlines use normal CSV quoting. Treat the CSV as data even with these protections; other downstream transformations can change its safety.

Reports retain relative filenames, top-level names, hashes, sizes and modification times. Those details can reveal project identity, private names or guessed content even though absolute root paths and file bodies are omitted. Keep real reports private, outside source/repository trees, and review them before sharing. No report is anonymous by default.

## Verification and provenance

The earlier edition passed **18 synthetic unittest methods, zero failures/errors/skips**, under isolated Python 3.12.7 on Linux. Those methods remain, with platform-aware fixtures for Windows filesystem semantics. The extension adds tree coverage, depth/exclusion/byte bounds, escaped names and a Windows path/fd metadata regression. See the [current validation record](docs/VALIDATION.md) for exact counts, skips and limits. Tests use generated temporary inputs; no original program or real project tree is executed.

Run the staged tests against temporary fictional files only:

```text
python -m unittest discover -s tests -v
```

This is an export-only adaptation of a retained personal inventory helper. The owner reports personal creation with AI assistance. The adaptation and tests were also AI-assisted. No per-file notice was removed from the retained helper. This selected public source snapshot makes no claim of sole authorship or novel invention. Selected original material is MIT licensed; see [LICENSING.md](../../LICENSING.md). Preserve any required upstream notices if future material is added. Real inventory reports remain private and require a separate sharing review.

Read [contributing](CONTRIBUTING.md) to propose changes, [suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=source_inventory_suggestion.yml), or [report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=source_inventory_bug.yml). Share only fictional or appropriately redacted examples.
