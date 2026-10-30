# Downloadable OUTLANDS Toolkit

[Download Toolkit 0.9.0](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/toolkit-v0.9.0).
Frozen public source `75c65911953af8eb4319f734471dddc9ca256ccd` contains **110 tools and 17 systems**.
Application bytes remain exact; packaging and worked exercises have a separate pin.

| Package | Included primary components |
| --- | --- |
| Complete | All 127 components |
| Release and developer QA | 15 tools |
| File, backup and workflow | 9 tools |
| Document and media inspection | 10 tools |
| Android and Linux inspection | 13 tools |
| Desktop diagnostics | 7 tools |
| Local productivity applications | 4 tools |
| Data and AI tools | 50 tools |
| Game utilities | 2 tools |

## Source ZIP or bundled Windows app?

These nine source ZIPs contain no installed runtimes or dependencies. Supply the
Python, Node.js, PowerShell, .NET, Tk and optional dependencies required by each
module. [Separate Windows bundles](../docs/START-HERE.md) include their pinned
runtime where stated and retain their own versions, launchers and limits.
Systems belong to the complete ZIP; family packages retain their assigned tools,
shared methodology and guides. Cross-family guides may need the complete tree.

## Download and verify

Download the chosen ZIP and SHA256SUMS.txt from the same release. Verify the exact
filename before extracting into a fresh folder, then read START-HERE.md.

PowerShell: `Get-FileHash -Algorithm SHA256 ./outlands-complete-0.9.0.zip`.
Linux: `sha256sum --check --ignore-missing SHA256SUMS.txt`; confirm your chosen ZIP
is explicitly reported OK. Checksums establish consistency, not publisher identity.
PACKAGE-MANIFEST.json records exact members, sizes, hashes and both pins.

## Intake to reviewed evidence

Follow the [five-minute fictional exercise](../workshops/ingestion-evidence.md):

```text
python -B workshops/ingestion_evidence.py --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY
```

From the complete ZIP with Python 3.12/3.13 supplied separately, 23 original CLI
calls connect two batches, six rows, four accepted records and two duplicates.
Changed mapping, altered receipt pins and missing coverage require review.
Two trusted authored Python summary checks produce one match and one deliberate
mismatch. Complete failure evidence can be reviewed for nine private files while
the unmatched verdict remains. No actual import, authenticated receipt authority,
exactly-once processing, sandbox or publication permission is established.

## Setup and update planning exercises

