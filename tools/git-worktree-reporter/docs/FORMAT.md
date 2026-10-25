# Input, report and operational contract

## Supported inputs

CPython 3.12-3.14, trusted Git 2.49+, a trusted local ordinary worktree or linked
worktree, UTF-8 Git names and stable inputs are required. Bare repositories,
subdirectories masquerading as the selected root, linked filesystem components,
UNC/device paths, custom `core.worktree`, configured filter drivers, local config
includes, partial clones, sparse configuration, shallow history, grafts and
alternate object stores are outside this edition. The selected executable must
be an ordinary file; Windows requires an `.exe`, not an implicit batch shell.

The worktree `.git` directory or Git-written `gitdir:` file and optional
`commondir` file establish supported metadata locations. Raw pointer routing syntax
is validated before pointer filesystem observation; the normalized absolute route
receives local-path checks, and link checks also retain unnormalized components.
Symbolic-link resolution does not silently erase a linked component. These paths remain trusted owner-controlled
input. Checks do not prevent adversarial replacement or mount-point races.

## Git invocation

No command shell is used. The runtime never discovers executables from `PATH`.
It executes only the supplied Git and these command groups:

1. `--version` to require the supported Git minimum.
2. `config --null --name-only --list --no-includes` for preflight key checks.
   Config values, including remote URLs, are not requested or reported.
3. `rev-parse --show-toplevel --is-inside-work-tree` to require the exact root.
4. `status --porcelain=v2 -z --branch --ahead-behind --untracked-files=all
   --ignored=no --ignore-submodules=all --renames` for observed status.

Global/system configuration is disabled. Inherited `GIT_*`, `GCM_*`, `SSH_*`,
pager and common loader-injection variables are removed. Protected command-line
settings disable optional locks, replacement objects, lazy fetching, protocols,
hooks, FSMonitor, untracked cache, maintenance/automatic GC, external diff, global
attributes/ignore paths and submodule recursion. Git's `safe.directory` ownership
protection is not weakened. No fetch, push, credential helper, checkout, staging,
commit, reset, cleanup or remote query is issued by the inspector.

Preflight refuses keys for filters, includes, custom worktree redirects, partial
clones/promisor config, sparse config, alternate-ref commands and custom diff
command/textconv. Unsupported includes are not expanded for preflight. This
edition refuses locally configured Git LFS drivers, but does not inventory disabled
global/system filter drivers or validate LFS objects. A globally filtered worktree
can have different isolated status. Normal user status can also differ because other global/system policy is isolated. Git may read file
bodies internally to compute status. This is not a claim that arbitrary Git
code/configuration is safe or that every future helper mechanism is covered.

Each owned child has 15 seconds after startup, at most 8 MiB stdout (config query
1 MiB; version 4 KiB), and 64 KiB stderr. Owned POSIX process groups or Windows
kill-on-close jobs are terminated on bounds/failure. Windows job assignment occurs
immediately after process creation, not as an atomic hostile-process sandbox.
Native process startup and filesystem operations have no hard real-time limit.
The trusted executable must not deliberately evade ownership or spawn untrusted
code. No broad process-name killing occurs.

Before/after SHA-256 comparisons cover observed `HEAD`, index, worktree/common
config, packed refs and pointer control files when present. Each metadata file is
limited to 32 MiB. Detection of an observed control change fails the report.
This does not lock all worktree files, every loose ref or the whole object store.

## Porcelain parser

Version 2 NUL records are required. The supported records are ordinary tracked
`1`, renamed/copied `2` with the following original-path record, unmerged `u`,
untracked `?`, and documented branch headers. Unknown optional headers are counted
without echoing text. Unknown entry records, malformed/duplicate headers or paths,
invalid statuses, modes, object IDs, scores, non-UTF-8 names and truncated records
fail with a fixed code. SHA-1 and SHA-256 object-ID lengths are accepted.

Names are relative data, never joined to a filesystem root. Portable path limits
exclude leading slash/backslash, drive-looking paths, empty/dot/parent components
and NUL. Supported UTF-8 spaces/tabs/newlines remain data and are JSON escaped.
Record names are at most 4,096 characters; entries at most 10,000. Some legal Git
or POSIX names are intentionally outside this portable report subset.

## JSON report

`schema_version: 1` identifies the current report. `head_state` is `branch`,
`detached` or `unborn`; no commit gives `head_oid: null`, and a detached head gives
`branch: null`. `upstream` contains a stored ref name and integer ahead/behind
counts when Git provides them. Missing comparison data is `null`/`unavailable`,
not an invented zero. All counts are based on local stored objects/refs only.

Entries contain relative `path`, kind, index/worktree status, optional original
path/similarity and observed submodule marker. Submodule contents are not scanned.
`counts` has untracked, unmerged, staged and unstaged counts. Staged/unstaged
counts exclude unmerged entries but can overlap each other. `entry_count` is the
unique number of emitted paths. Rows use ordinal path order.

The report also records the raw-status SHA-256, supported Git version, coverage,
limits, isolated-config policy, and `observed_control_files_unchanged`. The latter
describes only the observed files listed above, not a snapshot of the entire repo.
The 8 MiB encoded report limit is checked before creating a new directory.

## Outputs, errors and privacy

The new output must have an existing trusted parent and be outside the worktree
and linked/common Git metadata. Existing input/output-parent directories are
validated for links before canonicalization; their physical spellings are then
compared, so Windows DOS short/long aliases do not bypass containment. Canonical
paths are validated again and used for output creation. These observations are
not a race-proof filesystem transaction. `report.json` and `MANIFEST.json` use exclusive
creation; existing paths are never replaced. POSIX requests owner-only storage;
Windows inherits parent ACLs and does not establish privacy from mode bits.
Partial I/O failure may leave a new incomplete directory and exits 2.

Exit 0 means supported status was recorded, including dirty work. Exit 2 means
incomplete input/config/format/limit/change/output handling. Stdout is counts or a
stable error code. Raw Git errors, source contents, absolute worktree paths and
remote URLs are omitted. Filenames, refs and object IDs can still be private.
Review reports separately before sharing; no report is automatic MIT clearance,
secret screening, content backup, push verification or a restoration guarantee.

Primary references: [Git status/porcelain](https://git-scm.com/docs/git-status),
[Git command/environment options](https://git-scm.com/docs/git),
[Git configuration](https://git-scm.com/docs/git-config), and
[attribute filter behavior](https://git-scm.com/docs/gitattributes).
