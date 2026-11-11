# OUTLANDS | Source Inventory

Capture a bounded inventory of an explicitly selected folder: relative names,
sizes, modification times and SHA-256 in CSV, with counts/exclusions in JSON.
Optional tree export renders the same observed selection as quoted text. The
rule classifier groups captured rows without rescanning source files.

Download the initial **0.1.0 standalone source ZIP** from the
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/source-inventory-v0.1.0),
extract it into a fresh folder and follow [USAGE.md](USAGE.md). Keep all three
runtime scripts together: `source_inventory.py`, `classify_inventory.py` and
`inventory_windows.py`. Use Python **3.12–3.15**; qualification selects 3.15.2
for that minor. No third-party package, pip installation, network, model or
account is needed by the CLI. The source ZIP contains no interpreter, runtime,
dependency binary, real tree, original helper, generated report or raw log.

**Exit 0 / `COMPLETE_WITH_EXCLUSIONS` covers selected regular files only.** It
does not clear a whole tree for publication, establish confidentiality or make
an atomic snapshot. Default exclusions and skipped entries remain visible.
Real reports retain identifying filenames, hashes and timestamps; keep them
private even when file bodies and absolute root paths are omitted.

## Fictional workflow

From the extracted source folder, select new destinations in an existing
[private workspace](docs/PRIVATE-WORKSPACE.md):

```text
python -B examples/create_classification_example.py --destination ABSOLUTE_NEW_FICTIONAL_WORKSPACE
python -B source_inventory.py --root ABSOLUTE_FICTIONAL_SOURCE --output-dir ABSOLUTE_EXISTING_REPORT_PARENT --label demo
python -B source_inventory.py --root ABSOLUTE_FICTIONAL_SOURCE --output-dir ABSOLUTE_EXISTING_REPORT_PARENT --label tree-demo --tree --tree-depth 1
python -B classify_inventory.py --inventory ABSOLUTE_SUCCESSFUL_RUN --rules ABSOLUTE_RULES_JSON --output ABSOLUTE_NEW_CLASSIFICATION
```

The generator creates four authored text inputs, literal rules and an initial
inventory/classification. It never imports or executes the fictional `app.py`.
The commands then create independent fresh runs. Use the successful tree CLI's
`snapshot` name to select its run directory for classification.
[USAGE.md](USAGE.md) gives Windows/Ubuntu commands and expected counts;
[examples](examples/README.md) preserves the original generated walkthroughs.

Inventory roots and report parents must exist, remain trusted/unchanged and
not overlap. Filesystem roots are refused. Each successful inventory creates
a fresh run directory with `files.csv` and `summary.json`; `--tree` also writes
`tree.txt`. Classifier output must be new with an existing parent. Existing
reports are never overwritten. Python/device policy still applies; user-owned
portable prerequisites do not inherently require administrator access. Do not
bypass restrictions to run a fixture or install software.

## Selection, tree and classification

- Default limits: 1,000 selected files, 8 MiB/file, 64 MiB total selected bytes
  and 10,000 encountered directory entries. Hard ceilings: 10,000 files,
  64 MiB/file and 256 MiB total. Entry count is fixed. Default exclusions cover
  common VCS, credential, dependency/cache/build, data/model, backup/log and
  prior-report names. They are convenience filters, not a sensitive-data policy.
- `--exclude-dir` adds up to 64 case-insensitive directory basenames without
  removing defaults. `--tree-depth` requires `--tree`, accepts 1–64 and defaults
  to 16. Depth affects display only: deeper selected files remain hashed/in CSV.
- The tree uses the same collection/hash pass, includes observed nonexcluded
  empty directories, orders directories first and then case-folded/exact names,
  quotes names and escapes controls/bidirectional formatting. It records depth
  omissions explicitly and is bounded to 1 MiB; overflow fails before output.
- CSV paths use reversible leading-apostrophe escaping when `path_escaped` is
  true. Remove exactly one leading apostrophe only with that flag. CSV quoting
  alone is not spreadsheet protection; downstream transformations can change it.
- The classifier checks the captured CSV hash and supported summary/count
  contract. Literal `exact`, `prefix` and `suffix` rules use explicit case
  sensitivity; the first matching rule selects a category, while every matching
  ID and overlaps/unmatched rows remain visible. No regex/glob execution occurs.
- Classifier outputs are `classification.json`, `classified-paths.csv` and
  `MANIFEST.json` with exact output sizes/hashes. It validates supplied-report
  consistency, not authenticity or source completeness. Rewriting CSV and its
  summary hash together is possible. Categories are user labels, not verified
  safety, ownership or license verdicts. See [CLASSIFICATION.md](docs/CLASSIFICATION.md).

## Failure, filesystem and privacy boundary

Inventory errors return **2 / `INCOMPLETE`**; handled Windows interruption
returns **130 / `INCOMPLETE` / `INTERRUPTED`**. Classifier success returns
**0 / `CLASSIFIED_SUPPLIED_ROWS`**, including unmatched/overlapping rows; its
input/output/coverage errors return **2 / `INCOMPLETE`**. Help exits zero.

A failed operation can leave partial files or even a complete-looking but
unconfirmed summary. File existence/hash agreement does not prove CLI success.
Inspect selected outputs privately and choose fresh names; no automatic cleanup,
source moves or deletion is performed. Requested directory/file modes are
0700/0600; effective behavior depends on OS/Python and inherited ACLs. This is
not a Windows confidentiality audit or encryption guarantee.

Use trusted quiescent local storage. Observed links/reparse entries are not
followed, and unsupported entries are counted as skipped. Native Windows guards
check supported names/handles/identity; POSIX uses available descriptor/no-follow
protections. Hard links remain separate names; only unnamed file data is hashed.
There is no ADS/ACL/topology certification, atomic snapshot, hostile-filesystem
sandbox, universal I/O timeout, power-loss or live-SMB guarantee. Detected read,
size/identity/time changes fail rather than silently produce a complete result.
Read the preserved [Windows contract](docs/WINDOWS.md).

Eight fresh extracted-ZIP Windows/Ubuntu Python 3.12–3.15 qualification lanes
run the existing regressions and copied-runtime CLI fixtures in new venvs
without pip/distributions. Actual counts/skips appear in release `VALIDATION.json`;
planned coverage is not a passing result. See [qualification](docs/QUALIFICATION.md)
and separate [historical validation](docs/VALIDATION.md).

Selected original material is [MIT licensed](LICENSE), with AI assistance and
no claim of exclusive authorship. Retained originals remain unchanged and outside
the release; unrelated rights remain uncleared. Read [provenance](docs/PROVENANCE.md),
[collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md)
and [CONTRIBUTING.md](CONTRIBUTING.md). Public bug reports must use authored
fictional inputs, not real inventories, personal paths or unreviewed reports.
