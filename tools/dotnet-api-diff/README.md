# .NET Public API Diff

Compare the public metadata declarations in two builds of the same managed
assembly. The CLI reads PE metadata without loading that assembly, running its
module initializer, resolving dependencies or invoking methods. It helps review
a library or plugin update before release.

**Use only trusted, completed local build artifacts that you own or are
permitted to inspect.** The .NET metadata reader is not a security boundary for
hostile DLLs. Microsoft documents that malformed or malicious metadata can
crash or hang its readers. See the
[Microsoft metadata trust warning](https://learn.microsoft.com/dotnet/api/system.reflection.metadata).
File/signature limits reduce accidental processing problems; they do not make
arbitrary downloads safe to inspect. No timeout, process isolation or security
sandbox is provided.

Download the initial **0.1.0 standalone source ZIP** from the
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/dotnet-api-diff-v0.1.0).
Extract it into a fresh source directory and follow [USAGE.md](USAGE.md). It
contains original [MIT source](LICENSE), tests, documentation and fictional
fixture source. Generated DLLs, SDKs/runtimes, dependency binaries, original
private helpers, actual input assemblies and raw diagnostics are not bundled.

## Build and try the fictional update

The default target is **.NET 10 LTS (`net10.0`)**, using pinned SDK **10.0.404**.
The additional target is **.NET 11 (`net11.0`)**, using pinned SDK **11.0.100**
and `-p:TargetFramework=net11.0` on both restore and build. Official Windows x64
and Ubuntu x64 archive URLs/SHA-512 are pinned in [docs/SDKS.json](docs/SDKS.json).
There are no NuGet packages; `NuGet.Config` clears feeds. Required reference
packs must already be in the selected SDK, and OS libraries remain separate.

Use an external [private workspace](docs/PRIVATE-WORKSPACE.md). From the source
folder, invoke the selected pinned SDK:

```text
dotnet restore tests/ApiDiff.Tests.csproj --configfile NuGet.Config --artifacts-path ABSOLUTE_PRIVATE_BUILD
dotnet build tests/ApiDiff.Tests.csproj -c Release --artifacts-path ABSOLUTE_PRIVATE_BUILD --no-restore
```

The test project builds the CLI and both fictional `Example.Plugin` libraries:
all four projects use the selected target. For .NET 11, add the override to
**both** commands. [USAGE.md](USAGE.md) includes process-only SDK first-run
opt-outs, full Windows/Ubuntu commands and the test/compare walkthrough.

Comparing the fictional before/after DLLs should return **exit 1** and exactly
six declaration changes: one added method, two removed methods (including a
public setter) and three changed declarations. This is an expected difference
result. Comparing a fixture to itself returns `0`; an input/output/coverage
error returns `2`. The [original walkthrough](examples/walkthrough.md) explains
each golden change.

A built CLI needs its app files and matching .NET runtime, with no Python,
network, model or account. Optional source/release helpers use Python
3.12–3.15, standard library only, and refuse optimized Python. Portable SDKs in
user-owned folders do not inherently require administrator access. Follow
device policy and do not bypass restrictions.

## Supported comparison scope

- Public top-level types and nested public types with a fully public enclosing
  chain; public methods, constructors, fields, properties, events and accessors.
- Overload parameter types, generic arity/constraints, return types, base types,
  implemented interfaces, declaration flags and public accessor presence.
- Supported arrays, pointers, references, generic instantiations, function
  pointers and required/optional signature modifiers.

Return types/flags are compared values rather than method identity. Duplicate
identities and unsupported delimiter-bearing type names fail with coverage
errors. See [the exact version 1 format](docs/FORMAT.md).

**No differences means only the supported declarations matched.** It is not a
source, binary, runtime, semantic-versioning or game-compatibility verdict.
Exclusions include constant/enum values, parameter names/defaults and `ref`
versus `out` flags, nullable annotations, custom attributes, marshaling, layout
offsets, type forwarders, assembly version/strong-name identity and method bodies.
Changing framework/compiler versions can itself change reference scopes/flags.

## Files, reports and evidence

Use trusted completed ordinary local files and stop producers first. Existing
symlink/reparse components and UNC paths are refused. Portable .NET checks do
not prove Unix regular-file type or prevent adversarial path replacement.
Windows sharing blocks writers during a read; size/time checks are sampled.
Two bounded immutable input snapshots are taken sequentially, not atomically.
Each input is at most 32 MiB; metadata/signature/work limits are in
[FORMAT.md](docs/FORMAT.md).

Inputs and existing reports are preserved. An optional `--output` file must be
new with an existing parent. A failed fresh write can leave a partial report.
This standalone release adds an explicit output-leaf metadata check before
creation, refusing observed existing leaves including dangling symbolic links.
The CLI change is limited to that precheck; the inspector, report format and
fictional fixture sources are unchanged. Check/create race windows remain.
There are no downloads, scans, installs, network calls or telemetry in the CLI.
Reports retain API/assembly names, declaration details and input SHA-256 values;
metadata may contain identifying/path-like text even though wrapper paths,
method bodies, resources and PDB paths are omitted. Keep real reports private.
Inspecting an assembly grants no right to republish it or its declarations.

Qualification requires four fresh Windows/Ubuntu x64 source-build/runtime lanes
and eight Python source/build-helper lanes. Actual versions, counts, outcomes
and skips are recorded in release `VALIDATION.json`; the planned matrix is not
a passing result. Read [qualification](docs/QUALIFICATION.md) and the separate
[historical .NET 8 validation](docs/VALIDATION.md).

See [provenance](docs/PROVENANCE.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
[Report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=dotnet_api_bug.yml)
or [suggest a feature](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=dotnet_api_suggestion.yml)
using minimal authored fixture source. Do not attach private DLLs, actual API
reports, personal paths, account details or proprietary source.
