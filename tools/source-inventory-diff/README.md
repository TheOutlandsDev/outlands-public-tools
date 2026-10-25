# Offline Source Inventory Diff

Compare two saved Source Inventory runs using their `files.csv` and `summary.json`
only. Python 3.12+, standard library only. The single script needs no sibling
module. It does not rescan source trees, reopen inventoried bodies, move/delete
files, verify renames or choose a canonical copy. Output is JSON to stdout;
the diff itself creates no report files.

Real reports/results are private. Relative filenames, modification times, sizes,
digests and relationships can reveal projects or guessed contents. Keep them
outside source control; this tool validates and compares metadata, not privacy,
ownership, licensing, authenticity, safety or permission to publish.

## Fictional walkthrough

Run from the collection root:

```text
python -B tools/source-inventory-diff/inventory_diff.py --before tools/source-inventory-diff/examples/before --after tools/source-inventory-diff/examples/before
```

Exit **0**, `MATCHING_SELECTED_RECORDS`: four unchanged selected records and no
review issues. This does not establish identical source roots or full coverage.

```text
python -B tools/source-inventory-diff/inventory_diff.py --before tools/source-inventory-diff/examples/before --after tools/source-inventory-diff/examples/after
```

Exit **1**, `REVIEW_REQUIRED`: one record only in before, two only in after,
one hash/size change, one timestamp-only change and one unchanged. A shared
reported hash/size group links the fictional old/new document names as a hint;
it is not a verified rename. Coverage declarations match, but actual scopes
are still unverified.

```text
python -B tools/source-inventory-diff/inventory_diff.py --before tools/source-inventory-diff/examples/before --after tools/source-inventory-diff/examples/coverage-changed
```

Exit **1**, `REVIEW_REQUIRED`: the same four records remain unchanged, but the
additional directory exclusion differs and a skipped directory is declared.
Omitted rows never establish deletion or absence from the underlying sources.
All three saved runs contain newly authored fictional filenames and hashes only;
see [examples](examples/README.md).

For real work, choose explicit before/after run directories under an
[external private workspace](../../docs/PRIVATE-WORKSPACE.md). Absolute and
ordinary relative directory paths are accepted without environment expansion.
Each run must contain the supported fixed control filenames. Extra files such
as `tree.txt` are not read or enumerated. A run can be compared with itself.

## Supported report contract

The parser adapts the collection's public
[Inventory Rule Classifier contract](../source-inventory/docs/CLASSIFICATION.md).
Required summary schema is `outlands.source_inventory.v1`, coverage is
`selected_regular_files_only`, and path encoding is exactly
`Remove one leading apostrophe only when path_escaped is true.` Unknown top-level
fields fail. Optional `additional_excluded_directories` and `tree` are accepted;
the tree object is bounded but uninterpreted, and `tree.txt` is never read.

CSV headers, in order, must be:

```text
path,path_escaped,bytes,modified_utc,sha256,status
```

The SHA-256 of the exact captured CSV bytes must match `files_csv_sha256`.
The parser also checks counts, total bytes, top-level counts, configured limits,
exclusion/skip metadata and timestamps. Rows require status `ok`, canonical
nonnegative integer sizes within the declared bounds, 64-hex digests and aware
UTC timestamps. Duplicate decoded paths, wrong columns, unsupported metadata,
invalid UTF-8/JSON/CSV, duplicate JSON keys and noninteger JSON numbers fail.
Empty selected reports are supported. Source report limits and exclusions remain.

The reversible spreadsheet escape is checked canonically: remove exactly one
leading apostrophe only when `path_escaped` is `true`. Literal apostrophes,
formula-like names, control text, Unicode and embedded backslashes remain data.
Paths must be nonempty relative slash-separated text without empty, `.` or `..`
components, a leading slash/backslash, a drive prefix or NUL. Embedded
backslashes are literal POSIX filename characters, not separators. Reported
paths are never joined to a filesystem root or used as commands.

## Comparison semantics

Matching uses **exact decoded path text**, without case folding or Unicode
normalization. Row order is deterministic: case-folded path, then exact path.
Reported digests are normalized to lowercase and UTC timestamp spellings are
normalized before comparison. Run labels, capture times, CSV row order and
optional tree metadata do not affect selected-record classification. Exact
input CSV/summary hashes remain recorded separately.

| Classification | Meaning within the supplied reports |
| --- | --- |
| `ONLY_IN_BEFORE` | No exact-path record in after |
| `ONLY_IN_AFTER` | No exact-path record in before |
| `HASH_OR_SIZE_CHANGED` | Same path, different reported digest or size |
| `MTIME_ONLY_CHANGED` | Same path/hash/size, different reported UTC mtime |
| `UNCHANGED` | Same path/hash/size/UTC mtime |

Every row retains path, classification and before/after metadata or null. These
are report observations, not actual file additions, deletions or verified body
changes. Equal digests are declarations, not recomputed source hashes.

