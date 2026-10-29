# Five-minute fictional release and update review

Use the complete Toolkit 0.6 source ZIP with separately supplied Python 3.12/3.13.
Choose a new absolute private directory under an existing trusted parent, outside
the extracted package. This is an approximate walkthrough, not a timed benchmark.

From the extracted package root:

```text
python -B workshops/lifecycle_exercises.py --exercise updates --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY
```

1. Capture two invented four-file packages into new private snapshots. Independent
   hashes check every copied file against its explicit manifest. The launcher is
   an inert text-file declaration and is never executed.
2. Compare without the five prerequisite/backup/removal/dependency assertions.
   Expect five blockers. A retained blocked plan cannot be approved.
3. Save a comparison with the explicit assertions. Expect one ADD, one REMOVE,
   two REPLACE and one UNCHANGED entry, plus one dependency version-text change.
   Those are descriptions, not operations. No target is read or changed.
4. Save a manual plan. An unapproved export is refused. Review that exact plan,
   then produce an eight-file private handoff. Hashes verify all seven manifest
   entries; payload files are excluded and execution/publication remain unauthorized.
5. Save another plan for the same pair: it inherits no approval. Revoke the earlier
   plan and observe that future exports are refused. Previously exported files
   remain outside the application's control. Reopen retained records and verify
   original input bytes, copied snapshots and the fictional target sentinel.

All five update/recovery checkpoints remain `NOT_PERFORMED`; runtime, backup and
target-state verification remain unestablished. The runner records its original
34 original CLI calls and private results in `exercise-results.json`.

To inspect the saved records, replace the placeholder with the same actual directory,
append `/updates`, and run from the complete package root:

```text
python -B systems/release-update-workbench/workbench.py --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY/updates serve
```

Open the printed local address and inspect the snapshots, comparisons, three plans
and approval/revocation state. Stop the server before separate CLI access. Keep the
whole stopped instance for a complete copy; index backups omit payload/artifact files.
Existing exercise directories are refused and failed evidence is retained.

This workbench never applies updates, executes a payload, controls services, probes
networks or performs recovery. Actual setup/update/acceptance/recovery must occur
through a separately reviewed process. See the [application contract](../systems/release-update-workbench/docs/CONTRACT.md)
and [validation boundary](../systems/release-update-workbench/docs/VALIDATION.md).
