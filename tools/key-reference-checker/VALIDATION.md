# Validation and limits

The relational-quality-checks workflow qualifies Python 3.12/3.13 on Windows and
Ubuntu with source pins, fictional core/contracts and mandatory applicable native
file fixtures. Hardlink and parent symlink/junction fixtures must run; only the
opposite-platform method per tool may skip. Local volume link skips are recorded
and never count as native qualification.

Known results cover strict typed/null rows and complete physical-row accounting,
decimal normalization, composite keys without concatenation collisions, every
primary-key duplicate, missing/nullable foreign references, self references,
schema changes/order/no-rename inference, join duplicate fanout and explicit null
matching, outer/unmatched counts, empty sides and an independent fictional
materialized-pair oracle. Result cases cover all actual embedded pins, matching
false pin declarations, ordered columns, row ranges, strict truncation flags,
explicit partial-result policy and distinguishable dataset/result diagnostics.

The collection CLI walkthrough copies each directory independently, verifies source
pins, executes fictional examples, checks input hashes/no mutation, new report and
overwrite/source-tree refusals, fixed errors and omission of payload values. A
connected cohort uses the existing public CSV intake's actual invented records,
checks key references, join count 3, schema equality and one supplied result row
with actual recomputed pins. Result selection is Python fixture logic; SQL is
never executed. A non-SQL string may PASS pin/type checks, with semantic/authority
flags false: that evidence limit is explicitly tested.

No database, deployed schema, production query/result, source completeness,
transaction, SQL dialect, migration, query optimizer, representative volume or
execution-time guarantee is qualified. Empty tables may pass vacuously within
declared constraints. Native guards require trusted quiescent storage and do not
sandbox hostile concurrency or impose OS quotas. Real inputs/reports remain
private; source/functional checks are not a universal privacy/security review.
