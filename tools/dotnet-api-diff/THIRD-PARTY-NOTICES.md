# Third-party notices

Original C# source, Python helpers, tests, docs and fictional fixture source:
Copyright (c) 2026 TheOutlandsDev. [MIT License](LICENSE).

The .NET SDK/runtime, framework and standard-library implementations are
supplied separately and retain their applicable licenses. No SDK, runtime,
NuGet package implementation, installer, compiled app or fixture DLL is bundled.
See the official [.NET runtime license](https://github.com/dotnet/runtime/blob/main/LICENSE.TXT)
and [SDK license](https://github.com/dotnet/sdk/blob/main/LICENSE.TXT).

Optional source/release helpers use Python's standard library. Python is
installed separately and is not bundled or relicensed. See the
[Python license](https://docs.python.org/3/license.html).

There are no `PackageReference` entries. `NuGet.Config` clears feeds; required
reference packs must already exist in the selected SDK. Pinned archive URLs
and SHA-512 digests in [docs/SDKS.json](docs/SDKS.json) identify prerequisites,
not included binary implementations. This is not a dependency advisory audit.

The metadata reader is used through public .NET interfaces; its implementation
is not original OUTLANDS work. Its trusted-input warning and upstream terms
remain applicable. Inspecting an assembly or its public declarations grants
no right to redistribute the assembly/report. Actual inputs, private original
helpers and external material retain their respective rights and notices.
