# Inventory rule classification

`classify_inventory.py` groups the **already captured rows** of a Source
Inventory run. It reads only that run's `files.csv`, `summary.json` and an
explicit rules file. It does not walk a source directory, reopen any inventoried
file body, collect device data or contact a network service. Keep these three
inputs and their parent directories stable during the operation.

## Commands

Use Python 3.12 or 3.13 from `tools/source-inventory`. No package install is
needed. First use `source_inventory.py` to capture your explicitly selected
source into an external private workspace. Set `$inventoryRun` to the absolute
path of its newly created run directory and `$privateWork` to an existing,
trusted absolute workspace outside this checkout:

```text
python -B classify_inventory.py --help
python -B classify_inventory.py --inventory "$inventoryRun" --rules "$privateWork/rules.json" --output "$privateWork/classification-new"
```

All three paths must be absolute. The output directory must not exist, its
parent must already exist, and it cannot overlap the input run or contain the
rules input. Existing files are never overwritten. On success the CLI prints
only counts, including unmatched and overlapping files, and exits **0**. An
invalid/unsupported input, exceeded bound, observed change or output error exits
**2** with a fixed error code. Unmatched/overlapping rows are explicit outcomes,
not failures: classification is a user-written grouping policy, not a safety
verdict. A write error can leave a new partial directory; no success is claimed.

Try the [fictional generated example](../examples/README.md) first. Its expected
result is four rows, one unmatched row and one row matching two rules.

## Rules v1

```json
{
  "schema_version": "outlands.path_rules.v1",
  "case_sensitive": true,
  "rules": [
    {"id": "docs-first", "category": "documentation", "kind": "prefix", "value": "docs/"},
    {"id": "markdown", "category": "text", "kind": "suffix", "value": ".md"},
    {"id": "python", "category": "source", "kind": "suffix", "value": ".py"}
  ]
}
```

Every field shown is required. No other field is accepted. Each rule has a
unique `id`; IDs and category labels use one to 48 lowercase letters/digits,
underscores or hyphens and begin with a letter/digit. Multiple rules may select
the same category. Rules are evaluated in their listed order against the entire
decoded relative path. The **first matching rule selects the category**. Every
matching rule ID is still reported, so overlaps remain visible even if their
categories are the same. Selected file/byte totals count each row only once.
Unmatched rows have JSON `category: null` and an empty CSV category.

Kinds are `exact` (whole path equality), `prefix` (literal beginning) and `suffix`
(literal ending). Slashes are ordinary characters; `docs/` means that exact
prefix, and `.py` matches any entire path ending in those characters. There are
no regular expressions, wildcards, glob expansion, implicit directory
boundaries or filesystem queries. `*` and `?` are literal characters. Rule
`kind: "glob"` and `kind: "regex"` are unsupported. An empty value is invalid.

Case sensitivity is explicit and mandatory. With `false`, Python Unicode
`casefold()` is applied to both the path and pattern; it is not an emulation of
the source filesystem. No Unicode normalization is performed. For example,
`Straße.py` can match the case-folded prefix `STRASSE`, while differently
normalized filenames remain distinct. Output rows are sorted by case-folded
path with exact text as the secondary key; output rule IDs preserve rule order.

## Accepted source report contract

The supported summary schema is `outlands.source_inventory.v1`, coverage
`selected_regular_files_only`, with Source Inventory's exact path-encoding
description. The classifier checks the SHA-256 of the **same CSV snapshot** it
parses against `files_csv_sha256`. It also verifies selected/hashed counts,
selected bytes, top-level counts, configured size/count bounds, basic timestamp,
skip-count and exclusion metadata, and the expected fields. Unknown top-level
summary fields fail the current contract. The optional `tree` object is not
interpreted or certified, and `tree.txt` is not read.

CSV headers must be exactly, in order:

```text
path,path_escaped,bytes,modified_utc,sha256,status
```

