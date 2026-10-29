# Five minutes: intake to reviewed evidence

Use the complete Toolkit 0.7.0 source ZIP and separately supplied Python 3.12/3.13.
From its extracted root, choose a new absolute private directory under an existing
trusted, quiescent parent, outside the package. It must not exist; avoid redirected
or linked parents. The runner never reuses an existing exercise.

```text
python -B workshops/ingestion_evidence.py --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY
```

The runner calls the original public CLIs 23 times. It writes invented inputs,
reports and an original Test & Evidence instance into that private directory.

1. Compare equivalent mappings, then change a required-field declaration. Expect
   PASS followed by REVIEW_REQUIRED with REQUIRED_CHANGED. No mapping is applied.
2. Preview two three-row CSV batches. Each has two distinct accepted records and
   one exact duplicate. Reconcile actual source, mapping and preview bytes against
   pinned receipts. A deliberately altered preview pin must require review.
3. Plan skip for batch-a and manual review for batch-b using selected fictional
   committed-status snapshots. Missing batch-b coverage withholds totals. Supplying
   both declarations gives six input rows = four accepted + two duplicates.
4. Import two authored coverage-summary checks into Test & Evidence. Import and
   trust execute nothing. An untrusted run is refused. After explicit exact-hash
   trust, run the pinned plan: observed six rows matches expected six in one case
   and deliberately fails expected seven in the other. Raw captures and script,
   input and artifact hashes are independently checked.
5. Pending evidence cannot export; incomplete review checks cannot approve it.
   Review complete failure evidence and inspect nine private export files. Every
   member hash is recomputed. Reopening retains one match and one unmatched result;
   approval never changes the verdict. Original fixture bytes remain unchanged.

Expected counts are described here; `exercise-results.json` records only what the
runner observed on your machine. Exit 0 means these oracles passed. Exit 1 means
refusal or a failed oracle; inspect the retained private workspace. Never publish
its raw logs, inputs, database, capture streams or reports without a separate review.

## What this establishes

The intake/reconciler recompute per-file row accounting and byte pins. Batch tools
evaluate supplied declarations; they do not authenticate receipt authority, verify
a transaction, read a real store or establish exactly-once processing. No import,
retry or external service is performed. The two authored standard-library Python
checks assert the saved fictional coverage summary; they do not rerun an import.
They execute with operator filesystem/network permissions, without a sandbox or
descendant containment. Local review labels are assertions, not authenticated
identities. Evidence approval does not authorize execution or publication.

For an interface walkthrough, separately download the Windows Test & Evidence
bundle through the [collection start guide](../docs/START-HERE.md). Its bundled
Python belongs to that separate release; these Toolkit source ZIPs contain no
installed runtimes or dependencies. A modern browser is needed only for the GUI.
