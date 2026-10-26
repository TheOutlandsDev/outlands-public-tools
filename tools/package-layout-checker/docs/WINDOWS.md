# Windows backend and validation boundary

The CLI dispatches to `layout_windows.py` on Windows. Keep it beside
`layout_check.py`; only Python's standard library and OS-provided APIs are used.
No DLL, third-party implementation or runtime is bundled. The manifest v1,
limits, result shape, exit codes, static AST parsing and literal checks remain.
The POSIX descriptor backend and its 33 regression tests are preserved unchanged.

## Native inputs and file lifetime

Windows control paths can be ordinary relative or drive-absolute paths, up to
4,096 characters and 64 components. There is no environment expansion. User UNC,
device/extended paths, parent traversal, drive-relative paths, alternate streams,
reserved names and trailing dots/spaces are refused. Original parts are checked
before absolute normalization can erase suffixes. Components are conservatively
limited to 255 characters; selected relative paths retain the common 512-character
manifest limit and a Windows limit of 64 components.

The backend opens existing local paths using
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
with reparse-point opening and directory support flags. It queries file type,
attributes, file ID, link count and normalized NT-volume path information through
native handles. Only ordinary disk files/directories on normalized local
HarddiskVolume paths with usable identities are supported. Network, shadow-copy,
virtual and other filesystems are not generally supported or certified.

Every lexical ancestor gets a retained directory handle. Each newly opened
component's normalized native name must match its retained parent's native name
plus the requested component, with case-insensitive comparison. This refuses
observed ancestry changes and alternate short-name spellings before reading the
selected body. Reparse attributes are refused on roots, manifest ancestors,
selected-file ancestors and selected leaves. A regular file must have one link;
hard links are rejected, not followed as an alternate package source.

Handles request `FILE_SHARE_READ` only, without ordinary data-write or delete
sharing. Incompatible existing writers/deleters can make checks fail. Sharing
restrictions do not cover every metadata, mapped-view or filesystem operation;
this is not an immutable snapshot. File/ancestor identity and native names are
sampled again after checks. The common bounded descriptor reader also checks
size and timestamps before/after reads. Presence-only entries request no body
read; content checks reserve the same full observed size against the 2 MiB budget.

The file handle is transferred to a noninheritable binary CRT descriptor using
[open_osfhandle](https://docs.python.org/3.12/library/msvcrt.html#msvcrt.open_osfhandle).
Descriptor closure owns the native file closure; the backend separately closes
every retained ancestor handle. Ownership is explicit so a handle is not closed
twice after transfer. See Microsoft's
[ownership notes](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/open-osfhandle).

Use stable trusted local packages and manifests. Drive/mount rebinding, hostile
concurrent mutation, remote storage, power loss, Windows ACL privacy and every
filter/filesystem behavior remain outside the guarantee. Unsupported metadata,
sharing conflicts and observed changes fail rather than weakening checks.
The Windows backend does not claim POSIX directory-descriptor semantics; the
existing POSIX implementation still uses its anchored no-follow operations.

## Results and privacy

The CLI reports the same schema and fixed result codes. A file-specific failure
produces a failed row; invalid/inaccessible control roots or manifests reject
the run. Source text, matched marker values, normalized native paths, volume/file
IDs and native error text are not printed. Relative manifest paths remain and
can identify private projects. Real manifests can themselves contain sensitive
literal rules; keep them and output private and outside the checkout.

Selected Python is parsed, never imported or run. No selected-package directory
is enumerated, no unlisted file is opened, and no file, setting or service is
changed. PASS establishes declared checks only: it does not attest to an exact
export list, absence of private data/secrets, application correctness, dependency
safety, ownership, licensing or release readiness. Static syntax support remains
limited to the interpreter doing the parsing.

## Fictional validation

Run the full platform suite from the collection root:

```text
python -B -m unittest discover -s tools/package-layout-checker/tests -v
```

There are 33 unchanged POSIX methods, 28 new native Windows methods and three
portable contract methods. The local Windows/Python 3.12.7 run discovered 64:
27 passed, 37 skipped. That includes 25 passed native Windows methods, two passed
portable methods, 33 POSIX skips, one POSIX-only API skip and unavailable native
hardlink/symlink/junction creation. Skips are not passes. On Windows CI,
`OUTLANDS_LAYOUT_REQUIRE_NATIVE_LINKS=1` makes those three fixture-creation failures
fail the job. Short-name tests may skip if the filesystem supplies no alternate
spelling; their skips remain explicit.

Checks cover real handle open/read/close behavior, read-only sharing refusals,
noninheritable descriptors, source/manifest limits and redacted findings,
metadata-only presence checks, native short-name aliases, hardlinks, reparse
roots/ancestors/leaves, case/stream/reserved-name refusals and unchanged package
bytes. Repeated success/rejection runs showed no process-handle-count growth in
the local fixture process. These observations do not prove arbitrary runtime
containment or exhaustive filesystem behavior.

A separate two-file copy outside the checkout passed 23 native CLI scenarios
with fictional packages only, including static source that would raise if
executed. Inputs/checker bytes remained unchanged. The collection regression
discovered 559 methods: 532 passed, 27 skipped. The Windows platform CI and Ubuntu
POSIX regression target Python 3.12/3.13; consult exact-commit Actions logs for
executed native cases, preservation evidence and platform skip counts. See the
[batch review](../../../docs/BATCH-19-PACKAGE-LAYOUT-WINDOWS.md).

The new code and fixtures adapt only this public MIT toolkit. No original
private verifier, project, manifest, business schema, user record, path,
credential, endpoint or operational configuration was selected/read/copied/run.
Earlier source/rights holds remain; OS/Python runtime terms remain their own.
