# Markdown Document Builder: standalone usage

Use the source ZIP with a matching CPython 3.12, 3.13, 3.14 or 3.15.2 runtime.
Qualification covers Windows x64 and Ubuntu x86_64. Use canonical local paths
and a trusted private working directory outside the unpacked source. Nothing
below requires administrator privileges or PowerShell script activation.

Download the release ZIP, `USAGE.md`, `VALIDATION.json`, `build-manifest.json`
and `SHA256SUMS.txt` together. Verify the four checksum rows before unpacking.
Compare the ZIP hash with the separately reviewed release description too;
files from the same untrusted source do not independently authenticate each
other. `SOURCE-MANIFEST.json` records the unpacked allowlisted source bytes.
The source ZIP contains no interpreter, wheels, environments or generated DOCX.

## Prepare the exact dependencies

The runtime closure is `python-docx==1.2.0`, `lxml==6.1.3` and
`typing_extensions==4.16.0`. Installer `pip==26.3` has its own lock. Read
[the dependency method](dependency-locks/README.md) and
[DEPENDENCIES.json](dependency-locks/DEPENDENCIES.json) before downloading/installing. The binary
wheels are obtained from PyPI's official file host and verified against selected
sizes and SHA-256 values. They are not bundled or relicensed by this source ZIP.
This is a reproducible version selection, not a dependency security audit.

The following PowerShell variables are **fictional examples**. Replace them with
your actual unpacked source directory, matched Python executable and an existing
private parent. Choose new child directories; do not reuse an unrelated folder.

```powershell
$source = 'D:\Source\document-builders-0.1.0'
$python = 'D:\Private\Python315\python.exe'
$privateWork = 'D:\Private\document-builder-review'
$wheelhouse = Join-Path $privateWork 'new-wheelhouse'
$environment = Join-Path $privateWork 'new-environment'
```

Download and verify the four wheels for the host platform/interpreter. This
step makes HTTPS requests; the document builder itself has no download step.

```powershell
& $python -I -B (Join-Path $source 'packaging/dependencies.py') --download $wheelhouse
& $python -m venv $environment
$py = Join-Path $environment 'Scripts/python.exe'
```

For this Windows CPython 3.15 example, install the exact installer and three
runtime wheels offline. `--force-reinstall` ensures an already installed pip
does not bypass the pinned installer selection. No activation script or policy
change is needed.

```powershell
& $py -m pip install --force-reinstall --no-index --find-links $wheelhouse --only-binary=:all: --no-deps --require-hashes -r (Join-Path $source 'dependency-locks/installer.txt')
& $py -m pip install --no-index --find-links $wheelhouse --only-binary=:all: --no-deps --require-hashes -r (Join-Path $source 'dependency-locks/requirements-windows-cp315.txt')
& $py -m pip check
```

Select `cp312`, `cp313`, `cp314` or `cp315` to match the interpreter. On Ubuntu,
use the corresponding `requirements-ubuntu-cpNNN.txt` and environment
`bin/python` path; the download helper selects the host lane. Do not substitute
a different platform's wheel or disable hash/version checks. The selected
qualified lanes and exact artifact filenames are in `DEPENDENCIES.json`.
The convenience root `requirements.txt` permits the selected closure across
the declared lanes; qualification installs the narrower per-lane lock.

For a no-pip application environment matching the qualification architecture,
use `packaging/qualify.py` with an external wheelhouse and owned workspace.
It uses the separately pinned installer wheel; see
[qualification details](docs/QUALIFICATION.md). Keep all downloaded wheels and
environments private, outside the source tree.

## Fictional create, inspect and refusal walkthrough

These commands use only the bundled authored Markdown. Create the private parent
yourself before running them; the builder creates neither the parent nor a
missing directory. The first command shows static help and writes no document.

```powershell
$script = Join-Path $source 'markdown_docx.py'
$inputFile = Join-Path $source 'examples/fictional_request.md'
$document = Join-Path $privateWork 'new-fictional-request.docx'
& $py -B $script --help
& $py -B $script --input $inputFile --output $document --title 'OUTLANDS Synthetic Example'
```

Creation returns 0 and prints exactly this message (with the host's stdout line
ending):

```text
Document created; review its content before sharing.
```

The fictional package contains the title, “Fictional Parts Request”, a three-
column table with `DEMO-A`/`DEMO-B`, headings and lists. Its configured core
creator and last-modified-by are `OUTLANDS`; created/modified values are the
fixed neutral `2000-01-01T00:00:00Z`. Review the document content and package
metadata before sharing. Default-template application properties, a thumbnail,
custom XML and ZIP member timestamps remain. Package checks do not verify
Word/LibreOffice visual rendering, and whole-DOCX bytes need not reproduce.

Repeat the same build command. It returns 2, prints no success message and emits
the fixed stderr line below. The original document remains byte-for-byte intact.

```powershell
& $py -B $script --input $inputFile --output $document --title 'OUTLANDS Synthetic Example'
```

```text
DOCUMENT_BUILD_FAILED:OUTPUT_EXISTS
```

An overlong title is refused before creating a document:

```powershell
$longTitle = 'X' * 161
$rejectedDocument = Join-Path $privateWork 'rejected-title.docx'
& $py -B $script --input $inputFile --output $rejectedDocument --title $longTitle
```

This returns 2 and emits `DOCUMENT_BUILD_FAILED:TITLE_INVALID`. The new output
does not exist. A separate missing-site-packages probe demonstrates the fixed
dependency refusal without uninstalling anything from the environment:

```powershell
$missingDependencyDocument = Join-Path $privateWork 'missing-dependency.docx'
& $py -S -B $script --input $inputFile --output $missingDependencyDocument --title 'OUTLANDS Synthetic Example'
```

It returns 2 and emits `DOCUMENT_BUILD_FAILED:DEPENDENCY_UNAVAILABLE`. No output
is created. `-S` is used only for this diagnostic; ordinary builds use the locked
environment normally. There is no `--version` option. Unknown or incomplete
arguments return `DOCUMENT_BUILD_FAILED:ARGUMENTS_INVALID` without echoing values.

## Safeguards and recovery

The builder reads only the selected regular Markdown input. It limits bytes,
lines, line length, title length and rectangular table shape. Symlink paths,
parent traversal and invalid inputs are refused. Windows additionally checks
native handles/identities, single links, reparse points, streams, ambiguous names
and observed short aliases. POSIX retains its original file behavior; do not
assume every Windows-only policy is a POSIX refusal. In particular a regular
hardlinked input can be read on POSIX, while Windows refuses it.

Existing files, directories and destination links are never intentionally
replaced. The complete DOCX is constructed in memory before exclusive output
creation. Windows retries short writes, flushes and checks final size/identity.
Failure after creation retains a partial or unconfirmed new file; preserve it
for review and choose a different new name. POSIX attempts to remove its own
same-identity newly created file after a failed write. Neither policy is a
backup transaction, atomic snapshot or protection against a hostile filesystem.
The program does not enforce a source-directory exclusion; keep outputs private
through the explicit paths above. Windows ACL confidentiality is not established.

Real Markdown, titles, generated documents, private diagnostics and logs remain
private until separately reviewed. Validation does not anonymize them, establish
business accuracy or authorize publication.
