# Copy, verification and failure boundaries

1. Validate the request/head and commit a started event before payload writes.
2. Bound the selected source walk, recording exclusions and stable file/directory
   identities. Included links, reparse points and special files fail.
3. Create a new generated target and its directory tree exclusively. Read guarded
   regular files, create payload files without replacement and record SHA-256 pins.
4. Compare the selected source inventory/identities again and re-read source hashes.
   Refuse ordinary concurrent changes rather than treating counts/sizes as proof.
5. Verify the copied tree's exact paths, empty directories, sizes and hashes. Write
   the canonical manifest, then the completion marker, and verify them together.
6. Commit the completed journal event. Only then is a normal snapshot registered.

This is not an atomic point-in-time filesystem transaction. Sources must be
quiescent and parents trusted; repeated checks cannot defeat a hostile writer
that controls the complete source and timing. Only primary file bytes and directory
structure are retained. Metadata, links, alternate streams, database consistency,
application state, permissions and operating-system restore are outside the format.

Restores first verify the pinned source snapshot. They copy into a new managed tree,
verify restored bytes, reverify the source package, write a restore receipt and
verify that receipt/tree before committing the completed job. Received snapshots
use an independently retained manifest pin and cannot select arbitrary destinations.
No received file, package hook, archive content or restored executable is run.

Failures commit a fixed error code where possible. Partial payloads and metadata
remain private and are never reused automatically. If the journal cannot finalize,
the started record remains pending for explicit review. A physical completion marker
without a completed journal event is not automatically adopted as a registered
backup. Read-only manifest inspection does not reverify payload integrity.

After a crash, confirm that all instance processes are stopped. Explicit recovery
marks pending jobs interrupted and keeps their files. It never resumes, deletes,
overwrites or infers completion. A lost browser response may follow a committed
operation; inspect the reloaded journal/head before another deliberate request.
Automatic write retries are not implemented.

Retention checks are observations at review time. They do not lock files forever
or authorize deletion. Source/restore files may change later. No cleanup interface
is supplied. At a finite journal cap or after index loss, preserve the old instance,
bring a separately reviewed complete snapshot copy into a fresh inbox, and restore
with its independently retained manifest pin. That recovers bytes without rewriting
or importing old journal history. An index backup alone contains no snapshot bytes.

Windows/POSIX guards use existing first-party native I/O boundaries for exclusive
outputs, bounded stable reads, link/reparse refusal and SQLite access. The HTTP UI
is single-operator loopback with Host/Origin/token checks, no automatic request
logging and literal text rendering. This is not multi-user authentication, encryption,
malware containment, immutable storage or protection against a hostile local user.
