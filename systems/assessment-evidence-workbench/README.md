# Offline Assessment & Evidence Management Workbench

A complete, single-operator offline management application for scope assertions,
received submission receipts, findings, duplicate/risk dispositions, manual retests,
review decisions, revision comparisons and private handoffs. MIT, TheOutlandsDev.

Python 3.12/3.13 with SQLite and a browser are sufficient. Runtime uses the standard
library. The separate optional Chromium acceptance suite needs the hash-pinned
packages in `requirements-browser.txt` and their paired browser.

## Start with fictional inputs

Extract the focused source ZIP. Open a terminal in this directory. Choose fresh
private instance directories outside the source tree and any Git repository.
The guarded I/O layer requires paths without parent-traversal components. Build
absolute sibling paths first; do not pass a literal `../` path to the application.

PowerShell:

```text
$assessmentParent = Split-Path -Parent (Get-Location).Path
$assessmentDemo = Join-Path $assessmentParent 'private-assessment-demo'
$assessmentPrivate = Join-Path $assessmentParent 'private-assessment-ui'
$assessmentArchive = Join-Path $assessmentParent 'assessment-evidence-workbench-source.zip'
python -B workbench.py --workspace "$assessmentDemo" demo
python -B workbench.py --workspace "$assessmentPrivate" init
python -B workbench.py --workspace "$assessmentPrivate" serve
```

Ubuntu shell:

```text
assessmentParent="$(dirname "$PWD")"
assessmentDemo="$assessmentParent/private-assessment-demo"
assessmentPrivate="$assessmentParent/private-assessment-ui"
assessmentArchive="$assessmentParent/assessment-evidence-workbench-source.zip"
python -B workbench.py --workspace "$assessmentDemo" demo
python -B workbench.py --workspace "$assessmentPrivate" init
python -B workbench.py --workspace "$assessmentPrivate" serve
```

The demo creates eight immutable revisions, two inert receipts, a manually reviewed
`Resolved` finding, separate legacy declarations, a private export and a validated
database backup. It executes no assessment or target. The UI command prints an
ephemeral loopback URL; open it on the same computer. Choose **Create fictional
example**, then select operation templates to add submissions, findings and retests.
Templates are editable JSON and remain bound to their original assessment/hash.
The finding detail view displays narratives as text. The receipt picker inserts
opaque bytes without recording the source filename. Use **Stop local server** to
close normally, or interrupt the terminal.

An instance has `workspace.json`, `database/`, `inbox/`, `reports/` and `backups/`.
Treat all of it as private. Scope, authorization references, identities, narratives,
evidence references and received bytes can be sensitive. The application does not
automatically redact them or prove authorization, identity, rights or outcomes.

## CLI and compatibility

```text
python -B workbench.py --workspace "$assessmentPrivate" list
python -B workbench.py --workspace "$assessmentPrivate" create --file inbox/create.json
python -B workbench.py --workspace "$assessmentPrivate" act --file inbox/command.json
python -B workbench.py --workspace "$assessmentPrivate" show --assessment sample_assessment
python -B workbench.py --workspace "$assessmentPrivate" history --assessment sample_assessment
python -B workbench.py --workspace "$assessmentPrivate" compare --assessment sample_assessment --left 1 --right 2
python -B workbench.py --workspace "$assessmentPrivate" export --file inbox/export-review.json
python -B workbench.py --workspace "$assessmentPrivate" backup
```

Input files must already be selected inside the private instance. Each `act` input
contains `assessment_id`, the latest `expected_sha256`, and a `command` with
`operation`, `actor`, `reason` and `data`. The fictional create/command bodies are in
[sample-assessment.json](examples/sample-assessment.json). The browser generates
these complete bodies and hash pins. Unknown fields and execution commands fail.
Export review bodies require the assessment ID/hash, actor/reason, and exact Boolean
`quality`, `privacy`, `rights`, `context` checks, all true.

The `legacy` command retains the original neutral `schema_version: 1` assessment
format without silently mapping its claims into managed findings. Its unchanged
public checker reports inconsistent relationship drafts as `REVIEW_REQUIRED`.
Legacy `closure_claimed` remains an unverified declaration even when consistent.
[legacy-records.json](examples/legacy-records.json) is entirely fictional.

## Review and handoff behavior

- Each management command appends a hash-linked snapshot. Reads replay every command
  and compare its resulting snapshot. Stale assessment/finding revisions fail.
- Findings require received submission bytes. Direct `Resolved` and `Retesting`
  transitions fail. Retests require triage and a later revision of the same series.
- `Fixed` requires reproduction notes, positive-control notes and an evidence
  reference. Only an explicit accepted review can record `Resolved`. Accepting a
  fixed retest for an older-than-latest declared replacement fails. These are
  operator assertions, not independent evidence of a fix.
- Duplicate references cannot form chains/cycles. Accepted risk requires an owner
  and review condition. Disposed findings can reopen through `Triaged`.
- Every private export needs review of the current exact hash. It writes a fresh
  directory with JSON, receipt bytes and a checksum manifest. The manifest always
  says `public_release_authorized: false`. Partial failed exports stay private.
- Backups copy the database, validate its exact schema and replay its histories.
  There is no automatic restore. Preserve the current instance before a separately
  reviewed restore into a stopped private instance.

## Limits and recovery

Eight assessments, 64 revisions each, 128 total snapshots; 32 records per collection;
48 KiB per receipt and 256 KiB total received bytes per assessment; 768 KiB document,
4 MiB I/O message and 64 MiB SQLite store limits. No deletion/compaction is provided;
start a separately reviewed fresh instance when a cap is reached. Record snapshots
include received bytes, so history consumes space. History exports contain command
hashes and actor/reason summaries; exact past snapshots remain in the database and
can be viewed with `show --version N`.

Files are never unpacked, rendered as active content, imported as modules or run.
There are no scanner, lab, target network, email or deployment adapters. The UI
listens on loopback, checks Host/Origin/token, and renders private text with
`textContent`. It is for one trusted local operator; it is not multi-user security,
encrypted storage, malware isolation or tamper-proof attestation. A local attacker
able to rewrite the database and the whole history can forge assertions.

Windows/POSIX guards refuse links/reparse points, hardlinked files, alternate
streams, unsafe parents, unexpected schema and live sidecars. Exports are exclusive
and never replace files. These checks assume trusted parents and no hostile
concurrent filesystem editor. They do not guarantee zero host/browser OS writes.
After a crash, verify no instance process remains before:

```text
python -B workbench.py --workspace "$assessmentPrivate" recover --confirm-stopped
```

This only clears an unchanged empty session-lock directory; it never replays an
unfinished operation. A normal `serve` session must stop before CLI commands use
the same instance.

## Validate and package

```text
python -B -W error run_checks.py
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install --with-deps chromium
python -B -W error run_browser_checks.py
python -B release_source.py check
python -B release_source.py package --output "$assessmentArchive"
```

The source packager verifies an explicit hash inventory, includes only source,
fictional examples, docs and tests, and writes a new deterministic ZIP. It refuses
unlisted files. Never add a private instance to this tree.

See [contract](docs/CONTRACT.md), [design and origins](docs/ORIGINS.md) and
[validation boundaries](docs/VALIDATION.md).
