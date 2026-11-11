# Private workspace

Extract reviewed public source into a fresh directory. Choose a separate
existing, user-owned private parent for interpreters/venvs, authored inputs,
generated workspace trees, captures and qualification work:

```text
source/project-workspace-0.1.0/  selected source only
private/project-workspace/
  venv312/                     separately created no-pip environment
  fictional_walkthrough.py     private copy of the supplied verification driver
  fictional-demo/              new owned fictional input/project parent
  captures/                    private console outcomes/diagnostics
  qualification/               fresh extraction, environment, fixtures, receipts
```

Keep `workspace.py` and `workspace_windows.py` adjacent and select the intended
interpreter/script explicitly. `--root` is an existing private parent;
`--name` selects a new destination. The default plan writes no workspace but
reads an optional selected source for validation. It reserves nothing and
provides no promise about later creation.

`--create` retains opaque input bytes under neutral `original/intake.bin` and
`working/intake.bin`, records size/SHA-256 and writes a neutral control/layout.
Renaming a copy does not remove identifiers/secrets from its content. Real
inputs/generated workspaces, hashes, results, paths and captures stay private.
Prepare a separate reviewed export before sharing anything.

Existing destinations are refused. A failed/interrupted invocation can leave
partial or complete-looking unconfirmed new output, with no automatic cleanup
or rollback. Inspect it privately and check the process outcome. The ignore
file is attempted early but can fail or remain incomplete; ignore rules are
not access controls. Parent ACLs and OS/Python govern permissions.

Use stable ordinary input and fully spelled trusted quiescent local parents.
Observed native/path/link guards remain in force. Only unnamed data is copied;
streams, ACLs, ownership, topology and timestamps are not backed up. Reads may
affect access metadata and Python caches are separate. The supplied driver
uses `-B` and checks input/runtime/existing-output bytes, not every OS property.

Sampled checks retain pathname/create/open race windows. No atomic transaction,
hostile-filesystem containment, universal deadline, live/cloud/remote-provider
or power-loss guarantee is made. Use the preserved [WINDOWS.md](WINDOWS.md)
contract rather than inferring wider acceptance from successful fictional tests.

User-owned Python/venvs do not inherently require administrator access. Respect
device policy and OS prerequisites without bypasses. No pip packages, network,
model or account are required. Release venvs contain no pip/distributions;
interpreters remain separately licensed prerequisites.

Source/build/qualification outputs must be fresh private destinations outside
source, with existing parents. Shell redirection/caller code can overwrite its
own captures independently of the tool; choose new capture paths deliberately.
Publish designated reviewed source assets and sanitized evidence only, excluding
actual inputs/workspaces, original templates, interpreter/dependency binaries,
personal paths and raw logs. See [USAGE.md](../USAGE.md) and
[QUALIFICATION.md](QUALIFICATION.md).
