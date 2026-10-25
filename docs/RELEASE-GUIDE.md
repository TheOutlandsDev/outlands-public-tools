# Curated source release guide

This collection ships original MIT source, tests, documentation and fictional
examples. It includes no installed runtime, dependency implementation, game/mod
payload, operational configuration, or real application data. Use the
[catalog](CATALOG.md) as the tool index and the individual README as the setup
and platform contract. The [source review](PUBLIC-SOURCE-REVIEW-2026-10-25.md)
records retained legal attribution and finding dispositions.

## Choose a starting point

| Work | Start here | Requirements and limits |
| --- | --- | --- |
| Review a release or update | [Release Preflight](../tools/release-preflight/README.md) | Python 3.12+, standard library; local static checks/plans |
| Package selected source or back up private files | [Verified Transfers](../tools/verified-transfers/README.md) | Python 3.12+, standard library; externally pinned manifests; opaque backup contents |
| Audit source and documentation | [Public Release Audit](../tools/public-release-audit/README.md), [Documentation Check](../tools/documentation-check/README.md) | Bounded pattern/link checks; findings need review |
| Inspect locks, layouts, file inventories or XML | [Catalog](CATALOG.md) | Read each tool's documented filesystem and schema requirements; earlier POSIX validation does not prove Windows acceptance |
| Generate DOCX | [Document Builder](../tools/document-builders/README.md) | Declared python-docx dependency; subset conversion and metadata limits |
| Move or recover files | [Safe File Mover](../tools/safe-file-mover/README.md) | Start with a disposable plan; move/purge actions change data; native Windows/SMB behavior has limits |
| Plan maintenance | [Server Maintenance](../tools/server-maintenance/README.md) | Offline operator-supplied facts; no process or readiness inspection |
| Inspect ELF dependencies | [Offline ELF Inspector](../tools/offline-elf-inspector/README.md) | Python 3.12/3.13, standard library; static metadata and conservative candidate graphs; reports remain private |
| Keep Windows awake | [Keep Awake](../tools/keep-awake/README.md) | Windows runtime; recorded simulation does not establish native acceptance |
| Set up work and review data | [Project Workspace](../tools/project-workspace/README.md), [Dataset Review](../systems/dataset-review/README.md), [Methodology](../methodology/README.md) | Explicit private inputs/outputs; neutral workflow templates |
| Edit a local site | [Local Site Builder](../tools/local-site-builder/README.md) | Node 24 and its pinned npm dependencies; local session/backup limits |
| Generate a portfolio site/PDF | [Portfolio Builder](../tools/portfolio-builder/README.md) | Python 3.12/3.13, its pinned PDF dependencies and optional Tk desktop |
| Track jobs and quotes | [Job & Quote Tracker](../tools/job-quote-tracker/README.md) | Python 3.12/3.13, standard library and optional Tk desktop |

Keep your working stores, generated sites/documents, customer/player records,
evidence, credentials, reports and backup bundles outside the source checkout.
Input data and third-party dependencies retain their own rights and licenses.

## Verify release files

The curated release has three assets:

- `outlands-public-tools-v0.1.0-source.zip`: exact selected Git tree, without Git
  history, caches, dependencies, private ledgers or runtime outputs.
- `SOURCE-MANIFEST.json`: public commit/tree identity and a relative path,
  byte length and SHA-256 for every source file.
- `SHA256SUMS.txt`: SHA-256 of the ZIP and external source manifest.

Before extraction, compare the downloaded ZIP and manifest with the checksums:

```powershell
Get-FileHash -Algorithm SHA256 ./outlands-public-tools-v0.1.0-source.zip
Get-FileHash -Algorithm SHA256 ./SOURCE-MANIFEST.json
```

On a system with the standard `sha256sum` utility:

```text
sha256sum -c SHA256SUMS.txt
```

Obtain checksums from a separately trusted release view. Matching files and
checksums from the same compromised source do not establish authenticity.
The manifest is an inventory of this source release, not proof that a future
operator input, package or generated output is public-safe.

## Validation record

The Windows/Python 3.12.7 collection regression run discovered 129 methods:
124 passed and five native link cases were skipped. The new preflight fixture
commands passed, and application source manifests were checked. These results
are independent of older tool-specific suites recorded in their README/review
files. GitHub's release-commit workflow provides the current Windows/Linux app
and collection checks; consult its actual result for the chosen revision.

These checks do not establish native game/server operation, production
acceptance, network-share or power-loss recovery, application data consistency,
or complete secret/IP clearance. See [Batch 8](BATCH-8-REVIEW.md), the
[catalog](CATALOG.md), and [licensing](../LICENSING.md). Older Git history and the
standalone repositories may retain previous owner attribution; the current
source package uses the owner's selected public identity.
