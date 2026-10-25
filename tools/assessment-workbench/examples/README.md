# Fictional workbench walkthrough

`records.json` is newly authored metadata matching the app's fictional demo:
two submissions, one finding and one retest. Its four record checks pass because
the declarations agree. No test was performed and no vulnerability was verified
or resolved by this fixture.

From the collection root, define an absolute `$privateWork` using the
[private workspace guide](../../../docs/PRIVATE-WORKSPACE.md), then import into
a NEW store:

```text
python -B tools/assessment-workbench/workbench.py import --input tools/assessment-workbench/examples/records.json --store "$privateWork/assessment-demo-001.sqlite"
python -B tools/assessment-workbench/workbench.py check --store "$privateWork/assessment-demo-001.sqlite"
python -B tools/assessment-workbench/workbench.py gui
```

The imported ledger starts at store revision 0. In the desktop, choose **Open
store** and select that private file. Select the finding, change state to `open`
and selected retest to `(none)`, then Apply and Save. This creates revision 1.
The retest remains as a historical summary and does not force closure. Reopen
the store to confirm the change persisted.

History still contains the original closure claim. Preview revision 0 without
changing the active draft, or clone through it to a NEW store:

```text
python -B tools/assessment-workbench/workbench.py revision --store "$privateWork/assessment-demo-001.sqlite" --revision 0 --records
python -B tools/assessment-workbench/workbench.py clone --store "$privateWork/assessment-demo-001.sqlite" --output "$privateWork/assessment-recovery-001.sqlite" --revision 0
```

The clone does not overwrite or repair the source. Real ledgers, stdout,
histories, clones and exports remain private even when they contain only IDs
and coded declarations. Do not replace the shipped fixture with real records.
