# Fictional saved inventory reports

These three run directories contain only invented relative names and SHA-256
values computed from newly authored fictional text strings. They contain no
source bodies, original project inventory, private path, credential or real
operational record. Timestamps are fixed fictional UTC instants in 2030.

`before` has four records. `after` changes one reported body hash, changes one
mtime, introduces two names and omits one name. One old/new name pair shares a
reported digest and size, producing a review hint rather than a verified rename.
`coverage-changed` retains all before records but adds a directory exclusion
and declares one skipped directory.

Run the [walkthrough](../README.md#fictional-walkthrough) from the repository root.
Self-comparison returns exit 0; the other two comparisons return exit 1.
`.gitattributes` preserves the exact CSV/summary bytes so the recorded CSV
digests survive checkout. No run writes output files or reopens a source body.
