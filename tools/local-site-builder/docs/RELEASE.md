# Local Site Builder 1.0.2

[Focused source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-site-builder-v1.0.2/local-site-builder-1.0.2.zip)

Adds checked Windows/Linux launchers, actionable dependency and runtime checks,
a shorter [first-run guide](../START-HERE.md), and
[extracted-ZIP HTTP/CLI recovery acceptance](DOWNLOAD-CHECK.md). Node 24 and
separately installed locked dependencies remain required. No data format or
application dependency changed. Source only; no runtime, credentials or site data.

The release provides SHA256SUMS.txt and a source revision in release-matrix.json.
`downloads/build.py` packages exact committed app blobs and verifies the app
source manifest. Windows and Ubuntu checks freshly extract and install the ZIP,
run tests, prove the fictional workflow and compare the package hashes before
publication. Existing releases remain immutable. No fresh local UI capture was
possible during review; earlier 1.0.1 captures keep their original scope.

## Historical 1.0.1 instructions

# Local Site Builder 1.0.1

[Focused source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-site-builder-v1.0.1/local-site-builder-1.0.1.zip)
· [Release and checksum](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/local-site-builder-v1.0.1)
· [Maintained source](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/local-site-builder)

This patch release adds repeatable browser/recovery acceptance and fixes the
editor toolbar overlap at desktop widths between 1101 and 1700 px. Runtime
dependency versions and data formats are unchanged. No existing website,
credentials or database is migrated.

## Fresh installation

1. Download the focused ZIP and its `SHA256SUMS.txt` from the release. Compare its
   SHA-256 with `Get-FileHash -Algorithm SHA256 ZIP_PATH` on PowerShell or
   `sha256sum ZIP_PATH` on Linux.
2. Extract it to a new folder. Open a terminal in `local-site-builder-1.0.1`.
3. Select Node.js 24 with npm. The native SQLite dependency may use a prebuilt
   binary or require an installed compiler/SDK; none is bundled. Read
   [the setup instructions](../README.md#start-here).
4. Choose a private data directory outside the extracted source and set
   `SITE_DATA_DIR`. Run `npm ci`, `npm run setup`, then `npm start`.
   On PowerShell use `npm.cmd` if necessary.
5. Open the printed loopback admin URL, log in with your new password and try
   [the fictional workflow](../examples/WORKSHOP.md).
6. Stop cleanly before [backup/verify/restore](../README.md#backup-verify-and-recover).
   Restore into a new directory and reopen both public content and private drafts.

Setup creates a private `.env` beside the app. Keep it separate from shared
source and backups. The starter is Cedar Workshop, an invented three-page site;
the release contains no real website, uploads, runtime database or credentials.

## Packaging and provenance

`scripts/package-release.js` checks the explicit reviewed inventory and refuses
uncommitted bytes, extra committed files, existing outputs and outputs inside the
source checkout. It uses Git's ZIP exporter for the selected application subtree,
including its MIT license, retained notices, npm locks and source hash manifest.
Git and Node.js 24 are maintainer packaging requirements; Git is not needed to
run an extracted application.

From a clean committed checkout, choose a new absolute output outside it:

```text
node scripts/package-release.js ABSOLUTE_NEW_ZIP_PATH
```

Only source, fictional templates, tests, documentation and reviewed captures are
shipped. `node_modules`, browser/runtime installations, `.env`, user content,
data/logs/backups and generated test results are excluded. The published release
provides the source commit and outer ZIP checksum. Earlier collection and
standalone releases remain historical; this folder is the maintained application.

See [validation and limits](VALIDATION.md) and [browser reproduction](BROWSER-CHECKS.md).
