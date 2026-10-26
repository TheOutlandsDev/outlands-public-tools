# Server Maintenance Planner input checks

Python 3.12+, standard library only. Keep `maintenance.py` beside
`maintenance_windows.py` on Windows; POSIX does not load the Windows backend.
The backend is copied without changes from this collection's public MIT
Python Helpers input guards. No original operational script or configuration
is included.

## Preserved contract

Calendar, lifecycle and readiness rules and result fields are unchanged.
`execution_performed` is always false. Inputs are operator declarations;
the program does not collect observations, probe endpoints, execute commands,
control services or processes, register schedules, or write reports.

The input cap remains 64 KiB, measured in bytes. UTF-8 with an optional BOM,
duplicate-key rejection at every object depth and rejection of JSON's
nonstandard NaN/Infinity constants are preserved. The low-level JSON loader
still permits any JSON top-level value; plan/readiness rules require their
existing exact object shapes. Existing exponent decoding behavior is unchanged;
numeric field rules still apply. Relative ordinary paths remain supported.
Stable hard-linked regular inputs remain supported; this is read-only input,
not an exclusive output or a confidentiality guarantee.

## Path and read boundary

POSIX checks all path ancestors, refuses links/nonregular inputs, retains
available no-follow/nonblocking flags and a noninheritable descriptor, reads
at most cap plus one byte, and verifies size, identity, timestamps and link
count. Ancestor identities are resampled after reading. Parent traversal is
refused. No Windows backend is needed for POSIX use.

Windows additionally rejects UNC/device, drive-relative, root-relative,
alternate-stream, reserved-device, invalid Unicode and trailing-dot/space
spellings before native access. Native directory and primary file handles
remain open without delete sharing during the read. The unnamed data stream
is read through a checked binary, noninheritable CRT descriptor. Native/CRT
identity, normalized names, reparse attributes and final parent/file metadata
are compared. Observed short-name aliases and nonlocal drive types are refused.
Existing named streams are neither inspected nor changed when the ordinary
file is selected. These stricter Windows path restrictions are intentional.

CLI input/argument failures retain `PLAN_INPUT_INVALID`, exit 2, and no selected
path, supplied value or native error text. Windows help uses a fixed program
name. Handled Windows interruption now reports `PLAN_INTERRUPTED` and exit 130;
the library and POSIX CLI retain interruption propagation. Library exceptions
are not a redacted reporting API; keep native exceptions and diagnostic logs
private.

## Validation and limits

Fictional tests include malformed/duplicate/deep JSON, exact byte boundaries,
oversize input, short reads, early EOF, observed growth/mutation, descriptor
cleanup, nonregular paths, supported hard links, symlinks/junctions, native
identity mismatch, named streams, optional short-name aliases, and CLI rules.
Windows/Ubuntu Python 3.12/3.13 CI runs the original 15 maintenance methods and
46 additional methods. Native Windows link/junction cases are required; POSIX
methods and optional short-name availability are recorded explicitly.

Local Windows/Python 3.12.7: new suite 35 passes/11 skips (seven POSIX-only and
four unavailable native link cases); the short-name case ran. A copied two-file
runtime passed 30 fresh-process scenarios. Against frozen public source, 7,680
lifecycle, 1,344 calendar, 16 readiness and 100 decoded-JSON cases matched.
The copied runtime and selected fictional inputs stayed byte-identical without
bytecode. Exact-commit CI evidence is reviewed before merge.

Use one operator and quiescent trusted local files. Metadata checks are sampled,
not an atomic snapshot, hostile-filesystem sandbox or write freeze. Cooperative
data writers can still change a held Windows file. Drive rebinding, arbitrary
mounts, network/cloud providers, permissions/ACL privacy, all-stream inspection,
hard I/O timeouts and hostile concurrent mutation are outside validation.
There is no live server, backup/restore, scheduler, or deployment acceptance.

Actual plans, player observations, service details, endpoints, credentials,
private paths, records, audit markers, logs and reports stay private. Structural
validation does not anonymize input or establish publication or IP clearance.
