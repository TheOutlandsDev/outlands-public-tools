<p align="center"><img src="https://raw.githubusercontent.com/TheOutlandsDev/TheOutlandsDev/main/assets/outlands-dev-lab.svg" alt="OUTLANDS Dev Lab — tools, games and systems" width="100%"></p>

<p align="center">
  <a href="https://github.com/TheOutlandsDev">OUTLANDS profile</a> ·
  <a href="https://github.com/TheOutlandsDev/outlands-public-tools">Public Tools</a> ·
  <a href="https://github.com/TheOutlandsDev/outlands-game-tools">Game Tools</a> ·
  <a href="https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/PROJECT-MAP.md">Project map</a>
</p>

# OUTLANDS | Public Tools and Methods

**[Download Toolkit 0.6.0](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/toolkit-v0.6.0)**
— complete source or eight tool-family packages, covering 79 components: 62 tools and 17 systems
at a fixed revision. Start with the [download guide](packages/README.md) and
[three worked methodology examples](methodology/worked-examples/README.md),
[eight family workshops](workshops/README.md) and the [shared catalog](catalog/generated/INDEX.md).

New modular source tools: [workbook/CSV intake](tools/workbook-intake-checker/README.md), [snapshot checks](tools/snapshot-contract-checker/README.md), [workflow XML](tools/xml-workflow-checker/README.md) and [planner handoff](tools/planner-handoff-checker/README.md). These are source-only additions; the fixed Toolkit download above is unchanged.

New document source tools: [DOCX tables](tools/docx-table-extractor/README.md), [document intake](tools/document-intake-checker/README.md), [tabular reconciliation](tools/tabular-reconciliation-checker/README.md) and [document content diff](tools/document-content-diff/README.md). These independent additions are pending packaging.

New notification source tools: [literal templates](tools/message-template-renderer/README.md), [envelope checks](tools/message-envelope-checker/README.md), [EML/MIME inspection](tools/eml-mime-inspector/README.md) and [delivery evidence](tools/delivery-evidence-reconciler/README.md). Independent offline modules with fictional examples; no sending/provider adapter. Packaging deferred.

Reusable development utilities and neutral engineering/assessment methods. Use the [catalog](docs/CATALOG.md) for compatibility and validation boundaries, [methodology](methodology/README.md) for workflow templates, and [systems roadmap](systems/README.md) for larger application candidates. The small Python utilities are mostly standard-library programs; Document Builder uses python-docx. Larger applications below declare their own dependencies. Optional Python desktops need Tk/Tcl. Read each tool's platform and validation limits.

The [current source review](docs/PUBLIC-SOURCE-REVIEW-2026-10-25.md) records the
owner-attribution correction, retained upstream notices, scanner dispositions,
and the limits of this selected-source review.

For a curated download, runtime choices and checksum instructions, use the
[release guide](docs/RELEASE-GUIDE.md) and [changelog](CHANGELOG.md).

<!-- START-HERE:BEGIN -->
## Choose a tool for your task

Start with one focused download and its fictional exercise. Windows downloads marked Python included or Node included supply that runtime. Source ZIPs need the runtime documented in their guide.

