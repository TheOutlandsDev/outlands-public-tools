# Kiro development kit 1.1.0

A portable project setup for Windows 11, Kiro IDE 1.x / CLI V3, and the GPT
models enabled by your organization. It supplies working instructions, three
agent profiles, six reusable skills, a session-start information hook, an
installer with backups and rollback, and dependency-free language fixtures.

Version 1.1 adds the [Kiro/Bedrock pairing guide](BEDROCK-PAIRING.md), a
standalone non-admin laptop inspection, a credential-free pairing-plan
checker, and four in-memory Python SDK endpoint/authentication checks.

The kit uses Kiro's native model selection. It does not install or invoke Codex,
create a model gateway, change your AWS account, or enable a restricted model.
It reproduces a documented development workflow, not another product's agent
implementation or identical model behavior. The existing 76-tool wheel bundle
keeps its Python 3.12/3.13 requirement; this kit uses Python 3.15 independently.

## Start on an approved Windows workspace

Use an existing CPython 3.15 environment. The fixture baseline is Python 3.15.2,
Node 26.13.0, and JDK 27.0.1; see [versions.json](versions.json). Existing
repositories keep their own declared toolchains and dependency locks.

Open PowerShell in this kit directory. Select an existing project folder:

```powershell
$project = Read-Host 'Existing project folder'
$python = (Get-Command python).Source
& $python --version
./scripts/Install-KiroKit.ps1 -Target $project -Python $python
```

Review the preview. To install the listed files:

```powershell
./scripts/Install-KiroKit.ps1 -Target $project -Python $python -Apply
./scripts/Test-KiroKit.ps1 -Target $project -Python $python
```

The installer writes only the reviewed template paths plus local backup and
receipt state under `.kiro-kit/state/`. Differing existing files cause a stop.
Review those differences before using `-Replace`; keep the returned receipt.
Identical files are unchanged. Existing organization instructions remain the
authority: adapt the template to them instead of replacing them blindly.

Open the project in the employer-managed Kiro IDE, sign in through the provided
organization connection, and choose `outlands-developer` in the agent picker.
For CLI use an approved Kiro CLI installation, start `kiro-cli --v3` in the
project, and select the agent through `/agent`. Check `/model` or the IDE model
picker for the actual selected GPT model and effort. The information hook uses
the `python` resolved by Kiro's shell: the IDE terminal/runtime environment
must therefore resolve Python 3.15 too. A terminal and a GUI can have different
PATH values. Run `.kiro/devkit/check_context.py` in the IDE terminal to check.

No sign-in, model request, automatic memory change, MCP server installation,
or Kiro setting change is performed by the installer. The profiles expose
read/write/shell for development and read-only tools for investigation/review;
the organization's permission prompts and policies continue to apply. External
MCP and powers are not automatically loaded by these profiles. Add vetted
tools explicitly only when needed.

## Select approved models

Profiles initially omit `model` and inherit the managed Kiro default. This
allows installation before you know the company's model IDs. It is not proof
that the default is GPT or that a model request will succeed.

Record the exact IDs displayed by the employer-managed picker in a local JSON
file with an `available_model_ids` array. That inventory is a user-supplied
record, not authentication or a service query. Then rerun the preview:

```powershell
$inventory = Read-Host 'Local JSON file containing available_model_ids'
$primary = Read-Host 'Exact approved GPT model ID'
./scripts/Install-KiroKit.ps1 -Target $project -Python $python -AvailableModels $inventory -Primary $primary
./scripts/Install-KiroKit.ps1 -Target $project -Python $python -AvailableModels $inventory -Primary $primary -Replace -Apply
```

Optional `-Review` and `-Fast` IDs select the reviewer and investigator models;
both otherwise use the primary ID. IDs absent from the supplied inventory are
rejected. Confirm the actual route and any fallback in the Kiro client after
starting a new chat. The kit never infers provider identity from model text.
See [ROUTING.md](ROUTING.md) for task routing and supported feature boundaries.

## Verify local tools and agent behavior separately

```powershell
& $python -B scripts/kiro_kit.py check-fixtures
& $python -B -m unittest discover -s tests -v
./tests/test_powershell.ps1 -Python $python
./tests/test_laptop_inspection.ps1
```

Fixture checks run copies in an OS temporary directory. They exercise Python
stock/order boundaries, Node integer-cent discounts, and Java stock checks.
They also verify that a seeded Python bug and Node rounding regression fail.
There are no downloaded libraries, model calls, or live AWS requests.

The optional Bedrock SDK probe uses the pinned dependencies in
`requirements-bedrock-check.txt`. Its transport stays in memory and sockets
are blocked. See [BEDROCK-PAIRING.md](BEDROCK-PAIRING.md) before interpreting
offline results as access to Kiro or to a direct Bedrock API.

[ACCEPTANCE.md](ACCEPTANCE.md) describes the managed Kiro qualification. Local
`verify` always reports `ready_for_managed_work: false` and `NOT_RUN` for live
behavior. It cannot certify sign-in, model access, agent loading, a real
repository's compatibility, or cloud availability. `evals/managed-session.json`
is a worksheet; editing its status does not prove the workflow works.

## Restore project files

Use the target and receipt returned at installation. Preview first:

```powershell
$receipt = Read-Host 'Receipt path relative to project'
./scripts/Restore-KiroKit.ps1 -Target $project -Receipt $receipt -Python $python
./scripts/Restore-KiroKit.ps1 -Target $project -Receipt $receipt -Python $python -Apply
```

Rollback verifies every current installed file and backup before changing any
file. It refuses files edited after installation so user work can be preserved.
It restores original bytes, removes only named kit files that were newly
created, and retains local receipts/backups, empty directories, and the
`.kiro-kit/.gitignore` privacy marker. For multiple installations, restore in
reverse order. This is a file installer, not a snapshot of the whole project.
Review the preview and diff as for any development tool; concurrent writers
should be stopped during installation and restore.

## Publication and sources

Generic templates, fixture source, methods, and CI are public. Runtime folders,
installer binaries, local reports, model inventories, authentication files,
session evidence, and employer repositories remain outside the public kit.
The repository's MIT license applies to this original source. Obtain Kiro and
language runtimes from their respective publishers under their own licenses.

Format references checked on 2026-11-09: [custom agents](https://kiro.dev/docs/custom-agents/configuration-reference/),
[models](https://kiro.dev/docs/models/), [steering](https://kiro.dev/docs/steering/),
[skills](https://kiro.dev/docs/skills/), [hooks](https://kiro.dev/docs/hooks/),
and [enterprise governance](https://kiro.dev/docs/enterprise/governance/).
The managed Kiro client remains the authoritative validator for agent loading.
