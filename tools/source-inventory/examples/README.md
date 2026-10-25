# Fictional folder-tree example

Run commands from `tools/source-inventory`. Create an absolute `$privateWork`
outside the repository using the collection's
[private-workspace guide](../../../docs/PRIVATE-WORKSPACE.md). The destination
below must not exist; its parent must exist and remain trusted and unchanged.

```text
python examples/create_example.py --destination "$privateWork/tree-example"
python source_inventory.py --root "$privateWork/tree-example/input" --output-dir "$privateWork/tree-example/reports" --label full-tree --tree
python source_inventory.py --root "$privateWork/tree-example/input" --output-dir "$privateWork/tree-example/reports" --label shallow-tree --tree --tree-depth 1 --exclude-dir scratch
```

The generator creates only fictional text and an empty directory. It does not
import or execute generated `app.py`. It refuses an existing destination; a
failure may leave a new partial example directory, which is never certified as
complete. It does not remove anything automatically.

The full example hashes four selected files and skips the fictional `.git`
directory and `.env` file. Its tree includes the empty directory. The second
run excludes `scratch`, hashes three selected files, and limits only the tree
display to depth one. Inspect `summary.json`: deeper selected files remain in
`files.csv`, and `tree.hidden_by_depth` reports entries omitted from `tree.txt`.

Every run uses a fresh report directory. Keep those generated directories outside
source control; real inventories can reveal private filenames and metadata.

## Fictional classification example

From the same module directory, choose a new destination under your existing
private workspace:

```text
python -B examples/create_classification_example.py --destination "$privateWork/classifier-example"
```

This creates four original fictional text inputs, a normal Source Inventory run,
an explicit `rules.json`, and a fresh `classification` output. It never imports
or executes the generated `app.py`. Expected stdout counts are **four files,
one unmatched file and one overlapping file**. Three selected categories contain
one file each: `source`, `text` and `documentation`. `docs/guide.md` matches both
the `docs/` prefix and `.md` suffix; the first rule selects `documentation`.
`scratch.txt` stays unmatched. Counts and byte totals cover only selected rows.

The JSON stdout `inventory_run` is a relative location under the new example
workspace. To try the classifier CLI again, set `$inventoryRun` to the absolute
path of that run, then choose another new output directory:

```text
python -B classify_inventory.py --inventory "$inventoryRun" --rules "$privateWork/classifier-example/rules.json" --output "$privateWork/classifier-second-run"
```

Inspect `classification.json`, `classified-paths.csv` and `MANIFEST.json`. The
manifest lists the exact JSON/CSV output sizes/hashes. No source bodies were
copied to those reports, and the classifier does not need the fictional source
files to remain present. Its trust is the supplied report, not a new source
scan. See the [full rule contract](../docs/CLASSIFICATION.md) for bounds and the
limits of the self-consistency checks. An existing destination is refused; an
output error can leave a new partial example directory without a success result.
