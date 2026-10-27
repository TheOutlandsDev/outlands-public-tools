# Release Preflight file handling

Python 3.12+, standard library only. On Windows keep `preflight.py` and
`preflight_windows.py` together in the existing `tools/release-preflight`
layout. The main module identifies the collection root from that layout.
POSIX does not load the Windows backend.

## Preserved behavior

Manifest/launcher JSON formats, exact external hash pins, metadata/payload/count
limits, canonical relative-name rules, case collisions, exact candidate file
sets and selected-current ADD/REPLACE/UNCHANGED decisions are preserved.
Unlisted current files are not enumerated or selected for deletion. Launcher
arguments are checked structurally and omitted from results; executable bytes
are only hashed. No executable, shell, service, scheduler, installer or network
operation is invoked. Results retain `execution_performed: false`.

The optional private report remains the only output. Its JSON encoding and
content are preserved. Output must be new, with an existing parent outside the
collection, candidate and selected current roots. There is no overwrite,
automatic directory creation, deployment, rollback or automatic cleanup.
Stable hard-linked inputs and linked/reparse paths remain refused.

## Checked reads and directories

Windows rejects UNC/device, drive-relative, root-relative, alternate-stream,
reserved-device, invalid Unicode and trailing-dot/space paths before native
access. Native directory/file handles check normalized names, file types,
reparse attributes, identities and link counts. A checked binary,
noninheritable CRT descriptor is used for streaming hashes. Read-only native
selection checks do not consume payload bytes. Observed short-name aliases
and nonlocal drive types are refused; these path restrictions are stricter
than the previous metadata-only Windows checks.

Candidate/current root scopes and each enumerated folder retain checked native
ancestors. Existing ancestors of missing current paths are checked without
creating directories. Native names supplement lexical root separation and
report exclusion checks. Named streams are not accepted as arguments; selecting
an ordinary file neither reads nor changes its other streams.

POSIX preserves available no-follow/nonblocking flags and refuses nonregular
files before opening. Descriptors are noninheritable. Ancestor identities are
resampled after reads/enumeration; size, identity, modification/change timestamps
and link counts are checked. Hash reads consume at most their limit plus one
byte. These checks strengthen filesystem observations without changing pins.

## Report creation and failures

Both platforms use exclusive new-file creation, write loops that handle short
writes, flush and readback verification. POSIX requests mode 0600 where
meaningful. Windows checks native output/repository/input names and held parent
handles; file metadata and link counts are checked. No Windows ACL or encryption
privacy is established. A zero write, readback/flush error or final guard failure
prevents success. A partial or complete **unconfirmed new** report can remain;
retain it privately for inspection. Existence or parseability does not prove
successful completion. No retry replaces that existing file.

Controlled CLI failures omit selected paths, arguments and native error text.
Windows help uses a fixed program name; handled Windows interruption reports
`PREFLIGHT_INTERRUPTED`, exit 130. Library and POSIX interruption propagation
remain. Native/library exceptions and report bodies are private information,
not a redacted output API.

## Evidence and limits

The original 28 preflight methods remain unchanged. There are 47 new fictional
I/O methods: 22 portable, eight POSIX and 17 Windows. Windows/Ubuntu Python
3.12/3.13 CI requires the original native tests and additional hardlink,
symlink and junction cases. Only platform-specific and optional short-name
availability skips are accepted on Windows.

Local Windows/Python 3.12.7: original 26 passes/two unavailable native skips;
new 31 passes/16 skips (eight POSIX and eight unavailable native link cases).
The optional short-name case ran locally. A copied two-file runtime passed 24
fresh processes. Across 100 fictional package trees, verify/plan/launcher
results and report bytes matched frozen public source. Runtime/input bytes
stayed unchanged without bytecode. Comparisons are retained privately and bound
to the exact publication files. CI evidence is reviewed before merge.

Use one operator and quiescent trusted local trees. Retained handles and sampled
checks do not freeze content or establish an atomic multi-file snapshot,
hostile-filesystem sandbox, I/O deadline or application-consistent backup.
Concurrent hostile mutation, drive rebinding, arbitrary mounts, remote/cloud
providers, all-stream inspection, ACL privacy, power loss, live service behavior
and deployment remain outside validation. A plan is not a reservation; recheck
inputs before a separate authorized update.

Actual manifests, package origins, launcher arguments, deployment paths,
credentials, operational configuration, private records, logs, audit markers,
reports and captures stay private. Byte agreement and schema validation do not
anonymize data or establish ownership, safety, authorship or publication rights.
