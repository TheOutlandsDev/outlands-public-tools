# Batch 34: Verified Transfers I/O hardening

This update uses existing public MIT code and freshly invented disposable
trees. The [transfer tool](../tools/verified-transfers/README.md) retains both
bundle formats, external hash pins, exact source selection, text/path filters,
stopped-state assertions and no-overwrite behavior. Actual source inventories,
records, credentials, server configuration, deployment paths, assets, backups,
restores and original operational programs are not selected or executed.

Windows gains retained native file/directory handles, strict path spellings,
observed alias/checkout/source-destination checks and guarded streamed creation.
POSIX retains its protections and adds checked descriptors, ancestor rechecks,
bounded reads, completed short writes and readback verification. Native helper
functions come from the existing public preflight backend. Only new destinations
are populated; partial/unconfirmed output is retained rather than deleted.

See [I/O checks and limits](../tools/verified-transfers/IO-SAFETY.md) for the
stricter Windows path boundary and failure handling. Shared helpers also serve
private opaque backup/restore, so synthetic regressions cover those modes without
claiming application-consistent backups or publishing any data.

Validation uses the unchanged 39 transfer methods and 55 additional fictional
methods with a Windows/Ubuntu Python 3.12/3.13 matrix requiring native links and
junctions. Local original suite: 37 passes/two unavailable native skips. New
suite: 36 passes/19 platform or native-feature skips. A copied two-file runtime
passed 24 fresh processes. Across 100 fictional source trees, results and bundle
bytes matched frozen public source with cross-verification; ten invented opaque
round trips also matched. Runtime/input bytes stayed unchanged without bytecode.
Comparisons remain private with runtime hashes. Exact-commit CI evidence is
reviewed before merge.

Publication is limited to the exact reviewed source/documentation/test diff.
Frozen and current release auditors are compared with private markers; invented
negative-path flags must be dispositioned against exact file hashes. No scanner
rule is disabled. Generated trees, manifests, bundles, restored files, logs,
reports, markers and captures stay outside publication. No held original source
family or operational input is cleared by this update.
