# Corpus & Model Workbench

A complete local Python application for building a reviewed coding/DevOps corpus,
searching it, preparing training/RAG exports, comparing local model responses,
and recording planner/coder/reviewer discussions. Includes a browser UI, CLI,
SQLite history, private workspaces and a fully fictional demonstration.

This release adapts the owner's original application core, model workflow,
schema and interface. It retains the implementation and methods; instance
configuration and historical content are excluded. See [design](docs/DESIGN.md),
[validation limits](docs/VALIDATION.md) and [source origins](docs/ORIGINS.md).

## Requirements

Python 3.12 or 3.13, with SQLite FTS5 enabled, on Windows or Ubuntu. Standard
library only; no Python runtime, model, model server or third-party asset is
bundled. Real model operations use an explicitly selected, separately installed
Ollama-compatible loopback service. The fictional demo needs no service.

Run commands from this application's folder. Replace `../sample-workbench` with
a new private directory outside the downloaded source or Git checkout, beneath
an existing trusted directory. Relative example paths below are invented.

## Complete fictional demonstration

```text
python -B workbench.py --workspace ../sample-workbench demo
python -B workbench.py --workspace ../sample-workbench status
python -B workbench.py --workspace ../sample-workbench serve --fictional-models --port 0
```

Open the loopback URL printed by `serve`. The fictional banner distinguishes
fake model responses from real inference. Explore **Training database**, **Model
comparisons** and **Model conversations**. Select a record to view provenance,
context, review checks and evidence notes. The demo imports five invented rows
into four deduplicated records, approves them using fictional review assertions,
exports SFT and RAG, records six fake benchmark responses and three invented
scores, creates vectors with a fake embedder, records a four-turn discussion,
queues its answer for human review and makes a database backup. No generated
code executes. Fixture scores do not measure model quality.

Use **Stop local UI** after jobs finish, or Ctrl+C, to stop. The token in the
local HTML page authorizes this session's API reads and writes; do not share the
page or expose the server. The UI binds to loopback only and is a trusted local
single-operator application, not a remotely accessible service.

## Start an empty application instance

Use a different new workspace from the demonstration:

```text
python -B workbench.py --workspace ../sample-empty init
python -B workbench.py --workspace ../sample-empty load-benchmarks
python -B workbench.py --workspace ../sample-empty import-jsonl inbox/sample-corpus.jsonl
python -B workbench.py --workspace ../sample-empty search Python
python -B workbench.py --workspace ../sample-empty export review
python -B workbench.py --workspace ../sample-empty backup
python -B workbench.py --workspace ../sample-empty serve --port 0
```

`init` installs fresh neutral settings and the two fictional input fixtures. It
does not scan, import or run anything from an existing environment. Imports and
supplemental context must be explicitly placed inside this private workspace.
All imported and model-generated records start pending. Approval requires a
reviewer, evidence note and all four explicit boolean quality/privacy/rights/
context assertions. These are local assertions, not independent verification.

Load benchmarks **before** importing candidate records so exact matching user
prompts are assigned to test. Reimport affected inputs after adding benchmarks;
loading a benchmark alone does not retroactively resplit existing records.
Linked duplicate groups inherit the most restrictive split. This is exact
content/prompt matching, not semantic contamination detection.

The UI supports approvals, exports, backups, model discovery, comparisons,
scoring and discussions. Import, benchmark loading, embeddings, semantic search,
recommendations and recovery also have CLI commands; see `--help` and each
subcommand's `--help`. Real model commands require `--url` or a manually edited
private `config/settings.json` `ollama_url`. Default is null. Only explicit HTTP
loopback URLs are allowed, with proxies and redirects disabled. No automatic
model installation or remote provider access is included.

## Storage, backup and restart

The private instance contains `workspace.json`, `config`, `database`, `inbox`,
`sources`, `exports`, `backups`, `benchmarks` and `reports`. Generated exports,
databases, prompts, reviewers, model names, scores, endpoints, histories and
backups are private application data. Source sanitization does not anonymize
future inputs or outputs. Keep the whole instance outside Git and shared folders.

One empty `.session-lock` directory prevents ordinary concurrent sessions. An
unclean stop may leave it behind. After independently confirming every process
using the instance has stopped, run:

```text
python -B workbench.py --workspace ../sample-empty recover --confirm-stopped
```

Recovery removes only an ordinary empty stale lock and marks unfinished model
runs/discussions interrupted for review. It never retries inference. Recovery
is not damaged-database repair or protection against a concurrent hostile actor.
New export folders and backup files never replace existing destinations.

Backups use SQLite's backup API and have SHA-256 receipts. They contain private
content. No automatic restoration, encryption, retention deletion, training or
external delivery is implemented. Back up a stopped private workspace separately
if you need its source files and configuration as well as its database.

## Check or package the reviewed source

```text
python -B -W error run_checks.py
python -B release_source.py check
python -B release_source.py package --output ../corpus-model-workbench-source.zip
```

The source inventory pins this application's code, docs, tests and fictional
fixtures. Packaging is deterministic and refuses existing outputs. It does not
package instances. The focused release ZIP is the reviewed application; GitHub's
automatic whole-repository archives include other collection files.

MIT, copyright TheOutlandsDev. Python and separately installed model software
retain their own terms. Model outputs and caller inputs require their own review.
