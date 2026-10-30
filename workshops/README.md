# Family quick-start workshops

Eight original fictional workflows, each shipped with its tool family. Use Python 3.12/3.13; all workshop commands use the standard library and separately installed runtime only.

- [Release and developer QA](release-qa.md)
- [File, backup and workflow](files-workflows.md)
- [Document and media inspection](documents-media.md)
- [Android and Linux inspection](android-linux.md)
- [Desktop diagnostics](desktop-diagnostics.md)
- [Local productivity applications](local-apps.md)
- [Data and AI tools](data-ai.md)
- [Game utilities](game-utilities.md)

Each workshop records its design decision, exact expectations, failure handling and limits. Run from a new external scratch workspace. Passing these CLI examples does not establish every tool, GUI, device or production workflow.

## Two complete-package system exercises

Toolkit 0.5 adds [reviewed imports](import-migration.md) and
[pinned document generation](document-template.md). Use the complete source ZIP:

```text
python -B workshops/system_exercises.py --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

Python 3.12/3.13 is supplied separately. Expect two exercises and 33 CLI commands,
independent SQLite/XML readback, explicit refusal paths and preserved prior output.
The complete package includes both applications; family ZIPs only carry these
shared guides. Generated instances, stores, documents and raw logs remain private.

## Toolkit 0.6 setup and update planning exercises

- [Review supplied setup declarations and manual order](environment-setup.md).
- [Compare copied packages, review a plan and revoke its handoff approval](release-update.md).

```text
python -B workshops/lifecycle_exercises.py --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY
```

Use the complete source package and a new absolute private path with an existing
trusted parent outside the package. Both exercises inspect independent hashes and
explicit refusal paths. The applications never install software or perform target
updates; manual setup, runtime acceptance and recovery remain unperformed.

## Toolkit 0.7 intake to evidence

[Follow two invented batches through mapping, receipts, coverage and evidence review](ingestion-evidence.md). The complete ZIP includes the 23-call runner, expected failures, independent capture/export hashes and explicit declaration-versus-transaction limits. Python is supplied separately.

## Manufacturing review

[Capacity, eligibility, delays and declared flow](manufacturing-review.md) connects four independent source tools in twelve fictional CLI checks. The complete ZIP and Python 3.12/3.13 supplied separately are required. Four expected review outcomes remain recorded; operator review and every real manufacturing action remain unperformed.

## Material-to-quality review

[Canonical lots, allocations, inspection coverage and rework dispositions](material-quality-review.md) connects eight independent tools in 24 original CLI calls, retaining thirteen expected review outcomes and exact input/report pins. Use the complete source ZIP with Python supplied separately.
