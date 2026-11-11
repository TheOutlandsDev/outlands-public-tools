# Use Source Inventory 0.1.0

Download the source ZIP from the
[standalone release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/source-inventory-v0.1.0)
and extract it into a fresh directory. Keep `source_inventory.py`,
`classify_inventory.py` and `inventory_windows.py` adjacent. No interpreter,
third-party package, dependency binary, original helper, real inventory or
generated report is included.

Use normal Python **3.12, 3.13, 3.14 or 3.15**; qualification selects 3.15.2
for that minor. The CLI uses only the standard library and needs no pip,
network, model or account. A user-owned interpreter/venv does not inherently
need administrator access. Follow device/software policy and do not bypass
restrictions. Python/OS prerequisites retain their own licenses.

## Private interpreter and workspace

Choose an existing trusted external [private parent](docs/PRIVATE-WORKSPACE.md).
You can make a new venv without pip. Windows PowerShell example:

```powershell
py -3.12 -m venv --without-pip 'D:\Private\SourceInventory\venv312'
$python = 'D:\Private\SourceInventory\venv312\Scripts\python.exe'
& $python --version
& $python -B source_inventory.py --help
& $python -B classify_inventory.py --help
```

Ubuntu example:

```sh
python3.12 -m venv --without-pip '/absolute/private/source-inventory/venv312'
python='/absolute/private/source-inventory/venv312/bin/python'
"$python" --version
"$python" -B source_inventory.py --help
"$python" -B classify_inventory.py --help
```

Replace paths and interpreter selection for your system/minor version. No
package installation follows. Keep the source directory separate from all
generated inputs, reports, venvs and qualification work.

## Fictional inventory → tree → classify

Run from the extracted source directory. The supplied classification generator
creates four fictional files, `rules.json`, an initial inventory and an initial
classification. It never imports or executes the generated `app.py`. Its new
destination's parent must already exist and stay trusted/unchanged.

PowerShell, continuing with `$python`:

```powershell
$demo = 'D:\Private\SourceInventory\fictional-demo'
& $python -B examples/create_classification_example.py --destination $demo
& $python -B source_inventory.py --root "$demo/fictional-source" --output-dir "$demo/inventories" --label plain
& $python -B source_inventory.py --root "$demo/fictional-source" --output-dir "$demo/inventories" --label tree-demo --tree --tree-depth 1
$LASTEXITCODE
$inventoryRun = Join-Path $demo 'inventories/SNAPSHOT_FROM_SUCCESSFUL_TREE_STDOUT'
& $python -B classify_inventory.py --inventory $inventoryRun --rules "$demo/rules.json" --output "$demo/classification-second"
$LASTEXITCODE
```

Ubuntu, continuing with `python`:

```sh
demo='/absolute/private/source-inventory/fictional-demo'
"$python" -B examples/create_classification_example.py --destination "$demo"
"$python" -B source_inventory.py --root "$demo/fictional-source" --output-dir "$demo/inventories" --label plain
"$python" -B source_inventory.py --root "$demo/fictional-source" --output-dir "$demo/inventories" --label tree-demo --tree --tree-depth 1
printf '%s\n' "$?"
inventory_run="$demo/inventories/SNAPSHOT_FROM_SUCCESSFUL_TREE_STDOUT"
"$python" -B classify_inventory.py --inventory "$inventory_run" --rules "$demo/rules.json" --output "$demo/classification-second"
printf '%s\n' "$?"
```

Before classification, replace `SNAPSHOT_FROM_SUCCESSFUL_TREE_STDOUT` with the
actual `snapshot` basename from the successful tree command's JSON stdout.
Continue only after exit **0** and `result: COMPLETE_WITH_EXCLUSIONS`; failure
may leave complete-looking unconfirmed files. No actual run name is fixed in
this guide. Choose another new example/classification destination when repeating.

Both explicit inventory commands select **four files**. The plain run writes
only `files.csv` and `summary.json`. The tree run adds `tree.txt`; depth one
hides deeper display entries without reducing hashing or CSV selection.
`summary.json` records `tree.hidden_by_depth` and `tree.display_complete`.
Every inventory run has a fresh timestamp/label/random-suffix directory.

Classification should exit **0 / `CLASSIFIED_SUPPLIED_ROWS`** with four files,
one unmatched file and one overlapping file. `docs/guide.md` matches both the
`docs/` prefix and `.md` suffix; the first rule selects `documentation`.
`README.md` selects `text`, `app.py` selects `source`, and `scratch.txt` is
unmatched. Existing initial reports remain unchanged.

The generated rules are the following literal schema, not executable patterns:

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

Every shown field is required; extra/duplicate fields and unsupported types
fail. Rules use literal `exact`, `prefix` or `suffix`, explicit case sensitivity
and ordered first-match categories. Every matching ID remains visible, including
overlaps with the same category. There are no regex/glob patterns or implicit
directory boundaries. The [full contract](docs/CLASSIFICATION.md) defines slugs,
case folding, accepted report fields, work bounds and failure behavior.

