# Release review

The [Package Layout Checker](../tools/package-layout-checker/README.md) can run
declared-file checks on POSIX or supported Windows local volumes. Select stable
fictional inputs for public examples; keep real manifests and findings private.
PASS does not inspect unlisted files, establish the exact publication set,
detect arbitrary secrets or clear ownership/licensing. Audit the actual selected
export bytes separately. Read the [Windows limits](../tools/package-layout-checker/docs/WINDOWS.md).

The [Offline Dependency Lock Diff](../tools/dependency-lock-diff/README.md)
can identify changed lock declarations for private release review. Keep actual
package names/hashes and results private; differences do not establish upgrade
direction, artifact authenticity, compatibility or vulnerability status.

The [Offline Source Inventory Diff](../tools/source-inventory-diff/README.md)
can compare saved report metadata and expose exclusion/coverage uncertainty.
Keep real comparisons private. Matching hashes or grouped names do not select
an authentic original, establish ownership or approve a source release.

1. Identify the exact files intended for release; preserve originals and private provenance separately.
2. Review source origins, dependency terms, notices and the intended license for those files.
3. Replace private configuration with neutral templates. Use fictional fixtures and empty schemas instead of operational records.
4. Review code, comments, tests, documentation, relative names and generated outputs for credentials, identities, endpoints and confidential logic.
5. Treat archives, documents, screenshots, binaries and metadata as separate review targets. Text scanning does not clear them.
6. Run applicable checks; record actual platform coverage, failures, skips and untested behavior.
7. Record and independently review the exact export inventory and hashes. Recheck after every intentional change.
8. Inspect proposed Git additions and commit metadata. Keep private source history, reports, markers and runtime state outside the public repository.
9. Review branches, tags, release assets and historical versions separately where applicable.
10. Record publication approval, exact revision and remaining limitations before sharing.

Status: DRAFT. No generic scanner provides semantic confidentiality or ownership clearance.
