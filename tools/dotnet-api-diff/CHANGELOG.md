# Changelog

## 0.1.0

- Added the initial standalone source-ZIP release of the existing original
  .NET Public API Diff implementation and fictional fixture sources.
- Set .NET 10 LTS (`net10.0`) as default using pinned SDK 10.0.404, with explicit
  .NET 11 (`net11.0`) builds using pinned SDK 11.0.100 across all four projects.
- Added source inventory/packaging helpers and fresh qualification for four
  Windows/Ubuntu x64 SDK/runtime lanes and eight Python 3.12–3.15 helper lanes.
  Actual results and interpreter patches are recorded in release `VALIDATION.json`.
- Added standalone usage, private-workspace, qualification and external notices.
- Preserved `Program.cs`, `Inspector.cs`, version 1 format, provenance,
  historical validation, fixture API source and the six-change walkthrough.
- Kept SDKs/runtimes, compiled DLLs, original private material, actual input
  assemblies/reports and raw diagnostics outside the source release.
