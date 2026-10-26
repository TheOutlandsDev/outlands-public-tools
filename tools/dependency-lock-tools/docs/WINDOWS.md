# Windows dependency-lock input and output contract

Keep `lock_common.py`, `lock_windows.py`, `report_to_lock.py` and
`verify_locks.py` together. The backend adapts only the existing public MIT
Package Layout Checker native-handle code. It calls OS-provided APIs through
Python's standard library; no DLL, runtime or third-party implementation is
bundled. Conversion/validation grammar and package/report/lock bounds remain.

## Input handling

The CLIs preserve raw Windows argument strings for validation before path
normalization. Ordinary relative and drive-absolute paths are bounded at 4,096
characters, 64 components and 255 characters/component. Parent traversal,
UNC/device/extended user paths, drive-relative forms, alternate streams, reserved
device names and trailing dots/spaces are refused. No environment expansion or
remote probing is performed.

Existing ancestors are opened with retained native directory handles. Input
files use `OPEN_EXISTING`, `FILE_FLAG_OPEN_REPARSE_POINT`, directory-support flags
and read sharing only. The backend queries disk type, attributes, file identity,
link count and normalized NT-volume names. Only supported ordinary local
HarddiskVolume names with usable identities are accepted. Each child name must
match its retained parent's normalized name plus the selected component;
observed ancestry changes and short-name aliases are refused. Reparse roots,
ancestors and leaves, directories as files and multi-link inputs are refused.

A noninheritable binary CRT descriptor owns each transferred input handle.
Reads are bounded before decoding; size/timestamps and retained native identity/
name observations are checked around reads. Parent handles remain until file
checks and closure complete. Conflicting ordinary data writers/deleters can
cause refusal. These sharing restrictions do not freeze every metadata,
mapped-view or filesystem operation.

## New-file outputs and failure handling

The complete bounded report is parsed and the lock rendered before output
creation. An existing parent must be selected explicitly; none is created.
The parent chain is checked and retained while native
[`CreateFileW`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
uses `CREATE_NEW`. This makes the no-replacement decision in the native open;
there is no overwrite-capable fallback. Existing files, directories, symlinks
and hardlinks are left intact. Windows errors for different existing object
types can map to different fixed rejection categories.

The new file requests no sharing during writing. Before any body write it must
be an ordinary single-link disk file at the expected normalized native name.
Bounded synchronous
[`WriteFile`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-writefile)
calls handle short writes and reject failed/zero writes. After
[`FlushFileBuffers`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers),
stable file identity, expected final size, native name and parent observations
are checked before closure. This does not promise directory-entry durability,
hardware persistence, power-loss recovery or an atomic report-to-lock transaction.

Permissions inherit from the chosen parent's Windows ACL. The backend does
not implement POSIX mode 0600, inspect ACL confidentiality, encrypt output or
restrict administrator access. Operators must choose a trusted private parent
outside the public checkout. New locks retain package names, versions and hashes
and can identify private work.

If anything fails after creation, the new file remains for inspection. It can be
empty, partial or fully written but unconfirmed; it is not a successful output.
No Windows failure handler unlinks a pathname. A retry requires a different new
filename. Existing files and the report are never deleted as recovery. A close
failure may leave a handle open until the process exits; no cleanup guarantee
is made after an OS close failure.

## Preserved POSIX behavior and results

Only platform dispatch is added to the common readers/writer; their original
POSIX bodies and all 32 original test methods/file remain unchanged. Pure report
conversion, normalization, fixed-version subset, lock rendering and strict lock
parser definitions are unchanged. POSIX keeps its original mode request,
no-follow checks, directory-relative exclusive output, flushing and
identity-qualified cleanup behavior and existing limits.

Success still emits counts-only JSON; handled errors return code 2 and a fixed
category. Argument parsing/help use static program names; interruption has a
fixed category. Raw argument values, native paths/IDs, records and OS error text
are not printed. Library tracebacks can retain source locations. Real reports,
locks and captured results need separate private handling and sharing review.

Use stable trusted local inputs and parents. Network/virtual storage, mount/drive
rebinding, hostile concurrent mutation, ACL privacy and exhaustive filesystem
behavior are not certified. The tool does not invoke pip, download, install,
inspect an environment, verify actual artifacts or check advisories. A matching
hash declaration is not artifact authenticity, compatibility or release clearance.

## Fictional validation

The platform workflow runs the unchanged original POSIX suite on Ubuntu and the
new portable/native suite on Windows/Ubuntu with Python 3.12/3.13. Windows native
hardlink/symlink/junction creation is required in CI; unavailable native cases
locally and missing alternate short-name spellings are explicit skips. Test
inputs are fictional disposable reports, locks and directory trees only. See
the [Batch 20 review](../../../docs/BATCH-20-DEPENDENCY-LOCK-WINDOWS.md) and
exact-commit Actions logs for counts and remaining validation limits.
