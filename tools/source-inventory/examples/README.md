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
