# OUTLANDS Mod Profile Activation Manager — 0.1.0

Import named verified copies into an explicitly selected local workspace,
preview activation, switch its `active` tree, retain prior copies and recover
documented interrupted operations. Original [MIT source](LICENSE), Python 3.12
or newer. The CLI uses only the standard library. The optional Tk desktop needs
separately provided compatible Tcl/Tk bindings and a working display.

Activation affects only `WORKSPACE/active`. The manager does not locate a game,
deploy into its installation, read saves, start a game or execute imported files.
Fictional examples are ordinary invented text, not installable mods. No game,
loader, gameplay, mod rights or compatibility claim follows from these checks.

## Download and safe fictional start

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/mod-profile-manager-v0.1.0):
source ZIP, checksums, executable guide, public validation JSON and build manifest.
The ZIP contains 36 reviewed source files plus their manifest, 37 members. Python,
Tk libraries, actual mods/games/saves, environments, generated workspaces and raw
logs are excluded. Verify checksums, extract to a fresh owned folder and keep
the complete module together. No pip package, admin, login or network service is
needed for the fictional CLI flow. See [USAGE.md](USAGE.md).

From this module folder, no arguments/help show static help without importing Tk
or creating a workspace:

```text
python -E -s -B profile_manager.py
python -E -s -B profile_manager.py --help
```

