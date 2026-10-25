# OUTLANDS | Job & Quote Tracker

A small, offline desktop and command-line application for recording jobs, quote
revisions, customer decision references, schedules, and follow-ups. Records stay
in a SQLite file you select. Close and reopen the application without losing
saved work. Original code, tests, documentation and fictional examples are
[MIT licensed](LICENSE).

This is part of [OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools).
There are no cloud accounts, analytics, email sends, external APIs, or third-party
Python package dependencies. It is designed for one person using trusted local
storage, not a shared business server.

## Quick start

1. Install Python **3.12 or 3.13**. The desktop needs Tk: Windows python.org
   installers normally offer Tcl/Tk; Ubuntu distributions provide `python3-tk`.
   The command line works without a display. No `pip install` is needed.
2. Download the collection source ZIP or clone it. In a terminal, change to
   `tools/job-quote-tracker` inside the collection.
3. Run `python tracker.py` (`python3` on systems that use that name).
4. Choose **Fictional demo** and select a NEW `.sqlite` filename in your private
   working folder. The demo contains two fictional jobs and one recorded sample
   approval. No existing file is overwritten.
5. For real work choose **Create store**, using a different NEW filename outside
   your source checkout. Use **Open store** to return to saved work.

From the collection root you can instead run:

```text
python tools/job-quote-tracker/tracker.py
```

## Desktop workflow

1. **New job** clears the editor. Enter a title and customer/organization; contact,
   notes and follow-up date are optional. Select **Save job details**. All dates
   are real calendar dates in `YYYY-MM-DD` form.
2. Select the saved job. In **New quote revision**, enter an amount with exactly
   two decimals (`125.00`), USD/CAD/EUR/GBP, scope, and optional exclusions.
   **Save new quote revision** adds history rather than overwriting a previous quote.
3. In **Decision & progress**, record a reference to the actual outside decision
   you received, then select **Record approval** or **Record rejection**. Only one
   decision can be recorded per revision. A correction needs a new revision.
4. An approved revision can be **scheduled** with a date, then moved to
   **in_progress**, **completed**, and **archived**. Cancel an active job before
   archiving it. To remove a schedule, move scheduled back to approved with the
   date field empty. There is no delete operation.
5. A new quote revision returns an editable job to **quoted**, clears the schedule,
   and requires a decision on that new revision. Earlier approvals remain visible
   in history and do not approve the new work. Quotes cannot be revised after work
   starts; record separate new work as a new job.
6. Use the status and follow-up filters, then **Refresh / filter**. The date filter
   includes active jobs due on or before the given date. It excludes completed,
   cancelled and archived jobs. It does not send notifications or reminders.
7. **Read-only history** shows every quote revision, decision reference and
   activity entry. An outdated editor cannot silently overwrite another instance:
   refresh and review the job if the version has changed.

Job-detail changes require **Save job details**. Quote-entry fields are temporary
drafts until **Save new quote revision**; switching jobs clears those draft fields.
Save a quote before selecting another job. There is no quote-draft autosave.
The unsaved-details prompt covers job details, not temporary quote/reference fields.

The application records what its operator enters. It does **not** verify a
signature, customer identity, authority, permit, professional qualification, tax,
payment, invoice, or completion of actual work. Do not treat its status buttons
as independent approval evidence. There are no role or authentication controls.

## Backup and recovery

Select **Backup**, then a parent folder. The app creates a uniquely named new
folder containing `store.sqlite` and `MANIFEST.json`. It uses SQLite's backup API
to include committed WAL data, checks database integrity and foreign keys, and
verifies the snapshot's SHA-256/length. A running SQLite store must not be backed
up by copying only its main file. Keep the complete verified backup folder.

Select **Restore backup**, choose that folder, then a NEW `.sqlite` filename.
Recovery verifies the two-file inventory, hashes and database checks before
opening the recovered store. Existing files are refused. If an operation fails
or is cancelled, a partial **new** output may remain; inspect it and retry with
another new name. Cancellation is cooperative. The desktop waits for background
work to finish before closing. Backup has a cooperative ten-second budget.

A backup manifest detects accidental changes relative to that manifest; it is
not a cryptographic signature. Protect your backups as private customer data.
Try a recovery and compare your records before relying on a backup.

## Reports

