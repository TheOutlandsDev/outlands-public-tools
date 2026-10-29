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