| Your task | Start with | Follow the exercise |
| --- | --- | --- |
| Manufacturing and reporting | [Workfloor for Windows](https://github.com/TheOutlandsDev/workfloor/releases/download/windows-v0.4.1-1/workfloor-0.4.1-windows-x64.zip) / [Cross-platform source ZIP](https://github.com/TheOutlandsDev/workfloor/releases/download/v0.4.1/workfloor-0.4.1.zip) / [Source setup guide](https://github.com/TheOutlandsDev/workfloor/blob/v0.4.1/README.md#start-here) | [Requirements, expected result and limits](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/START-HERE.md#manufacturing) |
| Build a local website | [Local Site Builder for Windows](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-site-builder-windows-v1.0.2-2/local-site-builder-1.0.2-windows-x64.zip) / [Cross-platform source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-site-builder-v1.0.2/local-site-builder-1.0.2.zip) / [Source setup guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/local-site-builder-v1.0.2/tools/local-site-builder/START-HERE.md) | [Requirements, expected result and limits](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/START-HERE.md#local-website) |
| Inspect and validate code | [Developer Workspace for Windows](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/developer-workspace-windows-v0.1.1-1/developer-workspace-0.1.1-windows-x64.zip) / [Cross-platform source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/developer-workspace-v0.1.1/developer-workspace-0.1.1.zip) / [Source setup guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/developer-workspace-v0.1.1/downloads/workbenches/developer-workspace/START-HERE.md) | [Requirements, expected result and limits](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/START-HERE.md#source-review) |

[Read the complete starting guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/START-HERE.md) · [Portfolio guide](https://connor-oshea-outlands.thatrobotguy.chatgpt.site/#start-here)
<!-- START-HERE:END -->

**Lifecycle exercises:** [Setup declarations](https://github.com/TheOutlandsDev/outlands-public-tools/blob/toolkit-v0.6.0/workshops/environment-setup.md) · [Import and document validation](https://github.com/TheOutlandsDev/outlands-public-tools/blob/toolkit-v0.6.0/workshops/README.md) · [Update planning](https://github.com/TheOutlandsDev/outlands-public-tools/blob/toolkit-v0.6.0/workshops/release-update.md). Invented inputs, observed checks and explicit limits; no real setup or target update is performed.

**Setup review on Windows:** [Download Environment & Setup Workbench with Python included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/environment-setup-workbench-windows-v0.1.0-1). Extract All, open **Setup Demo.cmd**, then follow the [five-minute fictional exercise](downloads/windows/environment-setup-workbench/FIVE-MINUTE.txt). Nine supplied checks, three blocked steps before and zero after a changed declaration, review refusal and a six-file private handoff. **Setup Exercise.cmd** performs the 19-command companion. All real setup and manual runtime verification remain unperformed. [Recorded Windows walkthrough](https://connor-oshea-outlands.thatrobotguy.chatgpt.site/#setup-exercise).

**Update review on Windows:** [Download Release & Update Workbench with Python included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/release-update-workbench-windows-v0.1.0-1). Extract All, open **Update Demo.cmd**, then follow the [five-minute fictional exercise](downloads/windows/release-update-workbench/FIVE-MINUTE.txt). Compare two copied packages, retain five blockers, review one exact plan, create an eight-file private handoff and revoke future exports. A new plan inherits no approval; saved revocation reopens after shutdown. **Update Exercise.cmd** performs the 34-command companion. Target changes and recovery remain unperformed. [Recorded Windows captures and acceptance](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/release-update-workbench-windows-v0.1.0-1).

**Data jobs on Windows:** [Download Data & Services Stack with Python included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/data-services-stack-windows-v0.2.0-1). Extract All and open **Data Services Demo.cmd**, then follow the [five-minute fictional exercise](downloads/windows/data-services-stack/FIVE-MINUTE.txt). Preview six invented records, inspect predictions 10/10/10 and MAE/RMSE 4, review a three-file private report and retain fake retry/uncertain outcomes across restart. **Data Services Exercise.cmd** performs 22 original CLI checks. Real delivery and useful real-data forecast accuracy remain unverified. [Recorded Windows captures and acceptance](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/data-services-stack-windows-v0.2.0-1).

**Production planning on Windows:** [Download Production Planning & Operations Workbench with Python and pinned dependencies included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/production-planning-workbench-windows-v0.1.1-1). Extract All and open **Planning Demo.cmd**, then follow the [five-minute fictional exercise](downloads/windows/production-planning-workbench/FIVE-MINUTE.txt). Explain 160 = 25 assigned dock + 85 WIP + 50 uncovered, save a revised 170-unit plan, compare two five-file private reports and reopen revision history. **Planning Exercise.cmd** performs 14 original CLI calls with independent arithmetic, report hashes, SQLite integrity and stale-write refusals. Plans and local review cannot start production, reserve identities or authorize shipment. [Recorded Windows captures and acceptance](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/production-planning-workbench-windows-v0.1.1-1).

**Connected analytics on Windows:** [Download Operations Analytics & Scenario Workbench with Python included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/operations-analytics-workbench-windows-v0.1.1-1). Extract All and open **Analytics Demo.cmd**, then follow the [five-minute fictional Planning-to-Analytics exercise](downloads/windows/operations-analytics-workbench/FIVE-MINUTE.txt). Attach a checked five-file Planning report with 160 = 25 + 85 + 50, ingest 25 -> 33 completed units, replay without another event or revision, retain three revisions and export eight-file private reports. **Analytics Exercise.cmd** performs 20 original CLI calls with arithmetic, hashes, SQLite integrity and refusal checks. Planning references do not map eligibility or completions; no production, purchasing or mail is executed. [Actual Windows captures and acceptance](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/operations-analytics-workbench-windows-v0.1.1-1).

**Visual annotation on Windows:** [Download Visual Dataset & Annotation Workbench with Python included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/visual-annotation-workbench-windows-v0.1.0-1). Extract All and open **Visual Demo.cmd**, then follow the [five-minute generated-image exercise](downloads/windows/visual-annotation-workbench/FIVE-MINUTE.txt). Draw a region, save immutable corrections, review one exact version and export checked masks while keeping a test specimen out of training. **Visual Exercise.cmd** performs 25 original CLI calls with independent pixel, hash, review, split, backup-integrity and reopen checks. No real images, model training or inference are supplied. [Actual Windows captures and acceptance](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/visual-annotation-workbench-windows-v0.1.0-1).

**Offline ML on Windows:** [Download ML Experiment & Evaluation Workbench with Python included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/ml-experiment-workbench-windows-v0.1.0-1). Extract All and open **ML Demo.cmd**, then follow the [five-minute fictional training/evaluation exercise](downloads/windows/ml-experiment-workbench/FIVE-MINUTE.txt). Inspect training-only preprocessing, validation threshold selection, separate test evaluation and artifact-specific review before an eight-file private export. **ML Exercise.cmd** performs 29 original CLI calls with independent prediction/metric arithmetic, report hashes, backup integrity and reopen checks. Generated-task results do not establish real-world accuracy or calibration. [Actual Windows captures and acceptance](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/ml-experiment-workbench-windows-v0.1.0-1).

## Try a focused workbench

**[SQL Report Workbench for Windows: Python included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/sql-report-workbench-windows-v0.1.1-1).** Extract All and double-click **SQL Report Demo.cmd**. Run the saved query for 8/11, change the minimum binding to 4 for 5/11, then review/export and reopen the saved result. [Windows first run](downloads/windows/sql-report-workbench/START-HERE.txt) · [Recovery, source/runtime pins and qualification](downloads/windows/sql-report-workbench/RELEASE.md). Demo and blank workspaces are separate, outside the app; state-only backups omit snapshots and exports. The existing source downloads below remain unchanged.

**[Developer Workspace for Windows: Python included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/developer-workspace-windows-v0.1.1-1).** Extract All, double-click **Developer Demo.cmd**, then choose **sample-project**. Validate five invented files, save a changed revision and compare it; an approved historical export preserves the original source. [Windows first run](downloads/windows/developer-workspace/START-HERE.txt) · [Nonexecution, private storage and recovery limits](downloads/windows/developer-workspace/RELEASE.md). Separate blank/demo workspaces persist outside the app.

- **[SQL Report Workbench package 0.1.1](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/sql-report-workbench-v0.1.1)** — parameterized SQL over invented datasets, saved query/report definitions, checked results and private exports. [Quick start](downloads/workbenches/sql-report-workbench/START-HERE.md) · [Methodology](downloads/workbenches/sql-report-workbench/PROVENANCE.md).
- **[Developer Workspace package 0.1.1](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/developer-workspace-v0.1.1)** — immutable text-project revisions, nonexecuting syntax checks, comparison and reviewed historical source exports. [Quick start](downloads/workbenches/developer-workspace/START-HERE.md) · [Methodology](downloads/workbenches/developer-workspace/PROVENANCE.md).

Both require Python 3.12/3.13 and SQLite; application use needs no pip packages or
external service. The ZIP adds an outer START-HERE.md around unchanged application
source declaring 0.1.0. [Try the original fictional workflows](https://connor-oshea-outlands.thatrobotguy.chatgpt.site/#workbench-downloads).
Fresh-ZIP acceptance checks the original source pins, core suites, independent
results/exports, persisted CLI reopen and real Chromium workflows on Windows/Ubuntu.
Keep future user inputs and generated instances private.

## Featured application: Local Site Builder

Edit a fictional website privately, publish when ready, then verify and restore
a stopped-site backup into a new directory. This Node.js/SQLite application has
a focused source download, actual interface captures and a complete browser/CLI
acceptance workflow alongside its 32 integration tests.

[Download 1.0.2](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/local-site-builder-v1.0.2)
· [Source and quick start](tools/local-site-builder/README.md)
· [60-second walkthrough](https://connor-oshea-outlands.thatrobotguy.chatgpt.site/#local-site-builder-walkthrough)
· [Validation and limits](tools/local-site-builder/docs/VALIDATION.md)

## Try a dashboard first

[Resource Monitor](tools/resource-monitor/README.md) is a small way to explore
the collection without a game, account or third-party Python package. Its
built-in demo supplies fictional CPU, memory and network samples to the actual
dashboard.

![Actual Resource Monitor dashboard in FICTIONAL DEMO mode, showing synthetic CPU, memory and network metrics](https://raw.githubusercontent.com/TheOutlandsDev/TheOutlandsDev/main/assets/resource-monitor-demo.png)

*Actual Resource Monitor built-in **FICTIONAL DEMO**, using synthetic metrics.
No machine metrics were read. See the [screenshot provenance and capture
scope](https://github.com/TheOutlandsDev/TheOutlandsDev/blob/main/assets/SHOWCASE.md).*

**Windows 11 x64:** [Download Resource Monitor with Python included](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/resource-monitor-windows-v0.1.1-1/resource-monitor-0.1.1-windows-x64.zip),
Extract All, then double-click **Resource Monitor.cmd** for fictional samples.
Use **Resource Monitor Live.cmd** only to opt into actual aggregate metrics;
the pinned native dependency is included. [Windows first run and limits](downloads/windows/resource-monitor/START-HERE.txt)
· [Runtime/dependency pins and qualification](downloads/windows/resource-monitor/RELEASE.md).
Pause freezes the tab, not sampling. Download JSON/CSV deliberately; restarting
resets history and the session token, while saved files remain. Exports are not
imported or auto-restored. Keep real reports and token URLs private.

**Source alternative:** [Original source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/resource-monitor-v0.1.1/resource-monitor-0.1.1.zip)
with Python 3.12/3.13. The commands below retain that separate source workflow.

From the repository root, with Python **3.12 or 3.13** selected as `python`:

```text
cd tools/resource-monitor
python -m resource_monitor demo
python -m resource_monitor serve --demo --port 0 --duration 120
```

The first Python command prints fictional samples. The second starts a local
loopback dashboard for up to two minutes; open the complete local URL printed
by the server. Press **Ctrl+C** to stop it sooner. Demo mode reads no machine
metrics and needs no additional packages. See the [Resource Monitor
guide](tools/resource-monitor/README.md) for live-mode requirements and the
separate validation scope.

### Requirements at a glance

| Starting point | Requirements | Setup details |
| --- | --- | --- |
| Resource Monitor demo | Windows portable ZIP includes Python; separate source needs Python 3.12/3.13. | [Demo and dashboard guide](tools/resource-monitor/README.md) |
| Python utilities and other apps | Use each module's documented Python version, platform and dependencies; many small utilities use the standard library. | [Tool catalog](docs/CATALOG.md) · [Application list](#applications-in-this-collection) |
| Local Site Builder | Windows portable ZIP includes Node and dependencies; separate source needs Node 24/npm. | [Site Builder setup](tools/local-site-builder/README.md) |
| Portfolio Builder | Python 3.12/3.13 and pinned PDF dependencies; optional Tk/Tcl for the desktop editor. | [Portfolio Builder setup](tools/portfolio-builder/README.md) |

## Choose your starting point

| I want to… | Start here |
| --- | --- |
| Build a local site or portfolio | [Local Site Builder](tools/local-site-builder/README.md) · [Portfolio Builder](tools/portfolio-builder/README.md) |
| Track work, quotes and follow-ups | [Job & Quote Tracker](tools/job-quote-tracker/README.md) |
| Inspect source, packages or dependencies | [Tool catalog](docs/CATALOG.md) |
| Review engineering examples and evidence | [Skills map](docs/SKILLS-MAP.md) · [Source review](docs/PUBLIC-SOURCE-REVIEW-2026-10-25.md) |
| Find another OUTLANDS project | [Public project map](docs/PROJECT-MAP.md) |

**Maintained application home:** use this collection's Site Builder and Portfolio Builder folders for current additions and support. Their earlier standalone repositories preserve project history.

## Developer utilities

| Tool | Purpose | Documentation |
| --- | --- | --- |
| Dependency Lock Tools | Convert a supported pip JSON report to sorted name/version/SHA-256 requirements and validate that limited lock format offline. | [Usage, format and limits](tools/dependency-lock-tools/README.md) |
| Offline Dependency Lock Diff | Compare two supported locks by package declaration, version text and hash without downloads, installs or upgrade-direction inference. | [Fictional locks, comparison and limits](tools/dependency-lock-diff/README.md) |
| Package Layout Checker | Check caller-declared files, optional Python syntax and case-insensitive literal markers without importing the selected package. | [Usage, examples and limits](tools/package-layout-checker/README.md) |
| Source Inventory | Hash an explicitly selected bounded tree and write private reports, with optional folder trees, exclusions and native Windows checks. | [Usage, reports and limits](tools/source-inventory/README.md) |
| Offline Source Inventory Diff | Compare two saved inventory reports, separate metadata changes from coverage uncertainty, and group reported hash/size hints without rescanning sources. | [Fictional reports, comparison and limits](tools/source-inventory-diff/README.md) |
| XML Recipe Inspector | Summarize operator-supplied unnamespaced recipe XML using retained schema conventions and bounded parsing. | [Usage, schema and limits](tools/xml-recipe-inspector/README.md) |
| Markdown Document Builder | Convert an explicitly selected Markdown subset into a fresh DOCX with styled headings/tables and neutral core properties. | [Usage, dependency and metadata limits](tools/document-builders/README.md) |
| Safe File Mover | Copy, hash-verify and commit without replacement, with a local journal and retained recovery copy by default. Move/purge actions change files. | [Disposable preview, recovery and limits](tools/safe-file-mover/README.md) |
| Keep Awake | Request Windows system/display wakefulness, with console or animated Tk mode and bounded native lifecycle checks. | [Usage, cleanup and native-test limits](tools/keep-awake/README.md) |
| Public Release Audit | Inspect bounded text exports and exact inventories, with unchanged detectors and native Windows file checks. | [Scope and limitations](tools/public-release-audit/README.md) |
| Project Workspace | Plan or create a fresh private workspace with verified opaque input copies and native Windows creation checks. | [Usage, privacy and limits](tools/project-workspace/README.md) |
| Documentation Check | Check common local Markdown links and JSON syntax with bounded reads/enumeration and native Windows metadata checks. | [Grammar, filesystem and coverage limits](tools/documentation-check/README.md) |
| Python Helpers | Load JSON objects through checked bounded file reads and redact selected sensitive keys in nested data. | [API, filesystem and redaction limits](tools/python-helpers/README.md) |
| Verified Source Packages and Private Data Handoffs | Copy a reviewed, hash-pinned source inventory or private opaque snapshot through guarded Windows/POSIX I/O into new destinations. | [Scope, use and privacy limits](tools/verified-transfers/README.md) |
| Server Maintenance Planner | Calculate calendar windows and return offline lifecycle/readiness checklists from operator-supplied observations, with guarded Windows/POSIX input reads. | [Input contract and execution limits](tools/server-maintenance/README.md) |
| Release Preflight | Verify a pinned local component inventory, plan additions/replacements, and check a launcher specification with guarded Windows/POSIX I/O and no input execution. | [Examples, format and recovery limits](tools/release-preflight/README.md) |
| Environment Contract Checker | Check declared prerequisite metadata without reading/executing targets; keep operator observations unverified, with guarded Windows/POSIX control/report I/O. | [Fictional examples, privacy and limits](tools/environment-contract-checker/README.md) |
| Connection Plan Checker | Validate declared loopback bindings and identify repeated transport/address/port claims without contacting hosts or inspecting listeners. | [Fictional plans, privacy and limits](tools/connection-plan-checker/README.md) |
| Offline Configuration Contract Checker | Validate flat JSON settings against declared types, bounds, choices and integer ordering rules, with no configuration changes or runtime probes. | [Fictional settings, contract format and privacy](tools/configuration-contract-checker/README.md) |
| Backup Retention Planner | Calculate advisory count/age/pin protections for declared independent full snapshots, with no backup scan or deletion authorization. | [Fictional plans, policy and limits](tools/backup-retention-planner/README.md) |
| Offline Backup Chain Checker | Check declared full/incremental parent relationships and selected dependency order, with no backup-content access or restore/deletion actions. | [Fictional chains, contract and limits](tools/backup-chain-checker/README.md) |
| Offline Workflow Plan Checker | Check declared task prerequisites/states and return an order and eligible IDs only for consistent plans, without executing tasks. | [Fictional workflows, contract and limits](tools/workflow-plan-checker/README.md) |
| Offline Assessment Record Contract Checker | Check neutral submission, finding and retest relationships and declared workflow consistency without inspecting evidence or testing targets. | [Fictional records, schema and limits](tools/assessment-record-checker/README.md) |
| Offline Evaluation Metrics Calculator | Calculate exact accuracy, precision, recall and F1 from declared single-label confusion counts, with explicit undefined ratios and no model execution. | [Fictional counts, formulas and privacy](tools/evaluation-metrics-calculator/README.md) |
| Offline ELF Dependency Inspector | Inspect local Linux/Android ELF metadata; report candidate libraries, ambiguity, architecture mismatches and coverage issues without running binaries. | [Instructions, examples and limits](tools/offline-elf-inspector/README.md) |

## Applications in this collection

Use this repository as the shared home for new original public applications.
Each application has its own folder, license notices, detailed instructions,
fictional examples, tests and source manifest. Run commands from its folder.

| Application | Useful for | Start here |
| --- | --- | --- |
| Local Site Builder | Edit a small website locally with templates, drafts, images, publishing, backups and static export. | [Instructions and examples](tools/local-site-builder/README.md) |
| Portfolio Builder | Build a portfolio site and PDF from your own structured content and evidence. | [Instructions and examples](tools/portfolio-builder/README.md) |
| Job & Quote Tracker | Keep persistent jobs, quote revisions, decision references, follow-ups and schedules; export reports and verify recovery. | [Instructions and examples](tools/job-quote-tracker/README.md) |
| Offline Assessment Workbench | Edit neutral submission/finding/retest drafts in a private store, preserve history, validate links and import/export or clone to new destinations. | [Desktop, CLI and fictional walkthrough](tools/assessment-workbench/README.md) |
| Friendlies — experimental SPT source | Solo companion prototype with guarded activation receipts and formation presets. Gameplay unverified; disabled by default; Fika blocked. | [Source build, fixtures and pending raid plan](tools/friendlies/README.md) |
| Steven Chat (Stephen) | Terminal chat with a separately supplied local Ollama model, bounded conversation context and optional session files. | [Setup, demo, examples and limits](tools/steven-chat/README.md) |
| App Affinity Launcher | Preview or launch a selected Windows executable with verified CPU affinity and normal priority. | [Setup, disposable examples and limits](tools/app-affinity-launcher/README.md) |
| Resource Monitor | View local CPU, memory and aggregate network metrics through a Python API and browser dashboard; demo and live modes are explicit. | [Dashboard, API, examples and limits](tools/resource-monitor/README.md) |
| Hash Journal | Create and verify bounded hash-chained event records, with fresh snapshot writes and optional externally trusted anchors. | [Format, commands, tests and limits](tools/hash-journal/README.md) |

Local Site Builder requires Node 24 and pinned npm packages. Portfolio Builder
uses Python 3.12/3.13 and its pinned PDF dependencies. Job & Quote Tracker needs
only Python 3.12/3.13, plus Tk for its desktop. Their MIT source does not relicense
dependencies or your input data. Keep generated sites, portfolios, stores,
customer reports, evidence, credentials and backups private.

Offline Assessment Workbench uses Python 3.12/3.13, SQLite and optional Tk from
the installed Python runtime. Start empty or choose its explicit fictional demo;
real stores, journals, history, exports and recovery copies remain private.

[Report bugs or suggest improvements](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Select the application's form and use fictional examples. Earlier standalone
Site Builder and Portfolio Builder repositories remain available as history;
their collection folders are the home for these additions and support links.
See [the application review](docs/APPLICATIONS-2026-10-25.md) for test scope and
consolidation details.

See the [engineering skills map](docs/SKILLS-MAP.md) for the languages, implementation boundaries, examples and verification evidence represented by the collection.

## Archive policy and compiled metadata tools

| Tool | Use | Instructions and examples |
| --- | --- | --- |
| ZIP Package Policy Verifier (PowerShell 7.2+) | Check a bounded ZIP against an explicit member, hash and literal-text policy without extraction. | [Commands, generated examples and limits](tools/zip-package-policy/README.md) |
| .NET Public API Diff (C# / .NET 8) | Compare supported public declarations in trusted managed build artifacts without loading their code. | [Build, comparison examples and coverage](tools/dotnet-api-diff/README.md) |
| ELF Runtime Reference Hints (Python) | Optionally identify bounded string-derived library/path hints separately from declared ELF dependencies. | [Offline inspector and optional hints](tools/offline-elf-inspector/README.md) |

These tools inspect selected local files. A policy match, API difference or string
hint is limited evidence; read the coverage and provenance notes before drawing
compatibility, authenticity or runtime conclusions. Suggestions and fictional
reproductions are welcome through the [issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).

## Saved media evidence and inventory rules

| Tool | Use | Instructions and examples |
| --- | --- | --- |
| FFmpeg Capture Log Inspector (PowerShell 7.2+) | Summarize supported saved progress records and error markers without invoking FFmpeg or a capture device. | [Commands, fictional logs and coverage](tools/ffmpeg-log-inspector/README.md) |
| VPD Media Reference Checker (Python) | Inspect the supported VideoProc Vlogger JSON subset and optionally check explicitly mapped local copies using metadata only. | [Project subset, generated examples and limits](tools/vpd-reference-checker/README.md) |
| Source Inventory Rule Classifier (Python) | Group a previously generated inventory using ordered literal rules, with overlap and unmatched reports. | [Classification commands and rule format](tools/source-inventory/README.md) |

These are reusable implementations of local helper mechanisms. Log observations,
declared project references, local availability metadata and user-written categories
are separate evidence types. Read each tool's coverage and provenance notes.
Suggestions and fictional reproductions are welcome through the
[issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).

## Git worktrees and document asset QA

| Tool | Use | Instructions and examples |
| --- | --- | --- |
| Git Worktree Review Reporter | Report local status and stored branch relationships for an explicitly selected trusted repository, using an isolated Git policy. | [Setup, generated repositories and coverage](tools/git-worktree-reporter/README.md) |
| PDF Text Bounds Inspector | Compare observed glyph boxes with selected PDF page bounds in trusted completed documents. | [Geometry, generated PDFs and limits](tools/pdf-text-bounds/README.md) |
| SVG Content & Reference Inspector | Inspect a supported SVG/XML/CSS subset for declared dimensions, references and review signals without rendering or fetching. | [Runtime requirements, examples and coverage](tools/svg-content-inspector/README.md) |

The tools describe selected local evidence. Git status is not a backup; glyph
bounds are not visual-quality proof; static SVG findings do not establish safe
rendering. Read the precise scope and runtime requirements in each guide.
Suggestions and fictional reproductions are welcome through the
[issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).

## Android and Linux configuration review

| Tool | Useful for | Instructions and examples |
| --- | --- | --- |
| Android Init Service Inspector | Index selected literal services, action references, duplicate names and reboot markers without following imports. | [Setup, fictional init files and scope](tools/android-init-inspector/README.md) |
| Android Build Copy-Map Inspector | Review declared PRODUCT_COPY_FILES append entries for destination conflicts and unsupported paths/expressions. | [Setup, explicit roots and examples](tools/android-copy-map-inspector/README.md) |
| Fstab Configuration Diff | Explain Linux or Android mount-record value and relative-order changes, retaining duplicate targets as ambiguous. | [Modes, generated comparisons and scope](tools/fstab-diff/README.md) |

These Python standard-library tools inspect explicitly selected text. They do
not evaluate Make/init, read imports, copy payloads, mount filesystems or prove a
successful boot/build. Unsupported syntax remains explicit review coverage.
Private field values are omitted by default; hashes and structure may still
identify inputs. Read each guide before sharing reports. Suggestions and minimal
fictional reproductions are welcome through the
[issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).

## Disk-image, kernel-module and Android interface metadata

| Tool | Useful for | Instructions and examples |
| --- | --- | --- |
| Offline GPT Disk Image Inspector | Inspect bounded partition-table metadata, CRCs, ranges and primary/backup agreement in a regular raw image. | [Sector selection, generated images and scope](tools/gpt-image-inspector/README.md) |
| Kernel Module List & Dependency Inspector | Review selected text for ambiguous names, unresolved dependencies, cycle witnesses and a supported selected dependency order. | [Metadata grammar, examples and limits](tools/kernel-module-inspector/README.md) |
| Android VINTF Manifest Inspector | Index and compare supported selected HAL declarations while keeping duplicate identities and unsupported grammar explicit. | [Supported XML subset, examples and comparison scope](tools/vintf-manifest-inspector/README.md) |

These original MIT Python tools inspect selected local metadata and create fresh
private reports. They do not open physical drives, load modules, merge effective
VINTF configuration or establish successful boot/runtime compatibility. The
VINTF reader has an explicitly restricted XML grammar. Metadata hashes/structure may identify an
input even when names are omitted. Read the precise scope and
[source review](docs/PLATFORM-INSPECTORS-REVIEW-2026-10-25.md).
Suggestions and fictional reproductions are welcome through the
[issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).

## Saved Windows events and configuration snapshots

| Tool | Useful for | Instructions and examples |
| --- | --- | --- |
| Windows Event Timeline Inspector | Sort selected saved event metadata with exact timestamp arithmetic, grouped counts, declared gaps and scoped record-ID observations. | [JSON/XML examples, privacy and export guide](tools/windows-event-timeline/README.md) |
| Android Property Configuration Diff | Explain supported key/value changes while keeping duplicate keys, imports and unidentified rows explicit. | [Snapshot grammar, examples and comparison scope](tools/android-property-diff/README.md) |
| Filesystem Permission Manifest Diff | Compare declared UID/GID/mode/label/capability fields without applying them or inventing removals for unsupported rows. | [Metadata grammar, examples and limits](tools/permission-manifest-diff/README.md) |

These original MIT Python tools inspect explicitly selected saved files. They
do not query live Windows logs, apply properties/permissions or establish a
failure's cause or effective system state. Default field omission is not
anonymization; raw inputs and identifying reports stay private. Read the
[source review](docs/EVENT-CONFIG-REVIEW-2026-10-25.md) and precise module limits.
Suggestions and fictional reproductions are welcome through the
[issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).

## Android image structure and saved APK metadata

| Tool | Useful for | Instructions and examples |
| --- | --- | --- |
| Android Sparse Image Inspector | Review sparse chunk structure, declared expanded sizes and file boundaries without reconstruction. | [Supported format and generated examples](tools/android-sparse-inspector/README.md) |
| Boot / Vendor Boot Header Inspector | Review supported v3/v4 image headers and component ranges without extracting firmware. | [Header scope, examples and limits](tools/android-boot-inspector/README.md) |
| APK Metadata Report Diff | Compare supported declarations from two saved AAPT2 badging text reports. | [Report grammar, examples and comparison limits](tools/apk-report-diff/README.md) |

These original MIT Python tools inspect explicitly selected saved files. Image
payloads, signatures, bootability, device compatibility and effective installed
application state are outside their evidence. No firmware, APKs or real private
reports are bundled. Read the [source review](docs/ANDROID-IMAGES-REVIEW-2026-10-26.md).
Suggestions and fictional reproductions are welcome through the
[issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).

## Saved telemetry, verified patch plans and build declarations

| Tool | Useful for | Instructions and examples |
| --- | --- | --- |
| Offline Session Telemetry Analyzer | Summarize supported saved JSONL events, valid metric samples and declared dropped records with coverage visible. | [Schema, statistics and generated sessions](tools/session-telemetry-analyzer/README.md) |
| Verified Binary Patch Planner | Preview explicit byte edits against a verified source; optionally create a separate fresh verified output. | [Plan schema, preview/apply examples and limits](tools/binary-patch-planner/README.md) |
| Android Build Module Declaration Inspector | Review supported literal declarations in selected build files and requested-name coverage. | [Parser subset, examples and ambiguity](tools/android-build-module-inspector/README.md) |

These original MIT tools use explicitly selected local files and synthetic
examples. Telemetry statistics describe supplied samples; build declarations
do not prove build inclusion. Patch preview is the default; an explicit apply
option creates a new output and does not overwrite the input. No private
telemetry, game assets, vendor configurations or device recipes are bundled.
Read the [source review](docs/SESSION-PATCH-BUILD-REVIEW-2026-10-26.md).
Ideas and fictional reproductions are welcome through the
[issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).

## Mod Profile Activation Manager

Manage named, verified mod-profile copies in one explicit private workspace.
Preview activation/deactivation, review drift, retain previous active copies and
recover interrupted operations. Source folders remain intact; the stable
`active` folder belongs to the manager's workspace. The optional Tk desktop and
CLI share the same engine. No game assets, real profiles or private runtime
records are bundled. Game integration is manual and game-dependent.

- [Installation, CLI/desktop instructions and fictional examples](tools/mod-profile-manager/README.md)
- [Workspace contract, recovery and validation boundaries](docs/PROFILE-MANAGER-REVIEW-2026-10-26.md)
- [Bug reports and suggestions](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose)

## USB Connection Monitor

Observe sampled presence for one explicitly selected Windows USB PnP instance,
with an idle-start desktop, bounded background queries, a readable timeline,
unknown-gap handling and explicit private JSON export. Fictional demos and
offline sample replay also work without hardware. Session reports omit device
IDs/names, machine details, absolute dates and raw native output. Selection
lists remain private. Polling can miss transitions and does not establish cause.

- [Installation, desktop/CLI walkthrough and fictional examples](tools/usb-connection-monitor/README.md)
- [Source review and observed validation boundaries](docs/USB-MONITOR-REVIEW-2026-10-26.md)
- [Bug reports and suggestions](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose)

## Desktop Network Monitor

The owner's existing desktop packet monitor now has an idle-start Tk dashboard,
offline demo/replay, bounded metadata, explicit owned capture workers and manual
OTX lookup. Local port/length matches and declared pulse counts are separate
review observations, not malware verdicts. Aggregate exports omit addresses,
payloads, interface names and absolute dates. No real traffic or credentials are
bundled. Live capture/service acceptance remains explicitly unqualified.

- [Installation, desktop/CLI walkthrough and fictional examples](tools/desktop-network-monitor/README.md)
- [Owner-confirmed source, separate dependency licenses and test boundaries](docs/NETWORK-MONITOR-REVIEW-2026-10-26.md)
- [Bug reports and suggestions](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose)

## Quick start

See the [fresh-download walkthrough](docs/V0.1.0-WALKTHROUGH.md) and create an
[external private workspace](docs/PRIVATE-WORKSPACE.md) before examples that write
files, stores, reports or backups. The command below only reads the selected source.

Use each tool's documented runtime: most fixture results are from Python 3.12/Linux, while Keep Awake requires Windows for runtime operation. The first four groups need no third-party package installation. Document Builder requires the declared python-docx dependency in an existing environment. File Mover runs as a module from its own tool directory; start with its read-only plan command on disposable data. It changes files when asked to move, restore, abandon or purge. Read each tool's limits.

```text
python tools/documentation-check/docs_check.py --root .
```

To work with an existing report or lock, provide your own explicit private input/output paths:

```text
python tools/dependency-lock-tools/report_to_lock.py --report INPUT_REPORT_JSON --output NEW_LOCK_FILE
python tools/dependency-lock-tools/verify_locks.py LOCK_FILE
```

The [Dataset Review Manager](systems/dataset-review/README.md) now has checked
JSONL import/export with preserved review rules and private-store requirements.
Store opening now validates the canonical legacy format without migration;
WAL/sidecar/custom-schema states are refused. See its
[store/schema contract](systems/dataset-review/docs/STORE-SCHEMA.md) and
[JSONL I/O limits](systems/dataset-review/docs/JSONL-IO.md).

## Recorded validation

The table below preserves historical reference runs. Current Keep Awake
validation adds 29 methods: all 56 local Windows methods passed, including 15
opt-in native request/Tk cases; a standalone copy passed 16 fresh processes.
See [the native Windows review](docs/BATCH-24-KEEP-AWAKE-WINDOWS.md) for limits
and the separate Windows/Ubuntu CI matrix. API calls do not prove idle sleep.

| Tool | Synthetic unittest methods | Runtime |
| --- | ---: | --- |
| Dependency Lock Tools | 32 passed | Python 3.12.7, Linux |
| Package Layout Checker | 33 passed | Python 3.12.14, Linux |
| Source Inventory | 18 passed | Python 3.12.7, Linux |
| XML Recipe Inspector | 34 passed | Python 3.12.7, Linux |
| Markdown Document Builder | 27 passed | Python 3.12.14, Linux; python-docx 1.2.0 |
| Safe File Mover | 54 passed; 12 skipped (66 discovered) | Python 3.12.7, Linux |
| Keep Awake | 27 synthetic/simulated methods passed | Python 3.12.7, Linux; no native Windows/Tk execution |

Across seven groups, 237 methods were discovered: 225 passed, 12 Windows-only File Mover methods were skipped, with no failures/errors. The earlier six groups retain their separate recorded results; Keep Awake adds 27 fresh synthetic methods using simulated APIs/fake widgets. Skips are not passes, and simulations are not native Windows acceptance. These are separate recorded tool suites, not one integrated application acceptance test. A separate fictional layout CLI run passed for two declared files; it is not counted as additional unittest cases. Validation used bounded, isolated child processes with network system calls denied. A separate fictional Document Builder CLI run and package metadata inspection also passed. File Mover tests include fixture-only destructive and recovery operations. Keep Awake tests make no native power or GUI calls. No real report, package artifact, business data or production environment was accepted by these tests.

## Scope

Lock validation checks syntax and hash pairing. Hashes come from the supplied report; the tools do not establish artifact origin, dependency resolution, installability, platform coverage or vulnerability status. Report URLs and source constraints are not carried into the generated format.

Layout checks cover only declared files. PASS does not enumerate extra files, prove an exact export list, find arbitrary secrets or establish application correctness. Syntax parsing is not execution. Source Inventory reports preserve relative names, hashes, sizes and timestamps; exclusions do not guarantee removal of every private file. XML summaries retain selected recipe identifiers and geometry. The XML schema assumptions are not vendor measurement validation or accuracy evidence. Read each tool's limits before selecting inputs. None of these tools is an anonymity mechanism, a universal filesystem sandbox or a complete snapshot. XML Recipe Inspector preserves its POSIX/XML logic and adds Windows native input and new-directory output with [documented permission and transaction limits](tools/xml-recipe-inspector/docs/WINDOWS.md). Dependency Lock Tools preserves its POSIX bodies and adds Windows native input checks and exclusive output with [inherited-ACL and failure limits](tools/dependency-lock-tools/docs/WINDOWS.md). Package Layout Checker preserves its POSIX descriptor backend and adds a separately tested Windows native-handle backend with [documented limits](tools/package-layout-checker/docs/WINDOWS.md). Source Inventory preserves its POSIX/report/classifier contracts and adds native Windows filesystem guards with [documented scope and limits](tools/source-inventory/docs/WINDOWS.md); real inventories stay private. Document Builder preserves its parser/layout and Linux I/O and adds Windows native file checks with [fictional DOCX package evidence and limits](tools/document-builders/docs/WINDOWS.md); Office visual rendering remains unverified. Its core-property settings do not remove copied input text, inherited template parts or ZIP timestamps, and its direct dependency pin is not a complete transitive lock or advisory audit.

File Mover creates local state and can rename/delete data. Its journal, staging/recovery copies, console output and GUI logs contain operational details. Owner-private POSIX storage checks and verification do not make it an application backup, anonymity mechanism or hostile-filesystem sandbox; Windows CLI/engine behavior has separate [native fixture evidence and limits](tools/safe-file-mover/docs/WINDOWS.md); GUI, live SMB and power-loss behavior remain unvalidated.

Keep Awake is a Windows-only runtime utility. Its original Linux tests use fakes; the newer [Windows contract](tools/keep-awake/docs/WINDOWS.md) records real request/Tk lifecycle checks and fixed failure handling. Actual idle sleep, policy and mixed-DPI/other-layout acceptance remain separate. Its original selected drive path could not be freshly checked; the verified retained public source and historical mapping remain the provenance basis.

Keep real reports, generated locks, private manifests, credentials, mover journals/recovery copies, runtime outputs and identifying support material outside this repository. Use stable, trusted files and parents.

See [the second-batch review](docs/BATCH-2-REVIEW.md) for inventory/XML validation and [the Document Builder review](docs/BATCH-3-REVIEW.md) for its CLI privacy correction and validation scope. See [the file-mover review](docs/BATCH-4-REVIEW.md) for its source adaptation, fixture results and destructive-operation limits. See [the Keep Awake review](docs/BATCH-5-REVIEW.md) for simulated tests, cleanup corrections and the original-source readback gap.

## Provenance and licensing

The owner reports personal work created with AI assistance; the adaptations, documentation and synthetic tests were also AI-assisted. Only the selected generic mechanisms and fictional examples are included. No required license or attribution notice was removed from the selected sources. This statement is not independent proof of exclusive authorship.

The selected original source, tests, documentation and fictional examples are offered under the [MIT License](LICENSE). See [LICENSING.md](LICENSING.md) for scope, dependency notices and the earlier review history. Private source records, real data and unselected projects are outside this repository.
