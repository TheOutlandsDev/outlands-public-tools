# Use Hash Journal 0.2.0

Download the source ZIP from the
[0.2.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/hash-journal-v0.2.0)
and extract it into a **fresh** source directory. Keep prerequisites, build
artifacts, real journals and reports in an external
[private workspace](docs/PRIVATE-WORKSPACE.md). The release contains source,
not an executable or a .NET SDK/runtime.

## Select the prerequisites

Use SDK **10.0.404** for the default **.NET 10 LTS / `net10.0`** target, or SDK
**11.0.100** for **.NET 11 / `net11.0`**. Select Windows x64 or Ubuntu x64 for
your system. [docs/SDKS.json](docs/SDKS.json) pins official archive URLs and
SHA-512 digests. The official
[.NET 10 archive page](https://dotnet.microsoft.com/en-us/download/dotnet/10.0)
and [.NET 11 archive page](https://dotnet.microsoft.com/en-us/download/dotnet/11.0)
cover the separately supplied SDKs and runtimes.

A verified portable SDK can be extracted into a user-owned private folder and
invoked directly, without inherently needing administrator access. Follow your
device's software policy; do not bypass restrictions. Ubuntu must already have
the required system libraries. External tools retain their own license terms.

Optional source/release helpers support **Python 3.12, 3.13, 3.14 and 3.15**,
using only the standard library. Use normal Python: optimized runs (`-O`, `-OO`
or `PYTHONOPTIMIZE`) are refused. Prerequisite downloads need network access.
A built CLI needs only its app files and matching .NET runtime; Python,
network access, a model and an account are not needed to use it.

Before using an SDK manually, set the following variables in that shell. The
global-tools opt-out prevents the SDK's first run from adding its tools folder
to the user `PATH`. These settings affect this process and its children only:

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

The SDK and qualification helpers already set these opt-outs in their child
process environment, including first-run ASP.NET certificate generation,
telemetry and build-server controls. They do not persist these settings in a
shell profile, user `PATH` or machine policy.

The optional pinned-SDK helper verifies the archive's SHA-512 before extraction
or execution. Run it from the source folder with an exact version and a fresh
private output directory:

```powershell
py -3.12 packaging/sdk.py --version 10.0.404 --out 'D:\Private\HashJournal\sdk10'
```

```sh
python3.12 packaging/sdk.py --version 10.0.404 --out '/absolute/private/hash-journal/sdk10'
```

For the other target, request `--version 11.0.100` and another output directory.
The selected host is in `runtime/dotnet.exe` on Windows or `runtime/dotnet` on
Ubuntu under that directory. Downloaded archives, runtime files and receipts
stay outside the source directory.
SHA-512 is the archive identity check. The helper bounds the download at
512 MiB and records the actual downloaded byte count; that count is not an
expected length supplied by the official metadata.

## Build on Windows x64

Open PowerShell in the extracted source folder. These paths are fictional;
select your own private folders. The journal folder must already exist before
you use it. Invoke the pinned SDK directly to avoid selecting another SDK from
`PATH`.

```powershell
$sdk = 'D:\Private\HashJournal\sdk10\runtime\dotnet.exe'
$build = 'D:\Private\HashJournal\build10'
& $sdk --version
& $sdk restore HashJournal.csproj --configfile NuGet.Config --artifacts-path $build
& $sdk build HashJournal.csproj -c Release --artifacts-path $build --no-restore
$app = Join-Path $build 'bin/HashJournal/release/Outlands.HashJournal.dll'
& $sdk $app --help
& $sdk $app demo
```

The version must be `10.0.404`. The display-only `demo` prints marked fictional
JSON and opens no journal. Its display is **not** a JSONL journal to redirect
and later verify.

For .NET 11, select SDK `11.0.100` and a separate build folder. Add the explicit
target to **both restore and build**:

```powershell
$sdk = 'D:\Private\HashJournal\sdk11\runtime\dotnet.exe'
$build = 'D:\Private\HashJournal\build11'
& $sdk --version
& $sdk restore HashJournal.csproj --configfile NuGet.Config --artifacts-path $build -p:TargetFramework=net11.0
& $sdk build HashJournal.csproj -c Release --artifacts-path $build --no-restore -p:TargetFramework=net11.0
$app = Join-Path $build 'bin/HashJournal/release/Outlands.HashJournal.dll'
& $sdk $app demo
```

A `net11.0` build needs the .NET 11 runtime; a `net10.0` build needs the .NET 10
runtime. The selected SDK contains a runtime for its own target. For use on
another computer, retain the built app files together and separately supply
the matching runtime. No generated build is included in this source release.

## Build on Ubuntu x64

Open a shell in the extracted source folder and invoke the selected SDK:

```sh
sdk='/absolute/private/hash-journal/sdk10/runtime/dotnet'
build='/absolute/private/hash-journal/build10'
"$sdk" --version
"$sdk" restore HashJournal.csproj --configfile NuGet.Config --artifacts-path "$build"
"$sdk" build HashJournal.csproj -c Release --artifacts-path "$build" --no-restore
app="$build/bin/HashJournal/release/Outlands.HashJournal.dll"
"$sdk" "$app" --help
"$sdk" "$app" demo
```

For .NET 11, use SDK `11.0.100`, a separate build directory and the override
on **both operations**:

```sh
sdk='/absolute/private/hash-journal/sdk11/runtime/dotnet'
build='/absolute/private/hash-journal/build11'
"$sdk" --version
"$sdk" restore HashJournal.csproj --configfile NuGet.Config --artifacts-path "$build" -p:TargetFramework=net11.0
"$sdk" build HashJournal.csproj -c Release --artifacts-path "$build" --no-restore -p:TargetFramework=net11.0
app="$build/bin/HashJournal/release/Outlands.HashJournal.dll"
"$sdk" "$app" demo
```

No NuGet packages are used. `NuGet.Config` clears feeds, and the selected SDK
must already contain the matching reference packs. Missing packs cause failure;
do not enable feeds to work around the pinned build. Warnings are treated as
errors. Cleared feeds are not a dependency advisory audit.

## Fictional create → append → anchored verify

Use an existing trusted local journal directory. Each output filename must be
new. These exact fictional texts match the independently calculated golden
heads in [the format guide](docs/FORMAT.md) and
[the example guide](examples/README.md).

PowerShell, continuing with the selected `$sdk` and `$app`:

```powershell
$old = 'D:\Private\HashJournal\journals\fictional-001.jsonl'
$new = 'D:\Private\HashJournal\journals\fictional-002.jsonl'
& $sdk $app create --output $old --text 'Fictional build prepared.'
& $sdk $app append --input $old --output $new --text 'Fictional checks passed.'
& $sdk $app verify --input $new --expected-head ec91f00284e1d0faccd7f3301ae23ae7af1c8eed6121cab890dd1648d9f33d36 --expected-count 2
```

Ubuntu, continuing with the selected `sdk` and `app`:

```sh
old='/absolute/private/hash-journal/journals/fictional-001.jsonl'
new='/absolute/private/hash-journal/journals/fictional-002.jsonl'
"$sdk" "$app" create --output "$old" --text 'Fictional build prepared.'
"$sdk" "$app" append --input "$old" --output "$new" --text 'Fictional checks passed.'
"$sdk" "$app" verify --input "$new" --expected-head ec91f00284e1d0faccd7f3301ae23ae7af1c8eed6121cab890dd1648d9f33d36 --expected-count 2
```

`append` verifies the old file before creating the two-record version. The
one-record input remains unchanged. Existing outputs are refused; keep old
versions and select another new filename when repeating this demonstration.

Anchored verify should report `status: VALID_HEAD_MATCHED`, `count: 2`,
`anchor: HEAD_MATCHED`, `expectedCountMatched: true` and `outputWritten: false`
in its JSON metadata. Create and append report `VALID_UNANCHORED`; they do not
create an external anchor automatically.

For actual journals, independently retain the successful head **and count**
in a separately trusted place, then use those retained values in a later
check. Reading an expected head from the same file you are checking provides
no independent protection. The fixed head above applies only to these two
exact fictional events.

Without `--expected-head`, verification checks internal consistency. Removing
the second complete record leaves an internally valid one-record prefix.
The independently retained two-record head detects that truncation; the count
also catches the missing record. A count alone cannot detect a same-length
replacement. A whole journal can be replaced and rehashed to pass unanchored
verification. A matched head is not proof of identity, truth, occurrence time
or continuous retention.

## Commands and failures

```text
create --output ABSOLUTE_NEW_FILE --text TEXT
append --input ABSOLUTE_FILE --output ABSOLUTE_NEW_FILE --text TEXT
verify --input ABSOLUTE_FILE [--expected-head LOWERCASE_SHA256] [--expected-count N]
demo
--help
```

There are no implicit file/destination defaults. Options require a value;
names are case-sensitive, and duplicates/unknown options are refused. Expected
head is 64 lowercase hex characters. Expected count is an unsigned decimal
integer from 1 to 10,000.

Exit `0` means the selected command completed its stated scope. Exit `2`
reports a fixed JSON error on standard error. Successful create/append/verify
output is JSON metadata, omitting event text and full paths. The journal
stores complete text in clear text. Arguments, shell history, OS records and
redirection can retain text, paths and reports; keep them private.

The [version 1 format](docs/FORMAT.md) refuses BOM, CRLF, missing final LF,
blank lines, malformed JSON, duplicate/unknown members and invalid Unicode.
Do not let an editor silently change line endings. Simultaneous limits are
1,048,576 file bytes, 65,536 bytes per line, 10,000 records and 8,192 UTF-8 bytes
per nonblank text.

Use absolute, nonlinked file paths with existing trusted parents. The CLI
does not create missing parents, append in place, overwrite or delete files.
Windows network/device/alternate-stream paths and mapped network drives are
refused. Choose trusted local storage on Unix. Observed-link and size/time
checks have race windows; they do not freeze a directory tree or contain all
hostile concurrent filesystem replacement.

`OUTPUT_WRITE_FAILED_PARTIAL_POSSIBLE` means a new partial output may remain.
Inspect the selected file privately and choose another fresh filename. Unix
creation requests owner-only mode; Windows inherits the parent's ACL. Neither
is encryption or an immutable append-only store. See [SECURITY.md](SECURITY.md).

## Native tests

Use the same selected SDK and private artifacts. For the default target:

```text
dotnet restore tests/HashJournal.Tests.csproj --configfile NuGet.Config --artifacts-path ABSOLUTE_PRIVATE_TEST_BUILD
dotnet build tests/HashJournal.Tests.csproj -c Release --artifacts-path ABSOLUTE_PRIVATE_TEST_BUILD --no-restore
dotnet ABSOLUTE_PRIVATE_TEST_BUILD/bin/HashJournal.Tests/release/HashJournal.Tests.dll ABSOLUTE_EXISTING_TEST_PARENT
```

Replace `dotnet` with the pinned executable. For .NET 11, add
`-p:TargetFramework=net11.0` to both test restore and test build. The optional
last argument selects an existing private test parent; otherwise the harness
uses the operating system's temporary directory. It creates and cleans its
own disposable child. Platform/permission cases can be skipped. Read
[qualification](docs/QUALIFICATION.md) for current release evidence, separately
from source checks and the historical 0.1.0 result.