Toolkit 0.6 adds Environment & Setup Workbench and Offline Release & Update
Workbench, and includes the merged [Corpus hardening in PR #52](https://github.com/TheOutlandsDev/outlands-public-tools/pull/52).
From the complete ZIP, use separately supplied Python 3.12/3.13 and a new absolute
private directory under an existing trusted parent outside the package:

```text
python -B workshops/lifecycle_exercises.py --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY
```

Expect two exercises and 53 original CLI calls. The [setup exercise](../workshops/environment-setup.md)
checks nine supplied declarations, three blocked then three ordered manual steps,
review refusal and a private handoff. The [update exercise](../workshops/release-update.md)
checks two copied four-file snapshots, exact differences, five blockers, scoped
approval, revocation and private evidence hashes. Inputs, copied snapshots and an
invented target sentinel stay unchanged. No actual setup, target update or recovery
is performed. Corpus fixture responses do not establish inference or model quality.

## Import and document exercises

Use the complete ZIP, Python 3.12/3.13, and a new absolute scratch directory whose
parent exists outside the package:

```text
python -B workshops/system_exercises.py --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

Expect two exercises and 33 CLI command checks:

- [Reviewed import](../workshops/import-migration.md): seven invented rows, three
  records, five provenance entries, two rejections. Missing rejection approval,
  repeats and conflicting keys are refused. Direct read-only SQLite checks verify
  actual values and preservation of the existing store and input bytes.
- [Pinned documents](../workshops/document-template.md): two revisions/previews/DOCX
  files, two item rows and total seven. Independent ZIP/XML checks verify wording,
  sections and values. An unreviewed build is refused and old output is preserved.
  Review generated pages in the intended viewer before use.

The runner refuses existing paths. Instances, stores, documents, reports and backups
remain private. Original methodology examples and eight family workshops are also
included; see [workshops](../workshops/README.md).


## Rebuild and qualification

From a committed checkout, choose new external directories:

```text
python -B -m unittest discover -s packages/tests -v
python -B packages/build.py --output NEW_EXTERNAL_PACKAGE_DIRECTORY
python -B packages/release_check.py --output NEW_EXTERNAL_PACKAGE_DIRECTORY
```

The 23 package tests cover 127-component inventory, original Git blob bytes,
checksums, tamper refusal, deterministic archives, fresh extraction, nine demos,
eight family workshops, three methodology examples and five system exercises.
Hosted Windows/Ubuntu qualification also runs all 80 original Chromium methods
for the retained four GUI workflows. Ubuntu renders both exact fictional DOCX
outputs with separately installed LibreOffice/Poppler. Visual review is recorded
separately. This does not certify every tool, real service, device, Word layout,
production workflow or separate-PC Explorer handoff.

### Qualification failure diagnostics

Hosted qualification prints the current component and stage before each CLI,
browser or rendering check. On a handled failure, the separate
`qualification-failure-OS-ATTEMPT` Actions artifact contains only `failure.json`:
an allowlisted component/stage, failure category, known failed check, numeric
exit code or timeout when applicable, and validated workflow identifiers.
It contains no child output, command arguments, paths, environment values or
tracebacks. Raw logs and partial timeout output stay in the private runner
workspace; hosted runner storage is temporary and is not a recovery archive.

The qualification step remains failed. Successful screenshots and summaries
are uploaded only by successful qualification, and failure receipts use a
separate artifact name for each run attempt. Earlier attempts stay visible in
Actions. No automatic retries, changed test counts or longer timeouts are added.
The receipt identifies the failed stage; it does not diagnose or fix its cause.
Setup failures before qualification and hard runner termination may have no
receipt; inspect the named Actions step in those cases.

For a local run, `packages/qualify_system_exercises.py --diagnostics` accepts a
new absolute directory with an existing parent, separate from the package,
workspace and successful-evidence directories. Review the receipt before sharing
it. The eight failure-injection tests run alongside the 23 package tests.

Toolkit 0.6.0 and earlier releases remain immutable. New work after this source
freeze stays pending until separately packaged. The release manifest/catalog
defines the archive even when retained documents describe other revisions.
See [release notes](RELEASE.md) and [review methodology](REVIEW.md).

## Fictional manufacturing review

Follow [the five-minute manufacturing review](../workshops/manufacturing-review.md) from the complete source ZIP with separately supplied Python 3.12/3.13. Twelve original CLI calls preserve four expected review outcomes: missing capability, combined capacity conflict, incomplete event history and a quantity mismatch. Individually eligible proposals still need combined capacity review. Revised declarations fit capacity two, account for 12 ticks as 9 active plus 3 held, and reconcile 20 + 5 - 3 - 1 = 21 pieces. Duplicate identities do not inflate results. Input and report hashes are recomputed, and prior diagnostics remain unchanged. Exercise PASS is a reproducibility result; operator review remains REQUIRED. No physical qualification, work assignment, scheduler, reservation update, inventory change, live clock or publication authority is established. Hosted qualification and fresh public-download verification both run this example on Windows and Linux. Earlier release evidence remains immutable.

## Fictional material-to-quality review

[Follow the 24-call exercise](../workshops/material-quality-review.md) with separately supplied Python 3.12/3.13 and the complete source ZIP. Four fictional kits require four motors and eight filters. Two labels overreserve the same canonical lot; incomplete coverage and failed measurements remain visible. Explicitly selected histories yield two first-pass good, one reworked good and one scrap, with exact fractions 1/2, 3/4 and 1/4. Thirteen expected REVIEW_REQUIRED outcomes remain retained. Input/report hashes and authored mappings are checked; existing scratch directories are refused unchanged. Exercise PASS means reproducibility; operator review remains REQUIRED. No physical stock, delivery, genealogy, inspection, repair, quality target or production authority is established. Hosted qualification and fresh public-download verification run this example on Windows and Linux.
