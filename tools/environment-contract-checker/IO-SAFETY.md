# Environment Contract Checker control/report I/O

Python 3.12+, standard library only. Windows needs `environment_check.py` beside
`environment_windows.py` in the existing module layout. POSIX does not load the
Windows backend. The backend is copied byte-for-byte from the collection's
public MIT Verified Transfers backend; no original setup code is included.

## Preserved boundary

Contract and observation schemas, JSON/BOM/duplicate-key rules, prerequisite
decisions, evidence/status codes, limits, between-probe budget, program suffix
rules, execute-access observations and report schema/encoding are preserved.
Target probing functions remain unchanged: they use metadata only, never read
target/program bodies, enumerate selected trees, run programs or probe services.
An operator observation remains UNKNOWN/unverified, even when reported true.

Only explicitly selected control JSON and a newly created report body are read.
Ordinary relative control paths remain supported. The 64 KiB control cap and
single-link regular-file requirement remain. The optional report is still the
only file output. Missing protected program directories remain reportable;
they are not silently created or treated as present.

## Read and write guards

Windows adds native normalized-name, identity, type, reparse, link-count and
local-volume checks to control-file I/O. Checked native file/ancestor handles
and a matched binary, noninheritable CRT descriptor remain open during reads.
UNC/device, root-relative, drive-relative, alternate-stream, reserved-device,
invalid Unicode and trailing-dot/space spellings are refused before native
control access. Observed short-name aliases are refused. These stricter I/O
path restrictions do not change the metadata-only target-probing algorithms.

POSIX retains available no-follow/nonblocking flags and rejects unsafe nodes
before opening. Read loops consume at most cap plus one byte, handle short
reads and reject observed early EOF, growth or metadata changes. Descriptors
are noninheritable; ancestor identities are resampled after reading.

Report creation preserves lexical and directory-identity exclusions, and adds
native protected-root/parent handles on Windows. Existing protected directories
are held; missing ones are sampled before/after without opening target files.
Windows handles for protected directories request metadata, not their contents.
POSIX resamples the parent and protected-directory boundary. Reports must be
new, outside the checkout and supplied protected roots, with an existing parent.

Both platforms use exclusive creation, checked short-write loops, flush and
readback verification of the intended report bytes with retained creation
descriptors. POSIX requests mode 0600 where meaningful. A partial or complete
unconfirmed **new** report can remain after a write, flush, verification or
final-boundary failure. Existence/parseability does not prove successful
completion. No overwrite, cleanup, directory creation or retry replacement
is added. Windows ACL privacy or encryption is not established.

CLI controlled error reporting remains fixed and omits native details/paths.
Handled Windows interruption now reports `INPUT_OR_REPORT_INTERRUPTED`, exit
130, with target-read/execution flags false. Library and POSIX interruption
propagation remain. Native/library exceptions and actual report IDs/metadata
remain private; they are not anonymized output.

## Evidence and limits

The original 53 tests, including the unchanged fixture generator, are preserved.
There are 50 new fictional tests: 27 portable, eight POSIX and 15 Windows.
Windows/Ubuntu Python 3.12/3.13 CI requires original native cases and additional
hardlink/symlink/junction coverage. Platform and optional short-name availability
skips are recorded explicitly.

Local Windows/Python 3.12.7: original 49 passes/four platform/native skips; new
35 passes/15 skips (eight POSIX and seven unavailable native link cases).
Optional short-name checks ran locally. A copied two-file runtime passed 24
fresh processes. Against frozen public source, 100 full-result/report-byte and
100 decoded-JSON cases matched. Target checks ran with data-open, enumeration
and native-control-backend calls forbidden. Runtime/input bytes stayed unchanged
without bytecode. Exact-commit CI evidence is reviewed before merge.

Use one operator and quiescent trusted local paths. Metadata sampling and held
handles are not a content freeze, hostile-filesystem sandbox, atomic snapshot
or I/O deadline. Drive rebinding, arbitrary mounts, remote/cloud providers,
hostile concurrent changes, all-stream inspection, ACL privacy, installed-program
acceptance and real setup/operations remain outside validation. The fixture
generator is unchanged and has its separately recorded boundary.

Actual environment inventories, installed-program paths, identities, configs,
credentials, observations, reports, audit markers, logs and captures remain
private. Structural validation and presence do not establish runtime readiness,
publication rights or complete secret/IP clearance.
