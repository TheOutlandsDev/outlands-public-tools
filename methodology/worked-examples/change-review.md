# Orchard dependency change: a difference needs interpretation

**Intake.** Explain a proposed dependency-lock change without installing packages
or representing fictional artifact hashes as verified downloads.

**Decision.** Compare normalized declarations in the supported narrow lock format.
Keep formatting-equivalent records distinct from version-text or hash changes.
A changed version string is not automatically an upgrade or a safe replacement.

**Procedure.** The three-example runner compares the supplied `before.lock` with
`equivalent.lock`, then with `after.lock`. Expected exits are 0 and 1, with
`MATCHING_LOCK_RECORDS` and `LOCK_DIFFERENCES_REPORTED` respectively. Exit 1 here
is the intended review result, not a broken walkthrough. The changed fixture
contains additions, removal, version/hash edits and an unchanged declaration.

**Tradeoff.** Offline comparison is reproducible and does not alter an environment.
It cannot establish vulnerability status, dependency resolution, artifact origin,
license compatibility or successful application behavior after installation.

**Handoff.** Retain the old lock, identify the intended new lock and record the
actual comparison. A real update needs a separate install/test/rollback decision.
The supplied fictional locks are never installation recommendations.