Coverage checks compare effective excluded-directory sets (default plus
additional), excluded-suffix sets and configured limits. Exclusion sets are
case-folded and order-independent; the limits must match exactly. Different
sets/limits give `DIRECTORY_EXCLUSIONS_DIFFER`, `SUFFIX_EXCLUSIONS_DIFFER` or
`LIMITS_DIFFER`. Output omits the exclusion-name lists but retains both skip
count objects. Any nonzero skipped count gives `SKIPPED_ENTRIES_PRESENT`, even
when both count objects match. Matching declarations or counts never verify
equivalent roots, omitted entries or snapshot completeness.

The combined name set is also checked for distinct exact names sharing a Python
Unicode `casefold()` key. These groups give `CASEFOLD_PATH_AMBIGUITY`; exact-path
rows remain separate. This is a review signal, not filesystem emulation, a
collision proof or Unicode normalization.

`hash_size_groups` groups reported digest/size pairs with duplicates on either
side, or with records on both sides under different path sets. It retains all
before/after paths and never expands a many-to-many group into rename claims.
Any such hint gives `HASH_SIZE_GROUP_HINTS_PRESENT`, including duplicate groups
in otherwise unchanged reports. A digest associated with multiple declared sizes
gives `DIGEST_SIZE_CONFLICT`; incompatible sizes are not merged into one hint.
No group establishes ownership, an authentic original, dispensability or the
correct canonical copy.

## Status, output and bounds

Any coverage, skip, case-fold, digest-size or group-hint issue makes the result
`REVIEW_REQUIRED`. Without issues, changed selected records give
`DIFFERENCES_REPORTED`; otherwise status is `MATCHING_SELECTED_RECORDS`.

Exit **0** means matching selected records without review issues; **1** means
differences or review; **2** means input/output/argument error; **130** means
interrupted. `--help` and `--version` are static. Errors have fixed codes and
omit selected paths, supplied metadata and native exception text. All scan,
source-body access, mutation, deletion, rename-verification, canonical-selection,
authenticity/scope-verification and network-probe flags remain false.

| Bound per run or operation | Limit |
| --- | ---: |
| CSV / summary bytes per selected run | 16 MiB / 1 MiB |
| Selected rows per run | 10,000 |
| Decoded relative path | 4,096 characters |
| Declared file / total selected bytes | 64 MiB / 256 MiB |
| Summary JSON depth / value nodes | 16 / 50,000 |
| Serialized stdout JSON | 32 MiB, plus final newline |

Grouping uses indexes and path lists, not quadratic rename-pair expansion.
Output is bounded before printing; bound failures produce a fixed error instead
of a partial comparison. OS stdout failures or interruption can still leave
partial captured output and must not be treated as a completed JSON report.
JSON uses ASCII escapes for control/Unicode data. No CSV output is emitted;
downstream spreadsheet/terminal transformations can change handling.

The reader checks ordinary single-link control files and ordinary ancestors
with sampled descriptor/path identities before/during/after reads. All four
inputs are rechecked after comparison. Link/reparse and ambiguous/reserved path
forms are refused; original path suffixes are checked before Windows absolute
normalization. Use stable trusted local inputs. Sequential snapshots are not an
atomic four-file transaction or hostile-filesystem sandbox. Mount aliases and
blocked OS I/O remain outside the guarantee; underlying storage can involve a
network filesystem without a probe in this program. Formatted library exceptions
can retain Python source locations. An editor can rewrite CSV plus summary hash
consistently; no external trust anchor or original-body verification is provided.

## Validation and provenance

```text
python -B -m unittest discover -s tests -p test_inventory_diff.py -v
```

The local Windows/Python 3.12.7 suite discovered 45 methods: 43 passed and two
unavailable native-link operations were skipped. Tests include compatibility
with a newly generated fictional Source Inventory run, 200 seeded comparisons
against separate list-search/grouping reference logic, exact fields/hashes,
escaping, coverage/ambiguity handling, reversal/permutation invariants,
10,000-row grouping, reader/output limits and single-script standalone execution.
Skips are not passes. CI targets Windows/Ubuntu with Python 3.12/3.13; consult
exact-commit Actions results for executed jobs.

The parser, spreadsheet escaping and input guard adapt existing public MIT code
at `6797c65129122de9e6d2b2a799a71de5e0c469ad`. No held source archive, original private
inventory, configuration, filenames, hashes, credentials, operational records
or game assets were selected, read, copied or executed. Only fictional reports
ship here; real inputs/results and audit evidence remain private. Selected
original source/docs/tests/examples use [MIT](../../LICENSE), attributed to
TheOutlandsDev. No third-party implementation or runtime is bundled. See the
[batch review](../../docs/BATCH-17-INVENTORY-DIFF.md) for scope and evidence.
