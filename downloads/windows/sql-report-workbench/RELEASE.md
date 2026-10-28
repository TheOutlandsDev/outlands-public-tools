# SQL Report Workbench — portable Windows x64, package 0.1.1-1

**Extract All, then double-click SQL Report Demo.cmd.** Python is included; a
current browser and Windows 11 x64 are required. No Python installation, pip,
administrator rights, PATH change, account or external service is needed to run
the extracted app. Keep the console open while using it.

The separate **SQL Report Workbench.cmd** launcher starts a blank private
workspace. The demo seeds just one invented dataset and one saved query, only on
a new workspace. Existing workspaces are reopened without reset or reseeding.

## First exercise

1. In the demo browser UI, click **Run saved query**: alpha **8**, beta **11**.
2. Set the query bindings JSON to `{"minimum":4}` and run again: **5** and **11**.
3. Review the selected artifact, record the four assertions and approve it, then
   export. Files remain private under the workspace's `reports` directory.
4. Use **Stop local server**, relaunch, and load a saved artifact. The dataset,
   definitions, results and reviews persist. Unsaved browser drafts do not.

This focused tutorial is intentionally separate from the original full CLI demo,
which records two query revisions, four artifacts and report validation.

## Private storage and recovery

The default workspace folders live outside the extracted app under
`%LOCALAPPDATA%\Outlands\SQLReportWorkbench\fictional-demo` and `workspace`.
The launchers never search for, move or overwrite older installations. Replacing
the app does not delete the external workspace. A second running instance of the
same workspace is refused.

The UI's **Back up state database only** omits snapshots, inbox and reports. It
is **not a complete workspace backup**. Stop every process using the workspace,
copy the entire folder into a new private location, retain the original and open
the copy with the launcher's `--workspace` option. Acceptance compares the full
copy and reopens its snapshots, historical results, reviews and exported files.
No automatic copy utility, scheduling, overwriting or deletion is added.

An interrupted process can leave an empty session marker. The original explicit
`recover --confirm-stopped` operation requires the operator to independently stop
all processes first. It does not repair a damaged store or replay jobs. See the
offline `START-HERE.txt` for exact commands, refusals and remaining limits.

## Included source and runtime

The unchanged application declares **0.1.0** and comes from reviewed public source
`f67b3c5e686595336d243d44e85bc2b3ccc76b0d`, verified against the original focused
0.1.1 source ZIP and every original source-manifest member. Its original manifest
is retained inside `application/`.

The runtime is the official **CPython 3.14.10 Windows x64 embeddable package**,
pinned to SHA-256
`90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159`.
All runtime binaries and licenses remain exact; only `python314._pth` adds the
sibling application folder with automatic site imports disabled. Original
launchers, offline instructions, notices and a complete member manifest wrap it.
[Upstream release and checksum](https://www.python.org/downloads/release/python-31410/).

The original source ZIP, earlier releases and Toolkit snapshot remain unchanged.
This archive includes no user workspace, database, query history, credentials,
browser, pip or installer. Future user inputs and generated files stay private.

## Qualification and limits

Windows and Ubuntu builders must produce identical archive bytes. Windows
acceptance extracts the ZIP into a path containing spaces, launches from a
different working directory, restricts PATH to Windows system directories and
sets invalid PYTHONHOME/PYTHONPATH values. The original 60-test core suite runs
under the bundled interpreter, including its owned SQL worker processes.
Applicable native link fixtures are required; the opposite-platform fixture is
reported separately as a skip.

Acceptance independently checks 8/11, 5/11 and 9/12 results, saved revision
boundaries, approved private export hashes/CSV/JSON, persistence after a real
process restart, a stopped complete-workspace copy, explicit stale-marker recovery,
separate blank storage, original full CLI demo and unchanged distribution bytes.
An additional Chromium workflow drives queries, review/export, report-field
validation, restart and full-copy recovery against separate bundled processes.
The browser dependency is installed only for CI, outside the user package.
Only sanitized counts/check outcomes are published; raw logs, tokens, private
workspaces and generated outputs are not uploaded.

This is hosted Windows and interpreter-isolation evidence, not a manual test on a
Python-free PC or universal Explorer/default-browser acceptance. The intended
desktop is Windows 11 x64; other Windows architectures and other operating systems
are not qualified for this portable download. Use the separate source download
where appropriate. The outer package is not Authenticode-signed by OUTLANDS.
If policy blocks it, use the source alternative or consult the administrator;
do not disable protections.

SQL preflight is not a parser or OS sandbox. SQLite is not SQL Server. Report
validation inspects a supported structural subset and columns; it does not render
reports. Review assertions are not publication clearance. No production use,
external database integration or active-write crash durability is claimed.
