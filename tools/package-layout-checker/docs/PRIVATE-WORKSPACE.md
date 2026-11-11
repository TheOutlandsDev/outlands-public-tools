# Private workspace

Extract public source into a fresh directory. Choose a separate existing,
user-owned private parent for interpreters/venvs, authored packages/manifests,
stdout captures and qualification:

```text
source/package-layout-checker-0.1.0/ selected source only
private/package-layout/
  venv312/                         separately created no-pip environment
  fictional_walkthrough.py         private copy of the verification driver
  fictional-demo/                  new owned packages and outside-package controls
  captures/                        caller-selected private stdout/diagnostics
  qualification/                   extraction, environment, fixtures, receipts
```

Keep `layout_check.py` and `layout_windows.py` adjacent. Select the intended
interpreter/script explicitly and provide both `--root` and `--manifest`.
The checker has no project/data default, environment expansion, output writer,
installer, network action or source execution. It writes only stdout. Shell
redirection/caller code independently controls any captured file and can
overwrite it; deliberately choose new private capture paths.

Actual manifests may contain private literal rules. Relative declared names
remain in results even though source, matched literals, parser excerpts,
native/root paths and raw errors are omitted. Fixed codes are not anonymization;
library tracebacks, captured results and surrounding logs need separate review.
Keep actual package/control/result material private and prepare a separate
reviewed export before sharing anything.

Only declared files are checked. Presence-only entries use metadata without
reading content, and unlisted entries are not enumerated/opened. A passing
manifest is not an exact export allowlist or proof of privacy, ownership,
licensing, dependency safety, runtime correctness or release acceptance.
Static Python syntax depends on the selected running parser.

Use stable ordinary files under trusted quiescent local parents. The manifest
and selected files require supported single-link/type/path metadata. POSIX
descriptor anchoring and Windows retained native handles have distinct limits.
Observed links/reparse/identity changes are refused; unsupported Windows volume/
alias/stream/name spellings remain outside scope. Reads may affect access
metadata, and Python caches are separate. The supplied driver uses `-B` and
checks existing bytes/tree entries, not every OS property.

There are no package/report writes to roll back. Interrupted or failed stdout
capture can be partial; require a complete JSON value and actual successful
result. Sampled checks/sharing are not an atomic snapshot, hostile-filesystem
sandbox, universal deadline, mount/drive-rebinding, live/network/virtual-provider
or power-loss guarantee. ACL privacy/streams/topology are outside the checks.
Read [WINDOWS.md](WINDOWS.md), whose historical wording is preserved with only
its standalone review hyperlink updated.

User-owned Python/venvs do not inherently require administrator access. Respect
device policy and OS prerequisites without bypasses. No pip packages, network,
model or account are required; interpreters remain separately licensed.

Build/qualification outputs must be new private paths outside source with
existing parents. Publish reviewed source and sanitized validation only,
excluding actual packages/manifests/literals/results, original private code,
personal paths, runtime/dependency binaries and raw logs. See
[USAGE.md](../USAGE.md), [QUALIFICATION.md](QUALIFICATION.md) and
[PROVENANCE.md](PROVENANCE.md).
