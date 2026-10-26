# Managed workspace, formats and recovery

Schema version 1 is a local operational format, not a public report or a game
configuration format. Select a new absolute local workspace under an existing
trusted parent. Do not hand-edit manager metadata or import a workspace as a
profile. Read [README](../README.md) for command and desktop walkthroughs.

## Layout

```text
workspace/
  owner.json
  state.json
  .lock
  profiles/
    orchard/
      manifest.json
      payload/
        README.txt
        config/demo.ini
  operations/
    <32-lowercase-hex-operation-id>/
      intent.json
      stage/       (only where an operation needs it)
      previous/    (retained prior active tree, where applicable)
  active/          (present only while a profile is active)
```

`owner.json` has exactly `schema_version: 1` and `workspace_id`, a generated
32-character lowercase hexadecimal ID. `state.json` has exactly
`schema_version: 1`, `active_profile` (profile ID or JSON null) and `pending`
(operation ID or null). A new workspace has no active profile or pending work.
The persistent one-byte `.lock` supports the operating-system lock; its
existence alone does not mean a process currently holds that lock.

Profiles are imported copies. There is no profile replacement command. A profile
directory contains exactly `manifest.json` and `payload`. A started operation contains
`intent.json` and, when needed, a stage or retained previous tree. Import stages
contain a manifest and payload before becoming a profile; activation stages
contain the candidate file tree directly. Do not move these directories manually.
Manager-owned temporary metadata names may remain after an interrupted write;
they are not permission to introduce arbitrary extra workspace entries.

An operation folder can be created just before the first intent is written.
If the process stops at that point, only an empty folder or a folder containing
bounded valid `.tmp-<32-lowercase-hex-id>` regular metadata temporary files is
recognized as retained preparation. It must not be referenced by `state.pending`.
No intent, stage, payload or previous active tree is inferred from this folder.
An unknown file/tree or an intent missing from a referenced pending operation
still causes refusal. Preparation folders are retained without automatic cleanup.

## Profile names, paths and limits

A profile ID matches `[a-z][a-z0-9-]{0,39}`. It is case-sensitive and has at most
40 ASCII characters. Slugs are identifiers, not a way to select external paths.

Payload names use `/`-separated relative components. Each component matches
`[A-Za-z0-9_. +@()\-]{1,120}`, with no leading/trailing spaces, trailing dot,
empty component, `.` or `..`. Windows reserved device names and their extensions
are refused, case-insensitively: CON, CONIN$, CONOUT$, PRN, AUX, NUL, COM0-COM9
and LPT0-LPT9 (including the reserved superscript variants). Backslashes,
absolute paths and drive/stream syntax cannot form a payload name. File and
directory names must be unique under case folding, including across types.

| Bound | Limit |
| --- | --- |
| Profiles | 32 |
| Regular files per profile | 1,024; at least one is required |
| Directories per profile | 2,048, including empty nested directories |
| One file | 8 MiB (8,388,608 bytes) |
| Aggregate profile bytes | 64 MiB (67,108,864 bytes) |
| Relative path | 512 characters, including separators |
| Path component | 120 characters |
| Recorded operations | 250, including imports, aborted operations and retained preparations |
| One metadata JSON document | 1 MiB, with bounded parser collections |

Payload file bytes are opaque; this tool neither interprets nor executes them.
Links, reparse routes, hardlinked regular files, special objects, named Windows
streams, network/device paths, ambiguous Windows paths and source/workspace
overlap are refused. Sources must be quiescent and separate from the workspace.
Byte copies do not preserve or scrub full metadata: owners, inherited ACLs,
timestamps, alternate streams and external metadata are outside the copy claim.

## Manifest

The exact manifest fields are `schema_version`, `directories`, `files`,
`total_bytes` and `digest`. `schema_version` is integer 1. `directories` is a
lexically sorted list of supported relative directory names. `files` is a list
sorted by `path`; each record has exactly `path`, `bytes` (nonnegative integer)
and `sha256` (64 lowercase hexadecimal characters). Every non-root parent is
listed in `directories`. `total_bytes` equals the sum of file byte lengths.
The root itself is implicit and is not a directory record.

`digest` is SHA-256 of the remaining four fields encoded with the engine's
canonical JSON: sorted keys, compact separators, ASCII escapes, finite JSON
values only, UTF-8 bytes and one trailing newline. Hashes verify byte consistency;
they do not establish authenticity, input rights, safety or game compatibility.
Unexpected, missing and changed files or directories fail complete-tree checks.
Booleans are not accepted in integer fields. Duplicate JSON keys, extra schema
fields and invalid values are refused rather than repaired implicitly.

