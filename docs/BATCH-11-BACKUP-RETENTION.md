# Backup Retention Planner review — 2026-10-25

This batch adds [Backup Retention Planner](../tools/backup-retention-planner/README.md),
a fresh Python 3.12+ standard-library implementation from a neutral public
specification. The private audit identified backup-policy methods as a review
candidate; no held original server/backup source, private inventory,
configuration or operational record was selected, read, copied or executed
for this implementation. Earlier source-family holds remain in place. The
input metadata guard adapts the existing public MIT checker pattern.

## Planning and privacy boundary

One bounded JSON input declares an explicit UTC `as_of`, a count/age policy
and IDs, timestamps and pin flags for independent full snapshots. Count,
age and pin protection form a union. Every tie at the newest-count cutoff is
protected. Future-dated entries are retained for review and cannot displace
the nonfuture newest-count baseline. A shortage of nonfuture entries also
requires review. Zero age days disables age protection; a positive window
uses inclusive rolling 24-hour periods in UTC.

The planner returns IDs with `KEEP` or `REVIEW` and fixed reason/issue codes.
It omits dates, policy values, paths and raw input metadata. IDs, relationships
and decisions can still disclose backup design, so real plans and results
remain private. `REVIEW` means outside the declared protections and requiring
private human review; it is never deletion authorization.

The independent-full label, timestamps and pins are operator declarations,
not verified facts. Incremental, differential, deduplicated and other
reference-dependent sets are outside scope; dependency/path/size fields are
refused rather than ignored. A falsely labelled dependent set cannot be
detected from this metadata. The result does not prove backup existence,
independence, completeness, integrity, ownership, redundancy or restorability.

There is no wall-clock lookup, backup-location enumeration, backup-content
read, filesystem mutation, copy/restore/delete operation, command generation
or network/service probe. Only the selected JSON control file is read, and
the CLI writes JSON to stdout. Both deletion-performed and deletion-authorized
flags are always false.

## Bounds and validation

The input is limited to 64 KiB and 1 to 256 snapshots. IDs are unique neutral
ASCII tokens. Exact integer/boolean checks, canonical Gregorian UTC timestamps
at whole-second precision, policy bounds, exact field sets and duplicate-key
rejection prevent silent coercion or unsupported metadata handling. No local
clock or timezone is consulted. Age durations are compared without subtracting
a cutoff from an extreme calendar date.

The fictional suite covers union rules, all timestamp ties, exact age boundaries,
leap/calendar limits, future baseline isolation, shortages, strict schemas,
input preservation, fixed errors, output redaction and absence of scanning,
clock, network/process and mutation activity. The local Windows/Python 3.12.7
utility suite discovered 39 methods: 37 passed and two unavailable native link
operations were skipped. The collection run discovered 306 methods: 291 passed
and 15 were skipped, with no failures/errors. Skips are not passes.

Independent review passed 569 bounded fictional scenarios, including 500 seeded
plans compared with a separate sort-free oracle. Twenty-eight fictional CLI
scenarios passed and shipped example hashes remained unchanged. Ruff checks/
formatting and 161 local document checks passed. No actual backup was inspected.
The dedicated
workflow runs Windows/Ubuntu with Python 3.12/3.13 and checks documentation.
Consult the exact commit's Actions results for executed platforms.

The control-file guard checks sampled file/ancestor identities, regular-file
single-link metadata and link/reparse forms before/after a bounded read. Use
stable trusted local files. This is not an atomic snapshot or hostile-filesystem
sandbox. Mapped or mounted storage may involve OS network I/O, and byte limits
cannot interrupt blocked filesystem calls. Formatted reader errors suppress
native input detail while retaining Python source locations.

Selected original source, tests, documentation and fictional examples use MIT
with TheOutlandsDev attribution. No runtime or third-party implementation is
bundled. Private marker lists, audit findings, local evidence and publication
receipts remain outside the public repository. This review covers the addition
and its changed documentation, not unrelated imports, Git history, release
assets or the full private drive.

The exact 12-file publication set retains one conservative scanner finding:
an invented UNC path used by a negative input test. It must be refused before
filesystem access and represents no discovered host or operational path. The
finding has a private file-hash-bound disposition. Scanner status remains
`REVIEW_REQUIRED`, with no detector disabled and zero unresolved findings after
review. There were no private-marker matches or scanner errors.
