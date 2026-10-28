# Design and source origins

This standalone first-party MIT implementation adapts the generic management model
from an earlier assessment-manager prototype: engagement scope assertions, received
submission hashes, finding dispositions, manual retest notes and reviewed resolution.
It rebuilds persistence as replay-checked immutable snapshots and adds a small
standard-library loopback UI, compatibility import, comparisons and reviewed private
handoffs. It does not copy that prototype's runtime state or operational adapters.

The original prototype was inspected as source only. Its tests, server, scanners,
workers, package hooks and environments were not run. This release contains no
original records, organization-specific schema, operational profiles, target
inventories, containment settings, downloaded assets, binaries or private paths.
All examples and test receipts were newly invented.

The guarded SQLite/filesystem helpers in `assessment/vendor/store_io.py` and
`review_io_windows.py` are unchanged snapshots of the public Developer Workspace
helpers. `runtime.py` adapts only the instance/schema/sample names. The neutral
`record_contract.py` is an unchanged snapshot from the public Assessment Workbench.
These existing first-party MIT notices remain under TheOutlandsDev. Optional
browser-test dependencies are named/hash-pinned separately and are not bundled.

This app records manual work. It never establishes operational containment or
proves a vulnerability, remediation, legal authorization, reviewer identity or
permission to redistribute future received material.
