# Validation record — 2026-10-25

Local Windows / Python 3.12: 34 discovered unittest cases; 33 passed and one
native symlink case skipped because this test process lacks that privilege.
All six real Tk desktop cases passed. No native symlink success is claimed for
that local run. The collection CI requires Tk on Windows and Ubuntu, Python
3.12 and 3.13; check the linked run before treating a platform as passed.

The generated tests cover persistence, exact cents, Unicode, field/date/money
rejection, optimistic concurrency, immutable revision/decision history, approval
invalidation on revision, schedule clearing, transitions, archiving, follow-up
filtering, transaction rollback at limits, SQL parameterization, existing-file
refusal, missing/unrelated store refusal, JSON rejection, HTML escaping, CSV
formula protection, export hashes, backup verification, tamper rejection,
committed WAL backup, fresh-only recovery and controlled CLI failures.

Desktop cases instantiate actual Tk widgets and exercise create/edit, quote,
approval, scheduling, read-only history, stale edits, filtering/unsaved details,
and background backup/recovery. The tests use generated fixtures and invoke
controller methods; they do not prove usability for every screen size or assistive
technology. A duplicate polling callback found during local tests was corrected
and the complete suite rerun without Tcl callback errors.

The source gate checks exact paths, SHA-256, UTF-8/text bounds, Python syntax,
JSON syntax, common private-source patterns and local Markdown links. Pattern
scanning is limited and is not proof that arbitrary secrets are absent. Manual
review covers the explicitly included new source and fictional examples.

No real business records, emails, signatures, customers, payments or trade work
were used. There was no cloud synchronization, real approval validation,
power-loss injection, hostile filesystem test, tampered-schema acceptance,
production scale test, schema migration, full accessibility certification or
shared-network database acceptance. Backup tests demonstrate fixture consistency
and byte verification, not universal disaster-recovery assurance.

[Collection checks](https://github.com/TheOutlandsDev/outlands-public-tools/actions)
