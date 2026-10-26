# Python Helpers input contract

Python 3.12+, standard library only. Windows file loading requires
`helpers_windows.py` beside `helpers.py`. POSIX file loading and pure redaction
do not need that backend. Import explicitly as documented; no CLI, installer,
service or background job is added. Only existing public MIT mechanisms and
invented fixtures are selected.

## Preserved JSON and redaction behavior

`load_json_object(path, max_bytes=1024*1024)` retains its default 1 MiB limit,
maximum 16 MiB override and strict integer limit validation. Invalid limits
still raise `INVALID_LIMIT` before any I/O. The loader retains UTF-8 BOM
handling, default duplicate-key behavior, object-only results and the same
NaN/infinity literal rejection. Standard decoder exponent/number behavior is
unchanged; for example, numeric overflow is not a new finite-number policy.

Read/parse failures still raise `HelperError('JSON_OBJECT_LOAD_FAILED')` with
suppressed exception display context. Invalid path-type errors now also map to
that fixed error. Fixed messages do not anonymize caller tracebacks, retained
exception objects, decoded values or logs. Keep these private.

The sensitive-key set and entire `redact_structure` implementation remain
byte-identical, including key normalization, depth/type behavior, independent
copies and error strings. Unknown keys, free text and identifying values are
not anonymized. Existing float behavior is preserved. Redaction does not make
arbitrary input safe to publish or establish secrecy/ownership rights.

## Paths and actual reads

Input must be an ordinary stable file at a trusted path. Absolute and relative
child paths are supported; parent-traversal components are now refused rather
than normalized through an ambiguous path. Observed symlinks/reparse ancestors
and leaves, directories and special files are refused. Hardlinked ordinary
source files remain supported. Selected bytes are never parsed as Python,
imported, evaluated or launched, regardless of filename extension.

Size/identity checks precede descriptor reads and are repeated after bounded
I/O. Short reads complete or fail; early EOF, growth and observed same-size
mutation fail. One extra rejection byte can be consumed; excess bytes are not
decoded. Input content is not rewritten and no report/output file is created.
Reads can affect OS access metadata; Python may manage its ordinary import
cache separately. Byte limits are not total CPU, memory, JSON-depth, result-size
or elapsed-time quotas.

POSIX checks existing ancestors/leaf and uses available `O_NOFOLLOW` and
`O_NONBLOCK` flags plus noninheritable descriptors. Ordinary-file identity,
size/time and final pathname are compared. FIFO/socket inputs are rejected
before opening. Ancestor checks are sampled and are not an `openat` sandbox.
Trusted local storage is required; network/virtual/provider filesystems are not
accepted as equivalent proof.

Windows uses public native local-volume, path, reparse, identity and normalized
name checks, retaining observed ancestor/file handles during the read and
comparing them with a binary noninheritable CRT descriptor. UNC/device paths,
drive/root-relative forms, ADS arguments, reserved names, trailing dots/spaces,
invalid controls, surrogate text and observed 8.3 aliases are refused. Bounds
are 4,096 characters, 64 components and 255/component; supported volumes are
local fixed/removable drives. Select fully spelled private paths; temporary
paths can use aliases. Only unnamed data is read; named streams, ACLs,
ownership and topology are outside scope.

Interruption behavior remains a library exception: `KeyboardInterrupt`
propagates to the caller while owned descriptors/handles are closed. No CLI
status, retry, rollback or cleanup routine is added.

## Validation and publication

Tests use disposable fictional JSON and redaction values. Local Windows/Python
3.12.7: all five original helper methods passed; 40 new methods had 30 passes/
10 skips, comprising six POSIX-only cases and four unavailable native link/
junction cases. Local short-name rejection ran. Windows/Ubuntu Python 3.12/3.13
CI requires native Windows hardlink/symlink/junction fixtures and reports
optional short-name/platform skips separately. Other versions remain unverified.

A separate two-file library copy passed 25 fresh processes (22 direct API
consumers, three controlled failures). A hash-verified frozen public baseline
matched complete outcomes on 100 fictional JSON and 100 redaction cases. Input/
runtime bytes stayed unchanged, without bytecode or generated files in selected
trees. Local combined regression had 46 passes/one native-symlink skip;
collection had 532 passes/27 skips; documentation/JSON checks: 445 passed.

Real JSON, credentials, paths, decoded/redacted results, logs, marker lists,
reports and captures stay private. Publication uses a separate exact export,
independent auditors and manual content/rights review. No full secret-detection,
anonymity or semantic IP clearance is supplied.

Stable trusted parents remain required. Checks have pathname/open windows and
do not freeze content or directory ancestry atomically. Hostile mutation,
drive-map rebinding, live/remote/cloud providers, blocking native/filesystem
calls, hardware/power loss and all-stream/metadata backup acceptance remain
outside scope. No deadline covers every I/O.
