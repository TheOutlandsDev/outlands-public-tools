# Private workspace

Extract public source into a fresh directory. Choose a separate existing,
user-owned private parent for Python/venvs, fictional work, real locks, stdout
captures and qualification receipts:

```text
source/dependency-lock-diff-0.1.0/  selected source only
private/lock-diff/
  venv312/                         separately created no-pip environment
  fictional_walkthrough.py         private copy of the documented driver
  fictional-demo/                  new owned fictional locks and extra files
  actual-before.lock               actual private declarations
  actual-after.lock                actual private declarations
  captures/                        caller-selected stdout and diagnostics
  qualification/                   extraction, environments and receipts
```

Select the intended interpreter and `lock_diff.py` explicitly. Provide
`--before FILE --after FILE`; there is no project/environment default, output
writer, package manager, installer, resolver or network action. The CLI reads
only the selected two locks and prints JSON stdout. Extra adjacent files and
package artifacts are not enumerated or opened. Shell redirection/caller code
independently controls any saved capture and can overwrite it; select new
private capture paths deliberately.

Package names, versions, hashes, comments and relationships can identify a
project or its dependencies. Results omit raw comments and selected paths but
retain declarations and exact input hashes. Fixed errors omit native details
and supplied content, without anonymizing results, caller logs or formatted
library tracebacks. Keep actual locks/results private and review a separate
export before sharing. A declaration or matching digest is not independent
artifact authentication, vulnerability status, reproducibility or permission
to install or publish anything.

Use stable ordinary files under trusted quiescent local ancestors. The reader
requires usable identities, ordinary single-link files and supported path/type
metadata, with sampled ancestor/descriptor/path checks before/during/after
reads and both inputs rechecked after comparison. Observed link/reparse,
multi-link, special-file, identity change and unsupported name/path forms are
refused. Original path suffixes are checked before Windows absolute-path
normalization can erase them.

Sequential sampled checks do not form an atomic two-file transaction,
immutable snapshot or hostile-filesystem sandbox. Mount aliases/rebinding,
remote/provider behavior, blocked OS I/O, mapped writers, power loss and ACL
privacy remain outside acceptance. No network probe is made; underlying storage
can still be remote. Reads can affect OS access metadata; Python caches are
separate. Bounds are not total CPU/memory/deadline quotas.

Require complete JSON and the actual exit/status before trusting a capture.
Output is bounded before printing, but interruption or OS stdout failure can
leave partial captured output. There is no checker-owned report tree to roll
back. The guide keeps its authored fictional work for inspection without
automatic cleanup or rollback.

User-owned Python/venvs do not inherently need administrator access. Respect
device policy and OS prerequisites without bypasses. No pip distributions,
network, model or account are needed. Test-only public validator sources are
separate from CLI execution; interpreters remain separately licensed.

Build/qualification outputs must be new private paths outside source with
existing parents. Publish designated reviewed source and sanitized actual
validation only, excluding actual locks, package metadata/artifacts, environment
configuration, results, personal paths, real timestamps, original private source,
interpreter/dependency binaries and raw logs. See [USAGE.md](../USAGE.md),
[QUALIFICATION.md](QUALIFICATION.md) and [PROVENANCE.md](PROVENANCE.md).