Choose an existing absolute private parent you control outside source. Every
workspace/example output must be fresh. After setting `$privateWork` to it,
PowerShell 5.1 or newer can run:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/profile-demo"
python -E -s -B profile_manager.py init --workspace "$privateWork/profile-workspace"
python -E -s -B profile_manager.py import-profile --workspace "$privateWork/profile-workspace" --profile orchard --source "$privateWork/profile-demo/orchard"
python -E -s -B profile_manager.py import-profile --workspace "$privateWork/profile-workspace" --profile meadow --source "$privateWork/profile-demo/meadow"
python -E -s -B profile_manager.py plan --workspace "$privateWork/profile-workspace" --action activate --profile orchard
python -E -s -B profile_manager.py activate --workspace "$privateWork/profile-workspace" --profile orchard
python -E -s -B profile_manager.py activate --workspace "$privateWork/profile-workspace" --profile meadow
python -E -s -B profile_manager.py plan --workspace "$privateWork/profile-workspace" --action deactivate
python -E -s -B profile_manager.py deactivate --workspace "$privateWork/profile-workspace"
python -E -s -B profile_manager.py status --workspace "$privateWork/profile-workspace"
```

For a POSIX shell use `python3` and the same arguments with `$privateWork` set to
the selected absolute parent. The generator creates four small fictional text
files. Import copies and hashes them without changing their sources. Switching
retains the old active copy in the operation history; deactivation retains the
current copy and records no active profile. Use a new workspace for another run.

## Commands and desktop

| Command | Effect |
| --- | --- |
| `init --workspace NEW_ABSOLUTE_PATH` | Creates a new manager-owned workspace; refuses an existing directory. |
| `import-profile --workspace ABS --profile ID --source ABS` | Creates an immutable named copy of a separate supported source tree. |
| `status` / `list` with `--workspace ABS` | Reviews active/pending/history metadata without activating or cleaning up. |
| `plan --workspace ABS --action activate --profile ID` | Validates an advisory read-only activation preview. |
| `plan --workspace ABS --action deactivate` | Validates a read-only retention/deactivation preview. |
| `activate --workspace ABS --profile ID` | Verifies a staged candidate, retains any old active tree and commits a new managed active copy. |
| `deactivate --workspace ABS` | Verifies/retains the active tree and records no active profile. |
| `recover --workspace ABS` | Inspects one pending operation and actual tree locations before resuming or retaining an aborted incomplete stage. |
| `gui` optionally with `--workspace ABS` | Explicitly opens the optional Tk desktop. |

To try the desktop on a separately verified Python/Tk distribution:

```text
python -E -s -B profile_manager.py gui
```

Initialize/import confirmations and activation/deactivation/recovery confirmations
describe the managed-workspace scope. Preview reserves nothing: activation gets
a new plan and revalidates after confirmation. Cancel leaves files unchanged.
The result panel can show bounded structured details; it never runs imported
content. Verification is synchronous and can occupy the window during a copy.
The manager does not detect/stop a running game or a loader writing into `active`.

Native Tk acceptance is separate from CLI/controller tests. A headless/unavailable
desktop does not count as a GUI pass. Release lanes require all ten native widget
tests using the measured Tcl/Tk bindings and a working display (Xvfb on Ubuntu).
`GUI-LOCK.json` records selected bundled component/script identities; do not assume
every Python version uses the same Tk major version. See the
[qualification contract](docs/QUALIFICATION.md) and actual release validation.

Exit 0 means the requested operation completed (`status: "OK"`) or help was
displayed. Exit 1 means `REVIEW_REQUIRED`; exit 2 means `INCOMPLETE`/refusal, input,
unsupported primitive or I/O failure. CLI interruption exits 130. Fixed error
codes omit upstream exception text and absolute input filenames. A pending or
incomplete result is not a successful activation.

## Drift, recovery and retained copies

Profile and active trees must match complete file/directory inventories and
SHA-256 hashes. Changed, missing, unexpected or unsupported data requires review;
activation does not overwrite it to hide drift. Plans hold the nonblocking OS
lock only while checking; a prior preview is neither a reservation nor a token
authorizing later mutation. Busy workspaces refuse another operation.

After interruption preserve the whole workspace, inspect `status` and explicitly
run `recover`. Do not edit state, remove the lock, discard an intent, or delete a
stage/previous tree to bypass a refusal. Recovery checks the actual tree locations,
including rename-before-journal windows. A verified stage may finish activation;
an absent/incomplete stage can be retained as `aborted_incomplete_stage` while
the old active state remains intact. Unknown/inconsistent data stays held.
The [exact state/recovery format](docs/FORMAT.md) defines the supported cases.

An empty/temp-only folder left before the first intent is retained preparation,
reported as `RETAINED_PREPARATION`; it counts toward the operation limit but does
not invent pending work. Other content/referring missing intent is refused.
History sorts random operation IDs, not chronology. No automatic deletion,
profile replacement, retained-copy purge, cleanup, shell/network or game-launch
command exists. Retention consumes disk space; keep independent backups.

## Bounds and limitations

Profile IDs match `[a-z][a-z0-9-]{0,39}`. Plain payload paths use the portable
ASCII grammar in [FORMAT.md](docs/FORMAT.md), with casefold-unique file/directory
names. Links/reparse routes, hardlinks, named streams, special objects, traversal,
network/device paths, overlapping source/workspace trees and unsupported names
are refused. Inputs must be quiescent and local.

| Item | Limit |
| --- | --- |
| Profiles / recorded operations | 32 / 250, including aborted operations and retained preparation. |
| Regular files / directories per profile | 1,024 / 2,048; at least one file required. |
| One file / aggregate profile bytes | 8 MiB / 64 MiB. |
| Relative path / component | 512 / 120 characters. |
| One metadata JSON | 1 MiB with bounded collections/schema. |

Commits use Windows native no-replace rename or Linux `renameat2(RENAME_NOREPLACE)`;
unavailable primitives fail closed. Known metadata files have checked replacement.
These checks rely on trusted ancestors and cooperative/quiescent files, not an
OS sandbox or an atomic hostile-writer snapshot. Flush/readback requests do not
establish power-loss durability. Failed operations can leave pending metadata,
partial stages and retained trees; no universal rollback guarantee is made.

Copies preserve supported file bytes/directory layout rather than full owners,
ACLs, timestamps, streams or external metadata. No filesystem rights scrub,
authentication, encryption, anonymity, save protection or cross-platform security
verdict is provided. Names, relative paths, IDs, hashes and GUI-visible paths can
identify content. Keep operational records private. Read [SECURITY.md](SECURITY.md).

## Evidence and contributions

The [qualification contract](docs/QUALIFICATION.md) preserves all 118 originals
and adds thirty copied-runtime CLI checks per Windows/Ubuntu Python 3.12–3.15
lane. Its independent executable guide uses invented files only and never opens
Tk; native-widget evidence is recorded separately. The
[historical validation](docs/VALIDATION.md), [provenance](docs/PROVENANCE.md) and
[example record](examples/README.md) remain unchanged.

Submit a fictional reproduction through [GitHub Issues](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Include exact source/Python/OS/Tk versions, commands and expected/observed behavior.
Exclude actual games, mods, saves, machine paths, journals, screenshots or input
rights data unless separately reviewed. See [CONTRIBUTING.md](CONTRIBUTING.md).