Rows require the supported `ok` status, nonnegative canonical integer sizes,
64-hex file digests and a timezone-aware UTC timestamp. Duplicate decoded paths,
wrong column counts, malformed CSV, inconsistent totals and unsupported path
encodings fail. The classifier removes **one leading apostrophe only when
`path_escaped` is `true`**, then verifies canonical re-encoding. It never strips
unflagged apostrophes or guesses whether an entry is an escaped path.

Supported path text has nonempty slash-separated components without `.`/`..`,
no leading slash/backslash, no NUL and no leading drive designator. Embedded
backslashes remain literal characters, which can occur in POSIX filenames;
they are never treated as separators or resolved. Unicode and control text
allowed by the original source report stays as data. Unsupported report names
must be reviewed using another tool; they are not silently omitted.

This validates a **self-consistent supplied report**, not its authenticity. An
editor can rewrite both CSV and summary hash. No original body hashes are
recomputed, and no external trust anchor, source completeness, ownership,
necessity, copyright, license or file safety is established. A category name is
the user's label, not a legal or technical assessment of the underlying file.
Prior Source Inventory exclusions and timing limits still apply.

## Outputs and privacy

A new successful output directory contains:

- `classification.json`: sorted relative-path rows, sizes, selected category,
  every matching rule ID, overlap flags, selected totals, unmatched count, rule
  order, bounded-work counters and hashes of the three input snapshots.
- `classified-paths.csv`: relative path, `path_escaped`, size, selected category,
  `|`-separated matching rule IDs and a lowercase overlap flag.
- `MANIFEST.json`: byte lengths and SHA-256 values for the exact JSON/CSV outputs.

JSON uses ASCII escapes for controls and Unicode, preventing invisible report
text from becoming literal terminal control sequences when the JSON is read as
text. CSV reuses the original reversible leading-apostrophe protection for
formula-like paths. Rule IDs/categories are restricted slugs. Treat CSV as data;
downstream transformations or spreadsheet behavior can change its handling.
Reports omit absolute input/output paths and file bodies. Relative names,
categories, byte counts and hashes can still identify private work. Review real
reports before sharing, and keep them outside source control by default.

The manifest identifies output bytes. It is not a signature, an authentication
record, or proof of a complete source snapshot. A failed output operation can
leave partial new files and must not be treated as a completed result.

## Bounds and filesystem assumptions

| Input or work | Hard limit |
| --- | ---: |
| CSV snapshot | 16 MiB |
| Summary JSON | 1 MiB |
| Rules JSON | 256 KiB |
| JSON nesting / traversed value nodes | 16 / 50,000 |
| Selected rows | 10,000 |
| Decoded path / pattern length | 4,096 / 1,024 characters |
| Rules | 128 |
| Path/rule comparisons | 1,000,000 |
| Matching work units (folded path + pattern lengths) | 64 MiB |
| JSON / CSV output | 32 MiB / 16 MiB |

Every supported row is compared with every rule to expose overlaps. Exceeding
a count, work or output bound fails the entire operation before output creation.
Work units are a conservative string-length budget, not measured CPU time.
Strict JSON rejects duplicate fields, nonfinite/fractional numbers, wrong types
and malformed text. Stored file-byte counts are bounded by the source summary's
supported ceilings: 64 MiB/file and 256 MiB total.

Inputs must be ordinary local files in trusted, quiescent directories. UNC,
device/extended network paths, Windows alternate data streams, symlinks/reparse
components and nonregular leaf inputs are rejected where inspected. Bounded
reads compare path/descriptor identity and timestamps; final checks detect some
changes across the three sequential snapshots. No-follow/nonblocking flags are
used where available. These mechanisms do not provide an atomic multi-file
snapshot, hostile-filesystem sandbox or timeout for every native filesystem
operation. An unresponsive filesystem can still block. There are no automatic
repairs, source moves, deletion, device queries, uploads or report cleanup.

## Suggestions

Use the [bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=inventory_rules_bug.yml)
or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=inventory_rules_suggestion.yml).
Include a small generated inventory, rule document and expected category/overlap
result that you have rights to share. Never attach a real private inventory,
phone blob list, credentials, proprietary filenames or unreviewed report.
