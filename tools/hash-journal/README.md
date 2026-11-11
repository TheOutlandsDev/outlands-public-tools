# OUTLANDS | Hash Journal

Create and verify a small offline hash-chained event journal. Each record links
its sequence, previous hash and exact text to the next record. `create` writes a
new journal, `append` writes a new version while preserving its input, and
`verify` checks an explicitly selected file against optional independently
retained head and count values.

Download the **0.2.0 source ZIP** from the
[Hash Journal release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/hash-journal-v0.2.0).
Extract it into a fresh source directory and follow [USAGE.md](USAGE.md). The ZIP
contains original [MIT source](LICENSE), tests, documentation and fictional
examples. It contains no compiled app, SDK, runtime, dependency binary, original
private project, real journal or raw local diagnostic log.

**A valid unanchored chain proves internal consistency only.** Anyone who can
replace a journal can recompute the entire chain. Removing a complete-record
tail can also leave a valid prefix. Keep the expected head and count in a
separately trusted place to detect replacement or truncation. A matching head
does not establish who wrote an event, whether it is true, or when it occurred.

## Prerequisites and build

The default target is **.NET 10 LTS (`net10.0`)**, using pinned SDK **10.0.404**.
The additional target is **.NET 11 (`net11.0`)**, using pinned SDK **11.0.100**
and an explicit `-p:TargetFramework=net11.0` on both restore and build. Select the
Windows x64 or Ubuntu x64 SDK for your system. Exact official archive URLs and
SHA-512 digests are recorded in [docs/SDKS.json](docs/SDKS.json).

Keep SDKs, build artifacts and actual journals in an external
[private workspace](docs/PRIVATE-WORKSPACE.md). Portable prerequisites can be
extracted into a user-owned folder without inherently needing administrator
access. Follow device policy; do not bypass restrictions. Ubuntu must already
have the required operating-system libraries.

From the freshly extracted source folder, using the selected pinned SDK:

```text
dotnet restore HashJournal.csproj --configfile NuGet.Config --artifacts-path ABSOLUTE_PRIVATE_BUILD
dotnet build HashJournal.csproj -c Release --artifacts-path ABSOLUTE_PRIVATE_BUILD --no-restore
```

For .NET 11, select its pinned SDK and add `-p:TargetFramework=net11.0` to **both**
commands. [USAGE.md](USAGE.md) provides complete Windows/Ubuntu commands and a
fictional create → append → anchored-verify walkthrough.

There are no NuGet packages. `NuGet.Config` clears feeds; matching reference
packs must already be in the selected SDK. It does not fetch missing packs or
perform a dependency advisory audit. Once built, the CLI needs only its app
files and matching .NET runtime. It needs no Python, network, model or account.
Python 3.12–3.15 is used only by optional source/release helpers, which refuse
optimized Python (`-O`, `-OO` or `PYTHONOPTIMIZE`).

## Supported boundaries

- Strict UTF-8 without BOM; one JSON object per LF-terminated line. CRLF,
  missing final LF, blank lines, duplicate/unknown members and invalid text
  are refused. Version 1 and its golden hashes are unchanged in 0.2.0.
- At most 1 MiB per journal, 64 KiB per line, 10,000 records and 8,192 UTF-8
  bytes per nonblank event text. These bounds apply together.
- Select absolute paths in existing trusted, unchanged parent folders.
  Existing outputs and observed links/reparse points are refused. Windows
  network/device/alternate-stream paths are unsupported. Choose trusted local
  storage on Unix; mount topology is not an isolation boundary.
- Path-link and input size/time checks have race windows. They do not create
  an atomic snapshot or contain hostile concurrent writers. A failed fresh
  output may be partial; inspect it privately and choose another new filename.
- Journals store event text in clear text. Arguments, shell history, OS records
  and redirection can retain private material. Unix output requests owner-only
  mode; Windows inherits the selected parent's ACL.

Read [the exact format](docs/FORMAT.md), [privacy guidance](SECURITY.md) and
[provenance](docs/PROVENANCE.md).

## Validation and contribution

Qualification separates four Windows/Ubuntu x64 SDK/runtime lanes from eight
Windows/Ubuntu Python 3.12–3.15 source/build-helper lanes. Read the release's
`VALIDATION.json` for actual discovered/passed/failed/skipped totals;
[docs/QUALIFICATION.md](docs/QUALIFICATION.md) explains the checks. A skip is not
a pass. The historical 0.1.0 result of 73 discovered cases is separate evidence
in [docs/VALIDATION.md](docs/VALIDATION.md).

Generated fixtures cover parsing, golden hashes, tampering, anchoring,
valid-prefix truncation, bounded I/O, input preservation, fresh outputs and CLI
errors. The [example guide](examples/README.md) includes a fictional file and
independently calculated expected head.

[Suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=hash_journal_suggestion.yml)
or [report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=hash_journal_bug.yml).
Include the source version, SDK/OS, expected behavior and a minimal fictional
reproduction. Keep real journals, personal paths, accounts, secrets and
proprietary source out of public reports. Read [CONTRIBUTING.md](CONTRIBUTING.md).
