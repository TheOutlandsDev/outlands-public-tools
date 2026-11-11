# Private workspace

Extract source into a fresh public-source directory. Select a separate existing
user-owned private parent for interpreters/venvs, authored fixture trees,
walkthrough scripts, explicit captures, source packages and qualification work:

```text
source/documentation-check-0.1.0/   selected source only
private/documentation-check/
  venv312/                        separately created no-pip environment
  fictional_walkthrough.py         private copy of the supplied demo block
  fictional-demo/                  new owned good/bad trees
  captures/                        explicitly selected private stdout captures
  qualification/                   extraction, clean venv/test work and receipts
```

The CLI requires an explicit `--root`; it does not choose documents or output
locations. It emits JSON on stdout and writes no selected file/report/manifest.
Ordinary reads can affect OS access metadata. Redirect/capture stdout only to
a deliberately selected fresh private filename; shell redirection may overwrite
an existing destination. Keep captures outside the selected tree/source checkout.

Use ordinary trusted quiescent local trees and fully spelled Windows parents.
Existing path/link/reparse/provider checks remain in force. Sampled checks have
race windows and are not atomic snapshots, hostile-filesystem containment,
universal native-I/O deadlines, live/remote-provider or power-loss acceptance.
Do not weaken a guard to accommodate an unsupported path or provider.

User-owned Python/venvs do not inherently require administrator access. Device
policy and OS prerequisites still apply; never bypass restrictions or change
privilege merely to make tests pass. The CLI requires no package/network service.

Relative filenames, line numbers and findings can identify private work even
without absolute roots. Output is not redacted or anonymous. Shell arguments,
history and captures can retain private information too. Keep real documents,
reports, mappings, credentials and operational evidence private. PASS is limited
documentation hygiene, not secrecy/security or permission to publish a tree.

Source packaging/qualification outputs must be new private destinations with
existing parents, outside source. Their cleanup is limited to owned test work;
the checker does not clean or repair selected document trees. Publish only
designated reviewed source assets and sanitized validation summaries. No real
docs, reports, original helpers, interpreter trees, binaries or raw logs belong
in the source ZIP. Use authored fictional public reproductions. See
[USAGE.md](../USAGE.md) and [QUALIFICATION.md](QUALIFICATION.md).
