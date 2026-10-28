<!-- Generated from catalog/start-here.json and registry.json. -->

## Choose a tool for your task

Start with one focused download and its fictional exercise. Workfloor, SQL Report Workbench and Developer Workspace Windows packages include Python; Local Site Builder includes Node and its dependencies. Other source downloads need the runtime documented in their guide.

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

**Start with Local Site Builder for Windows.** [Download ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-site-builder-windows-v1.0.2-2/local-site-builder-1.0.2-windows-x64.zip) · [Quick start](https://github.com/TheOutlandsDev/outlands-public-tools/blob/local-site-builder-windows-v1.0.2-2/downloads/windows/local-site-builder/START-HERE.txt) · [Evidence and methodology](https://github.com/TheOutlandsDev/outlands-public-tools/blob/local-site-builder-windows-v1.0.2-2/downloads/windows/local-site-builder/RELEASE.md)

Alternatives: [Cross-platform source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-site-builder-v1.0.2/local-site-builder-1.0.2.zip) · [Source setup guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/local-site-builder-v1.0.2/tools/local-site-builder/START-HERE.md)

**Requirements:** Windows 11 x64 and a modern browser. Node 24.22.2, all 86 locked dependencies and upstream native SQLite are included. No npm, compiler, installer, account, admin rights or PATH change. The separate source ZIP still uses Node 24/npm on Windows or Linux.

**Try this:** Extract All into a new local folder, then double-click Local Site Builder.cmd. Choose and confirm a private admin password in the console; sign in as admin. In the fictional Cedar Workshop, edit Welcome and Save Draft. Reload the separate public preview, then Publish explicitly. Save a newer private draft, stop with Ctrl+C and relaunch.

**Expected result:** The draft stays private until Publish; the local public preview then shows the changed headline. Published content and any newer draft persist after restart; sign in again because sessions expire.

**Limits:** A single-user loopback-only editor. Publish updates local pages; internet hosting is separate and email delivery is off. Settings and data persist outside the app. Stopped backups exclude credentials: keep .env separately. Restore into a new explicit data directory and select that --data path on later launches. Manual Node-free-PC/Explorer/default-browser acceptance remains unperformed; the outer package is unsigned.

**Then try [Verify a stopped-site backup and restore](https://github.com/TheOutlandsDev/outlands-public-tools/blob/local-site-builder-windows-v1.0.2-2/downloads/windows/local-site-builder/START-HERE.txt):** Stop with Ctrl+C, create and verify a backup, then restore into a new explicit data directory. Reopen the published page and newer private draft using --data on each later launch. The guide gives quoted PowerShell commands; existing destinations and changed backups are refused. Keep private .env separately because backup excludes credentials.

<a id="source-review"></a>
### Inspect and validate code

**Start with Developer Workspace for Windows.** [Download ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/developer-workspace-windows-v0.1.1-1/developer-workspace-0.1.1-windows-x64.zip) · [Quick start](https://github.com/TheOutlandsDev/outlands-public-tools/blob/developer-workspace-windows-v0.1.1-1/downloads/windows/developer-workspace/START-HERE.txt) · [Evidence and methodology](https://github.com/TheOutlandsDev/outlands-public-tools/blob/developer-workspace-windows-v0.1.1-1/downloads/windows/developer-workspace/RELEASE.md)

Alternatives: [Cross-platform source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/developer-workspace-v0.1.1/developer-workspace-0.1.1.zip) · [Source setup guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/developer-workspace-v0.1.1/downloads/workbenches/developer-workspace/START-HERE.md)

**Requirements:** Windows 11 x64 and a modern browser. Python 3.14.10 is included; no Python installation, pip, account, admin rights or PATH change. The separate source ZIP uses Python 3.12/3.13 on Windows or Ubuntu.

**Try this:** Extract All, double-click Developer Demo.cmd, then choose sample-project from Saved project. Validate revision 1, review its checked/unchecked files and approve that exact validation. Select src/sample.py, edit and save revision 2, then compare 1 with 2. Validate again to see a new pending artifact; select the approved revision-1 validation and export its original source. Stop the server before maintenance.

**Expected result:** After the exercise: 5 files / 2 saved revisions / 4 passing format checks / 1 explicitly unchecked Markdown file. The new validation starts pending. The approved nine-member private export stays pinned to revision 1.

**Limits:** Supplied project code is not executed. Passing syntax does not prove behavior or publication clearance. Demo and blank workspaces are separate and persist outside the app. The state backup omits inbox/exported files; stop every process and copy the full workspace for complete recovery. Package 0.1.1-1 wraps unchanged source declaring 0.1.0. Manual Python-free-PC/Explorer acceptance remains unperformed; the outer package is unsigned.

**Then try [Release and developer QA workshop](https://github.com/TheOutlandsDev/outlands-public-tools/blob/toolkit-v0.3.0/workshops/release-qa.md):** Use the release-qa family ZIP and Python 3.12/3.13. Run python -B workshops/run.py --family release-qa --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY with a new absolute path outside the package. Expect three checked examples and eight commands, including deliberate differences. This does not establish installation or deployment acceptance. [Download ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/toolkit-v0.3.0/outlands-release-qa-0.3.0.zip).

These are versioned demonstrations with documented platform checks, not a claim of production deployment. Observed evidence is linked above; reproduce the exercise before treating an expected result as a local test result.

[Complete catalog](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/catalog/generated/INDEX.md) · [Methodology examples](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/methodology/worked-examples) · [All family workshops](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/workshops)
