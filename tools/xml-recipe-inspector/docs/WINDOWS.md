# Windows XML input and new-directory report contract

Keep `xml_recipe_inspector.py` and `xml_windows.py` together. The backend adapts
only the collection's public MIT native file mechanisms. It uses Python's
standard library and OS-provided APIs; no DLL, runtime, original recipe or
third-party implementation is bundled. XML interpretation, geometry conventions,
parser/resource limits, CSV shielding and JSON output formats remain unchanged.

## Inputs

Windows CLI arguments retain raw spelling until validation. Ordinary relative
and drive-absolute paths are bounded at 4,096 characters, 64 components and 255
characters/component. Parent traversal, UNC/device/extended user paths,
drive-relative forms, alternate streams, reserved device names, control
characters and trailing dots/spaces are refused. No environment expansion occurs.

Retained native handles cover existing ancestors. Inputs use `OPEN_EXISTING`
with reparse-point/directory-support flags and read sharing only. Queries check
disk type, reparse/directory attributes, file identity, link count and normalized
NT-volume names. Supported ordinary local HarddiskVolume names and usable IDs
are required. Each child's normalized native name must match its retained
parent's name plus the selected component. Reparse roots/ancestors/leaves,
multi-link inputs and observed short-name aliases are refused.

A noninheritable binary CRT descriptor owns the transferred input handle. Reads
are bounded before XML parsing, with size/timestamp and native identity/name
observations checked around reading. Conflicting ordinary data writers/deleters
can cause refusal. Read-sharing restrictions do not freeze every metadata,
mapped-view, filter or filesystem operation.

The pure parser still rejects DTDs, entity declarations, external entities,
processing instructions and namespaces, including declaration attempts in
UTF-16. Ordinary XML character references are allowed. It never expands
XInclude, opens referenced images, fetches URLs or runs selected content.

## New-directory outputs

The entire XML is inspected and all report bytes rendered within the combined
4 MiB bound before directory creation. The writer accepts only the existing
fixed JSON/CSV report names, byte payloads and bounded nonempty mappings; its
low-level contract permits an empty byte payload. Missing parents are not created.

[`CreateDirectoryW`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createdirectoryw)
makes the native new-directory decision and refuses an existing destination.
The backend then opens and verifies the new directory's normalized name/type
and retains its handle through every report close. Creation and handle
acquisition are separate: a hostile ordinary-directory replacement in that gap
can be indistinguishable. Stable trusted parents are required. This is not an
atomic owned-directory transaction or a replacement-resistant sandbox.

Each fixed report uses
[`CreateFileW`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
with `CREATE_NEW`, no ordinary sharing and no replacement fallback. Unexpected
existing report names cause refusal. Bounded synchronous writes handle short
writes and reject zero/failed writes, then flush the file. All report handles
remain until final identity/name/size checks; directory/ancestor observations
are checked before writes and after file closure. Every file close is attempted
on failure. File handles close sequentially; this is not an immutable report-set
snapshot. Other processes can add child entries, and the backend does not
enumerate unlisted children or certify exact output-tree privacy.

Directory/report permissions inherit from the chosen parent's Windows ACL.
There is no POSIX 0700/0600 equivalent, ACL confidentiality check, encryption or
administrator-access restriction. Select a trusted private parent outside the
public checkout. File flushing does not prove directory-entry or hardware
durability, power-loss recovery or all-or-nothing publication of the report set.

Any failure after directory creation retains the new directory and created files.
It can be empty, partial or fully written but unconfirmed. An error is not a
successful export. No Windows error handler deletes, rolls back or retries into
that directory; inspect it privately and choose a different new destination.
Existing files/directories/links and the input are not removed as recovery.
OS close failures can leave handles open until process exit.

## POSIX, results and remaining limits

The original POSIX reader/writer bodies remain after the new Windows dispatch;
their mode requests, no-follow checks, exclusive directory-relative report
creation, flushing and failure behavior are unchanged. All original pure XML,
geometry, numeric, CSV and rendering definitions and the 34-test file are
preserved. Static help stays fixed; interruption has a fixed error category.

Success remains counts-only stdout JSON. Handled errors return code 2 with fixed
stderr JSON; raw arguments, recipe excerpts, identifiers, normalized native
paths/IDs and OS error text are not printed. Library tracebacks can retain source
locations. Reports intentionally retain selected identifiers, locations,
geometry and calibration-derived values; real XML and reports require private
handling and a separate sharing/rights review. This tool does not anonymize data.

Network/virtual storage, mount/drive rebinding, hostile concurrent mutation,
mapped views, ACL privacy and exhaustive filesystem behavior are not certified.
Neither backend proves a vendor schema/algorithm, measurement accuracy,
application correctness, authorization, ownership or public-release readiness.

## Fictional validation

The platform workflow runs the unchanged original 34 methods on Ubuntu and the
new portable/native suite on Windows/Ubuntu, Python 3.12/3.13. Windows CI requires
native hardlink/symlink/junction creation; local unavailability and unavailable
alternate short-name spellings remain explicit skips. Fixtures contain invented
XML and disposable output trees only. See the
[Batch 21 review](../../../docs/BATCH-21-XML-RECIPE-WINDOWS.md) and exact-commit
Actions logs for executed counts and the separate standalone CLI walkthrough.
