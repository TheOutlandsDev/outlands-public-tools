# OUTLANDS | Source Inventory

A small standard-library utility that writes a CSV of relative filenames, sizes, modification times and SHA-256 hashes for an explicitly chosen folder. A JSON summary records counts, exclusions and the CSV hash. File contents are read for hashing but are not copied into either report.

Use a narrow, trusted folder whose contents and parent directories will stay unchanged during the scan. Keep the output parent trusted and unchanged too. This tool is not an atomic filesystem snapshot, a sandbox for hostile concurrent writers, a credential detector, an anonymization tool or a full-system audit.

## Use

Use Python 3.12; the recorded fixture run used Python 3.12.7 on Linux. No third-party runtime dependency or installation is needed. Windows behavior has not been tested.

Create a fictional `example-input` folder and a separate existing `example-reports` folder, then run:

```text
python source_inventory.py --root ./example-input --output-dir ./example-reports --label demo
```

Both folders must already exist, their paths must not contain symlink/reparse components, and the output folder must be outside the input tree. There is no implicit project root. The filesystem root is rejected. Labels use one to 48 lowercase letters/digits, hyphens or underscores and must start with a letter or digit.

Each successful run creates a fresh timestamp/label/random-suffix directory containing `files.csv` and `summary.json`. Existing run directories and report files are never overwritten or appended. New directories request mode 0700 and report files request mode 0600; effective permission semantics depend on the operating system. A failed output write can leave a new partial run directory; an error result does not certify its reports. Ordinary CLI output gives the run directory name without absolute input/output paths.

Exit status 0 means `COMPLETE_WITH_EXCLUSIONS` for the selected regular-file scope. Exit status 2 means `INCOMPLETE` and a fixed error code; an unreadable directory or file does not silently become a successful complete inventory. This result does not certify every entry below the root.

## Bounds and exclusions

Defaults are 1,000 selected files, 8 MiB per file, 64 MiB total selected bytes and 10,000 visited directory entries. You can lower the byte/file bounds:

```text
python source_inventory.py --root ./example-input --output-dir ./example-reports --label limited --max-files 100 --max-file-bytes 1048576 --max-total-bytes 8388608
```

Hard ceilings are 10,000 files, 64 MiB per file and 256 MiB total. The entry ceiling is fixed. Metadata is checked before hashing; captured reads are also bounded and checked against observed size/identity/timestamps. Detected growth, replacement or metadata change fails the run. These checks do not freeze the whole directory tree or detect every possible change.

Default exclusions cover common version-control, credential-store, dependency, cache/build, data, model, backup, log and prior-inventory directories, plus environment-like filenames, common key/database/log/archive suffixes and selected credential filenames. Exact directory/suffix lists and skip counts are in the summary. This is a conservative convenience filter, not a complete sensitive-file policy. Ordinary configuration, filenames or content outside those patterns can still contain private information. Choose and review the input scope yourself.

File and directory symlinks/reparse points are skipped rather than followed; unsupported nonregular entries are skipped and counted. Open descriptors are checked to be regular files. Where available, no-follow and nonblocking open flags reduce leaf-link/FIFO risks. Parent-directory operations still have time-of-check/time-of-use windows. Trusted, quiescent input and output parents are required; hostile concurrent replacement is outside the supported boundary.

## Reports and spreadsheet handling

CSV rows are sorted by relative path using a case-folded key and an exact secondary key. Repeated CSV bytes are deterministic for unchanged selected files and timestamps; run names and summary timestamps vary.

CSV quoting alone does not prevent spreadsheet formula evaluation. Potential formula-prefix, leading-tab/newline and apostrophe path cells receive an extra leading apostrophe, and `path_escaped` is `true`. To recover the exact relative path, remove one leading apostrophe only when that flag is true. Other paths have `path_escaped=false`. Unicode and embedded newlines use normal CSV quoting. Treat the CSV as data even with these protections; other downstream transformations can change its safety.

Reports retain relative filenames, top-level names, hashes, sizes and modification times. Those details can reveal project identity, private names or guessed content even though absolute root paths and file bodies are omitted. Keep real reports private, outside source/repository trees, and review them before sharing. No report is anonymous by default.

## Verification and provenance

The staged version passed **18 synthetic unittest tests, zero failures/errors/skips**, under isolated Python 3.12.7 on Linux. Tests cover exact hashes/counts and stable ordering; Unicode/newline/formula filename serialization; conservative exclusions; file/directory links and a FIFO; byte/count/entry limits; traversal/open failures; growth/replacement/change detection; exclusive outputs; and omission of absolute root/output paths from ordinary reports. No original program, real project tree, network, service or Windows runtime was exercised.

Run the staged tests against temporary fictional files only:

```text
python -m unittest discover -s tests -v
```

This is an export-only adaptation of a retained personal inventory helper. The owner reports personal creation with AI assistance. The adaptation and tests were also AI-assisted. No per-file notice was removed from the retained helper. This selected public source snapshot makes no claim of sole authorship or novel invention. Selected original material is MIT licensed; see [LICENSING.md](../../LICENSING.md). Preserve any required upstream notices if future material is added. Real inventory reports remain private and require a separate sharing review.
