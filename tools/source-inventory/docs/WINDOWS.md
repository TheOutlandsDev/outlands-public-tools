# Source Inventory Windows filesystem contract

Use Python 3.12/3.13 with the adjacent `inventory_windows.py` backend. Only
existing public MIT mechanisms and generated fixtures are included. No actual
tree, inventory, configuration, DLL, runtime or third-party implementation is
bundled. Keep real reports and runtime captures private.

## Paths and observed identity

Windows accepts supported local fixed/removable drive paths, including relative
child paths against the caller's working directory. Parent traversal,
drive-relative/root-relative forms, UNC/device spellings, ordinary ADS syntax,
reserved names, trailing dots/spaces, invalid controls and surrogate text are
refused. Bounds are 4,096 characters, 64 components and 255 characters/component.
The CLI preserves Windows argument spelling until validation and uses static
help text. Already constructed `Path` objects may normalize benign spellings
before the library receives them.

[GetDriveTypeW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdrivetypew)
checks the drive before a root handle is opened; unknown, remote, optical and
RAM-drive types are refused. Observed native names must use the supported local
hard-disk volume namespace. Not every provider/disk type is supported.
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
opens reparse-aware handles and
[GetFinalPathNameByHandleW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew)
supplies normalized NT names without depending on DOS mount-name lookup.
Component-name comparisons reject observed short-name aliases. Native-volume
keys strengthen source/output overlap checks across drive aliases. Drive-map
rebinding and hostile namespace behavior are not guaranteed safe.

Windows may expose a default temporary directory using an 8.3 spelling. Such
paths are still refused: select a fully spelled private workspace. CI sets
fixture `TEMP`/`TMP` to the runner's fully spelled temporary directory rather
than relaxing alias checks; this does not alter the application's environment.

## Collection and hashing

Checked root/output/ancestor handles remain held through an inventory. Each
visited directory is checked and held before a one-level `os.walk` call. The
original caller still filters exclusions and counts entries/files/bytes. Tree
rendering uses the same collected scope; there is no second broad scan/hash.
Links/reparse entries remain skipped and counted; linked roots or ancestors
fail instead of following a target.

Before hashing, the native regular-file handle and binary noninheritable CRT
descriptor must identify the same object/name. Checks retain the original
path/fd size/time comparisons and add native metadata/name comparisons before
and after bounded reads. Growth fails before excess bytes enter the digest.
Cooperative data writers remain permitted; this is not an atomic snapshot.
Regular hard links retain a row and byte contribution for each selected name.
Only unnamed file data is hashed. ADS, ACLs, ownership, link topology and other
filesystem metadata are not inventoried or certified.

## Reports and failures

CSV/JSON/tree schemas, ordering, spreadsheet protection, exclusions and bounds
remain unchanged. Classifier source/input reading and rule matching remain
unchanged; the shared Windows directory/exclusive-writer helpers are stronger.
No atomic classifier input snapshot or classification authority is established.

Output ancestors are retained, a fresh directory is created without replacement,
then its handle is opened and checked. Files use `O_CREAT | O_EXCL`. Existing
files/directories/links are never replaced. Short writes are completed, zero
progress fails, `fsync` is requested, and observed file name/identity/link count
and size are checked before close. Creation/open gaps and sampled pathname
operations still require trusted, quiescent parents.

Windows confidentiality depends on parent ACLs and OS/Python version; no POSIX
owner-mode equivalent or ACL audit is claimed. Flushes do not prove directory,
hardware or power-loss durability, and reports are not a multi-file transaction.
All partial or unconfirmed output is retained. A late failure can leave a
complete-looking `summary.json`; existence, parsability and internal hash
agreement do not certify CLI completion. Handled Windows interruption closes
owned resources and returns 130 / `INCOMPLETE` / `INTERRUPTED`. Source data is
not moved or deleted. POSIX behavior is retained.

## Evidence and remaining limits

Local Windows/Python 3.12.7: original 92 methods, 85 passed/seven skipped; new
32 methods, 22 passed/ten skipped, no failures/errors. Nine new native
hardlink/symlink/junction cases are unavailable in this sandbox; one case is
Linux-only. Local short-name rejection ran. Native skips are not passes.
Fixtures combine actual local I/O with explicitly injected fictional failures.

A copied three-file runtime passed 28 fresh processes: 25 direct CLI and three
controlled partial-write, late-flush and interruption cases. Fictional report
hashes/counts/tree/manifest and classifier compatibility were checked.
Input/runtime bytes stayed unchanged and no bytecode appeared. Captures and
generated reports stay private.

CI runs Windows/Ubuntu Python 3.12/3.13 and requires Windows native link/junction
fixtures. Optional short-name availability is reported separately. Linux retains
the original POSIX suite plus portable backend checks. Exact-commit outcomes
are recorded separately.

Trusted quiescent local trees/parents remain required. Hostile concurrent
mutation, drive rebinding, cloud/offline/remote providers, blocked native I/O,
live SMB and power-loss behavior are outside acceptance. No deadline covers
every filesystem call. This is not a complete tree/stream snapshot, credential
detector, anonymizer, backup or sharing-rights assessment. Relative filenames,
hashes and timestamps can identify private work; keep real exports outside GitHub.
