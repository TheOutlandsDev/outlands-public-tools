# Provenance and license scope

This module was authored as an original reusable C# implementation for Outlands Public Tools. Its starting use case was a local metadata inspection helper used during plugin development. That earlier helper had project-specific filters and broad metadata output; it is not redistributed here. The bounded decoder, canonical comparison model, command interface, generated metadata tests, and documentation are new work.

All shipped C# test source and example names are fictional and original. Tests build their own assemblies from the included source; no game binaries, commercial SDK assemblies, mod assets, firmware, PDBs, historical output reports, or private filesystem inventories are included.

The module's original files are covered by [MIT](../LICENSE). The .NET SDK/runtime/framework retain their upstream licenses; they are prerequisites, not bundled artifacts. The project has no NuGet package references. `NuGet.Config` clears package sources so a local SDK with the required targeting packs can restore without external feeds.

Reading an assembly does not establish its provenance or grant permission to distribute it or its API report. Users remain responsible for rights and privacy review of their inputs. This tool does not contact a game, launcher, phone, server, or external service.

The trust boundary is based on Microsoft's [System.Reflection.Metadata documentation](https://learn.microsoft.com/dotnet/api/system.reflection.metadata), checked during this module's preparation: its readers are intended for trusted inputs and are not hardened for malicious metadata. The implementation independently reads the public CLI metadata structure; no Microsoft implementation source was copied into this module.