**Export report** creates a new folder with `index.html`, `jobs.csv`, `data.json`,
`README.txt`, and a SHA-256 `MANIFEST.json`. Open the HTML directly in your browser;
it has no JavaScript or external assets. CSV contains job summaries; JSON contains
the complete report including quote history and activity. Export is read-only
with respect to the store, but writes a new report folder. It is **not** a backup.

Reports include customer names, contact details, notes, scope, prices and decision
references. Keep real exports private. CSV formula-leading cells are prefixed
with an apostrophe and HTML text is escaped; review data before sharing anyway.
The app never publishes an export or opens an upload connection.

## Command line

Commands below run from this tool's directory. Substitute your own private paths.
All output files/folders must be NEW except the explicitly selected working store.
Success is exit 0 with JSON on stdout; controlled input/storage failures are exit
2 with a JSON error on stderr. Argument-usage errors also exit 2.

```text
python tracker.py --help
python tracker.py demo demo.sqlite
python tracker.py list demo.sqlite
python tracker.py show demo.sqlite JOB_ID
python tracker.py list demo.sqlite --status approved
python tracker.py list demo.sqlite --due-before 2026-11-30
python tracker.py new demo.sqlite --input examples/job.json
python tracker.py quote demo.sqlite JOB_ID --expected-version 1 --input examples/quote.json
python tracker.py decision demo.sqlite JOB_ID --expected-version 2 --state approved --reference "Fictional approval record"
python tracker.py status demo.sqlite JOB_ID --expected-version 3 --state scheduled --date 2026-12-01
python tracker.py edit demo.sqlite JOB_ID --expected-version 4 --input examples/edit.json
python tracker.py backup demo.sqlite backup-new
python tracker.py verify-backup backup-new
python tracker.py restore backup-new recovered-new.sqlite
python tracker.py export recovered-new.sqlite report-new
python tracker.py gui recovered-new.sqlite
```

`JOB_ID` is the actual `job-...` ID returned by `new`, not the literal placeholder.
The example versions apply to a **newly created job** with exactly those operations.
Read the current `version` with `show` before an edit, quote, decision, or status
change. Versions are mandatory positive integers. Every successful mutation
increments that job's version. See the [worked example](examples/WALKTHROUGH.md).

`init NEW.sqlite` creates an empty store. `edit` accepts any nonempty subset of
title/customer/contact/notes/follow_up. Job/quote JSON rejects extra and duplicate
fields, numeric amounts and invalid text. Inputs are at most 64 KiB.

## Limits and storage

- 200 jobs including archived, 50 quote revisions per job, 2,000 total revisions,
  10,000 activity entries, 128 MiB store/snapshot and 32 MiB report bounds.
- Amounts are integer cents: `0.00` through `9999999.99`. There are no line items,
  arithmetic totals, taxes, discounts, currency conversions, attachments or imports.
- There is no background synchronization, multi-user server, encryption, password
  system or tamper-proof audit. SQLite and local OS permissions protect ordinary
  operation; the file owner can alter or replace the database outside this app.
- Use trusted local paths and stable parents. Existing symlink/junction ancestors
  and UNC paths are rejected best effort. This is not a hostile-filesystem sandbox,
  race-proof path resolver or network/mapped-drive support guarantee. Do not open
  arbitrary databases received from strangers. Do not run concurrent app instances
  on a cloud-synchronized or network folder.
- Automatic schema migrations are not implemented. This release reads store schema
  1. Back up before updating; unsupported stores are refused.

At a record limit, retain a verified backup and start a separate new store.
There is no automated rollover or pruning. Standard SQLite files, exports and
backups can contain sensitive data; choose OS storage permissions accordingly.

## Test, contribute, suggest

```text
python -B source_check.py
python -B -m unittest discover -s tests -v
```

Tests use generated data in owned temporary folders. Set `TRACKER_REQUIRE_TK=1`
to make an unavailable desktop display a test failure; Linux CI runs under Xvfb.
See [validation](docs/VALIDATION.md), [provenance](docs/PROVENANCE.md),
[contributing](CONTRIBUTING.md), and [security reporting](SECURITY.md).

[Suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=job_quote_tracker_suggestion.yml)
or [report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=job_quote_tracker_bug.yml).
Fictional examples and small reproducible cases are welcome. Never attach a real
store, backup, customer export, approval record, credential or private project.
