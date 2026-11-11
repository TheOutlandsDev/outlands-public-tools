# Private workspace

Extract the public source into a fresh directory. Use a separate existing,
user-owned private parent for Python/venvs, saved reports, stdout captures,
fictional walkthrough work and qualification receipts:

```text
source/source-inventory-diff-0.1.0/ selected source only
private/inventory-diff/
  venv312/                         separately created no-pip environment
  fictional_walkthrough.py         private copy of the documented driver
  fictional-demo/                  new owned fictional saved controls
  actual-before/                   real files.csv and summary.json, private
  actual-after/                    real files.csv and summary.json, private
  captures/                        caller-selected stdout and diagnostics
  qualification/                   fresh extraction, environment and receipts
```

Select the intended interpreter/script explicitly and provide `--before` and
`--after`. Only the two fixed controls per run are read. Extra files including
`tree.txt` are not opened or enumerated. Reported paths are comparison data,
never joined to a source root or used as commands. The CLI does not create
report files, scan/reopen inventoried source bodies, install, mutate, delete,
verify renames or choose a canonical copy. Capturing stdout is a separate
caller operation and shell redirection can overwrite an existing capture.

Relative filenames, timestamps, sizes, hashes and relationships can identify
projects or guessable content. Successful results intentionally retain those
fields. Fixed errors omit selected paths/metadata/native text, but they do not
anonymize caller logs, captured results or formatted library tracebacks.
Keep actual controls/results private and review a separate export before
sharing. Matching CSV/summary hashes are consistency checks without an
external authenticity anchor or verification of original bodies.

Use stable ordinary controls under trusted quiescent local ancestors. The
reader refuses observed link/reparse, multi-link, special-file and unsupported
path/name forms, sampling ancestor/descriptor/path identities and rechecking
all four files after comparison. These are sequential observations, without an
atomic four-file transaction, immutable snapshot or hostile-filesystem sandbox.
Mount aliases/rebinding, provider/network behavior, blocked OS I/O, mapped
writers, power loss and ACL privacy are outside acceptance. No network probe is
made; underlying storage can still be remote. Reads may affect OS access
metadata; Python caches are separate.

Require complete JSON and the actual exit/status before trusting a capture.
Output is bounded before printing, but interruption or OS stdout failure can
leave partial captured output. Bounds are not total CPU/memory/deadline quotas.
No checker-owned output tree exists to roll back; the walkthrough intentionally
keeps its authored work for inspection and has no automatic cleanup.

User-owned Python/venvs do not inherently require administrator access. Respect
device policy and OS prerequisites without bypasses. No pip distribution,
network, model or account is needed. The test-only producer pair is separate
from CLI execution, and interpreters remain separately licensed.

Build/qualification outputs must be new private paths outside source with
existing parents. Publish reviewed source and sanitized actual validation only,
excluding original private source, real controls/results, personal paths,
timestamps from real runs, interpreter/dependency binaries and raw logs. See
[USAGE.md](../USAGE.md), [QUALIFICATION.md](QUALIFICATION.md) and
[PROVENANCE.md](PROVENANCE.md).
