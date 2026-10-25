# Fictional dependency locks

These files contain invented package labels, version declarations and SHA-256
values computed from new fictional marker strings. No artifact is bundled or
verified. They are parser/comparison data, not installation recommendations;
do not use them to install packages.

- `before.lock` has four declarations.
- `after.lock` changes a version and its hash, changes another hash only, omits
  one name, introduces another and retains one unchanged declaration.
- `hash-only.lock` retains all version strings and changes just one hash.
- `equivalent.lock` changes comments, adds a BOM and uppercases hash text while
  preserving every parsed record.

Use the [walkthrough](../README.md#fictional-walkthrough). The local attributes
preserve exact fixture bytes through checkout. Keep real locks, package names,
digests, configuration and comparison output private and outside this collection.
