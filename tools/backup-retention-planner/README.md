# Backup Retention Planner

Review an explicitly selected JSON declaration of independent full snapshots
against count, age and pin protections. Python 3.12+, standard library only.
The planner reads the selected plan and writes JSON to stdout. It does not
scan storage, read backup contents, copy, restore, delete, generate commands,
contact a host or create report files.

`KEEP` means a declaration is protected by the supplied policy or uncertainty
rule. `REVIEW` means it falls outside those declared protections and needs
private human review. **Neither decision authorizes deletion.** The planner
does not verify snapshot existence, independence, metadata, integrity,
restorability, redundancy or available space.

## Fictional examples

Run from the collection root:

```text
python -B tools/backup-retention-planner/retention_plan.py --plan tools/backup-retention-planner/examples/plan.json
```

Expected exit: **1**, `REVIEW_REQUIRED`. Five snapshots are `KEEP` and one is
`REVIEW`. The latest-count cutoff protects `sample_a`, `sample_b` and `sample_c`,
including the timestamp tie. `sample_d` is protected at the inclusive age
boundary; `sample_e` is pinned. Only `sample_f` falls outside the declared
protections. There are no plan issues. This does not make `sample_f` safe to
delete.

```text
python -B tools/backup-retention-planner/retention_plan.py --plan tools/backup-retention-planner/examples/keep-only-plan.json
```

Expected exit: **0**, `KEEP_ONLY_PLAN`. All three snapshots are `KEEP`: two tie
at the latest cutoff, and the third is pinned. Age protection is disabled.

```text
python -B tools/backup-retention-planner/retention_plan.py --plan tools/backup-retention-planner/examples/future-plan.json
```

Expected exit: **1**, `REVIEW_REQUIRED`, although both snapshots are `KEEP`.
`sample_a` is later than the declared review instant and is protected for
review. The one nonfuture snapshot is also protected, but cannot meet the
declared latest count. Issues are `FUTURE_TIMESTAMPS_PRESENT`, then
`LATEST_COUNT_NOT_MET`. Future metadata never displaces the nonfuture baseline.

These files are newly authored fictional metadata. No actual backup directory,
backup application or deletion operation is needed.

## Plan format

The UTF-8 JSON object has exactly these fields:

```json
{
  "schema_version": 1,
  "snapshot_kind": "independent_full",
  "as_of": "2030-04-10T12:00:00Z",
  "policy": {"keep_latest": 1, "keep_days": 0},
  "snapshots": [
    {"id": "sample_a", "created_at": "2030-04-10T12:00:00Z", "pinned": false}
  ]
}
```

The schema version is the integer `1`; `snapshot_kind` must be exactly
`independent_full`. Supply 1 to 256 snapshots. Each has exactly `id`,
`created_at` and `pinned`. IDs start with a lowercase ASCII letter, followed by
lowercase letters, digits, underscores or hyphens, at most 40 characters total;
each must be unique. `pinned` is an actual JSON boolean.

`as_of` and `created_at` are canonical UTC instants in
`YYYY-MM-DDTHH:MM:SSZ` form. Years 0001 through 9999 and valid Gregorian dates
are accepted; offsets, fractional seconds, leap seconds, whitespace variants
and implicit time zones are refused. `as_of` is supplied by the operator. The
planner never substitutes the machine clock.

The policy has exactly `keep_latest` and `keep_days`. `keep_latest` is an
integer from 1 to 256. `keep_days` is an integer from 0 to 36500; **0 disables
age protection**. Booleans, strings and floating-point numbers are not integers.
Unknown fields, duplicate JSON keys/IDs, wrong types and nonstandard JSON
numeric constants are refused. Values are not coerced or expanded.

Paths, sizes and dependency fields are outside this schema. Incremental,
differential, deduplicated and reference-dependent sets are unsupported. The
`independent_full` declaration is only an operator assertion, not proof of a
self-contained backup. Use a different review process when independence is
uncertain; do not strip dependency fields to make such a set fit this format.

