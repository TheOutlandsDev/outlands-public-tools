# Public Release Audit filesystem contract

The runtime remains Python 3.12+, standard library only. Windows/Ubuntu
Python 3.12/3.13 are the tested matrix; other versions are unverified. Keep
`audit_windows.py` beside the script. No real export, marker list, report,
configuration, runtime, DLL or third-party implementation is bundled.

## Preserved behavior

The detector function, patterns, filename rules, example-address exceptions,
manifest validator and original 19 audit tests are unchanged. POSIX export
scanning and new-file report writing retain their bodies. Control JSON reads
are strengthened on both platforms. Stable supported trees retain report
schemas, findings, ordering, hashes and bytes read. Incomplete/mutating trees
can yield different partial observations and must never be treated as clear.

## Windows paths and reads

Supported local fixed/removable drive paths are accepted. Parent traversal,
drive/root-relative forms, UNC/device spellings, ordinary ADS syntax, reserved
names, trailing dots/spaces, invalid controls and surrogate text are refused.
Bounds are 4,096 characters, 64 components and 255 characters/component.
Relative child paths remain supported against the working directory. A Windows
filesystem root cannot be selected for export scanning.

Public MIT native mechanisms provide
[GetDriveTypeW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdrivetypew)
checks before root opens, reparse-aware
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew),
and [GetFinalPathNameByHandleW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew)
for observed native-volume names. Checked root/ancestor/directory/file handles
are held during scoped operations. Observed aliases/reparse/name changes are
refused. Windows temp paths can use 8.3 names: choose a fully spelled private
workspace. CI uses canonical temporary paths rather than relaxing alias checks.

Directory enumeration stops after the remaining entry budget plus one probe,
before sorting. Overflow requires review rather than silently truncating a
clear result. Reads compare observed paths, native handles and binary
noninheritable CRT descriptors, plus size/time/name checks. Cooperative data
writers are permitted: these are observations, not a content freeze/snapshot.

The 2 MiB/file, 64 MiB total and 20,000-entry limits remain. Windows also charges
bytes consumed by failed reads against the total. One extra-byte EOF/growth
probe can be read, but excess bytes never enter a digest. Export hard links
remain separate names. ADS, ACLs, ownership, topology and other metadata remain
outside the selected text inventory.

## Controls and outputs

JSON controls are bounded to 16 MiB with an extra-byte rejection probe and
ordinary-file/identity checks before decoding. POSIX uses available no-follow/
nonblocking flags. Windows controls must have one hard link. JSON schemas,
duplicate-key semantics, marker validation and manifest matching are otherwise
retained. These byte limits are not complete CPU/memory quotas for JSON/regex.

Windows reports/manifests are encoded before creation with a 64 MiB per-output
ceiling. Indented JSON, ASCII escapes and LF bytes remain unchanged. Native
names strengthen the outside-root requirement, including observed drive aliases.
Missing parents are not created. `O_CREAT | O_EXCL` refuses existing entries;
short writes complete or fail, flushes are requested and observed identity,
name, size and link count are checked. Parent ACLs and OS/Python version govern
permissions; confidentiality is not audited and no POSIX mode equivalent is
promised.

Checks are sampled, with pathname/create/open windows. No atomic multi-output
transaction or hardware/power-loss durability is provided. Failed writes retain
partial or fully written but unconfirmed output, even if the JSON contains a
clear-looking status. Existence, parsability and hashes alone do not prove CLI
success. Windows interruption returns 130 with fixed `ERROR` /
`AUDIT_INTERRUPTED`; POSIX interruption behavior is retained.

## Privacy and evidence

Finding records omit matched content snippets. Relative filenames can contain
private markers/identifiers; hashes can identify known content. Reports are not
redacted or anonymous. Keep marker lists, reports, manifests, mappings and
captures private. Console summaries contain counts and fixed errors only.

Tests use invented exports/markers and disposable I/O. A hash-verified frozen
auditor independently matches complete results on 100 stable generated trees.
A copied two-file package passed 25 fresh processes (22 direct CLI, three
controlled failures), preserving input/runtime bytes without bytecode.
Local Windows/Python 3.12.7: new 40 methods, 29 passed/11 skipped; eight native
link cases are unavailable in this sandbox, plus three POSIX-only methods.
Local short-name rejection executed. The original combined 47-method suite
remains byte-identical; 46 passed/one native-symlink skip locally.
CI requires native Windows link/junction cases; optional short-name and
platform skips remain explicit. Exact-commit results are recorded separately.

Trusted quiescent local files/parents remain required. Hostile mutation,
drive-map rebinding, live/remote/cloud providers, blocked native I/O, power loss,
all-stream backups, Git history/assets, semantic IP review and complete secret
detection remain outside acceptance. No deadline covers every filesystem call.
