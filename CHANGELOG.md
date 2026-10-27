# Changelog

## Unreleased

- Add Offline Record Ingestion: bounded in-memory CSV/JSONL validation, normalization, duplicate/conflict review and an explicit clean-batch gate, with fictional examples and design notes.

- Harden Environment Contract Checker control/report I/O on Windows/POSIX, preserving schemas, prerequisite rules, metadata-only targets and report bytes; retain missing-root reporting and unconfirmed new reports.

- Harden Verified Transfers source packaging/verification and shared I/O on Windows/POSIX, preserving formats, hash pins, source filters, stopped assertions and no-overwrite behavior; verify new files and retain unconfirmed output.

- Harden Release Preflight file/directory and new-report handling on Windows/POSIX, preserving external pins, manifest/launcher rules, report bytes and plan-only decisions.

- Harden Server Maintenance Planner input reads on Windows/POSIX while preserving lifecycle, readiness, calendar and JSON rules; add fictional platform tests and fixed Windows interruption/help behavior.

- Harden Dataset Review store/schema acceptance with guarded file initialization,
  canonical legacy-format validation, read-only preflight and explicit refusal
  of WAL/sidecar/custom-schema states; preserve record and review rules.
- Harden Dataset Review JSONL import/export with checked reads and exclusive
  verified writes on Windows/POSIX, preserving review rules and SQLite connection/
  schema behavior; document retained unconfirmed output and lifecycle limits.
- Harden Python Helpers file input with bounded ordinary-file/identity checks
  on Windows/POSIX, preserving JSON parsing, limits and the redactor/key set.
  Document stricter path rules, fixed errors and redaction limitations.
- Harden Documentation Check with actual bounded reads and directory collection,
  native Windows metadata/target checks and generated failure fixtures, while
  preserving Markdown/JSON rules, exclusions and POSIX link protections.
- Harden Project Workspace Windows input, directory and exclusive output I/O,
  preserving POSIX/plan behavior and adding generated native failure fixtures.
  Document private/unconfirmed outputs, stream scope and permissions limits.
- Harden Public Release Audit Windows paths, bounded reads and exclusive
  outputs while retaining the detector and POSIX export/report implementation.
  Bound JSON controls on both platforms and document private filename metadata.
- Harden Source Inventory Windows paths, directory enumeration, native file
  identity and exclusive output, preserving POSIX/report/classifier contracts.
  Add generated native fixtures and explicit partial/unconfirmed output limits.
- Harden Keep Awake's thread ownership, fixed error categories and Tk callback,
  timer and cleanup failure handling. Keep self-test checks active under `-O`.
  Add opt-in native Windows request/Tk fixtures and Windows/Ubuntu CI.
- Harden Safe File Mover's Windows CLI/engine path, journal, reservation and
  named-stream checks; add native disposable recovery/restore/purge fixtures.
  Preserve Linux protections, managed hard-link recovery and no-replace commits.
- Harden Document Builder Windows input/output with retained native handles and
  exclusive creation while preserving parsing, layout and Linux I/O bodies.
  Add fictional DOCX package/metadata checks and correct stale licensing text.
- Add XML Recipe Inspector Windows native input and new-directory report output,
  preserving POSIX I/O bodies, XML limits, entity rejection and CSV shielding.
  Document inherited ACLs, directory creation/open gap and retained failed exports.
- Add Windows native input checks and exclusive new-file output to Dependency
  Lock Tools, preserving the POSIX bodies and strict report/lock parsers.
  Document inherited Windows ACLs and retained partial/unconfirmed outputs.
- Add a native Windows backend to Package Layout Checker, with retained ancestor
  handles, reparse/hardlink/alias refusal, bounded reads and fixed findings.
  Preserve the POSIX descriptor implementation and its 33 original tests.
  Add fictional Windows fixtures and a Windows/Ubuntu Python 3.12/3.13 CI matrix.
- Add Offline Dependency Lock Diff for two locks in the existing narrow format.
  Compare declarations, version text and hashes without package operations,
  semantic version ranking, environment inspection or advisory checks.
- Add Offline Source Inventory Diff for two saved CSV/summary report pairs.
  Validate captured bytes and totals; classify exact-path records, flag coverage
  uncertainty and group hash/size hints without body rescans or rename/deletion claims.
- Add Offline Workflow Plan Checker for declared task prerequisites and states.
  Missing/cyclic links and inconsistent active/completion claims withhold all
  order/next-step lists. No task execution, state mutation or authorization.
- Add Offline Backup Chain Checker for declared full/incremental dependencies,
  cycles, series/sequence consistency and selected ancestry. It checks metadata
  only, with no backup-content reads, restore/deletion actions or authorization.
- Add Offline Assessment Workbench with an empty private SQLite store, explicit
  fictional demo, guided desktop/CLI editing, version-checked atomic saves,
  retained history and new-only validated imports, exports and logical clones.
- Reject unsupported WAL stores before SQLite opens them; canonicalize Windows
  database names and protect checkout and SQLite sidecar boundaries.
- Add Offline Evaluation Metrics Calculator for bounded declared confusion
  counts. Ratios preserve exact formula counts, zero denominators are explicit,
  and F1 is computed independently from precision/recall availability.
  No model, corpus, prompt, response or individual record is loaded or executed.
- Add Offline Assessment Record Contract Checker for neutral submissions,
  findings and retest summaries. Broken dependencies block claims; explicit
  pending/closure selections must use the highest declared series revision.
  It performs no tests and verifies no authorization, isolation or outcomes.
- Add Backup Retention Planner for operator-declared independent full snapshots.
  It preserves timestamp ties, protects future records without consuming the
  normal latest-count baseline, and marks other records for human review.
  It never scans, copies, restores or deletes backups, or authorizes deletion.
- Add Offline Configuration Contract Checker for bounded flat JSON settings,
  with strict types, declared constraints, integer ordering and redacted results.
  Missing or invalid dependencies block rules; settings are never changed.
- Add a neutral Diagnostic Evidence Plan methodology template with fictional
  examples separating declarations, operator assertions and runtime evidence.
- Add Connection Plan Checker: strict loopback binding declarations and
  conflict groups with fixed result fields. It never probes ports, inspects
  listeners, generates commands, installs rules or writes report files.
- Add Environment Contract Checker: explicitly selected prerequisite metadata,
  fixed result fields, unverified operator observations, external new-file
  reports and disposable fictional examples. No target execution or installation.
- Add fictional privacy, schema, metadata and report-boundary regression tests
  with Windows/Ubuntu Python 3.12/3.13 CI.

## 0.1.0 — 2026-10-25

- Curate the selected development utilities, neutral methodology, dataset
  review core, and three generic applications into one source collection.
- Add externally pinned release verification, selected-file update planning,
  static launcher checks and recovery guidance through Release Preflight.
- Include Offline ELF Inspector for conservative local metadata/dependency
  review without executing the inspected inputs.
- Review every current-source pattern finding, retain required upstream legal
  notices, and use the owner-selected TheOutlandsDev copyright identity.
- Add a release guide and exact source/checksum assets. Private configuration,
  operational records, original data and third-party runtime assets are excluded.
- Record validation limits for each component; historical test evidence is
  distinguished from the current collection regression and GitHub workflow.
