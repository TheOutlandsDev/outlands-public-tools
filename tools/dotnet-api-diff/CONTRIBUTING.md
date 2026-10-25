# Contributing

Small, reproducible improvements are welcome. Use the [bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=dotnet_api_bug.yml) or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=dotnet_api_suggestion.yml), or submit a pull request using the guidance below.

Describe the .NET SDK/runtime, operating system, command, expected supported declaration, and observed result. Use a tiny fictional source fixture you are allowed to share. Do not upload game assemblies, proprietary dependencies, real reports containing private names, credentials, or binaries you cannot license. Include only reviewed/redacted snippets.

Changes to signature support should include a generated fixture or metadata test, expected canonical output, processing bounds, and an update to `docs/FORMAT.md`. Changes to visibility or comparison scope need a documented rationale. Keep the command metadata-only, read-only, deterministic, dependency-free, and honest about exclusions. Do not replace failed parsing with a partial successful report.

Run the complete generated-fixture test harness and source gate before submitting a pull request. Contributions to this original module are made under its MIT license. Third-party rights and notices must remain intact.
