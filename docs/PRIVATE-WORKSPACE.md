# Private workspace for examples

Run tool commands from their documented source folder, and keep generated
stores, reports, backups, fixtures and exports in a separate private workspace.
For the disposable examples, create a fresh absolute folder outside the entire
checkout. This is especially relevant to the collection: `../output` from a
tool folder still points inside the collection's `tools` directory.

PowerShell:

```powershell
$privateWork = Join-Path ([IO.Path]::GetTempPath()) ("outlands-demo-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $privateWork | Out-Null
$privateWork
```

POSIX shell:

```sh
privateWork="$(mktemp -d "${TMPDIR:-/tmp}/outlands-demo.XXXXXX")"
privateWork="$(cd "$privateWork" && pwd -P)"
printf '%s\n' "$privateWork"
```

Check that the printed path is absolute, outside the checkout, and on trusted
local storage. Keep the variable in the same terminal while following examples.
Commands use quoted paths such as `"$privateWork/report-001"`; choose fresh names
when repeating a workflow. Create a required input directory or output parent
before running a tool that requires it. Do not substitute `../../../...` paths:
some tools deliberately reject parent-traversal components.

This temporary folder is for fictional practice. For real work, select a private
persistent location with appropriate access and backup arrangements. Reports,
hash inventories, exports and copies can still contain identifying content;
these path choices do not sanitize or encrypt it.

Local Site Builder intentionally keeps its private, ignored `.env` beside
`server.js`. Its data root can be moved using `SITE_DATA_DIR`; keep the `.env`
private and exclude it from commits, support material and shared backups. The
other examples select their private stores/outputs explicitly. Optional virtual
environments and installed dependencies also remain separate from release
source assets.
