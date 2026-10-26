# Project Workspace

Windows now uses checked local paths, bounded native file reads and exclusive
directory/output creation with readback verification. Keep `workspace_windows.py`
beside the script. The original POSIX creation/check bodies are preserved.
Read the [filesystem contract](docs/WINDOWS.md) and
[Windows review](../../docs/BATCH-27-PROJECT-WORKSPACE-WINDOWS.md).

A neutral Python 3.12+ workspace builder using only the standard library. The default command plans without writing:

```text
python tools/project-workspace/workspace.py --root EXISTING_PRIVATE_PARENT --name demo-project
```

Add `--create` to create a new workspace. Add `--source INPUT_FILE` to retain a bounded input as opaque `original/intake.bin` and `working/intake.bin` copies. The tool reads the source, verifies both copies with SHA-256, and records only size/hash metadata. It does not parse, launch or modify the input. The input limit is 16 MiB; filenames are normalized instead of carrying original identifiers into control records.

The layout includes original, working, evidence/screenshots, evidence/test-output, deliverables, logs, rollback, and a generic control record. An existing destination is rejected. Paths crossing symlinks or Windows reparse points are rejected. Parent directories must already exist. Failures can leave a partial newly created workspace for inspection; no automatic recursive deletion or rollback occurs. Use stable trusted parents; these checks are not protection against a hostile filesystem or a guarantee of crash-atomic creation.

The resulting workspace is private operational material, including its copied input. Its ignore file excludes all contents from normal Git discovery; ignore rules are not access controls. Publish only a separate reviewed export. Console errors omit source paths and values.

Planning reads a selected source but writes nothing; it does not reserve a name.
Windows failures/interruption can leave complete-looking unconfirmed output,
even before a complete ignore file exists. Inspect it privately and check the
command result. Windows handled interruption returns 130; other handled input/
I/O errors return 2. Only the unnamed input data is copied, not streams or ACLs.

This is a new portable implementation of a generic original-preservation workflow. No workplace-specific template, name, identifier or fixed drive path is included. MIT licensed; see [licensing](../../LICENSING.md) and [validation](../../docs/BATCH-6-REVIEW.md).
