# Input and output safety

The CLI reads one explicitly selected bounded UTF-8 JSON request through the reviewed public toolkit. It neither opens a network connection nor executes the inspected content. Optional `--out` creates a new file outside source and refuses overwrite. Reports can reveal keys, tags, counts and hashes; review them before sharing.