## Reports, selection and limits

Inventory summary schema is `outlands.source_inventory.v1`, with coverage
`selected_regular_files_only`. CSV headers are exactly:

```text
path,path_escaped,bytes,modified_utc,sha256,status
```

The classifier reads only `files.csv`, `summary.json` and rules. It checks the
same CSV snapshot's hash against the summary, supported counts/totals and path
encoding. It does not rescan original files, recompute their hashes or certify
tree metadata. An editor can rewrite CSV and its summary hash together.
Self-consistency is not authenticity, full-source coverage or a license verdict.

Classification produces `classification.json`, `classified-paths.csv` and
`MANIFEST.json`; the manifest records exact JSON/CSV byte lengths and SHA-256.
These hashes identify bytes, not an authorized writer or complete snapshot.

Default inventory bounds are 1,000 files, 8 MiB/file, 64 MiB total selected bytes
and 10,000 encountered entries. Options can lower file/byte bounds; hard ceilings
are 10,000 files, 64 MiB/file and 256 MiB total. Exceeding a bound fails.
`--exclude-dir BASENAME` adds up to 64 case-insensitive directory basenames;
defaults cannot be removed. Default exclusion names and skipped counts are in
the summary. They do not detect every secret or make a tree eligible to publish.

`--tree-depth` requires `--tree`, accepts 1–64 and defaults to 16. Display depth
does not change selection. Tree output is bounded to 1 MiB and orders directories
first, then case-folded/exact names. Quoted names escape controls/bidirectional
formatting. Observed empty directories can appear; excluded/link entries do not.
The [preserved example guide](examples/README.md) also demonstrates exclusions.

CSV uses reversible leading-apostrophe protection for selected formula-like
paths. Remove exactly one leading apostrophe only when `path_escaped` is true.
Treat CSV as data; quoting alone and later spreadsheet transformations are not
a confidentiality or formula-safety guarantee.

## Failure, native paths and privacy

Inventory success is `COMPLETE_WITH_EXCLUSIONS`, exit `0`; error is `INCOMPLETE`,
exit `2`. Handled Windows interruption is `INCOMPLETE` / `INTERRUPTED`, exit
`130`; POSIX interruption behavior is preserved. Classifier unmatched/overlap
counts are normal results, not errors; invalid/unsupported input, limits or
output failure return `2 / INCOMPLETE`. Help exits zero.

Use explicit, preferably absolute paths under trusted quiescent local parents.
Inventory input/report parents must exist and not overlap; filesystem roots
are refused. Classifier's three paths must be absolute; its output must be new
with an existing parent and cannot overlap its inputs. Observed links/reparse
entries are not followed; unsupported entries are skipped/countable. Windows
native name/handle/identity guards and POSIX descriptor checks remain in force.
Hard links are separate names; only unnamed data is hashed, not ADS/ACL/topology.

Existing reports/inputs are preserved. Failure can leave partial or fully
written but **unconfirmed** output, including a complete-looking summary.
Successful hashes/file existence are not substitutes for the CLI exit/result.
Inspect privately and choose fresh destinations. No automatic report deletion,
source moves or cleanup is performed by the CLI. Requested modes 0700/0600
depend on OS/Python and inherited ACLs; Windows confidentiality is not audited.

Reports retain relative names, top-level names, modification times, hashes,
sizes and user categories. These can identify private projects/content even
without absolute roots or file bodies. Shell arguments/history and redirection
can also retain private information. Keep actual reports outside public source
control and use only authored fictional public reproductions.

The checks do not provide atomic tree/multi-file snapshots, a hostile-filesystem
sandbox, immunity to concurrent replacement, universal filesystem timeouts,
power-loss recovery or live-SMB acceptance. Read the preserved
[Windows contract](docs/WINDOWS.md), [provenance](docs/PROVENANCE.md) and
[classification limits](docs/CLASSIFICATION.md).

## Source packaging and qualification

Optional maintainer helpers require normal Python and refuse `-O`, `-OO` or
`PYTHONOPTIMIZE`. They do not change the CLI's standard-library dependency scope.
From reviewed committed repository source, use:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
```

The output must be new with an existing parent. Release reproduction also builds
a second new reference package from the same committed source, then runs
`packaging/qualify.py --packages PACKAGE_DIR --reference-build REFERENCE_DIR
--workspace NEW_ABSOLUTE_WORKSPACE --report NEW_ABSOLUTE_REPORT_JSON` with the
selected normal Python. Both input directories must exist; workspace/report
must be new with existing parents. Omitting the optional reference comparison
for a local run supplies no deterministic-rebuild proof.

Fresh extracted-ZIP qualification uses eight Windows/Ubuntu Python 3.12–3.15
lanes, new venvs without pip or distributions, 124 existing regressions and
26 copied-runtime process methods. Exact helper commands and evidence are in
[QUALIFICATION.md](docs/QUALIFICATION.md).
Actual counts/outcomes/skips belong to release `VALIDATION.json`; historical
docs describe earlier support/evidence and remain separate from fresh results.
