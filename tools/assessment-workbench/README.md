# OUTLANDS | Offline Assessment Workbench

A local desktop and command-line editor for neutral submission, finding and
retest records. Create an empty private SQLite store, edit structured drafts,
save revision history, and reopen the saved work. Python 3.12 or 3.13 and the
standard library only; the desktop also needs Tcl/Tk.

This records operator declarations. Consistency does not prove a performed
test, a fixed vulnerability, authorization or target isolation. There are no
target, evidence, narrative, identity or credential fields, and no network,
model, command or test execution.

## Desktop quick start

From the collection root:

```text
python -B tools/assessment-workbench/workbench.py
```

Choose **Fictional demo** and select a NEW `.sqlite` filename under an existing
private parent outside the entire checkout. The demo contains two invented
submissions, one finding and one retest. Its four passing checks describe
record consistency only. For your own work choose **Create store** with a
different NEW filename. An empty revision-0 store starts as `REVIEW_REQUIRED`
with `EMPTY_WORKSPACE`.

Use the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md) to choose a
private location. No previous store is remembered or opened automatically.
Windows Python installers commonly offer Tcl/Tk; Ubuntu's desktop prerequisite
is supplied separately as `python3-tk`. The CLI works without a display.

## Editing and saving

1. Select a submission, finding or retest tab. Use **New / clear form** to add a
   record, or select an existing table row to edit it. IDs cannot be changed
   during an edit. Reference, state and outcome choices are guided dropdowns;
   the explicit `(none)` selected-retest choice becomes JSON null.
2. **Apply form to draft** changes only the in-memory draft. Apply each form
   before saving. **Validate draft** displays fixed-code consistency results;
   it does not write the store.
3. **Save draft** commits the whole draft as one new history sequence. There is
   no autosave. Schema-valid `REVIEW_REQUIRED` drafts can be saved; malformed
   records cannot. References are never silently repaired and states are never
   automatically advanced.
4. **Remove selected from draft** removes that current record without cascading
   changes to references. Earlier saved snapshots retain its plaintext. Review
   any resulting blocked references before saving. A completely empty workspace
   is allowed; other ledgers must have at least one submission.
5. **Refresh saved store** reloads the saved head. Switching stores, refreshing
   or closing asks before discarding unsaved drafts or unapplied form changes.
   If another instance saved first, Save refuses the stale revision and retains
   your draft. Refresh discards that draft; retain any needed edits privately
   before reloading and reapplying them. There is no automatic merge.

Imported dangling references remain visible until explicitly corrected. The
editor does not replace them with a valid-looking default. The status line
distinguishes unapplied forms, unsaved draft changes and the last validation.

## History, export and recovery

**Read-only history** previews saved ledgers by sequence. It is change history,
not a test-execution log or signed evidence. Removing a current record does not
erase older snapshots. A new save appends history; there is no pruning.

**Export saved JSON** writes a NEW private file containing the complete saved
ledger, including references, series labels, revisions, states and outcomes.
It exports the saved head, not an unsaved draft, and is not a history backup.
The desktop requires saving or refreshing unapplied/unsaved changes first.
**Import to NEW store** reads this neutral ledger format into revision 0 of a
new store. It does not merge records or import the previous store's history.

**Clone saved store** creates a NEW private store containing validated history.
From history, a selected revision can be cloned with all history through that
sequence. The active editor is unchanged. This is logical recovery from an
entirely valid store, not repair of a corrupt database or hot journal. Existing
destinations are refused; source databases and rejected sidecars are preserved.

The internal SHA-256 chain can detect accidental inconsistency relative to the
stored chain. It is not a signature, trusted audit trail or authenticity proof.
A consistent external rewrite can pass validation. Real stores, journals,
exports, clones and history are private plaintext; no encryption or Windows ACL
privacy is established by the application.

## Command-line walkthrough

First define an absolute `$privateWork` outside the checkout using the private
workspace guide. These commands use a fresh filename and the stated revisions:

