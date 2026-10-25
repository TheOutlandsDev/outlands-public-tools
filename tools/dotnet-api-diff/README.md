# .NET Public API Diff

Compare the public metadata declarations in two builds of the same managed assembly. This C# command-line tool reads PE metadata without loading the assembly, running its module initializer, resolving its dependencies, or invoking methods. It helps review a library or plugin update before a release.

**Use only trusted, completed local build artifacts that you own or are permitted to inspect.** The .NET metadata reader is not a security boundary for hostile DLLs. Microsoft documents that malformed or malicious metadata can crash or hang its readers. See the [Microsoft metadata trust warning](https://learn.microsoft.com/dotnet/api/system.reflection.metadata). File limits and signature checks reduce accidental processing problems; they do not make arbitrary downloads safe to inspect.

## Quick start

Install a .NET 8 SDK, clone this repository, and open a terminal in `tools/dotnet-api-diff`. No NuGet packages are used; the supplied configuration deliberately clears external feeds. Run these commands in either PowerShell or a POSIX shell:

```text
dotnet restore tests/ApiDiff.Tests.csproj --configfile NuGet.Config --artifacts-path ../../../.outlands-api-build --nologo
dotnet build tests/ApiDiff.Tests.csproj -c Release --artifacts-path ../../../.outlands-api-build --no-restore --nologo
dotnet ../../../.outlands-api-build/bin/ApiDiff.Tests/release/ApiDiff.Tests.dll
dotnet ../../../.outlands-api-build/bin/ApiDiff/release/ApiDiff.dll --help
```

The artifacts directory is outside the repository. The test project builds two fictional `Example.Plugin` assemblies, so this example needs no game files or third-party DLLs:

```text
dotnet ../../../.outlands-api-build/bin/ApiDiff/release/ApiDiff.dll compare --before ../../../.outlands-api-build/bin/Before/release/Example.Plugin.dll --after ../../../.outlands-api-build/bin/After/release/Example.Plugin.dll
```

Expect exit code **1** and six declaration changes: an added method, two removed methods (including a public setter), and three changed declarations. This nonzero result means differences were found. It is not a test failure.

For your own assembly, replace the `--before` and `--after` arguments with quoted local file paths. To save JSON, add `--output report.json`. Its parent directory must already exist, and the output file must be new. Existing reports and source assemblies are never overwritten. There are no automatic downloads, network calls, directory scans, installation steps, or telemetry.

| Exit | Meaning |
| --- | --- |
| `0` | Supported declarations are equal, or help was requested. |
| `1` | Supported declarations differ; a complete report was emitted. |
| `2` | Input, output, or coverage failed. No successful comparison is claimed. |

## What it compares

- Public top-level types and nested public types whose entire enclosing chain is public.
- Public methods, constructors, fields, properties, events, and public accessor methods. Protected/internal/private members are excluded.
- Overload parameter types, generic arity/constraints, return types, base types, implemented interfaces, declaration flags, and public accessor presence.
- Arrays (including shapes), pointers, references, generic instantiations, function pointers, and required/optional signature modifiers.

Return types and flags are compared values rather than part of method identity, so changing a return type is reported as `changed`. Overloads remain separate. Duplicate identities and unsupported delimiter-bearing type names fail with a coverage error rather than silently merging declarations. The initial type-name character subset is described in the format guide.

**No differences means only the supported declarations matched.** This is not a source, binary, runtime, semantic-versioning, or game-compatibility verdict. Important exclusions include constant and enum values, parameter names/defaults and `ref` versus `out` parameter flags, nullable annotations, custom attributes, marshaling, layout offsets, type forwarders, assembly version/strong-name identity, and method bodies. See [the format and scope](docs/FORMAT.md) before relying on a result.

## Inputs, limits, and privacy

Only regular, completed local build files are supported. Do not point this tool at devices, FIFOs, sockets, remote paths, changing build outputs, or directories controlled by an untrusted process. Existing reparse points/symlinks and UNC paths are refused; portable .NET path checks cannot prove that a Unix path is a regular file or prevent an adversarial path replacement race. Windows file sharing blocks writers while reading. Length and last-write observations detect some changes; they are not an atomic snapshot guarantee on every filesystem. Stop producers first.

Each assembly is read into a bounded immutable in-memory snapshot (32 MiB maximum). The two snapshots are taken sequentially. Limits also cover metadata rows, signatures, nesting, decoding work, and declarations; [FORMAT.md](docs/FORMAT.md) lists the exact bounds. Exceeding a limit fails the whole comparison.

Reports contain API names, declaration details, assembly simple names, and input SHA-256 hashes. They omit input filesystem paths, method bodies, resources, debug data, and PDB paths. Metadata itself can contain identifying names or embedded path-like text. Keep real reports private until reviewed; this is not an anonymizer. Example sources are fictional and MIT licensed. Dependencies retain their own licenses; inspecting a DLL grants no right to republish it.

## Learn, test, and contribute

- [Guided fictional example](examples/walkthrough.md)
- [Report format, canonical identities, and exclusions](docs/FORMAT.md)
- [Validation and test coverage](docs/VALIDATION.md)
- [Source provenance and license scope](docs/PROVENANCE.md)
- [Contribution guide](CONTRIBUTING.md)
- [Report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=dotnet_api_bug.yml)
- [Suggest a feature](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=dotnet_api_suggestion.yml)

This module's original source and fictional fixtures are available under the [MIT license](LICENSE). Suggestions, small reproductions, and improvements to signature coverage are welcome.
