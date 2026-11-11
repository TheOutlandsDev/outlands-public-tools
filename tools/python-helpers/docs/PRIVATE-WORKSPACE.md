# Private workspace

Extract public source into a fresh directory. Choose a separate existing,
user-owned private parent for interpreters/venvs, authored JSON fixtures,
consumer scripts, decoded/redacted values, explicit captures and qualification:

```text
source/python-helpers-0.1.0/     selected source only
private/python-helpers/
  venv312/                     separately created no-pip environment
  fictional_consumer.py        private copy of the supplied demonstration
  fictional-demo/              new owned JSON fixture directory
  captures/                    caller-selected private API outcomes/logs
  qualification/               extraction, clean environment/test work, receipts
```

This library has no CLI, report writer, installer or background service. Import
the explicitly selected source module; keep its Windows companion adjacent.
Your consumer selects inputs, serializes results and controls any captures.
Use fresh destinations for demonstrations/captures; ordinary shell redirection
or consumer code can overwrite files independently of the library.

Use stable ordinary files under trusted quiescent local parents. Existing native
path/provider/link guards remain in force. Parent traversal and observed links/
reparse paths are refused; supported hardlinked files remain allowed. Checks
have pathname/open race windows, not atomic snapshots, hostile-filesystem
containment, universal deadlines, live/provider or power-loss acceptance.

The loader does not rewrite inputs or create outputs; reads may affect OS
access metadata, and Python can manage import caches separately. The supplied
consumer uses `-B` and verifies input/runtime bytes. Its fixtures are fictional,
not a license to run arbitrary/private source or dump real data.

Redaction replaces values under known normalized keys only. Unknown keys, free
text, identifying metadata and existing float semantics remain. Fixed error
messages do not anonymize caller tracebacks, caught exception objects/contexts,
decoded/redacted values or logs. Keep actual inputs/results and captures out of
public source control and review them before sharing. Redaction is not privacy,
secret-detection, ownership or publication clearance.

User-owned Python/venvs do not inherently require administrator access. Respect
device policy and OS prerequisites without bypasses. The library needs no
packages, network, model or account. Qualified environments contain no pip or
installed distributions; interpreters remain separately licensed prerequisites.

Source packaging/qualification destinations must be new with existing parents,
outside source. Publish designated reviewed source assets and sanitized metadata
only. Real JSON, captured results, original helpers, runtime/dependency binaries,
private paths and raw logs are not public source payloads. See
[USAGE.md](../USAGE.md), [QUALIFICATION.md](QUALIFICATION.md) and the preserved
[INPUT-CONTRACT.md](INPUT-CONTRACT.md).
