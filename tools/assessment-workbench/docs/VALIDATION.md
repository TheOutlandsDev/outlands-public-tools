# Validation and remaining limits

Tests use newly generated fictional records in owned private temporary folders.
No actual assessment targets, people, findings, evidence, stores or held
application data are needed. The desktop smoke uses real Tk widgets with native
dialogs replaced by controlled test choices; this is separate from a human
usability or accessibility study.

## Reproduce

From the collection root:

```text
python -B tools/assessment-workbench/source_check.py
python -B -m unittest discover -s tools/assessment-workbench/tests -v
```

Set `ASSESSMENT_WORKBENCH_REQUIRE_TK=1` for the tests to require a working Tk
display instead of skipping desktop checks. CI targets Windows and Ubuntu with
Python 3.12/3.13 and requires real Tk; Linux uses a display server for those
tests. Consult the exact commit's Actions results for executed platforms.

The local Windows/Python 3.12.7 suite discovered 62 tests: 60 passed and two
unavailable native-link operations were skipped. All 12 real-Tk tests ran and
passed. Skips are not passes.

For standalone handoff validation, copy only the 20 app files outside the
collection and run the source check and complete suite from that copy. The
checker provenance test uses the pinned bundled-source hash and explicit
fictional status/evidence vectors; it does not load a sibling collection file.
The separate handoff run's outcome is recorded in the linked batch review.

The contention regression uses a separate child process to hold a SQLite writer
lock. The revised local suite passed its exact `STORE_BUSY` check and confirmed
unchanged saved snapshot, history and source bytes. It does not open an
unsupported external SQLite connection inside the app process.

The independent local desktop walkthrough passed 15 real-Tk fictional scenarios:
empty startup without storage writes, create, actual Apply/Save controls, guided
references, immutable IDs, draft-only removal without cascades, validation,
refresh, history, export, selected-revision clone, stale-save retention and null
selection. Native dialogs were mocked for that noninteractive run. A separate
26-scenario CLI walkthrough passed empty/init/save, full-record reads, history,
import/export round trips, selected-history clone/recover, review-draft edits,
removal without cascades, retained old records, stale saves and refusal to
replace existing destinations. The shipped fixture and refused files retained
their hashes. Collection suite figures and publication review are recorded in the
[batch review](../../../docs/BATCH-14-ASSESSMENT-WORKBENCH.md).

## Required behavior

Storage checks cover empty/demo/import creation; real SQLite transactions;
revision/history persistence; schema-valid review drafts; stale expected
revisions; exact database schema and canonical snapshots; chain and corruption
refusal; pre-connection header/WAL refusal without artifact creation; serialized
storage access and reentrant-call refusal; input/output bounds; path/sidecar
boundaries; new-only exports/clones;
and original-file preservation on refusal. Desktop checks cover typed controls,
explicit draft application/saving, unsaved-change confirmation, readonly
history and preservation of a stale draft after conflicts.

Each exact export must also pass source-manifest and sensitive-pattern review.
A source check or passing fixture suite does not sanitize a future store,
operator input, export or changed file.

## Unproven behavior

- Real test execution, remediation quality, authorization and target isolation
  are never verified.
- The app has no user authentication, encryption, signed approvals, multi-user
  service or tamper-proof audit. Consistent external database rewrites can pass.
- Internal history preserves removed plaintext. JSON export omits history;
  logical clone preserves validated history and is not corrupt/hot-journal repair.
- Use trusted stable local files. Path/identity checks are sampled, not an atomic
  filesystem sandbox. Arbitrary mount aliases, hostile concurrent mutation,
  mapped-storage guarantees and Windows ACL privacy are not established.
- The sampled SQLite busy/progress budget cannot interrupt a blocked OS call.
  Desktop operations are synchronous and can wait on that call.
- Public storage APIs must be the sole SQLite access in the process. External
  connections in that same process are unsupported; API serialization is not
  multi-process access control or a hostile-filesystem boundary.
- No migrations, pruning, automatic cleanup or live-store file-copy backup is
  implemented. Failed new outputs can remain for inspection.

Skips are not passes. Synthetic consistency and recovery checks do not prove a
real assessment occurred or establish safety for a specific operational store.
