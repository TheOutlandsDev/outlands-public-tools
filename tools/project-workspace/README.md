# Project Workspace

Plan or create a neutral private project folder, with optional byte-preserving
intake copies. The default command validates a plan without creating a workspace.
It reads a selected source for validation; planning does not reserve a name.

Download the **0.1.0 standalone source ZIP** from the
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/project-workspace-v0.1.0),
extract into a fresh folder and follow [USAGE.md](USAGE.md). Keep `workspace.py`
and `workspace_windows.py` adjacent. Use Python **3.12–3.15**; qualification
selects 3.15.2 for that minor. Only the standard library is needed, with no pip
packages, network, model or account. No interpreter, dependency binary, actual
input/generated workspace, private template or raw diagnostic log is bundled.

```text
python -B workspace.py --root EXISTING_PRIVATE_PARENT --name fictional-project
python -B workspace.py --root EXISTING_PRIVATE_PARENT --name fictional-project --source FICTIONAL_INPUT --create
```

Run from the extracted source folder or use an explicit script path. `--root`
must already be a trusted private directory. `--name` is 1–64 lowercase ASCII
letters/digits/underscores/hyphens, beginning with a letter or digit; reserved
device names are refused. Existing destinations are refused. `--source` selects
an optional ordinary file of at most **16 MiB**. Add `--create` to write.

| Result | Exit code | Meaning |
| --- | ---: | --- |
| `PLAN_ONLY` | 0 | Parent/name/destination and optional source validated; no workspace created or reserved. |
| `WORKSPACE_CREATED` | 0 | Requested creation and applicable byte checks completed. |
| `ERROR` / `WORKSPACE_INPUT_OR_OUTPUT_ERROR` | 2 | Handled argument/input/I/O failure; new output can remain unconfirmed. |
| `ERROR` / `WORKSPACE_INTERRUPTED` | 130 | Handled Windows interruption; new output can remain unconfirmed. |

Normal output is JSON. POSIX interruption behavior remains unchanged. Static
help is separate from these operation results. Check the actual process result;
a populated tree or matching hashes alone do not prove successful completion.

## What creation writes

The layout contains `original`, `working`, `evidence/screenshots`,
`evidence/test-output`, `deliverables`, `logs` and `rollback`, plus `.gitignore`
and a neutral `CONTROL.md`. With a source, opaque bytes become
`original/intake.bin` and `working/intake.bin`; `original/SOURCE.json` records
only byte size and SHA-256. Source data is never parsed, imported or launched.
The source name/path is not copied into the metadata. Successful copying does
not remove private content from those bytes.

The original POSIX bodies, folder/name rules and template remain preserved.
Windows uses the adjacent native backend for checked local paths, bounded
reads, exclusive directories/files, retained handles and output readback.
Version 0.1.0 fixes an output refusal bug exposed by Windows qualification:
an existing dangling output symlink could cause its missing target to be
created before a later native check failed. The backend now refuses every
observed existing output leaf before its creation attempt. This check retains
a pathname/open race window under the trusted-parent requirement.
Observed links/reparse components and unsupported Windows spellings/providers
are refused; ordinary hardlinked sources remain supported. Only unnamed file
data is copied, without named streams, ACLs, ownership, topology or timestamps.
Read the preserved [filesystem contract](docs/WINDOWS.md).

**Generated workspaces and actual inputs/results stay private.** The ignore
file is attempted early but can be missing/incomplete after failure; Git ignore
rules are not access controls. Parent ACLs and OS/Python behavior govern
permissions. New partial or complete-looking unconfirmed output is retained
for inspection, with no automatic recursive cleanup or rollback.

Select stable ordinary inputs under trusted quiescent local parents. Sampled
path/create/open checks retain race windows. This is not an atomic transaction,
hostile-filesystem sandbox, universal I/O deadline, live/cloud/remote-provider
acceptance or power-loss recovery guarantee. Source size is bounded; total CPU,
memory and elapsed time are not quotas.

## Use and evidence

[USAGE.md](USAGE.md) gives a fictional plan → create → verify walkthrough,
complete JSON/exit outcomes and input/runtime/existing-output hash checks.
Choose an external [private workspace](docs/PRIVATE-WORKSPACE.md). User-owned
Python/venvs do not inherently require administrator access; respect device
policy and OS prerequisites without bypasses.

Eight fresh extracted-ZIP Windows/Ubuntu Python lanes select six original
shared regression bodies, 40 existing safety methods and copied-runtime CLI
consumers in no-pip/no-distribution venvs. Actual versions/counts/skips/results
belong to release `VALIDATION.json`; intended coverage is not a passing result.
See [qualification](docs/QUALIFICATION.md). Historical observations in
[WINDOWS.md](docs/WINDOWS.md) remain separate from fresh release qualification.
The CLI, POSIX bodies and template remain unchanged; the Windows backend
contains the reviewed output-leaf fix. Runtime hash checks during qualification
refer to the selected release bytes, not equality with the pre-fix backend.

Selected original source is [MIT licensed](LICENSE), with retained notices and
AI-assisted preparation, without an exclusive-authorship claim. See
[provenance](docs/PROVENANCE.md),
[collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md)
and the [earlier review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-27-PROJECT-WORKSPACE-WINDOWS.md).
[Report an issue](https://github.com/TheOutlandsDev/outlands-public-tools/issues)
with authored fictional data and complete outcomes. Do not attach actual input,
private workspace trees, personal paths or raw diagnostics.
