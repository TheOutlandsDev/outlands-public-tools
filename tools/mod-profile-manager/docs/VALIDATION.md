# Validation scope

The suite uses newly generated fictional regular-file trees. It does not use
real game files, private profiles, saves, vendor configuration or held projects.
All generated stores and copied payloads belong outside the source checkout.
See [the walkthrough](../README.md) and [example expectations](../examples/README.md).

## Reproduce

From this module directory, using CPython 3.12 or newer:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

The first command checks the reviewed source inventory; it does not certify
third-party input rights or game behavior. Refreshing its expected inventory is
a review action, not a way to suppress an unexplained change.

For native desktop acceptance on Windows PowerShell:

```powershell
$env:PROFILE_MANAGER_REQUIRE_TK = '1'
python -B -W error -m unittest discover -s tests -p test_gui.py -v
```

For a Linux machine with Tk installed and an X virtual framebuffer:

```sh
PROFILE_MANAGER_REQUIRE_TK=1 xvfb-run -a python3 -B -W error -m unittest discover -s tests -p test_gui.py -v
```

The configured Windows/Linux CI requires Tk. When the requirement is set,
missing bindings or a failed root/display creation fails the GUI tests. A
developer without Tk may see an explicit native-widget skip when the variable
is absent; that skip is not a pass or desktop evidence. CLI import/help does
not load Tk. Native test windows stay withdrawn and use no live game.

## Desktop evidence and test boundaries

The local Windows CPython 3.12.7 / Tcl-Tk 8.6.13 desktop suite passes **23 tests**:
13 UI-independent controller tests and ten real hidden-widget tests. The
controller tests verify inert construction, explicit confirmations, canceled
and denied changes, read-only preview, recovery branching and fixed-code error
reporting without private exception text. Native widgets verify status/list
updates, profile selection, action buttons, existing-only workspace selection,
readable output, the explicit structured-details toggle and a read-only result
pane. A retained-preparation diagnostic is explained without implying that an
operation is pending or preventing a new read-only preview.

One hidden-widget test uses the actual engine and generated orchard source:
initialize, import, preview, activate and deactivate. It verifies active state,
the managed active copy and retained source fixture. Fake APIs test UI ordering;
they are not substituted for that actual engine workflow.

Engine/CLI coverage is maintained in `tests/test_engine.py` and
`tests/test_cli.py`. These distinguish ordinary transitions, malformed or drifted
state, bounds, unsupported paths/objects, source retention and API-only injected
interruption/recovery cases. Platform-specific primitives and subprocess locks
must be exercised on each supported platform. A Linux test run or CI result
must be reported separately from a Windows run; a workflow file alone is not
evidence that a remote job succeeded.

Review the complete suite output and CI run for the exact selected revision.
Counts above identify the desktop suite only; they are not an aggregate count
for independent first-party support, engine, CLI and source-gate suites.

## What is not certified

- No actual game/mod-loader integration, gameplay, multiplayer or live-running
  application acceptance has been performed. Activation targets only the fixed
  manager-owned `active` path.
- No claim covers macOS, network filesystems, hostile concurrent ancestor
  mutation, unknown filesystem primitives or arbitrary disk corruption.
- Injected process interruption exercises documented state boundaries. It does
  not simulate every OS/filesystem failure, prove hardware power-loss durability,
  or guarantee recovery from missing/drifted retained data.
- Byte/hash verification does not certify executable safety, input provenance,
  authenticity, metadata anonymity or compatibility with a specific game.
- Full ACL/owner/timestamp/alternate-stream preservation is not supported.
  Runtime state and GUI-selected paths remain private local operational data.

Do not weaken guards to make an unsuitable fixture pass. Report an issue with a
minimal invented fixture and fixed error code through the [suggestion and bug
forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
See [CONTRIBUTING](../CONTRIBUTING.md) for the information that helps a reviewer
reproduce a problem without publishing real data.
