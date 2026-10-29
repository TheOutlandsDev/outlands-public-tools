# Validation and limits

The ingestion-control-checks workflow qualifies Python 3.12/3.13 on Windows and
Ubuntu with source pins, fictional contract tests, malformed JSON, full row
accounting and required native file fixtures. Hardlink and parent symlink/junction
fixtures must run in CI; only the opposite-platform boundary method per tool may
skip. Local volume link skips do not qualify those native boundaries.

Known results cover public mapping types/order/identity changes, no rename inference,
private-header omission, batch/receipt snapshot conflicts, stream/sequence/content/
receipt-ID aliases, failed/uncertain histories, rejected/conflicting source counts,
checkpoint gaps/no-change/bounds and exact run totals without duplicate weighting.
Any issue withholds batch plans/checkpoint suggestions/totals. Valid mapping
differences intentionally retain descriptive change codes for explicit review.

Actual CLI acceptance copies each complete tool independently, checks source pins,
executes fictional examples, creates new reports and refuses overwrite/source-tree
output. It checks fixed diagnostics and preserved input pins. A connected four-tool
cohort executes the already-public CSV intake and receipt reconciler on two
invented sources, binds actual generated source/map/preview/receipt pins and checks
known replay decisions, checkpoint 2 and four accepted source records in totals.
Committed status remains a fictional caller assertion, never store/transaction proof.

No real source-system access, database connection, delivery, automatic retry,
checkpoint persistence, target writes, operational recipe, browser application
or production validation is included. These tests do not prove exactly-once
processing, complete history, source count truth in supplied declarations,
authenticated receipts, migration compatibility or universal privacy/security.
Real inputs/reports remain private. Native guards require trusted quiescent
storage and do not sandbox hostile concurrency or impose OS resource quotas.
