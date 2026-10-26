# OUTLANDS Mod Profile Activation Manager

Keep named, verified mod-profile copies in an explicitly selected local
workspace. Preview activation, build a verified `active` copy, switch profiles,
retain the previous active tree, and recover interrupted managed operations.
Use either the CLI or the optional Tk desktop interface.

This original [MIT source](LICENSE) manages **its own workspace**. Imported source
folders remain unchanged. Activation affects `WORKSPACE/active`; it does not
automatically detect or deploy into an existing game installation. A game loader
may be configured separately to read that managed path if it supports doing so.
The fictional examples are not installable mods and prove no game compatibility.

## Install and choose a private workspace

Use **CPython 3.12 or newer**, Windows or Linux. The CLI uses only the standard
library; no `pip install`, Android/game SDK, administrative rights, account or
network service is needed. The optional desktop requires separately installed
Tk/Tcl bindings. Keep the complete module folder together when copying it.

Clone or download [outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools)
and enter `tools/mod-profile-manager`. `python --version` checks your runtime.
Use `python3` where that is your Python 3 command. No arguments and `--help`
show static help without creating a store, importing Tk or scanning a game:

```text
python -B profile_manager.py
python -B profile_manager.py --help
```

Keep all real inputs, generated fixtures, workspaces, manifests, operational
results and retained copies **outside this source checkout**. Choose an existing
absolute private parent directory you control; see the collection's
[workspace guide](../../docs/PRIVATE-WORKSPACE.md). The new workspace path must
not already exist. Source imports must be separate from the managed workspace.

## Try the complete fictional CLI example

Windows PowerShell, after setting `$privateWork` to that existing private parent:

```powershell
python -B examples/generate.py --output "$privateWork/profile-demo"
python -B profile_manager.py init --workspace "$privateWork/profile-workspace"
python -B profile_manager.py import-profile --workspace "$privateWork/profile-workspace" --profile orchard --source "$privateWork/profile-demo/orchard"
python -B profile_manager.py import-profile --workspace "$privateWork/profile-workspace" --profile meadow --source "$privateWork/profile-demo/meadow"
python -B profile_manager.py plan --workspace "$privateWork/profile-workspace" --action activate --profile orchard
python -B profile_manager.py activate --workspace "$privateWork/profile-workspace" --profile orchard
python -B profile_manager.py status --workspace "$privateWork/profile-workspace"
python -B profile_manager.py activate --workspace "$privateWork/profile-workspace" --profile meadow
python -B profile_manager.py plan --workspace "$privateWork/profile-workspace" --action deactivate
python -B profile_manager.py deactivate --workspace "$privateWork/profile-workspace"
python -B profile_manager.py list --workspace "$privateWork/profile-workspace"
```

Linux shell, after setting `private_work` to that existing absolute parent:

```sh
python3 -B examples/generate.py --output "$private_work/profile-demo"
python3 -B profile_manager.py init --workspace "$private_work/profile-workspace"
python3 -B profile_manager.py import-profile --workspace "$private_work/profile-workspace" --profile orchard --source "$private_work/profile-demo/orchard"
python3 -B profile_manager.py import-profile --workspace "$private_work/profile-workspace" --profile meadow --source "$private_work/profile-demo/meadow"
python3 -B profile_manager.py plan --workspace "$private_work/profile-workspace" --action activate --profile orchard
python3 -B profile_manager.py activate --workspace "$private_work/profile-workspace" --profile orchard
python3 -B profile_manager.py status --workspace "$private_work/profile-workspace"
python3 -B profile_manager.py activate --workspace "$private_work/profile-workspace" --profile meadow
python3 -B profile_manager.py deactivate --workspace "$private_work/profile-workspace"
python3 -B profile_manager.py list --workspace "$private_work/profile-workspace"
```

The generator creates four tiny text files under two source directories. Each
profile has a fictional README and `config/demo.ini`. Import creates verified
private copies, with profile IDs `orchard` and `meadow`. Planning reads the
selected managed state and reserves nothing. Activation performs a new check.

