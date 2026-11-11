# Private workspace

Extract public source into a fresh directory. Choose a separate existing,
user-owned private parent for interpreters/venvs, invented exports, marker
controls, reviewed manifests, reports, captures and qualification work:

```text
source/public-release-audit-0.1.0/ selected source only
private/release-audit/
  venv312/                       separately created no-pip environment
  fictional_walkthrough.py       private copy of the verification driver
  fictional-demo/                new owned invented exports/controls/reports
  captures/                      private console outcomes/raw diagnostics
  qualification/                 extraction, environment, fixtures, receipts
```

Keep `release_audit.py` and `audit_windows.py` adjacent and select the intended
interpreter/script explicitly. Use stable ordinary exports under trusted
quiescent local parents. Reports/manifests must be new files under existing
private parents outside the scanned root. Keep private marker controls outside
the export as well. Parent directories are not created implicitly.

Actual marker strings can identify organizations, projects, hosts and other
private matters. Literal matching and omitted snippets do not anonymize finding
filenames, hashes, line numbers or captured results. Keep exports, markers,
mappings, reports/manifests, inventories and dispositions private; review a
separate intended export before sharing anything.

Only selected unnamed ordinary text is inspected. Root `.git` is excluded;
unknown/binary/archive/private/runtime/linked entries require review. Nothing
is imported or launched. Reads may affect access metadata and Python caches
are separate; the walkthrough uses `-B` and verifies existing bytes during each
CLI call. It deliberately adds one authored file to demonstrate manifest drift.

Existing reports/manifests must be preserved. On failure/interruption new
output can be partial or complete-looking but unconfirmed. Require the actual
result even if a report parses and looks clear. No automatic recursive cleanup/
rollback occurs. Parent ACLs and OS/Python govern permissions; output placement
and sampled native guards do not audit confidentiality.

Native guards cover supported fully spelled local paths. Trusted parents and
pathname/open/create race windows remain; no atomic multi-output transaction,
hostile-filesystem sandbox, universal I/O deadline, live/cloud/remote-provider,
all-stream backup or power-loss guarantee is made. The preserved
[WINDOWS.md](WINDOWS.md) records historical scope/evidence; fresh validation
and any reviewed Windows output correction are separate.

User-owned Python/venvs do not inherently require administrator access. Respect
device policy and OS prerequisites without bypasses. No pip packages, network,
model or account are required; interpreters remain separately licensed.

Build/qualification outputs must be fresh private destinations outside source
with existing parents. Shell redirection can independently overwrite captures;
deliberately select new paths. Publish reviewed source and sanitized evidence
only, excluding actual exports/markers/reports, private originals, personal
paths, interpreters/binaries and raw logs. See [USAGE.md](../USAGE.md),
[QUALIFICATION.md](QUALIFICATION.md) and [PROVENANCE.md](PROVENANCE.md).
