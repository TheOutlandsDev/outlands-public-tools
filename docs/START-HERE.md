<!-- Generated from catalog/start-here.json and registry.json. -->

## Choose a tool for your task

Start with one focused download and its fictional exercise. Workfloor and SQL Report Workbench Windows packages include Python. Other source downloads need the runtime documented in their guide.

Compare the ZIP SHA-256 with SHA256SUMS.txt from the same release before extracting into a new folder. Keep generated data outside the source folder where the guide requires it. All exercises use invented inputs; keep future real data private.

<a id="manufacturing"></a>
### Manufacturing and reporting

**Start with Workfloor for Windows.** [Download ZIP](https://github.com/TheOutlandsDev/workfloor/releases/download/windows-v0.4.1-1/workfloor-0.4.1-windows-x64.zip) · [Quick start](https://github.com/TheOutlandsDev/workfloor/blob/windows-v0.4.1-1/portable/START-HERE.txt) · [Evidence and methodology](https://github.com/TheOutlandsDev/workfloor/blob/windows-v0.4.1-1/docs/PORTABLE-WINDOWS.md)

Alternatives: [Cross-platform source ZIP](https://github.com/TheOutlandsDev/workfloor/releases/download/v0.4.1/workfloor-0.4.1.zip) · [Source setup guide](https://github.com/TheOutlandsDev/workfloor/blob/v0.4.1/README.md#start-here)

**Requirements:** Windows 11 x64 and a current browser. Python 3.14.10 is included; no Python installation, pip, account, admin rights or PATH change is needed. Other platforms can use the separate source ZIP with Python 3.12/3.13.

**Try this:** Extract All into a new local folder, then double-click Workfloor.cmd. It opens the local report in your browser. On a fresh database, keep From date 2026-10-01 and Before date 2026-10-08. Run the report and compare the correct aggregation with the deliberately wrong join. Save a snapshot, stop with Ctrl+C in the console, then launch again and reopen it.

**Expected result:** 9 orders / 365 units / 4 delayed. The incorrect join counts 26 rows / 1,195 units. The saved snapshot retains its original report after restart.

**Limits:** Synthetic demonstration with invented manufacturing records. Default private data lives outside the app under the Windows local application-data folder, Outlands/Workfloor/data. Existing data is reopened and never reset automatically. Automated qualification covers an isolated bundled runtime and Chromium on hosted Windows, plus local CLI/recovery checks; a manual Python-free-PC/Explorer test remains unperformed. The outer package is not Authenticode-signed. No factory/employer connection.

**Then try [SQL Report Workbench for Windows](https://github.com/TheOutlandsDev/outlands-public-tools/blob/sql-report-workbench-windows-v0.1.1-1/downloads/windows/sql-report-workbench/START-HERE.txt):** Windows x64: Python is included. Extract All and double-click SQL Report Demo.cmd. Click Run saved query for alpha/beta 8/11, change the query bindings to {"minimum":4}, then run for 5/11. The tutorial seeds one invented dataset and one query only on a new separate workspace; later records persist. The original source CLI demo still demonstrates revisions and 9/12. State-only backups omit snapshots and exports; stop all processes and copy the entire workspace for complete recovery. [Download ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/sql-report-workbench-windows-v0.1.1-1/sql-report-workbench-0.1.1-windows-x64.zip).

<a id="local-website"></a>
### Build a local website

**Start with Local Site Builder.** [Download ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-site-builder-v1.0.2/local-site-builder-1.0.2.zip) · [Quick start](https://github.com/TheOutlandsDev/outlands-public-tools/blob/local-site-builder-v1.0.2/tools/local-site-builder/START-HERE.md) · [Evidence and methodology](https://github.com/TheOutlandsDev/outlands-public-tools/blob/local-site-builder-v1.0.2/tools/local-site-builder/docs/PROVENANCE.md)

**Requirements:** Node.js 24 with npm, Windows or Linux, and a modern browser. npm ci downloads locked dependencies; the native SQLite binding may require compiler/SDK prerequisites.

**Try this:** Follow the quick start to set a private password and a new data directory outside the app. In the fictional Cedar Workshop site, change a headline and Save Draft. Check the public preview, Publish explicitly, then restart using the same data directory.

**Expected result:** The draft stays private until Publish; the local public preview then shows the changed headline. Published content and any newer draft persist after restart; sign in again because sessions expire.

**Limits:** A single-user local editor. Publish updates its local preview; internet hosting is separate. Dependencies and the Node runtime are not bundled. Backup/restore requires a stopped app and new destination.

**Then try [Verify a stopped-site backup and restore](https://github.com/TheOutlandsDev/outlands-public-tools/blob/local-site-builder-v1.0.2/tools/local-site-builder/START-HERE.md#recover-a-stopped-site):** Create and verify a stopped-site backup, restore into a new directory, and reopen both the published page and newer private draft. The guide gives the exact commands and refuses existing destinations.

<a id="source-review"></a>
### Inspect and validate code

**Start with Developer Workspace.** [Download ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/developer-workspace-v0.1.1/developer-workspace-0.1.1.zip) · [Quick start](https://github.com/TheOutlandsDev/outlands-public-tools/blob/developer-workspace-v0.1.1/downloads/workbenches/developer-workspace/START-HERE.md) · [Evidence and methodology](https://github.com/TheOutlandsDev/outlands-public-tools/blob/developer-workspace-v0.1.1/downloads/workbenches/developer-workspace/PROVENANCE.md)

**Requirements:** Python 3.12 or 3.13 with SQLite and a modern browser on Windows or Ubuntu. No application pip packages, account or external service.

**Try this:** Extract to a new folder. Follow the outer START-HERE.md: run the demo with a new private workspace, then serve that same workspace. Inspect saved revisions, compare the changed file and review the historical export. Stop the server before using another CLI command on that instance.

**Expected result:** 5 files / 2 revisions / 4 passing checks / 1 explicitly unchecked file. The second validation remains pending. A nine-member private export stays pinned to revision 1.

**Limits:** Checks do not execute supplied project code. Passing syntax checks do not prove behavior or publication clearance. Package 0.1.1 wraps unchanged application source declaring 0.1.0. Keep real source, workspaces and exports private.

**Then try [Release and developer QA workshop](https://github.com/TheOutlandsDev/outlands-public-tools/blob/toolkit-v0.3.0/workshops/release-qa.md):** Use the release-qa family ZIP and Python 3.12/3.13. Run python -B workshops/run.py --family release-qa --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY with a new absolute path outside the package. Expect three checked examples and eight commands, including deliberate differences. This does not establish installation or deployment acceptance. [Download ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/toolkit-v0.3.0/outlands-release-qa-0.3.0.zip).

These are versioned demonstrations with documented platform checks, not a claim of production deployment. Observed evidence is linked above; reproduce the exercise before treating an expected result as a local test result.

[Complete catalog](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/catalog/generated/INDEX.md) · [Methodology examples](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/methodology/worked-examples) · [All family workshops](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/workshops)