After the first activation, status reports `active_profile: "orchard"`. Switching
to meadow changes it to `"meadow"` and retains the previous orchard active tree.
Deactivation records `active_profile: null` while retaining the meadow tree.
The imported profiles and original `profile-demo` source files still exist.
Use a different new workspace for a second walkthrough; existing destinations
are refused. See [example expectations](examples/README.md).

## Desktop walkthrough

From the module directory:

```text
python -B profile_manager.py gui
```

Or open the already initialized fictional workspace explicitly:

```powershell
python -B profile_manager.py gui --workspace "$privateWork/profile-workspace"
```

1. Enter the absolute workspace path. **Browse** selects an existing workspace.
   To initialize one, type a new absolute path under an existing parent and
   press **Initialize new**; review the confirmation before creation.
2. Select a source folder, enter a lowercase profile ID, and press **Import copy**.
   Import copies supported file bytes and verifies them; it does not move or
   delete the source. A reused profile ID is refused.
3. **Refresh status** fills the profile list and shows the active/pending state.
   Select a list entry to use its ID.
4. **Preview activation** shows the read-only plan. **Activate…** obtains a new
   plan, asks you to confirm the managed workspace scope, then revalidates and
   changes managed state. A preview is not an authorization token or reservation.
5. **Deactivate…** previews and confirms retention of the managed active tree.
   **Recover pending…** asks before attempting documented recovery.

The desktop's result panel defaults to readable summaries of state, plans,
operation results and review items. Select **Show structured details** to see
the bounded JSON result, including operational IDs. These results remain private;
the desktop does not render or execute imported content. Verification runs
synchronously; a large supported copy may temporarily occupy the window. Close
other programs using managed files before a change. The manager does not detect
or stop running games for you.

Tk is optional. On Linux, run desktop tests with a working display or `xvfb-run`.
Install Tk through your operating system's normal Python/Tk distribution if it
is missing. An unavailable GUI returns a fixed `GUI_UNAVAILABLE` result; the CLI
remains independent. Native GUI fixtures are distinct from actual game tests.

## Commands, exits and effects

Every CLI command takes an explicit absolute `--workspace`, except `gui` may
start with an empty workspace field. Commands emit JSON, apart from static help.

| Command | Effect |
| --- | --- |
| `init` | Creates a new manager-owned workspace; never adopts an arbitrary existing directory. |
| `import-profile --profile ID --source ABS` | Copies and verifies a new named profile from a separate regular-file tree. |
| `status` / `list` | Reviews profile/active/pending/history metadata; no activation or cleanup. |
| `plan --action activate --profile ID` | Checks current state and selected profile and returns an advisory activation plan. |
| `plan --action deactivate` | Checks current active state and returns a retention/deactivation plan. |
| `activate --profile ID` | Stages a verified copy, retains an old active tree and commits the new managed active tree. |
| `deactivate` | Retains the verified active tree and records no active profile. |
| `recover` | Inspects a pending operation and verifies actual trees before resuming or retaining an aborted incomplete stage. |
| `gui` | Opens the optional desktop only when explicitly requested. |

There is no delete, profile replacement, retained-copy purge, live game launch,
automatic installation, shell execution, network or upload command. To activate
a previous named profile again, select its immutable imported copy and activate
it normally. Every switch creates another retained history entry. This is not
an in-place content editor or a generic file mover.

| Exit | Meaning |
| --- | --- |
| 0 | Requested operation completed with `status: "OK"`, or help was displayed. |
| 1 | `REVIEW_REQUIRED`: read the fixed issues/pending/drift observations. |
| 2 | `INCOMPLETE`: invalid/refused input, unsupported state/primitive, limit or I/O failure. |
| 130 | CLI interruption: review status and documented recovery before further changes. |

CLI errors use fixed codes without upstream exception text or absolute filenames.
An incomplete operation is not a successful activation. It can leave a pending
journal, partial stage or retained copy that must be reviewed. Keep these intact.

## Drift, interruption and recovery

Imported payloads and the active tree are verified against their declared file
and directory inventories. Unexpected, missing, changed, linked or unsupported
objects require review; they are not overwritten or silently removed. Activation
is not a way to suppress a drift finding. A game loader writing into `active`
can cause drift, so use quiescent data and understand your loader separately.

If a process is interrupted or reports an I/O failure, inspect:

