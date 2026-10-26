# Project Workspace filesystem contract

Python 3.12+, standard library only. Keep `workspace_windows.py` beside
`workspace.py`. This update adapts existing public MIT mechanisms and invented
fixtures. No original private implementation, template, record, configuration,
credential, capture or asset is bundled.

## Plan and compatibility

The original POSIX creation body, path/source checks, neutral control template,
folder/name rules and six workspace regression methods remain unchanged.
POSIX code keeps its prior behavior and limitations. Windows retains layout,
summary keys, the 16 MiB source limit, opaque input copies, size/SHA-256 metadata,
and platform text newline encoding. No option is added.

The default remains plan-only: it validates the parent/name/destination and
reads an optional source for validation, but creates nothing. Reading can affect
OS access metadata; this is not a no-read plan. Planning does not reserve a
destination or guarantee that a later creation will succeed.

## Windows reads and paths

Supported paths use local fixed/removable drives, an existing fully spelled
parent and a neutral lowercase workspace name. UNC/device spellings, ADS
arguments, drive/root-relative forms, traversal, reserved names, trailing
dots/spaces, invalid controls, surrogate text and observed aliases/reparse points
are refused. Limits are 4,096 characters, 64 components and 255/component.
Relative child paths remain supported against the working directory.

Native local-drive/type/name/identity checks retain root/ancestor/file handles
through scoped operations. Binary noninheritable descriptors are compared with
the native file identity. Reads are bounded before and during I/O and checked
afterward. Growth can consume one extra rejection byte; excess bytes are not
accepted. Changed parents/files require failure if observed. A rename may be
blocked or detected afterward; handle retention is not a universal rename lock.

Inputs are opaque ordinary unnamed file data. Source hard links remain allowed;
the selected bytes are read without rewriting either name. Named streams, ACLs,
ownership, topology and timestamps are not backed up. No selected input is
parsed, imported, executed or launched. A successful copy can still contain
private data; generated workspaces must stay private.

## Creation and failure

New directories use exclusive creation and retained observed directory handles.
Only directories created by this invocation are reused for shared layout
parents. Existing destinations/children are refused. Every output, including
`.gitignore`, `SOURCE.json` and `CONTROL.md`, uses exclusive new-file creation,
short-write handling, requested flush and observed size/name/identity/link-count
checks. Each output is read back and compared with expected bytes; outputs with
extra hard links are refused. Both intake copies retain exact bytes.

The ignore file is attempted early. It can be absent, incomplete or ineffective
after a failure, and Git ignore rules are not confidentiality controls. Parent
ACLs and OS/Python version govern permissions; confidentiality is not audited
and a Unix mode equivalent is not promised.

Failure or Windows interruption leaves new partial or complete-looking but
unconfirmed output for private inspection. No existing data is replaced and no
automatic recursive cleanup/rollback occurs. A fully populated tree, matching
hashes or the static control text does not prove successful completion. Check
the command result. Handled Windows interruption returns 130 with fixed
`ERROR` / `WORKSPACE_INTERRUPTED`; other handled I/O/input errors return 2 with
`WORKSPACE_INPUT_OR_OUTPUT_ERROR`. Console errors omit paths and exception text.
POSIX interruption behavior is preserved.

## Evidence and limits

Tests use disposable fictional inputs. Local Windows/Python 3.12.7: all six
original workspace methods passed; 40 new methods had 29 passes/11 skips.
Eight native link/junction cases were unavailable locally, plus three POSIX-only
cases; local short-name rejection ran. Windows/Ubuntu Python 3.12/3.13 CI
requires native Windows link/junction cases; optional short-name availability
and platform skips remain explicit. Other Python versions remain unverified.

A separate two-file runtime copy passed 21 fresh-process scenarios (18 direct
CLI, three controlled failures). Against a hash-verified frozen public baseline,
100 fictional cases matched complete layouts and bytes. Input/runtime bytes
stayed unchanged without bytecode. The original combined 47-method suite had
46 passes/one native-symlink skip locally; collection checks had 532 passes/27
skips. Documentation/JSON checks: 441 passed.

Exact publication hashes, standalone walkthrough results and CI evidence are
reviewed separately. Real inputs, generated workspaces, marker lists, reports,
captures and audit dispositions stay private. A separate export needs its own
content/rights review.

Trusted stable local parents remain required. These are sampled observations
with pathname/create/open windows, not an atomic transaction or hostile
filesystem sandbox. Drive-map rebinding, cooperative mutation between samples,
live/remote/cloud providers, blocking native calls, hardware/power loss,
all-stream backups, complete secret detection and semantic IP clearance remain
outside acceptance. No deadline covers every filesystem call.
