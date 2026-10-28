# Operations Analytics & Scenario Workbench

The [Operations Analytics Workbench](../systems/operations-analytics-workbench/README.md)
is one complete local application for capacity/coverage, process/cycle analytics,
inventory proposals, declared dispatch and snapshot/completion reconciliation.
It includes forms, JSON editing, immutable scenarios, comparison, review, CLI,
private reports, local mail drafts and SQLite backups.

This batch uses fresh standard-library implementation and invented fixtures,
with unchanged public MIT native I/O helpers and an adapted public instance/
HTTP/packaging pattern. A reviewed educational design informed the scope; its
unlicensed code and generated artifacts are not copied. No original customer/
employer source, policies, schemas, configurations, records, endpoints, credentials,
database, workbook, deployment code, model or asset is selected.

The fictional example independently supports 201 units of capacity, minimum
headcount three under its assumptions, OEE 0.5625, cycle P90 7.1 minutes, an
18-unit reorder proposal, two eligible/two blocked candidates and 25→33 completed
units without duplicate replay. All calculations remain advisory declarations.

The optional planning importer verifies the companion report's exact inventory,
hashes and reconciled totals. It stores a receipt and totals without converting
planning stages/readiness into dispatch decisions or opening a planning database.
The apps retain separate private instances.

Validation targets Windows/Ubuntu Python 3.12/3.13 with required native guards,
independent arithmetic, transaction/restart/refusal tests, complete fictional
workflow, deterministic source ZIPs and document checks. See
[validation and limits](../systems/operations-analytics-workbench/docs/VALIDATION.md).
Interactive browser automation could not initialize locally, so full browser
acceptance remains unverified. Runtime state and audit ledgers remain private;
this does not clear other source families or earlier operating systems.