## Protection rules and results

Protections are a union:

1. Pinned snapshots are protected.
2. Future-dated snapshots are protected for review and excluded from both the
   latest-count ranking and age calculation.
3. Nonfuture snapshots are ranked by their declared creation instant. The Nth
   latest instant is the cutoff; **all** snapshots tied at that cutoff are
   protected. If fewer than N nonfuture snapshots exist, all are protected and
   `LATEST_COUNT_NOT_MET` requires review.
4. When age protection is enabled, nonfuture snapshots whose age is no greater
   than `keep_days` rolling 24-hour periods are protected, including the exact
   boundary. This is elapsed UTC time, not a calendar-day grouping.

Rows remain in declaration order. A `KEEP` row lists its applicable fixed
reasons in this order: `PINNED`, `FUTURE_TIMESTAMP_UNVERIFIED`, `LATEST_COUNT`,
`WITHIN_AGE_WINDOW`. A `REVIEW` row has only
`OUTSIDE_DECLARED_PROTECTIONS`. Overlapping protections do not create duplicate
snapshot counts. Timestamp ties can protect more than `keep_latest` snapshots.

Per-snapshot output includes only `id`, `decision` and `reasons`. Counts are
`keep`, `review`, `future`, `nonfuture` and `latest_protected`. Issues, when
applicable, are ordered `FUTURE_TIMESTAMPS_PRESENT`, then
`LATEST_COUNT_NOT_MET`. Results omit dates, policy values, sizes, raw metadata,
input paths and native errors. IDs and reason relationships can still identify
a design or operational pattern.

The result scope is `DECLARED_INDEPENDENT_FULL_METADATA_ONLY`. Flags
`filesystem_scanned`, `backup_contents_verified`, `metadata_verified`,
`deletion_performed`, `deletion_authorized` and `network_probed` are always false.
Exit `0` means `KEEP_ONLY_PLAN` with no review rows or issues. Exit `1` means
`REVIEW_REQUIRED`, including an all-KEEP plan with issues. Exit `2` means
`ERROR` for invalid inputs or arguments; interruption returns `130`.

Declared pin flags are not independently verified. A matching policy does not
establish backup authenticity or recovery success, and is not a
storage-management action or permission to remove data.

## Privacy and filesystem limits

Keep real plans and stdout private. IDs, counts and reasons can disclose
information even though timestamps and policy values are omitted. This is not
a secret scanner, anonymizer, IP review or clearance to publish operator inputs.
Use the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md) for your own
plans, and keep real backup records outside the checkout.

The selected plan is limited to 64 KiB and must be a regular single-link file
with verifiable file and ancestor identities. Paths are limited to 4,096
characters and 64 parts; traversal, UNC paths, drive-relative paths and unsafe
stream/device forms are refused. Symlink/reparse paths, special nodes and
detected metadata changes are refused. These checks do not freeze a tree or
create an atomic or hostile-filesystem boundary. Use stable trusted local
storage. No socket/DNS probe is performed, but reading a plan on mapped drives
or mounted shares can involve the operating system's network storage stack.
Remote storage, arbitrary mounts and concurrent writers are not proven safe.
The input size bound cannot interrupt a blocked filesystem operation.

The CLI accepts `--plan FILE`, `--help` and `--version`; there is no report-file
option. Examples use Python's `-B` option to avoid generating bytecode files.

## Provenance, licensing and validation

This is fresh neutral planning code with newly authored fictional metadata.
The bounded reader pattern reuses reviewed public implementation; no held
operational source, private backup configuration, source mapping, user record,
credential or third-party backup payload is included or read. Selected original
source and examples use the repository's [MIT license](../../LICENSE),
attributed to TheOutlandsDev; this does not relicense operator inputs or
third-party material.

See the [batch review](../../docs/BATCH-11-BACKUP-RETENTION.md) for actual
validation results and remaining limits. CI targets Windows and Ubuntu with
Python 3.12 and 3.13. Fictional policy tests do not prove a backup exists or can
be restored.
