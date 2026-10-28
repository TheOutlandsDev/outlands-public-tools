# Local Site Builder 1.0.2 - portable Windows x64, package 1

Extract All, double-click **Local Site Builder.cmd**, choose/confirm a private
admin password in the console, then sign in as admin in the local browser editor.
Node 24.22.2, all 86 locked npm dependencies and compiled native SQLite are
included. No npm, compiler, installer, account, admin rights or PATH change is
needed for ordinary operation. [Complete first run and recovery](START-HERE.txt).

## Reproduce one useful workflow

The supplied Cedar Workshop is fictional. Edit Welcome, Save Draft, reload the
separate public preview and observe the original headline. Publish explicitly;
the preview changes. Save a newer private draft, stop with Ctrl+C and restart.
Sign in again: both versions persist and the old session has expired. Stop before
backup; verify it, restore into a new explicit data directory, and reopen the
published page and newer draft. Running backups, changed backups and existing
restore destinations are refused. Original data is preserved.

Private defaults are under the Windows local application-data directory,
Outlands/LocalSiteBuilder: .env contains the password hash/session secret, and
data contains SQLite, drafts, uploads, inbox, published pages and logs. Neither
is stored in the extracted package. Backups include private content/logs but
exclude credentials; preserve .env separately. Selecting a restored --data path
is explicit on every launch; default double-click continues to open default data.
There is no automatic reset, migration, password reset or public hosting.

## Exact release inputs and publication gate

- Application/source ZIP 1.0.2 is unchanged, pinned to
  `42d4490e62c7ffb5d4d40a19e0c27e3ceb2d8897`.
  Source ZIP SHA-256: `d5253bcff738c69b4f60a5b2c4ecf94f3044512ed41b9f4a91d6897af029ff11`.
- Official [Node 24.22.2 Windows x64](https://nodejs.org/dist/v24.22.2/)
  ZIP SHA-256: `ca1bff5d8ead13c9f2ea404a176db46bd430704d5b5113734049fa365e7799e2`.
  Deliver its exact executable, LICENSE, README and CHANGELOG; npm/node-gyp remain
  build tools and are excluded from runtime/. All component notices are retained.
- All 86 dependencies are fetched by the original package-lock's SHA-512 pins.
  Complete published tarball bytes, including source/licenses, are reconstructed
  under node_modules without install scripts or generated npm state.
- better-sqlite3 13.0.3 includes native modules in its published npm tarball.
  Its unchanged win32-x64 prebuild uses Node-API 10. NATIVE-ORIGIN.json records
  the exact selected module and digest. No compiler, node-gyp invocation or
  dependency install script runs during packaging or user startup.
- Windows and Ubuntu independently reconstruct identical ZIP/receipt/checksum
  bytes from the same pinned public inputs. Every npm member and runtime/wrapper
  byte is independently compared again before publication, including the native
  module. This verifies distribution provenance, not independent review of
  upstream native implementation or compiler reproducibility.
- The release workflow requires all **32 original integration tests, zero skips**,
  a fresh extracted ZIP, literal CMD health entry point with hostile external
  Node settings, real SQLite, external private storage, 16 end-to-end checks
  including hosted Chromium draft/publish/restart/backup/restore, unchanged
  distribution and independent input audit before immutable main publication.
  Consult the actual workflow result and public acceptance.json; configuration
  alone is not a passing run. Public SHA256SUMS.txt covers ZIP/receipt/acceptance.

## Contribution and methodology

Connor designed the application and its workflow. The original source preserves
its project-specific contribution and AI-assistance disclosure. This packaging
adds runtime/dependency verification, a private first-run launcher, guarded
maintenance commands and reproducible synthetic acceptance without changing
application behavior or data format. Original source, full dependency notices,
source pins and test boundaries remain inspectable. The release uses a separate
tag and never replaces the source-only ZIP or older releases.

## Limits

Windows 11 x64 is the target. Automated hosted Windows/Chromium qualification
is distinct from a human using Explorer on a Node-free PC; that manual test and
default-browser integration remain unperformed. ARM64/32-bit packages, mobile
editing, other browsers, independent security/accessibility review and power-loss
recovery remain unqualified. The outer ZIP/CMD is unsigned. Checksums are not
signatures and package verification is not malicious-code sandboxing.

The editor is single-user, loopback-only, with memory sessions. Email delivery is
forced off by this wrapper. Publish updates local generated pages only; internet
hosting remains separate. Disk failure during multi-resource publication can
leave an incomplete output requiring retry. Trusted ordinary local storage is
required; path checks do not defeat every reparse tag or adversarial race.
See the unchanged [application limits](../../../tools/local-site-builder/docs/VALIDATION.md)
and [original source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/local-site-builder-v1.0.2).
