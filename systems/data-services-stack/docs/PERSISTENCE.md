# Persistence and restart review

A private workspace contains immutable generation directories `r000000`,
`r000001`, and so on, plus a transient empty `.writer-lock` during a session.
Each generation contains canonical `state.json` and, only after that write has
been flushed/readback-verified, an empty `COMMITTED` marker. The envelope includes
the format, sequence and SHA-256 of the preceding committed envelope.

Opening a workspace bounds enumeration/bytes, refuses unexpected entries and
nonordinary/link targets, checks commit markers, canonical JSON, predecessor
hashes and complete state/relationship rules. Selected schema/code is never
executed. Uncommitted generation output is preserved and counted, with bounded
ordinary-file reads, but is not parsed as state. Committed corruption is refused;
the application does not rewrite or silently repair it.

## Write and crash boundaries

- Run start commits `RUNNING` with original job settings and an input hash.
- Successful calculation commits the result and `PENDING` notification together.
- Dispatch commits an incremented `IN_FLIGHT` claim before invoking the transport.
- Its observed outcome commits separately. Definite non-acceptance may schedule
  a retry; acceptance stores a receipt; uncertainty requires review.
- If the outcome cannot be saved, the earlier claim remains. Recovery cannot
  infer whether the external operation took effect and must withhold replay.

New file writes are exclusive, flushed and readback-verified by the public I/O
backend. POSIX also syncs containing directory entries. A failed write poisons
the live session: it cannot continue reporting a cached state as confirmed.
Reopening determines which commit markers and valid snapshots are visible.
An operation can commit even when its acknowledgment is lost; idempotency and
recovery handle that uncertainty. No atomic power-loss/hardware guarantee is made.

## Recovery command

After stopping every caller using this private workspace:

```text
python -B stack.py --workspace PRIVATE_WORKSPACE recover --confirm-stopped
```

The assertion is required; it is not an automatic liveness probe. If a stale lock
exists, recovery removes only that fixed **empty** coordination directory after
type/identity checks. Nonempty, linked or changed locks are refused unchanged.
The operation never recursively deletes data. A false stopped assertion is
unsafe on a shared/concurrent workspace; this application is single-operator.

Recovery marks remaining `RUNNING` records and `IN_FLIGHT` attempts as
`REVIEW_REQUIRED / RESTART_UNCERTAIN`. It preserves interrupted generation files
and all prior commits. Other terminal/uncertain states remain terminal. There is
no automatic retry, evidence-based promotion, reconciliation or reset of those
records. Review provider state privately before planning any separate action.

Normal mutating commands refuse a workspace with unfinished intents until this
review transition is recorded. Status/result inspection remains possible when
the coordination lock can be acquired. An interrupted first initialization with
no valid initial commit is refused; preserve it and select a different new path.

## Limits and integrity

Version 1 retains up to 16 configured jobs and 128 run/queue keys. A state envelope
is at most 1 MiB. There are at most 2,048 generation slots and 64 MiB of committed
plus retained uncommitted state bytes. These are explicit local reference limits,
not a throughput claim. Exhaustion refuses further writes; state is not purged to
make room. Failed claims do not invoke a transport. Workspaces and history need
an independent private backup/retention policy; no archive/compaction API is supplied.

Hashes are integrity linkage, not authentication, confidentiality or ownership
proof. Replacing a history with a forged chain or a valid earlier prefix cannot
be ruled out without an independently trusted checkpoint/access controls. Status
returns the current head hash for private comparison. Parent directories must
remain stable and trusted; native checks are not a hostile filesystem/VFS sandbox.
