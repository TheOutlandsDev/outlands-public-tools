# Use .NET Public API Diff 0.1.0

Download the source ZIP from the
[0.1.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/dotnet-api-diff-v0.1.0)
and extract it into a fresh source directory. Choose an external
[private workspace](docs/PRIVATE-WORKSPACE.md) for prerequisites, build outputs,
trusted input assemblies and reports. No generated DLL, SDK/runtime or private
assembly is included in the source ZIP.

**Inspect only trusted, completed local build artifacts you own or may inspect.**
The tool reads metadata without loading the input assembly or executing its
initializers/methods. This is not a security sandbox: malformed or malicious
metadata can crash or hang the underlying reader. Read the
[Microsoft trust warning](https://learn.microsoft.com/dotnet/api/system.reflection.metadata).
There is no inspection timeout or process isolation.

## Select prerequisites

Use pinned SDK **10.0.404** for the default **.NET 10 LTS / `net10.0`** target,
or SDK **11.0.100** for **.NET 11 / `net11.0`**. Official Windows x64 and Ubuntu
x64 archive URLs and SHA-512 digests are in [docs/SDKS.json](docs/SDKS.json).
Official [.NET 10](https://dotnet.microsoft.com/en-us/download/dotnet/10.0) and
[.NET 11](https://dotnet.microsoft.com/en-us/download/dotnet/11.0) prerequisites
are supplied separately. Required operating-system libraries must be present.

Portable prerequisites in user-owned private folders do not inherently need
administrator access. Follow device policy; do not bypass restrictions. A built
CLI needs its app files and matching .NET runtime, without Python, network,
model or account. Initial SDK downloading is a separate networked operation.

Optional helpers use the Python standard library and support Python 3.12–3.15
(the qualification matrix selects 3.15.2 for that minor). Optimized Python
(`-O`, `-OO` or `PYTHONOPTIMIZE`) is refused. To obtain a pinned SDK, run from
the source directory with a **new absolute output directory** whose parent
already exists:

```powershell
py -3.12 packaging/sdk.py --version 10.0.404 --out 'D:\Private\ApiDiff\sdk10'
```

```sh
python3.12 packaging/sdk.py --version 10.0.404 --out '/absolute/private/api-diff/sdk10'
```

Select `--version 11.0.100` and another output for .NET 11. The helper verifies
pinned SHA-512 before extraction/execution, limits downloads to 512 MiB and
records actual bytes; metadata does not supply an expected byte length. Its
host is `runtime/dotnet.exe` on Windows or `runtime/dotnet` on Ubuntu beneath
the output. SDK archives/receipts stay outside the source folder.

Before **manual SDK use**, set process-only first-run opt-outs:

```powershell
$env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH = 'false'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE = 'false'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_CLI_USE_MSBUILD_SERVER = '0'
$env:MSBUILDDISABLENODEREUSE = '1'
```

```sh
export DOTNET_ADD_GLOBAL_TOOLS_TO_PATH=false
export DOTNET_GENERATE_ASPNET_CERTIFICATE=false
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_CLI_USE_MSBUILD_SERVER=0
export MSBUILDDISABLENODEREUSE=1
```

These prevent first-run global-tools user-`PATH` changes and ASP.NET certificate
generation, opt out of telemetry and control build servers for this shell and
its children. SDK/qualification helpers set these controls in child environments
already. The settings are not persisted in shell profiles or machine policy.

## Build all four projects on Windows x64

Open PowerShell in the source folder. Replace these fictional paths with your
own private locations. Invoke the selected SDK directly:

```powershell
$sdk = 'D:\Private\ApiDiff\sdk10\runtime\dotnet.exe'
$build = 'D:\Private\ApiDiff\build10'
& $sdk --version
& $sdk restore tests/ApiDiff.Tests.csproj --configfile NuGet.Config --artifacts-path $build
& $sdk build tests/ApiDiff.Tests.csproj -c Release --artifacts-path $build --no-restore
$app = Join-Path $build 'bin/ApiDiff/release/ApiDiff.dll'
$tests = Join-Path $build 'bin/ApiDiff.Tests/release/ApiDiff.Tests.dll'
$before = Join-Path $build 'bin/Before/release/Example.Plugin.dll'
$after = Join-Path $build 'bin/After/release/Example.Plugin.dll'
& $sdk $tests $before $after
& $sdk $app --help
```

The SDK version must be `10.0.404`. The test project's references build the CLI
and **both** fictional libraries along with the harness, all at the selected
target. Fixture DLLs and all other outputs stay in the private artifacts path.

For .NET 11, use SDK `11.0.100` and another build directory. Supply the explicit
target during **both restore and build** so the entire four-project graph uses
`net11.0`:

```powershell
$sdk = 'D:\Private\ApiDiff\sdk11\runtime\dotnet.exe'
$build = 'D:\Private\ApiDiff\build11'
& $sdk --version
& $sdk restore tests/ApiDiff.Tests.csproj --configfile NuGet.Config --artifacts-path $build -p:TargetFramework=net11.0
& $sdk build tests/ApiDiff.Tests.csproj -c Release --artifacts-path $build --no-restore -p:TargetFramework=net11.0
$app = Join-Path $build 'bin/ApiDiff/release/ApiDiff.dll'
$tests = Join-Path $build 'bin/ApiDiff.Tests/release/ApiDiff.Tests.dll'
$before = Join-Path $build 'bin/Before/release/Example.Plugin.dll'
$after = Join-Path $build 'bin/After/release/Example.Plugin.dll'
& $sdk $tests $before $after
```

## Build all four projects on Ubuntu x64

Open a shell in the source folder, set the process opt-outs above and invoke
the selected pinned SDK:

```sh
sdk='/absolute/private/api-diff/sdk10/runtime/dotnet'
build='/absolute/private/api-diff/build10'
"$sdk" --version
"$sdk" restore tests/ApiDiff.Tests.csproj --configfile NuGet.Config --artifacts-path "$build"
"$sdk" build tests/ApiDiff.Tests.csproj -c Release --artifacts-path "$build" --no-restore
app="$build/bin/ApiDiff/release/ApiDiff.dll"
tests="$build/bin/ApiDiff.Tests/release/ApiDiff.Tests.dll"
before="$build/bin/Before/release/Example.Plugin.dll"
after="$build/bin/After/release/Example.Plugin.dll"
"$sdk" "$tests" "$before" "$after"
"$sdk" "$app" --help
```

For .NET 11, select SDK `11.0.100`, another build directory and the target on
**both** operations:

```sh
sdk='/absolute/private/api-diff/sdk11/runtime/dotnet'
build='/absolute/private/api-diff/build11'
"$sdk" --version
"$sdk" restore tests/ApiDiff.Tests.csproj --configfile NuGet.Config --artifacts-path "$build" -p:TargetFramework=net11.0
"$sdk" build tests/ApiDiff.Tests.csproj -c Release --artifacts-path "$build" --no-restore -p:TargetFramework=net11.0
app="$build/bin/ApiDiff/release/ApiDiff.dll"
tests="$build/bin/ApiDiff.Tests/release/ApiDiff.Tests.dll"
before="$build/bin/Before/release/Example.Plugin.dll"
after="$build/bin/After/release/Example.Plugin.dll"
"$sdk" "$tests" "$before" "$after"
```

If building individual projects instead, use the same SDK/target override on
restore and build for the CLI, harness, Before and After projects. Do not mix
fixture targets accidentally. `NuGet.Config` clears feeds; there are no NuGet
packages, and matching reference packs must already exist in the SDK. Missing
packs fail rather than trigger enabling a feed. Warnings are errors. This
arrangement is not a dependency advisory audit.

The SDK contains a matching runtime. To run the built CLI elsewhere, retain
its app files together and separately supply the matching .NET 10 or .NET 11
runtime. Generated binaries are not assets in this source-only release.

## Compare the fictional update

Continue with the selected `sdk`/`app`/`before`/`after` variables. Choose a new
report filename in an existing private directory. In PowerShell:

```powershell
$report = 'D:\Private\ApiDiff\reports\fictional-update.json'
& $sdk $app compare --before $before --after $after --output $report
$LASTEXITCODE
& $sdk $app compare --before $before --after $before
$LASTEXITCODE
& $sdk $app compare --before $before
$LASTEXITCODE
```

On Ubuntu:

```sh
report='/absolute/private/api-diff/reports/fictional-update.json'
"$sdk" "$app" compare --before "$before" --after "$after" --output "$report"
printf '%s\n' "$?"
"$sdk" "$app" compare --before "$before" --after "$before"
printf '%s\n' "$?"
"$sdk" "$app" compare --before "$before"
printf '%s\n' "$?"
```

Expected exit codes, in order, are **1**, **0**, **2**. Run the example
interactively; a shell configured to stop on every nonzero exit must account
for the expected difference/error cases. The first command's six changes are:

- `Added()` added; `Removed()` and the public `set_Name(string)` removed.
- `Name` setter presence, `Level` field type and `Convert(Int32)` return type
  changed. The string overload stays separate and unchanged.

The changed constant value is deliberately excluded. Read the preserved
[fictional walkthrough](examples/walkthrough.md) for exact identities. Fixture
hashes can differ with compiler/framework versions; qualify declaration results
rather than prescribing a hardcoded DLL hash. The fixtures' initializer marker
must remain absent after metadata inspection.

The first command writes the report to the selected new file; without
`--output`, JSON goes to standard output. Reports are UTF-8 JSON with final LF.
Inputs are preserved, and existing reports are refused. Repeat examples with
another fresh filename. A failed new write can leave a partial report; inspect
it privately and retain evidence before selecting another new output.
The standalone CLI adds an explicit metadata check of the output leaf before
creation, including a dangling symbolic link whose target does not exist.
Observed existing leaves are refused; the check and creation still have a
race window. This is not atomic containment against concurrent replacement.

## Interpretation and private inputs

```text
compare --before OLD.dll --after NEW.dll [--output NEW.json]
--help
```

Options are case-sensitive; unknown, duplicate or incomplete options fail.
Exit `0` means equal supported declarations (or help), `1` means differences
with a complete report, and `2` means input/output/coverage failure. Errors
are fixed text on standard error; they are not JSON comparison reports.

Compare trusted completed builds with the same assembly simple name. That
name does not establish full assembly identity or authenticity. Equal results
do not establish binary/runtime/semantic-versioning/game compatibility.
Constant/enum values, names/defaults/parameter flags (`ref` versus `out`),
nullable/custom attributes, marshaling/layout offsets, type forwarders,
assembly version/strong-name identity and method bodies are excluded. Framework
and compiler changes can themselves alter reference scopes or declaration flags.

Use ordinary stable local copies, preferably selected by absolute paths, and
stop writers first. Observed symlink/reparse components, UNC paths, controls
and Windows alternate streams are refused. Portable .NET checks do not prove
Unix regular-file type or prevent hostile path replacement. Snapshot size is
bounded to 32 MiB per input; the two snapshots are sequential. Other bounds
are in [FORMAT.md](docs/FORMAT.md). No atomic snapshot, timeout, process
isolation or hostile-input security boundary is provided.

Reports contain API/assembly names, declaration details and input SHA-256;
metadata itself can embed identifying/path-like text. Wrapper filesystem
paths, method bodies, resources and debug/PDB paths are omitted, but that is
not anonymization. Arguments, shell history and redirection can retain private
information. Keep actual DLLs/reports private and publish only fictional
reproductions you have rights to share. See [qualification](docs/QUALIFICATION.md)
and [provenance](docs/PROVENANCE.md).
