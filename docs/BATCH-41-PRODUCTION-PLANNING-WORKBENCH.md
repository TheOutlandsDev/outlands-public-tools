# Production Planning & Operations Workbench

This coherent application batch adapts five owner-authored engine sources into
the [Production Planning & Operations Workbench](../systems/production-planning-workbench/README.md):
allocation/conservation, versioned demand, lot sequencing, operator transitions
and shipment-readiness decisions. A new neutral CLI/browser application adds
private instances, append-only revisions/actions, optimistic versions, reports,
SQLite backups and a complete invented two-product workflow.

Customer-specific backend/schema/adapters, original configuration/policies,
product routes/mappings, identities, endpoints, credentials, workbooks, records,
databases, logs, deployment code and runtime assets are excluded. Original source
files remain untouched. Reviewed first-party Windows/POSIX I/O helpers retain MIT;
Pydantic and its pinned dependencies are separately supplied under their own terms.

The fictional demo reconciles 160 remaining units into 25 assigned dock units,
85 allocated WIP units and 50 uncovered units, with three unreserved lot
proposals. It records an operator acknowledgment, exports four private report
files, appends an order revision and verifies a database backup. Calculations
and reviewer/shipping declarations do not authorize or verify physical work.

The CI matrix covers Windows/Ubuntu CPython 3.12/3.13, mandatory applicable native
link fixtures, strict input/failure cases, the complete fictional workflow,
source pins, deterministic source ZIPs and documentation. See
[validation and limits](../systems/production-planning-workbench/docs/VALIDATION.md).
Interactive browser acceptance remains unverified after local automation could
not initialize; real HTTP-handler tests are recorded separately.

This selected engine/application release advances the
[whole-program roadmap](PROGRAM-MIGRATION-ROADMAP.md). Remaining original
backend, analytics/database sources and operating instances need separate review.
The real drive inventory, detailed migration ledger and scanner markers remain
private. Source acceptance never clears actual runtime inputs or outputs.