## Operation records and observable state

Each `intent.json` has exactly `schema_version`, `id`, `action`, `profile`,
`before`, `phase` and `outcome`. `action` is `import`, `activate` or `deactivate`.
`profile` is the target profile ID for import/activation and null for
deactivation. `before` records the previous active profile or null.

Phases are `intent`, `ready`, `previous_retained`, `active_committed`,
`state_saved`, `complete` or `aborted`; not every action traverses every phase.
Terminal `complete` has outcome `complete`; terminal `aborted` has outcome
`aborted_incomplete_stage`. Nonterminal outcomes are null. Phase names are
journal observations, not proof that the next filesystem effect did not happen.
There is at most one pending operation. Recovery also recognizes an unfinished
intent if a crash occurred before its pending reference was saved.

A retained pre-intent folder has no `intent.json`; its synthesized history record
has action `preparation`, profile null, and phase/outcome `retained_preparation`.
It is not an unfinished mutation. Status reports `REVIEW_REQUIRED` with issue
`RETAINED_PREPARATION`, but this diagnostic does not itself block verified plans
or future mutations. If no other operation is pending, recovery checks current
state and returns `no_pending_operation`; it does not remove the preparation.

`status`/`list` returns the active profile, pending ID, profile counts/byte totals,
bounded operation history and fixed-code review issues. History is sorted by
operation ID, **not chronologically**; there are no wall-clock timestamps in
this schema. CLI/desktop structured results omit absolute paths and raw payload
bytes, but IDs, names, hashes and relative paths in private manifests can still
identify content. Keep the whole workspace private.

## Normal transition and interruption

All APIs use a nonblocking OS file lock over the existing known regular `.lock`
file (`msvcrt` on Windows, `fcntl` on Linux). A busy lock is a refusal. A plan
validates under that lock, then releases it. Activation rechecks actual state;
a previous plan reserves nothing and cannot authorize a later change by itself.

Import inventories and hashes the source, records intent, copies an independently
verified candidate, and renames that stage to a previously absent profile path.
Activation records intent and verifies a fresh candidate stage. If an active
tree exists, it is checked and retained under `operations/<id>/previous` before
the new stage becomes `active`. Deactivation verifies and retains the active
tree, then records no active profile. Imported originals and previous trees are
not deleted. Already-active/already-disabled requests can return their explicit
no-change outcomes without adding a new operation, but still validate state.

Directory commits use Windows native no-replace rename or Linux
`renameat2(RENAME_NOREPLACE)`. Unavailable primitives fail closed; there is no
replacement fallback. Metadata replacement is limited to known manager files
and checked paths. This depends on trusted local ancestors and quiescent data;
it is not a sandbox against malicious concurrent ancestor changes. Requested
flushes and readback checks are not a power-loss durability guarantee.

## Recovery and retained data

After an interruption or I/O failure, preserve the workspace, inspect `status`
and use the explicit `recover` command or desktop confirmation. Do not remove
the lock, state, intent, stage or retained tree to force a fresh operation.
Other mutations remain blocked while an operation is pending.

Recovery compares actual tree locations and manifests, including a crash after
a rename but before the next journal update. It can resume a complete verified
import/activation candidate, finish a verified deactivation or clear a terminal
pending reference. An absent/incomplete candidate can be recorded as
`aborted_incomplete_stage` only when the prior active state is still intact.
Its partial stage remains retained; it is never deployed or deleted. A malformed,
unexpected or drifted candidate/previous/active tree requires review and can be
refused without automatic repair. With no pending operation, recovery checks
the current state and returns `no_pending_operation`.

Recovery can itself be interrupted; rerun status and recovery against the
preserved workspace. Successful recovery means the specific verified transition
was completed or safely recorded as aborted, not that arbitrary disk damage was
repaired. Fault hooks exist only in the Python API for generated tests; no CLI
flag or environment variable injects failures into normal data.

Retained data consumes storage. There is no delete/purge/compaction/export of
history and no automatic cleanup when the 250-operation bound is reached.
Plan storage and keep an independent backup; use a separately chosen fresh
workspace if starting another supported history. This format does not claim a
complete backup of an application, game installation or operating system.
