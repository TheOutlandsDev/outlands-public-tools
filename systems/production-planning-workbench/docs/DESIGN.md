# Retained engines and application architecture

The owner's authored allocation, demand-state, lot-sequencing, operator-transition
and readiness decision logic form the reusable program core. The private
customer-facing backend is replaced with an explicit local instance contract,
SQLite persistence, CLI and escaped browser UI.

## Planning and conservation

For each product, replay the append-only order states. The demand reducer guards
identity/version conflicts and records create/increase/decrease/shipping/cancel
effects on gross demand. Exact current-version replay has no duplicate event;
metadata-only versions can change state without a demand event. Gross lot counts
aggregate a product's demand before whole-lot rounding. This is a reference over
gross demand, not the WIP-adjusted action recommendation.

Validate dock declarations against current order versions and stage-7 stock.
Subtract declared assigned dock units from remaining demand. Feed the residual
into the retained allocation engine: sort orders by due date, sequence and ID;
consider stages 6 down to 1, choosing smaller available lots then lexical IDs;
allocate without exceeding demand or available quantity. Configured timing and
optional exceptions determine risk/priority. Prove both demand and WIP
conservation, and separately reconcile assigned dock units:

```text
remaining demand = assigned dock units + allocated WIP units + uncovered units
WIP input = allocated WIP + remaining WIP
```

The retained allocation start allowance uses Decimal half-up rounding. The
separate retained lot proposal uses a ceiling on factor-adjusted uncovered
units, followed by whole-lot ceiling. These distinct original rules remain
visible rather than being treated as interchangeable. Lot IDs follow observed
four-letter sequences, reject exhaustion and are proposals only. No external
identity lookup or reservation occurs.

Readiness follows the original dock/clearance decision tree, adapted to neutral
typed declarations. The six states distinguish missing dock evidence, missing
lot evidence, awaiting production clearance, partial readiness, readiness and
declared shipping evidence. Actual shipping remains unverified. No transport,
manufacturing-system client, database connection string or background worker is
included in the application.

## Persistence and local review

Each private project revision stores canonical JSON, an increasing sequence,
parent SHA-256 and a revision digest binding all three. Saving requires the
current expected revision and preserves the exact normalized order-history
prefix. Identical current content is idempotent. SQLite triggers forbid ordinary
updates/deletes of revision/action rows. Database-owner access can bypass local
controls; hashes are not signatures or externally anchored tamper proof.

Operator action identities bind the full project revision and allocation.
Original command/transition validation remains. The application adds optimistic
versions, transactional event/state insertion, bounded reviewer aliases/notes,
and preservation of exception codes when adding notes. A new revision gets new
action identities; review never authorizes physical operations.

The private instance's session lock prevents ordinary overlapping processes.
Database operations use a process lock and short transactions. Backups use the
SQLite backup API, validate the schema and produce a byte hash. Reports use new
UUID directories, exclusive writes and file manifests. No automatic restore or
command replay runs after interruption.

## File and browser boundaries

The same reviewed first-party helper functions and Windows backend as the public
Corpus Workbench are reused unchanged. Windows checks native identity, hard
links, reparse points and physical output boundaries. POSIX uses guarded
no-follow opens, ordinary file checks and ancestor/identity verification. The
source/Git tree cannot be an instance destination. Existing stores require the
exact trusted schema, version, ordinary single-link metadata, rollback-journal
header and no journal/WAL/SHM sidecars. Extensions are disabled.

This assumes stable trusted local storage. It is not hostile-SQLite acceptance,
an adversarial race guarantee, multiuser authorization or power-loss proof.
The session lock and file checks are not a distributed lock or network-storage
protocol. Inputs are separately read, not snapshotted against concurrent writers.

The local HTTP server binds to a literal loopback address. API reads/writes
require a random page token; writes check Origin, and requests check Host. JSON
bodies and reads are bounded, errors use fixed codes, and responses are no-store.
Untrusted content renders with DOM textContent/value rather than interpolated
HTML. Inline trusted scripts/styles remain in the local page's CSP. Shutdown
waits for active request threads before releasing the instance lock. The server
is a standard-library local tool, not a production web service.