```text
python -B tools/assessment-workbench/workbench.py init --store "$privateWork/assessment-001.sqlite"
python -B tools/assessment-workbench/workbench.py check --store "$privateWork/assessment-001.sqlite"
python -B tools/assessment-workbench/workbench.py save --store "$privateWork/assessment-001.sqlite" --input tools/assessment-workbench/examples/records.json --expected-revision 0
python -B tools/assessment-workbench/workbench.py show --store "$privateWork/assessment-001.sqlite" --records
python -B tools/assessment-workbench/workbench.py history --store "$privateWork/assessment-001.sqlite"
python -B tools/assessment-workbench/workbench.py export --store "$privateWork/assessment-001.sqlite" --output "$privateWork/assessment-export-001.json"
python -B tools/assessment-workbench/workbench.py clone --store "$privateWork/assessment-001.sqlite" --output "$privateWork/assessment-clone-001.sqlite" --revision 1
```

The initial empty `check` returns exit **1**. The save commits the fictional
ledger as revision **1**; its four record checks pass. `--records` explicitly
requests the full private ledger on stdout. Normal status output is also
private: IDs, counts and workflow codes can identify a design.

| Command | Purpose |
| --- | --- |
| `init --store NEW` | Empty revision-0 store |
| `demo --store NEW` | Invented four-record revision-0 store |
| `import --input JSON --store NEW` | Import a schema-valid ledger, including review drafts |
| `show --store STORE [--records]` | Saved-head status, optionally complete records |
| `check --store STORE` | Check the current saved ledger |
| `history --store STORE` | Read-only history summaries |
| `revision --store STORE --revision N [--records]` | Inspect a selected saved sequence |
| `save --store STORE --input JSON --expected-revision N` | Append an explicitly supplied whole ledger |
| `put --store STORE --kind submissions\|findings\|retests --record JSON --expected-revision N [--id ID]` | Add a record, or update the same immutable ID |
| `remove --store STORE --kind submissions\|findings\|retests --id ID --expected-revision N` | Remove from the current ledger without cascading or erasing history |
| `export --store STORE --output NEW_JSON` | Complete saved ledger, without history |
| `clone --store STORE --output NEW_DB [--revision N]` | Validated history through a selected sequence; `recover` is an alias |
| `gui` | Desktop; no arguments also start the desktop |

Read `--help` before a command. Expected store revisions are mandatory for
mutations; read the current revision again before each edit. Mutation commands
return exit `0` when a draft was stored even if it requires review. `check`
returns `0` for consistent records and `1` for review. Invalid input/storage
operations return `2`; interruption returns `130`. Controlled errors use fixed
codes and omit selected paths and native error text.

## Format, limits and public boundary

See [FORMAT](docs/FORMAT.md) for the exact neutral schema and state rules.
Stores are single-operator local files, capped at 16 MiB with 4 KiB SQLite pages
and 128 saved snapshots including revision 0. A canonical ledger is at most
64 KiB. There are no migrations, automatic rollover, pruning, background sync,
role/authentication controls or attachment stores.

Stores and new export/clone destinations require absolute external paths with
ordinary existing parents. File/ancestor identities and Windows alias checks
protect the tested checkout boundary. Store sidecar families are reserved, and
existing journals/WAL/shared-memory sidecars are refused and preserved. Use
stable trusted local storage. These checks are not an atomic snapshot or a
hostile-filesystem sandbox; arbitrary mounts, concurrent hostile writers and
mapped-storage support remain unproven. File reads can still involve the OS's
network storage stack. SQLite's two-second busy/progress budget is sampled and
cannot interrupt a blocked filesystem call; synchronous desktop operations can
wait on that call. Partial **new** outputs can remain after failure; automatic
cleanup does not delete them.

The public source and demo contain no real assessment data. Keep completed
stores, import/export files, snapshots, histories and stdout outside the
checkout and private. Validation is not anonymization or publication clearance.
No targets, people, narratives, evidence, credentials, authorization documents,
source builds or operator hashes are accepted as ledger fields.

See [validation](docs/VALIDATION.md), [provenance](docs/PROVENANCE.md),
[contributing](CONTRIBUTING.md) and [security reporting](SECURITY.md). Selected
original source and fictional examples are [MIT licensed](LICENSE), attributed
to TheOutlandsDev. The held original assessment application and private records
are not exported or cleared by this fresh implementation.
