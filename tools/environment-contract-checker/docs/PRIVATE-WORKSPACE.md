# Private workspace

Extract reviewed source into a fresh directory. Keep checker/backend adjacent
and the generator under `examples`. Choose a separate existing, user-owned
private parent for Python environments, controls, fixtures, reports and receipts:

```text
source/environment-contract-checker-0.1.0/  selected source and JSON examples
private/environment-contract/
  venv312/                                  no-pip environment
  fictional_walkthrough.py                  private guide driver
  fictional-demo/                           new invented fixtures
  controls/                                 actual private declarations
  reports/                                  new private result names
  qualification/                            extraction and sanitized receipts
```

Select Python, `--contract`, optional `--root`, explicit repeatable
`--program-dir` and optional `--observations` deliberately. No implicit
PATH/PATHEXT/current-directory search, environment expansion, package install,
target-body read/import/execution, service probe or host/account/hardware inventory
occurs. Only selected control JSON and new-report readback are read as contents.
POSIX program checks additionally observe execute access. Present metadata proves
no runnable/compatible/correctly versioned or operationally ready program.

Unselected scopes yield UNKNOWN; an explicitly invalid root is an error. A
selected missing program directory can yield MISSING and is never created; it
remains a protected report exclusion. Observation true/false values always stay
UNKNOWN, with fixed unverified-attestation evidence. IDs/statuses/boolean evidence
can identify work even when paths, program names and raw environment strings are
omitted. Keep actual contracts/results/history private; fixed errors do not
anonymize captures or library tracebacks.

Reports must be new with existing parents outside source and every selected
root/program directory, including missing selections. Two constant-block repairs
protect the whole collection in literal `tools/environment-contract-checker`
placement, otherwise the standalone module folder. This is not Git discovery.
The Windows writer refuses an observed existing output leaf before CRT creation;
the check does not remove concurrent-mutation windows. Exclusive creation, write
loops, flush and readback can leave partial or complete-looking unconfirmed new
output on failure. Require actual exit/status; retain failures and choose new
names for retry. No overwrite, parent creation, auto-cleanup or rollback occurs.
Caller stdout capture/redirection has separate overwrite behavior.

The generator requires `--destination` to be a new absolute external directory
with an ordinary existing parent and verifiable boundary identities. It creates
three child directories and two invented files, including a program it never
runs. Writes are new-only and flushed; this is not an installer or final
application-consistency proof. Failure can leave a partial new tree without
automatic deletion. Generated files stay private. Requested 0700/0600 modes
depend on OS/Python/ACL behavior, not guaranteed confidentiality or encryption.

Use canonical trusted paths and one operator with quiescent local inputs. Target
metadata and native control/report I/O have distinct path checks; no blanket
original-spelling/alias refusal is promised. Observed unsafe links/reparse/
special/multi-link nodes and sampled changes are not treated as present. Held
handles/sampled identities are not atomic snapshots, writer denial, a hostile-
filesystem sandbox or I/O deadline. Metadata access can use OS network storage
without a socket/DNS probe. Rebinding, arbitrary mounts, remote/cloud/live
providers, all-stream inspection, ACL privacy, blocked I/O and power loss remain
outside acceptance. Access metadata/caches remain separate.

Controls are bounded at 64 KiB each; contracts at 128 requirements; program
search at 16 explicit directories; relative names at 240 characters/32 parts.
At most 2,048 target probes and a five-second between-probe budget are checked.
That clock cannot interrupt a blocked filesystem call or bound the whole command.
These are not total CPU/RAM/JSON-depth/storage quotas. See [README.md](../README.md).

User-owned Python/venvs need no inherent administrator access; respect device
policy without bypasses. No pip distribution, account or model is needed.
Build/qualification outputs must be new external private paths with existing
parents. Publish reviewed source and sanitized actual validation only; exclude
real records, identities, credentials, observations, actual generated/installed
programs, paths, private originals, binaries and raw diagnostics. See
[USAGE.md](../USAGE.md), [QUALIFICATION.md](QUALIFICATION.md),
[PROVENANCE.md](PROVENANCE.md) and historical [IO-SAFETY.md](../IO-SAFETY.md).
