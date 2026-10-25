# Batch 7: verified transfers and server lifecycle planning

Prepared 2026-10-25 for the selected public source tree. This batch adds a reviewed-source packager, an opaque private file handoff mode, and an offline server-maintenance planner. It does not publish or configure a live server or application.

## Source review and selection

The security/lab source set included documentation checking, explicit-manifest source packaging, data handoff, and schema export helpers. The existing public documentation checker already covers common local Markdown links and JSON syntax, so the app-specific documentation helper was not copied. The schema exporter and its management/worker request contracts remain application-specific and private. The original data handoff depended on one manager's database schema, record IDs, artifact naming, and storage layout; those contracts were removed from the public design.

The server/game source set contains live operational configuration, data, plugin overlays, scheduler state, logs, and source mixed with third-party game content. Existing lifecycle scripts target a specific Windows server root and can invoke RCON, stop processes, install plugin overlays, update or restart services, and manage scheduled tasks. Those scripts, configs, records, plugin code and game assets were excluded.

The new `verified-transfers` module is a bounded, neutral implementation of two methods: copy only an exact source inventory after an external hash pin, or copy opaque private files into a new integrity-checked handoff. It does not carry application schemas, source mappings, server roots, endpoints, player records or third-party payloads. The new `server-maintenance` module is a pure planner that emits a checklist from operator-supplied observations; it contains no process, network, service, RCON, scheduler or game-specific control.

The selected original material is covered by the owner-selected MIT license. This is based on the owner's report of personal work and does not prove exclusive authorship of every private source. No game/plugin assets or vendor code are included.

## Validation

On Windows with Python 3.12.7, the combined selected-tool unittest run discovered 101 methods: 98 passed, 3 were skipped because native symlink/hard-link creation was unavailable, and none failed. Tests use synthetic disposable fixtures. Separate actual CLI checks passed for pinned source packaging and verification, private opaque backup/verification/restore, and an offline maintenance plan reporting `execution_performed: false`.

The documentation checker reviewed the repository's Markdown and JSON files. The offline release auditor inventoried 77 files before this review note was added; its 22 findings exactly matched the earlier reviewed tree, with no finding in either new tool, its documentation or the new test file. The retained result is `REVIEW_REQUIRED`, not an automatic clearance. Those prior findings remain bound to their exact source hashes in the private review record. The original application helpers, their tests, live server or server data were not executed.

## Limits and handling

- Source packaging accepts only an explicit, externally pinned inventory. It does not decide whether the selected source is private, proprietary, safe, or properly licensed. Review the exported contents and run [Public Release Audit](../tools/public-release-audit/README.md) before publication.
- Opaque handoff copies are private data. Their manifests retain relative filenames and content hashes; bundles may contain personal records, secrets or configuration. The tool does not encrypt, redact, anonymize or validate application state. The stopped-state flag is an operator assertion, not a process check.
- A bundle's internal checksum is not an authenticity proof. Restore requires a separately recorded manifest digest and writes only to a new destination.
- Maintenance and readiness results rely on facts supplied by the operator. `OBSERVATIONS_COMPLETE` means the required fields were supplied as true; the tool does not independently check them.
- Windows reparse/alternate-stream handling beyond the synthetic cases, network shares, hostile concurrent writers, Linux acceptance, application-specific backups and live service behavior remain unverified.
- This review covers only the exact selected source tree. It does not clear the rest of the drive or any unselected project.