```powershell
python -B profile_manager.py status --workspace "$privateWork/profile-workspace"
python -B profile_manager.py recover --workspace "$privateWork/profile-workspace"
```

Recovery checks actual stored manifests and tree locations, including a crash
between a rename and the next journal update. A verified completed stage may
resume activation. An incomplete stage can be retained with outcome
`aborted_incomplete_stage` if the previous active state remains intact. Unknown,
changed or inconsistent data remains held. Recovery does not imply every possible
filesystem failure can be repaired automatically. Read [the state and recovery
contract](docs/FORMAT.md) before managing valuable content.

One operation can be pending at a time. Other mutations are refused until it is
recovered. All API calls use a nonblocking operating-system lock; a busy workspace
is refused rather than running concurrent operations. Plans are read-only checks,
not locks held across commands. Do not edit state/journals to bypass a refusal.
Requested flushes, hash matches and readback are not proof of power-loss
durability or a host-independent atomic snapshot.

A process can stop after creating an operation folder but before writing its
first intent. An empty folder, or one containing only valid bounded metadata
temporary files, is retained and reported as `RETAINED_PREPARATION`. It counts
toward the 250-operation limit. This diagnostic makes status require review but
does not represent pending work: verified plans and changes may continue, and
recovery with no other pending operation reports `no_pending_operation`. Unknown
content or an intent missing from an operation referenced by state is still
refused. The manager does not delete these retained preparation folders.

## Supported files, bounds and storage

The selected source is a bounded plain-file tree. The engine refuses links,
reparse routes, hardlinked files, special objects, path traversal, case collisions,
unsupported names, UNC/device/stream paths and source/workspace overlap. Supported
names are deliberately portable; see [the exact path grammar](docs/FORMAT.md).
Source bytes are copied without a claim to preserve owners, ACLs, alternate
streams, timestamps or other filesystem metadata. The active path is fixed
inside the managed workspace; files elsewhere are outside this program's state.

Limits are **32 profiles**, **1,024 files/profile**, **2,048 directories/profile**,
**8 MiB/file**, **64 MiB/profile**, **512 characters/relative path** and
**250 operations**, including imports and retained preparations.
Collection/schema limits are detailed in [format](docs/FORMAT.md). Unsupported
or over-limit inputs are refused, not silently truncated. These are limits for
small managed profiles, not a claim to handle complete game installations.

Retained copies and partial operations consume disk space. The manager never
cleans them automatically. It is not a complete application backup, a repository
backup, a game save system, or a rights-clearing tool. Keep an independent backup
and sufficient local storage for the selected copies and history. Windows and
Linux have different APIs; macOS and network filesystems are outside acceptance.

## Privacy, licensing and verification

The public package contains original code, guides/tests and generators for
fictional profiles. No actual workspace, personal/game data, private paths,
credentials, game assets, vendor configuration or identifying runtime record is
bundled. Operational state belongs in your private workspace outside the checkout.

Runtime profile IDs, filenames, relative paths, hashes, sizes, operation IDs and
history can identify an input. GUI-selected paths are visible locally. Field
minimization is not anonymization. The program is not a general metadata scrubber.
GitHub retains ordinary source/commit metadata, and required license notices
remain. Do not post real manifests, journals, screenshots or profile bodies in
an issue without a separate privacy/rights review.

MIT applies to this original program, authored docs/tests and fictional fixtures.
Imported profiles, active derivatives and retained copies keep their own rights.
Hash consistency does not establish authenticity, safety, ownership or game
compatibility. Read [provenance](docs/PROVENANCE.md),
[security boundaries](SECURITY.md) and [validation](docs/VALIDATION.md).

Run from this module directory:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

Native Tk tests are required in configured Windows/Linux CI. The separate
[validation record](docs/VALIDATION.md) distinguishes engine/CLI, injected crash,
real operating-system lock/rename and hidden native-widget checks. Test skips
are never counted as passes; generated fixtures are not live game acceptance.

Suggestions, format proposals and fictional bug reproductions are welcome through
the [community forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Choose this tool's form and include your source commit, OS/Python/Tk version,
minimal invented fixture, steps and expected behavior. See [CONTRIBUTING.md](CONTRIBUTING.md).
