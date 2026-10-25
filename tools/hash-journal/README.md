# OUTLANDS | Hash Journal

Create and verify a small offline hash-chained event journal. Each record links
its sequence, previous hash and exact text to the next record. The C#/.NET 8
client can create a journal, produce a new version with another event, and verify
an existing file against an optional separately trusted head hash and count.

This is original [MIT source](LICENSE), tests, documentation and fictional
examples in [OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools).
It uses the separately installed .NET SDK/runtime and no NuGet packages. It
starts no service, opens no network connection and includes no wallet, money,
private key, certificate or historical journal data.

**A valid unanchored chain proves internal consistency only.** Anyone who can
replace a whole journal can recompute it. Complete-record tail truncation can
also remain internally valid. Keep a trusted head outside the journal when
you need to detect those changes. A matched head does not establish who wrote
the events, whether they are true, or when they occurred. See [format and
limits](docs/FORMAT.md).

## Build and try the display-only demo

Install the **.NET 8 SDK** (the recorded local build used SDK 9.0.310 with the
installed .NET 8 reference/runtime packs). Open a terminal in this folder.
Choose an existing external private workspace using the collection's
[workspace guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/PRIVATE-WORKSPACE.md). Keep build artifacts and
actual journals outside the source checkout.

PowerShell example; replace the fictional paths with your private folders:

```powershell
$build = 'D:\Private\HashJournalBuild'
dotnet restore HashJournal.csproj --configfile NuGet.Config --artifacts-path $build
dotnet build HashJournal.csproj -c Release --artifacts-path $build --no-restore
dotnet "$build/bin/HashJournal/release/Outlands.HashJournal.dll" demo
```

POSIX shell equivalent:

```sh
build='/absolute/private/hash-journal-build'
dotnet restore HashJournal.csproj --configfile NuGet.Config --artifacts-path "$build"
dotnet build HashJournal.csproj -c Release --artifacts-path "$build" --no-restore
dotnet "$build/bin/HashJournal/release/Outlands.HashJournal.dll" demo
```

`NuGet.Config` clears package feeds because this module has no package
references. Matching SDK reference packs must already be installed. It does
not install a runtime, obtain a missing SDK, or act as a dependency advisory
audit. Build warnings are treated as errors.

The demo prints a clearly marked fictional JSON display and creates no files.
It is not itself a JSONL journal to redirect and later verify. Help is available
with no arguments or `--help`.

## Create, extend and verify

Use **absolute filenames** in an existing trusted private directory. Outputs
must be new filenames. The examples use PowerShell variables from above:

```powershell
$app = "$build/bin/HashJournal/release/Outlands.HashJournal.dll"
dotnet $app create --output 'D:\Private\Journals\events-001.jsonl' --text 'Fictional build prepared.'
dotnet $app append --input 'D:\Private\Journals\events-001.jsonl' --output 'D:\Private\Journals\events-002.jsonl' --text 'Fictional checks passed.'
dotnet $app verify --input 'D:\Private\Journals\events-002.jsonl'
```

`append` reads and verifies the selected old file, then writes a **new version**.
The input is never edited, and an existing output is refused. No input folder,
filename, journal root or destination is chosen implicitly. Missing output
parents are not created. A failed write may leave a new partial file; the error
explicitly warns of that possibility. Inspect that selected file privately
before choosing a new filename. Existing files are not deleted for recovery.

Successful command output is JSON metadata: record count, head hash, anchoring
status and whether an output was written. It omits event text and full paths.
The actual journal contains the complete event text in clear text. Command-line
arguments, terminal history, shell redirection and OS records can also retain
events or filenames; use fictional events in demonstrations and keep actual
journals outside public repositories.

To check a separately trusted head, copy the actual 64-character lowercase head
from a record you independently retained. `TRUSTED_HEAD_HEX` below is a placeholder,
not a valid hash:

```text
dotnet APP_DLL verify --input ABSOLUTE_JOURNAL_FILE --expected-head TRUSTED_HEAD_HEX --expected-count 2
```

A count check alone remains `UNANCHORED`; it can catch a missing tail of known
length but cannot prevent a same-length replacement. The head must be trusted
independently of the file being checked. There is no signature, timestamp
authority, access-control system or automatic external anchor service.

## Format and supported boundaries

- Strict UTF-8 without BOM, one JSON object per LF-terminated line. CRLF,
  missing final LF, blank lines, duplicate/unknown properties and invalid text
  are refused. Do not let an editor convert the line endings silently.
- Version 1 fields: `schema`, `sequence`, `previous`, `text`, `hash`. Sequence
  begins at one and is contiguous. Hashes are lowercase SHA-256 hex. Text is
  hashed as exact UTF-8, without Unicode normalization.
- Maximum 1 MiB per selected journal, 64 KiB per line, 10,000 records and
  8,192 UTF-8 bytes per nonblank event text. These limits apply together; the
  byte ceiling can be reached before the record ceiling.
- Files must be explicit, nonlinked paths in trusted, unchanged parents. The
  client rejects observed symlinks/reparse points, directories, Windows UNC,
  device/alternate-stream paths and mapped network drives. Unix mount topology
  is not an isolation boundary; choose trusted local storage yourself.
- Detected size/timestamp changes fail a read. The checks do not freeze a
  directory tree or prevent every hostile concurrent filesystem replacement.
- Output creation requests owner-only permissions on Unix; Windows inherits
  the selected parent's ACL. Files are not encrypted, anonymized or immutable.

See [the complete format](docs/FORMAT.md), [provenance](docs/PROVENANCE.md),
[validation](docs/VALIDATION.md) and [privacy guidance](SECURITY.md).

## Tests and examples

The tests use generated data and disposable files. They cover strict parsing,
an independent SHA-256 golden value, tampering, reordering, anchoring/truncation,
bounded reads/writes, source preservation, fresh-file semantics and CLI errors.
No historical blockchain, real event log, key, game or network is used.

```powershell
dotnet restore tests/HashJournal.Tests.csproj --configfile NuGet.Config --artifacts-path $build
dotnet build tests/HashJournal.Tests.csproj -c Release --artifacts-path $build --no-restore
dotnet "$build/bin/HashJournal.Tests/release/HashJournal.Tests.dll" 'D:\Private\ExistingTestParent'
```

The optional last argument selects an existing test-parent folder. Without it,
the harness uses the operating system's temporary directory. A fresh owned
subdirectory is created and cleaned up; symlink/Unix-only cases can be skipped
where unavailable. Read the [validation record](docs/VALIDATION.md) and current
Actions results for platform-specific totals.

The [example guide](examples/README.md) includes a fictional two-record JSONL
file and its independently generated head. Keep real journals private.

## Suggestions and contributions

[Suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=hash_journal_suggestion.yml)
or [report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=hash_journal_bug.yml).
Use minimal fictional records and include the source commit, SDK/OS and expected
versus actual behavior. Do not attach real journals, secrets, private filenames,
account details or proprietary source. Read [contributing](CONTRIBUTING.md).

Exit code `0` means the selected command completed its stated scope; `2` means
a fixed structured validation/I/O error. An unanchored success is not an
authenticity result or a complete system/application recovery guarantee.
