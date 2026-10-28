# Developer Workspace — portable Windows x64, package 0.1.1-1

**Extract All, then double-click Developer Demo.cmd.** Python is included; a current
browser and Windows 11 x64 are required. No Python installation, pip, administrator
rights, PATH change, project dependencies, account or external service is needed.

The demo starts with five invented files in revision 1 and no validation,
approval or export. **Developer Workspace.cmd** opens a separate blank workspace.
Existing workspaces are reopened without reset, reimport or reseeding.

## Reproduce one useful workflow

1. Choose **sample-project** from **Saved project**, then validate the saved revision: **four format checks pass; Markdown stays unchecked**.
2. Review the text and record the four assertions to approve that exact validation.
3. Select `src/sample.py`, change its return to `sum(values) + 1`, then save.
   **Revision 2** appears; comparing 1 to 2 shows one changed file.
4. Validate again: the new artifact starts pending. Select the approved revision-1
   validation and export. The private nine-member ZIP contains **revision 1's
   original files**, while revision 2 remains available.
5. Stop the local server and relaunch. Saved source, checks, reviews and exports
   persist; unsaved browser drafts/notes do not.

Supplied project code is not executed. Validation is limited to Python AST syntax,
strict JSON, bounded XML and conservative SQL preflight. Other accepted text
formats remain explicitly unchecked. These checks do not establish runtime
behavior, dependency correctness, universal privacy or publication permission.

## Private storage and recovery

Defaults live outside the extracted app under
`%LOCALAPPDATA%\Outlands\DeveloperWorkspace\fictional-demo` and `workspace`.
Older source-download instances are not discovered, moved or overwritten. A second
running instance of the same workspace is refused. Replacing the app does not
delete the private workspace.

The state-backup button omits inbox and exported files. For full recovery, stop
every process using the workspace, copy its entire folder to a new private local
destination, retain the original, then open the copy with `--workspace`. Acceptance
reopens such a stopped copy and compares exact historical source and export bytes.
No automatic copying, scheduling, overwrite or deletion utility is added.

An interrupted process can leave an empty session marker. The existing
`recover --confirm-stopped` command requires the operator to independently stop
all processes first. It verifies/removes only the empty marker; it does not repair
stores, replay lost work or establish active-write crash durability. Offline
`START-HERE.txt` gives all first-run and maintenance commands and limits.

## Included source and runtime

The unchanged application declares **0.1.0** and comes from reviewed public source
`f67b3c5e686595336d243d44e85bc2b3ccc76b0d`. Its original source manifest and every
source file are verified against the focused 0.1.1 ZIP and committed Git objects.
The previous source ZIP and immutable Toolkit release remain unchanged.

The official **CPython 3.14.10 Windows x64 embeddable runtime** is pinned to
SHA-256 `90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159`.
All binaries and licenses remain exact. Only `python314._pth` adds the sibling
application folder with automatic site imports disabled.
[Official release and checksum](https://www.python.org/downloads/release/python-31410/).

Original launchers, offline instructions, third-party notices and a complete member
manifest wrap these fixed inputs. No user database, project, note, export, browser,
pip or installer is bundled. Future user inputs and generated files stay private.

## Qualification and limits

Windows and Ubuntu builders must produce identical package bytes. Windows
acceptance extracts into a path containing spaces, launches from a different
working directory, restricts PATH to Windows system directories and sets invalid
PYTHONHOME/PYTHONPATH values. All original **55 core cases** run under the bundled
interpreter, including owned validation workers. Applicable native link fixtures
are required; the opposite-platform fixture remains an explicit skip.

Acceptance checks the five-file tutorial, 4-pass/1-unchecked coverage, distinct
revisions/checks/reviews, a supplied-code execution canary that must remain absent,
all original revision-1 export bytes, real process restart, a stopped full-copy
recovery, explicit stale-marker recovery, separate blank storage, the original full
CLI demo and unchanged distribution files. An additional Chromium workflow edits,
validates, compares, exports the historical revision, restarts and opens a full
copy through separate bundled-runtime processes. Browser dependencies are outside
the user package. Only sanitized counts/outcomes are published; raw logs, tokens,
generated projects/workspaces and exported files remain private.

These are hosted Windows and interpreter-isolation checks, not a manual test on a
Python-free PC or universal Explorer/default-browser acceptance. Windows 11 x64
is the intended desktop; other architectures/operating systems are not qualified
for this portable download. The outer archive and launchers are not
Authenticode-signed by OUTLANDS. If policy blocks execution, use the source
alternative or consult the administrator; do not disable protections.

No full IDE, project execution, production deployment, authenticated review identity
or automatic release clearance is claimed. Review unchecked text and real exports
separately before sharing anything.
