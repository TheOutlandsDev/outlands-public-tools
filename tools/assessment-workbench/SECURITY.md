# Security and private records

This app is an offline single-operator record editor on trusted local storage.
It is not an assessment executor, authorization system, target-isolation tool or
multi-user service. Record consistency does not verify outcomes.

Stores, sidecars, history, imports, exports and clones contain private plaintext.
Removed records remain in earlier saved snapshots. Internal checksums are not
signatures and do not detect every deliberate consistent rewrite. Protect files
and recovery copies with appropriate local handling; the app does not establish
encryption or Windows ACL privacy.

Use stable ordinary local parents outside the checkout. The app refuses tested
unsafe path and sidecar conditions, existing output destinations, invalid schemas
and inconsistent history. Those checks are not a hostile-filesystem sandbox or
an atomic guarantee against concurrent changes. Do not remove a rejected journal
or modify a store to force it through validation. Clone/recover requires a valid
source and does not repair corrupt databases or hot journals.

For a report, provide the source revision, fixed error code and a newly invented
minimal reproduction. Never publish an actual store, export, journal, evidence,
authorization record, key, credential or private path. Use a private repository
security-report channel if available for details that cannot safely be made
fictional. Do not upload private records to a public issue or pull request.

See [validation limits](docs/VALIDATION.md) and the collection's
[release review](../../methodology/release-review.md) before sharing an export.
